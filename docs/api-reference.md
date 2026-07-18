# API Reference

## Python SDK

```python
from mempalace_evolve import MemPalace

memory = MemPalace("./.mempalace", wing="project-alpha")
```

`wing` is the isolation boundary. Use one stable wing per project, agent, or
user. `room` is a category inside a wing.

| Method | Purpose |
| --- | --- |
| `remember(content, room="general", metadata=None, source="", ttl=None, tags=None)` | Store one durable memory |
| `recall(query, limit=5, room=None, threshold=0.8, hybrid=True)` | Retrieve relevant memories |
| `forget(drawer_id)` | Delete one memory |
| `batch_remember(memories)` | Store a list of memory dictionaries |
| `batch_recall(queries, limit=3, room=None, threshold=0.8)` | Recall for multiple queries |
| `batch_forget(drawer_ids)` | Delete multiple memories |
| `add_fact(subject, predicate, object)` | Add a knowledge graph relationship |
| `query_entity(entity, direction="both")` | Retrieve graph relationships |
| `digest(conversation)` | Extract memories from a transcript or messages |
| `context_for(query, limit=10, max_tokens=2000)` | Format recalled context for an agent prompt |
| `evolve(transcript=None)` | Run scoring, promotion, decay, and conflict handling |
| `export(format="json", output=None)` | Export the active wing |
| `import_memories(source)` | Import a list or JSON backup |
| `stats()` | Return memory and graph statistics |
| `purge_expired(ttl_days=90, ttl_summary_days=180)` | Remove expired or stale memories |
| `compress_old_memories(compress_after_days=60, max_chars=800)` | Archive/compress old memories |

`recall()` returns a list of dictionaries. Access content with
`result["content"]`, metadata with `result["metadata"]`, and similarity
information with `result["distance"]` or `_score`. Every result also has a
`drawer_id` and an `explanation` object with the source, creation time, score
components, match reason, lifecycle status, and any replacement fact.

### Lifecycle Rules

Memories begin as `active`. A conflicting decision or configuration may be
marked `superseded` and linked to its replacement; stale memories are
down-ranked; TTL-expired memories are never returned by `recall()` and can be
removed with `purge_expired()`. `stats()["lifecycle"]` reports the current
active, stale, superseded, and expired counts. `forget()` is permanent, so
export a backup before deleting data you may need later.

## CLI

```bash
mempalace doctor
mempalace remember "Use PostgreSQL" --room architecture --palace ./.mempalace
mempalace recall "database choice" --limit 5 --palace ./.mempalace
mempalace evolve --palace ./.mempalace
mempalace export --format json --output backup.json --palace ./.mempalace
mempalace serve --host 127.0.0.1 --port 8765 --palace ./.mempalace --wing project-alpha
```

Other lifecycle commands are `review`, `top`, `similar`, `purge`, `compress`,
and `consolidate`. Use `mempalace --help` for their exact arguments.

## REST API

Start the service with `mempalace serve --palace ./.mempalace --wing project-alpha`.
When `--api-key` is supplied, every route except `/health` requires `X-API-Key`.

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/health` | GET | Service, path, and wing confirmation |
| `/remember` | POST | Store one memory |
| `/recall` | POST | Retrieve memories |
| `/forget/{drawer_id}` | POST | Delete one memory |
| `/remember/batch` | POST | Store many memories |
| `/recall/batch` | POST | Recall for many queries |
| `/forget/batch` | POST | Delete many memories |
| `/kg/add` | POST | Add a graph fact |
| `/kg/query/{entity}` | POST | Query graph relationships |
| `/kg/query_v2` | POST | Structured temporal graph query |
| `/kg/path` | POST | Find a graph path |
| `/digest` | POST | Extract memories from a transcript |
| `/evolve` | POST | Run the evolution pipeline |
| `/stats` | GET | Memory and graph statistics |
| `/export` | GET | Export JSON or Markdown |
| `/review/due` | GET | Find due review items |
| `/review/mark` | POST | Mark a memory reviewed |
| `/review/snooze` | POST | Defer a review item |
| `/lifecycle/purge` | POST | Purge stale/expired memories |
| `/lifecycle/compress` | POST | Compress old memories |
| `/lifecycle/consolidate` | POST | Deduplicate and consolidate |

Example:

```bash
curl -X POST http://127.0.0.1:8765/remember \
  -H "Content-Type: application/json" \
  -d '{"content":"The API uses FastAPI.","room":"architecture"}'

curl -X POST http://127.0.0.1:8765/recall \
  -H "Content-Type: application/json" \
  -d '{"query":"Which framework does the API use?","limit":3}'
```

`POST /recall` accepts the same `limit`, `room`, `threshold`, and `hybrid`
options as the SDK and returns the same result and `explanation` structure.

## MCP Server

Install with `pip install -e ".[mcp]"`, configure `mempalace-mcp`, then set
`MEMPALACE_PATH` and `MEMPALACE_WING` in the client environment. The server
exposes memory write/recall, batch operations, graph operations, review and
lifecycle operations, and `evolve`.

The MCP tool names intentionally match the primary SDK verbs: `remember`,
`recall`, `batch_remember`, `batch_recall`, `add_fact`, `query_entity`,
`forget`, `batch_forget`, `purge_expired`, `compress_old_memories`, and
`evolve`.
