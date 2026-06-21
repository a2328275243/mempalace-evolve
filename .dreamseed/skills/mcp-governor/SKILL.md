---
name: mcp-governor
description: Govern DreamSeed MCP tools. Use when adding, auditing, enabling, disabling, or risk-scoring MCP servers.
---

# MCP Governor

## Goal
Make MCP capability structured, discoverable, and bounded by risk.

## Workflow
1. Run `dreamseed doctor mcp` before adding or changing MCP servers.
2. Register every server in `config/mcp.registry.json` with source, command, risk tags, network use, read/write behavior, and output limits.
3. Keep external MCP servers as candidates until the user explicitly enables them.
4. Label high-risk servers with one or more of: `browser`, `desktop`, `network-write`, `filesystem-write`, `credentialed`.
5. Smoke test config and command shape before relying on a server.

## Rules
- Secrets come from environment variables or private local config only.
- Do not auto-enable high-risk MCP servers.
- Prefer narrow tools with concise JSON output.
