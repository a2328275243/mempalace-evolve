"""Memory importance auto-scoring — compute and update memory importance scores.

This module analyzes memories based on:
1. Recall frequency (how often it's retrieved)
2. Knowledge graph centrality (how many KG relations point to it)
3. Access recency (when it was last accessed)
4. Cross-wing hits (used by multiple projects)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("mempalace_evolve.core.importance_scorer")

# Score components weights (sum = 1.0)
WEIGHTS = {
    "recall_frequency": 0.30,    # How often recalled
    "kg_centrality": 0.25,       # Knowledge graph connections
    "recency": 0.20,             # Recently accessed
    "cross_wing_hits": 0.15,     # Used by multiple projects
    "content_quality": 0.10,     # Content-based signals (length, keywords)
}

# Recency half-life in days
RECENCY_HALF_LIFE_DAYS = 30


def compute_importance_score(
    recall_count: int,
    kg_degree: int,
    last_accessed: str | None,
    cross_wing_hits: int,
    content: str,
) -> float:
    """Compute overall importance score (0.0 - 1.0).

    Args:
        recall_count: Number of times the memory was recalled.
        kg_degree: Number of KG relations (incoming + outgoing).
        last_accessed: ISO timestamp of last access.
        cross_wing_hits: Number of different wings that recalled this.
        content: Memory text content.

    Returns:
        Score between 0.0 and 1.0.
    """
    # 1. Recall frequency score (normalized by max expected recalls)
    recall_score = min(recall_count / 10.0, 1.0) * WEIGHTS["recall_frequency"]

    # 2. KG centrality score
    kg_score = min(kg_degree / 5.0, 1.0) * WEIGHTS["kg_centrality"]

    # 3. Recency score (exponential decay)
    recency_score = _compute_recency_score(last_accessed) * WEIGHTS["recency"]

    # 4. Cross-wing hits score
    cross_score = min(cross_wing_hits / 3.0, 1.0) * WEIGHTS["cross_wing_hits"]

    # 5. Content quality score
    quality_score = _compute_content_score(content) * WEIGHTS["content_quality"]

    return recall_score + kg_score + recency_score + cross_score + quality_score


def _compute_recency_score(last_accessed: str | None) -> float:
    """Compute recency score using exponential decay."""
    if not last_accessed:
        return 0.0  # Never accessed

    try:
        last_dt = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return 0.0

    now = datetime.now(timezone.utc)
    days_ago = (now - last_dt).total_seconds() / 86400

    if days_ago < 0:
        days_ago = 0

    # Exponential decay: score = e^(-ln(2) * days / half_life)
    import math
    decay = math.exp(-math.log(2) * days_ago / RECENCY_HALF_LIFE_DAYS)
    return min(max(decay, 0.0), 1.0)


def _compute_content_score(content: str) -> float:
    """Compute content quality score based on signals."""
    if not content:
        return 0.0

    score = 0.0

    # Length bonus (substantial content)
    length = len(content)
    if length > 100:
        score += 0.3
    if length > 500:
        score += 0.2
    if length > 1000:
        score += 0.1

    # Keyword signals of important content
    important_keywords = [
        "important", "remember", "critical", "decision",
        "architecture", "design pattern", "security",
        "error", "bug", "fix", "workaround",
        "config", "setup", "install",
    ]
    content_lower = content.lower()
    keyword_matches = sum(1 for kw in important_keywords if kw in content_lower)
    score += min(keyword_matches * 0.15, 0.4)

    return min(score, 1.0)


def score_all_memories(palace) -> dict[str, Any]:
    """Score all memories in the palace.

    Args:
        palace: MemPalace instance.

    Returns:
        Dict with scores and stats.
    """
    collection = palace._get_collection()
    if not collection:
        return {"scored": 0, "errors": ["collection unavailable"]}

    try:
        data = collection.get(
            where={"wing": palace._wing},
            include=["documents", "metadatas"],
        )
    except Exception as e:
        return {"scored": 0, "errors": [str(e)]}

    if not data or not data.get("ids"):
        return {"scored": 0, "scores": []}

    # Get KG entity degrees
    kg = palace._get_kg()
    scores = []
    scored_count = 0

    for i, doc_id in enumerate(data["ids"]):
        meta = data["metadatas"][i] if data.get("metadatas") else {}
        content = data["documents"][i]

        recall_count = meta.get("recall_count", 0)
        cross_wing_hits = meta.get("cross_wing_hits", 0)
        last_accessed = meta.get("last_accessed")

        # Get KG degree for this entity (using content hash as proxy)
        entity_name = content[:50].strip()
        kg_degree = 0
        try:
            outgoing = kg.query_entity(entity_name, direction="outgoing")
            incoming = kg.query_entity(entity_name, direction="incoming")
            kg_degree = len(outgoing) + len(incoming)
        except Exception:
            pass

        score = compute_importance_score(
            recall_count=recall_count,
            kg_degree=kg_degree,
            last_accessed=last_accessed,
            cross_wing_hits=cross_wing_hits,
            content=content,
        )

        # Update metadata with score
        meta["importance_score"] = round(score, 3)
        try:
            collection.update(ids=[doc_id], metadatas=[meta])
            scored_count += 1
        except Exception:
            pass

        scores.append({
            "id": doc_id,
            "score": round(score, 3),
            "recall_count": recall_count,
            "kg_degree": kg_degree,
        })

    return {
        "scored": scored_count,
        "scores": sorted(scores, key=lambda x: x["score"], reverse=True),
    }


def get_top_memories(palace, n: int = 10) -> list[dict]:
    """Get top N most important memories.

    Args:
        palace: MemPalace instance.
        n: Number of memories to return.

    Returns:
        List of top memory dicts.
    """
    result = score_all_memories(palace)
    return result.get("scores", [])[:n]