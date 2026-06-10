# DreamSeed Code

DreamSeed Code is a source-first custom coding agent distribution. It keeps the recovered source in `restored-src/` and adds its own agent layer: memory, MCP, skills, specialist agents, hooks, launchers, verification, and packaging.

The publishable repository intentionally does not include bundled runtime artifacts. A local compatible runtime can exist while developing, but GitHub and release zips should contain only the split source and DreamSeed layers.

## What It Adds
- `dreamseed` launcher with automatic `.dreamseed`, MCP, memory, and prompt wiring.
- DreamSeed Provider Bridge: a small local Anthropic-compatible proxy for OpenAI-chat-compatible upstream providers.
- MemPalace MCP integration for recall plus reviewed-only promotion.
- Skills for memory curation, self-evolution, MCP recommendation, and verification.
- Specialist agents for memory architecture, self-improvement review, and MCP scouting.
- Source-first packaging that excludes local kernels, memory databases, caches, and credentials.

## Running Locally

Install the `dreamseed` command from a clone:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-dreamseed.ps1
dreamseed --help
```

or install it through npm:

```powershell
npm install -g .
dreamseed --help
```

DreamSeed now uses a compatible runtime as its only execution kernel. Configure
one local runtime, then run `dreamseed --print "hello"` or enter the normal
interactive session.

```powershell
$env:DREAMSEED_COMPAT_KERNEL_JS = "<path-to-compatible-kernel.js>"
node bin\dreamseed-agent.js --help
```

or use an installed compatible command:

```powershell
$env:DREAMSEED_COMPAT_KERNEL_CLI = "compatible-agent"
node bin\dreamseed-agent.js
```

Inspect the compatible-runtime route and known slow-path graph:

```powershell
dreamseed doctor kernel
```

## Provider Bridge

DreamSeed does not require CC Switch at runtime. The easiest path is the bundled local model manager:

```powershell
dreamseed manager
```

This opens a local browser UI where you can add, edit, delete, test, and switch saved model endpoints before entering the agent. The manager only binds to `127.0.0.1`, uses a per-launch token for its local API, and does not show saved API keys in the model list.

The upstream side is OpenAI-compatible `/v1/chat/completions` by default. A saved model endpoint needs a display name, base URL, API key or API-key environment variable, and model name.

Advanced CLI setup is still available:

```powershell
dreamseed provider setup --name glm --url https://your-glm-endpoint.example.com --key your-token --model GLM-5.1
dreamseed provider list
dreamseed provider use glm
dreamseed provider status
```

DreamSeed's provider bridge exposes a local Anthropic-compatible `/v1/messages` endpoint to the runtime. `providers.local.json` is ignored by Git and must not be published. The launcher auto-starts `scripts/provider_bridge.mjs` when a private provider file exists.

For local migration only, an existing CC Switch provider can be imported once:

```powershell
python scripts\import_ccswitch_provider.py --provider GLM --output .dreamseed\providers.local.json
```

After import, DreamSeed uses its own local bridge and no longer reads the CC Switch database during normal runs.

## Memory

DreamSeed uses MemPalace when available:

```powershell
scripts\install-python-deps.ps1
scripts\dreamseed-memory-bridge.ps1 -Mode status
```

New memory first goes to `memory-candidates/` or the configured `DREAMSEED_MEMORY_CANDIDATES_DIR`. Only reviewed candidates may be promoted:

```powershell
scripts\memory_review.py apply --all
scripts\memory_promote.py promote-reviewed --all
```

The default memory directory is `.dreamseed-memory` in the active project and is ignored by Git.

## Self-Evolution

DreamSeed has a controlled opening for improving itself:

```powershell
dreamseed evolve status
dreamseed evolve propose --title "..." --problem "..." --evidence "..." --change "..." --file ".dreamseed/skills/self-evolve/SKILL.md"
dreamseed evolve inspect <proposal-id>
dreamseed evolve apply <proposal-id> --yes
dreamseed evolve verify <proposal-id>
dreamseed evolve rollback <proposal-id> --yes
```

The flow is proposal-first. `propose` writes a candidate under `self-evolve-candidates/` and creates a `files/` staging area. It does not edit the repository. `apply --yes` copies staged files into the repository only after path, secret, and publish-layer checks, then creates backups under `self-evolve-backups/` and runs `scripts/dreamseed-audit.ps1`.

After a verified improvement, write a memory candidate instead of promoting directly:

```powershell
dreamseed evolve memory-candidate <proposal-id> --lesson "Reusable lesson"
python scripts\memory_review.py apply --all
python scripts\memory_promote.py promote-reviewed --all
```

This keeps self-iteration useful without turning it into uncontrolled self-modification. Local proposal and backup directories are ignored by Git and excluded from release zips.

## Legacy History Import

Old compatible-agent history can be imported into a private DreamSeed archive:

```powershell
python scripts\import_claude_history.py import
python scripts\import_claude_history.py status
python scripts\import_claude_history.py search "keyword"
python scripts\import_claude_history.py list-sessions --limit 12
python scripts\import_claude_history.py resume-context "keyword-or-session-id"
python scripts\import_claude_history.py sync-native-resume --target-cwd .
```

The importer stores raw legacy sessions in `legacy-history/claude-code/` and writes project-level memory candidates into `memory-candidates/`. These directories are ignored by Git and excluded from release zips.

After import and native resume sync, launch DreamSeed and use `/resume` to continue from old imported history:

```text
dreamseed
/resume
/resume 研究项目
/resume 0147d369-c090-4afd-8271-b3c3ef5c5046
```

`sync-native-resume` writes private bridge files into the runtime resume index for the target working directory. `dreamseed-local.ps1` runs this sync automatically for this machine when imported history exists. `/resume` loads the selected legacy session into the current conversation as private context. It does not directly write to MemPalace; durable items still need the normal review path:

```powershell
python scripts\memory_review.py list
python scripts\memory_review.py apply --all
python scripts\memory_promote.py promote-reviewed --all
```

## Packaging

Create a source-first release zip:

```powershell
scripts\package-dreamseed.ps1
```

The zip includes `restored-src/`, `.dreamseed/`, `.mcp.json`, `bin/`, `config/providers.example.json`, `manager/`, `scripts/`, `docs/`, `vendor/python-wheels/`, `requirements-dreamseed.txt`, `AGENTS.md`, `DREAMSEED.md`, `README.md`, and `package.json`.

The zip excludes `package/`, private provider configs, imported legacy history, memory candidates, self-evolution candidates/backups, archive artifacts, memory directories, caches, and logs.
