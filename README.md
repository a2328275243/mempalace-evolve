<!--
+========================================================================+
|  DreamSeed Contest README Template                                     |
|                                                                        |
|  Notes:                                                                |
|  1. Place this block at the very top of the entry's README.md          |
|  2. The banner image must use the official DreamField contest URL      |
|  3. Keep the DREAMFIELD_README_HEADER_START / END markers              |
|  4. Below the horizontal rule, creators can freely author content      |
+========================================================================+
-->

<!-- DREAMFIELD_README_HEADER_START -->

<p align="center">
  <a href="https://www.dreamfield.top">
    <img src="https://www.dreamfield.top/dream-field/contest-readme/assets/dreamseed-readme-banner.png" alt="DreamSeed Contest Entry" width="100%" />
  </a>
</p>

<!-- DREAMFIELD_README_HEADER_END -->

---

# DreamSeed Code

This repository ships two things, designed to be used together or independently:

1. **MemPalace Evolve** - an auto-evolving long-term memory system for AI agents (Python, runs as an MCP server). Use it with Claude Code, Cursor, your own bot, or anything else that speaks the Model Context Protocol.
2. **DreamSeed Code** - a terminal coding agent built on top of **DreamSeed Lite Kernel**, a single-file 100 KB kernel written from scratch (not a fork or wrapper). DreamSeed comes with MemPalace pre-wired, plus skills, sub-agents, hooks, permissions, self-evolution, and a provider bridge for OpenAI-chat-compatible upstreams.

Pick the path that fits what you need.

---

## Path A: I only want the memory system

You do **not** need the DreamSeed agent for this. You only need Python and an MCP-capable client.

### 1. Install the Python package

Install from the included source (requires Python 3.10+):

```powershell
pip install -e ".[mcp]"
```

(works on Windows, Linux, and macOS; installs MemPalace Evolve from source plus chromadb and fastmcp)

### 2. Register it as an MCP server in your client

Add this entry to your client's MCP config (Claude Desktop's `claude_desktop_config.json`, Cursor's MCP settings, your custom bot's `.mcp.json`, etc.):

```json
{
  "mcpServers": {
    "mempalace": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mempalace_evolve.adapters.mcp_server"],
      "env": {
        "PYTHONIOENCODING": "utf-8",
        "MEMPALACE_PATH": ".mempalace",
        "MEMPALACE_WING": "default"
      }
    }
  }
}
```

`MEMPALACE_PATH` is where the memory database lives (relative to the client's working directory, or use an absolute path). `MEMPALACE_WING` separates memories per project.

### 3. Restart your client

Your client now has MemPalace tools available (recall, store, promote, audit). The system evolves stored memories automatically over time: noisy entries decay, useful entries get promoted, and conflicts get reconciled.

That is the whole install for the memory system. Skip the rest of this file unless you also want the DreamSeed agent.

---

## Path B: I want the full DreamSeed agent (terminal) with MemPalace built in

This gives you a `dreamseed` command that runs an interactive coding agent or a one-shot `--print` query, with MemPalace already wired in as MCP.

### Requirements

- Windows (the install scripts are PowerShell; the kernel itself is cross-platform Node, but installation is currently Windows-first).
- Node.js 18+.
- Python 3.10+.

### Install

```powershell
git clone <this-repo>
cd dreamseed-code-0.1.0
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-dreamseed.ps1
dreamseed --help
```

The installer:
- registers the `dreamseed` command on your PATH,
- installs the Python deps including MemPalace from the bundled wheelhouse,
- creates `%APPDATA%\DreamSeed\` for private config and history (never published),
- leaves your old shells' history untouched.

### Add a model

DreamSeed runs against any OpenAI-chat-compatible endpoint. The easiest way is the local manager:

```powershell
dreamseed manager
```

This opens a small local web UI to add, edit, test, and switch models. It writes to `%APPDATA%\DreamSeed\providers.local.json` (gitignored). Or do it from the command line:

```powershell
dreamseed provider setup --name my-model --base-url https://example.com/v1 --model glm-5.1
dreamseed provider use my-model
dreamseed provider test
```

### Run

```powershell
dreamseed                                  # interactive REPL
dreamseed --print "Reply exactly: ok"      # one-shot
```

When DreamSeed starts it boots the provider bridge automatically, exposes `http://127.0.0.1:17891` to the kernel, and runs the **DreamSeed Lite Kernel** underneath. MemPalace is started on demand as an MCP server.

### Common commands

```powershell
dreamseed provider status
dreamseed provider test
dreamseed history status
dreamseed memory audit
dreamseed mcp list
dreamseed doctor context
dreamseed eval run --suite smoke
```

### Importing legacy history

If you previously used the old compatibility kernel, import its sessions into DreamSeed's private archive so `/resume` can find them:

```powershell
python scripts\import_claude_history.py import
python scripts\import_claude_history.py search "keyword"
python scripts\import_claude_history.py sync-native-resume --target-cwd .
dreamseed
/resume
```

Raw imports stay in `legacy-history/`. Reviewable summaries land in `memory-candidates/`. Both are gitignored.

### Self-evolution

```powershell
dreamseed evolve status
dreamseed evolve propose --title "..." --problem "..." --change "..."
dreamseed evolve inspect <proposal-id>
dreamseed evolve apply <proposal-id> --yes
```

Proposals never modify source until `apply --yes`. Apply backs originals up under `self-evolve-backups/`, blocks private paths and likely secrets, and runs the audit.

---

## What is not in this repo

This is a terminal-only build. There is no Electron desktop app, no browser UI, no bundled "compatibility kernel" - DreamSeed Lite Kernel is the only kernel and the source is right there in `bin/dreamseed-lite-kernel.js` (about 100 KB, readable). Private data also never enters the repo:

- model API keys / private provider configs
- imported legacy history
- memory candidates and the live MemPalace database
- self-evolve candidates and backups
- DreamSeed Lite Kernel logs and caches
- `node_modules/` and `package-lock.json`

## Upgrading from an earlier DreamSeed build

If you previously ran a build that used the 13 MB compatibility kernel (`runtime\claude-cli.js`) or an Electron desktop app, this version replaces both with DreamSeed Lite Kernel. There is no fallback to the old kernel.

1. `git pull` (or reinstall this repo over the old one).
2. Delete `runtime\claude-cli.js` from your DreamSeed local data dir if you want a clean install. The launcher only looks at `bin\dreamseed-lite-kernel.js` now, so leaving the old file is harmless but wasteful.
3. Reinstall: `npm install -g .` or `scripts\install-dreamseed.ps1`.
4. `dreamseed --print "ok"` to confirm the new kernel boots.

If the launcher cannot find the kernel it prints `DreamSeed Lite Kernel was not found`. Point `DREAMSEED_KERNEL_JS` at a local `dreamseed-lite-kernel.js` file or reinstall.

## Layout

- `bin/` - `dreamseed-agent.js` launcher and `dreamseed-lite-kernel.js` kernel.
- `.dreamseed/` - agents, skills, hooks, settings.
- `.mcp.json` - MCP server registrations (MemPalace + a few defaults).
- `src/mempalace_evolve/` + `pyproject.toml` - MemPalace Evolve Python package source (install with `pip install -e ".[mcp]"`).
- `config/providers.example.json` - publishable provider template.
- `docs/` - system prompt, installation, brand audit, eval suite, ecosystem notes.
- `manager/` - local web UI for managing model endpoints.
- `scripts/` - provider bridge, MemPalace MCP launcher, history importer, audit, doctor, eval, packaging, self-evolve.

## License

MIT. See `LICENSE`.
