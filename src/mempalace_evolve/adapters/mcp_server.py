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
from pathlib import Path


def create_mcp_server(palace_path: str | None = None, wing: str = "global"):
    """Create a FastMCP server exposing MemPalace tools."""
    try:
        from fastmcp import FastMCP
    except ImportError:
        raise ImportError(
            "MCP adapter requires fastmcp. Install with: "
            "pip install mempalace-evolve[mcp]"
        )

    from mempalace_evolve.sdk import MemPalace

    if palace_path is None:
        palace_path = os.environ.get(
            "MEMPALACE_PATH", str(Path.home() / ".mempalace")
        )
    wing = os.environ.get("MEMPALACE_WING", wing)

    palace = MemPalace(palace_path, wing=wing)
    mcp = FastMCP("mempalace")

    @mcp.tool()
    def remember(content: str, room: str = "general") -> str:
        """Store important information for future sessions.

        Use this when you learn something worth remembering:
        decisions, errors, architecture, user preferences, etc.

        Args:
            content: What to remember (be specific and concise)
            room: Category — one of: decisions, errors, architecture,
                  config, preferences, progress, general
        """
        drawer_id = palace.remember(content, room=room)
        return json.dumps({"stored": True, "id": drawer_id, "wing": wing, "room": room})

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
            output.append({
                "content": r["content"],
                "room": r.get("metadata", {}).get("room", ""),
                "distance": round(r.get("distance", 0), 4),
            })
        return json.dumps({"results": output, "count": len(output)}, ensure_ascii=False)

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
    def forget(memory_id: str) -> str:
        """Delete a specific memory by its ID.

        Args:
            memory_id: The drawer ID returned by remember()
        """
        ok = palace.forget(memory_id)
        return json.dumps({"deleted": ok, "id": memory_id})

    @mcp.tool()
    def evolve(transcript: str = "") -> str:
        """Run memory evolution — extract and promote valuable memories.

        Call this at the end of a session to automatically learn from
        the conversation.

        Args:
            transcript: Session transcript to analyze (optional)
        """
        report = palace.evolve(transcript=transcript or None)
        return json.dumps(report)

    return mcp


def main():
    """Entry point for mempalace-mcp command."""
    mcp = create_mcp_server()
    mcp.run()


if __name__ == "__main__":
    main()

