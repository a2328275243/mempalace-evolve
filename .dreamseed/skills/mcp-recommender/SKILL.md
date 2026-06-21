---
name: mcp-recommender
description: Recommend, configure, or audit MCP servers for DreamSeed Code. Use when the user asks for tools, integrations, external services, memory, browser, GitHub, filesystem, database, or other MCP capabilities.
---

# MCP Recommender

## Goal
Add MCP capability only when it clearly helps the requested workflow.

## Workflow
1. Identify the job-to-be-done and the external state needed.
2. Prefer existing configured MCP servers. Inspect `.mcp.json` and settings before adding anything.
3. Choose tools with narrow, discoverable names and read-only defaults when possible.
4. For local stdio servers, define command, args, env, and failure messages. Avoid ambiguous shell wrappers.
5. Smoke test the server startup or schema. If dependencies are missing, report the exact install command but do not install unless the user asked.

## Evaluation Criteria
- Tool names are action-oriented and scoped.
- Outputs are concise JSON or short markdown, not noisy logs.
- Errors say what to fix next.
- Secrets are read from env vars, never committed.
- The server can be disabled without breaking DreamSeed Code.
- Prefer official or actively maintained servers for common domains.
- Prefer capability discovery and smoke tests over blind installation.

## Default Memory MCP
Use the `mempalace` MCP for long-term memory:
- `remember`: store durable facts.
- `recall`: retrieve context before asking the user.
- `add_fact` and `query_entity`: maintain relationship knowledge.
- `evolve`: consolidate memory at session boundaries.
