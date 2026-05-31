"""Similarity deduplication — check for similar memories before storing.

This module computes semantic similarity between new content and existing
memories in the palace. If similarity exceeds a threshold, the new memory
is either rejected or merged with the existing one.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("mempalace_evolve.core.dedup")

# Default similarity threshold (0.0 - 1.0)
DEFAULT_SIMILARITY_THRESHOLD = 0.85

# Minimum content length to check
MIN_CONTENT_LENGTH = 20


def find_similar_memories(
    collection,
    wing: str,
    content: str,
    room: str | None = None,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find memories similar to the given content.

    Args:
        collection: ChromaDB collection.
        wing: Wing to search in.
        content: New content to compare.
        room: Optional room filter.
        threshold: Minimum similarity to return.
        limit: Max number of results.

    Returns:
        List of similar memory dicts with similarity scores.
    """
    if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
        return []

    # Build query filter
    where = {"wing": wing}
    if room:
        where["room"] = room

    try:
        # Use ChromaDB's native where filter
        results = collection.query(
            query_texts=[content],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.debug("Similarity query failed: %s", e)
        return []

    if not results or not results.get("ids"):
        return []

    similar = []
    for i, doc_id in enumerate(results["ids"][0]):
        distance = results["distances"][0][i]
        # Convert distance to similarity (1 - distance, clipped to 0-1)
        similarity = max(0.0, min(1.0, 1.0 - distance))

        if similarity >= threshold:
            similar.append({
                "id": doc_id,
                "content": results["documents"][0][i],
                "room": results["metadatas"][0][i].get("room", "general"),
                "similarity": round(similarity, 3),
                "distance": distance,
            })

    return similar


def check_and_deduplicate(
    collection,
    wing: str,
    content: str,
    room: str = "general",
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    action: str = "skip",  # "skip", "merge", "allow"
) -> dict[str, Any]:
    """Check for similar memories and decide what to do.

    Args:
        collection: ChromaDB collection.
        wing: Wing to search in.
        content: New content to store.
        room: Room to check in.
        threshold: Similarity threshold.
        action: What to do if similar found ("skip", "merge", "allow").

    Returns:
        Dict with decision and details.
    """
    if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
        return {"action": "allow", "reason": "content too short", "similar": []}

    similar = find_similar_memories(
        collection=collection,
        wing=wing,
        content=content,
        room=room,
        threshold=threshold,
    )

    if not similar:
        return {"action": "allow", "reason": "no similar found", "similar": []}

    # Found similar memories
    best_match = similar[0]  # Already sorted by similarity

    if action == "skip":
        return {
            "action": "skip",
            "reason": f"similarity {best_match['similarity']:.2f} >= {threshold}",
            "similar": similar,
            "matched_id": best_match["id"],
        }

    if action == "merge":
        # Return merge info (caller should update the existing memory)
        return {
            "action": "merge",
            "reason": f"similarity {best_match['similarity']:.2f} >= {threshold}",
            "similar": similar,
            "matched_id": best_match["id"],
            "matched_content": best_match["content"],
        }

    # action == "allow" — store anyway
    return {
        "action": "allow",
        "reason": f"similar found but action={action}",
        "similar": similar,
    }


def merge_similar_content(existing: str, new: str) -> str:
    """Merge two similar memories into one.

    Uses a simple strategy: keep the longer, more detailed version,
    but append unique parts from the new one.

    Args:
        existing: Existing memory content.
        new: New memory content.

    Returns:
        Merged content string.
    """
    # Keep the longer one as base
    if len(new) > len(existing):
        base, addon = new, existing
    else:
        base, addon = existing, new

    # Simple merge: append new info if substantially different
    if addon.lower() not in base.lower():
        # Add a separator and the new content
        merged = f"{base}\n\n---\n{addon}"
        # Truncate if too long
        if len(merged) > 2000:
            merged = merged[:1997] + "..."
        return merged

    return base