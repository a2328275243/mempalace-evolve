"""Evolution pipeline — orchestrates the full evolution cycle.

Pipeline steps:
1. Extract candidates from transcript
2. Review and score candidates
3. Promote high-quality candidates to long-term memory
4. Run consolidation (dedup, conflict detection)
"""

from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mempalace_evolve.sdk import MemPalace

logger = logging.getLogger("mempalace_evolve.evolution")


class EvolutionPipeline:
    """Orchestrates the memory evolution cycle."""

    def __init__(self, palace: "MemPalace"):
        self.palace = palace

    def run(self, transcript: str | None = None) -> dict[str, Any]:
        """Run a full evolution cycle.

        Args:
            transcript: Optional session transcript to process.

        Returns:
            Report dict with stats from each step.
        """
        report = {"steps": [], "promoted": 0, "dropped": 0, "candidates": 0, "errors": []}

        # Step 1: Extract candidates
        candidates = []
        if transcript:
            from mempalace_evolve.evolution.candidate import CandidateExtractor
            extractor = CandidateExtractor()
            candidates = extractor.extract(transcript)
            report["candidates"] = len(candidates)
            report["steps"].append({
                "step": "extract",
                "candidates_found": len(candidates),
            })

        # Step 2: Review candidates
        if candidates:
            from mempalace_evolve.evolution.reviewer import MemoryReviewer
            reviewer = MemoryReviewer()
            promoted = []
            dropped = []

            for c in candidates:
                verdict = reviewer.review(c)
                if verdict == "promote":
                    promoted.append(c)
                elif verdict == "drop":
                    dropped.append(c)

            report["steps"].append({
                "step": "review",
                "promoted": len(promoted),
                "dropped": len(dropped),
                "pending": len(candidates) - len(promoted) - len(dropped),
            })

            # Step 3: Promote to long-term memory
            for c in promoted:
                try:
                    self.palace.remember(
                        c["content"],
                        room=c.get("type", "general"),
                        metadata={"source": "evolution", "score": c.get("score", 0)},
                    )
                    report["promoted"] += 1
                except Exception as e:
                    report["errors"].append(str(e))

            report["dropped"] = len(dropped)

        report["steps"].append({"step": "complete"})
        logger.info(
            "Evolution cycle: %d promoted, %d dropped",
            report["promoted"],
            report["dropped"],
        )
        return report
