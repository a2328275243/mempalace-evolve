"""Base adapter class for connecting MemPalace to any AI agent.

Subclass AgentAdapter to integrate with your agent framework.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from mempalace_evolve.sdk import MemPalace


class AgentAdapter(ABC):
    """Abstract base class for agent adapters.

    Each adapter translates between an agent framework's event model
    and MemPalace's memory operations.
    """

    def __init__(self, palace: MemPalace):
        self.palace = palace

    # ------------------------------------------------------------------
    # Lifecycle events — override in subclasses
    # ------------------------------------------------------------------

    @abstractmethod
    def on_session_start(self, context: dict[str, Any]) -> str | None:
        """Called when a new agent session begins.

        Should retrieve relevant memories and return them as context
        to inject into the agent's prompt/system message.

        Args:
            context: Session metadata (user query, project path, etc.)

        Returns:
            Memory context string to inject, or None.
        """
        ...

    @abstractmethod
    def on_session_end(self, transcript: str, context: dict[str, Any]) -> None:
        """Called when a session ends.

        Should extract memory candidates from the transcript.

        Args:
            transcript: Full session transcript text.
            context: Session metadata.
        """
        ...

    def on_user_input(self, query: str, context: dict[str, Any]) -> str | None:
        """Called on each user input (optional).

        Can retrieve relevant memories for the current query.
        Default implementation does a semantic search.

        Args:
            query: The user's input text.
            context: Additional context (project path, etc.)

        Returns:
            Memory context string, or None.
        """
        results = self.palace.recall(query, limit=3)
        if not results:
            return None
        lines = [f"- {r.get('content', '')[:200]}" for r in results]
        return "Relevant memories:\n" + "\n".join(lines)

    def on_error(self, error: str, context: dict[str, Any]) -> None:
        """Called when the agent encounters an error (optional).

        Default stores it in the error_patterns room.
        """
        self.palace.remember(
            f"Error: {error}",
            room="error_patterns",
            metadata={"type": "error", **context},
        )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def remember(self, content: str, room: str = "general", **kwargs) -> str:
        """Shortcut to palace.remember()."""
        return self.palace.remember(content, room=room, **kwargs)

    def recall(self, query: str, **kwargs) -> list[dict]:
        """Shortcut to palace.recall()."""
        return self.palace.recall(query, **kwargs)
