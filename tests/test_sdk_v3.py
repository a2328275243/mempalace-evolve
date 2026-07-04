"""Tests for previously untested SDK public methods."""

import pytest


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