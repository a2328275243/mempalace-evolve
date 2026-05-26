"""Memory reviewer — score and classify candidates for promotion.

Extracted from memory_review.py, made agent-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("mempalace_evolve.evolution")

# Boilerplate patterns to penalize
BOILERPLATE = [
    "template", "placeholder", "todo", "fixme",
    "lorem ipsum", "example", "sample",
]


class MemoryReviewer:
    """Review memory candidates and decide: promote, drop, or archive."""

    def __init__(
        self,
        promote_threshold: int = 7,
        drop_threshold: int = 3,
        max_age_days: int = 7,
    ):
        self.promote_threshold = promote_threshold
        self.drop_threshold = drop_threshold
        self.max_age_days = max_age_days

    def review(self, candidate: dict[str, Any]) -> str:
        """Review a single candidate.

        Returns:
            "promote", "drop", or "pending"
        """
        score = self.score(candidate)
        if score >= self.promote_threshold:
            return "promote"
        if score < self.drop_threshold:
            return "drop"
        return "pending"

    def score(self, candidate: dict[str, Any]) -> int:
        """Score a candidate (0-10)."""
        score = candidate.get("score", 5)
        content = candidate.get("content", "")

        # Substance check
        if not self._has_substance(content):
            return 0

        # Boilerplate penalty
        lower = content.lower()
        if any(bp in lower for bp in BOILERPLATE):
            score -= 2

        # Type bonus
        ctype = candidate.get("type", "general")
        if ctype in ("decision", "error_pattern", "architecture"):
            score += 1

        # Length bonus
        if len(content) > 100:
            score += 1

        return max(0, min(10, score))

    def _has_substance(self, content: str) -> bool:
        """Check if content has real substance (not just filler)."""
        if len(content) < 20:
            return False
        words = content.split()
        if len(words) < 5:
            return False
        # Check for actual information density
        unique_words = set(w.lower() for w in words)
        if len(unique_words) / len(words) < 0.3:
            return False
        return True
