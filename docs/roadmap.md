# MemPalace Wiki Roadmap

> Self-evolving knowledge base for AI agents.
> A knowledge base that grows itself from files, notes, and AI conversations.

This is the living roadmap for MemPalace Wiki. It tracks the 10-month plan to
turn MemPalace Evolve from a memory SDK into a self-evolving AI knowledge base.

## Positioning

MemPalace Wiki is **not** a plain RAG store and **not** a plain memory SDK.

| Layer        | What it holds                          | Visible to users      |
|--------------|----------------------------------------|-----------------------|
| Sources      | files, notes, web pages, AI chats      | via `mempalace ingest`|
| Knowledge Base | wiki pages, entities, relations, timeline | `.mempalace/wiki/`  |
| Memory Layer | preferences, decisions, task context   | via `kb_store_memory` |

The differentiator is the **evolution loop**: memories that are reused,
confirmed, or referenced get promoted into the knowledge base; stale,
duplicated, or conflicting ones get decayed, merged, or flagged.

## Month 1 — Reposition and reface (in progress)

- Rename product to **MemPalace Wiki: Self-Evolving Knowledge Base for AI Agents**.
- Rewrite README with a 60-second demo and three-layer architecture diagram.
- Add `docs/vision.md` explaining why this is not plain RAG.
- Add `README.zh-CN.md`.
- Land this roadmap in `docs/roadmap.md`.
- Freeze the plan in `.codex-project/PROJECT_MEMORY.md`.

## Month 2 — Unified data model

New first-class objects: `Source`, `Chunk`, `Memory`, `Entity`, `Relation`,
`WikiPage`, `Citation`. Every generated fact must trace back to a source.
Vector layer stays on Chroma; structured metadata on SQLite; knowledge graph
gains time + source fields.

## Month 3 — Ingestion system

`mempalace init` / `mempalace ingest <path>` / `mempalace sources status`.
Support `.md`, `.txt`, `.py`, `.json`, `.yaml`, `.html`. `.mempalaceignore`.
Hash-based incremental indexing, archive-on-delete, partial rebuild on change.

## Month 4 — Automatic wiki generation

`mempalace build` emits `.mempalace/wiki/` Markdown pages: `index`, `overview`,
`architecture`, `decisions`, `tasks`, `entities/<name>`. Rule-based skeleton by
default; optional LLM summaries. Every section carries citations.

## Month 5 — Memory evolution upgrade

States: `candidate -> active -> promoted -> stale/conflicted -> archived`.
`mempalace memory review/promote/archive/explain`. Reused memories promote;
duplicates merge; contradictions surface as `needs_review` conflicts.

## Month 6 — First-class MCP

Tools: `kb_search`, `kb_ask`, `kb_read_page`, `kb_list_pages`, `kb_ingest`,
`kb_store_memory`, `kb_review_conflicts`, `kb_graph_query`, `kb_timeline`.
Every answer returns evidence, source ids, confidence, and warnings.

## Month 7 — QA and RAG quality

`mempalace ask "<question>"` with hybrid retrieval over chunks, pages, graph,
and promoted memories. Evidence-first answers; explicit uncertainty; optional
LLM via OpenAI-compatible or local endpoint. No key stored in-repo.

## Month 8 — Static site export

`mempalace export site` produces a deployable static site with wiki pages,
search index, entity graph (Mermaid/light D3), timeline, and conflicts view.
No backend; GitHub Pages friendly.

## Month 9 — Eval, stability, privacy

Metrics: recall precision, source attribution, stale suppression, conflict
detection, wiki coverage, answer faithfulness, ingest/search latency.
`mempalace eval run`, `mempalace benchmark`, `mempalace privacy scan`,
`mempalace cleanup`. Local-only default, secret/PII redaction.

## Month 10 — v1.0 release and growth

PyPI `pip install mempalace-evolve`. Three demos, three articles, English-first
README, `README.zh-CN.md`. Target: 3000+ stars, real external feedback.