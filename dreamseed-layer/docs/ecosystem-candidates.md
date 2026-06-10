# DreamSeed Ecosystem Candidates

DreamSeed absorbs external agent ideas as reviewable candidates first. A candidate is not installed, enabled, or injected into prompts by default.

## Candidate Fields
- `id`: Stable local identifier.
- `source`: Upstream project or pattern.
- `url`: Public reference URL when available.
- `capability`: What DreamSeed can learn from it.
- `risk`: Low, medium, or high.
- `dependencies`: Runtime dependencies, if any.
- `adaptation`: How the idea maps into DreamSeed without adding heavy orchestration.
- `defaultState`: `candidate`, `disabled`, or `enabled`.
- `network`: Whether it needs network access.
- `readWrite`: Whether it writes files, memory, or external state.
- `acceptance`: Commands or checks required before enabling.

## Initial Candidates

| ID | Source | Capability | Risk | Default |
| --- | --- | --- | --- | --- |
| hermes-skill-evolution | Hermes-style loop | Skill self-evolution, failure archive, reviewed learning | medium | candidate |
| codex-audit-execution | Codex-style execution | Layered instructions, small scoped edits, verification before claims | low | candidate |
| langgraph-state-flow | LangGraph | Observe-plan-act-verify-review state graph without runtime dependency | low | candidate |
| crewai-task-contracts | CrewAI | Separate agents from tasks without always-on swarm | low | candidate |
| openhands-eval-sandbox | OpenHands | Sandbox-minded evals, failure artifacts, reproducible checks | medium | candidate |
| mcp-structured-tools | MCP official guidance | Structured tools, minimal permissions, schema-first safety | low | candidate |

## Policy
- External MCP and skill ideas must pass `dreamseed eval run --suite mcp` or a focused acceptance check before enablement.
- High-risk candidates must not auto-enable.
- Candidate records are publishable only if they do not contain secrets, private paths, or local history.
