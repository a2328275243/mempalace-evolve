# DreamSeed Code Agent Guide

DreamSeed Code is a source-first coding agent distribution. The repository should be understandable from split source and extension files, not from a single bundled runtime artifact.

## Architecture
- `restored-src/` is the reviewable recovered source.
- `.dreamseed/skills/` contains reusable workflows.
- `.dreamseed/agents/` contains specialist subagents.
- `.mcp.json` connects external state, currently MemPalace memory.
- `scripts/` contains deterministic diagnostics, memory, extraction, and packaging helpers.
- `scripts/provider_bridge.mjs` is DreamSeed's lightweight provider bridge. It replaces CC Switch for runtime provider routing.
- `scripts/import_claude_history.py` imports old compatible-agent history into a private `legacy-history/` archive and reviewable `memory-candidates/` only.
- `config/providers.example.json` is a publishable template. Private provider files such as `providers.local.json` are never committed.
- `bin/dreamseed-agent.js` is the launcher. It always routes interactive and `--print` runs to a configured compatible runtime, while keeping DreamSeed's provider, memory, MCP, skill, and audit wiring around it. Published source packages must not include bundled runtime artifacts.

## Operating Loop
1. Read local context first.
2. Recall memory before asking the user to repeat durable context.
3. Make small, reversible changes.
4. Verify with focused commands.
5. Capture durable lessons as reviewable memory candidates only when they will help future sessions.

## Publication Rule
Do not commit or package:
- `package/`
- local runtime archives
- `.dreamseed-memory/`
- `.dreamseed-runtime/`
- `legacy-history/`
- `memory-candidates/`
- `providers.local.json`
- credentials, logs, or caches

After publishing, run `dreamseed` directly. The DreamSeed Lite Kernel is bundled in `bin/`. If a model provider is needed, set `DREAMSEED_PROVIDER_CONFIG` to a private provider config; DreamSeed will start its own provider bridge.
