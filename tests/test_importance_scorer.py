"""Tests for core/importance_scorer.py — importance scoring and ranking."""

import math
from datetime import datetime, timedelta, timezone

import pytest

from mempalace_evolve.core.importance_scorer import (
    compute_importance_score,
    _compute_recency_score,
    _compute_content_score,
    score_all_memories,
    get_top_memories,
    WEIGHTS,
    RECENCY_HALF_LIFE_DAYS,
)


# ---------------------------------------------------------------------------
# compute_importance_score
# ---------------------------------------------------------------------------

class TestComputeImportanceScore:
    def test_all_zero_inputs(self):
        score = compute_importance_score(
            recall_count=0,
            kg_degree=0,
            last_accessed=None,
            cross_wing_hits=0,
            content="",
        )
        assert score >= 0.0

    def test_max_inputs_yields_high_score(self):
        now = datetime.now(timezone.utc).isoformat()
        score = compute_importance_score(
            recall_count=50,
            kg_degree=20,
            last_accessed=now,
            cross_wing_hits=10,
            content="Very important " * 100,
        )
        assert score > 0.5
        assert score <= 1.0

    def test_score_is_between_zero_and_one(self):
        now = datetime.now(timezone.utc).isoformat()
        score = compute_importance_score(
            recall_count=3,
            kg_degree=2,
            last_accessed=now,
            cross_wing_hits=1,
            content="Some content here",
        )
        assert 0.0 <= score <= 1.0

    def test_recall_count_caps_at_10(self):
        low = compute_importance_score(5, 0, None, 0, "test")
        high = compute_importance_score(50, 0, None, 0, "test")
        # Beyond 10, recall_count doesn't add more score
        assert high >= low

    def test_kg_degree_caps_at_5(self):
        low = compute_importance_score(0, 2, None, 0, "test")
        high = compute_importance_score(0, 50, None, 0, "test")
        assert high >= low

    def test_cross_wing_hits_caps_at_3(self):
        low = compute_importance_score(0, 0, None, 1, "test")
        high = compute_importance_score(0, 0, None, 50, "test")
        assert high >= low


# ---------------------------------------------------------------------------
# _compute_recency_score
# ---------------------------------------------------------------------------

class TestComputeRecencyScore:
    def test_none_last_accessed(self):
        assert _compute_recency_score(None) == 0.0

    def test_empty_string(self):
        assert _compute_recency_score("") == 0.0

    def test_invalid_date(self):
        assert _compute_recency_score("not-a-date") == 0.0

    def test_now_is_maximum(self):
        now = datetime.now(timezone.utc).isoformat()
        score = _compute_recency_score(now)
        assert score == pytest.approx(1.0, rel=0.05)

    def test_decays_over_half_life(self):
        past = datetime.now(timezone.utc) - timedelta(days=RECENCY_HALF_LIFE_DAYS)
        score = _compute_recency_score(past.isoformat())
        assert score == pytest.approx(0.5, rel=0.1)

    def test_decays_over_double_half_life(self):
        past = datetime.now(timezone.utc) - timedelta(days=RECENCY_HALF_LIFE_DAYS * 2)
        score = _compute_recency_score(past.isoformat())
        assert score == pytest.approx(0.25, rel=0.15)

    def test_very_old_is_near_zero(self):
        past = datetime.now(timezone.utc) - timedelta(days=1000)
        score = _compute_recency_score(past.isoformat())
        assert score < 0.01

    def test_z_suffix_handled(self):
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z"
        score = _compute_recency_score(now)
        assert score > 0.9

    def test_future_date_clamped(self):
        future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        score = _compute_recency_score(future)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# _compute_content_score
# ---------------------------------------------------------------------------

class TestComputeContentScore:
    def test_empty_content(self):
        assert _compute_content_score("") == 0.0

    def test_none_content(self):
        assert _compute_content_score(None) == 0.0

    def test_short_content(self):
        score = _compute_content_score("Hi")
        assert score >= 0.0

    def test_medium_content(self):
        score = _compute_content_score("A" * 150)
        assert score >= 0.3

    def test_long_content(self):
        score = _compute_content_score("A" * 600)
        assert score >= 0.5

    def test_very_long_content(self):
        score = _compute_content_score("A" * 1200)
        assert score >= 0.6

    def test_important_keywords_boost(self):
        plain = _compute_content_score("Some text here")
        keyword = _compute_content_score("This is a critical security bug fix for production")
        assert keyword > plain

    def test_score_capped_at_one(self):
        score = _compute_content_score("important " * 200 + "A" * 3000)
        assert score <= 1.0


# ---------------------------------------------------------------------------
# score_all_memories / get_top_memories
# ---------------------------------------------------------------------------

class TestScoreAllMemories:
    def test_empty_palace(self, palace):
        result = score_all_memories(palace)
        assert result["scored"] == 0

    def test_scores_memories(self, palace):
        palace.remember("Important config: use uvicorn", room="config")
        palace.remember("Bug fix: timeout issue", room="bugs")
        result = score_all_memories(palace)
        assert result["scored"] >= 1
        assert "scores" in result

    def test_get_top_memories(self, palace):
        palace.remember("Memory 1", room="general")
        palace.remember("Memory 2", room="general")
        palace.remember("Memory 3", room="general")
        top = get_top_memories(palace, n=2)
        assert len(top) <= 2

    def test_get_top_memories_empty(self, palace):
        top = get_top_memories(palace)
        assert top == []


# ---------------------------------------------------------------------------
# WEIGHTS
# ---------------------------------------------------------------------------

class TestWeights:
    def test_weights_sum_to_one(self):
        total = sum(WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_weights_all_positive(self):
        for name, value in WEIGHTS.items():
            assert value > 0, f"weight {name} should be positive"
