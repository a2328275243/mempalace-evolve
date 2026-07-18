# Architecture And Memory Lifecycle

MemPalace separates the public integration surface from durable memory storage
and the lifecycle that keeps recalled context useful.

```text
SDK / REST / MCP / OpenAI / LangChain
                 |
                 v
          MemPalace SDK
        /        |        \
   vector store  graph store  runtime metadata
        \        |        /
                 v
  recall, scoring, conflict handling, lifecycle
```

## Isolation

Every memory has a `wing` and a `room`.

- A `wing` is a project, tenant, user, or agent boundary.
- A `room` categorizes information inside a wing, for example `decisions`,
  `architecture`, `config`, or `errors`.
- Provenance, tags, TTL, timestamps, and scores are stored as metadata.

All integration paths must preserve these fields. A client should never rely
on a default `global` wing for production multi-project data.

## Write Path

1. An adapter or SDK call validates content and creates metadata.
2. The memory is stored in ChromaDB with wing and room filters.
3. Optional graph facts are stored in the local knowledge graph.
4. Duplicate and conflict handling can mark older or similar entries.

## Recall Path

1. A query is scoped to the active wing and optional room.
2. Vector and optional graph signals retrieve candidate memories.
3. Recency, importance, access, and confidence adjust candidate scores.
4. The SDK returns content, metadata, distance, and score information to the
   calling adapter.

## Lifecycle

`evolve()` runs memory maintenance after a meaningful session or import.
Lifecycle operations can also be invoked explicitly:

- `purge_expired()` removes expired or stale low-value context.
- `compress_old_memories()` archives older material.
- `consolidate()` deduplicates and merges related context.
- review APIs support spaced repetition for important memories.

Before a large migration, export the wing to JSON. Importing the JSON preserves
provenance, tags, TTL-related metadata, and custom metadata.

## Operational Boundaries

- The system is local-first and stores data in the palace directory.
- REST writes are serialized inside one application process.
- Back up a palace with `export()` before moving or deleting it.
- Run `mempalace doctor` after installation and before diagnosing retrieval.
