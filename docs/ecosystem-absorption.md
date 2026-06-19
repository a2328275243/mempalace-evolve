# DreamSeed Ecosystem Absorption

DreamSeed borrows patterns from mature agent projects without adding a heavy orchestration framework by default.

## What Was Adopted
- Hermes: closed-loop learning through reviewable improvement proposals and memory candidates.
- Codex: layered instructions, scoped edits, evidence-first implementation, and verification before claims.
- LangGraph: explicit state flow: observe, plan, act, verify, review, archive.
- CrewAI: agents and tasks are separated. Agents review bounded domains; skills store reusable workflows.
- OpenHands: sandbox-minded execution, reproducible checks, rollback notes, and failure artifacts.
- MCP: structured tools, narrow permissions, timeouts, and no secret echoing.

## What Was Not Adopted
- No always-on multi-agent swarm.
- No automatic source rewriting.
- No direct durable-memory writes.
- No automatic high-risk MCP/profile activation.
- No bundled upstream runtime in the source release package.

## Runtime Policy
Use the `ecosystem-governor` skill for cross-cutting work. Use the `ecosystem-integrator` agent when a change touches more than one of these surfaces: memory, MCP, provider bridge, hooks, skills, agents, self-evolution, packaging, or restored source.

## Verification Policy
Changes to ecosystem behavior must pass:
- focused smoke test for the changed command or workflow
- `scripts/dreamseed-audit.ps1`
- `scripts/package-dreamseed.ps1` when publishable files change
- brand audit for user-visible UI or release-source wording changes

## Memory Policy
Session-end capture writes candidates only. Durable memory requires:
1. candidate creation
2. review/apply into `reviewed/`
3. promotion through the reviewed promotion command

Low-value chatter, temporary debugging, long raw logs, and generic compact reminders should be rejected or heavily downranked.
