#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
consolidation.py — 每日记忆整合系统
===================================
功能：
1. 分析当天所有 drawer 记录
2. 识别重复、冲突、过时信息
3. 生成每日摘要
4. 合并相似记忆
5. 更新知识图谱
6. 生成整合报告
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mempalace_evolve.core.chroma_helper import get_collection, get_all_metadata, add_drawer
from mempalace_evolve.core.config import get_config, GLOBAL_CHROMA
from mempalace_evolve.core.knowledge_graph import KnowledgeGraph


def get_today_drawers(collection, wing=None):
    """获取今天创建的所有 drawers"""
    today = datetime.now(timezone.utc).date()
    all_items = get_all_metadata(collection)

    today_drawers = []
    for item in all_items:
        meta = item.get("metadata", {})
        filed_at = meta.get("filed_at", "")

        if filed_at:
            try:
                filed_date = datetime.fromisoformat(filed_at).date()
                if filed_date == today:
                    if wing is None or meta.get("wing") == wing:
                        today_drawers.append(item)
            except (ValueError, TypeError):
                pass

    return today_drawers


def _text_similarity(text1: str, text2: str) -> float:
    """计算文本相似度，用于去重检测。

    设计原则：宁可漏判也不误杀。
    文本级去重只负责捕获「完全相同内容被重复保存」的情况。
    标准化处理：统一空白、去除尾部标点后做精确比较。
    语义级去重（"相似但不同的表述"）应由 ChromaDB 向量距离承担。

    返回值：
    - 1.0: 标准化后完全相同（应合并）
    - < 0.90: 有任何实质差异（不触发 0.95 阈值）
    """
    if not text1 or not text2:
        return 0.0

    import re

    def _normalize(s: str) -> str:
        """统一空白、去尾部标点、折叠连续空格"""
        s = re.sub(r'\s+', ' ', s).strip()
        s = s.rstrip('.,;:!?。，；：！？')
        return s

    n1 = _normalize(text1)
    n2 = _normalize(text2)

    if n1 == n2:
        return 1.0

    # 任何实质性文本差异 → 返回低分，不触发合并
    # 用 SequenceMatcher 给出参考分数（用于日志/调试），但压到安全范围
    from difflib import SequenceMatcher
    raw_ratio = SequenceMatcher(None, n1, n2).ratio()
    return raw_ratio * 0.85  # 确保最高不超过 ~0.85


def identify_duplicates(drawers, threshold=0.95):
    """识别重复记忆（基于字符级 n-gram 相似度，支持中英文）

    threshold 默认 0.95：仅合并几乎完全相同的记忆，避免误杀。
    """
    duplicates = []

    for i, d1 in enumerate(drawers):
        for j, d2 in enumerate(drawers[i+1:], start=i+1):
            text1 = d1.get("document", "").lower()
            text2 = d2.get("document", "").lower()

            similarity = _text_similarity(text1, text2)

            if similarity >= threshold:
                duplicates.append({
                    "drawer1": d1.get("id"),
                    "drawer2": d2.get("id"),
                    "similarity": similarity,
                    "text1": text1[:100],
                    "text2": text2[:100]
                })

    return duplicates


def identify_conflicts(drawers, kg: KnowledgeGraph):
    """识别冲突记忆（基于实体共享检测矛盾的决策）"""
    try:
        from entity_detector import extract_chinese_candidates, extract_candidates as extract_english_candidates
        _has_entity_detector = True
    except ImportError:
        _has_entity_detector = False

    conflicts = []

    # 提取所有决策类记忆
    decisions = [d for d in drawers if d.get("metadata", {}).get("room") == "decisions"]

    if _has_entity_detector:
        # 基于实体分组（extract_*_candidates 返回 dict: name → freq）
        entity_map = defaultdict(set)  # entity -> set of drawer indices
        for idx, d in enumerate(decisions):
            content = d.get("document", "")
            cn_entities = list(extract_chinese_candidates(content).keys())
            en_entities = list(extract_english_candidates(content).keys())
            for entity in cn_entities + en_entities:
                entity_map[entity].add(idx)

        # 检查共享 2+ 实体的决策组
        entity_groups = defaultdict(set)
        for entity, indices in entity_map.items():
            for idx in indices:
                entity_groups[idx].add(entity)

        # 找到共享实体的决策对
        checked = set()
        for i in range(len(decisions)):
            for j in range(i + 1, len(decisions)):
                shared = entity_groups.get(i, set()) & entity_groups.get(j, set())
                if len(shared) >= 2:
                    pair_key = (decisions[i].get("id"), decisions[j].get("id"))
                    if pair_key not in checked:
                        checked.add(pair_key)
                        conflicts.append({
                            "type": "decision_conflict",
                            "shared_entities": list(shared),
                            "count": 2,
                            "drawers": [decisions[i].get("id"), decisions[j].get("id")],
                            "content_preview": [
                                decisions[i].get("document", "")[:100],
                                decisions[j].get("document", "")[:100],
                            ]
                        })
    else:
        # 回退到简单的关键词检测
        decision_topics = defaultdict(list)
        for d in decisions:
            content = d.get("document", "")
            if "前端" in content or "React" in content or "Vue" in content:
                decision_topics["前端技术栈"].append(d)
            if "数据库" in content or "MySQL" in content or "PostgreSQL" in content:
                decision_topics["数据库"].append(d)

        for topic, topic_decisions in decision_topics.items():
            if len(topic_decisions) > 1:
                conflicts.append({
                    "type": "decision_conflict",
                    "topic": topic,
                    "count": len(topic_decisions),
                    "drawers": [d.get("id") for d in topic_decisions]
                })

    return conflicts


def generate_daily_summary(drawers, wing=None):
    """生成每日摘要"""
    summary = {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "wing": wing or "global",
        "total_drawers": len(drawers),
        "by_room": defaultdict(int),
        "key_facts": [],
        "decisions": [],
        "errors": []
    }

    for d in drawers:
        meta = d.get("metadata", {})
        room = meta.get("room", "general")
        summary["by_room"][room] += 1

        content = d.get("document", "")

        # 提取关键事实
        if room == "project":
            summary["key_facts"].append(content[:200])
        elif room == "decisions":
            summary["decisions"].append(content[:200])
        elif room == "error_patterns":
            summary["errors"].append(content[:200])

    return summary


def merge_similar_drawers(collection, duplicates, dry_run=True):
    """合并相似记忆"""
    merged = []

    for dup in duplicates:
        if dry_run:
            merged.append({
                "action": "would_merge",
                "drawer1": dup["drawer1"],
                "drawer2": dup["drawer2"],
                "similarity": dup["similarity"]
            })
        else:
            # 实际合并：保留较新的，删除较旧的
            try:
                items = collection.get(
                    ids=[dup["drawer1"], dup["drawer2"]],
                    include=["documents", "metadatas"]
                )
                if not items or not items["metadatas"] or len(items["metadatas"]) < 2:
                    merged.append({"action": "skipped", "reason": "not_found", "dup": dup})
                    continue

                # 确定新旧（按 filed_at 排序）
                filed1 = items["metadatas"][0].get("filed_at", "")
                filed2 = items["metadatas"][1].get("filed_at", "")
                older_idx = 0 if filed1 <= filed2 else 1
                newer_idx = 1 - older_idx

                older_id = items["ids"][older_idx]
                newer_id = items["ids"][newer_idx]
                older_meta = items["metadatas"][older_idx]
                newer_meta = items["metadatas"][newer_idx]
                older_doc = items["documents"][older_idx]
                newer_doc = items["documents"][newer_idx]

                # 合并内容：新内容在前，旧内容标记为合并来源
                merged_content = newer_doc + "\n\n--- 合并自旧记录 ---\n" + older_doc

                # 合并唯一 metadata
                merged_meta = dict(newer_meta)
                merged_meta["merged_from"] = older_id
                merged_meta["merged_at"] = datetime.now(timezone.utc).isoformat()
                # 从旧记录中保留新记录缺少的字段
                for key in ("source_file", "wing", "room"):
                    if key not in merged_meta and key in older_meta:
                        merged_meta[key] = older_meta[key]

                # 更新新记录
                collection.update(
                    ids=[newer_id],
                    documents=[merged_content],
                    metadatas=[merged_meta],
                )

                # 删除旧记录
                collection.delete(ids=[older_id])

                # 更新知识图谱中的边指向
                kg = KnowledgeGraph()
                conn = kg._conn()
                conn.execute(
                    "UPDATE triples SET source_closet=? WHERE source_closet=?",
                    (newer_id, older_id),
                )
                conn.commit()
                # conn reused by KG connection pool

                merged.append({
                    "action": "merged",
                    "kept_id": newer_id,
                    "deleted_id": older_id,
                    "similarity": dup["similarity"]
                })
            except Exception as e:
                merged.append({
                    "action": "error",
                    "drawer1": dup["drawer1"],
                    "drawer2": dup["drawer2"],
                    "error": str(e)
                })

    return merged


def update_knowledge_graph(drawers, kg: KnowledgeGraph):
    """从今日记忆更新知识图谱"""
    updated = []

    for d in drawers:
        content = d.get("document", "")
        meta = d.get("metadata", {})

        # 简单的实体关系提取（实际应该用 NLP）
        # 示例：检测 "X 使用 Y" 模式
        if "使用" in content:
            parts = content.split("使用")
            if len(parts) >= 2:
                subject = parts[0].strip().split()[-1] if parts[0].strip() else None
                obj = parts[1].strip().split()[0] if parts[1].strip() else None

                if subject and obj:
                    kg.add_triple(
                        subject=subject,
                        predicate="uses",
                        obj=obj,
                        valid_from=meta.get("filed_at"),
                        source_closet=d.get("id"),
                    )
                    updated.append(f"{subject} uses {obj}")

    return updated


def consolidate_daily(wing=None, dry_run=False):
    """执行每日整合"""
    config = get_config()
    collection = get_collection(str(GLOBAL_CHROMA))
    kg = KnowledgeGraph()

    # 1. 获取今天的 drawers
    today_drawers = get_today_drawers(collection, wing)

    if not today_drawers:
        return {
            "status": "no_drawers",
            "message": "今天没有新的记忆"
        }

    # 2. 识别重复
    duplicates = identify_duplicates(today_drawers)

    # 3. 识别冲突
    conflicts = identify_conflicts(today_drawers, kg)

    # 4. 生成摘要
    summary = generate_daily_summary(today_drawers, wing)

    # 5. 合并相似记忆
    merged = merge_similar_drawers(collection, duplicates, dry_run)

    # 6. 更新知识图谱
    kg_updates = update_knowledge_graph(today_drawers, kg)

    # 7. 生成报告
    report = {
        "status": "success",
        "date": datetime.now(timezone.utc).isoformat(),
        "wing": wing or "global",
        "summary": summary,
        "duplicates": {
            "count": len(duplicates),
            "items": duplicates[:5]  # 只返回前 5 个
        },
        "conflicts": {
            "count": len(conflicts),
            "items": conflicts
        },
        "merged": {
            "count": len(merged),
            "items": merged[:5]
        },
        "kg_updates": {
            "count": len(kg_updates),
            "items": kg_updates[:10]
        },
        "dry_run": dry_run
    }

    # 8. 保存每日摘要到 daily_summaries room
    if not dry_run:
        summary_content = f"""# 每日记忆整合报告

日期: {report['date']}
项目: {report['wing']}

## 统计
- 总记忆数: {summary['total_drawers']}
- 重复记忆: {len(duplicates)}
- 冲突记忆: {len(conflicts)}
- 知识图谱更新: {len(kg_updates)}

## 按类别分布
{chr(10).join(f'- {room}: {count}' for room, count in summary['by_room'].items())}

## 关键事实
{chr(10).join(f'- {fact}' for fact in summary['key_facts'][:5])}

## 决策记录
{chr(10).join(f'- {dec}' for dec in summary['decisions'][:5])}

## 错误模式
{chr(10).join(f'- {err}' for err in summary['errors'][:5])}
"""

        add_drawer(
            collection=collection,
            wing=wing or "global",
            room="daily_summaries",
            content=summary_content,
            source_file=f"consolidation_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            chunk_index=0,
            added_by="consolidation",
        )

    return report


if __name__ == "__main__":
    import json

    # 测试运行
    result = consolidate_daily(dry_run=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
