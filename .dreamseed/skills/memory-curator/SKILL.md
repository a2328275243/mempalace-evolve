---
name: memory-curator
description: Curate DreamSeed Code memory. Use when the user asks to remember, recall, forget, organize, deduplicate, promote, or audit long-term memory across MemPalace, DREAMSEED.md, AGENTS.md, and project notes.
---

# Memory Curator

## Goal
Keep memory useful, small, current, and safe across sessions.

## Workflow
1. Retrieve before writing. Search MemPalace with focused terms through MCP or `scripts/dreamseed-memory-bridge.ps1 -Mode recall -Query "<query>"`.
2. Classify the finding:
   - `user`: stable user preferences and collaboration style.
   - `project`: durable decisions, constraints, external context not derivable from files.
   - `procedural`: reusable lessons, error patterns, debugging tactics.
   - `transient`: useful only in this session; do not save.
3. Deduplicate. Update or supersede existing memory when the new fact overlaps instead of writing a duplicate.
4. Write new findings to `memory-candidates/` first. Promote only through `scripts/memory_review.py apply` followed by `scripts/memory_promote.py promote-reviewed`.
5. Promote stable project instructions to `DREAMSEED.md` or `AGENTS.md` when they should be visible without semantic recall.
6. Forget safely. If the user asks to forget, find the exact memory and remove only matching entries.

## Rules
- Never store secrets, tokens, private keys, passwords, or credential-like values.
- Prefer concise memories with source and date context when available.
- Downgrade generic compact/checkpoint notes, low-value chat, temporary debugging traces, and long tool output. They should not reach `reviewed/`.
- If two memories conflict, keep the newer one only when evidence is clear; otherwise ask the user.
- After any memory candidate, review, or promotion, summarize what changed and where it was stored.
