"""Tests for new V3 features: recall_stream, query_entity_v2, query_path, FSRS review cards."""

from __future__ import annotations

import pytest

from mempalace_evolve.sdk import MemPalace


# ---------------------------------------------------------------------------
# recall_stream
# ---------------------------------------------------------------------------

class TestRecallStream:
    def test_stream_yields_items(self, palace):
        palace.remember("Python async patterns", room="decisions")
        palace.remember("Django ORM tips", room="decisions")

        results = list(palace.recall_stream("Python", limit=2))
        assert len(results) >= 1
        for item in results:
            assert "content" in item

    def test_stream_respects_limit(self, palace):
        palace.remember("A", room="general")
        palace.remember("B", room="general")
        palace.remember("C", room="general")

        results = list(palace.recall_stream("A B C", limit=2))
        assert len(results) <= 2

    def test_stream_empty_palace(self, palace):
        results = list(palace.recall_stream("nothing"))
        assert results == []

    def test_stream_sets_stream_meta_after_first(self, palace):
        palace.remember("First entry", room="general")
        palace.remember("Second entry", room="general")

        results = list(palace.recall_stream("entry", limit=3))
        if len(results) >= 2:
            for i, item in enumerate(results):
                if i > 0:
                    meta = item.get("_stream_meta")
                    assert meta is not None, f"Item {i} missing _stream_meta"
                    assert "index" in meta
                    assert "total" in meta
                    assert "is_last" in meta

    def test_stream_room_filter(self, palace):
        palace.remember("Python config", room="config")
        palace.remember("Python decision", room="decisions")

        results = list(palace.recall_stream("Python", room="config", limit=3))
        for item in results:
            meta = item.get("metadata", {})
            assert meta.get("room") == "config"


# ---------------------------------------------------------------------------
# query_entity_v2
# ---------------------------------------------------------------------------

class TestQueryEntityV2:
    def test_returns_structured_result(self, palace_with_kg):
        result = palace_with_kg.query_entity_v2("Python")
        assert "entity" in result
        assert result["entity"] == "Python"
        assert "outgoing" in result
        assert "incoming" in result
        assert isinstance(result["outgoing"], list)
        assert isinstance(result["incoming"], list)

    def test_outgoing_contains_subject_predicate_object(self, palace_with_kg):
        result = palace_with_kg.query_entity_v2("Python")
        assert len(result["outgoing"]) >= 1
        for edge in result["outgoing"]:
            assert "subject" in edge
            assert "predicate" in edge
            assert "object" in edge

    def test_incoming_contains_referencing_facts(self, palace_with_kg):
        result = palace_with_kg.query_entity_v2("Python")
        assert len(result["incoming"]) >= 1
        for edge in result["incoming"]:
            assert "subject" in edge
            assert "predicate" in edge
            assert "object" in edge

    def test_empty_entity(self, palace):
        result = palace.query_entity_v2("NonExistent")
        assert result["entity"] == "NonExistent"
        assert result["outgoing"] == []
        assert result["incoming"] == []

    def test_as_of_temporal_filter(self, palace_with_kg):
        result = palace_with_kg.query_entity_v2("Python", as_of="2099-01-01")
        assert result["entity"] == "Python"
        total = len(result["outgoing"]) + len(result["incoming"])
        assert total >= 1

    def test_entity_with_many_relations(self, palace):
        palace.add_fact("Central", "depends_on", "A")
        palace.add_fact("Central", "depends_on", "B")
        palace.add_fact("Central", "depends_on", "C")
        palace.add_fact("X", "references", "Central")
        palace.add_fact("Y", "uses", "Central")

        result = palace.query_entity_v2("Central")
        assert len(result["outgoing"]) == 3
        assert len(result["incoming"]) == 2


# ---------------------------------------------------------------------------
# query_path
# ---------------------------------------------------------------------------

class TestQueryPath:
    def test_direct_path(self, palace_with_kg):
        path = palace_with_kg.query_path("Flask", "Python", max_depth=4)
        assert len(path) >= 1
        for edge in path:
            assert "predicate" in edge
            assert "direction" in edge

    def test_no_path(self, palace):
        path = palace.query_path("A", "B", max_depth=4)
        assert path == []

    def test_path_max_depth_respected(self, palace):
        palace.add_fact("A", "links_to", "B")
        palace.add_fact("B", "links_to", "C")
        palace.add_fact("C", "links_to", "D")
        palace.add_fact("D", "links_to", "E")

        path = palace.query_path("A", "E", max_depth=1)
        assert path == []

    def test_self_path(self, palace):
        path = palace.query_path("Python", "Python", max_depth=4)
        assert path == []

    def test_longer_chain(self, palace):
        palace.add_fact("A", "next", "B")
        palace.add_fact("B", "next", "C")
        palace.add_fact("C", "next", "D")

        path = palace.query_path("A", "D", max_depth=5)
        assert len(path) == 3


# ---------------------------------------------------------------------------
# FSRS ReviewCard lifecycle integration
# ---------------------------------------------------------------------------

def _set_recall_count(palace, drawer_id, count):
    """Helper to set recall_count on a memory to make it review-eligible."""
    col = palace._get_collection()
    data = col.get(ids=[drawer_id], include=["metadatas"])
    if data and data.get("metadatas"):
        meta = data["metadatas"][0]
        meta["recall_count"] = count
        # Also set a past last_accessed to make it immediately due
        meta["last_accessed"] = "2020-01-01T00:00:00+00:00"
        col.update(ids=[drawer_id], metadatas=[meta])


class TestFSRSLifecycle:
    def test_full_review_cycle(self, palace):
        did = palace.remember("Review candidate memory", room="general")
        assert did

        _set_recall_count(palace, did, 2)

        due = palace.get_due_for_review()
        assert did in [d["id"] for d in due]

        # Mark as reviewed
        ok = palace.mark_reviewed(did)
        assert ok is True

        # After review it should not be due (re-set interval)
        due = palace.get_due_for_review()
        assert did not in [d["id"] for d in due]

    def test_mark_reviewed_nonexistent(self, palace):
        ok = palace.mark_reviewed("nonexistent_id")
        assert ok is False

    def test_snooze_delays_review(self, palace):
        did = palace.remember("Snooze test memory for review", room="general")
        _set_recall_count(palace, did, 2)

        due = palace.get_due_for_review()
        assert did in [d["id"] for d in due]

        ok = palace.snooze_memory(did, days=90)
        assert ok is True

        # After snoozing far out, should not be due
        due = palace.get_due_for_review()
        assert did not in [d["id"] for d in due]

    def test_snooze_nonexistent(self, palace):
        ok = palace.snooze_memory("nonexistent_id")
        assert ok is False

    def test_score_memories_returns_result(self, palace):
        palace.remember("Important decision memory", room="decisions")
        palace.remember("Trivial note memory data", room="general")

        result = palace.score_memories()
        assert "scored" in result
        assert "scores" in result
        assert result["scored"] >= 2

    def test_top_memories_returns_best(self, palace):
        for i in range(5):
            palace.remember(f"Memory item number {i}", room="general")

        palace.score_memories()
        top = palace.top_memories(n=3)
        assert len(top) <= 3
        for item in top:
            assert "id" in item
            assert "score" in item

    def test_top_memories_empty(self, palace):
        top = palace.top_memories(n=5)
        assert top == []

    def test_find_similar_basic(self, palace):
        # Content must be >= 20 characters for find_similar to work
        content = "JWT authentication with RS256 signing algorithm practice"
        palace.remember(content, room="decisions")
        similar = palace.find_similar(
            "JWT authentication using RS256 signing method",
            threshold=0.5,
        )
        assert len(similar) >= 1
        for item in similar:
            assert "content" in item
            assert "distance" in item

    def test_find_similar_no_match(self, palace):
        palace.remember("Python project config management guide", room="config")
        similar = palace.find_similar("ZXYQPT totally unrelated nonsense data", threshold=0.99)
        assert similar == []
