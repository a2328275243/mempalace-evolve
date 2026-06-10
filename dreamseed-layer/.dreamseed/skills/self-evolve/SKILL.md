---
name: self-evolve
description: Improve DreamSeed Code itself. Use when the user asks the agent to self-iterate, upgrade its abilities, absorb lessons from a session, improve prompts/skills/agents/hooks/MCP, or review its own failures.
---

# Self Evolve

## Goal
Make reversible, tested improvements to DreamSeed Code without destabilizing the runtime kernel.

## Workflow
1. Diagnose from evidence. Read current files, recent failures, and memory before proposing changes.
2. Create a gated proposal with `dreamseed evolve propose`. Record the problem, evidence, target files, risk, verification plan, and rollback plan.
3. Stage replacement files under `self-evolve-candidates/<id>/files/<relative-path>` only when the proposal is clear.
4. Apply only through `dreamseed evolve apply <id> --yes`. This creates backups, blocks private paths and secrets, and runs the DreamSeed audit unless explicitly skipped.
5. Verify. Run `dreamseed evolve verify <id>`, `scripts/dreamseed-audit.ps1`, the relevant smoke test, and any command that proves the changed path works.
6. Capture durable lessons with `dreamseed evolve memory-candidate <id> --lesson "..."` when the change teaches a reusable pattern. Promote only after review.

## Design Biases
- Keep the permanent prompt lean; move repeatable procedures into skills.
- Use specialist agents for bounded review, scouting, and architecture tasks.
- Prefer MCP when the task needs external state, but keep servers narrow and inspectable.
- Treat memory as layered: candidate pool, reviewed queue, promoted durable memory, and explicit forget paths.
- Require verification before an improvement becomes the new default.
- Prefer proposal-first self-iteration over automatic self-modification.

## Self-Review Checklist
- Does the change improve a repeatable workflow?
- Is it source-first and publishable without bundled upstream runtime artifacts?
- Does it avoid secrets and local-only assumptions?
- Did validation run, and are failures explained?
- Would a future agent understand why this exists?

## Rules
- Do not auto-publish, auto-push, or rewrite history.
- Do not hide failures. Preserve enough context for the next iteration.
- Prefer improving `.dreamseed/skills`, `.dreamseed/agents`, scripts, and docs; edit `restored-src` only when DreamSeed needs native source behavior.
- Do not write directly into MemPalace. Use memory candidates and the reviewed promotion path.
