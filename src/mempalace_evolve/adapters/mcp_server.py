"""MCP Server adapter — lets Claude Code / Cursor / any MCP client use MemPalace.

Setup in Claude Code:
    # ~/.claude/settings.json
    {
      "mcpServers": {
        "mempalace": {
          "command": "mempalace-mcp",
          "args": []
        }
      }
    }

Or run standalone:
    mempalace-mcp
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any


def create_mcp_server(palace_path: str | None = None, wing: str = "global"):
    """Create a FastMCP server exposing MemPalace tools."""
    try:
        from fastmcp import FastMCP
    except ImportError:
        raise ImportError(
            "MCP adapter requires fastmcp. Install with: pip install mempalace-evolve[mcp]"
        )

    from mempalace_evolve.sdk import MemPalace

    if palace_path is None:
        palace_path = os.environ.get("MEMPALACE_PATH", str(Path.home() / ".mempalace"))
    wing = os.environ.get("MEMPALACE_WING", wing)

    palace = MemPalace(palace_path, wing=wing)
    _write_lock = threading.Lock()
    mcp = FastMCP("mempalace")

    def _dump_result(result: Any) -> str:
        if hasattr(result, "model_dump"):
            result = result.model_dump()
        elif hasattr(result, "dict"):
            result = result.dict()
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def remember(
        content: str,
        room: str = "general",
        metadata: dict[str, Any] | None = None,
        source: str = "",
        ttl: int | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Store important information for future sessions.

        Use this when you learn something worth remembering:
        decisions, errors, architecture, user preferences, etc.

        Args:
            content: What to remember (be specific and concise)
            room: Category — one of: decisions, errors, architecture,
                  config, preferences, progress, general
        """
        with _write_lock:
            drawer_id = palace.remember(
                content,
                room=room,
                metadata=metadata,
                source=source,
                ttl=ttl,
                tags=tags,
            )
        return json.dumps(
            {"stored": True, "id": drawer_id, "wing": wing, "room": room},
            ensure_ascii=False,
        )

    @mcp.tool()
    def recall(query: str, limit: int = 5, room: str | None = None) -> str:
        """Search past memories by semantic similarity.

        Use this to check what you already know before asking the user,
        or to retrieve context from previous sessions.

        Args:
            query: Natural language search query
            limit: Max results (default 5)
            room: Optional filter by category
        """
        results = palace.recall(query, limit=limit, room=room)
        if not results:
            return json.dumps({"results": [], "message": "No relevant memories found"})
        output = []
        for r in results:
            output.append(
                {
                    "content": r["content"],
                    "room": r.get("metadata", {}).get("room", ""),
                    "distance": round(r.get("distance", 0), 4),
                }
            )
        return json.dumps({"results": output, "count": len(output)}, ensure_ascii=False)

    @mcp.tool()
    def batch_remember(memories: list[dict[str, Any]]) -> str:
        """Store multiple memories in a single batch operation.

        Args:
            memories: List of memory objects with content, room, metadata,
                source, ttl, and tags fields.
        """
        with _write_lock:
            result = palace.batch_remember(memories)
        return _dump_result(result)

    @mcp.tool()
    def batch_recall(
        queries: list[str],
        limit: int = 3,
        room: str | None = None,
        threshold: float = 0.8,
    ) -> str:
        """Recall memories for multiple queries in one tool call.

        Args:
            queries: Natural language search queries.
            limit: Max results per query.
            room: Optional room/category filter.
            threshold: Max distance, lower is more similar.
        """
        result = palace.batch_recall(
            queries,
            limit=limit,
            room=room,
            threshold=threshold,
        )
        return _dump_result(result)

    @mcp.tool()
    def add_fact(subject: str, predicate: str, object: str) -> str:
        """Add a relationship to the knowledge graph.

        Use for structured facts: "project uses FastAPI",
        "user prefers dark_mode", "module_A depends_on module_B".

        Args:
            subject: The entity (e.g. "project", "user", "auth_module")
            predicate: The relationship (e.g. "uses", "prefers", "depends_on")
            object: The target (e.g. "FastAPI", "dark_mode", "database")
        """
        with _write_lock:
            palace.add_fact(subject, predicate, object)
        return json.dumps({"added": True, "triple": [subject, predicate, object]})

    @mcp.tool()
    def query_entity(entity: str) -> str:
        """Query knowledge graph for all relationships of an entity.

        Args:
            entity: The entity name to look up
        """
        rels = palace.query_entity(entity)
        return json.dumps({"entity": entity, "relations": rels}, ensure_ascii=False)

    @mcp.tool()
    def query_entity_v2(entity: str, as_of: str = "") -> str:
        """Query knowledge graph returning structured result with separate
        incoming/outgoing lists.

        Args:
            entity: Entity name to query.
            as_of: Optional date string for temporal filtering (ISO format).
        """
        result = palace.query_entity_v2(entity, as_of=as_of or None)
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def query_path(start_entity: str, end_entity: str, max_depth: int = 4) -> str:
        """Find shortest path between two entities in the knowledge graph.

        Args:
            start_entity: Name of the starting entity.
            end_entity: Name of the target entity.
            max_depth: Maximum traversal depth (default 4).
        """
        path = palace.query_path(start_entity, end_entity, max_depth=max_depth)
        return json.dumps({"path": path, "length": len(path)}, ensure_ascii=False, default=str)

    @mcp.tool()
    def recall_stream(
        query: str, limit: int = 5, room: str = "", threshold: float = 0.8, hybrid: bool = True
    ) -> str:
        """Stream recall results as a generator (returned as a list).

        Same semantics as recall(), but yields results one-by-one with
        streaming metadata for real-time display in chat interfaces.

        Args:
            query: Natural language search query.
            limit: Max results to yield (default 5).
            room: Optional room filter.
            threshold: Max distance (0-1, lower = more similar).
            hybrid: If True, expand via KG relationships.
        """
        results = list(
            palace.recall_stream(
                query,
                limit=limit,
                room=room or None,
                threshold=threshold,
                hybrid=hybrid,
            )
        )
        output = []
        for r in results:
            item = {
                "content": r.get("content", ""),
                "room": r.get("metadata", {}).get("room", ""),
                "distance": round(r.get("distance", 0), 4),
            }
            if "_stream_meta" in r:
                item["_stream_meta"] = r["_stream_meta"]
            output.append(item)
        return json.dumps({"results": output, "count": len(output)}, ensure_ascii=False)

    @mcp.tool()
    def forget(memory_id: str) -> str:
        """Delete a specific memory by its ID.

        Args:
            memory_id: The drawer ID returned by remember()
        """
        with _write_lock:
            ok = palace.forget(memory_id)
        return json.dumps({"deleted": ok, "id": memory_id})

    @mcp.tool()
    def batch_forget(memory_ids: list[str]) -> str:
        """Delete multiple memories in a single batch operation.

        Args:
            memory_ids: Drawer IDs returned by remember() or batch_remember().
        """
        with _write_lock:
            result = palace.batch_forget(memory_ids)
        return _dump_result(result)

    @mcp.tool()
    def purge_expired(ttl_days: int = 90, ttl_summary_days: int = 180) -> str:
        """Purge memories that have expired by lifecycle rules.

        Args:
            ttl_days: TTL for low-importance memories
            ttl_summary_days: TTL for summarized memories
        """
        with _write_lock:
            result = palace.purge_expired(
                ttl_days=ttl_days,
                ttl_summary_days=ttl_summary_days,
            )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def compress_old_memories(compress_after_days: int = 60, max_chars: int = 800) -> str:
        """Compress old unused memories into archive summaries.

        Args:
            compress_after_days: Age threshold in days
            max_chars: Maximum summary length
        """
        with _write_lock:
            result = palace.compress_old_memories(
                compress_after_days=compress_after_days,
                max_chars=max_chars,
            )
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def consolidate(dry_run: bool = False) -> str:
        """Deduplicate and merge similar memories.

        Args:
            dry_run: If True, report planned changes without writing them
        """
        with _write_lock:
            result = palace.consolidate(dry_run=dry_run)
        return json.dumps(result, ensure_ascii=False, default=str)

    @mcp.tool()
    def evolve(transcript: str = "") -> str:
        """Run memory evolution — extract and promote valuable memories.

        Call this at the end of a session to automatically learn from
        the conversation.

        Args:
            transcript: Session transcript to analyze (optional)
        """
        with _write_lock:
            report = palace.evolve(transcript=transcript or None)
        return json.dumps(report)

    return mcp


def main():
    """Entry point for mempalace-mcp command."""
    mcp = create_mcp_server()
    mcp.run()


if __name__ == "__main__":
    main()
