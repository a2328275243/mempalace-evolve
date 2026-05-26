#!/usr/bin/env python3
"""
adaptive_scorer.py — 自适应评分模块
====================================
根据向量搜索结果的质量动态调整评分置信度。
f_dist: 距离质量（top-1 结果的余弦距离好坏）
f_gap: 区分度（top-1 和 top-2 之间的差距）

适配自 M-flow 的 adaptive_scoring.py，简化为单 collection 场景。
"""

import math


def compute_confidence(distances: list) -> dict:
    """
    从 ChromaDB 余弦距离列表计算置信度。

    Args:
        distances: 余弦距离列表 (0=完全相同, 2=完全相反)

    Returns:
        {
            "f_dist": float,    # 0-1, 距离质量
            "f_gap": float,     # 0-1, 区分度
            "confidence": float, # f_dist * f_gap
            "suggested_threshold": float  # 建议的相似度阈值
        }
    """
    if not distances:
        return {
            "f_dist": 0.0,
            "f_gap": 0.0,
            "confidence": 0.0,
            "suggested_threshold": 0.7,
        }

    top1 = distances[0]

    # f_dist: 距离质量，距离越小越好
    # ChromaDB cosine distance: 0 = 相同, ~0.5 = 相似, ~1.0 = 无关
    if top1 < 0.3:
        f_dist = 1.0
    elif top1 < 0.6:
        f_dist = 1.0 - (top1 - 0.3) / 0.3 * 0.3  # 1.0 -> 0.7
    elif top1 < 1.0:
        f_dist = 0.7 - (top1 - 0.6) / 0.4 * 0.4  # 0.7 -> 0.3
    else:
        f_dist = max(0.1, 0.3 - (top1 - 1.0) * 0.3)

    # f_gap: 区分度，top1 和 top2 的差距
    if len(distances) >= 2:
        gap = max(0, distances[1] - distances[0])
        if gap > 0.15:
            f_gap = 1.0
        elif gap > 0.05:
            f_gap = 0.6 + (gap - 0.05) / 0.10 * 0.4
        elif gap > 0.01:
            f_gap = 0.2 + (gap - 0.01) / 0.04 * 0.4
        else:
            f_gap = 0.2
    else:
        f_gap = 1.0  # 只有一个结果，假设高区分度

    confidence = f_dist * f_gap

    # 动态阈值：高置信度时严格，低置信度时宽松
    base_threshold = 0.7
    suggested = base_threshold + (confidence - 0.5) * 0.2
    suggested = max(0.5, min(0.9, suggested))

    return {
        "f_dist": round(f_dist, 4),
        "f_gap": round(f_gap, 4),
        "confidence": round(confidence, 4),
        "suggested_threshold": round(suggested, 4),
    }


def adjust_scores(results: list, confidence: dict) -> list:
    """
    根据置信度调整搜索结果分数。

    高置信度 -> 保持原始排序（top 结果可靠）
    低置信度 -> 压缩分数向均值靠拢（区分度不够）

    Args:
        results: search_raw 返回的结果列表
        confidence: compute_confidence 的返回值

    Returns:
        调整后的结果列表（按 adjusted_similarity 排序）
    """
    if not results:
        return results

    conf = confidence.get("confidence", 0.5)

    # 计算均值相似度
    similarities = [r.get("similarity", 0) for r in results]
    if not similarities:
        return results

    mean_sim = sum(similarities) / len(similarities)

    for r in results:
        sim = r.get("similarity", 0)
        # 置信度加权：高置信度保持原值，低置信度向均值收缩
        adjusted = sim * conf + mean_sim * (1 - conf)
        r["adjusted_similarity"] = round(adjusted, 4)

    # 按 adjusted_similarity 降序排序
    results.sort(key=lambda x: -x.get("adjusted_similarity", 0))
    return results


# ---------------------------------------------------------------------------
# Per-Wing 自适应基线（适配自 M-flow 的 per-collection baselines）
# ---------------------------------------------------------------------------

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("mempalace.adaptive_scorer")

_BASELINES_PATH = Path(__file__).parent / ".adaptive_baselines.json"

# 内存缓存，避免每次搜索都读磁盘
_baselines_cache = None
_baselines_mtime = 0.0


def _load_baselines() -> dict:
    """加载历史距离基线（带内存缓存）"""
    global _baselines_cache, _baselines_mtime
    try:
        current_mtime = _BASELINES_PATH.stat().st_mtime if _BASELINES_PATH.exists() else 0.0
        if _baselines_cache is not None and current_mtime == _baselines_mtime:
            return _baselines_cache
        if _BASELINES_PATH.exists():
            data = json.loads(_BASELINES_PATH.read_text(encoding="utf-8"))
            _baselines_cache = data
            _baselines_mtime = current_mtime
            return data
    except Exception:
        logger.debug("failed to load adaptive baselines", exc_info=True)
    return {}


def _save_baselines(baselines: dict):
    """保存历史距离基线（原子写入，同时更新内存缓存）"""
    global _baselines_cache, _baselines_mtime
    try:
        from mempalace_evolve.core.config import atomic_write_json
        atomic_write_json(_BASELINES_PATH, baselines, ensure_ascii=False, indent=2)
        _baselines_cache = baselines
        try:
            _baselines_mtime = _BASELINES_PATH.stat().st_mtime
        except Exception:
            _baselines_mtime = 0.0
    except Exception:
        logger.debug("failed to save adaptive baselines", exc_info=True)


def update_wing_baseline(wing: str, distances: list):
    """
    用一次搜索结果更新 wing 的历史距离分布。
    记录 top-1 距离的滑动平均值。

    Args:
        wing: wing 名称
        distances: 本次搜索的余弦距离列表
    """
    if not distances:
        return

    baselines = _load_baselines()

    top1 = distances[0]
    entry = baselines.get(wing, {"avg_top1": 0.5, "count": 0, "avg_gap": 0.1})

    # 滑动平均（指数衰减，alpha=0.2）
    alpha = 0.2
    entry["avg_top1"] = entry["avg_top1"] * (1 - alpha) + top1 * alpha
    entry["count"] = entry.get("count", 0) + 1

    if len(distances) >= 2:
        gap = max(0, distances[1] - distances[0])
        entry["avg_gap"] = entry.get("avg_gap", 0.1) * (1 - alpha) + gap * alpha

    baselines[wing] = entry
    _save_baselines(baselines)


def get_wing_adjusted_confidence(wing: str, distances: list) -> dict:
    """
    基于 wing 历史基线调整置信度。

    稀疏 wing（高平均距离）→ 降低阈值
    密集 wing（低平均距离）→ 提高阈值

    Args:
        wing: wing 名称
        distances: 本次搜索的余弦距离列表

    Returns:
        调整后的置信度字典
    """
    base_conf = compute_confidence(distances)

    baselines = _load_baselines()
    entry = baselines.get(wing)

    if not entry or entry.get("count", 0) < 3:
        # 数据不足，使用默认值
        return base_conf

    avg_top1 = entry["avg_top1"]

    # 如果 wing 历史平均距离较高（稀疏），降低阈值使其更容易返回结果
    if avg_top1 > 0.7:
        adjustment = -0.05 * (avg_top1 - 0.7) / 0.3  # 最多降 0.05
    elif avg_top1 < 0.3:
        adjustment = 0.05 * (0.3 - avg_top1) / 0.3  # 最多升 0.05
    else:
        adjustment = 0.0

    adjusted_threshold = base_conf["suggested_threshold"] + adjustment
    adjusted_threshold = max(0.4, min(0.9, adjusted_threshold))

    base_conf["suggested_threshold"] = round(adjusted_threshold, 4)
    base_conf["wing_baseline_avg"] = round(avg_top1, 4)
    base_conf["wing_baseline_count"] = entry.get("count", 0)

    return base_conf
