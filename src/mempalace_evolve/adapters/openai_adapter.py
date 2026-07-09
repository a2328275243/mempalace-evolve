"""OpenAI adapter — integrate MemPalace via function calling.

Usage with OpenAI API:
    from mempalace_evolve import MemPalace
    from mempalace_evolve.adapters.openai import OpenAIAdapter

    palace = MemPalace("~/my-project")
    adapter = OpenAIAdapter(palace)

    # Get tool definitions for OpenAI
    tools = adapter.get_tools()

    # Handle tool calls from OpenAI response
    result = adapter.handle_tool_call(tool_name, arguments)
"""

from __future__ import annotations

import json
from typing import Any

from mempalace_evolve.adapters.base import AgentAdapter
from mempalace_evolve.sdk import MemPalace


class OpenAIAdapter(AgentAdapter):
    """Adapter for OpenAI function calling / tool use."""

    def on_session_start(self, context: dict[str, Any]) -> str | None:
        query = context.get("system_prompt", "") or context.get("first_message", "")
        if not query:
            return None
        return self.on_user_input(query, context)

    def on_session_end(self, transcript: str, context: dict[str, Any]) -> None:
        self.palace.evolve(transcript=transcript)

    def get_tools(self) -> list[dict]:
        """Return OpenAI-compatible tool definitions."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "mempalace_remember",
                    "description": "Store important information for future reference",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "What to remember"},
                            "room": {"type": "string", "description": "Category: decisions, errors, config, progress"},
                            "metadata": {"type": "object", "description": "Optional metadata fields"},
                            "source": {"type": "string", "description": "Optional source identifier"},
                            "ttl": {"type": "integer", "description": "Optional time-to-live in seconds"},
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Optional labels for filtering or access control",
                            },
                        },
                        "required": ["content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "mempalace_recall",
                    "description": "Search past memories for relevant information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "What to search for"},
                            "limit": {"type": "integer", "description": "Max results", "default": 5},
                            "room": {"type": "string", "description": "Optional room/category filter"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "mempalace_add_fact",
                    "description": "Add a relationship to the knowledge graph",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subject": {"type": "string"},
                            "predicate": {"type": "string"},
                            "object": {"type": "string"},
                        },
                        "required": ["subject", "predicate", "object"],
                    },
                },
            },
        ]

    def handle_tool_call(self, name: str, arguments: dict[str, Any]) -> str:
        """Handle a tool call from OpenAI and return the result as string."""
        if name == "mempalace_remember":
            drawer_id = self.palace.remember(
                arguments["content"],
                room=arguments.get("room", "general"),
                metadata=arguments.get("metadata"),
                source=arguments.get("source", ""),
                ttl=arguments.get("ttl"),
                tags=arguments.get("tags"),
            )
            return json.dumps({"stored": True, "id": drawer_id})

        elif name == "mempalace_recall":
            results = self.palace.recall(
                arguments["query"],
                limit=arguments.get("limit", 5),
                room=arguments.get("room"),
            )
            return json.dumps({"results": results}, ensure_ascii=False)

        elif name == "mempalace_add_fact":
            self.palace.add_fact(
                arguments["subject"], arguments["predicate"], arguments["object"]
            )
            return json.dumps({"added": True})

        return json.dumps({"error": f"Unknown tool: {name}"})
