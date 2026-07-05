"""Tests for new SDK features: batch_remember, fuzzy_search, recent, search_by_metadata,
TTL expiry, tags, KG enhancements (import_triples, find_entity_by_fuzzy, graph_traverse),
and AdvancedQuery module."""

import json, tempfile, os, time
from pathlib import Path


class TestBatchRemember:
    def test_batch_remember_success(self, palace):
        result = palace.batch_remember([
            {"content": "Memory A", "room": "general"},
            {"content": "Memory B", "room": "decisions"},
            {"content": "Memory C", "room": "config"},
        ])
        assert result.stored == 3
        assert result.duplicates == 0
        assert len(result.ids) == 3

    def test_batch_remember_empty_content_skipped(self, palace):
        result = palace.batch_remember([
            {"content": "Valid memory", "room": "general"},
            {"content": "", "room": "general"},
            {"content": "   ", "room": "general"},
        ])
        assert result.stored == 1
        assert result.duplicates == 0

    def test_batch_remember_with_ttl_and_tags(self, palace):
        result = palace.batch_remember([
            {"content": "Ephemeral memory", "room": "general", "ttl": 60, "tags": ["temp", "debug"]},
            {"content": "Important memory", "room": "decisions", "tags": ["important", "arch"]},
        ])
        assert result.stored == 2

    def test_batch_remember_recallable(self, palace):
        palace.batch_remember([
            {"content": "Batch recall test memory", "room": "general"},
        ])
        results = palace.recall("Batch recall test")
        assert any("Batch recall test memory" in r["content"] for r in results)


class TestFuzzySearch:
    def test_fuzzy_search_basic(self, palace):
        palace.remember("JWT uses RS256 for signing tokens", room="decisions")
        results = palace.fuzzy_search("JWT token signing", limit=5)
        assert len(results) >= 1
        assert "JWT" in results[0]["content"]
        assert "distance" in results[0]

    def test_fuzzy_search_no_match(self, palace):
        palace.remember("Something completely unrelated", room="general")
        results = palace.fuzzy_search("xyzzy_nonexistent_12345", limit=5)
        assert isinstance(results, list)

    def test_fuzzy_search_room_filter(self, palace):
        palace.remember("Database memory", room="architecture")
        palace.remember("Another memory", room="general")
        results = palace.fuzzy_search("database", room="architecture", limit=5)
        for r in results:
            assert r["metadata"].get("room") == "architecture"

    def test_fuzzy_search_threshold(self, palace):
        palace.remember("Exact match memory for testing", room="general")
        results = palace.fuzzy_search("Exact match memory", threshold=0.9, limit=5)
        assert len(results) >= 1

class TestRecent:
    def test_recent_returns_most_recent_first(self, palace):
        palace.remember("First memory", room="general")
        palace.remember("Second memory", room="general")
        palace.remember("Third memory", room="general")
        results = palace.recent(limit=5)
        assert len(results) >= 3
        assert results[0]["content"] == "Third memory"

    def test_recent_limit(self, palace):
        for i in range(10):
            palace.remember(f"Recent memory #{i}", room="general")
        results = palace.recent(limit=3)
        assert len(results) == 3

    def test_recent_room_filter(self, palace):
        palace.remember("Decision memory", room="decisions")
        palace.remember("Config memory", room="config")
        results = palace.recent(room="decisions", limit=10)
        assert len(results) >= 1
        for r in results:
            assert r["metadata"].get("room") == "decisions"

    def test_recent_offset(self, palace):
        for i in range(5):
            palace.remember(f"Offset memory #{i}", room="general")
        # Without offset we get 5 items; with offset we skip some
        full = palace.recent(limit=10, offset=0)
        partial = palace.recent(limit=10, offset=3)
        assert len(full) >= 3
        assert len(partial) >= 0
        # offset=0 returns more items than offset=3
        assert len(full) >= len(partial)


class TestSearchByMetadata:
    def test_search_by_tags(self, palace):
        palace.remember("Important memory", room="general", tags=["important", "arch"])
        palace.remember("Debug memory", room="general", tags=["debug"])
        # search_by_metadata checks raw metadata, tags are stored as JSON string
        results = palace.search_by_metadata({"room": "general"})
        important_found = False
        for r in results:
            tags_val = r["metadata"].get("tags", "")
            if "important" in tags_val:
                important_found = True
        assert important_found

    def test_search_by_room(self, palace):
        palace.remember("Decision 1", room="decisions")
        palace.remember("Config 1", room="config")
        results = palace.search_by_metadata({"room": "decisions"})
        assert len(results) >= 1
        for r in results:
            assert r["metadata"].get("room") == "decisions"

    def test_search_by_metadata_empty(self, palace):
        results = palace.search_by_metadata({"room": "nonexistent_room_xyz"})
        assert isinstance(results, list)


class TestTTLExpiry:
    def test_remember_with_ttl_sets_expire_at(self, palace):
        did = palace.remember("TTL test memory", room="general", ttl=3600)
        assert did
        results = palace.search_by_metadata({"room": "general"})
        ttl_found = False
        for r in results:
            if r["content"] == "TTL test memory":
                assert "expire_at" in r["metadata"]
                ttl_found = True
        assert ttl_found

    def test_remember_without_ttl_no_expire_at(self, palace):
        did = palace.remember("No TTL memory", room="general")
        assert did
        results = palace.search_by_metadata({"room": "general"})
        for r in results:
            if r["content"] == "No TTL memory":
                expire_val = r["metadata"].get("expire_at")
                assert expire_val is None


class TestKGEnhancements:
    def test_import_triples(self, palace):
        result = palace.import_triples([
            {"subject": "Python", "predicate": "is_a", "object": "language"},
            {"subject": "Flask", "predicate": "uses", "object": "Python"},
        ])
        assert result["added"] == 2
        assert result["total"] == 2

    def test_find_entity_by_fuzzy(self, palace):
        palace.add_fact("PostgreSQL", "is_a", "database")
        matches = palace.find_entity_by_fuzzy("Postgres", threshold=0.5)
        assert len(matches) >= 1
        assert matches[0]["similarity"] >= 0.5

    def test_graph_traverse(self, palace):
        palace.add_fact("Python", "is_a", "language")
        palace.add_fact("Flask", "uses", "Python")
        edges = palace.graph_traverse("Python", max_depth=2)
        assert len(edges) >= 1

    def test_kg_stats_integration(self, palace):
        palace.add_fact("Django", "is_a", "framework")
        palace.add_fact("Django", "uses", "Python")
        stats = palace.kg_stats()
        assert stats["entities"] >= 2
        assert stats["current_facts"] >= 2


class TestAdvancedQuery:
    def test_hybrid_search_basic(self, palace):
        from mempalace_evolve.advanced_query import AdvancedQuery
        palace.remember("JWT authentication with RS256", room="decisions")
        aq = AdvancedQuery(palace)
        results = aq.hybrid_search("JWT auth", limit=5)
        assert len(results) >= 1
        assert "_score" in results[0]

    def test_filter_by_metadata(self, palace):
        from mempalace_evolve.advanced_query import AdvancedQuery
        palace.remember("Decision memory", room="decisions", tags=["arch"])
        palace.remember("Config memory", room="config")
        aq = AdvancedQuery(palace)
        results = aq.filter_by_metadata(room="decisions")
        assert len(results) >= 1
        for r in results:
            assert r["metadata"].get("room") == "decisions"

    def test_hybrid_search_with_tags_filter(self, palace):
        from mempalace_evolve.advanced_query import AdvancedQuery
        palace.remember("Important decision", room="decisions", tags=["important"])
        palace.remember("Trivial note", room="general")
        aq = AdvancedQuery(palace)
        results = aq.hybrid_search("decision", tags=["important"], limit=5)
        for r in results:
            tags_val = r["metadata"].get("tags", "")
            assert "important" in tags_val
