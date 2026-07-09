"""Tests for core/consolidation.py — daily memory consolidation pipeline."""

import math
from datetime import datetime, timedelta, timezone

import pytest

from mempalace_evolve.core.consolidation import (
    get_today_drawers,
    _text_similarity,
    identify_duplicates,
    identify_conflicts,
    generate_daily_summary,
    merge_similar_drawers,
    update_knowledge_graph,
    consolidate_daily,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _col(palace):
    from mempalace_evolve.core.chroma_helper import get_collection
    return get_collection(str(palace.path / "palace"), create=True)


# ---------------------------------------------------------------------------
# _text_similarity
# ---------------------------------------------------------------------------

class TestTextSimilarity:
    def test_identical_text(self):
        assert _text_similarity("hello world", "hello world") == 1.0

    def test_normalized_same(self):
        assert _text_similarity("hello   world.", "hello world") == 1.0

    def test_different_text_low_similarity(self):
        sim = _text_similarity("hello world", "completely different text")
        assert sim < 0.90

    def test_empty_text(self):
        assert _text_similarity("", "hello") == 0.0

    def test_both_empty(self):
        assert _text_similarity("", "") == 0.0

    def test_whitespace_normalization(self):
        sim = _text_similarity("hello\nworld", "hello world")
        assert sim == 1.0

    def test_trailing_punctuation_stripped(self):
        sim = _text_similarity("hello.", "hello。")
        assert sim == 1.0

    def test_any_text_difference_returns_low_score(self):
        """Any real content difference should stay under 0.90."""
        sim = _text_similarity("the quick brown fox", "the quick brown dog")
        assert sim < 0.90


# ---------------------------------------------------------------------------
# identify_duplicates
# ---------------------------------------------------------------------------

class TestIdentifyDuplicates:
    def test_empty_list(self):
        assert identify_duplicates([]) == []

    def test_no_duplicates(self):
        drawers = [
            {"id": "a", "document": "First memory"},
            {"id": "b", "document": "Second totally different memory"},
        ]
        result = identify_duplicates(drawers, threshold=0.95)
        assert result == []

    def test_identical_documents(self):
        drawers = [
            {"id": "a", "document": "same text here"},
            {"id": "b", "document": "same text here"},
        ]
        result = identify_duplicates(drawers)
        assert len(result) >= 1
        dup = result[0]
        assert "drawer1" in dup
        assert "drawer2" in dup
        assert dup["similarity"] >= 0.95

    def test_identical_documents_across_length_bucket_boundary(self):
        document = ("a" * 49).strip()
        drawers = [
            {"id": "a", "document": document},
            {"id": "b", "document": document + "."},
        ]
        result = identify_duplicates(drawers)
        assert len(result) == 1
        assert result[0]["similarity"] >= 0.95


# ---------------------------------------------------------------------------
# identify_conflicts
# ---------------------------------------------------------------------------

class TestIdentifyConflicts:
    def test_empty_decisions(self, palace):
        kg = palace._kg_store
        drawers = [{"id": "a", "document": "Grocery list", "metadata": {"room": "general"}}]
        result = identify_conflicts(drawers, kg)
        assert isinstance(result, list)

    def test_single_decision_no_conflict(self, palace):
        kg = palace._kg_store
        drawers = [
            {"id": "a", "document": "Use Python for backend", "metadata": {"room": "decisions"}}
        ]
        result = identify_conflicts(drawers, kg)
        assert result == []

    def test_returns_list(self, palace):
        kg = palace._kg_store
        drawers = [
            {"id": "a", "document": "Decision A", "metadata": {"room": "decisions"}},
            {"id": "b", "document": "Decision B", "metadata": {"room": "decisions"}},
        ]
        result = identify_conflicts(drawers, kg)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# generate_daily_summary
# ---------------------------------------------------------------------------

class TestGenerateDailySummary:
    def test_empty_drawers(self):
        result = generate_daily_summary([])
        assert result["total_drawers"] == 0
        assert result["by_room"] == {}
        assert result["key_facts"] == []
        assert result["decisions"] == []
        assert result["errors"] == []

    def test_single_drawer(self):
        drawers = [
            {
                "id": "a",
                "document": "A test memory",
                "metadata": {"room": "general", "wing": "test"},
            }
        ]
        result = generate_daily_summary(drawers)
        assert result["total_drawers"] == 1
        assert "general" in result["by_room"]

    def test_multiple_rooms(self):
        drawers = [
            {"id": "a", "document": "General note", "metadata": {"room": "general"}},
            {"id": "b", "document": "Important decision", "metadata": {"room": "decisions"}},
            {"id": "c", "document": "Error occurred", "metadata": {"room": "errors"}},
        ]
        result = generate_daily_summary(drawers)
        assert result["total_drawers"] == 3
        rooms = result["by_room"]
        assert rooms.get("general", 0) >= 1
        assert rooms.get("decisions", 0) >= 1
        assert rooms.get("errors", 0) >= 1

    def test_decisions_exist(self):
        drawers = [
            {
                "id": "a",
                "document": "We decided to use Redis",
                "metadata": {"room": "decisions"},
            }
        ]
        result = generate_daily_summary(drawers)
        assert isinstance(result["decisions"], list)

    def test_errors_exists_field(self):
        drawers = [
            {
                "id": "a",
                "document": "NullPointerException in module X",
                "metadata": {"room": "errors"},
            }
        ]
        result = generate_daily_summary(drawers)
        assert isinstance(result["errors"], list)


# ---------------------------------------------------------------------------
# merge_similar_drawers
# ---------------------------------------------------------------------------

class TestMergeSimilarDrawers:
    def test_empty_duplicates(self, palace):
        col = _col(palace)
        result = merge_similar_drawers(col, [])
        assert result == []

    def test_merge_duplicates(self, palace):
        col = _col(palace)
        drawer_id1 = palace.remember("Merge test same text", room="general")
        drawer_id2 = palace.remember("Merge test same text", room="general")

        dup = [{"drawer1": drawer_id1, "drawer2": drawer_id2, "similarity": 1.0}]
        result = merge_similar_drawers(col, dup)
        assert len(result) >= 1

    def test_dry_run_does_not_delete(self, palace):
        col = _col(palace)
        drawer_id1 = palace.remember("Dry run same text", room="general")
        drawer_id2 = palace.remember("Dry run same text", room="general")

        dup = [{"drawer1": drawer_id1, "drawer2": drawer_id2, "similarity": 1.0}]
        result = merge_similar_drawers(col, dup, dry_run=True)
        # In dry run, both drawers should still exist
        check1 = col.get(ids=[drawer_id1])
        check2 = col.get(ids=[drawer_id2])
        assert len(check1["ids"]) == 1
        assert len(check2["ids"]) == 1


# ---------------------------------------------------------------------------
# update_knowledge_graph
# ---------------------------------------------------------------------------

class TestUpdateKG:
    def test_empty_drawers(self, palace):
        kg = palace._kg_store
        result = update_knowledge_graph([], kg)
        assert result == []

    def test_uses_pattern_detected(self, palace):
        kg = palace._kg_store
        drawers = [
            {
                "id": "a",
                "document": "Python 使用 FastAPI",
                "metadata": {"filed_at": datetime.now(timezone.utc).isoformat()},
            }
        ]
        result = update_knowledge_graph(drawers, kg)
        assert isinstance(result, list)

    def test_no_uses_pattern(self, palace):
        kg = palace._kg_store
        drawers = [
            {
                "id": "a",
                "document": "Just plain text without pattern",
                "metadata": {},
            }
        ]
        result = update_knowledge_graph(drawers, kg)
        assert result == []


# ---------------------------------------------------------------------------
# consolidate_daily
# ---------------------------------------------------------------------------

class TestConsolidateDaily:
    def test_dry_run_returns_report(self, palace):
        palace.remember("Consolidation test memory", room="general")
        result = consolidate_daily(wing="test", dry_run=True)
        assert isinstance(result, dict)

    def test_no_drawers_report(self, palace):
        result = consolidate_daily(wing="nonexistent_clean_wing", dry_run=True)
        assert result["status"] == "no_drawers"
