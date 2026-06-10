---
name: context-economist
description: Reduce DreamSeed context and token waste. Use when the user asks about token cost, compacting prompts, large skills, context bloat, or keeping /resume and memory injection small.
---

# Context Economist

## Goal
Keep the active prompt small, useful, and auditable without removing capabilities.

## Workflow
1. Run `dreamseed doctor context` or `python scripts/dreamseed_context_doctor.py --json`.
2. Inspect the largest prompt, skill, agent, MCP, and memory-candidate sources first.
3. Move durable operating rules into short skills or docs; do not paste raw logs or raw legacy history into default context.
4. Keep `/resume` summary-based and load exact legacy sessions only when the user asks.
5. Prefer targeted recall and focused file reads over broad context injection.

## Rules
- Do not delete useful skills just to reduce count.
- Do not store temporary debug output in memory.
- Report concrete files and estimated token pressure before making changes.
