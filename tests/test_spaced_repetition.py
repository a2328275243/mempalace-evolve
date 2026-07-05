"""Tests for core/spaced_repetition.py — FSRS-inspired adaptive scheduler."""

import math
from datetime import datetime, timedelta, timezone

import pytest

from mempalace_evolve.core.spaced_repetition import (
    _compute_interval,
    calculate_next_review,
    get_interval_days,
    get_memories_due_for_review,
    mark_reviewed,
    snooze,
    INITIAL_INTERVAL_DAYS,
    STABILITY_FACTOR,
    MAX_INTERVAL_DAYS,
    MIN_RECALL_COUNT,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _col(palace):
    from mempalace_evolve.core.chroma_helper import get_collection
    return get_collection(str(palace.path / "palace"), create=True)


# ---------------------------------------------------------------------------
# _compute_interval
# ---------------------------------------------------------------------------

class TestComputeInterval:
    def test_zero_recall_count(self):
        assert _compute_interval(0) == INITIAL_INTERVAL_DAYS

    def test_negative_recall_count(self):
        assert _compute_interval(-1) == INITIAL_INTERVAL_DAYS

    def test_recall_count_1(self):
        interval = _compute_interval(1)
        expected = INITIAL_INTERVAL_DAYS * (STABILITY_FACTOR ** 0)
        assert interval == pytest.approx(expected)

    def test_recall_count_2(self):
        interval = _compute_interval(2)
        expected = INITIAL_INTERVAL_DAYS * STABILITY_FACTOR
        assert interval == pytest.approx(expected)

    def test_recall_count_5(self):
        interval = _compute_interval(5)
        expected = INITIAL_INTERVAL_DAYS * (STABILITY_FACTOR ** 4)
        assert interval == pytest.approx(expected)

    def test_recall_count_10(self):
        interval = _compute_interval(10)
        expected = INITIAL_INTERVAL_DAYS * (STABILITY_FACTOR ** 9)
        assert interval > 30

    def test_interval_capped_at_max(self):
        interval = _compute_interval(100)
        assert interval == MAX_INTERVAL_DAYS

    def test_interval_monotonically_increasing(self):
        prev = _compute_interval(1)
        for i in range(2, 10):
            curr = _compute_interval(i)
            assert curr >= prev
            prev = curr


# ---------------------------------------------------------------------------
# calculate_next_review
# ---------------------------------------------------------------------------

class TestCalculateNextReview:
    def test_returns_iso_format(self):
        now = datetime.now(timezone.utc).isoformat()
        result = calculate_next_review(now, recall_count=2)
        assert isinstance(result, str)
        datetime.fromisoformat(result)

    def test_no_last_reviewed(self):
        result = calculate_next_review(None, recall_count=3)
        assert isinstance(result, str)
        dt = datetime.fromisoformat(result)
        assert dt > datetime.now(timezone.utc) - timedelta(minutes=5)

    def test_invalid_date(self):
        result = calculate_next_review("not-a-date", recall_count=2)
        assert isinstance(result, str)
        datetime.fromisoformat(result)

    def test_recall_count_affects_interval(self):
        near = calculate_next_review(None, recall_count=1)
        far = calculate_next_review(None, recall_count=10)
        near_dt = datetime.fromisoformat(near)
        far_dt = datetime.fromisoformat(far)
        assert far_dt > near_dt

    def test_z_suffix_handled(self):
        past = "2024-01-01T00:00:00Z"
        result = calculate_next_review(past, recall_count=2)
        dt = datetime.fromisoformat(result)
        assert dt > datetime.fromisoformat(past.replace("Z", "+00:00"))


# ---------------------------------------------------------------------------
# get_interval_days
# ---------------------------------------------------------------------------

class TestGetIntervalDays:
    def test_valid_interval_string(self):
        assert get_interval_days("7.0") == 7.0

    def test_none_uses_adaptive(self):
        result = get_interval_days(None, recall_count=2)
        expected = _compute_interval(2)
        assert result == pytest.approx(expected)

    def test_invalid_interval_falls_back(self):
        result = get_interval_days("bad", recall_count=3)
        expected = _compute_interval(3)
        assert result == pytest.approx(expected)

    def test_empty_string_falls_back(self):
        result = get_interval_days("", recall_count=1)
        expected = _compute_interval(1)
        assert result == pytest.approx(expected)

    def test_capped_at_max(self):
        assert get_interval_days("999.0") == MAX_INTERVAL_DAYS

    def test_zero_interval(self):
        assert get_interval_days("0.0") == 0.0


# ---------------------------------------------------------------------------
# get_memories_due_for_review
# ---------------------------------------------------------------------------

class TestGetMemoriesDueForReview:
    def test_empty_collection(self, palace):
        col = _col(palace)
        due = get_memories_due_for_review(col, wing="test")
        assert due == []

    def test_memories_without_min_recall_count_excluded(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("New memory with low recall", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["recall_count"] = 0
        meta["wing"] = "test"
        col.update(ids=[drawer_id], metadatas=[meta])

        due = get_memories_due_for_review(col, wing="test")
        assert len([m for m in due if m["id"] == drawer_id]) == 0

    def test_memory_without_next_review_included(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Memory without next_review", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["recall_count"] = 5
        meta["wing"] = "test"
        if "next_review" in meta:
            del meta["next_review"]
        col.update(ids=[drawer_id], metadatas=[meta])

        due = get_memories_due_for_review(col, wing="test")
        due_ids = [m["id"] for m in due]
        assert drawer_id in due_ids

    def test_future_review_not_due(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Future review memory", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["recall_count"] = 5
        meta["wing"] = "test"
        future = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        meta["next_review"] = future
        col.update(ids=[drawer_id], metadatas=[meta])

        due = get_memories_due_for_review(col, wing="test")
        due_ids = [m["id"] for m in due]
        assert drawer_id not in due_ids

    def test_past_review_is_due(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Overdue review", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["recall_count"] = 5
        meta["wing"] = "test"
        past = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        meta["next_review"] = past
        col.update(ids=[drawer_id], metadatas=[meta])

        due = get_memories_due_for_review(col, wing="test")
        due_ids = [m["id"] for m in due]
        assert drawer_id in due_ids

    def test_as_of_param(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Future check memory", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["recall_count"] = 5
        meta["wing"] = "test"
        far_future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        meta["next_review"] = far_future
        col.update(ids=[drawer_id], metadatas=[meta])

        future_as_of = datetime.now(timezone.utc) + timedelta(days=400)
        due = get_memories_due_for_review(col, wing="test", as_of=future_as_of)
        due_ids = [m["id"] for m in due]
        assert drawer_id in due_ids

    def test_returns_expected_keys(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Keys test", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["recall_count"] = 5
        meta["wing"] = "test"
        # Remove next_review if present so the memory shows up as due
        meta.pop("next_review", None)
        col.update(ids=[drawer_id], metadatas=[meta])

        due = get_memories_due_for_review(col, wing="test")
        match = [m for m in due if m["id"] == drawer_id]
        assert len(match) == 1
        m = match[0]
        assert "id" in m
        assert "content" in m
        assert "room" in m
        assert "interval_days" in m
        assert "last_reviewed" in m
        assert "recall_count" in m

    def test_invalid_next_review_skipped(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Invalid date test", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["recall_count"] = 5
        meta["wing"] = "test"
        meta["next_review"] = "garbage-date-not-iso"
        col.update(ids=[drawer_id], metadatas=[meta])

        due = get_memories_due_for_review(col, wing="test")
        due_ids = [m["id"] for m in due]
        assert drawer_id not in due_ids


# ---------------------------------------------------------------------------
# mark_reviewed
# ---------------------------------------------------------------------------

class TestMarkReviewed:
    def test_nonexistent_drawer(self, palace):
        col = _col(palace)
        assert mark_reviewed(col, "nonexistent-id", recall_count=2) is False

    def test_marks_reviewed_and_updates_metadata(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Test mark reviewed", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["recall_count"] = 3
        meta["wing"] = "test"
        col.update(ids=[drawer_id], metadatas=[meta])

        assert mark_reviewed(col, drawer_id, recall_count=3) is True

        updated = col.get(ids=[drawer_id], include=["metadatas"])
        new_meta = updated["metadatas"][0]
        assert new_meta.get("recall_count") is not None

    def test_increments_review_count(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Review count test", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["recall_count"] = 2
        meta["review_count"] = 5
        meta["wing"] = "test"
        col.update(ids=[drawer_id], metadatas=[meta])

        mark_reviewed(col, drawer_id, recall_count=2)

        updated = col.get(ids=[drawer_id], include=["metadatas"])
        new_meta = updated["metadatas"][0]
        assert new_meta.get("review_count", 0) >= 6

    def test_sets_next_review_future(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Next review future test", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["recall_count"] = 2
        meta["wing"] = "test"
        col.update(ids=[drawer_id], metadatas=[meta])

        mark_reviewed(col, drawer_id, recall_count=2)

        updated = col.get(ids=[drawer_id], include=["metadatas"])
        new_meta = updated["metadatas"][0]
        next_review = new_meta.get("next_review")
        assert next_review is not None
        review_dt = datetime.fromisoformat(next_review)
        assert review_dt > datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# snooze
# ---------------------------------------------------------------------------

class TestSnooze:
    def test_nonexistent_drawer(self, palace):
        col = _col(palace)
        assert snooze(col, "nonexistent-id") is False

    def test_snooze_postpones_review(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Snooze test", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["next_review"] = datetime.now(timezone.utc).isoformat()
        meta["wing"] = "test"
        col.update(ids=[drawer_id], metadatas=[meta])

        assert snooze(col, drawer_id, days=7) is True

        updated = col.get(ids=[drawer_id], include=["metadatas"])
        new_meta = updated["metadatas"][0]
        new_review = datetime.fromisoformat(new_meta["next_review"])
        expected_min = datetime.now(timezone.utc) + timedelta(days=6)
        assert new_review > expected_min

    def test_snooze_default_days(self, palace):
        col = _col(palace)
        drawer_id = palace.remember("Default snooze test", room="general")
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        meta = batch["metadatas"][0]
        meta["wing"] = "test"
        col.update(ids=[drawer_id], metadatas=[meta])

        assert snooze(col, drawer_id) is True


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_initial_interval_is_positive(self):
        assert INITIAL_INTERVAL_DAYS > 0

    def test_stability_factor_greater_than_one(self):
        assert STABILITY_FACTOR > 1.0

    def test_max_interval_is_reasonable(self):
        assert MAX_INTERVAL_DAYS > 0
        assert MAX_INTERVAL_DAYS <= 3650  # 10 years

    def test_min_recall_count(self):
        assert MIN_RECALL_COUNT >= 0
