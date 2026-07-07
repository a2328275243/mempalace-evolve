"""Spaced repetition scheduler — schedule and retrieve memories for review.

Uses an FSRS-inspired adaptive model where intervals grow exponentially
based on recall count:
  interval = INITIAL_INTERVAL * STABILITY_FACTOR ** (recall_count - 1)

This replaces the old fixed-interval table [1, 3, 7, 14, 30, 60, 90]
with a smoother, more personalised curve.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("mempalace_evolve.core.spaced_repetition")

# FSRS-inspired adaptive parameters
INITIAL_INTERVAL_DAYS = 1.0
STABILITY_FACTOR = 1.8
MAX_INTERVAL_DAYS = 365.0

# Minimum recall count before a memory becomes eligible for spaced repetition
MIN_RECALL_COUNT = 2

# Cache computed intervals (recall_count is usually small)
_INTERVAL_CACHE: dict[int, float] = {}
_INTERVAL_CACHE_MAX = 1000


def _compute_interval(recall_count: int) -> float:
    """Compute the next review interval in days using the adaptive formula."""
    if recall_count < 1:
        return INITIAL_INTERVAL_DAYS
    cached = _INTERVAL_CACHE.get(recall_count)
    if cached is not None:
        return cached
    raw = INITIAL_INTERVAL_DAYS * (STABILITY_FACTOR ** (recall_count - 1))
    result = min(raw, MAX_INTERVAL_DAYS)
    if len(_INTERVAL_CACHE) < _INTERVAL_CACHE_MAX:
        _INTERVAL_CACHE[recall_count] = result
    return result


def calculate_next_review(last_reviewed: str | None, recall_count: int) -> str:
    """Calculate the next review date based on current interval."""
    interval_days = _compute_interval(recall_count)
    if last_reviewed:
        try:
            last_dt = datetime.fromisoformat(last_reviewed.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            last_dt = datetime.now(timezone.utc)
    else:
        last_dt = datetime.now(timezone.utc)
    next_dt = last_dt + timedelta(days=interval_days)
    return next_dt.isoformat()


def get_interval_days(interval_str: str | None, recall_count: int = 0) -> float:
    """Parse stored interval string to days, falling back to adaptive calculation."""
    if interval_str:
        try:
            return min(float(interval_str), MAX_INTERVAL_DAYS)
        except (ValueError, TypeError):
            pass
    return _compute_interval(recall_count)


def get_memories_due_for_review(collection, wing: str, as_of: datetime | None = None) -> list[dict]:
    """Find all memories due for review."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    try:
        data = collection.get(
            where={"wing": wing},
            include=["documents", "metadatas"],
        )
    except Exception:
        return []

    if not data or not data.get("ids"):
        return []

    due_memories = []

    for i, doc_id in enumerate(data["ids"]):
        meta = data["metadatas"][i] if data.get("metadatas") else {}

        recall_count = meta.get("recall_count", 0)
        if recall_count < MIN_RECALL_COUNT:
            continue

        next_review = meta.get("next_review")
        if not next_review:
            due_memories.append({
                "id": doc_id,
                "content": data["documents"][i],
                "room": meta.get("room", "general"),
                "interval_days": INITIAL_INTERVAL_DAYS,
                "last_reviewed": meta.get("filed_at"),
                "recall_count": recall_count,
            })
            continue

        try:
            review_dt = datetime.fromisoformat(next_review.replace("Z", "+00:00"))
            if review_dt <= as_of:
                recall_count = meta.get("recall_count", 0)
                interval_days = get_interval_days(meta.get("interval_days"), recall_count)
                due_memories.append({
                    "id": doc_id,
                    "content": data["documents"][i],
                    "room": meta.get("room", "general"),
                    "interval_days": interval_days,
                    "last_reviewed": next_review,
                    "recall_count": recall_count,
                })
        except (ValueError, AttributeError):
            continue

    return due_memories


def mark_reviewed(collection, drawer_id: str, recall_count: int) -> bool:
    """Mark a memory as reviewed and schedule next review."""
    try:
        data = collection.get(ids=[drawer_id], include=["metadatas"])
        if not data or not data.get("metadatas"):
            return False

        meta = data["metadatas"][0]
        new_recall_count = (meta.get("recall_count", 0) or 0) + 1
        next_review = calculate_next_review(None, new_recall_count)

        meta["interval_days"] = str(_compute_interval(new_recall_count))
        meta["next_review"] = next_review
        meta["last_reviewed"] = datetime.now(timezone.utc).isoformat()
        meta["review_count"] = meta.get("review_count", 0) + 1

        collection.update(ids=[drawer_id], metadatas=[meta])
        logger.debug("Marked %s reviewed, next review: %s", drawer_id[:12], next_review)
        return True
    except Exception as e:
        logger.debug("Failed to mark reviewed: %s", e)
        return False


def snooze(collection, drawer_id: str, days: int = 1) -> bool:
    """Snooze a memory for a few days."""
    try:
        data = collection.get(ids=[drawer_id], include=["metadatas"])
        if not data or not data.get("metadatas"):
            return False

        meta = data["metadatas"][0]
        new_review = datetime.now(timezone.utc) + timedelta(days=days)
        meta["next_review"] = new_review.isoformat()

        collection.update(ids=[drawer_id], metadatas=[meta])
        return True
    except Exception:
        return False
