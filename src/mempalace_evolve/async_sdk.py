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
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from mempalace_evolve.models import BatchRememberResult, BatchForgetResult, BatchRecallResult

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
                        delay = base_delay * (2 ** attempt)
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
        max_workers: int = 4,
        **kwargs,
    ):
        """Initialize an async MemPalace instance.

        Args:
            palace_path: Path to the palace directory. Defaults to ./.mempalace
            wing: Wing/project name for scoping memories.
            auto_evolve: If True, run evolve() automatically in background.
            evolve_interval: Seconds between auto-evolve cycles.
            max_workers: Thread pool size for blocking I/O operations.
            **kwargs: Additional kwargs forwarded to MemPalace.
        """
        self._path = palace_path
        self._wing = wing
        self._auto_evolve = auto_evolve
        self._evolve_interval = evolve_interval
        self._kwargs = kwargs
        self._max_workers = max_workers
        self._sync_palace = None
        self._closed = False

    def _get_sync(self):
        """Lazy-init the underlying sync MemPalace."""
        if self._sync_palace is None:
            from mempalace_evolve.sdk import MemPalace

            self._sync_palace = MemPalace(
                palace_path=self._path,
                wing=self._wing,
                auto_evolve=self._auto_evolve,
                evolve_interval=self._evolve_interval,
                **self._kwargs,
            )
        return self._sync_palace

    def __getattr__(self, name: str) -> Any:
        """Fallback: try to expose any missing attribute from sync palace."""
        if name.startswith("_"):
            raise AttributeError(name)
        sync = self._get_sync()
        if hasattr(sync, name):
            attr = getattr(sync, name)
            if callable(attr):
                logger.warning(
                    "Calling sync method %r directly. Use async wrapper instead.", name
                )
                return attr
            return attr
        raise AttributeError(
            f"{type(self).__name__!r} has no attribute {name!r}"
        )

    async def _run(self, name: str, *args, **kwargs):
        """Execute a sync method in the thread pool."""
        if self._closed:
            raise RuntimeError("Palace is closed")
        func = getattr(self._get_sync(), name)
        return await asyncio.to_thread(func, *args, **kwargs)

    # ------------------------------------------------------------------
    # Core memory operations
    # ------------------------------------------------------------------

    async def remember(
        self, content: str, room: str = "general", **kwargs
    ) -> str | None:
        """Store a memory asynchronously."""
        return await self._run("remember", content=content, room=room, **kwargs)

    async def forget(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        return await self._run("forget", memory_id=memory_id)

    # ------------------------------------------------------------------
    # Search and retrieval
    # ------------------------------------------------------------------

    async def recall(
        self, query: str, room: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Search memories: current wing + global procedural."""
        return await self._run("recall", query=query, room=room, limit=limit)

    async def recall_stream(
        self, query: str, room: str | None = None, limit: int = 10
    ) -> list[dict]:
        """Stream recall results (returns list; use iter_all for true streaming)."""
        return await self._run("recall", query=query, room=room, limit=limit)

    async def search(
        self,
        query: str | None = None,
        *,
        limit: int = 10,
        mode: str = "hybrid",
        room: str | None = None,
        threshold: float = 0.7,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        time_from: float | None = None,
        time_to: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
        expand_kg: bool = False,
    ) -> list[dict[str, Any]]:
        """Unified async search router (hybrid / semantic / metadata)."""
        return await self._run(
            "search", query=query, limit=limit, mode=mode, room=room,
            threshold=threshold, memory_types=memory_types, tags=tags,
            time_from=time_from, time_to=time_to,
            metadata_filter=metadata_filter, expand_kg=expand_kg,
        )

    async def hybrid_search(
        self,
        query: str,
        limit: int = 10,
        room: str | None = None,
        threshold: float = 0.7,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        time_from: float | None = None,
        time_to: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
        expand_kg: bool = False,
    ) -> list[dict[str, Any]]:
        """Multi-faceted search: vector search + metadata + KG expansion."""
        return await self._run(
            "hybrid_search", query=query, limit=limit, room=room,
            threshold=threshold, memory_types=memory_types, tags=tags,
            time_from=time_from, time_to=time_to,
            metadata_filter=metadata_filter, expand_kg=expand_kg,
        )

    async def filter_by_metadata(
        self,
        limit: int = 10,
        room: str | None = None,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        time_from: float | None = None,
        time_to: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Pure metadata filter search (no semantic similarity)."""
        return await self._run(
            "filter_by_metadata", limit=limit, room=room,
            memory_types=memory_types, tags=tags,
            time_from=time_from, time_to=time_to,
            metadata_filter=metadata_filter,
        )

    async def search_by_metadata(
        self, filter: dict[str, Any], limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search memories by exact metadata field matching."""
        return await self._run("search_by_metadata", filter=filter, limit=limit)

    async def find_similar(
        self, content: str, room: str | None = None, threshold: float = 0.85,
    ) -> list[dict]:
        """Find similar memories to the given content."""
        return await self._run(
            "find_similar", content=content, room=room, threshold=threshold,
        )

    async def fuzzy_search(
        self,
        query: str,
        limit: int = 10,
        room: str | None = None,
        threshold: float = 0.7,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fuzzy hybrid search: semantic vector + metadata filtering."""
        return await self._run(
            "fuzzy_search", query=query, limit=limit, room=room,
            threshold=threshold, memory_types=memory_types, tags=tags,
        )

    async def recent(
        self, limit: int = 10, room: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve the most recently stored memories."""
        return await self._run("recent", limit=limit, room=room)

    async def context_for(self, query: str) -> str:
        """Get relevant context for a new query (for prompt injection)."""
        return await self._run("context_for", query=query)

    # ------------------------------------------------------------------
    # Spaced repetition
    # ------------------------------------------------------------------

    async def get_due_for_review(self) -> list[dict]:
        """Get memories due for spaced repetition review."""
        return await self._run("get_due_for_review")

    async def mark_reviewed(self, drawer_id: str) -> bool:
        """Mark a memory as reviewed."""
        return await self._run("mark_reviewed", drawer_id=drawer_id)

    async def snooze_memory(self, drawer_id: str, days: int = 7) -> bool:
        """Snooze a memory for N days."""
        return await self._run("snooze_memory", drawer_id=drawer_id, days=days)

    # ------------------------------------------------------------------
    # Importance scoring
    # ------------------------------------------------------------------

    async def score_memories(self) -> list[dict]:
        """Score all memories by importance."""
        return await self._run("score_memories")

    async def top_memories(self, n: int = 10) -> list[dict]:
        """Get top N most important memories."""
        return await self._run("top_memories", n=n)

    # ------------------------------------------------------------------
    # Conversation digestion
    # ------------------------------------------------------------------

    async def digest(self, conversation: str) -> list[dict]:
        """Auto-extract and store knowledge from a conversation."""
        return await self._run("digest", conversation=conversation)

    # ------------------------------------------------------------------
    # Import / export
    # ------------------------------------------------------------------

    async def import_memories(self, source: str | list[dict[str, Any]]) -> int:
        """Import memories from JSON file or list of dicts."""
        return await self._run("import_memories", source=source)

    # ------------------------------------------------------------------
    # Batch operations
    # ------------------------------------------------------------------

    async def batch_remember(
        self, memories: list[dict[str, Any]], room: str = "general",
    ) -> BatchRememberResult:
        """Store multiple memories in a single batch operation."""
        return await self._run("batch_remember", memories=memories, room=room)

    async def batch_forget(self, memory_ids: list[str]) -> BatchForgetResult:
        """Delete multiple memories in a single batch operation."""
        return await self._run("batch_forget", drawer_ids=memory_ids)

    async def batch_recall(
        self, queries: list[str], room: str | None = None, limit: int = 10,
    ) -> BatchRecallResult:
        """Bulk semantic recall: run multiple queries in a single batch."""
        return await self._run("batch_recall", queries=queries, room=room, limit=limit)

    async def bulk_remember_typed(self, memories: list[dict[str, Any]]) -> list[str | None]:
        """Typed alias for batch_remember with Pydantic validation."""
        return await self._run("bulk_remember_typed", memories=memories)

    # ------------------------------------------------------------------
    # Iteration / cursor
    # ------------------------------------------------------------------

    async def iter_all(self, batch_size: int = 100):
        """Lazy async iterator over all memories, yielding batches."""
        sync = self._get_sync()
        for batch in sync.iter_all(batch_size=batch_size):
            yield batch
            await asyncio.sleep(0)

    async def iter_all_items(self):
        """Flat async iterator yielding individual memory dicts."""
        sync = self._get_sync()
        for item in sync.iter_all_items():
            yield item
            await asyncio.sleep(0)

    # ------------------------------------------------------------------
    # Knowledge graph operations
    # ------------------------------------------------------------------

    async def add_fact(
        self, subject: str, predicate: str, obj: str,
    ) -> str | None:
        """Add a triple to the knowledge graph."""
        return await self._run("add_fact", subject=subject, predicate=predicate, obj=obj)

    async def import_triples(self, triples: list[dict[str, Any]]) -> int:
        """Import multiple triples in batch."""
        return await self._run("import_triples", triples=triples)

    async def query_entity(
        self, entity: str, as_of: str | None = None, direction: str = "outgoing",
    ) -> list[dict]:
        """Query the knowledge graph for an entity."""
        return await self._run("query_entity", entity=entity, as_of=as_of, direction=direction)

    async def query_entity_v2(self, entity: str, as_of: str | None = None) -> dict[str, Any]:
        """Query KG returning structured result with incoming/outgoing."""
        return await self._run("query_entity_v2", entity=entity, as_of=as_of)

    async def query_path(
        self, start_entity: str, end_entity: str, max_depth: int = 5,
    ) -> list[dict]:
        """Find shortest path between two entities in the knowledge graph."""
        return await self._run(
            "query_path", start_entity=start_entity, end_entity=end_entity, max_depth=max_depth,
        )

    async def find_entity_by_fuzzy(self, name: str, threshold: float = 0.8) -> list[dict]:
        """Fuzzy-match entity names for 'did you mean?' scenarios."""
        return await self._run("find_entity_by_fuzzy", name=name, threshold=threshold)

    async def graph_traverse(
        self, start_entity: str, max_depth: int = 3, direction: str = "both",
    ) -> dict[str, Any]:
        """Traverse the knowledge graph from a starting entity using BFS."""
        return await self._run(
            "graph_traverse", start_entity=start_entity, max_depth=max_depth, direction=direction,
        )

    async def kg_stats(self) -> dict[str, Any]:
        """Return knowledge graph statistics."""
        return await self._run("kg_stats")

    async def invalidate_triple(
        self, subject: str, predicate: str, obj: str, ended: str | None = None,
    ) -> bool:
        """Invalidate a knowledge graph triple."""
        return await self._run("invalidate_triple", subject=subject, predicate=predicate, obj=obj, ended=ended)

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

    async def recall_many(self, queries: list[str], room: str | None = None, limit: int = 10) -> list[list[dict]]:
        """Run multiple recall queries concurrently."""
        tasks = [self.recall(q, room=room, limit=limit) for q in queries]
        return await asyncio.gather(*tasks)

    async def remember_many(self, items: list[dict[str, Any]]) -> list[str | None]:
        """Store multiple items concurrently (thin wrapper over batch)."""
        return await self.batch_remember(items)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------


    # Lifecycle management (TTL, compression, consolidation)
    # ------------------------------------------------------------------

    async def purge_expired(self, ttl_days: int = 90, ttl_summary_days: int = 180) -> dict:
        """Purge expired (TTL) memories from the palace."""
        from mempalace_evolve.core.lifecycle import find_ttl_expired, purge_expired as _pe
        collection = self._get_collection()
        if not collection:
            return {"purged": 0, "purged_ids": []}
        expired = find_ttl_expired(collection, ttl_days=ttl_days, ttl_summary_days=ttl_summary_days, wing=self._wing)
        ids = []
        for item_list in expired.values():
            if isinstance(item_list, list):
                ids.extend(item.get("id", "") for item in item_list if isinstance(item, dict))
        if not ids:
            return {"purged": 0, "purged_ids": []}
        result = _pe(collection, ids)
        result["purged_ids"] = ids
        return result

    async def compress_old_memories(self, compress_after_days: int = 60, max_chars: int = 800) -> dict:
        """Compress old, unused memories into shorter summaries."""
        from mempalace_evolve.core.lifecycle import find_compress_candidates, compress_candidates
        collection = self._get_collection()
        if not collection:
            return {"candidates": 0, "compressed": 0}
        candidates = find_compress_candidates(collection, compress_after_days=compress_after_days)
        if not candidates:
            return {"candidates": 0, "compressed": 0}
        if self._chroma is None:
            return {"candidates": sum(len(v) for v in candidates.values()), "compressed": 0}
        archive_col = self._chroma._client.get_or_create_collection(name="mempalace_archive", metadata={"hnsw:space": "cosine"})
        result = compress_candidates(collection, candidates, archive_col, max_chars=max_chars)
        return result

    async def consolidate(self, dry_run: bool = False) -> dict:
        """Run daily consolidation: deduplicate and merge similar memories."""
        from mempalace_evolve.core.consolidation import consolidate_daily
        return consolidate_daily(wing=self._wing, dry_run=dry_run)

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
