"""
MemPalace ChromaDB 辅助模块
===========================
集中 ChromaDB 连接/CRUD 逻辑，所有模块共用。
"""

import hashlib
import logging
import sys
import threading
import time as _time
from datetime import datetime, timezone
from pathlib import Path

import chromadb

from mempalace_evolve.core.config import get_config, COLLECTION_NAME, GLOBAL_CHROMA

logger = logging.getLogger("mempalace.chroma")

# ---------------------------------------------------------------------------
# ChromaDB 客户端 + 集合单例缓存（线程安全）
# ---------------------------------------------------------------------------
_cache_lock = threading.RLock()
_client_cache: dict[str, chromadb.PersistentClient] = {}
_collection_cache: dict[str, chromadb.Collection] = {}
_last_health_check: dict[str, float] = {}
_HEALTH_CHECK_INTERVAL = 60  # seconds


def get_collection(palace_path: str = None, create: bool = True) -> chromadb.Collection | None:
    """获取或创建 ChromaDB 集合（带缓存，线程安全）。

    Args:
        palace_path: ChromaDB 数据目录。None 则使用全局。
        create: True=不存在则创建，False=不存在返回 None

    Returns:
        chromadb.Collection 或 None（获取失败时）
    """
    if palace_path is None:
        palace_path = str(GLOBAL_CHROMA)

    cache_key = f"{palace_path}:{COLLECTION_NAME}:{create}"
    with _cache_lock:
        if cache_key in _collection_cache:
            col = _collection_cache[cache_key]
            # 每 60 秒做一次健康检查，而非每次调用都检查
            now = _time.time()
            if now - _last_health_check.get(cache_key, 0) < 60:
                return col
            # 健康检查
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

        if create:
            col = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        else:
            try:
                col = client.get_collection(name=COLLECTION_NAME)
            except Exception:
                return None

        with _cache_lock:
            _collection_cache[cache_key] = col
        return col
    except Exception as e:
        logger.warning(f"ChromaDB 连接失败 [{palace_path}]: {e}")
        if create:
            col = _repair_collection(palace_path)
            if col:
                with _cache_lock:
                    _collection_cache[cache_key] = col
            return col
        return None


def file_already_mined(collection, source_file: str) -> bool:
    """检查文件是否已有 drawers。

    Args:
        collection: ChromaDB 集合
        source_file: 文件路径（相对或绝对）

    Returns:
        True = 已挖掘，可跳过
    """
    try:
        results = collection.get(
            where={"source_file": source_file},
            limit=1,
        )
        return len(results["ids"]) > 0
    except Exception:
        return False


def add_drawer(collection, wing: str, room: str, content: str,
               source_file: str, chunk_index: int,
               added_by: str = "mcp", extra_meta: dict = None) -> bool:
    """添加一条 drawer（分块记忆）。"""
    # 强制确保所有参数为 str（防止 JSON-RPC 编码问题）
    wing = str(wing)
    room = str(room)
    content = str(content)
    source_file = str(source_file)
    added_by = str(added_by)

    drawer_id = _make_drawer_id(wing, room, source_file, chunk_index)

    # 前置去重检查（避免依赖异常消息）
    try:
        existing = collection.get(ids=[drawer_id])
        if existing and existing["ids"]:
            return False
    except Exception:
        pass

    now_iso = datetime.now(timezone.utc).isoformat()
    metadata = {
        "wing": wing,
        "room": room,
        "source_file": source_file,
        "chunk_index": chunk_index,
        "added_by": added_by,
        "filed_at": now_iso,
        "last_accessed": now_iso,
    }
    if extra_meta:
        # 确保 extra_meta 的值也是 str/int/float
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
        logger.warning(f"添加 drawer 失败: {e}")
        return False


def delete_file_drawers(collection, source_file: str) -> int:
    """删除指定文件的所有 drawers。

    Returns:
        删除数量
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
    """删除指定翼的所有 drawers。

    Returns:
        删除数量
    """
    try:
        results = collection.get(where={"wing": wing})
        ids = results["ids"]
        if ids:
            collection.delete(ids=ids)
        return len(ids)
    except Exception:
        return 0


def get_all_metadata(collection, batch_size: int = 1000) -> list[dict]:
    """获取集合中所有文档的元数据（分批）。

    Returns:
        [{id, metadata, document}]
    """
    all_items = []
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
        logger.warning(f"获取元数据失败: {e}")
    return all_items


def _make_drawer_id(wing: str, room: str, source_file: str, chunk_index: int) -> str:
    """生成确定性 drawer ID"""
    raw = f"{source_file}:{chunk_index}"
    hash_part = hashlib.md5(raw.encode()).hexdigest()[:16]
    return f"drawer_{wing}_{room}_{hash_part}"


def _repair_collection(palace_path: str) -> chromadb.Collection | None:
    """尝试修复损坏的 ChromaDB：备份旧数据，创建新集合。
    修复后需要重新 sync 才能恢复数据。
    """
    import shutil

    path = Path(palace_path)
    backup = path.parent / f"{path.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        if path.exists():
            shutil.move(str(path), str(backup))
            logger.info(f"已备份损坏数据到: {backup}")
            logger.info("修复后请运行 sync_manager.py --all 重新同步数据")

        path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(path))
        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as e:
        logger.error(f"修复失败（可能文件被锁定）: {e}")
        return None
