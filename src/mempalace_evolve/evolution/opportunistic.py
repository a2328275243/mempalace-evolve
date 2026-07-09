"""
opportunistic_evolve.py — 被动进化模块
=====================================
在 evolve() 调用时执行四项维护：
  1. 低分清理：评分过低且长期未访问 → 自动删除
  2. candidate 晋升：candidate 翼中高质量记忆 → 移入项目 wing
  3. 孤立实体清理：KG 中无任何关系的实体 → 删除
  4. 过时决策标记：decisions room 中超时的 → 标记 stale
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from mempalace_evolve.core.lifecycle import find_ttl_expired, purge_expired, _safe_float

logger = logging.getLogger("mempalace_evolve.evolve")


def evolve_low_score_cleanup(
    collection,
    dry_run: bool = True,
    purge_days: int = 90,
    min_score: float = 0.30,
    protected_rooms: list[str] | None = None,
) -> dict:
    """低分清理：评分 < min_score 且超过 purge_days 未访问 → 删除

    protected_rooms 中的记忆不会被删除（如 decisions 设置了 never_delete）。
    """
    expired = find_ttl_expired(
        collection,
        ttl_days=purge_days,
        ttl_summary_days=purge_days * 2,
        min_importance=min_score,
    )

    # Filter out protected rooms
    if protected_rooms:
        expired = [e for e in expired if e.get("room") not in protected_rooms]

    if dry_run:
        return {"action": "low_score_cleanup", "dry_run": True, "candidates": len(expired)}

    ids = [e["id"] for e in expired]
    result = purge_expired(collection, ids)
    return {"action": "low_score_cleanup", "purged": result["purged"]}


def evolve_candidate_promotion(
    collection, dry_run: bool = True, promote_score: float = 0.45
) -> dict:
    """candidate 晋升 + 跨 wing 热门记忆自动升级为 procedural。

    晋升条件（满足任一）：
    1. candidate 翼中评分 >= promote_score → 移入项目 wing
    2. 任何记忆被 3+ 个不同 wing recall 命中 → 升级为 procedural（全局共享）
    """
    promoted = 0
    upgraded_to_procedural = 0

    # --- Part 1: candidate → project wing ---
    try:
        candidates = collection.get(
            where={"wing": "candidate"},
            include=["documents", "metadatas"],
        )
    except Exception:
        candidates = None

    if candidates and candidates.get("ids"):
        to_promote = []
        for i, doc_id in enumerate(candidates["ids"]):
            meta = candidates["metadatas"][i]
            importance = _safe_float(
                meta.get("enhanced_importance"), _safe_float(meta.get("importance"), 0.3)
            )
            if importance >= promote_score:
                to_promote.append((doc_id, candidates["documents"][i], meta, importance))

        if not dry_run:
            for doc_id, doc, meta, _ in to_promote:
                new_wing = meta.get("source_wing", meta.get("wing", "global"))
                if new_wing == "candidate":
                    new_wing = "global"
                meta["wing"] = new_wing
                meta["promoted_at"] = datetime.now(timezone.utc).isoformat()
                try:
                    collection.update(ids=[doc_id], documents=[doc], metadatas=[meta])
                    promoted += 1
                except Exception as e:
                    logger.warning(f"Failed to promote candidate '{doc_id}': {e}")

    # --- Part 2: cross-wing hot memories → procedural ---
    try:
        all_items = collection.get(include=["metadatas"])
        if all_items and all_items.get("ids"):
            for i, doc_id in enumerate(all_items["ids"]):
                meta = all_items["metadatas"][i]
                cross_hits = int(meta.get("cross_wing_hits", 0))
                current_type = meta.get("memory_type", "")
                if cross_hits >= 3 and current_type != "procedural":
                    if not dry_run:
                        meta["memory_type"] = "procedural"
                        meta["auto_promoted_reason"] = f"cross_wing_hits={cross_hits}"
                        try:
                            collection.update(ids=[doc_id], metadatas=[meta])
                            upgraded_to_procedural += 1
                        except Exception as e:
                            logger.warning(f"Failed to upgrade to procedural '{doc_id}': {e}")
                    else:
                        upgraded_to_procedural += 1
    except Exception as e:
        logger.error(f"Cross-wing hot memories scan failed: {e}")

    return {
        "action": "candidate_promotion",
        "promoted": promoted,
        "upgraded_to_procedural": upgraded_to_procedural,
        "dry_run": dry_run,
    }


def evolve_orphan_entities(dry_run: bool = True) -> dict:
    """孤立实体清理：KG 中无任何关系的实体 → 删除"""
    try:
        from mempalace_evolve.core.knowledge_graph import KnowledgeGraph

        kg = KnowledgeGraph()
    except (ImportError, Exception):
        return {"action": "orphan_cleanup", "skipped": True}

    try:
        all_entities = kg.get_all_entity_names()
    except Exception:
        return {"action": "orphan_cleanup", "error": "failed to get entities"}

    orphans = []
    for entity in all_entities:
        try:
            result = kg.query_entity(entity, direction="both")
            if not result or (isinstance(result, list) and len(result) == 0):
                orphans.append(entity)
        except Exception:
            continue

    if dry_run:
        return {
            "action": "orphan_cleanup",
            "dry_run": True,
            "total_entities": len(all_entities),
            "orphans": len(orphans),
        }

    removed = 0
    failed = 0
    for entity in orphans:
        try:
            if kg.remove_entity(entity):
                removed += 1
            else:
                logger.warning(f"Entity not found during orphan cleanup: {entity}")
        except Exception as e:
            failed += 1
            logger.warning(f"Failed to remove orphan entity '{entity}': {e}")

    if failed > 0:
        logger.warning(f"Orphan cleanup completed with {failed} failures")

    return {"action": "orphan_cleanup", "removed": removed, "failed": failed}


def evolve_stale_decisions(collection, dry_run: bool = True, stale_days: int = 180) -> dict:
    """过时决策标记：decisions room 中超过 stale_days 的 → 标记 stale"""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=stale_days)

    try:
        decisions = collection.get(
            where={"room": "decisions"},
            include=["documents", "metadatas"],
        )
    except Exception as e:
        logger.error(f"Failed to query decisions: {e}")
        return {"action": "stale_decisions", "error": f"query failed: {e}"}

    if not decisions or not decisions["ids"]:
        return {"action": "stale_decisions", "total": 0, "stale": 0}

    stale = []
    for i, doc_id in enumerate(decisions["ids"]):
        meta = decisions["metadatas"][i]
        if meta.get("status") == "stale":
            continue
        access_str = meta.get("last_accessed") or meta.get("filed_at", "")
        if not access_str:
            continue
        try:
            accessed = datetime.fromisoformat(access_str)
            if accessed.tzinfo is None:
                accessed = accessed.replace(tzinfo=timezone.utc)
            if accessed < cutoff:
                stale.append((doc_id, decisions["documents"][i], meta))
        except (ValueError, TypeError):
            continue

    if dry_run:
        return {
            "action": "stale_decisions",
            "dry_run": True,
            "total_decisions": len(decisions["ids"]),
            "stale_candidates": len(stale),
        }

    marked = 0
    failed = 0
    for doc_id, doc, meta in stale:
        meta["status"] = "stale"
        meta["stale_marked_at"] = now.isoformat()
        try:
            collection.update(ids=[doc_id], documents=[doc], metadatas=[meta])
            marked += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Failed to mark decision as stale '{doc_id}': {e}")

    if failed > 0:
        logger.warning(f"Stale decision marking completed with {failed} failures")

    return {"action": "stale_decisions", "marked_stale": marked, "failed": failed}


def run_opportunistic_evolve(
    collection,
    dry_run: bool = True,
    purge_days: int = 90,
    min_score: float = 0.30,
    promote_score: float = 0.45,
    stale_days: int = 180,
    protected_rooms: list[str] | None = None,
) -> dict:
    """执行完整的被动进化流程（四项维护）。"""
    results = {}
    results["low_score_cleanup"] = evolve_low_score_cleanup(
        collection,
        dry_run=dry_run,
        purge_days=purge_days,
        min_score=min_score,
        protected_rooms=protected_rooms,
    )
    results["candidate_promotion"] = evolve_candidate_promotion(
        collection, dry_run=dry_run, promote_score=promote_score
    )
    results["orphan_cleanup"] = evolve_orphan_entities(dry_run=dry_run)
    results["stale_decisions"] = evolve_stale_decisions(
        collection, dry_run=dry_run, stale_days=stale_days
    )
    return {"success": True, "dry_run": dry_run, "results": results}
