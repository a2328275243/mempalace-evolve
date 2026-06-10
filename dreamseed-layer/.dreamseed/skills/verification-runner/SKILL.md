---
name: verification-runner
description: Run focused verification for DreamSeed Code changes. Use when code, config, skills, agents, hooks, MCP, packaging, or memory bridge behavior changes and needs proof.
---

# Verification Runner

## Goal
Prove the changed behavior works and leave a concise audit trail.

## Standard Checks
Run the smallest set that covers the changed surface:
- Runtime smoke: `node bin\dreamseed-agent.js --help` with a local compatible runtime.
- Launcher smoke: `node bin\dreamseed-agent.js --help`.
- Memory smoke: `scripts\dreamseed-memory-bridge.ps1 -Mode status`.
- MCP config schema: parse `.mcp.json` as JSON and verify `mcpServers.mempalace`.
- Distribution audit: `scripts\dreamseed-audit.ps1`.
- Package build: `scripts\package-dreamseed.ps1`.

## Failure Handling
- Separate environment failures from implementation failures.
- Include the exact command, exit code, and meaningful stderr summary.
- If a dependency is missing, say which feature is degraded and how to restore it.
- Never claim success without a command or inspection that proves it.
- For packaging, inspect the archive contents for forbidden local kernels, memory databases, caches, and legacy namespaces.

## Rules
- Keep verification targeted; do not run expensive checks unrelated to the change.
- Do not modify files while verifying unless the user asked for auto-fixes.
- If a check writes local cache or memory, ensure it is ignored by Git.
