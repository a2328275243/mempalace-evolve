# Quick Start

## Install And Verify

```bash
pip install -e ".[api,mcp]"
mempalace doctor
```

Use Python 3.10 or newer. The doctor command must complete its memory and
knowledge graph checks before using a real palace.

## First Durable Memory

```python
from mempalace_evolve import MemPalace

palace = MemPalace("./my_first_palace", wing="documentation-demo")
palace.remember(
    "The application reads its API key from OPENAI_API_KEY.",
    room="config",
    source="deployment-guide",
    tags=["security"],
)

results = palace.recall("Where is the API key configured?", room="config")
print(results[0]["content"])
```

Use a different `wing` for every project, user, or agent. A `room` is a
category inside that boundary. `metadata` stores structured application fields,
`tags` are labels, and a positive `ttl` is the number of seconds before a
memory is excluded from recall.

## CLI

```bash
mempalace remember "Project uses Python 3.12" --room architecture --palace ./.mempalace
mempalace recall "Python version" --palace ./.mempalace
mempalace evolve --palace ./.mempalace
mempalace export --format json --output backup.json --palace ./.mempalace
```

Use `mempalace serve --palace ./.mempalace --wing documentation-demo` to start
the HTTP API. See the root README for MCP configuration and authenticated REST
examples.

## Backup And Recovery

Export before a risky migration or deletion, then verify the backup in a fresh
wing:

```python
palace.export(output="backup.json")
recovered = MemPalace("./recovered_palace", wing="recovery")
report = recovered.import_memories("backup.json")
assert report["errors"] == []
```

When recall is unexpectedly empty, run `mempalace doctor`, confirm the active
`--palace` and `--wing`, then inspect `palace.stats()["lifecycle"]` for expired
or superseded memories.
