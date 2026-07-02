# Vision: Why MemPalace Evolve Exists

> "An AI that doesn\'t remember is an AI that doesn\'t learn."

## The Problem

Every conversation with an AI assistant starts from scratch. You explain your project context, your preferences, your decisions 鈥?and then the conversation ends, and all that context evaporates.

Current solutions are fragmented:

- **Vector stores** (Chroma, Pinecone) store chunks but have no structure or evolution
- **Knowledge graphs** (Neo4j, Zep) require cloud infrastructure and monthly fees
- **Simple file storage** lacks semantic retrieval entirely
- **RAG pipelines** are designed for document Q&A, not for persistent agent memory

## The Solution

MemPalace Evolve is a **local-first, self-evolving knowledge base** that bridges the gap between raw vector storage and structured knowledge management.

### Three-Layer Architecture

```
鈹屸攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?        MEMORY LAYER            鈹? Preferences, decisions, task context
鈹? (short-term 鈫?long-term)       鈹? Auto-promoted by reuse
鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?      KNOWLEDGE BASE            鈹? Wiki pages, entities, relations, timeline
鈹? (structured, curated)          鈹? Built from promoted memories
鈹溾攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?鈹?         SOURCES                鈹? Files, notes, web pages, AI chats
鈹? (raw input, indexed)           鈹? Tracked and hash-verified
鈹斺攢鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹€鈹?```

### Key Differentiators

| Feature | MemPalace | Traditional RAG | Vector DB | Cloud KG |
|---------|-----------|----------------|-----------|----------|
| Self-evolves | 鉁?| 鉂?| 鉂?| 鉂?|
| Local-first | 鉁?| 鉁?| 鉁?| 鉂?|
| Knowledge graph | 鉁?| 鉂?| 鉂?| 鉁?|
| Memory promotion | 鉁?| 鉂?| 鉂?| 鉂?|
| Conflict detection | 鉁?| 鉂?| 鉂?| 鉂?|
| Free & open source | 鉁?| varies | varies | 鉂?|
| MCP ready | 鉁?| 鉂?| 鉂?| 鉂?|

## The Evolution Loop

This is the core innovation:

1. **Store** 鈫?Save a fact, decision, or observation
2. **Recall** 鈫?Retrieve relevant context when needed
3. **Promote** 鈫?Frequently used memories become permanent knowledge
4. **Decay** 鈫?Unused or contradicted memories fade
5. **Reconcile** 鈫?Conflicting facts are surfaced for review
6. **Build** 鈫?Generate wiki pages from consolidated knowledge

## Target Users

- **AI tool users** who want persistent context across sessions
- **Developers** building agents with LLMs
- **Researchers** managing evolving knowledge bases
- **Teams** sharing project context through MCP

## Non-Goals (what this is NOT)

- A full coding agent (use Claude Code / Cursor for that)
- A cloud service (everything runs locally)
- A general-purpose database (it\'s specialized for memory)
- A replacement for your primary note-taking app (though it can ingest from one)

## Road to v1.0

See [roadmap.md](roadmap.md) for the full 10-month plan.
