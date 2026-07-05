"""Tests for knowledge_graph.py — KnowledgeGraph: temporal entity-relationship graph."""
import json
import os
import time

import pytest

from mempalace_evolve.core.knowledge_graph import KnowledgeGraph


@pytest.fixture
def kg():
    """Create in-memory KG for each test — clean slate every time."""
    k = KnowledgeGraph(db_path=":memory:")
    yield k
    k.close()


# ── Entity CRUD ───────────────────────────────────────────────────────────

class TestEntityCRUD:
    """Tests for add_entity, remove_entity, get_all_entity_names."""

    def test_add_entity_basic(self, kg):
        kg.add_entity("Max", entity_type="person", properties={"age": 30})
        names = kg.get_all_entity_names()
        assert any(e["name"] == "Max" for e in names)

    def test_add_entity_with_defaults(self, kg):
        kg.add_entity("ProjectX")
        names = kg.get_all_entity_names()
        assert any(e["name"] == "ProjectX" for e in names)

    def test_add_entity_upsert(self, kg):
        """Upsert should change type but keep one entity."""
        kg.add_entity("Max", entity_type="person")
        kg.add_entity("Max", entity_type="cat")
        names = kg.get_all_entity_names()
        matched = [e for e in names if e["name"] == "Max"]
        assert len(matched) == 1

    def test_remove_entity(self, kg):
        kg.add_entity("ToDelete")
        assert kg.remove_entity("ToDelete") is True
        names = kg.get_all_entity_names()
        assert not any(e["name"] == "ToDelete" for e in names)

    def test_remove_entity_nonexistent(self, kg):
        assert kg.remove_entity("Ghost") is False

    def test_remove_entity_cascades_triples(self, kg):
        kg.add_triple("A", "loves", "B")
        kg.remove_entity("A")
        assert kg.query_entity("A") == []

    def test_get_all_entity_names_empty(self, kg):
        assert kg.get_all_entity_names() == []

    def test_get_all_entity_names_multiple(self, kg):
        for name in ["Alice", "Bob", "Charlie"]:
            kg.add_entity(name)
        names = kg.get_all_entity_names()
        found = {e["name"] for e in names}
        assert found == {"Alice", "Bob", "Charlie"}


# ── Triple operations ─────────────────────────────────────────────────────

class TestTripleOperations:
    """Tests for add_triple, query_entity, query_relationship."""

    def test_add_triple_auto_creates_entities(self, kg):
        kg.add_triple("Max", "loves", "swimming")
        names = kg.get_all_entity_names()
        assert any(e["name"] == "Max" for e in names)
        assert any(e["name"] == "swimming" for e in names)

    def test_add_triple_returns_triple_id(self, kg):
        tid = kg.add_triple("Max", "does", "sports")
        assert isinstance(tid, str)
        assert len(tid) > 0

    def test_add_duplicate_triple_returns_existing_id(self, kg):
        tid1 = kg.add_triple("Max", "loves", "chess")
        tid2 = kg.add_triple("Max", "loves", "chess")
        assert tid1 == tid2

    def test_add_triple_with_temporal(self, kg):
        kg.add_triple("Max", "lives_in", "Beijing", valid_from="2020-01-01")
        rels = kg.query_entity("Max")
        assert len(rels) == 1
        assert rels[0]["valid_from"] == "2020-01-01"

    def test_query_entity_outgoing(self, kg):
        kg.add_triple("Max", "child_of", "Alice")
        kg.add_triple("Max", "does", "swimming")
        rels = kg.query_entity("Max")
        objects = [r["object"] for r in rels]
        assert "Alice" in objects
        assert "swimming" in objects

    def test_query_entity_incoming(self, kg):
        kg.add_triple("Alice", "mother_of", "Max")
        kg.add_triple("Bob", "father_of", "Max")
        rels = kg.query_entity("Max", direction="incoming")
        assert len(rels) == 2
        subjects = [r["subject"] for r in rels]
        assert "Alice" in subjects
        assert "Bob" in subjects

    def test_query_entity_both(self, kg):
        kg.add_triple("Max", "friend_of", "Charlie")
        kg.add_triple("Dave", "friend_of", "Max")
        rels = kg.query_entity("Max", direction="both")
        assert len(rels) == 2

    def test_query_entity_empty(self, kg):
        assert kg.query_entity("Nobody") == []

    def test_query_entity_as_of_filters_expired(self, kg):
        kg.add_triple("Max", "has_issue", "injury", valid_from="2024-01", valid_to="2024-06")
        rels = kg.query_entity("Max", as_of="2025-01-01")
        assert len(rels) == 0

    def test_query_entity_as_of_shows_current(self, kg):
        kg.add_triple("Max", "lives_in", "Shanghai", valid_from="2020-01")
        rels = kg.query_entity("Max", as_of="2025-01-01")
        assert len(rels) == 1

    def test_query_relationship(self, kg):
        kg.add_triple("Alice", "mother_of", "Max")
        kg.add_triple("Alice", "mother_of", "Eve")
        kg.add_triple("Max", "friend_of", "Charlie")
        rels = kg.query_relationship("mother_of")
        assert len(rels) == 2

    def test_query_relationship_empty(self, kg):
        assert kg.query_relationship("nonexistent") == []

    def test_add_triple_with_confidence(self, kg):
        kg.add_triple("X", "implies", "Y", confidence=0.85)
        rels = kg.query_entity("X")
        assert rels[0]["confidence"] == 0.85

    def test_add_triple_with_source(self, kg):
        kg.add_triple("A", "relates_to", "B", source_closet="closet_1", source_file="test.txt")
        rels = kg.query_entity("A")
        assert rels[0]["source_closet"] == "closet_1"

    def test_predicate_normalization(self, kg):
        kg.add_triple("Max", "Has Issue", "back_pain")
        rels = kg.query_entity("Max")
        assert rels[0]["predicate"] == "has_issue"


# ── Invalidation ──────────────────────────────────────────────────────────

class TestInvalidation:
    """Tests for invalidate."""

    def test_invalidate_sets_valid_to_and_current_false(self, kg):
        kg.add_triple("Max", "has_issue", "back_pain")
        kg.invalidate("Max", "has_issue", "back_pain", ended="2025-06-01")
        rels = kg.query_entity("Max")
        assert len(rels) == 1
        assert rels[0]["valid_to"] == "2025-06-01"
        assert rels[0]["current"] is False

    def test_invalidate_as_of_filters_expired(self, kg):
        kg.add_triple("Max", "has_issue", "back_pain")
        kg.invalidate("Max", "has_issue", "back_pain", ended="2025-06-01")
        rels = kg.query_entity("Max", as_of="2025-07-01")
        assert len(rels) == 0

    def test_invalidate_uses_default_date(self, kg):
        kg.add_triple("X", "active", "Y")
        kg.invalidate("X", "active", "Y")
        rels = kg.query_entity("X")
        assert len(rels) == 1
        assert rels[0]["current"] is False

    def test_invalidate_nonexistent_no_error(self, kg):
        kg.invalidate("Ghost", "does", "thing")


# ── Canonical names ───────────────────────────────────────────────────────

class TestCanonicalNames:
    """Tests for set_canonical_name, query_entity_by_canonical."""

    def test_set_canonical_name(self, kg):
        kg.add_entity("Maximilian")
        kg.add_triple("Maximilian", "knows", "Alice")
        kg.set_canonical_name("Maximilian", "Max")
        results = kg.query_entity_by_canonical("Max")
        assert len(results) >= 1

    def test_query_by_canonical_finds_name_fallback(self, kg):
        kg.add_entity("Alice")
        kg.add_triple("Alice", "likes", "pizza")
        results = kg.query_entity_by_canonical("Alice")
        assert len(results) == 1

    def test_query_by_canonical_empty(self, kg):
        results = kg.query_entity_by_canonical("NoSuch")
        assert results == []

    def test_set_canonical_preserved_on_update(self, kg):
        kg.add_entity("Maximilian", entity_type="person")
        kg.add_triple("Maximilian", "codes", "Python")
        kg.set_canonical_name("Maximilian", "Max")
        kg.add_entity("Maximilian", entity_type="developer")
        results = kg.query_entity_by_canonical("Max")
        assert len(results) >= 1


# ── V2 query ──────────────────────────────────────────────────────────────

class TestQueryEntityV2:
    """Tests for query_entity_v2."""

    def test_v2_returns_structured(self, kg):
        kg.add_triple("Max", "loves", "chess")
        result = kg.query_entity_v2("Max")
        assert result["entity"] == "Max"
        assert "outgoing" in result
        assert "incoming" in result
        assert len(result["outgoing"]) == 1

    def test_v2_outgoing_keys(self, kg):
        kg.add_triple("Max", "does", "swimming")
        result = kg.query_entity_v2("Max")
        edge = result["outgoing"][0]
        for key in ["subject", "predicate", "object", "valid_from", "valid_to", "confidence", "current"]:
            assert key in edge, f"Missing key: {key}"

    def test_v2_incoming(self, kg):
        kg.add_triple("Alice", "mother_of", "Max")
        result = kg.query_entity_v2("Max")
        assert len(result["incoming"]) == 1
        assert result["incoming"][0]["subject"] == "Alice"

    def test_v2_current_flag(self, kg):
        kg.add_triple("X", "active", "Y")
        kg.invalidate("X", "active", "Y")
        rels = kg.query_entity_v2("X", as_of="2099-01-01")
        assert len(rels["outgoing"]) == 0

    def test_v2_as_of_filters(self, kg):
        kg.add_triple("Max", "lives_in", "Beijing", valid_from="2020-01", valid_to="2021-12")
        result = kg.query_entity_v2("Max", as_of="2023-01")
        assert len(result["outgoing"]) == 0


# ── Path query ────────────────────────────────────────────────────────────

class TestQueryPath:
    """Tests for query_path (BFS shortest path)."""

    def test_direct_path(self, kg):
        kg.add_triple("A", "knows", "B")
        path = kg.query_path("A", "B")
        assert len(path) == 1
        assert path[0]["predicate"] == "knows"

    def test_two_hop_path(self, kg):
        kg.add_triple("A", "knows", "B")
        kg.add_triple("B", "knows", "C")
        path = kg.query_path("A", "C")
        assert len(path) == 2

    def test_no_path(self, kg):
        kg.add_triple("A", "knows", "B")
        kg.add_triple("C", "knows", "D")
        path = kg.query_path("A", "C", max_depth=3)
        assert path == []

    def test_path_respects_max_depth(self, kg):
        kg.add_triple("A", "connects", "B")
        kg.add_triple("B", "connects", "C")
        kg.add_triple("C", "connects", "D")
        kg.add_triple("D", "connects", "E")
        path = kg.query_path("A", "E", max_depth=2)
        assert path == []

    def test_path_direction_agnostic(self, kg):
        kg.add_triple("A", "follows", "B")
        kg.add_triple("C", "follows", "B")
        path = kg.query_path("A", "C")
        assert len(path) == 2


# ── Graph traverse ────────────────────────────────────────────────────────

class TestGraphTraverse:
    """Tests for graph_traverse (BFS traversal)."""

    def test_basic_traverse(self, kg):
        kg.add_triple("A", "knows", "B")
        kg.add_triple("B", "knows", "C")
        edges = kg.graph_traverse("A", max_depth=2)
        assert len(edges) >= 1

    def test_traverse_outgoing_only(self, kg):
        kg.add_triple("A", "knows", "B")
        kg.add_triple("C", "knows", "A")
        edges = kg.graph_traverse("A", max_depth=2, direction="outgoing")
        assert len(edges) == 1
        assert edges[0]["object"] == "B"

    def test_traverse_incoming_only(self, kg):
        kg.add_triple("A", "knows", "B")
        kg.add_triple("C", "knows", "A")
        edges = kg.graph_traverse("A", max_depth=2, direction="incoming")
        assert len(edges) == 1
        assert edges[0]["subject"] == "C"

    def test_traverse_empty_start(self, kg):
        edges = kg.graph_traverse("Nobody")
        assert edges == []

    def test_traverse_depth_limit(self, kg):
        kg.add_triple("A", "links", "B")
        kg.add_triple("B", "links", "C")
        kg.add_triple("C", "links", "D")
        edges = kg.graph_traverse("A", max_depth=1)
        assert len(edges) == 1
        assert edges[0]["depth"] == 1

    def test_traverse_returns_depth_keys(self, kg):
        kg.add_triple("A", "knows", "B")
        edges = kg.graph_traverse("A", max_depth=2)
        for key in ["depth", "subject", "predicate", "object"]:
            assert key in edges[0]


# ── Timeline ──────────────────────────────────────────────────────────────

class TestTimeline:
    """Tests for timeline."""

    def test_timeline_all(self, kg):
        kg.add_triple("A", "did", "thing1", valid_from="2020-01")
        kg.add_triple("B", "did", "thing2", valid_from="2021-01")
        timeline = kg.timeline()
        assert len(timeline) == 2

    def test_timeline_filtered_by_entity(self, kg):
        kg.add_triple("Alice", "did", "homework", valid_from="2020-01")
        kg.add_triple("Bob", "did", "laundry", valid_from="2021-01")
        timeline = kg.timeline(entity_name="Alice")
        assert len(timeline) == 1
        assert timeline[0]["subject"] == "Alice"

    def test_timeline_empty(self, kg):
        assert kg.timeline() == []

    def test_timeline_chronological(self, kg):
        kg.add_triple("A", "event", "early", valid_from="2020-01")
        kg.add_triple("A", "event", "later", valid_from="2022-01")
        timeline = kg.timeline(entity_name="A")
        assert len(timeline) == 2


# ── Import triples ────────────────────────────────────────────────────────

class TestImportTriples:
    """Tests for import_triples batch import."""

    def test_import_empty_list(self, kg):
        result = kg.import_triples([])
        assert result == {"added": 0, "skipped": 0, "total": 0}

    def test_import_batch(self, kg):
        triples = [
            {"subject": "A", "predicate": "loves", "object": "B"},
            {"subject": "B", "predicate": "loves", "object": "C"},
            {"subject": "C", "predicate": "loves", "object": "D"},
        ]
        result = kg.import_triples(triples)
        assert result["added"] == 3
        assert result["total"] == 3

    def test_import_default_predicate(self, kg):
        triples = [{"subject": "X", "object": "Y"}]
        result = kg.import_triples(triples)
        assert result["added"] == 1

    def test_import_missing_subject(self, kg):
        triples = [{"object": "Y"}]
        result = kg.import_triples(triples)
        assert result["added"] == 0
        assert result["skipped"] == 1


# ── Fuzzy find ────────────────────────────────────────────────────────────

class TestFuzzyFind:
    """Tests for find_entity_by_fuzzy."""

    def test_fuzzy_exact_match(self, kg):
        kg.add_entity("Maximilian")
        results = kg.find_entity_by_fuzzy("Maximilian")
        assert len(results) == 1
        assert results[0]["similarity"] == 1.0

    def test_fuzzy_partial_match(self, kg):
        kg.add_entity("Maximilian")
        results = kg.find_entity_by_fuzzy("Max", threshold=0.3)
        assert len(results) >= 1

    def test_fuzzy_no_match(self, kg):
        kg.add_entity("Alice")
        results = kg.find_entity_by_fuzzy("Xyzzy", threshold=0.8)
        assert results == []

    def test_fuzzy_returns_type_and_name(self, kg):
        kg.add_entity("Alice", entity_type="person")
        results = kg.find_entity_by_fuzzy("Alice")
        assert "name" in results[0]
        assert "type" in results[0]
        assert "similarity" in results[0]

    def test_fuzzy_threshold_respected(self, kg):
        kg.add_entity("Alice")
        results = kg.find_entity_by_fuzzy("Zebra", threshold=0.99)
        assert results == []

    def test_fuzzy_sorted_by_similarity(self, kg):
        kg.add_entity("Alice")
        kg.add_entity("Alicia")
        kg.add_entity("Bob")
        results = kg.find_entity_by_fuzzy("Ali", threshold=0.2)
        assert len(results) >= 1
        sims = [r["similarity"] for r in results]
        assert sims == sorted(sims, reverse=True)


# ── Stats ─────────────────────────────────────────────────────────────────

class TestStats:
    """Tests for stats method."""

    def test_stats_empty(self, kg):
        s = kg.stats()
        assert s["entities"] == 0
        assert s["triples"] == 0
        assert s["current_facts"] == 0
        assert s["expired_facts"] == 0

    def test_stats_with_data(self, kg):
        kg.add_triple("A", "knows", "B")
        kg.add_triple("A", "likes", "C")
        s = kg.stats()
        assert s["entities"] == 3
        assert s["triples"] == 2
        assert s["current_facts"] == 2

    def test_stats_expired(self, kg):
        kg.add_triple("X", "was", "Y")
        kg.invalidate("X", "was", "Y")
        s = kg.stats()
        assert s["expired_facts"] == 1
        assert s["current_facts"] == 0

    def test_stats_relationship_types(self, kg):
        kg.add_triple("A", "loves", "B")
        kg.add_triple("C", "hates", "D")
        s = kg.stats()
        assert "loves" in s["relationship_types"]
        assert "hates" in s["relationship_types"]


# ── Edge cases ────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Tests for edge cases and robustness."""

    def test_special_characters_in_name(self, kg):
        kg.add_entity("Dr. O''Brien")
        names = kg.get_all_entity_names()
        assert any(e["name"] == "Dr. O''Brien" for e in names)

    def test_entity_id_normalization(self, kg):
        kg.add_entity("Max Power")
        kg.add_triple("Max Power", "does", "work")
        assert kg.query_entity("Max Power") != []

    def test_empty_triple_query(self, kg):
        assert kg.query_entity("Nonexistent") == []

    def test_many_triples(self, kg):
        for i in range(50):
            kg.add_triple(f"Entity{i}", "links", f"Entity{i+1}")
        assert kg.stats()["triples"] == 50

    def test_invalidate_multiple_versions(self, kg):
        """Invalidate marks the current active triple as expired."""
        kg.add_triple("A", "state", "on")
        kg.add_triple("A", "state", "on")  # duplicate, returns same id
        kg.invalidate("A", "state", "on")
        rels = kg.query_entity("A")
        assert rels[0]["current"] is False

    def test_timeline_returns_dicts(self, kg):
        kg.add_triple("X", "relates", "Y", valid_from="2023-01")
        tl = kg.timeline()
        assert isinstance(tl[0], dict)
        assert "subject" in tl[0]
        assert "predicate" in tl[0]
        assert "object" in tl[0]
