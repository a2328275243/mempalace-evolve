"""High-level SDK for mempalace-evolve.

Usage:
    from mempalace_evolve import MemPalace

    palace = MemPalace("~/my-project")
    palace.remember("JWT is used for auth", room="decisions")
    results = palace.recall("how does auth work?")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("mempalace_evolve")


class MemPalace:
    """Main entry point for the memory palace system.

    Provides a simple interface for storing and retrieving memories,
    managing knowledge graphs, and running evolution pipelines.
    """

    def __init__(self, palace_path: str | Path = None, wing: str = "global"):
        """Initialize a MemPalace instance.

        Args:
            palace_path: Path to the palace directory. Defaults to ~/.mempalace
            wing: Wing/project name for scoping memories.
        """
        from mempalace_evolve.core.config import PalaceConfig

        if palace_path is None:
            palace_path = Path.home() / ".mempalace"
        self._path = Path(palace_path).expanduser().resolve()
        self._path.mkdir(parents=True, exist_ok=True)
        self._wing = wing
        self._config = PalaceConfig(str(self._path))
        self._chroma = None
        self._kg = None
        self._layers = None

    @property
    def path(self) -> Path:
        return self._path

    @property
    def wing(self) -> str:
        return self._wing

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        room: str = "general",
        *,
        metadata: dict[str, Any] | None = None,
        source: str = "",
    ) -> str:
        """Store a memory in the palace.

        Args:
            content: The text content to remember.
            room: Room/category (e.g. "decisions", "errors", "config").
            metadata: Optional metadata dict.
            source: Source identifier (file path, URL, etc).

        Returns:
            The drawer ID of the stored memory.
        """
        store = self._get_chroma()
        meta = {
            "wing": self._wing,
            "room": room,
            "source_file": source,
            **(metadata or {}),
        }
        drawer_id = store.add_drawer(content, meta)
        logger.debug("Stored memory %s in %s/%s", drawer_id, self._wing, room)
        return drawer_id

    def recall(
        self,
        query: str,
        *,
        limit: int = 5,
        room: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories by semantic similarity.

        Args:
            query: Natural language query.
            limit: Max results to return.
            room: Optional room filter.

        Returns:
            List of matching memories with content and metadata.
        """
        store = self._get_chroma()
        where = {"wing": self._wing}
        if room:
            where["room"] = room
        return store.search(query, n_results=limit, where=where)

    def forget(self, drawer_id: str) -> bool:
        """Delete a memory by ID."""
        store = self._get_chroma()
        return store.delete_drawer(drawer_id)

    # ------------------------------------------------------------------
    # Knowledge Graph
    # ------------------------------------------------------------------

    def add_fact(self, subject: str, predicate: str, obj: str) -> None:
        """Add a triple to the knowledge graph."""
        kg = self._get_kg()
        kg.add_triple(subject, predicate, obj)

    def query_entity(self, entity: str, direction: str = "both") -> list[dict]:
        """Query knowledge graph for entity relationships."""
        kg = self._get_kg()
        return kg.query_entity(entity, direction=direction)

    # ------------------------------------------------------------------
    # Evolution Pipeline
    # ------------------------------------------------------------------

    def evolve(self, transcript: str | None = None) -> dict:
        """Run one evolution cycle.

        Args:
            transcript: Optional session transcript to extract candidates from.

        Returns:
            Evolution report dict.
        """
        from mempalace_evolve.evolution.pipeline import EvolutionPipeline

        pipeline = EvolutionPipeline(self)
        return pipeline.run(transcript=transcript)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_chroma(self):
        if self._chroma is None:
            from mempalace_evolve.core.chroma_helper import ChromaStore
            self._chroma = ChromaStore(str(self._path / "palace"))
        return self._chroma

    def _get_kg(self):
        if self._kg is None:
            from mempalace_evolve.core.knowledge_graph import KnowledgeGraph
            self._kg = KnowledgeGraph(str(self._path / "knowledge_graph.sqlite3"))
        return self._kg
