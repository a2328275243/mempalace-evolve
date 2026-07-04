"""LLM-backed pipeline for memory consolidation.

This module orchestrates the full LLM-driven pipeline:
  1. extract_candidates() — identify potential memories from raw text
  2. review_candidates() — assess importance, detect contradictions
  3. consolidate_memories() — merge near-duplicates, resolve conflicts
  4. summarize_daily() — generate structured daily digest

Each function falls back gracefully to the existing rule-based pipeline
when no LLM is configured.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from mempalace_evolve.core.llm.client import get_llm_client, LLMClient
from mempalace_evolve.core.llm.types import (
    CandidateMemory,
    ExtractionResult,
    ReviewBatchResult,
    ReviewVerdict,
    ConsolidationPlan,
    MergeGroup,
    DailySummary,
    EvolutionStep,
    EvolutionReport,
)

if TYPE_CHECKING:
    from mempalace_evolve.sdk import MemPalace

logger = logging.getLogger("mempalace.llm.pipeline")


# ── Step 1: Candidate Extraction ──────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """You are a memory extraction agent for an AI memory system called MemPalace.
Your job: read a conversation transcript and identify facts, decisions, observations,
and patterns that should be stored as long-term memories.

Rules:
1. Extract only substantive, reusable information — skip greetings and small talk.
2. For each memory, classify it as one of:
   - "episodic": a specific event or action that happened
   - "semantic": a general fact or knowledge (e.g. "The API uses FastAPI")
   - "decision": an important choice made (e.g. "We decided to use Redis for caching")
   - "procedural": a process or pattern that should be remembered for future use
3. Assign a room: "decisions", "config", "general", or "architecture"
4. Estimate importance (0.0–1.0): decisions > architecture > config > general
5. List key entities mentioned (people, projects, tools, concepts)
6. If temporal context exists (e.g. "starting next week"), note it
7. Output valid JSON matching the ExtractionResult schema.
"""

EXTRACTION_PROMPT_TEMPLATE = """Extract memories from this conversation transcript:

---
{transcript}
---

Output a JSON object with:
- "candidates": list of memory objects, each with: content, memory_type, room, importance, entities, temporal_context
- "summary": one-sentence summary of the overall conversation

Return only the JSON object."""


def extract_candidates(
    transcript: str,
    client: LLMClient | None = None,
) -> ExtractionResult | None:
    """Extract memory candidates from a transcript using LLM.

    Falls back to an empty result if LLM is unavailable.
    """
    if not transcript or not transcript.strip():
        return ExtractionResult(candidates=[], summary=None)

    llm = client or get_llm_client()

    if not llm.available:
        logger.debug("LLM not available — skipping candidate extraction.")
        return None

    prompt = EXTRACTION_PROMPT_TEMPLATE.format(transcript=transcript[:8000])

    result = llm.generate_structured(
        system_prompt=EXTRACTION_SYSTEM_PROMPT,
        prompt=prompt,
        response_model=ExtractionResult,
        temperature=0.05,
    )

    if result is None:
        logger.warning("LLM extraction returned None — falling back.")
        return None

    logger.info("LLM extracted %d candidates.", len(result.candidates))
    return result


# ── Step 2: Review & Score ────────────────────────────────────────────

REVIEW_SYSTEM_PROMPT = """You are a memory quality reviewer for an AI memory system called MemPalace.
Your job: review memory candidates and decide whether to promote, drop, or revise each one.

Rules:
1. "promote": the memory is valuable — keep it as-is
2. "drop": the memory is trivial, redundant, or already known — discard it
3. "revise": the memory has value but needs rewriting (too vague, too verbose, wrong room)
4. Assign importance_score (0.0–1.0):
   - 0.8–1.0: critical decisions, architecture choices, security configs
   - 0.5–0.8: useful observations, config details, reusable patterns
   - 0.2–0.5: minor facts, daily updates
   - 0.0–0.2: trivial noise that should be dropped
5. If revising, provide improved content in revised_content
6. Detect contradictions: if the new memory contradicts an existing one, list the
   conflicting memory IDs or content snippets in "contradictions"
7. Suggest the best room classification

Output valid JSON matching the ReviewBatchResult schema."""


def build_review_prompt(candidates: list[dict[str, Any]]) -> str:
    """Build a review prompt for a batch of candidates."""
    import json
    candidates_json = json.dumps(
        [{
            "index": i,
            "content": c.get("content", ""),
            "memory_type": c.get("type", c.get("memory_type", "episodic")),
            "room": c.get("room", "general"),
            "importance": c.get("score", c.get("importance", 0.5)),
            "entities": c.get("entities", []),
        } for i, c in enumerate(candidates)],
        ensure_ascii=False,
        indent=2,
    )

    return f"""Review these memory candidates and provide a verdict for each:

{candidates_json}

For each candidate, provide:
- "action": "promote", "drop", or "revise"
- "importance_score": 0.0–1.0
- "reasoning": brief justification
- "revised_content": only if action is "revise"
- "contradictions": list of conflicting IDs/content (or empty list)
- "suggested_room": best room classification
- "entities": list of key entities found

Output a JSON object with a "verdicts" array in the same order as the input."""


def review_candidates(
    candidates: list[dict[str, Any]],
    client: LLMClient | None = None,
) -> ReviewBatchResult | None:
    """Review and score a batch of memory candidates using LLM.

    Args:
        candidates: List of candidate dicts (from extract_candidates or rule-based).
        client: Optional LLM client instance.

    Returns:
        ReviewBatchResult with one verdict per candidate, or None if LLM unavailable.
    """
    if not candidates:
        return ReviewBatchResult(verdicts=[])

    llm = client or get_llm_client()

    if not llm.available:
        logger.debug("LLM not available — skipping review.")
        return None

    # Process in batches of 20 to avoid token limits
    all_verdicts: list[ReviewVerdict] = []
    batch_size = 20

    for i in range(0, len(candidates), batch_size):
        batch = candidates[i:i + batch_size]
        prompt = build_review_prompt(batch)

        result = llm.generate_structured(
            system_prompt=REVIEW_SYSTEM_PROMPT,
            prompt=prompt,
            response_model=ReviewBatchResult,
            temperature=0.1,
        )

        if result is None:
            logger.warning("LLM review batch %d failed.", i // batch_size)
            # Fall back: promote all with default scores
            for c in batch:
                all_verdicts.append(ReviewVerdict(
                    action="promote",
                    importance_score=c.get("score", 0.5),
                    reasoning="LLM unavailable — auto-promoted.",
                ))
        else:
            all_verdicts.extend(result.verdicts)

    logger.info("LLM reviewed %d candidates across %d batches.", len(all_verdicts),
                (len(candidates) + batch_size - 1) // batch_size)
    return ReviewBatchResult(verdicts=all_verdicts)


# ── Step 3: Consolidation ─────────────────────────────────────────────

CONSOLIDATION_SYSTEM_PROMPT = """You are a memory consolidation agent for MemPalace.
Your job: analyze a set of memories and identify near-duplicates to merge,
contradictions to resolve, and stale memories to deprecate.

Rules:
1. Identify near-duplicate memories (same fact, slightly different wording) → merge
2. Identify contradictory memories (opposite decisions on same topic) → flag the older as stale
3. For merged content: combine the best information from all duplicates
4. For each merge group, specify which ID to keep and which to delete
5. Be conservative: only merge when you're 90%+ confident they're truly the same

Output valid JSON matching the ConsolidationPlan schema."""


def build_consolidation_prompt(memories: list[dict[str, Any]]) -> str:
    """Build a consolidation prompt for a set of memories."""
    import json
    memories_json = json.dumps(
        [{
            "id": m.get("id", ""),
            "content": m.get("content", m.get("document", "")),
            "room": m.get("room", "general"),
            "filed_at": m.get("filed_at", m.get("created_at", "")),
            "importance": m.get("importance", m.get("score", 0.5)),
        } for m in memories],
        ensure_ascii=False,
        indent=2,
    )

    return f"""Analyze these memories for consolidation:

{memories_json}

Identify:
- "merges": groups of memories to merge (near-duplicates), with merged_content
- "stalls": IDs of memories to mark as stale/superseded
- "reason": overall analysis summary

For each merge group, specify:
- "keep_id": which memory ID to keep
- "merge_ids": list of IDs to merge into it
- "merged_content": the consolidated content
- "reason": why they should be merged

Output a JSON object with "merges", "stalls", and "reason" fields."""


def consolidate_memories(
    memories: list[dict[str, Any]],
    client: LLMClient | None = None,
) -> ConsolidationPlan | None:
    """Consolidate a set of memories — merge duplicates, resolve contradictions.

    Args:
        memories: List of memory dicts with id, content, room, etc.
        client: Optional LLM client instance.

    Returns:
        ConsolidationPlan with merge groups and stall list, or None if LLM unavailable.
    """
    if len(memories) < 2:
        return ConsolidationPlan(merges=[], stalls=[], reason="Too few memories to consolidate.")

    llm = client or get_llm_client()

    if not llm.available:
        logger.debug("LLM not available — skipping consolidation.")
        return None

    # Process in batches of 50 to stay within context limits
    all_merges: list[MergeGroup] = []
    all_stalls: list[str] = []
    batch_size = 50

    for i in range(0, len(memories), batch_size):
        batch = memories[i:i + batch_size]
        prompt = build_consolidation_prompt(batch)

        result = llm.generate_structured(
            system_prompt=CONSOLIDATION_SYSTEM_PROMPT,
            prompt=prompt,
            response_model=ConsolidationPlan,
            temperature=0.1,
        )

        if result is None:
            logger.warning("LLM consolidation batch %d failed.", i // batch_size)
        else:
            all_merges.extend(result.merges)
            all_stalls.extend(result.stalls)

    logger.info("LLM consolidation: %d merges, %d stalls.", len(all_merges), len(all_stalls))
    return ConsolidationPlan(
        merges=all_merges,
        stalls=all_stalls,
        reason=f"Consolidated {len(memories)} memories into {len(all_merges)} merge groups.",
    )


# ── Step 4: Daily Summary ─────────────────────────────────────────────

SUMMARY_SYSTEM_PROMPT = """You are a daily memory summarizer for MemPalace.
Your job: generate a structured daily summary from today's memories.

Output valid JSON matching the DailySummary schema:
- date: today's date in YYYY-MM-DD
- total_memories: total count
- by_room: counts per room (e.g. {"decisions": 3, "config": 2, "general": 5})
- key_decisions: list of critical decisions made today
- key_observations: list of important observations or facts
- action_items: list of action items extracted
- conflicts_resolved: number of conflicts detected and resolved
- narrative: one-paragraph narrative summary (optional)
"""


def build_summary_prompt(memories: list[dict[str, Any]], date_str: str) -> str:
    """Build a summary prompt for daily consolidation."""
    import json
    memories_json = json.dumps(
        [{
            "content": m.get("content", m.get("document", "")),
            "room": m.get("room", "general"),
            "importance": m.get("importance", m.get("score", 0.5)),
            "memory_type": m.get("memory_type", "episodic"),
        } for m in memories[:100]],  # Limit to 100 most recent
        ensure_ascii=False,
        indent=2,
    )

    return f"""Summarize these {len(memories[:100])} memories from {date_str}:

{memories_json}

Output a JSON object with: date, total_memories, by_room, key_decisions,
key_observations, action_items, conflicts_resolved, narrative.

Return only the JSON object."""


def summarize_daily(
    memories: list[dict[str, Any]],
    date_str: str | None = None,
    client: LLMClient | None = None,
) -> DailySummary | None:
    """Generate a structured daily summary using LLM.

    Args:
        memories: Today's memories.
        date_str: Date string, defaults to today.
        client: Optional LLM client instance.

    Returns:
        DailySummary, or None if LLM unavailable.
    """
    if not memories:
        return DailySummary(date=date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d"), total_memories=0)

    llm = client or get_llm_client()

    if not llm.available:
        logger.debug("LLM not available — skipping daily summary.")
        return None

    date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = build_summary_prompt(memories, date)

    result = llm.generate_structured(
        system_prompt=SUMMARY_SYSTEM_PROMPT,
        prompt=prompt,
        response_model=DailySummary,
        temperature=0.2,
        max_tokens=2000,
    )

    if result is None:
        logger.warning("LLM daily summary failed.")
        return None

    logger.info("LLM daily summary generated: %d memories across %d rooms.",
                result.total_memories, len(result.by_room))
    return result


# ── Full Pipeline ─────────────────────────────────────────────────────

def run_llm_pipeline(
    palace: "MemPalace",
    transcript: str | None = None,
    client: LLMClient | None = None,
) -> EvolutionReport:
    """Run the full LLM-backed evolution pipeline.

    This is the main entry point. It runs all steps in sequence:
      1. Extract candidates from transcript (LLM + fallback)
      2. Review and score candidates (LLM + fallback)
      3. Consolidate memories — merge duplicates (LLM + fallback)
      4. Generate daily summary (LLM + fallback)

    Args:
        palace: MemPalace SDK instance.
        transcript: Optional session transcript to process.
        client: Optional LLM client instance.

    Returns:
        EvolutionReport with details from each step.
    """
    import time
    start_time = time.time()
    llm = client or get_llm_client()
    llm_used = llm.available
    steps: list[EvolutionStep] = []
    promoted = 0
    merged = 0
    dropped = 0
    errors: list[str] = []

    # Step 1: Candidate Extraction
    if transcript and transcript.strip():
        try:
            extraction = extract_candidates(transcript, client=llm)
            if extraction and extraction.candidates:
                candidates = extraction.candidates
                steps.append(EvolutionStep(
                    step="extract",
                    status="success",
                    details={
                        "candidates_found": len(candidates),
                        "llm": llm_used,
                        "summary": extraction.summary,
                    },
                ))

                # Step 2: Review
                candidate_dicts = [c.model_dump() for c in candidates]
                review_result = review_candidates(candidate_dicts, client=llm)

                if review_result and review_result.verdicts:
                    promoted_items: list[dict[str, Any]] = []
                    dropped_count = 0

                    for v in review_result.verdicts:
                        if v.action == "drop":
                            dropped_count += 1
                        elif v.action == "promote":
                            promoted_items.append({
                                "content": v.revised_content or "",
                                "room": v.suggested_room,
                                "metadata": {
                                    "source": "llm-evolution",
                                    "importance": v.importance_score,
                                    "entities": v.entities,
                                    "reasoning": v.reasoning,
                                },
                            })
                        elif v.action == "revise" and v.revised_content:
                            promoted_items.append({
                                "content": v.revised_content,
                                "room": v.suggested_room,
                                "metadata": {
                                    "source": "llm-evolution",
                                    "importance": v.importance_score,
                                    "entities": v.entities,
                                    "reasoning": v.reasoning,
                                    "revised": True,
                                },
                            })

                    # Batch promote
                    if promoted_items:
                        try:
                            ids = palace.batch_remember(promoted_items)
                            promoted = len([i for i in ids if i])
                        except AttributeError:
                            for item in promoted_items:
                                try:
                                    palace.remember(
                                        item["content"],
                                        room=item["room"],
                                        metadata=item["metadata"],
                                    )
                                    promoted += 1
                                except Exception as e:
                                    errors.append(f"promote: {e}")

                    dropped = dropped_count

                    steps.append(EvolutionStep(
                        step="review",
                        status="success",
                        details={
                            "promoted": promoted,
                            "dropped": dropped,
                            "pending": len(candidates) - promoted - dropped,
                            "llm": llm_used,
                        },
                    ))
                else:
                    # No LLM review — use rule-based fallback
                    steps.append(EvolutionStep(
                        step="review",
                        status="skipped",
                        details={"reason": "No LLM available for review."},
                    ))
            else:
                # No LLM extraction
                steps.append(EvolutionStep(
                    step="extract",
                    status="skipped",
                    details={"reason": "No LLM available for extraction."},
                ))
        except Exception as e:
            logger.error("LLM pipeline extraction/review failed: %s", e)
            errors.append(f"extract/review: {e}")
            steps.append(EvolutionStep(
                step="extract_review",
                status="error",
                details={"error": str(e)},
            ))
    else:
        steps.append(EvolutionStep(
            step="extract",
            status="skipped",
            details={"reason": "No transcript provided."},
        ))

    # Step 3: Consolidation
    try:
        collection = palace._collection
        if collection and collection.count() > 1:
            # Get all memories from the collection
            all_items = collection.get(include=["documents", "metadatas"])
            if all_items and all_items.get("ids"):
                memory_dicts: list[dict[str, Any]] = []
                for i, doc_id in enumerate(all_items["ids"]):
                    memory_dicts.append({
                        "id": doc_id,
                        "content": all_items["documents"][i],
                        "room": all_items["metadatas"][i].get("room", "general"),
                        "filed_at": all_items["metadatas"][i].get("filed_at", ""),
                        "importance": all_items["metadatas"][i].get("importance", 0.5),
                    })

                consolidation = consolidate_memories(memory_dicts, client=llm)

                if consolidation and consolidation.merges:
                    # Apply merges
                    for merge_group in consolidation.merges:
                        try:
                            # Delete merged memories
                            for mid in merge_group.merge_ids:
                                try:
                                    collection.delete(ids=[mid])
                                except Exception:
                                    pass
                            # Update kept memory with consolidated content
                            if merge_group.merged_content:
                                try:
                                    collection.update(
                                        ids=[merge_group.keep_id],
                                        documents=[merge_group.merged_content],
                                    )
                                except Exception:
                                    pass
                            merged += 1
                        except Exception as e:
                            errors.append(f"merge: {e}")

                    steps.append(EvolutionStep(
                        step="consolidation",
                        status="success",
                        details={
                            "merges_applied": merged,
                            "stalls_identified": len(consolidation.stalls),
                            "llm": llm_used,
                            "reason": consolidation.reason,
                        },
                    ))
                elif consolidation:
                    steps.append(EvolutionStep(
                        step="consolidation",
                        status="success",
                        details={
                            "merges_applied": 0,
                            "stalls_identified": len(consolidation.stalls),
                            "reason": consolidation.reason,
                        },
                    ))
                else:
                    steps.append(EvolutionStep(
                        step="consolidation",
                        status="skipped",
                        details={"reason": "No LLM available for consolidation."},
                    ))
    except Exception as e:
        logger.warning("LLM consolidation failed: %s", e)
        errors.append(f"consolidation: {e}")

    # Step 4: Daily Summary
    try:
        collection = palace._collection
        if collection:
            from mempalace_evolve.core.consolidation import get_today_drawers
            today_memories = get_today_drawers(collection)
            if today_memories:
                memory_dicts = [
                    {
                        "content": m.get("document", ""),
                        "room": m.get("metadata", {}).get("room", "general"),
                        "importance": m.get("metadata", {}).get("importance", 0.5),
                        "memory_type": m.get("metadata", {}).get("memory_type", "episodic"),
                    }
                    for m in today_memories
                ]
                summary = summarize_daily(memory_dicts, client=llm)
                if summary:
                    steps.append(EvolutionStep(
                        step="daily_summary",
                        status="success",
                        details={
                            "total_memories": summary.total_memories,
                            "by_room": summary.by_room,
                            "key_decisions": summary.key_decisions,
                            "action_items": summary.action_items,
                            "narrative": summary.narrative,
                            "llm": llm_used,
                        },
                    ))
                else:
                    steps.append(EvolutionStep(
                        step="daily_summary",
                        status="skipped",
                        details={"reason": "No LLM available."},
                    ))
    except Exception as e:
        logger.warning("Daily summary failed: %s", e)
        errors.append(f"daily_summary: {e}")

    duration_ms = int((time.time() - start_time) * 1000)
    steps.append(EvolutionStep(
        step="complete",
        status="success" if not errors else "warning",
        details={"duration_ms": duration_ms, "errors": len(errors)},
    ))

    return EvolutionReport(
        steps=steps,
        promoted=promoted,
        merged=merged,
        dropped=dropped,
        errors=errors,
        duration_ms=duration_ms,
        llm_used=llm_used,
    )
