"""Tests for core/lifecycle.py — memory decay, compression, admission, expiry."""

import math
import time
from datetime import datetime, timedelta, timezone

import pytest

from mempalace_evolve.core.lifecycle import (
    decay_score,
    touch_drawers,
    find_compress_candidates,
    compress_text_block,
    check_admission,
    migrate_legacy_drawers,
    find_ttl_expired,
    purge_expired,
    _safe_float,
    TOUCH_DEBOUNCE_SECONDS,
)


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_normal_float(self):
        assert _safe_float(3.5) == 3.5
        assert _safe_float(0) == 0.0
        assert _safe_float("2.5") == 2.5

    def test_none_returns_default(self):
        assert _safe_float(None) == 0.0
        assert _safe_float(None, default=1.0) == 1.0

    def test_invalid_returns_default(self):
        assert _safe_float("abc") == 0.0
        assert _safe_float("abc", default=0.5) == 0.5

    def test_int_conversion(self):
        assert _safe_float(42) == 42.0


# ---------------------------------------------------------------------------
# decay_score
# ---------------------------------------------------------------------------

class TestDecayScore:
    def test_recent_memory_high_score(self):
        now = datetime.now(timezone.utc)
        score = decay_score(3.0, now.isoformat(), now.isoformat(), decay_lambda=0.02)
        assert score == pytest.approx(3.0, rel=0.01)

    def test_old_memory_decays(self):
        past = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        score = decay_score(3.0, past, past, decay_lambda=0.02)
        expected = 3.0 * math.exp(-0.02 * 90)
        assert score < 3.0
        assert score == pytest.approx(expected, rel=0.01)

    def test_zero_importance(self):
        score = decay_score(0.0, datetime.now(timezone.utc).isoformat(), "", 0.02)
        assert score == 0.0

    def test_fallback_to_filed_at(self):
        past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        score = decay_score(2.0, "", past, decay_lambda=0.02)
        expected = 2.0 * math.exp(-0.02 * 30)
        assert score == pytest.approx(expected, rel=0.01)

    def test_both_empty_returns_importance(self):
        score = decay_score(2.5, "", "", 0.02)
        assert score == 2.5

    def test_invalid_date_returns_importance(self):
        score = decay_score(3.0, "not-a-date", "also-bad", 0.02)
        assert score == 3.0

    def test_none_importance(self):
        now = datetime.now(timezone.utc).isoformat()
        score = decay_score(None, now, now, 0.02)
        assert score == 0.0

    def test_custom_lambda(self):
        past = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        fast = decay_score(3.0, past, past, decay_lambda=0.05)
        slow = decay_score(3.0, past, past, decay_lambda=0.01)
        assert fast < slow

    def test_future_date_not_negative(self):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        score = decay_score(3.0, future, future, 0.02)
        assert score == pytest.approx(3.0, rel=0.01)

    def test_decay_over_one_year(self):
        past = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        score = decay_score(5.0, past, past, 0.02)
        expected = 5.0 * math.exp(-0.02 * 365)
        assert score == pytest.approx(expected, rel=0.01)
        assert score < 0.01


# ---------------------------------------------------------------------------
# compress_text_block
# ---------------------------------------------------------------------------

class TestCompressTextBlock:
    def test_single_doc_fits(self):
        docs = ["Short text."]
        result = compress_text_block(docs, max_chars=800)
        assert "Short text." in result

    def test_multiple_docs_joined(self):
        docs = ["First doc.", "Second doc."]
        result = compress_text_block(docs, max_chars=800)
        assert "First doc." in result
        assert "Second doc." in result

    def test_truncates_when_exceeds_max(self):
        long_text = "A" * 2000
        docs = [long_text]
        result = compress_text_block(docs, max_chars=100)
        assert len(result) <= 200

    def test_empty_docs(self):
        result = compress_text_block([], max_chars=800)
        assert result == ""


# ---------------------------------------------------------------------------
# Helper: get the collection matching what palace.remember() uses
# ---------------------------------------------------------------------------

def _palace_collection(palace):
    """Get the ChromaDB collection used by a MemPalace instance."""
    from mempalace_evolve.core.chroma_helper import get_collection
    # MemPalace stores chroma data in path / "palace"
    return get_collection(str(palace.path / "palace"), create=True)


# ---------------------------------------------------------------------------
# touch_drawers
# ---------------------------------------------------------------------------

class TestTouchDrawers:
    def test_empty_list_returns_zero(self, palace):
        col = _palace_collection(palace)
        result = touch_drawers(col, [])
        assert result == 0

    def test_touch_updates_last_accessed(self, palace):
        drawer_id = palace.remember("Test memory for touch", room="general")
        col = _palace_collection(palace)

        # Get original last_accessed
        batch = col.get(ids=[drawer_id], include=["metadatas"])
        assert len(batch["ids"]) > 0, "Memory should exist in collection"
        original_accessed = batch["metadatas"][0].get("last_accessed", "")

        time.sleep(0.1)
        result = touch_drawers(col, [drawer_id])
        assert result == 1

        batch = col.get(ids=[drawer_id], include=["metadatas"])
        new_accessed = batch["metadatas"][0].get("last_accessed", "")
        assert new_accessed != original_accessed

    def test_debounce_prevents_duplicate_touch(self, palace):
        drawer_id = palace.remember("Test memory for debounce", room="general")
        col = _palace_collection(palace)

        result1 = touch_drawers(col, [drawer_id])
        assert result1 == 1

        # Second touch immediately — debounce should skip it
        result2 = touch_drawers(col, [drawer_id])
        assert result2 == 0

    def test_touch_nonexistent_drawer(self, palace):
        col = _palace_collection(palace)
        result = touch_drawers(col, ["nonexistent_drawer_id"])
        assert result == 0


# ---------------------------------------------------------------------------
# find_compress_candidates
# ---------------------------------------------------------------------------

class TestFindCompressCandidates:
    def test_empty_collection(self, palace):
        col = _palace_collection(palace)
        candidates = find_compress_candidates(col, compress_after_days=60)
        assert candidates == {}

    def test_recent_memory_not_candidate(self, palace):
        palace.remember("Recent memory", room="general")
        col = _palace_collection(palace)
        candidates = find_compress_candidates(col, compress_after_days=365)
        assert candidates == {}

    def test_candidates_grouped_by_room(self, palace):
        palace.remember("Memory in decisions", room="decisions")
        palace.remember("Memory in errors", room="errors")
        col = _palace_collection(palace)
        # Use 0 days to make all memories qualify
        candidates = find_compress_candidates(col, compress_after_days=0)
        assert isinstance(candidates, dict)
        assert len(candidates) >= 1


# ---------------------------------------------------------------------------
# check_admission
# ---------------------------------------------------------------------------

class TestCheckAdmission:
    def test_under_limit(self, palace):
        palace.remember("Single memory", room="general")
        col = _palace_collection(palace)
        result = check_admission(col, wing="test", max_total=500, max_per_wing=200)
        assert result["allowed"] is True
        assert "counts" in result
        assert result["counts"]["total"] >= 1

    def test_over_total_limit(self, palace):
        col = _palace_collection(palace)
        result = check_admission(col, wing="test", max_total=0, max_per_wing=200)
        assert result["allowed"] is False
        assert "counts" in result

    def test_returns_expected_keys(self, palace):
        palace.remember("Test", room="general")
        col = _palace_collection(palace)
        result = check_admission(col, wing="test", max_total=500, max_per_wing=200)
        assert "allowed" in result
        assert "counts" in result
        assert isinstance(result["counts"], dict)


# ---------------------------------------------------------------------------
# find_ttl_expired / purge_expired
# ---------------------------------------------------------------------------

class TestTTLExpiry:
    def test_find_ttl_expired_empty(self, palace):
        col = _palace_collection(palace)
        expired = find_ttl_expired(col, ttl_days=365, min_importance=0.8)
        assert expired == []

    def test_find_ttl_expired_returns_list(self, palace):
        palace.remember("Memory for TTL test", room="general")
        col = _palace_collection(palace)
        expired = find_ttl_expired(col, ttl_days=0, min_importance=0.0)
        assert isinstance(expired, list)

    def test_purge_expired_empty(self, palace):
        col = _palace_collection(palace)
        result = purge_expired(col, [])
        assert result["purged"] == 0

    def test_high_importance_not_expired(self, palace):
        drawer_id = palace.remember("Very important memory", room="decisions")
        col = _palace_collection(palace)
        assert col is not None

        # Manually update the enhanced_importance to a high value
        batch = col.get(ids=[drawer_id], include=["documents", "metadatas"])
        assert len(batch["ids"]) > 0, "drawer_id should exist after remember"
        meta = batch["metadatas"][0]
        doc = batch["documents"][0]
        meta["enhanced_importance"] = 0.99
        col.update(ids=[drawer_id], documents=[doc], metadatas=[meta])

        # With ttl_days=0 and min_importance=0.8, high-importance memory should be protected
        expired = find_ttl_expired(col, ttl_days=0, min_importance=0.8)
        ids = [e["id"] for e in expired]
        assert drawer_id not in ids


# ---------------------------------------------------------------------------
# migrate_legacy_drawers
# ---------------------------------------------------------------------------

class TestMigrateLegacyDrawers:
    def test_migrate_empty_collection(self, palace):
        col = _palace_collection(palace)
        result = migrate_legacy_drawers(col)
        assert isinstance(result, dict)
        assert "migrated" in result
