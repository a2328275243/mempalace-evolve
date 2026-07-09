"""Similarity deduplication — check for similar memories before storing.

This module computes semantic similarity between new content and existing
memories in the palace. If similarity exceeds a threshold, the new memory
is either rejected or merged with the existing one.
"""

from __future__ import annotations

import functools
import logging
import re
from typing import Any

logger = logging.getLogger("mempalace_evolve.core.dedup")

# Default similarity threshold (0.0 - 1.0)
DEFAULT_SIMILARITY_THRESHOLD = 0.85

# Minimum content length to check
MIN_CONTENT_LENGTH = 20


@functools.lru_cache(maxsize=512)
def text_overlap_similarity(text_a: str, text_b: str, min_overlap_ratio: float = 0.3) -> float:
    """Stage-2 semantic text overlap check using word overlap + Jaccard.

    This is a fast, deterministic fallback that confirms/disconfirms
    vector distance matches by measuring word-level overlap.

    Args:
        text_a: First text.
        text_b: Second text.
        min_overlap_ratio: Minimum ratio of shared words needed.

    Returns:
        Overlap score 0.0-1.0 (Jaccard * word presence bonus).
    """
    if not text_a or not text_b:
        return 0.0

    def tokenize(s: str) -> set[str]:
        normalized = s.lower()
        latin_tokens = re.findall(r"[a-z0-9]+", normalized)
        cjk_tokens = re.findall(r"[\u4e00-\u9fff]", normalized)
        return set(latin_tokens + cjk_tokens)

    tokens_a = tokenize(text_a)
    tokens_b = tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    jaccard = len(intersection) / len(union) if union else 0.0

    # Boost if one is mostly contained in the other
    containment = len(intersection) / min(len(tokens_a), len(tokens_b))

    # Weighted combination: 40% Jaccard + 60% containment
    score = 0.4 * jaccard + 0.6 * containment
    if containment < min_overlap_ratio:
        return min(score, containment)
    return min(1.0, score)



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
            # Stage 2: text overlap verification (reduce false positives)
            existing_content = results["documents"][0][i]
            overlap_score = text_overlap_similarity(content, existing_content)
            if overlap_score < 0.15:
                # Low text overlap despite high vector distance ? likely false positive
                continue
            # Combined score: weighted average of vector similarity and text overlap
            combined_similarity = round(0.6 * similarity + 0.4 * overlap_score, 3)
            if combined_similarity < threshold:
                continue
            similar.append({
                "id": doc_id,
                "content": existing_content,
                "room": results["metadatas"][0][i].get("room", "general"),
                "similarity": combined_similarity,
                "distance": distance,
                "text_overlap": round(overlap_score, 3),
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
