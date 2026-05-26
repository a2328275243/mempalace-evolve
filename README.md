<!--
╔══════════════════════════════════════════════════════════════════════╗
║  DreamSeed 种梦计划 — AI创造者大赛  官方 README 模板                ║
║                                                                      ║
║  使用说明：                                                          ║
║  1. 将本模板放在参赛仓库根目录 README.md 的顶部                       ║
║  2. 头图使用 DreamField 官方公开活动图片地址                         ║
║  3. 请保留 DREAMFIELD_README_HEADER_START / END 标识                 ║
║  4. 分割线以下供创作者自由编写项目内容                               ║
╚══════════════════════════════════════════════════════════════════════╝
-->

<!-- DREAMFIELD_README_HEADER_START -->

<p align="center">
  <a href="https://www.dreamfield.top">
    <img src="https://www.dreamfield.top/dream-field/contest-readme/assets/dreamseed-readme-banner.png" alt="DreamSeed 种梦计划参赛作品" width="100%" />
  </a>
</p>

<!-- DREAMFIELD_README_HEADER_END -->

---

# mempalace-evolve

Self-evolving memory palace for AI agents.

A persistent, layered memory system with automatic learning, knowledge graph, vector search, and self-evolution pipeline. Works with any AI agent — Claude Code, OpenAI, LangChain, or via REST API.

## Features

- **4-Layer Memory Architecture** (L0 core facts → L3 semantic search)
- **Knowledge Graph** — entity relationships with temporal tracking
- **Self-Evolution Pipeline** — automatic candidate → review → promote cycle
- **Vector Search** — ChromaDB-powered semantic retrieval
- **Daily Consolidation** — deduplication, conflict detection, merging
- **Adaptive Scoring** — importance decay + access frequency
- **Multi-Agent Support** — adapters for Claude Code, OpenAI, LangChain, REST API

## Quick Start

```bash
pip install mempalace-evolve

# Python SDK
from mempalace_evolve import MemPalace

palace = MemPalace("~/my-project")
palace.remember("The API uses JWT tokens for auth", room="decisions")
results = palace.recall("how does authentication work?")

# REST API server
pip install mempalace-evolve[api]
mempalace-server --port 8765
```

## Architecture

```
┌─────────────────────────────────────────┐
│         Your AI Agent                   │
├─────────────────────────────────────────┤
│  Adapter Layer                          │
│  ├── Claude Code (MCP + hooks)          │
│  ├── OpenAI (function calling)          │
│  ├── LangChain (BaseMemory)             │
│  └── REST API (universal)               │
├─────────────────────────────────────────┤
│  Evolution Pipeline                     │
│  ├── Candidate Generation               │
│  ├── Review & Scoring                   │
│  ├── Promotion to Long-term             │
│  └── Daily Consolidation                │
├─────────────────────────────────────────┤
│  Core Engine                            │
│  ├── Memory Layers (L0-L3)              │
│  ├── Knowledge Graph (SQLite)           │
│  ├── Vector Store (ChromaDB)            │
│  ├── Adaptive Scorer                    │
│  └── Lifecycle Manager                  │
└─────────────────────────────────────────┘
```
