# MemPalace Evolve Architecture

## Overview

MemPalace Evolve uses a layered architecture where information flows upward from raw sources through structured knowledge to active memory.

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?                  USER / AGENT                      鈹?鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?  SDK    鈹?  REST   鈹?  MCP    鈹? LangChain Tools   鈹?鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹粹攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?                  ADAPTER LAYER                     鈹?鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?                  EVOLUTION PIPELINE                鈹?鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?鈹? 鈹係coring  鈹?鈹侾romotion 鈹?鈹? Decay   鈹?鈹侰onflict鈹?鈹?鈹? 鈹?Engine  鈹?鈹? Gate    鈹?鈹? Engine  鈹?鈹侱etector鈹?鈹?鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?                  STORAGE LAYER                     鈹?鈹? 鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?鈹? 鈹?ChromaDB       鈹?鈹? SQLite    鈹?鈹?Knowledge   鈹?鈹?鈹? 鈹?(vector index) 鈹?鈹?(metadata) 鈹?鈹?Graph       鈹?鈹?鈹? 鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?                  CORE ENGINE                       鈹?鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?```

## Core Components

### 1. Storage Layer

**ChromaDB** 鈥?Vector embeddings for semantic search
- Stores chunk embeddings and metadata
- Supports cosine similarity search
- Wing-based collection isolation

**SQLite** 鈥?Structured metadata and configuration
- Memory records with scores, timestamps, categories
- Room-based organization
- Persistence configuration
- Evolution state tracking

**Knowledge Graph** 鈥?Entity-relationship store
- Entity nodes with typed relationships
- Temporal validity tracking
- Source citation links
- Local SQLite backend

### 2. Evolution Pipeline

**BundleScorer** 鈥?Scores each memory bundle on:
- Frequency of access
- Recency of access
- User-defined importance
- Cross-reference count
- Semantic uniqueness

**CandidateExtractor** 鈥?Identifies memories ready for:
- Promotion to knowledge base
- Decay (reduced score)
- Archival (score too low)
- Merge (near-duplicate)

**MemoryReviewer** 鈥?Conflict detection and resolution:
- Finds contradictory facts
- Flags for human review
- Proposes merge strategies

### 3. Adapter Layer

| Adapter | Protocol | Use Case |
|---------|----------|----------|
| Python SDK | Direct API | Full access from Python |
| REST API | HTTP | Remote clients, web UIs |
| MCP Server | stdio/SSE | Claude Desktop, Cursor, etc. |
| LangChain Tools | LangChain | Agent frameworks |
| OpenAI Adapter | OpenAI format | Compatible clients |

### 4. Memory Stack (Layers 0-3)

Memories are organized in a stack with increasing sophistication:

- **Layer 0**: Raw text, exact match retrieval
- **Layer 1**: Vector embeddings, semantic search
- **Layer 2**: Structured fields (categories, tags, importance)
- **Layer 3**: Knowledge graph integration, cross-references

## Data Flow

```
User Input 鈫?Adapter 鈫?Store(txt, meta, embedding)
                         鈫?                   Evolution Pipeline (async)
                         鈫?                   Promotion/Decay/Merge
                         鈫?                   Knowledge Graph Update
                         鈫?                   User Query 鈫?Recall 鈫?Scored Results
```

## Configuration

All configuration is stored in the palace directory:

```
.mempalace/
  鈹溾攢鈹€ config.json         # User configuration
  鈹溾攢鈹€ chroma.sqlite3      # ChromaDB (vector store)
  鈹溾攢鈹€ palace.db           # Metadata storage
  鈹溾攢鈹€ knowledge_graph.sqlite3  # Knowledge graph
  鈹斺攢鈹€ wings/
      鈹斺攢鈹€ <wing-name>/    # Per-wing storage
```

## Security Model

- All data is local by default
- No telemetry or external calls
- No cloud dependencies
- Privacy scan for PII/secret detection (planned)
