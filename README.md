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

<p align="center">
  <a href="https://github.com/a2328275243/mempalace-evolve/stargazers"><img src="https://img.shields.io/github/stars/a2328275243/mempalace-evolve?style=for-the-badge&amp;logo=github&amp;color=2ea44f" alt="GitHub Stars"/></a>
  <a href="https://github.com/a2328275243/mempalace-evolve/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/a2328275243/mempalace-evolve/tests.yml?style=for-the-badge&amp;logo=githubactions&amp;label=CI" alt="CI"/></a>
  <a href="https://pypi.org/project/mempalace-evolve/"><img src="https://img.shields.io/pypi/v/mempalace-evolve?style=for-the-badge&amp;logo=pypi&amp;color=3775a9" alt="PyPI"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-yellow.svg?style=for-the-badge" alt="License"/></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge" alt="PRs Welcome"/></a>
</p>



---

# MemPalace Evolve

MemPalace Evolve is a self-evolving long-term memory system for AI tools.

It gives an assistant a memory layer that can store facts, recall relevant context, promote useful memories, decay noisy ones, reconcile conflicts, and expose everything through Python, REST, LangChain-style tools, or MCP.

The goal is simple: make an AI assistant remember a project across sessions without forcing the user to repeat the same background every time.

## Why This Exists

Most AI tools have weak memory. A conversation ends, context disappears, and the next session starts cold.

MemPalace is built for long-running work:

- research projects
- coding projects
- writing projects
- personal knowledge bases
- agents that need durable context

It is not a full coding agent. It is the memory layer you plug into the agent or client you already use.

## Core Features

- **Persistent memory**: store facts, decisions, relationships, and project context.
- **Semantic recall**: retrieve memories relevant to the current task.
- **Knowledge graph**: connect entities and relationships instead of keeping only flat notes.
- **Memory evolution**: promote useful memories, decay weak ones, and reduce duplicates.
- **Multiple adapters**: Python SDK, REST API, MCP server, OpenAI-style helper, and LangChain-style tools.
- **Project isolation**: use `wing` names to separate memories by project, tool, or user.

## Quick Start

Requires Python 3.10+.

```bash
git clone https://github.com/a2328275243/mempalace-evolve.git
cd mempalace-evolve
pip install -e ".[mcp]"
```

Run a quick check:

```bash
mempalace doctor
```

Use the Python SDK:

```python
from mempalace_evolve import MemPalace

memory = MemPalace("./.mempalace", wing="demo")

memory.store_memory(
    content="The project uses a two-stage retrieval pipeline.",
    category="architecture",
    importance=0.8,
)

results = memory.recall("How does retrieval work?")
for item in results:
    print(item.content)
```

## Use With MCP Clients

Install with MCP support:

```bash
pip install -e ".[mcp]"
```

Add MemPalace as an MCP server in any MCP-capable client:

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

Restart your client. It should now see MemPalace tools for storing, recalling, promoting, auditing, and querying memory.

`MEMPALACE_PATH` controls where the memory database lives. `MEMPALACE_WING` separates memory spaces, for example one wing per project.

## Other Integration Options

REST API:

```bash
pip install -e ".[api]"
mempalace-server
```

LangChain-style tools:

```bash
pip install -e ".[langchain]"
python examples/langchain_agent.py
```

Minimal SDK example:

```bash
python examples/sdk_basic.py
```

Cursor MCP example:

```bash
python examples/cursor_mcp/verify_setup.py
```

Claude Code hook example:

```bash
python examples/claude_code_hook/stop_hook.py
```

These examples are optional. The core package works without any specific AI client.

## Project Layout

- `src/mempalace_evolve/` - core memory system, evolution pipeline, adapters, CLI, and SDK.
- `tests/` - regression tests for the memory engine and adapters.
- `examples/` - small integration examples.
- `pyproject.toml` - package metadata and optional dependencies.

## Development

Install development dependencies:

```bash
pip install -e ".[dev,mcp]"
```

Run tests:

```bash
python -m pytest tests/ -v
```

Run the doctor:

```bash
python -m mempalace_evolve.cli doctor
```

## Current Direction

The repository is now focused on MemPalace Evolve itself.

The next work is improving memory quality:

- better automatic summarization
- better conflict detection
- stronger knowledge graph extraction
- cleaner memory promotion and decay
- better demos that show memory improving across sessions

## License

MIT. See `LICENSE`.
