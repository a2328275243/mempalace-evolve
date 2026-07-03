"""MemPalace ChromaDB helper module.

Centralizes ChromaDB connection/CRUD logic shared by all modules.
Uses a singleton cached embedding function for performance.
"""

from __future__ import annotations

import hashlib
import logging
import sys
import threading
import time as _time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb

from mempalace_evolve.core.config import get_config, COLLECTION_NAME, GLOBAL_CHROMA
from mempalace_evolve.core.embeddings import get_cached_ef

logger = logging.getLogger("mempalace.chroma")

# ---------------------------------------------------------------------------
# ChromaDB client + collection singleton cache (thread-safe)
# ---------------------------------------------------------------------------
_cache_lock = threading.RLock()
_client_cache: dict[str, chromadb.PersistentClient] = {}
_collection_cache: dict[str, chromadb.Collection] = {}
_last_health_check: dict[str, float] = {}
_HEALTH_CHECK_INTERVAL = 60  # seconds


def get_collection(palace_path: str = None, create: bool = True) -> chromadb.Collection | None:
    """Get or create a ChromaDB collection (cached, thread-safe).

    Args:
        palace_path: ChromaDB data directory. None uses global default.
        create: True=create if missing, False=return None if missing.

    Returns:
        chromadb.Collection or None (on failure).
    """
    if palace_path is None:
        palace_path = str(GLOBAL_CHROMA)

    cache_key = f"{palace_path}:{COLLECTION_NAME}:{create}"
    with _cache_lock:
        if cache_key in _collection_cache:
            col = _collection_cache[cache_key]
            # Health check every 60s instead of every call
            now = _time.time()
            if now - _last_health_check.get(cache_key, 0) < _HEALTH_CHECK_INTERVAL:
                return col
            # Health check
            try:
                col.count()
                _last_health_check[cache_key] = now
                return col
            except Exception:
                _collection_cache.pop(cache_key, None)
                _client_cache.pop(palace_path, None)

    try:
        with _cache_lock:
            if palace_path not in _client_cache:
                _client_cache[palace_path] = chromadb.PersistentClient(path=palace_path)
            client = _client_cache[palace_path]

        ef = get_cached_ef()

        if create:
            col = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
                embedding_function=ef,
            )
        else:
            try:
                col = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
            except Exception:
                return None

        with _cache_lock:
            _collection_cache[cache_key] = col
        return col
    except Exception as e:
        logger.warning("Failed to get chroma collection: %s", e)
        return None


def add_drawer(
    collection,
    wing: str,
    room: str,
    content: str,
    source_file: str = "manual",
    chunk_index: int = 0,
    added_by: str = "manual",
    extra_meta: dict[str, Any] | None = None,
) -> bool:
    """Add a single drawer (memory document) to the collection.

    Returns True on success, False if duplicate or error.
    """
    # Force-convert all params to string for ChromaDB compatibility
    wing = str(wing)
    room = str(room)
    content = str(content)
    source_file = str(source_file)
    added_by = str(added_by)

    drawer_id = _make_drawer_id(wing, room, source_file, chunk_index)

    # Check for duplicates before adding
    try:
        existing = collection.get(ids=[drawer_id])
        if existing and existing.get("ids"):
            return False
    except Exception:
        pass  # If we can't check, proceed and let add handle it

    now_iso = datetime.now(timezone.utc).isoformat()

    metadata: dict[str, str | int | float] = {
        "wing": wing,
        "room": room,
        "source_file": source_file,
        "chunk_index": chunk_index,
        "added_by": added_by,
        "filed_at": now_iso,
        "last_accessed": now_iso,
    }
    if extra_meta:
        for k, v in extra_meta.items():
            if isinstance(v, (int, float, bool)):
                metadata[k] = v
            else:
                metadata[k] = str(v)

    try:
        collection.add(
            ids=[drawer_id],
            documents=[content],
            metadatas=[metadata],
        )
        return True
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            return False
        logger.warning("add_drawer failed: %s", e)
        return False


def batch_add_drawers(collection, drawers: list[dict]) -> tuple[int, int]:
    """Bulk-add drawers with a single ChromaDB call per chunk.

    Much faster than calling add_drawer() repeatedly.
    Returns (added_count, skipped_count).
    """
    if not drawers:
        return (0, 0)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for d in drawers:
        wing = str(d["wing"])
        room = str(d["room"])
        content = str(d["content"])
        source_file = str(d["source_file"])
        chunk_index = int(d.get("chunk_index", 0))
        extra_meta = d.get("extra_meta", {})

        drawer_id = _make_drawer_id(wing, room, source_file, chunk_index)
        ids.append(drawer_id)

        now_iso = datetime.now(timezone.utc).isoformat()
        meta: dict[str, str | int | float] = {
            "wing": wing,
            "room": room,
            "source_file": source_file,
            "chunk_index": chunk_index,
            "added_by": str(d.get("added_by", "bulk")),
            "filed_at": now_iso,
            "last_accessed": now_iso,
        }
        for k, v in extra_meta.items():
            if isinstance(v, (int, float, bool)):
                meta[k] = v
            else:
                meta[k] = str(v)
        metadatas.append(meta)
        documents.append(content)

    added = 0
    skipped = 0
    # Chroma has max batch size ~500
    for i in range(0, len(ids), 500):
        chunk_ids = ids[i : i + 500]
        chunk_docs = documents[i : i + 500]
        chunk_metas = metadatas[i : i + 500]
        try:
            collection.add(
                ids=chunk_ids,
                documents=chunk_docs,
                metadatas=chunk_metas,
            )
            added += len(chunk_ids)
        except Exception as e:
            msg = str(e).lower()
            if "already exists" in msg or "duplicate" in msg:
                skipped += len(chunk_ids)
            else:
                logger.warning("batch_add_drawers chunk failed: %s", e)
                skipped += len(chunk_ids)
    return (added, skipped)


def delete_file_drawers(collection, source_file: str) -> int:
    """Delete all drawers from a specific source file.

    Returns:
        Number of deleted items.
    """
    try:
        results = collection.get(where={"source_file": source_file})
        ids = results["ids"]
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0


def delete_by_wing(collection, wing: str) -> int:
    """Delete all drawers for a given wing.

    Returns:
        Number of deleted items.
    """
    try:
        results = collection.get(where={"wing": wing})
        ids = results["ids"]
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0


def delete_by_room(collection, wing: str, room: str) -> int:
    """Delete all drawers matching a specific wing + room.

    Returns:
        Number of deleted items.
    """
    try:
        results = collection.get(where={"$and": [{"wing": wing}, {"room": room}]})
        ids = results["ids"]
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0


def get_all_metadata(collection, batch_size: int = 1000) -> list[dict]:
    """Fetch all document metadata from the collection (batched).

    Returns:
        [{id, metadata, document}]
    """
    all_items: list[dict] = []
    try:
        total = collection.count()
        offset = 0
        while offset < total:
            results = collection.get(
                include=["metadatas", "documents"],
                limit=batch_size,
                offset=offset,
            )
            for i, doc_id in enumerate(results["ids"]):
                all_items.append({
                    "id": doc_id,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {},
                    "document": results["documents"][i] if results["documents"] else "",
                })
            if len(results["ids"]) < batch_size:
                break
            offset += len(results["ids"])
    except Exception as e:
        logger.warning("get_all_metadata failed: %s", e)
    return all_items


def get_pool_stats() -> dict:
    """Return connection pool statistics for monitoring."""
    with _cache_lock:
        return {
            "clients": len(_client_cache),
            "collections": len(_collection_cache),
            "health_checks": len(_last_health_check),
        }


def _make_drawer_id(wing: str, room: str, source_file: str, chunk_index: int) -> str:
    """Generate a deterministic drawer ID."""
    raw = f"{source_file}:{chunk_index}"
    hash_part = hashlib.md5(raw.encode()).hexdigest()[:16]
    return f"drawer_{wing}_{room}_{hash_part}"




def file_already_mined(collection: Any, source_file: str) -> bool:
    try:
        result = collection.get(where={"source_file": source_file})
        return bool(result and result.get("ids"))
    except Exception:
        return False


def delete_file_drawers(collection: Any, source_file: str) -> int:
    try:
        result = collection.get(where={"source_file": source_file})
        ids = result.get("ids", []) if result else []
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0


def _repair_collection(palace_path: str) -> chromadb.Collection | None:
    """Attempt to repair a corrupted ChromaDB: back up old data, create new collection.
    After repair, sync_manager must be run to restore data.
    """
    import shutil

    path = Path(palace_path)
    backup = path.parent / f"{path.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        if path.exists():
            shutil.move(str(path), str(backup))
            logger.info("Backed up damaged data to: %s", backup)
            logger.info("After repair, run sync_manager.py --all to resync data")

        path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(path))
        ef = get_cached_ef()
        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            embedding_function=ef,
        )
    except Exception as e:
        logger.error("Repair failed (files may be locked): %s", e)
        return None
