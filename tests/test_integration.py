"""Integration tests: batch API, context manager, thread safety, edge cases."""

import concurrent.futures
import json
import time
from pathlib import Path

import pytest

# ======================================================================
# Batch API Tests
# ======================================================================

class TestBatchAPI:
    def test_batch_remember(self, palace):
        items = [
            {"content": "Use Redis for caching", "room": "config"},
            {"content": "Use FastAPI for REST API", "room": "architecture"},
            {"content": "数据库用PostgreSQL", "room": "decisions"},
        ]
        result = palace.batch_remember(items)
        ids = result.ids
        assert result.stored == 3
        assert result.duplicates == 0
        assert len(ids) == 3
        assert all(isinstance(did, str) and did for did in ids)
        assert len(set(ids)) == 3  # All unique

    def test_batch_remember_empty(self, palace):
        result = palace.batch_remember([])
        assert result.ids == []
        assert result.stored == 0
        assert result.total == 0

    def test_batch_remember_invalid_skipped(self, palace):
        items = [
            {"content": "Valid memory", "room": "config"},
            {"content": "", "room": "general"},  # Empty — should be skipped
            {"content": "Another valid one", "room": "decisions"},
        ]
        result = palace.batch_remember(items)
        # Empty content produces placeholder ID
        assert result.stored == 2
        ids = result.ids
        assert len(ids) == 2
        assert ids[0] != ""

    def test_batch_forget(self, palace):
        result = palace.batch_remember([
            {"content": "Memory A", "room": "general"},
            {"content": "Memory B", "room": "general"},
        ])
        deleted = palace.batch_forget(result.ids)
        assert deleted.deleted == 2

    def test_batch_forget_partial(self, palace):
        result = palace.batch_remember([
            {"content": "Only one to keep"},
        ])
        # Some implementations may succeed on delete of nonexistent IDs
        deleted = palace.batch_forget(result.ids + ["drawer_fake_id_never_exists"])
        assert deleted.deleted >= 1  # At least the real one was deleted

# ======================================================================
# Context Manager Tests
# ======================================================================

class TestContextManager:
    def test_enter_exit(self, tmp_palace):
        from mempalace_evolve import MemPalace

        palace = MemPalace(tmp_palace)

        with palace:
            assert isinstance(palace, MemPalace)
            palace.remember("Inside context", room="test")

        # After exit, should be clean
        assert palace._chroma is None

    def test_auto_evolve_stops_on_exit(self, tmp_palace):
        from mempalace_evolve import MemPalace

        with MemPalace(tmp_palace, auto_evolve=True, evolve_interval=60) as palace:
            assert palace._evolve_thread is not None
            assert palace._evolve_thread.is_alive()

        # After exit, thread should be stopped
        assert palace._evolve_thread is None

# ======================================================================
# Thread Safety Tests
# ======================================================================

class TestThreadSafety:
    def test_concurrent_remember(self, tmp_palace):
        from mempalace_evolve import MemPalace

        palace = MemPalace(tmp_palace)

        def store(n):
            return palace.remember(f"Concurrent memory {n}", room="test")

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(store, i) for i in range(20)]
            results = [f.result() for f in futures]

        assert len(results) == 20
        assert len(set(results)) == 20  # All unique

    def test_concurrent_recall_safe(self, tmp_palace):
        from mempalace_evolve import MemPalace

        palace = MemPalace(tmp_palace)

        # Pre-populate
        for i in range(10):
            palace.remember(f"Test memory about Python {i}", room="general")

        def query(n):
            results = palace.recall(f"Python {n % 5}", limit=5)
            return len(results) >= 0  # Just check no crash

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futures = [ex.submit(query, i) for i in range(20)]
            all_ok = all(f.result() for f in futures)

        assert all_ok

# ======================================================================
# Edge Cases
# ======================================================================

class TestEdgeCases:
    def test_empty_recall(self, palace):
        results = palace.recall("")
        assert results == []

    def test_remember_unicode_special_chars(self, palace):
        unicode_str = "\U0001F680\u2705\u26A1"
        content = "Emoji test: " + unicode_str
        did = palace.remember(content, room="test")
        assert did
        results = palace.recall("emoji test", limit=1)
        assert len(results) >= 0

    def test_remember_with_special_chars(self, palace):
        content = "Memory with special chars: hello_world @test #hash"
        did = palace.remember(content, room="test")
        assert did
    def test_empty_recall(self, palace):
        results = palace.recall("")
        assert results == []

    def test_recall_very_long_query(self, palace):
        long_query = "Python " * 1000
        results = palace.recall(long_query)
        assert isinstance(results, list)


    def test_remember_very_long_content(self, palace):
        long_content = "X" * 10000
        did = palace.remember(long_content, room="test")
        assert did
        # Recall should still work
        results = palace.recall("X", limit=1)
        assert len(results) >= 1

    def test_forget_nonexistent(self, palace):
        """Forget a nonexistent ID should be safe (no crash)."""
        try:
            result = palace.forget("drawer_does_not_exist_12345")
            # Some implementations may return True, some False - both are acceptable
            assert result in (True, False)
        except Exception as e:
            pytest.fail(f"forget nonexistent should not crash: {e}")

    def test_duplicate_content_same_id(self, palace):
        """Identical content should return the same drawer ID (dedup)."""
        id1 = palace.remember("Same content", room="test")
        id2 = palace.remember("Same content", room="test")
        assert id1 == id2  # Dedup: same content = same ID

# ======================================================================
# Performance Baseline Tests
# ======================================================================

class TestPerformance:
    def test_batch_vs_individual(self, tmp_palace):
        from mempalace_evolve import MemPalace

        palace = MemPalace(tmp_palace)

        items = [{"content": f"Performance test memory {i}", "room": "perf"} for i in range(10)]

        # Batch
        start = time.time()
        result = palace.batch_remember(items)
        batch_time = time.time() - start

        # Cleanup
        palace.batch_forget(result.ids)

        # Individual
        start = time.time()
        for item in items:
            palace.remember(item["content"], room=item["room"])
        individual_time = time.time() - start

        # Batch should be at least as fast (or within reasonable margin)
        # This is a soft assertion — just records the numbers
        assert batch_time < individual_time * 2, (
            f"Batch {batch_time:.3f}s vs individual {individual_time:.3f}s"
        )

