"""Async SDK for mempalace-evolve.

Provides an async-first interface to MemPalace with connection pooling,
concurrent operations, and proper resource lifecycle management.

Usage:
    from mempalace_evolve.async_sdk import AsyncMemPalace

    async with AsyncMemPalace("./.mempalace", wing="demo") as palace:
        await palace.remember("JWT is used for auth", room="decisions")
        results = await palace.recall("how does auth work?")
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

logger = logging.getLogger("mempalace_evolve.async")

# Shared thread pool for all async palace instances (lazy init)
_pool: ThreadPoolExecutor | None = None
_pool_lock = asyncio.Lock()


async def _get_pool(max_workers: int = 4) -> ThreadPoolExecutor:
    """Get or create the shared thread pool for blocking I/O."""
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                _pool = ThreadPoolExecutor(
                    max_workers=max_workers,
                    thread_name_prefix="mempalace-io",
                )
    return _pool


import asyncio
import functools
import logging

logger = logging.getLogger(__name__)


def retry_on_error(max_retries: int = 3, base_delay: float = 0.5):
    """Decorator: retry async method on transient errors (StorageError).

    Exponential backoff: delay * 2**retry_count.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            from mempalace_evolve.exceptions import StorageError

            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(self, *args, **kwargs)
                except StorageError as e:
                    last_exc = e
                    if attempt < max_retries:
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            "Retry %d/%d for %s after %.1fs: %s",
                            attempt + 1,
                            max_retries,
                            func.__name__,
                            delay,
                            e,
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise
            raise last_exc

        return wrapper

    return decorator



class AsyncMemPalace:
    """Async wrapper around MemPalace with connection pooling.

    All blocking operations (ChromaDB, SQLite, file I/O) are delegated to
    a shared thread pool so they don't block the event loop.

    Supports both context-manager and manual lifecycle patterns:

        # Context manager (recommended)
        async with AsyncMemPalace("./.mempalace") as palace:
            results = await palace.recall("query")

        # Manual
        palace = AsyncMemPalace("./.mempalace")
        try:
            results = await palace.recall("query")
        finally:
            await palace.close()
    """

    def __init__(
        self,
        palace_path: str | Path | None = None,
        wing: str = "global",
        auto_evolve: bool = False,
        evolve_interval: int = 3600,
        scoring_config: dict[str, Any] | None = None,
        llm_enabled: bool | None = None,
        max_workers: int = 4,
    ):
        """Initialize an async MemPalace instance.

        Args:
            palace_path: Path to the palace directory. Defaults to ~/.mempalace
            wing: Wing/project name for scoping memories.
            auto_evolve: If True, run evolve() automatically in background.
            evolve_interval: Seconds between auto-evolve cycles.
            scoring_config: Per-room scoring rules.
            llm_enabled: Enable LLM-backed evolution.
            max_workers: Thread pool size for blocking I/O operations.
        """
        self._path = palace_path
        self._wing = wing
        self._auto_evolve = auto_evolve
        self._evolve_interval = evolve_interval
        self._scoring_config = scoring_config
        self._max_workers = max_workers
        self._sync_palace = None
        self._closed = False

    def _get_sync(self) -> "MemPalace":
        """Lazy-init the underlying sync MemPalace."""
        if self._sync_palace is None:
            from mempalace_evolve.sdk import MemPalace
            self._sync_palace = MemPalace(
                palace_path=self._path,
                wing=self._wing,
                auto_evolve=self._auto_evolve,
                evolve_interval=self._evolve_interval,
                scoring_config=self._scoring_config,

            )
        return self._sync_palace

    def __getattr__(self, name: str) -> Any:
        """Dynamically expose any sync SDK method as an async call.

        Unrecognized attribute names are forwarded to the underlying sync palace
        via the thread pool. This ensures all future sync-only methods are
        automatically available without manual wrapping.

        Args:
            name: Method name to proxy.

        Returns:
            An async callable that delegates to the sync SDK's method.

        Raises:
            AttributeError: If the sync palace has no such attribute.
        """
        # Skip private lookups from async def names to avoid recursion
        if name.startswith("_") and not name.startswith("__"):
            raise AttributeError(name)

        sync_palace = self._get_sync()
        sync_method = getattr(sync_palace, name, None)
        if sync_method is None or not callable(sync_method):
            raise AttributeError(
                f"AsyncMemPalace has no attribute {name!r} "
                f"(and sync palace has no callable {name!r} either)"
            )

        async def _proxy(*a, **kw):
            return await self._run(name, *a, **kw)

        # Cache the proxy so subsequent lookups bypass __getattr__
        setattr(self, name, _proxy)
        return _proxy

    async def _run(self, method_name: str, *args, **kwargs) -> Any:
        """Offload a sync method call to the shared thread pool."""
        if self._closed:
            raise RuntimeError("AsyncMemPalace is closed")
        palace = self._get_sync()
        method = getattr(palace, method_name)
        return await asyncio.to_thread(method, *args, **kwargs)

    # ------------------------------------------------------------------
    # Core memory operations (async wrappers)
    # ------------------------------------------------------------------

    @retry_on_error()
    async def remember(
        self,
        content: str,
        room: str = "general",
        *,
        memory_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        source: str = "",
    ) -> str:
        """Store a memory asynchronously."""
        return await self._run(
            "remember",
            content=content,
            room=room,
            memory_type=memory_type,
            metadata=metadata,
            source=source,
        )

    @retry_on_error()
    async def recall(
        self,
        query: str,
        *,
        limit: int = 5,
        room: str | None = None,
        threshold: float = 0.8,
        hybrid: bool = True,
    ) -> list[dict]:
        """Search memories semantically."""
        return await self._run(
            "recall",
            query=query,
            limit=limit,
            room=room,
            threshold=threshold,
            hybrid=hybrid,
        )

    @retry_on_error()
    async def forget(self, memory_id: str) -> bool:
        """Remove a memory by ID."""
        return await self._run("forget", memory_id)

    @retry_on_error()
    async def batch_remember(
        self,
        memories: list[dict[str, str]],
        room: str = "general",
    ) -> list[str]:
        """Store multiple memories in a single batch operation."""
        return await self._run("batch_remember", memories=memories, room=room)

    @retry_on_error()
    async def batch_forget(
        self,
        memory_ids: list[str],
    ) -> dict[str, bool]:
        """Remove multiple memories by ID."""
        return await self._run("batch_forget", memory_ids=memory_ids)

    # ------------------------------------------------------------------
    # Knowledge graph operations
    # ------------------------------------------------------------------

    async def add_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        valid_from: str | None = None,
        valid_to: str | None = None,
        confidence: float = 1.0,
    ) -> str | None:
        """Add a knowledge graph triple."""
        return await self._run(
            "add_triple",
            subject=subject, predicate=predicate, obj=obj,
            valid_from=valid_from, valid_to=valid_to, confidence=confidence,
        )

    @retry_on_error()
    async def query_entity(
        self,
        entity: str,
        as_of: str | None = None,
        direction: str = "outgoing",
    ) -> list[dict]:
        """Query the knowledge graph for an entity."""
        return await self._run(
            "query_entity", entity=entity,
            as_of=as_of, direction=direction,
        )

    async def invalidate_triple(
        self,
        subject: str,
        predicate: str,
        obj: str,
        ended: str | None = None,
    ) -> bool:
        """Invalidate a knowledge graph triple."""
        return await self._run(
            "invalidate_triple",
            subject=subject, predicate=predicate, obj=obj, ended=ended,
        )

    # ------------------------------------------------------------------
    # Evolution operations
    # ------------------------------------------------------------------

    async def evolve(self, transcript: str = "") -> dict[str, Any]:
        """Run an evolution cycle asynchronously."""
        return await self._run("evolve", transcript=transcript)

    async def start_auto_evolve(self) -> None:
        """Start background auto-evolution."""
        await self._run("start_auto_evolve")

    async def stop_auto_evolve(self) -> None:
        """Stop background auto-evolution."""
        await self._run("stop_auto_evolve")

    # ------------------------------------------------------------------
    # Utility operations
    # ------------------------------------------------------------------

    async def stats(self) -> dict[str, Any]:
        """Get palace statistics (memory count, graph size, etc.)."""
        return await self._run("stats")

    async def export(self, format: str = "json") -> str:
        """Export the entire palace to JSON or Markdown."""
        return await self._run("export", format=format)

    # ------------------------------------------------------------------
    # Concurrent operations (multiple calls in parallel)
    # ------------------------------------------------------------------

    async def recall_many(
        self,
        queries: list[str],
        room: str | None = None,
        limit: int = 10,
    ) -> list[list[dict]]:
        """Run multiple recall queries concurrently.

        This is the most common batch operation — searching for
        memories across multiple query vectors simultaneously.
        """
        tasks = [
            self.recall(q, room=room, limit=limit)
            for q in queries
        ]
        return await asyncio.gather(*tasks)

    async def remember_many(
        self,
        items: list[dict[str, Any]],
    ) -> list[str | None]:
        """Store multiple items concurrently (thin wrapper over batch)."""
        return await self.batch_remember(items)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Release resources. Safe to call multiple times."""
        if self._closed:
            return
        self._closed = True
        if self._sync_palace is not None:
            await asyncio.to_thread(self._sync_palace.close)
            self._sync_palace = None

    async def __aenter__(self) -> "AsyncMemPalace":
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    def __del__(self) -> None:
        """Best-effort cleanup."""
        if not self._closed and self._sync_palace is not None:
            try:
                self._sync_palace.close()
            except OSError:
                pass


# ------------------------------------------------------------------
# Module-level convenience functions
# ------------------------------------------------------------------


async def async_remember(
    content: str,
    room: str = "general",
    palace_path: str | Path | None = None,
    wing: str = "global",
    **kwargs,
) -> str | None:
    """One-shot async memory store."""
    async with AsyncMemPalace(palace_path, wing=wing) as palace:
        return await palace.remember(content, room=room, **kwargs)


async def async_recall(
    query: str,
    room: str | None = None,
    limit: int = 10,
    palace_path: str | Path | None = None,
    wing: str = "global",
) -> list[dict]:
    """One-shot async memory search."""
    async with AsyncMemPalace(palace_path, wing=wing) as palace:
        return await palace.recall(query, room=room, limit=limit)


async def async_forget(
    memory_id: str,
    palace_path: str | Path | None = None,
    wing: str = "global",
) -> bool:
    """One-shot async memory removal."""
    async with AsyncMemPalace(palace_path, wing=wing) as palace:
        return await palace.forget(memory_id)
