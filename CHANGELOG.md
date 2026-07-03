# Changelog

All notable changes to MemPalace Evolve will be documented in this file.

## [0.1.0] - 2025-07-02

### Added
- Core SDK (`MemPalace`) for remember/recall/forget operations
- ChromaDB vector storage backend
- SQLite metadata store with room-based organization
- Knowledge Graph for entity-relationship tracking
- Spaced Repetition scheduling with Leitner-like intervals
- Evolution Pipeline: auto-scoring, promotion/drop, dedup, consolidation
- Adaptive Scoring with recency decay and contradiction detection
- Working Memory Cache for fast repeated queries
- REST API (`mempalace serve`) with FastAPI
- MCP Server for Claude Desktop integration
- OpenAI-compatible adapter for custom AI agent integration
- LangChain adapter
- CLI: `remember`, `recall`, `forget`, `evolve`, `export`, `review`, `top`, `similar`, `serve`, `demo`, `playground`, `setup`
- Demo mode with self-contained showcase
- Interactive playground mode
- Setup wizard for MCP configuration
- Claude Code integration
- Import/export (JSON, Markdown)
- Digest and context generation
- Statistics and health check
- Test suite with 73 tests
- Documentation: API reference, architecture, roadmap, vision
- GitHub CI/CD pipeline (lint, test, build)
