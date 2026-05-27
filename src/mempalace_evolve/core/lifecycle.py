"""
MemPalace 记忆生命周期管理
=========================
四大机制：
  1. 时间衰减评分 — importance * e^(-λ * days_since_last_access)
  2. 渐进压缩 — 旧 drawers 压缩为摘要，原文归档
  3. 准入控制 — 容量上限检查
  4. 冲突覆盖 — 语义重复时新替旧
"""

import hashlib
import logging
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mempalace_evolve.core.config import get_config

logger = logging.getLogger("mempalace.lifecycle")


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# 1. 时间衰减评分
# ---------------------------------------------------------------------------

def decay_score(importance: float, last_accessed: str, filed_at: str,
                decay_lambda: float = 0.02) -> float:
    """计算衰减后的记忆评分。

    score = importance * e^(-λ * days_since_last_access)

    向后兼容：无 last_accessed 时用 filed_at 代替。
    """
    # 参数验证
    try:
        importance = float(importance) if importance is not None else 0.0
    except (ValueError, TypeError):
        importance = 0.0

    access_str = last_accessed or filed_at
    if not access_str:
        return importance

    try:
        accessed = datetime.fromisoformat(access_str)
        if accessed.tzinfo is None:
            accessed = accessed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return importance

    now = datetime.now(timezone.utc)
    days = max(0, (now - accessed).total_seconds() / 86400)

    return importance * math.exp(-decay_lambda * days)


# ---------------------------------------------------------------------------
# 2. Touch（更新访问时间）
# ---------------------------------------------------------------------------

# 简易去抖缓存：{(drawer_id, last_touch_time)}
_touch_cache: dict = {}
TOUCH_DEBOUNCE_SECONDS = 300  # 5 分钟


def touch_drawers(collection, drawer_ids: list) -> int:
    """批量更新 drawer 的 last_accessed 时间。

    带 5 分钟去抖，同一 drawer 5 分钟内不重复 touch。
    ChromaDB update 需要完整 document + metadata。
    """
    if not drawer_ids:
        return 0

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    updated = 0

    # 过滤去抖
    to_touch = []
    for did in drawer_ids:
        last = _touch_cache.get(did)
        if last and (now - last).total_seconds() < TOUCH_DEBOUNCE_SECONDS:
            continue
        to_touch.append(did)

    if not to_touch:
        return 0

    try:
        batch = collection.get(ids=to_touch, include=["documents", "metadatas"])
    except Exception:
        return 0

    update_ids = []
    update_docs = []
    update_metas = []

    for i, doc_id in enumerate(batch["ids"]):
        meta = batch["metadatas"][i]
        doc = batch["documents"][i]
        meta["last_accessed"] = now_iso
        update_ids.append(doc_id)
        update_docs.append(doc)
        update_metas.append(meta)
        _touch_cache[doc_id] = now

    if update_ids:
        try:
            collection.update(
                ids=update_ids,
                documents=update_docs,
                metadatas=update_metas,
            )
            updated = len(update_ids)
        except Exception:
            logger.debug("touch_drawers batch update failed", exc_info=True)

    return updated


# ---------------------------------------------------------------------------
# 3. 渐进压缩
# ---------------------------------------------------------------------------

def find_compress_candidates(collection, compress_after_days: int = 60) -> dict:
    """找出超过 N 天未访问的 drawers，按 room 分组。

    Returns:
        {room: [(id, doc, meta), ...]}
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=compress_after_days)

    candidates = defaultdict(list)
    total = collection.count()
    batch_size = 500
    offset = 0

    while offset < total:
        try:
            batch = collection.get(
                include=["documents", "metadatas"],
                limit=batch_size,
                offset=offset,
            )
        except Exception:
            break

        for i, doc_id in enumerate(batch["ids"]):
            meta = batch["metadatas"][i]
            access_str = meta.get("last_accessed") or meta.get("filed_at", "")
            if not access_str:
                continue

            try:
                accessed = datetime.fromisoformat(access_str)
                if accessed.tzinfo is None:
                    accessed = accessed.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            if accessed < cutoff:
                room = meta.get("room", "general")
                candidates[room].append((doc_id, batch["documents"][i], meta))

        if len(batch["ids"]) < batch_size:
            break
        offset += len(batch["ids"])

    return dict(candidates)


def compress_text_block(docs: list, max_chars: int = 800) -> str:
    """纯文本压缩：取每段首句拼接，截断到 max_chars。

    不依赖 LLM。
    """
    first_sentences = []
    for doc in docs:
        stripped = doc.strip()
        if not stripped:
            continue
        # 取第一句（句号、问号、叹号、换行）
        for sep in ["。", "？", "！", ".", "?", "!", "\n"]:
            idx = stripped.find(sep)
            if idx > 0:
                first_sentences.append(stripped[:idx + 1].strip())
                break
        else:
            first_sentences.append(stripped[:100].strip())

    summary = "\n".join(f"- {s}" for s in first_sentences)
    if len(summary) > max_chars:
        summary = summary[:max_chars - 3] + "..."

    return summary


def compress_candidates(collection, candidates: dict, archive_collection,
                        max_summary_chars: int = 800) -> dict:
    """对同一 room 的多个候选执行压缩。

    1. 原文移入 archive_collection
    2. 创建摘要 drawer 替换
    3. 至少 2 个同 room 候选才压缩
    """
    stats = {"rooms_compressed": 0, "drawers_archived": 0, "summaries_created": 0}

    now_iso = datetime.now(timezone.utc).isoformat()

    for room, entries in candidates.items():
        if len(entries) < 2:
            continue

        # 归档原文
        archive_ids = []
        archive_docs = []
        archive_metas = []
        for doc_id, doc, meta in entries:
            am = dict(meta)
            am["archived_at"] = now_iso
            am["original_id"] = doc_id
            archive_ids.append(f"arch_{doc_id}")
            archive_docs.append(doc)
            archive_metas.append(am)

        try:
            archive_collection.add(
                ids=archive_ids, documents=archive_docs, metadatas=archive_metas,
            )
        except Exception:
            logger.debug("archive add failed for room=%s", room, exc_info=True)
            continue

        # 创建摘要
        summary = compress_text_block(
            [d for _, d, _ in entries], max_summary_chars,
        )
        wing = entries[0][2].get("wing", "unknown")
        summary_id = (
            f"drawer_{wing}_{room}_summary_"
            f"{hashlib.md5(summary.encode()).hexdigest()[:12]}"
        )
        summary_meta = {
            "wing": wing,
            "room": room,
            "source_file": "compressed_summary",
            "chunk_index": -1,
            "added_by": "lifecycle_compress",
            "filed_at": entries[0][2].get("filed_at", now_iso),
            "last_accessed": now_iso,
            "importance": min(
                _safe_float(m.get("importance"), 3) for _, _, m in entries
            ),
            "is_summary": True,
            "source_drawer_count": len(entries),
        }

        # 添加摘要 + 删除原始（先添加后删除，防止摘要添加失败导致数据丢失）
        try:
            collection.add(ids=[summary_id], documents=[summary], metadatas=[summary_meta])
            collection.delete(ids=[e[0] for e in entries])
        except Exception:
            logger.debug("compress summary add/delete failed for room=%s", room, exc_info=True)
            # 尝试回滚：如果摘要已添加但删除未完成，这是可接受的
            try:
                collection.delete(ids=[summary_id])
            except Exception:
                logger.debug("rollback delete failed for summary_id=%s", summary_id, exc_info=True)
            continue

        stats["rooms_compressed"] += 1
        stats["drawers_archived"] += len(entries)
        stats["summaries_created"] += 1

    return stats


# ---------------------------------------------------------------------------
# 4. 准入控制
# ---------------------------------------------------------------------------

def check_admission(collection, wing: str,
                    max_total: int = 500, max_per_wing: int = 200) -> dict:
    """检查是否允许写入新 drawer。"""
    total = collection.count()

    if total >= max_total:
        return {
            "allowed": False,
            "reason": f"total_drawers ({total}) >= max_total ({max_total})",
            "counts": {"total": total},
            "suggestion": "run mempalace_lifecycle_compress to free space",
        }

    # 使用 where 过滤统计 wing 计数（避免全表扫描）
    try:
        wing_results = collection.get(where={"wing": wing}, include=[])
        wing_count = len(wing_results["ids"])
    except Exception:
        # 回退：使用 taxonomy 缓存（如果可用）代替全表扫描
        try:
            from mcp_tools_read import _get_taxonomy_cached
            from mempalace_evolve.core.chroma_helper import get_collection
            from mempalace_evolve.core.config import GLOBAL_CHROMA
            col = get_collection(str(GLOBAL_CHROMA))
            taxonomy = _get_taxonomy_cached(col)
            wing_count = sum(taxonomy.get(wing, {}).values())
        except Exception:
            wing_count = 0

    if wing_count >= max_per_wing:
        return {
            "allowed": False,
            "reason": f"wing '{wing}' count ({wing_count}) >= max_per_wing ({max_per_wing})",
            "counts": {"total": total, "wing": wing_count},
            "suggestion": "run mempalace_lifecycle_compress to free space in this wing",
        }

    return {"allowed": True, "counts": {"total": total, "wing": wing_count}}


# ---------------------------------------------------------------------------
# 5. 数据迁移
# ---------------------------------------------------------------------------

def migrate_legacy_drawers(collection) -> dict:
    """为没有 last_accessed 字段的 drawers 补充该字段（用 filed_at 初始化）。

    迁移是幂等的：重复运行不会重复处理。
    """
    total = collection.count()
    migrated = 0
    skipped = 0
    batch_size = 100

    now_iso = datetime.now(timezone.utc).isoformat()
    offset = 0

    while offset < total:
        try:
            batch = collection.get(
                include=["documents", "metadatas"],
                limit=batch_size,
                offset=offset,
            )
        except Exception:
            break

        update_ids = []
        update_docs = []
        update_metas = []

        for i, doc_id in enumerate(batch["ids"]):
            meta = batch["metadatas"][i]
            if "last_accessed" not in meta:
                meta["last_accessed"] = meta.get("filed_at", now_iso)
                update_ids.append(doc_id)
                update_docs.append(batch["documents"][i])
                update_metas.append(meta)
                migrated += 1
            else:
                skipped += 1

        if update_ids:
            try:
                collection.update(
                    ids=update_ids, documents=update_docs, metadatas=update_metas,
                )
            except Exception:
                migrated -= len(update_ids)
                skipped += len(update_ids)

        if len(batch["ids"]) < batch_size:
            break
        offset += len(batch["ids"])

    return {"total": total, "migrated": migrated, "skipped": skipped}


# ---------------------------------------------------------------------------
# 6. TTL 过期删除
# ---------------------------------------------------------------------------

def find_ttl_expired(collection, ttl_days: int = 90, ttl_summary_days: int = 180,
                     min_importance: float = 0.25,
                     protected_rooms: list = None) -> list:
    """找到满足 TTL 过期条件的 drawers。

    条件：last_accessed 超过 ttl_days 且 importance < min_importance。
    is_summary 的 drawers 使用 ttl_summary_days。
    protected_rooms 中的 drawers 永不过期。
    """
    if protected_rooms is None:
        protected_rooms = ["identity", "index", "config"]

    now = datetime.now(timezone.utc)
    expired = []
    total = collection.count()
    batch_size = 500
    offset = 0

    while offset < total:
        try:
            batch = collection.get(
                include=["documents", "metadatas"],
                limit=batch_size,
                offset=offset,
            )
        except Exception:
            break

        for i, doc_id in enumerate(batch["ids"]):
            meta = batch["metadatas"][i]
            room = meta.get("room", "general")

            if room in protected_rooms:
                continue

            access_str = meta.get("last_accessed") or meta.get("filed_at", "")
            if not access_str:
                continue

            try:
                accessed = datetime.fromisoformat(access_str)
                if accessed.tzinfo is None:
                    accessed = accessed.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            is_summary = meta.get("is_summary", False)
            applicable_ttl = ttl_summary_days if is_summary else ttl_days
            days_since = (now - accessed).days

            if days_since < applicable_ttl:
                continue

            importance = _safe_float(meta.get("enhanced_importance"),
                                     _safe_float(meta.get("importance"), 0.5))
            if importance >= min_importance:
                continue

            expired.append({
                "id": doc_id,
                "room": room,
                "wing": meta.get("wing", "unknown"),
                "days_since_access": days_since,
                "importance": importance,
                "is_summary": is_summary,
                "content_preview": batch["documents"][i][:100],
            })

        if len(batch["ids"]) < batch_size:
            break
        offset += len(batch["ids"])

    return expired


def purge_expired(collection, expired_ids: list) -> dict:
    """删除过期的 drawers。"""
    if not expired_ids:
        return {"purged": 0}

    try:
        collection.delete(ids=expired_ids)
        return {"purged": len(expired_ids)}
    except Exception:
        logger.debug("purge_expired failed", exc_info=True)
        return {"purged": 0, "error": "batch delete failed"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MemPalace 生命周期管理")
    parser.add_argument("command", choices=["migrate", "status", "compress", "test-decay"])
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", action="store_true")
    args = parser.parse_args()

    from mempalace_evolve.core.chroma_helper import get_collection
    from mempalace_evolve.core.config import GLOBAL_CHROMA
    col = get_collection(str(GLOBAL_CHROMA))

    if args.command == "migrate":
        result = migrate_legacy_drawers(col)
        print(f"迁移完成: {result}")

    elif args.command == "status":
        if not col:
            print("Palace 不可用")
        else:
            now = datetime.now(timezone.utc)
            buckets = {"active_7d": 0, "active_30d": 0, "stale_60d": 0, "ancient_90d": 0}
            total = col.count()
            offset = 0
            while offset < total:
                batch = col.get(include=["metadatas"], limit=500, offset=offset)
                for meta in batch["metadatas"]:
                    access_str = meta.get("last_accessed") or meta.get("filed_at", "")
                    if access_str:
                        try:
                            accessed = datetime.fromisoformat(access_str)
                            if accessed.tzinfo is None:
                                accessed = accessed.replace(tzinfo=timezone.utc)
                            days = (now - accessed).days
                            if days <= 7: buckets["active_7d"] += 1
                            if days <= 30: buckets["active_30d"] += 1
                            if days >= 60: buckets["stale_60d"] += 1
                            if days >= 90: buckets["ancient_90d"] += 1
                        except (ValueError, TypeError):
                            pass
                if len(batch["ids"]) < 500:
                    break
                offset += len(batch["ids"])
            print(f"总 drawers: {total}")
            for k, v in buckets.items():
                print(f"  {k}: {v}")

    elif args.command == "compress":
        dry_run = not args.no_dry_run
        config = get_config()
        lc = config.lifecycle_config
        candidates = find_compress_candidates(col, lc["compress_after_days"])
        if dry_run:
            print(f"DRY RUN — 压缩候选:")
            total_cand = 0
            for room, entries in sorted(candidates.items()):
                print(f"  {room}: {len(entries)} drawers")
                total_cand += len(entries)
            print(f"  总计: {total_cand} 个候选")
        else:
            import chromadb
            client = chromadb.PersistentClient(path=str(GLOBAL_CHROMA))
            archive_col = client.get_or_create_collection(
                "mempalace_archived", metadata={"hnsw:space": "cosine"},
            )
            stats = compress_candidates(col, candidates, archive_col, lc["compress_max_summary_chars"])
            print(f"压缩完成: {stats}")

    elif args.command == "test-decay":
        # 测试衰减曲线
        for days in [0, 7, 14, 30, 60, 90, 180, 365]:
            past = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            score = decay_score(3.0, past, past, 0.02)
            print(f"  {days:4d} days: score={score:.3f}")
