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

MemPalace Evolve is a local-first long-term memory layer for AI agents. It
stores durable facts, retrieves relevant context, tracks relationships, and
keeps each project, user, or agent isolated in its own `wing`.

It is a memory component, not a complete agent. Use it from Python, an MCP
client, or an HTTP client.

## Choose A Path

| Path | Best for | Start here |
| --- | --- | --- |
| Python SDK | Your own Python agent or application | [SDK quick start](#python-sdk-in-3-minutes) |
| MCP | Claude Code, Cursor, and other MCP clients | [MCP setup](#mcp-client-setup) |
| REST API | Services and non-Python clients | [REST API](#rest-api) |

Requires Python 3.10 or newer.

```bash
git clone https://github.com/a2328275243/mempalace-evolve.git
cd mempalace-evolve
pip install -e ".[api,mcp]"
mempalace doctor
```

`mempalace doctor` must report memory read/write and knowledge graph checks as
passing before you connect a client.

## Python SDK In 3 Minutes

```python
from mempalace_evolve import MemPalace

# Use a stable directory and a distinct wing for each project, user, or agent.
memory = MemPalace("./.mempalace", wing="payments-service")

memory.remember(
    "Authentication uses short-lived JWT access tokens.",
    room="decisions",
    metadata={"owner": "platform"},
    source="architecture-review",
    tags=["auth", "security"],
)

memory.add_fact("payments-service", "uses", "JWT")

for result in memory.recall("How does authentication work?", room="decisions"):
    print(result["content"])
```

For a complete runnable script, run `python examples/sdk_basic.py`.

## MCP Client Setup

Add this configuration to an MCP-capable client, then restart that client.

```json
{
  "mcpServers": {
    "mempalace": {
      "command": "mempalace-mcp",
      "env": {
        "MEMPALACE_PATH": ".mempalace",
        "MEMPALACE_WING": "payments-service"
      }
    }
  }
}
```

A successful connection exposes tools including `remember`, `recall`,
`batch_remember`, `batch_recall`, `add_fact`, `query_entity`, `forget`, and
`evolve`. Store one test fact, ask the client to recall it, and confirm that
the result is returned from the configured wing.

## REST API

Start an authenticated service for one memory wing:

```bash
mempalace serve --host 127.0.0.1 --port 8765 \
  --palace ./.mempalace --wing payments-service --api-key change-me
```

Check the service and write a memory:

```bash
curl http://127.0.0.1:8765/health

curl -X POST http://127.0.0.1:8765/remember \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d "{\"content\": \"The service uses PostgreSQL.\", \"room\": \"architecture\"}"
```

Recall it with:

```bash
curl -X POST http://127.0.0.1:8765/recall \
  -H "Content-Type: application/json" \
  -H "X-API-Key: change-me" \
  -d "{\"query\": \"Which database does the service use?\", \"limit\": 3}"
```

The health endpoint is intentionally public. All other endpoints require the
API key when `--api-key` is set. See [the API reference](docs/api-reference.md)
for batch, lifecycle, review, graph, and export routes.

## Core Concepts

| Concept | Meaning | Recommended convention |
| --- | --- | --- |
| `wing` | Hard project, user, or agent boundary | One stable identifier per tenant or project |
| `room` | Category inside a wing | Use `decisions`, `architecture`, `config`, `errors`, or `general` |
| `metadata` | Filterable structured fields | Keep values scalar and use stable keys |
| `tags` | Comma-separated labels persisted with a memory | Use short, reusable labels such as `security` |
| `ttl` | Lifetime in seconds for temporary information | Use it for volatile context, not core decisions |
| `evolve()` | Scores, promotes, and cleans stored context | Run after a meaningful session or on a schedule |

## A Durable Memory Workflow

1. Store a decision with `remember()` and a stable `source`.
2. Start a later session with `recall()` or `context_for()`.
3. Call `evolve()` after a substantial conversation or batch import.
4. Inspect `stats()` and export a backup before migration.

```python
report = memory.evolve()
backup = memory.export(format="json", output="mempalace-backup.json")
print(report, backup)
```

## Data Management And Troubleshooting

- Keep the palace directory on durable storage and back it up with
  `memory.export(format="json", output="backup.json")`.
- Restore with `memory.import_memories("backup.json")`.
- Remove one memory with `memory.forget(drawer_id)`; use a separate wing when
  deleting an entire project's data is required.
- Run `mempalace doctor` first when storage or dependencies fail.
- If recall is noisy, narrow the `room`, use a more specific query, add
  metadata/tags, and review conflicting or stale memories before lowering
  thresholds.

## More Documentation

- [Quick start](docs/quickstart.md)
- [API reference](docs/api-reference.md)
- [Architecture and lifecycle](docs/architecture.md)
- [Examples](examples/)
- [Security notes](docs/security.md)

## Development

```bash
pip install -e ".[dev,api,mcp]"
python -m pytest tests/ -v
ruff check src/
ruff format --check src/
```

## License

MIT. See `LICENSE`.
