# MemPalace Evolve 鈥?API Reference

## Python SDK

### MemPalace

The main class for interacting with the memory system.

```python
from mempalace_evolve import MemPalace

memory = MemPalace(palace_path="./.mempalace", wing="demo")
```

#### Constructor

```python
MemPalace(
    palace_path: str | Path = None,    # Path to palace dir (default: ~/.mempalace)
    wing: str = "global",              # Project/wing name for isolation
    auto_evolve: bool = False,         # Auto-run evolution periodically
    evolve_interval: int = 3600,       # Seconds between auto-evolve cycles
    scoring_config: dict | None = None # Per-room scoring rules
)
```

#### Core Methods

| Method | Description |
|--------|-------------|
| `store_memory(content, category, importance, room, metadata, source)` | Store a new memory |
| `recall(query, room, limit, min_score, include_graph)` | Semantic recall |
| `remember(content, room)` | Quick store shorthand |
| `forget(memory_id)` | Delete a specific memory |
| `get_stats()` | Get memory statistics |
| `evolve()` | Run evolution pipeline |
| `get_knowledge_graph()` | Get the knowledge graph instance |
| `search_kg(query, entity_type, as_of)` | Query the knowledge graph |
| `build_wiki(output_dir)` | Generate wiki pages from memories |

### CLI

```bash
# Quick health check
mempalace doctor

# Interactive shell
mempalace shell

# Run evolution pipeline
mempalace evolve --path ./.mempalace

# Get memory stats
mempalace stats --path ./.mempalace

# Start REST API server
mempalace-server --host 0.0.0.0 --port 8000

# Start MCP server
mempalace-mcp
```

## REST API

Start with:
```bash
pip install -e ".[api]"
mempalace-server
```

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/memories` | GET | List memories |
| `/v1/memories` | POST | Store a memory |
| `/v1/memories/{id}` | GET | Get a specific memory |
| `/v1/memories/{id}` | DELETE | Delete a memory |
| `/v1/recall` | POST | Semantic recall |
| `/v1/evolve` | POST | Trigger evolution |
| `/v1/stats` | GET | Get memory statistics |
| `/v1/graph/query` | POST | Query knowledge graph |
| `/health` | GET | Health check |

### Example

```bash
curl -X POST http://localhost:8000/v1/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "The API uses FastAPI", "room": "architecture"}'

curl -X POST http://localhost:8000/v1/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "What framework does the API use?"}'
```

## MCP Server

### Available Tools

| Tool | Description |
|------|-------------|
| `kb_store_memory` | Store a new memory |
| `kb_recall` | Semantic recall |
| `kb_get_stats` | Get memory statistics |
| `kb_evolve` | Trigger evolution |
| `kb_search_kg` | Query knowledge graph |

### Configuration

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

## Knowledge Graph

### Entity Operations

```python
kg = memory.get_knowledge_graph()

# Add a relationship
kg.add_triple("subject", "predicate", "object",
              valid_from="2025-01-01", source_id="mem_001")

# Query entity
results = kg.query_entity("subject", as_of="2025-06-01")

# Invalidate a relationship
kg.invalidate("subject", "predicate", "object", ended="2025-06-15")

# Get all relations
all_relations = kg.get_all_relations()
```

### Triple Format

Each triple has:
- **subject**: Entity (person, project, concept)
- **predicate**: Relationship type (is_a, uses, depends_on)
- **object**: Target entity or value
- **valid_from**: When the fact became true
- **valid_to**: When the fact stopped being true (None = still valid)
- **source_id**: Links back to the originating memory
