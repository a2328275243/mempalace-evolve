"""Spaced repetition scheduler — schedule and retrieve memories for review.

This module implements a spaced repetition system where memories are reviewed
at increasing intervals: 1d → 3d → 7d → 14d → 30d → 60d.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger("mempalace_evolve.core.spaced_repetition")

# Review intervals in days
REVIEW_INTERVALS = [1, 3, 7, 14, 30, 60, 90]

# Minimum recall count before a memory becomes eligible for spaced repetition
MIN_RECALL_COUNT = 2


def calculate_next_review(last_reviewed: str | None, current_interval_index: int) -> str:
    """Calculate the next review date based on current interval.

    Args:
        last_reviewed: ISO timestamp of last review (or creation if never reviewed).
        current_interval_index: Index into REVIEW_INTERVALS (0 = 1 day).

    Returns:
        ISO timestamp of next review date.
    """
    if current_interval_index >= len(REVIEW_INTERVALS):
        current_interval_index = len(REVIEW_INTERVALS) - 1

    interval_days = REVIEW_INTERVALS[current_interval_index]

    if last_reviewed:
        try:
            last_dt = datetime.fromisoformat(last_reviewed.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            last_dt = datetime.now(timezone.utc)
    else:
        last_dt = datetime.now(timezone.utc)

    next_dt = last_dt + timedelta(days=interval_days)
    return next_dt.isoformat()


def get_interval_index(interval_str: str | None) -> int:
    """Parse interval string to index, defaulting to 0 if invalid."""
    if not interval_str:
        return 0
    try:
        idx = int(interval_str)
        return max(0, min(idx, len(REVIEW_INTERVALS) - 1))
    except (ValueError, TypeError):
        return 0


def get_memories_due_for_review(collection, wing: str, as_of: datetime | None = None) -> list[dict]:
    """Find all memories due for review.

    Args:
        collection: ChromaDB collection.
        wing: Wing to search in.
        as_of: Reference time (default: now).

    Returns:
        List of memory dicts with review metadata.
    """
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
    now_ts = as_of.isoformat()

    for i, doc_id in enumerate(data["ids"]):
        meta = data["metadatas"][i] if data.get("metadatas") else {}

        # Skip memories that haven't been recalled enough
        recall_count = meta.get("recall_count", 0)
        if recall_count < MIN_RECALL_COUNT:
            continue

        # Check if due for review
        next_review = meta.get("next_review")
        if not next_review:
            # First-time review after enough recalls
            due_memories.append({
                "id": doc_id,
                "content": data["documents"][i],
                "room": meta.get("room", "general"),
                "interval_index": 0,
                "last_reviewed": meta.get("filed_at"),
                "recall_count": recall_count,
            })
            continue

        # Parse next_review and compare with now
        try:
            review_dt = datetime.fromisoformat(next_review.replace("Z", "+00:00"))
            if review_dt <= as_of:
                interval_idx = get_interval_index(meta.get("interval_index"))
                due_memories.append({
                    "id": doc_id,
                    "content": data["documents"][i],
                    "room": meta.get("room", "general"),
                    "interval_index": interval_idx,
                    "last_reviewed": next_review,
                    "recall_count": recall_count,
                })
        except (ValueError, AttributeError):
            continue

    return due_memories


def mark_reviewed(collection, drawer_id: str, interval_index: int) -> bool:
    """Mark a memory as reviewed and schedule next review.

    Args:
        collection: ChromaDB collection.
        drawer_id: ID of the memory.
        interval_index: Current interval index (0-based).

    Returns:
        True if successful.
    """
    try:
        data = collection.get(ids=[drawer_id], include=["metadatas"])
        if not data or not data.get("metadatas"):
            return False

        meta = data["metadatas"][0]
        next_interval = min(interval_index + 1, len(REVIEW_INTERVALS) - 1)
        next_review = calculate_next_review(None, next_interval)

        meta["interval_index"] = str(next_interval)
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
    """Snooze a memory for a few days.

    Args:
        collection: ChromaDB collection.
        drawer_id: ID of the memory.
        days: Days to snooze (default 1).

    Returns:
        True if successful.
    """
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