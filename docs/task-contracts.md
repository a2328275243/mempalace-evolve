# DreamSeed Task Contracts

Task contracts are lightweight descriptions of work. They separate what should be done from which agent or skill reviews it. DreamSeed does not require CrewAI or a swarm runtime to use them.

## Contract Shape
```json
{
  "id": "release-check",
  "type": "release-check",
  "goal": "Verify publishable DreamSeed source",
  "inputs": ["source tree", "package zip"],
  "allowedTools": ["read", "shell"],
  "forbiddenActions": ["print secrets", "include private history"],
  "acceptance": ["dreamseed-audit.ps1", "package-dreamseed.ps1"],
  "artifacts": ["dist/dreamseed-code-<version>-source.zip"]
}
```

## Built-In Task Types
- `release-check`: Audit, brand scan, package, zip content checks.
- `mcp-evaluation`: Registry review and non-invasive MCP smoke checks.
- `memory-curation`: Candidate scoring, rejection, reviewed-only promotion.
- `provider-debug`: Provider status, health, latency, redacted export.
- `ecosystem-candidate-review`: Evaluate external ideas before enabling.
- `regression-fix`: Reproduce, patch, verify, archive lesson.

## Rules
- Contracts are documentation and optional JSON task inputs, not autonomous workers.
- High-risk work still requires explicit user approval.
- Failure artifacts go to local `logs/` and are excluded from release packages.
