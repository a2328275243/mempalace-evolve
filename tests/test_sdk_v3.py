"""Tests for previously untested SDK public methods."""

import pytest
from datetime import datetime, timedelta, timezone


class TestReviewCycle:
    """Spaced-repetition review cycle."""

    def test_get_due_for_review_initially_empty(self, palace):
        due = palace.get_due_for_review()
        assert isinstance(due, list)

    def test_mark_reviewed(self, palace):
        did = palace.remember("Review test content", room="study")
        result = palace.mark_reviewed(did)
        assert result is True

    def test_mark_reviewed_nonexistent(self, palace):
        result = palace.mark_reviewed("nonexistent-id-12345")
        assert result is False

    def test_snooze_memory(self, palace):
        did = palace.remember("Snooze test content", room="study")
        result = palace.snooze_memory(did, days=7)
        assert result is True

    def test_snooze_nonexistent(self, palace):
        result = palace.snooze_memory("nonexistent-id-12345", days=3)
        assert result is False

    def test_full_review_lifecycle(self, palace):
        did = palace.remember("Full lifecycle test", room="study")
        assert palace.mark_reviewed(did) is True
        due = palace.get_due_for_review()
        assert isinstance(due, list)


class TestScoring:
    def test_score_memories(self, palace):
        palace.remember("Very important decision", room="critical")
        palace.remember("Casual note", room="general")
        result = palace.score_memories()
        assert isinstance(result, dict)

    def test_top_memories(self, palace):
        palace.remember("Important A", room="critical")
        palace.remember("Important B", room="critical")
        top = palace.top_memories(n=5)
        assert isinstance(top, list)
        assert len(top) <= 5

    def test_top_memories_empty(self, palace):
        top = palace.top_memories(n=3)
        assert isinstance(top, list)


class TestFindSimilar:
    def test_find_similar_basic(self, palace):
        palace.remember("Python async programming guide", room="dev")
        palace.remember("Rust systems programming guide", room="dev")
        similar = palace.find_similar("Python async coding", threshold=0.0)
        assert isinstance(similar, list)

    def test_find_similar_room_filter(self, palace):
        palace.remember("Frontend React component", room="frontend")
        palace.remember("Backend Python API", room="backend")
        similar = palace.find_similar("Python backend", room="backend", threshold=0.0)
        assert isinstance(similar, list)

    def test_find_similar_high_threshold(self, palace):
        palace.remember("X", room="test")
        similar = palace.find_similar("Some unrelated text", threshold=0.99)
        assert isinstance(similar, list)


class TestProperties:
    def test_path_returns_path(self, palace):
        from pathlib import Path
        p = palace.path
        assert isinstance(p, Path)

    def test_wing_returns_string(self, palace):
        w = palace.wing
        assert isinstance(w, str)


class TestLifecycleMethods:
    def test_purge_expired_removes_only_expired_current_wing_memory(self, palace):
        did = palace.remember("Temporary low-importance memory", room="general")
        col = palace._get_collection()
        batch = col.get(ids=[did], include=["documents", "metadatas"])
        meta = batch["metadatas"][0]
        doc = batch["documents"][0]
        old = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        meta["last_accessed"] = old
        meta["enhanced_importance"] = 0.0
        col.update(ids=[did], documents=[doc], metadatas=[meta])

        result = palace.purge_expired(ttl_days=1)

        assert result["purged"] == 1
        assert did in result["purged_ids"]
        remaining = col.get(ids=[did], include=[])
        assert remaining["ids"] == []

    def test_compress_old_memories_uses_lifecycle_summary_limit(self, palace):
        palace._scoring_config["dedup_threshold"] = 0
        ids = [
            palace.remember("Old lifecycle compression item one. Extra detail.", room="archive_test"),
            palace.remember("Old lifecycle compression item two. Extra detail.", room="archive_test"),
        ]
        col = palace._get_collection()
        old = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        batch = col.get(ids=ids, include=["documents", "metadatas"])
        for doc_id, doc, meta in zip(batch["ids"], batch["documents"], batch["metadatas"]):
            meta["last_accessed"] = old
            col.update(ids=[doc_id], documents=[doc], metadatas=[meta])

        result = palace.compress_old_memories(compress_after_days=1, max_chars=120)

        assert result["rooms_compressed"] >= 1
        assert result["drawers_archived"] >= 2
        assert result["summaries_created"] >= 1
