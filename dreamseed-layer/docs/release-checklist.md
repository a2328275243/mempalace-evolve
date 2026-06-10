# DreamSeed Release Checklist

Use this checklist before publishing DreamSeed source or a local kit.

## Required Checks
- `dreamseed --help`
- bare `dreamseed`
- `dreamseed provider status`
- `dreamseed provider test`
- `dreamseed history status`
- `dreamseed evolve status`
- `dreamseed doctor context`
- `dreamseed doctor mcp`
- `dreamseed doctor hooks`
- `dreamseed usage summary`
- `dreamseed memory audit`
- `dreamseed mcp list`
- `dreamseed eval run --suite smoke`
- `python scripts/brand_audit.py scan --strict`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dreamseed-audit.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/package-dreamseed.ps1`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dreamseed-smoke.ps1`

## Package Rules
- Source release includes source, docs, scripts, skills, agents, config templates, MCP registry, and wheelhouse README.
- Source release excludes runtime kernels, provider local config, imported history, memory data, self-evolution staging, logs, caches, and credentials.
- Full local kit may include dependency helpers and offline wheelhouse, but must still exclude secrets and private history.

## Secret Safety
- Never print API keys, bearer tokens, passwords, or provider local files.
- Provider exports must be redacted.
- Any exposed key should be rotated outside DreamSeed.
