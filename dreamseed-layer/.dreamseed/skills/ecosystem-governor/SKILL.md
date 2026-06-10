---
name: ecosystem-governor
description: Apply DreamSeed's lightweight ecosystem operating model. Use when planning, executing, reviewing, or packaging changes that involve skills, agents, MCP, memory, self-evolution, automation, or token efficiency.
---

# Ecosystem Governor

## Goal
Borrow useful agent-ecosystem patterns without turning DreamSeed into a heavy framework.

## Operating Graph
Use this state loop for non-trivial work:
1. Observe: inspect the repo, config, logs, memory candidates, and current failure.
2. Plan: write the smallest reversible plan with verification and rollback.
3. Act: modify the narrowest surface that solves the problem.
4. Verify: run focused checks, then the DreamSeed audit when packaging or shared behavior changes.
5. Review: look for regressions, local-only assumptions, secrets, prompt bloat, and broken packaging.
6. Archive: record failures, lessons, and durable preferences as memory candidates only.

## Borrowed Patterns
- Hermes style: closed-loop learning, but gated through proposals and reviewed memory candidates.
- Codex style: layered instructions, scoped edits, evidence-first execution, and auditable verification.
- LangGraph style: explicit state transitions instead of vague autonomous loops.
- CrewAI style: separate roles from tasks. Agents review bounded decisions; skills carry reusable workflows.
- OpenHands style: prefer sandboxed execution, reproducible checks, and failure artifacts.
- MCP style: expose structured tools with narrow permissions, clear inputs, timeouts, and no secret echoing.

## Token Economy
- Search before reading whole trees. Prefer `rg`, targeted file reads, and short summaries.
- Keep always-on prompts lean; move repeated workflows into skills and docs.
- Do not store low-value chatter, bulk command output, or temporary debugging as memory.
- Create compact checkpoints only when they preserve decisions, paths, or error patterns.

## Safety Rules
- High-risk tools, profile changes, publishing, deletion, and credential moves require explicit approval.
- New automation starts in report-only or proposal-only mode.
- Self-evolution must go through `dreamseed evolve propose` and `apply --yes`.
- Memory promotion must go through reviewed candidates; direct writes to durable memory are forbidden.
- Package changes must update audit checks and release packaging together.

## Review Checklist
- Does this reduce repeated work or real failure risk?
- Is the behavior inspectable and reversible?
- Are model decisions separated from deterministic checks?
- Can a future maintainer understand why this exists?
- Did the package path receive the same fix as the local path?
