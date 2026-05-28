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

    def __init__(self, palace_path: str | Path = None, wing: str = "global",
                 auto_evolve: bool = False, evolve_interval: int = 3600,
                 scoring_config: dict[str, Any] | None = None):
        """Initialize a MemPalace instance.

        Args:
            palace_path: Path to the palace directory. Defaults to ~/.mempalace
            wing: Wing/project name for scoping memories.
            auto_evolve: If True, run evolve() automatically in background.
            evolve_interval: Seconds between auto-evolve cycles (default 3600 = 1h).
            scoring_config: Per-room scoring rules. Example:
                {
                    "rooms": {
                        "decisions": {"weight": 2.0, "never_delete": True},
                        "errors": {"weight": 1.5, "min_score": 0.4},
                    },
                    "thresholds": {
                        "promote": 0.7,
                        "discard": 0.3,
                        "stale_days": 180,
                    }
                }
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
        self._evolve_thread = None
        self._evolve_stop = None
        self._scoring_config = scoring_config or {}
        self._last_evolve_at: str | None = None

        if auto_evolve:
            self._start_auto_evolve(evolve_interval)

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
        from mempalace_evolve.core.chroma_helper import add_drawer, _make_drawer_id
        from mempalace_evolve.exceptions import StorageError, ValidationError
        import hashlib

        if not content or not content.strip():
            raise ValidationError("Memory content cannot be empty")

        collection = self._get_collection()
        if collection is None:
            raise StorageError("Failed to initialize ChromaDB collection")

        # 用内容 hash 保证每条记忆有唯一 ID
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        source_key = source or f"sdk_{content_hash}"
        chunk_index = 0
        add_drawer(
            collection,
            wing=self._wing,
            room=room,
            content=content,
            source_file=source_key,
            chunk_index=chunk_index,
            added_by="sdk",
            extra_meta=metadata,
        )
        drawer_id = _make_drawer_id(self._wing, room, source_key, chunk_index)
        logger.debug("Stored memory %s in %s/%s", drawer_id, self._wing, room)
        return drawer_id

    def recall(
        self,
        query: str,
        *,
        limit: int = 5,
        room: str | None = None,
        threshold: float = 0.8,
        hybrid: bool = True,
        cross_wing: bool | str = "auto",
    ) -> list[dict[str, Any]]:
        """Search memories by semantic similarity + knowledge graph expansion.

        Args:
            query: Natural language query.
            limit: Max results to return.
            room: Optional room filter.
            threshold: Max distance to include (0-1, lower = more similar).
            hybrid: If True, expand results via KG entity relationships.
            cross_wing: Memory sharing mode:
                - "auto" (default): search current wing first, fallback to all
                  wings if no good results found. Zero config, fully automatic.
                - True: always search ALL wings
                - False: strictly only current wing (no cross-project)

        Returns:
            List of matching memories with content and metadata.
        """
        collection = self._get_collection()
        if collection is None:
            return []

        # Determine wing filter
        search_all = cross_wing is True
        auto_fallback = cross_wing == "auto"

        if search_all:
            where = {"room": room} if room else None
        else:
            where = {"wing": self._wing}
            if room:
                where = {"$and": [{"wing": self._wing}, {"room": room}]}

        try:
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where,
            )
        except Exception as e:
            logger.warning("Recall failed: %s", e)
            return []

        output = []
        seen_ids = set()
        if results and results.get("documents"):
            docs = results["documents"][0]
            metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
            dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
            ids = results["ids"][0] if results.get("ids") else []
            for doc, meta, dist, did in zip(docs, metas, dists, ids):
                if dist <= threshold:
                    output.append({"content": doc, "metadata": meta, "distance": dist})
                    seen_ids.add(did)

            # Feedback loop: touch recalled memories
            if output and ids:
                recalled_ids = ids[:len(output)]
                try:
                    from mempalace_evolve.core.lifecycle import touch_drawers
                    touch_drawers(collection, recalled_ids)
                except Exception:
                    pass

        # Auto fallback: if current wing has no good results, search all wings
        if auto_fallback and not output:
            try:
                fallback_where = {"room": room} if room else None
                fallback_results = collection.query(
                    query_texts=[query], n_results=limit, where=fallback_where,
                )
                if fallback_results and fallback_results.get("documents"):
                    fb_docs = fallback_results["documents"][0]
                    fb_metas = fallback_results["metadatas"][0] if fallback_results.get("metadatas") else [{}] * len(fb_docs)
                    fb_dists = fallback_results["distances"][0] if fallback_results.get("distances") else [0.0] * len(fb_docs)
                    fb_ids = fallback_results["ids"][0] if fallback_results.get("ids") else []
                    for doc, meta, dist, did in zip(fb_docs, fb_metas, fb_dists, fb_ids):
                        if dist <= threshold and did not in seen_ids:
                            output.append({
                                "content": doc, "metadata": meta,
                                "distance": dist, "source": "cross_wing_fallback",
                            })
                            seen_ids.add(did)
            except Exception:
                pass

        # Hybrid: expand via knowledge graph
        if hybrid and output:
            kg_extra = self._kg_expand(output, seen_ids, limit)
            output.extend(kg_extra)

        return output

    def forget(self, drawer_id: str) -> bool:
        """Delete a memory by ID."""
        collection = self._get_collection()
        if collection is None:
            return False
        try:
            collection.delete(ids=[drawer_id])
            return True
        except Exception:
            return False

    def digest(self, conversation: str | list[dict]) -> dict:
        """Auto-extract and store knowledge from a conversation.

        Args:
            conversation: Either a transcript string, or a list of
                message dicts [{"role": "user", "content": "..."}].

        Returns:
            Dict with extracted count and stored items.
        """
        from mempalace_evolve.evolution.candidate import CandidateExtractor

        if isinstance(conversation, list):
            transcript = "\n".join(
                f"{m.get('role', 'user')}: {m.get('content', '')}"
                for m in conversation
            )
        else:
            transcript = conversation

        extractor = CandidateExtractor()
        candidates = extractor.extract(transcript)

        stored = []
        for c in candidates:
            room = c.get("type", "general")
            drawer_id = self.remember(
                c["content"], room=room,
                metadata={"score": c["score"], "source": "digest"},
            )
            stored.append({"id": drawer_id, "type": room, "score": c["score"]})

        # Auto-extract knowledge graph triples from stored content
        triples = []
        try:
            triples = self._extract_triples(candidates)
            for s, p, o in triples:
                self.add_fact(s, p, o)
        except Exception as e:
            logger.debug("KG triple extraction skipped: %s", e)

        return {"extracted": len(candidates), "stored": stored, "triples": len(triples)}

    def context_for(self, query: str, *, limit: int = 10, max_tokens: int = 2000) -> str:
        """Get relevant context for a new query (for prompt injection).

        Args:
            query: The user's new question/message.
            limit: Max memories to search.
            max_tokens: Approximate max characters to return (prevents context overflow).

        Returns:
            Formatted string ready to inject into system prompt.
        """
        results = self.recall(query, limit=limit)
        if not results:
            return ""
        lines = []
        total_len = 0
        for r in results:
            meta = r.get("metadata", {})
            room = meta.get("room", "")
            prefix = f"[{room}] " if room else ""
            line = f"- {prefix}{r['content'][:500]}"
            if total_len + len(line) > max_tokens:
                break
            lines.append(line)
            total_len += len(line) + 1
        return "\n".join(lines)

    def export(self, format: str = "json", output: str | None = None):
        """Export all memories to JSON or Markdown.

        Args:
            format: "json" or "markdown".
            output: Optional file path. If None, returns data directly.

        Returns:
            Dict (json) or str (markdown).
        """
        from mempalace_evolve.export import export_json, export_markdown

        collection = self._get_collection()
        if format == "markdown":
            return export_markdown(collection, wing=self._wing, output=output)
        return export_json(collection, wing=self._wing, output=output)

    def import_memories(self, source: str | Path | list[dict]) -> dict:
        """Import memories from JSON file or list of dicts.

        Args:
            source: Path to a JSON file, or a list of memory dicts.
                Each dict should have: {"content": str, "room": str}
                Optional fields: "metadata", "wing" (defaults to current wing).

        Returns:
            {"imported": int, "skipped": int, "errors": list}
        """
        import json

        if isinstance(source, (str, Path)):
            with open(source, "r", encoding="utf-8") as f:
                items = json.load(f)
        else:
            items = source

        if not isinstance(items, list):
            items = [items]

        imported = 0
        skipped = 0
        errors = []

        for item in items:
            content = item.get("content", "").strip()
            if not content:
                skipped += 1
                continue
            room = item.get("room", "general")
            metadata = item.get("metadata")
            try:
                self.remember(content, room=room, metadata=metadata)
                imported += 1
            except Exception as e:
                errors.append({"content": content[:50], "error": str(e)})

        return {"imported": imported, "skipped": skipped, "errors": errors}

    def stats(self) -> dict:
        """Get memory palace statistics.

        Returns:
            Dict with total count, per-room distribution, KG entity count, etc.
        """
        collection = self._get_collection()
        result = {"wing": self._wing, "total": 0, "rooms": {}, "kg_entities": 0}

        if not collection:
            return result

        try:
            all_items = collection.get(
                where={"wing": self._wing},
                include=["metadatas"],
            )
            if all_items and all_items.get("ids"):
                result["total"] = len(all_items["ids"])
                for meta in all_items["metadatas"]:
                    room = meta.get("room", "general")
                    result["rooms"][room] = result["rooms"].get(room, 0) + 1
        except Exception:
            pass

        try:
            kg = self._get_kg()
            entities = kg.get_all_entity_names()
            result["kg_entities"] = len(entities) if entities else 0
        except Exception:
            pass

        return result

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
        """Run one evolution cycle (incremental: only processes new memories).

        Includes: candidate extraction → review → promote → consolidation → compress.
        Respects scoring_config for per-room weights and thresholds.

        Args:
            transcript: Optional session transcript to extract candidates from.

        Returns:
            Evolution report dict.
        """
        from datetime import datetime, timezone
        from mempalace_evolve.evolution.pipeline import EvolutionPipeline

        # Resolve scoring thresholds from config
        thresholds = self._scoring_config.get("thresholds", {})
        min_score = thresholds.get("discard", 0.30)
        promote_score = thresholds.get("promote", 0.45)
        stale_days = thresholds.get("stale_days", 180)

        pipeline = EvolutionPipeline(self)
        report = pipeline.run(transcript=transcript)

        # Consolidation: merge similar memories (incremental — only today's)
        try:
            collection = self._get_collection()
            if collection and collection.count() > 1:
                from mempalace_evolve.core.consolidation import (
                    get_today_drawers, identify_duplicates, merge_similar_drawers,
                )
                today = get_today_drawers(collection, wing=self._wing)
                if today:
                    dupes = identify_duplicates(today)
                    if dupes:
                        merged = merge_similar_drawers(collection, dupes, dry_run=False)
                        report["merged"] = merged
        except Exception as e:
            logger.debug("Consolidation skipped: %s", e)

        # Forgetting curve: compress old unused memories
        try:
            collection = self._get_collection()
            if collection and collection.count() > 10:
                from mempalace_evolve.core.lifecycle import find_compress_candidates
                candidates = find_compress_candidates(collection, compress_after_days=60)
                compress_count = sum(len(v) for v in candidates.values())
                if compress_count > 0:
                    report["compress_candidates"] = compress_count
        except Exception as e:
            logger.debug("Compress check skipped: %s", e)

        # Opportunistic evolve with configured thresholds
        try:
            collection = self._get_collection()
            if collection:
                from mempalace_evolve.evolution.opportunistic import (
                    run_opportunistic_evolve,
                )
                # Apply per-room never_delete protection
                rooms_config = self._scoring_config.get("rooms", {})
                protected_rooms = [
                    r for r, cfg in rooms_config.items()
                    if cfg.get("never_delete", False)
                ]

                opp = run_opportunistic_evolve(
                    collection,
                    dry_run=False,
                    min_score=min_score,
                    promote_score=promote_score,
                    stale_days=stale_days,
                    protected_rooms=protected_rooms,
                )
                if opp.get("success"):
                    report["opportunistic"] = opp["results"]
        except Exception as e:
            logger.debug("Opportunistic evolve skipped: %s", e)

        # Record evolve timestamp for incremental next run
        self._last_evolve_at = datetime.now(timezone.utc).isoformat()

        return report

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_collection(self):
        if self._chroma is None:
            from mempalace_evolve.core.chroma_helper import get_collection
            self._chroma = get_collection(str(self._path / "palace"), create=True)
        return self._chroma

    def _extract_triples(self, candidates: list[dict]) -> list[tuple[str, str, str]]:
        """Extract subject-predicate-object triples from candidates using patterns."""
        import re
        triples = []
        patterns = [
            # "X uses Y", "X 使用 Y"
            (r"(?:use|uses|using|用|使用)\s+(\w[\w\s]*\w)", "uses"),
            # "X built with Y", "X 基于 Y"
            (r"(?:built.with|based.on|基于)\s+(\w[\w\s]*\w)", "built_with"),
            # "X stores in Y", "X 存储在 Y"
            (r"(?:stores?.in|saved?.in|存储在|保存在)\s+(\w[\w\s]*\w)", "stores_in"),
            # "decided to use X", "决定用 X"
            (r"(?:decided?.to.use|决定用|选择了)\s+(\w[\w\s]*\w)", "decided"),
            # "X depends on Y"
            (r"(?:depends?.on|依赖)\s+(\w[\w\s]*\w)", "depends_on"),
            # "X replaced Y", "X 替换 Y"
            (r"(?:replaced?|替换了?|换成)\s+(\w[\w\s]*\w)", "replaced"),
        ]
        for c in candidates:
            content = c.get("content", "")[:500]
            for pattern, predicate in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches[:2]:
                    obj = match.strip()[:50]
                    if len(obj) > 2:
                        subj = self._wing or "project"
                        triples.append((subj, predicate, obj))
        return triples

    def _kg_expand(self, results: list[dict], seen_ids: set, limit: int) -> list[dict]:
        """Expand recall results via knowledge graph relationships.

        Extracts entities from top results, queries KG for related entities,
        then fetches memories linked to those entities.
        """
        try:
            kg = self._get_kg()
            collection = self._get_collection()
            if not kg or not collection:
                return []
        except Exception:
            return []

        # Extract entity names from result content (simple: use words > 3 chars)
        import re
        entities = set()
        for r in results[:3]:  # Only expand from top 3
            content = r.get("content", "")
            # Extract capitalized words and Chinese terms
            words = re.findall(r'[A-Z][a-z]+(?:[A-Z][a-z]+)*|\b\w{4,}\b', content)
            entities.update(w for w in words[:5])

        if not entities:
            return []

        # Query KG for related entities
        related_ids = set()
        for entity in list(entities)[:5]:
            try:
                rels = kg.query_entity(entity, direction="both")
                if isinstance(rels, list):
                    for rel in rels:
                        src = rel.get("source_closet", "")
                        if src and src not in seen_ids:
                            related_ids.add(src)
            except Exception:
                continue

        if not related_ids:
            return []

        # Fetch the related memories
        extra = []
        fetch_ids = list(related_ids)[:limit]
        try:
            fetched = collection.get(ids=fetch_ids, include=["documents", "metadatas"])
            if fetched and fetched.get("documents"):
                for doc, meta in zip(fetched["documents"], fetched["metadatas"]):
                    if meta.get("wing") == self._wing:
                        extra.append({
                            "content": doc,
                            "metadata": meta,
                            "distance": -1,  # KG-expanded, no vector distance
                            "source": "kg_expansion",
                        })
        except Exception:
            pass

        return extra

    def _get_kg(self):
        if self._kg is None:
            from mempalace_evolve.core.knowledge_graph import KnowledgeGraph
            self._kg = KnowledgeGraph(str(self._path / "knowledge_graph.sqlite3"))
        return self._kg

    def _start_auto_evolve(self, interval: int):
        """Start background thread that runs evolve() periodically."""
        import threading

        self._evolve_stop = threading.Event()

        def _loop():
            while not self._evolve_stop.wait(interval):
                try:
                    self.evolve()
                    logger.debug("Auto-evolve completed")
                except Exception as e:
                    logger.debug("Auto-evolve failed: %s", e)

        self._evolve_thread = threading.Thread(
            target=_loop, daemon=True, name="mempalace-auto-evolve"
        )
        self._evolve_thread.start()
        logger.info("Auto-evolve started (interval=%ds)", interval)

    def stop_auto_evolve(self):
        """Stop the background auto-evolve thread."""
        if self._evolve_stop:
            self._evolve_stop.set()
            self._evolve_thread = None
            logger.info("Auto-evolve stopped")
