# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-05-29

### Added

- **Setup wizard** (`mempalace setup`): interactive CLI that auto-detects Python / chromadb / fastmcp, finds Claude Code / Cursor config directories, and writes MCP config with backup. Supports `--wing` and `--palace` flags for non-interactive use.
- **Memory type system** (semantic / episodic / procedural): cognitive-science-inspired classification. Procedural memories (error patterns, lessons) are automatically shared across all projects.
- **`digest()`**: auto-extract knowledge from conversation transcripts — keyword matching + content scoring → candidate extraction → memory storage + KG triple extraction.
- **`context_for()`**: one-call API to retrieve relevant memories formatted for LLM prompt injection, with `max_tokens` budget control.
- **`import_memories()` / `export()`**: bulk import from JSON files or lists; export to JSON or Markdown, optionally write to file.
- **Recency decay scoring**: `recall()` results include a `_score` combining semantic distance, time decay, and access frequency.
- **Contradiction detection**: storing a new decision that contradicts an existing one in the same room automatically marks the old one as `superseded`.
- **Working memory cache**: consecutive `recall()` calls on similar topics use an in-process cache instead of hitting ChromaDB every time.
- **Smart promotion**: memories recalled by 3+ different projects are auto-promoted to `procedural` type for global sharing.
- **Configurable scoring**: `scoring_config` parameter on `MemPalace()` for per-room weights, `never_delete` protection, and custom thresholds.
- **Hybrid retrieval**: `recall()` combines vector search + knowledge-graph expansion in one call.
- **CLI commands**: `mempalace doctor`, `mempalace demo`, `mempalace playground`, `mempalace export`.
- **GitHub Actions CI**: test matrix on Python 3.10 / 3.11 / 3.12 with `doctor` smoke test.

### Changed

- **Adapters**: OpenAI / LangChain / MCP / REST adapters updated for the new memory type system.
- **Evolution pipeline**: now incremental (only scans today's new memories for dedup, uses timestamps for passive maintenance).

## [0.2.0] - 2025-05-20

### Added

- Knowledge graph (SQLite-backed) with `add_fact()` / `query_entity()`.
- Memory consolidation (merge similar drawers).
- Lifecycle management (TTL, compress old unused memories).
- Adaptive scorer.

## [0.1.0] - 2025-05-10

### Added

- Core `MemPalace` SDK with `remember()` / `recall()` / `forget()`.
- ChromaDB vector storage backend.
- Evolution pipeline: candidate extraction → review → promote → drop.
- MCP server adapter.
- OpenAI Function Calling adapter.
- LangChain adapter.
- REST API with optional API-key authentication.
