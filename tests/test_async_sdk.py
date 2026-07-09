"""Tests for async_sdk.py — AsyncMemPalace async context manager and operations."""

import asyncio
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from mempalace_evolve.async_sdk import (
    AsyncMemPalace,
    async_remember,
    async_recall,
    async_forget,
    _get_pool,
)


# ---------------------------------------------------------------------------
# Fixture: mock the sync MemPalace at the instance level
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_palace():
    """Return a mocked AsyncMemPalace._get_sync() so all calls go to a mock sync."""
    mock_sync = MagicMock()
    # Set return values for all SDK methods the async wrapper uses
    mock_sync.remember.return_value = "mem-1"
    mock_sync.recall.return_value = [{"id": "1", "text": "result"}]
    mock_sync.forget.return_value = True
    mock_sync.stats.return_value = {"total": 42}
    mock_sync.export.return_value = '{"data": "exported"}'
    mock_sync.evolve.return_value = {"cycles": 1}
    mock_sync.batch_remember.return_value = {"added": 2, "skipped": 0, "ids": ["mem-1", "mem-2"]}
    mock_sync.batch_recall.return_value = {"results": [{"query": "q", "memories": []}]}
    mock_sync.batch_forget.return_value = {"requested": 2, "deleted": 2, "not_found": 0}
    mock_sync.recall_stream.return_value = iter([{"content": "streamed"}])
    # Auto-proxy methods (not explicitly defined in AsyncSDK)
    mock_sync.fuzzy_search.return_value = [{"id": "1", "content": "hit"}]
    mock_sync.recent.return_value = [{"id": "1"}, {"id": "2"}]
    mock_sync.search_by_metadata.return_value = [{"id": "3", "content": "tagged"}]
    mock_sync.query_entity.return_value = [{"subject": "X"}]
    mock_sync.invalidate_triple.return_value = True
    mock_sync.start_auto_evolve.return_value = None
    mock_sync.stop_auto_evolve.return_value = None

    with patch.object(AsyncMemPalace, "_get_sync", return_value=mock_sync):
        yield mock_sync


# ---------------------------------------------------------------------------
# AsyncMemPalace
# ---------------------------------------------------------------------------

class TestAsyncMemPalace:
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_palace):
        """Context manager creates and closes properly."""
        palace = AsyncMemPalace(palace_path="/tmp/test", wing="demo")
        assert palace._closed is False
        async with palace:
            assert palace._closed is False
        assert palace._closed is True

    @pytest.mark.asyncio
    async def test_remember(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            result = await palace.remember("test content", room="decisions")
            assert result == "mem-1"
            mock_palace.remember.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            results = await palace.recall("how to auth?", room="decisions")
            assert isinstance(results, list)
            assert results[0]["text"] == "result"
            mock_palace.recall.assert_called_once()

    @pytest.mark.asyncio
    async def test_forget(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            ok = await palace.forget("mem-id")
            assert ok is True
            mock_palace.forget.assert_called_once()

    @pytest.mark.asyncio
    async def test_stats(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            stats = await palace.stats()
            assert stats["total"] == 42
            mock_palace.stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_export(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            data = await palace.export()
            assert "exported" in data
            mock_palace.export.assert_called_once()

    @pytest.mark.asyncio
    async def test_evolve(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            result = await palace.evolve("transcript text")
            assert result["cycles"] == 1
            mock_palace.evolve.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_remember(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            result = await palace.batch_remember([{"content": "a"}, {"content": "b"}])
            assert result["added"] == 2
            assert len(result["ids"]) == 2
            mock_palace.batch_remember.assert_called_once_with(
                memories=[{"content": "a"}, {"content": "b"}],
            )

    @pytest.mark.asyncio
    async def test_batch_recall_forwards_threshold(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            result = await palace.batch_recall(
                ["q"],
                room="decisions",
                limit=2,
                threshold=0.4,
            )
            assert "results" in result
            mock_palace.batch_recall.assert_called_once_with(
                queries=["q"],
                room="decisions",
                limit=2,
                threshold=0.4,
            )

    @pytest.mark.asyncio
    async def test_recall_forwards_threshold_and_hybrid(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            await palace.recall("q", room="decisions", limit=2, threshold=0.4, hybrid=False)
            mock_palace.recall.assert_called_once_with(
                query="q",
                room="decisions",
                limit=2,
                threshold=0.4,
                hybrid=False,
            )

    @pytest.mark.asyncio
    async def test_recall_stream_returns_list(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            result = await palace.recall_stream("q")
            assert result == [{"content": "streamed"}]
            mock_palace.recall_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall_many_concurrent(self, mock_palace):
        """recall_many runs recall in parallel for multiple queries."""
        async with AsyncMemPalace(wing="w") as palace:
            results = await palace.recall_many(["q1", "q2", "q3"])
            assert len(results) == 3
            assert mock_palace.recall.call_count == 3

    @pytest.mark.asyncio
    async def test_remember_many(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            result = await palace.remember_many([{"content": "x"}])
            assert result["added"] == 2  # mock returns added=2
            mock_palace.batch_remember.assert_called_once()

    @pytest.mark.asyncio
    async def test_real_batch_methods(self, tmp_palace):
        async with AsyncMemPalace(palace_path=tmp_palace, wing="async_batch") as palace:
            stored = await palace.batch_remember([
                {"content": "Async batch target", "room": "config"},
                {"content": "Async batch target", "room": "decisions", "source": "async-other"},
            ])
            assert stored.stored == 2

            recalled = await palace.batch_recall(
                ["Async batch target"],
                room="config",
                limit=5,
                threshold=0.8,
            )
            memories = recalled.results[0]["memories"]
            assert len(memories) >= 1
            assert all(m["metadata"].get("room") == "config" for m in memories)

            deleted = await palace.batch_forget(stored.ids)
            assert deleted.deleted == 2

    @pytest.mark.asyncio
    async def test_query_entity(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            results = await palace.query_entity("Alice")
            assert len(results) == 1
            mock_palace.query_entity.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_triple(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            ok = await palace.invalidate_triple("A", "works_on", "B")
            assert ok is True
            mock_palace.invalidate_triple.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_evolve_controls(self, mock_palace):
        async with AsyncMemPalace(wing="w") as palace:
            await palace.start_auto_evolve()
            mock_palace.start_auto_evolve.assert_called_once()
            await palace.stop_auto_evolve()
            mock_palace.stop_auto_evolve.assert_called_once()

    @pytest.mark.asyncio
    async def test_closed_raises(self, mock_palace):
        """Operations after close raise RuntimeError."""
        palace = AsyncMemPalace(wing="w")
        await palace.close()
        with pytest.raises(RuntimeError):
            await palace.remember("test")

    @pytest.mark.asyncio
    async def test_double_close_is_safe(self, mock_palace):
        """close() is idempotent."""
        palace = AsyncMemPalace(wing="w")
        await palace.close()
        await palace.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_with_no_sync(self, mock_palace):
        """close() is safe when _sync_palace is None."""
        palace = AsyncMemPalace(wing="w")
        await palace.close()
        # No sync palace was created, so close just sets _closed
        assert palace._closed is True

    def test_init_defaults(self):
        """Default parameters are set correctly."""
        palace = AsyncMemPalace()
        assert palace._wing == "global"
        assert palace._auto_evolve is False
        assert palace._closed is False

    def test_custom_init(self):
        """Custom parameters are passed through."""
        palace = AsyncMemPalace(
            palace_path="/custom/path",
            wing="my-project",
            auto_evolve=True,
            evolve_interval=7200,
            max_workers=8,
        )
        assert palace._wing == "my-project"
        assert palace._auto_evolve is True
        assert palace._evolve_interval == 7200
        assert palace._max_workers == 8


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------
    # ================================================================
    # Auto-proxy tests: methods not explicitly defined in AsyncSDK
    # ================================================================

    @pytest.mark.asyncio
    async def test_auto_proxy_fuzzy_search(self, mock_palace):
        mock_palace.fuzzy_search.return_value = [{"id": "1", "content": "Redis caching"}]
        async with AsyncMemPalace(wing="w") as palace:
            results = await palace.fuzzy_search("redis", limit=5)
            assert isinstance(results, list)
            assert len(results) > 0
            mock_palace.fuzzy_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_proxy_recent(self, mock_palace):
        mock_palace.recent.return_value = [{"id": "1"}, {"id": "2"}]
        async with AsyncMemPalace(wing="w") as palace:
            results = await palace.recent(limit=10)
            assert isinstance(results, list)
            assert len(results) >= 2
            mock_palace.recent.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_proxy_search_by_metadata(self, mock_palace):
        mock_palace.search_by_metadata.return_value = [{"id": "3", "content": "tagged"}]
        async with AsyncMemPalace(wing="w") as palace:
            results = await palace.search_by_metadata({"tags": "test-tag"}, limit=10)
            assert isinstance(results, list)
            mock_palace.search_by_metadata.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_proxy_missing_method_raises(self):
        """Calling a non-existent method should raise AttributeError."""
        # Use real sync palace (not mock) to avoid MagicMock swallowing all attrs
        palace = AsyncMemPalace.__new__(AsyncMemPalace)
        palace.__init__(wing="test_missing")
        # Close it immediately so _get_sync never creates real collection
        await palace.close()
        # For a real _get_sync() scenario, non_existent raises AttributeError
        with pytest.raises(AttributeError):
            _ = getattr(palace._get_sync(), "non_existent_method")

class TestConvenienceFunctions:
    @pytest.mark.asyncio
    async def test_async_remember(self, mock_palace):
        result = await async_remember("hello", room="greetings", wing="test")
        assert result == "mem-1"

    @pytest.mark.asyncio
    async def test_async_recall(self, mock_palace):
        results = await async_recall("search term", wing="test")
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_async_forget(self, mock_palace):
        ok = await async_forget("mem-id", wing="test")
        assert ok is True


# ---------------------------------------------------------------------------
# Thread pool
# ---------------------------------------------------------------------------

class TestThreadPool:
    @pytest.mark.asyncio
    async def test_get_pool_returns_same_instance(self):
        pool1 = await _get_pool()
        pool2 = await _get_pool()
        assert pool1 is pool2
