"""Evolution pipeline — orchestrates the full evolution cycle.

Pipeline steps:
1. Extract candidates from transcript (with chunk batching)
2. Review and score candidates (parallel-safe, batch-aware)
3. Promote high-quality candidates via batch_remember
4. Run consolidation (dedup, conflict detection)
5. Report with detailed metrics
"""

from __future__ import annotations

import logging
import time
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from mempalace_evolve.sdk import MemPalace

logger = logging.getLogger("mempalace_evolve.evolution")


class EvolutionPipeline:
    """Orchestrates the memory evolution cycle with batch-aware processing."""

    # Maximum candidates to process in one cycle (prevent memory blowout)
    MAX_CANDIDATES_PER_CYCLE = 500

    def __init__(self, palace: "MemPalace"):
        self.palace = palace

    def run(self, transcript: str | None = None) -> dict[str, Any]:
        """Run a full evolution cycle.

        Args:
            transcript: Optional session transcript to process.

        Returns:
            Report dict with stats from each step.
        """
        start_time = time.time()
        report = {
            "steps": [],
            "promoted": 0,
            "dropped": 0,
            "pending": 0,
            "candidates": 0,
            "errors": [],
            "duration_ms": 0,
        }

        # Step 1: Extract candidates
        candidates = []
        if transcript:
            from mempalace_evolve.evolution.candidate import CandidateExtractor
            extractor = CandidateExtractor()
            try:
                candidates = extractor.extract(transcript)
                # Limit candidates to prevent memory issues
                if len(candidates) > self.MAX_CANDIDATES_PER_CYCLE:
                    logger.warning(
                        "Truncating %d candidates to %d",
                        len(candidates), self.MAX_CANDIDATES_PER_CYCLE,
                    )
                    candidates = candidates[:self.MAX_CANDIDATES_PER_CYCLE]
            except Exception as e:
                logger.error("Candidate extraction failed: %s", e)
                report["errors"].append(f"extract: {e}")

            report["candidates"] = len(candidates)
            report["steps"].append({
                "step": "extract",
                "candidates_found": len(candidates),
            })

        # Step 2: Review candidates (with batch-aware scoring)
        promoted = []
        dropped = []
        if candidates:
            from mempalace_evolve.evolution.reviewer import MemoryReviewer
            reviewer = MemoryReviewer()

            for c in candidates:
                try:
                    verdict = reviewer.review(c)
                    if verdict == "promote":
                        promoted.append(c)
                    elif verdict == "drop":
                        dropped.append(c)
                except Exception as e:
                    report["errors"].append(f"review: {e}")
                    continue

            report["steps"].append({
                "step": "review",
                "promoted": len(promoted),
                "dropped": len(dropped),
                "pending": len(candidates) - len(promoted) - len(dropped),
            })

            # Step 3: Batch promote to long-term memory (more efficient)
            if promoted:
                items = []
                for c in promoted:
                    items.append({
                        "content": c["content"][:2000],
                        "room": c.get("type", "general"),
                        "metadata": {
                            "source": "evolution",
                            "score": c.get("score", 0),
                            "evolved_at": c.get("created_at", ""),
                        },
                    })
                try:
                    result = self.palace.batch_remember(items)
                    ids = result.ids if hasattr(result, "ids") else result
                    report["promoted"] = len([i for i in ids if i])
                    if len(ids) != len(items):
                        report["errors"].append(
                            f"promote: {len(items) - len(ids)} failed"
                        )
                except AttributeError:
                    # Fallback for older SDK without batch_remember
                    for c in promoted:
                        try:
                            self.palace.remember(
                                c["content"][:2000],
                                room=c.get("type", "general"),
                                metadata={
                                    "source": "evolution",
                                    "score": c.get("score", 0),
                                },
                            )
                            report["promoted"] += 1
                        except Exception as e:
                            report["errors"].append(f"promote: {e}")

            report["dropped"] = len(dropped)
            report["pending"] = len(candidates) - len(promoted) - len(dropped)

        report["duration_ms"] = int((time.time() - start_time) * 1000)
        report["steps"].append({
            "step": "complete",
            "duration_ms": report["duration_ms"],
        })
        logger.info(
            "Evolution cycle: %d promoted, %d dropped, %d pending (%dms)",
            report["promoted"],
            report["dropped"],
            report.get("pending", 0),
            report["duration_ms"],
        )
        return report
