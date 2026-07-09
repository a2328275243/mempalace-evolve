"""LangChain adapter — integrate MemPalace as LangChain tools/memory.

Usage:
    from mempalace_evolve import MemPalace
    from mempalace_evolve.adapters.langchain_adapter import LangChainAdapter

    palace = MemPalace("./my-memory")
    adapter = LangChainAdapter(palace)

    # Get LangChain-compatible tools
    tools = adapter.get_tools()

    # Use with an agent
    from langchain_openai import ChatOpenAI
    from langchain.agents import initialize_agent
    llm = ChatOpenAI(model="gpt-4")
    agent = initialize_agent(tools, llm, agent="zero-shot-react-description")
"""

from __future__ import annotations

import json
from typing import Any

from mempalace_evolve.adapters.base import AgentAdapter
from mempalace_evolve.sdk import MemPalace


class LangChainAdapter(AgentAdapter):
    """Adapter for LangChain agents via structured tools."""

    def on_session_start(self, context: dict[str, Any]) -> str | None:
        query = context.get("user_query", "")
        if not query:
            return None
        return self.on_user_input(query, context)

    def on_session_end(self, transcript: str, context: dict[str, Any]) -> None:
        self.palace.evolve(transcript=transcript)

    def get_tools(self) -> list:
        """Return LangChain StructuredTool instances.

        Requires langchain-core >= 0.1.0.
        """
        try:
            from langchain_core.tools import StructuredTool
            from pydantic import BaseModel, Field
        except ImportError:
            raise ImportError(
                "LangChain adapter requires langchain-core. "
                "Install with: pip install mempalace-evolve[langchain]"
            )

        class RememberInput(BaseModel):
            content: str = Field(description="What to remember — be specific and concise")
            room: str = Field(
                default="general",
                description="Category: decisions, errors, config, architecture, general",
            )

            metadata: dict[str, Any] | None = Field(default=None, description="Optional metadata fields")
            source: str = Field(default="", description="Optional source identifier")
            ttl: int | None = Field(default=None, description="Optional time-to-live in seconds")
            tags: list[str] | None = Field(default=None, description="Optional labels for filtering or access control")

        class RecallInput(BaseModel):
            query: str = Field(description="Natural language search query")
            limit: int = Field(default=5, description="Max results to return")
            room: str | None = Field(default=None, description="Optional room/category filter")

        class AddFactInput(BaseModel):
            subject: str = Field(description="Entity name (e.g. 'project', 'auth_module')")
            predicate: str = Field(description="Relationship (e.g. 'uses', 'depends_on')")
            object: str = Field(description="Target entity (e.g. 'FastAPI', 'database')")

        def _remember(
            content: str,
            room: str = "general",
            metadata: dict[str, Any] | None = None,
            source: str = "",
            ttl: int | None = None,
            tags: list[str] | None = None,
        ) -> str:
            drawer_id = self.palace.remember(
                content,
                room=room,
                metadata=metadata,
                source=source,
                ttl=ttl,
                tags=tags,
            )
            return json.dumps({"stored": True, "id": drawer_id})

        def _recall(query: str, limit: int = 5, room: str | None = None) -> str:
            results = self.palace.recall(query, limit=limit, room=room)
            return json.dumps(
                {"results": [{"content": r["content"], "room": r.get("metadata", {}).get("room", "")} for r in results]},
                ensure_ascii=False,
            )

        def _add_fact(subject: str, predicate: str, object: str) -> str:
            self.palace.add_fact(subject, predicate, object)
            return json.dumps({"added": True, "triple": [subject, predicate, object]})

        return [
            StructuredTool.from_function(
                func=_remember,
                name="mempalace_remember",
                description="Store important information for future sessions. Use for decisions, errors, architecture, user preferences.",
                args_schema=RememberInput,
            ),
            StructuredTool.from_function(
                func=_recall,
                name="mempalace_recall",
                description="Search past memories by semantic similarity. Use to check what you already know.",
                args_schema=RecallInput,
            ),
            StructuredTool.from_function(
                func=_add_fact,
                name="mempalace_add_fact",
                description="Add a structured fact to the knowledge graph. E.g. 'project uses FastAPI'.",
                args_schema=AddFactInput,
            ),
        ]
