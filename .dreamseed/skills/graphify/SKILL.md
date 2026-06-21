---
name: graphify
description: "Use for questions about a codebase, architecture, file relationships, project content, or an existing graphify-out knowledge graph. Full pipeline instructions are lazy-loaded from references/full.md only when graphify is actually invoked."
---

# Graphify

Use this skill when the user asks about architecture, code relationships, project structure, cross-file concepts, or wants to build/query a persistent knowledge graph.

## Fast Operating Rules

- If `graphify-out/graph.json` exists and the user asks a natural-language question about the project, prefer querying the existing graph instead of rebuilding.
- If the user explicitly asks to build, update, export, watch, or run `/graphify`, read the relevant section of `references/full.md` before acting.
- Keep default reasoning compact. Do not load or paste the full pipeline guide unless graph construction/query behavior is needed.
- For GitHub clone, multi-repo merge, media extraction, Neo4j, MCP, Obsidian, wiki, path, and explain workflows, consult `references/full.md` only for the requested workflow.

## Common Commands

```bash
/graphify <path>
/graphify <path> --update
/graphify query "<question>"
/graphify path "Source" "Target"
/graphify explain "NodeName"
```

## Lazy Reference

The full Graphify guide was moved to `references/full.md` to keep DreamSeed's default context small and compact fast. Load that file only when this skill is selected and the current task needs the extended pipeline details.
