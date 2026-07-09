"""High-level SDK for mempalace-evolve.

Usage:
    from mempalace_evolve import MemPalace

    palace = MemPalace("~/my-project")
    palace.remember("JWT is used for auth", room="decisions")
    results = palace.recall("how does auth work?")
"""

from __future__ import annotations

import os
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Self
from mempalace_evolve.advanced_query import AdvancedQuery
from mempalace_evolve.models import (
    BatchRememberInput,
    BatchRememberResult,
    BatchRecallInput,
    BatchRecallResult,
    BatchForgetResult,
)


logger = logging.getLogger("mempalace_evolve")

# Memory type constants
SEMANTIC = "semantic"      # Facts, configs, decisions (project-scoped)
EPISODIC = "episodic"      # Specific events, conversations (project-scoped)
PROCEDURAL = "procedural"  # Experiences, patterns, lessons (globally shared)

# Room → memory type mapping (auto-classification)
_ROOM_TYPE_MAP = {
    "decisions": SEMANTIC,
    "config": SEMANTIC,
    "architecture": SEMANTIC,
    "project": SEMANTIC,
    "preferences": SEMANTIC,
    "errors": PROCEDURAL,       # Error patterns are transferable
    "error_patterns": PROCEDURAL,
    "daily_summaries": EPISODIC,
    "progress": EPISODIC,
    "general": EPISODIC,
}


class MemPalace:
    """Main entry point for the memory palace system.

    Provides a simple interface for storing and retrieving memories,
    managing knowledge graphs, and running evolution pipelines.
    """

    def __init__(self, palace_path: str | Path = None, wing: str = "global",
                 auto_evolve: bool = False, evolve_interval: int = 3600,
                 llm_enabled: bool | None = None,
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
        if llm_enabled is not None:
            self._llm_enabled = llm_enabled
        else:
            # Auto-detect: enable if any common API key is in env
            self._llm_enabled = bool(
                os.environ.get("OPENAI_API_KEY")
                or os.environ.get("ANTHROPIC_API_KEY")
                or os.environ.get("GEMINI_API_KEY")
            )
        self._last_evolve_at: str | None = None
        # Working memory: session-level cache to avoid repeated searches
        self._working_memory: list[dict] = []
        self._working_memory_topic: str = ""
        self._working_memory_topic_words: set | None = None
        self._advanced_query: AdvancedQuery | None = None
        self._auto_evolve = auto_evolve
        self._evolve_interval = evolve_interval
        if auto_evolve:
            self._start_auto_evolve(evolve_interval)

    def __enter__(self) -> Self:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit: auto-close."""
        self.close()
        return False

    @property
    def path(self) -> Path:
        return self._path

    @property
    def wing(self) -> str:
        return self._wing

    @property
    def advanced_query(self):
        """Access the AdvancedQuery interface for hybrid search and complex filtering."""
        if self._advanced_query is None:
            self._advanced_query = AdvancedQuery(self)
        return self._advanced_query

    def __repr__(self) -> str:
        """Human-readable representation of this palace instance."""
        return f"<MemPalace wing={self._wing!r} path={self._path}>"

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        room: str = "general",
        *,
        memory_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        source: str = "",
        ttl: int | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Store a memory in the palace.

        Args:
            content: The text content to remember.
            room: Room/category (e.g. "decisions", "errors", "config").
            memory_type: "semantic", "episodic", or "procedural".
                If None, auto-classified by room type.
                - procedural memories are globally shared across all wings.
                - semantic/episodic memories stay in the current wing.
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

        # Auto-classify memory type based on room
        mtype = memory_type or _ROOM_TYPE_MAP.get(room, EPISODIC)

        # Dedup: O(1) content_hash lookup instead of O(N) get-all
        collection = self._get_collection()
        content_hash = hashlib.md5(content.encode()).hexdigest()[:12]
        if collection is not None:
            try:
                existing = collection.get(
                    where={"$and": [{"wing": self._wing}, {"room": room}, {"content_hash": content_hash}]},
                    include=["documents"],
                    limit=1,
                )
                if existing and existing.get("ids"):
                    logger.debug("Dedup hit: %s", existing["ids"][0])
                    return existing["ids"][0]
            except Exception as _e:
                logger.debug("Dedup check failed: %s", _e)


        if collection is None:
            raise StorageError("Failed to initialize ChromaDB collection")

        # Merge memory_type into metadata
        extra_meta = dict(metadata) if metadata else {}
        extra_meta["memory_type"] = mtype
        extra_meta["recall_count"] = extra_meta.get("recall_count", 0)
        extra_meta["cross_wing_hits"] = extra_meta.get("cross_wing_hits", 0)

        # TTL: auto-expire after ttl seconds
        if ttl is not None:
            expire_at = datetime.now(timezone.utc).timestamp() + ttl
            extra_meta["expire_at"] = expire_at

        # RBAC-style tags for access control labels
        if tags:
            extra_meta["tags"] = ",".join(tags)

        # --- Similarity dedup: check for similar memories BEFORE storing ---
        dedup_threshold = self._scoring_config.get("dedup_threshold", 0.85)
        if dedup_threshold > 0:
            from mempalace_evolve.core.dedup import check_and_deduplicate
            dedup_result = check_and_deduplicate(
                collection=collection,
                wing=self._wing,
                content=content,
                room=room,
                threshold=dedup_threshold,
                action=self._scoring_config.get("dedup_action", "skip"),
            )
            if dedup_result["action"] == "skip":
                logger.info("Skipped duplicate memory (similarity: %.2f)", dedup_result["similar"][0]["similarity"])
                # Return existing ID, no need to store
                return dedup_result["matched_id"]
            elif dedup_result["action"] == "merge":
                # Merge similar content into existing memory
                from mempalace_evolve.core.dedup import merge_similar_content
                existing_content = dedup_result["matched_content"]
                merged_content = merge_similar_content(existing_content, content)
                collection.update(
                    ids=[dedup_result["matched_id"]],
                    documents=[merged_content]
                )
                logger.info("Merged duplicate memory into %s", dedup_result["matched_id"])
                # Update metadata recall_count, etc.
                return dedup_result["matched_id"]

        # --- Contradiction detection: check if new memory conflicts with existing ---
        if mtype == SEMANTIC and room in ("decisions", "config", "architecture"):
            self._handle_contradiction(collection, content, room, extra_meta)

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
            extra_meta=extra_meta,
            check_existing=False,
        )
        drawer_id = _make_drawer_id(self._wing, room, source_key, chunk_index)
        logger.debug("Stored memory %s in %s/%s", drawer_id, self._wing, room)

        return drawer_id

    def get_due_for_review(self) -> list[dict]:
        """Get memories due for spaced repetition review.

        Returns:
            List of memory dicts due for review.
        """
        from mempalace_evolve.core.spaced_repetition import get_memories_due_for_review
        collection = self._get_collection()
        if not collection:
            return []
        return get_memories_due_for_review(collection, wing=self._wing)

    def mark_reviewed(self, drawer_id: str) -> bool:
        """Mark a memory as reviewed (for spaced repetition).

        Args:
            drawer_id: ID of the memory.

        Returns:
            True if successful.
        """
        from mempalace_evolve.core.spaced_repetition import mark_reviewed
        collection = self._get_collection()
        if not collection:
            return False
        # Get current interval index
        try:
            data = collection.get(ids=[drawer_id], include=["metadatas"])
            if data and data.get("metadatas"):
                meta = data["metadatas"][0]
                interval_idx = int(meta.get("interval_index", 0))
                return mark_reviewed(collection, drawer_id, interval_idx)
        except Exception as _e:
            logger.debug("Snooze failed", exc_info=_e)
            pass
        return mark_reviewed(collection, drawer_id, 0)

    def snooze_memory(self, drawer_id: str, days: int = 1) -> bool:
        """Snooze a memory for N days.

        Args:
            drawer_id: ID of the memory.
            days: Days to snooze.

        Returns:
            True if successful.
        """
        from mempalace_evolve.core.spaced_repetition import snooze
        collection = self._get_collection()
        if not collection:
            return False
        return snooze(collection, drawer_id, days)

    def score_memories(self) -> dict:
        """Score all memories by importance (auto-scoring).

        Returns:
            Dict with scoring results.
        """
        from mempalace_evolve.core.importance_scorer import score_all_memories
        return score_all_memories(self)

    def top_memories(self, n: int = 10) -> list[dict]:
        """Get top N most important memories.

        Args:
            n: Number of memories to return.

        Returns:
            List of top memory dicts.
        """
        from mempalace_evolve.core.importance_scorer import get_top_memories
        return get_top_memories(self, n)

    def find_similar(self, content: str, room: str | None = None, threshold: float = 0.85) -> list[dict]:
        """Find similar memories to the given content.

        Args:
            content: Content to search for.
            room: Optional room filter.
            threshold: Minimum similarity (0-1).

        Returns:
            List of similar memory dicts.
        """
        from mempalace_evolve.core.dedup import find_similar_memories
        collection = self._get_collection()
        if not collection:
            return []
        return find_similar_memories(collection, self._wing, content, room, threshold)

    def recall(
        self,
        query: str,
        *,
        limit: int = 5,
        room: str | None = None,
        threshold: float = 0.8,
        hybrid: bool = True,
    ) -> list[dict[str, Any]]:
        """Search memories: current wing + global procedural (experiences).

        Strategy:
        1. Check working memory cache (same topic → skip search)
        2. Search current wing (all memory types)
        3. ALWAYS search global procedural memories (experiences/patterns)
        4. Merge, deduplicate, track cross-wing hits for smart promotion
        5. Optionally expand via knowledge graph

        Args:
            query: Natural language query.
            limit: Max results to return.
            room: Optional room filter.
            threshold: Max distance (0-1, lower = more similar).
            hybrid: If True, expand via KG relationships.

        Returns:
            List of matching memories with content and metadata.
        """
        # Working memory cache: if same topic, return cached results (fast string prefix check)
        topic_sim = 0.0
        if self._working_memory_topic and query:
            # Use simple Jaccard similarity on word-level trigrams for speed
            query_words = set(query.lower().split())
            topic_words = self._working_memory_topic_words
            if not topic_words:
                topic_words = set(self._working_memory_topic.lower().split())
                self._working_memory_topic_words = topic_words
            if query_words and topic_words:
                intersection = query_words & topic_words
                union = query_words | topic_words
                topic_sim = len(intersection) / len(union) if union else 0.0
        if topic_sim > 0.7 and self._working_memory:
            return self._working_memory[:limit]

        collection = self._get_collection()
        if collection is None:
            return []

        output = []
        seen_ids = set()

        # --- Search 1: Current wing (all types) ---
        where_wing = {"wing": self._wing}
        if room:
            where_wing = {"$and": [{"wing": self._wing}, {"room": room}]}

        try:
            results = collection.query(
                query_texts=[query], n_results=limit * 2, where=where_wing,
            )
            if results and results.get("documents"):
                docs = results["documents"][0]
                metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
                dists = results["distances"][0] if results.get("distances") else [0.0] * len(docs)
                ids = results["ids"][0] if results.get("ids") else []
                for doc, meta, dist, did in zip(docs, metas, dists, ids):
                    if dist <= threshold:
                        score = self._compute_recall_score(dist, meta)
                        output.append({
                            "content": doc, "metadata": meta,
                            "distance": dist, "_score": score,
                        })
                        seen_ids.add(did)
        except Exception as e:
            logger.warning("Wing recall failed: %s", e)

        # --- Search 2: Global procedural memories (always, regardless of wing results) ---
        try:
            proc_where = {"memory_type": PROCEDURAL}
            proc_results = collection.query(
                query_texts=[query], n_results=limit, where=proc_where,
            )
            if proc_results and proc_results.get("documents"):
                p_docs = proc_results["documents"][0]
                p_metas = proc_results["metadatas"][0] if proc_results.get("metadatas") else [{}] * len(p_docs)
                p_dists = proc_results["distances"][0] if proc_results.get("distances") else [0.0] * len(p_docs)
                p_ids = proc_results["ids"][0] if proc_results.get("ids") else []
                for doc, meta, dist, did in zip(p_docs, p_metas, p_dists, p_ids):
                    if dist <= threshold and did not in seen_ids:
                        # Track cross-wing hit for smart promotion
                        if meta.get("wing") != self._wing:
                            self._track_cross_wing_hit(collection, did, meta)
                        score = self._compute_recall_score(dist, meta)
                        output.append({
                            "content": doc, "metadata": meta,
                            "distance": dist, "_score": score,
                            "source": "procedural_global",
                        })
                        seen_ids.add(did)
        except Exception as _e:
            logger.debug("Procedural search failed: %s", _e)

        # --- Feedback loop: touch recalled memories ---
        if output:
            recalled_ids = list(seen_ids)[:limit]
            try:
                from mempalace_evolve.core.lifecycle import touch_drawers
                touch_drawers(collection, recalled_ids)
            except Exception as _e:
                logger.debug("Touch-drawers failed", exc_info=_e)

        # --- Hybrid: expand via knowledge graph ---
        if hybrid and output:
            kg_extra = self._kg_expand(output, seen_ids, limit)
            output.extend(kg_extra)

        # --- Sort by composite score (recency + relevance + importance) ---
        output.sort(key=lambda x: x.get("_score", 0), reverse=True)

        # --- Update working memory cache ---
        self._working_memory = output
        self._working_memory_topic = query

        return output[:limit]  # Return top-scored results up to limit

    def _track_cross_wing_hit(self, collection, drawer_id: str, meta: dict):
        """Track when a memory is recalled from a different wing.

        If a memory gets hit by 3+ different wings, it's universally useful
        and should be promoted to procedural type (handled by evolve).
        """
        try:
            hits = int(meta.get("cross_wing_hits", 0)) + 1
            meta["cross_wing_hits"] = hits
            collection.update(ids=[drawer_id], metadatas=[meta])
        except Exception as _e:
            logger.debug("Silent exception", exc_info=_e)

    def _compute_recall_score(self, distance: float, meta: dict) -> float:
        """Compute composite recall score: relevance + recency - stale penalty.

        Formula inspired by Stanford Generative Agents:
            score = relevance * 0.5 + recency * 0.3 + importance * 0.2

        - relevance: 1 - distance (vector similarity)
        - recency: exponential decay based on days since last access
        - importance: from metadata (enhanced_importance or default 0.5)
        - stale penalty: -0.3 if marked stale
        """
        # Relevance: invert distance (0 = perfect match → 1.0)
        relevance = max(0.0, 1.0 - distance)

        # Recency: exponential decay, half-life = 30 days
        recency = 0.5  # default if no timestamp
        last_accessed = meta.get("last_accessed") or meta.get("added_at", "")
        if last_accessed:
            try:
                if "T" in str(last_accessed):
                    ts = datetime.fromisoformat(str(last_accessed).replace("Z", "+00:00"))
                else:
                    ts = datetime.fromisoformat(str(last_accessed))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                days_ago = (datetime.now(timezone.utc) - ts).total_seconds() / 86400
                recency = math.exp(-0.023 * days_ago)  # half-life ≈ 30 days
            except (ValueError, TypeError):
                pass

        # Importance
        importance = 0.5
        try:
            importance = float(meta.get("enhanced_importance",
                              meta.get("importance", 0.5)))
        except (ValueError, TypeError):
            pass

        # Composite score
        score = relevance * 0.5 + recency * 0.3 + importance * 0.2

        # Stale penalty: deprioritize outdated memories
        if meta.get("stale") or meta.get("status") == "stale":
            score -= 0.3

        # Superseded penalty: memory has been replaced by newer info
        if meta.get("status") == "superseded":
            score -= 0.4

        return round(score, 4)

    def _handle_contradiction(self, collection, new_content: str, room: str,
                              new_meta: dict):
        """Detect and handle contradictions with existing memories.

        When a new semantic memory (decisions/config) is stored, check if
        it contradicts an existing one in the same room. If so, mark the
        old memory as superseded.

        Uses lightweight heuristic: same room + high vector similarity +
        different content = likely update/contradiction.
        """
        try:
            where = {"$and": [{"wing": self._wing}, {"room": room}]}
            existing = collection.query(
                query_texts=[new_content], n_results=3, where=where,
            )
            if not existing or not existing.get("documents"):
                return
            docs = existing["documents"][0]
            metas = existing["metadatas"][0]
            dists = existing["distances"][0]
            ids = existing["ids"][0]

            for doc, meta, dist, did in zip(docs, metas, dists, ids):
                # Same topic (< 0.5 distance) but not identical content
                if dist < 0.5 and doc.strip() != new_content.strip():
                    # Mark old memory as superseded
                    meta["status"] = "superseded"
                    meta["superseded_by"] = new_content[:100]
                    meta["superseded_at"] = datetime.now(timezone.utc).isoformat()
                    collection.update(ids=[did], metadatas=[meta])
                    logger.debug("Marked memory %s as superseded", did[:20])
        except Exception as _e:
            logger.debug("Contradiction detection skipped: %s", _e)

    def forget(self, drawer_id: str) -> bool:
        """Delete a memory by ID."""
        collection = self._get_collection()
        if collection is None:
            return False
        try:
            collection.delete(ids=[drawer_id])
            return True
        except Exception as _e:
            logger.warning("Operation failed: %s", _e)
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
        # Handle export wrapper format: {"memories": [...]}
        if isinstance(items, dict) and "memories" in items:
            items = items["memories"]

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

        return {"imported": imported, "skipped": skipped, "errors": errors, "added": imported}

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
        except Exception as _e:
            logger.debug("Silent exception", exc_info=_e)

        try:
            kg = self._get_kg()
            entities = kg.get_all_entity_names()
            result["kg_entities"] = len(entities) if entities else 0
        except Exception as _e:
            logger.debug("Silent exception", exc_info=_e)

        return result

    # ------------------------------------------------------------------
    # Knowledge Graph
    # ------------------------------------------------------------------

    def add_fact(self, subject: str, predicate: str, obj: str) -> None:
        """Add a triple to the knowledge graph."""
        kg = self._get_kg()
        kg.add_triple(subject, predicate, obj)

    def import_triples(self, triples: list[dict]) -> dict:
        """Import multiple triples in a batch operation.

        Args:
            triples: List of triples, each with subject, predicate, object, etc.

        Returns:
            {"added": int, "skipped": int, "total": int}
        """
        kg = self._get_kg()
        return kg.import_triples(triples)

    def find_entity_by_fuzzy(self, name: str, threshold: float = 0.6) -> list[dict]:
        """Fuzzy-match entity names, useful for 'did you mean?' scenarios.

        Args:
            name: Entity name to search for.
            threshold: Minimum similarity ratio (0-1).

        Returns:
            List of matching entities with name, type, and similarity.
        """
        kg = self._get_kg()
        return kg.find_entity_by_fuzzy(name, threshold=threshold)

    def graph_traverse(self, start_entity: str, max_depth: int = 2, direction: str = "both") -> list[dict]:
        """Traverse the knowledge graph from a starting entity using BFS.

        Args:
            start_entity: Name of the starting entity.
            max_depth: Maximum traversal depth (default 2).
            direction: "outgoing", "incoming", or "both".

        Returns:
            List of edges with depth, subject, predicate, object.
        """
        kg = self._get_kg()
        return kg.graph_traverse(start_entity, max_depth=max_depth, direction=direction)

    def kg_stats(self) -> dict:
        """Return knowledge graph statistics.

        Returns:
            {"entities": int, "triples": int, "current_facts": int, "expired_facts": int, "relationship_types": list}
        """
        kg = self._get_kg()
        return kg.stats()

    def query_entity(self, entity: str, direction: str = "both") -> list[dict]:
        """Query knowledge graph for entity relationships."""
        kg = self._get_kg()
        return kg.query_entity(entity, direction=direction)
    def query_entity_v2(self, entity: str, as_of: str = None) -> dict:
        """Query knowledge graph returning structured result with separate incoming/outgoing lists.

        Args:
            entity: Entity name to query.
            as_of: Optional date string for temporal filtering.

        Returns:
            Dict with 'entity', 'outgoing', 'incoming' keys.
        """
        kg = self._get_kg()
        return kg.query_entity_v2(entity, as_of=as_of)

    def query_path(self, start_entity: str, end_entity: str, max_depth: int = 4) -> list[dict]:
        """Find shortest path between two entities in the knowledge graph.

        Args:
            start_entity: Name of the starting entity.
            end_entity: Name of the target entity.
            max_depth: Maximum traversal depth.

        Returns:
            List of edge dicts forming the path, or empty list if no path found.
        """
        kg = self._get_kg()
        return kg.query_path(start_entity, end_entity, max_depth=max_depth)

    def recall_stream(self, query: str, *, limit: int = 5, room: str | None = None,
                     threshold: float = 0.8, hybrid: bool = True):
        """Stream recall results as a generator.

        Same semantics as recall(), but yields results one-by-one instead of
        returning a batch list. Useful for real-time display in chat interfaces.

        Args:
            query: Natural language query.
            limit: Max results to yield.
            room: Optional room filter.
            threshold: Max distance (0-1, lower = more similar).
            hybrid: If True, expand via KG relationships.

        Yields:
            Dict with content, metadata, distance, _score, source.
        """
        results = self.recall(query, limit=limit, room=room,
                              threshold=threshold, hybrid=hybrid)
        total = len(results)
        for i, item in enumerate(results):
            if i > 0:
                item['_stream_meta'] = {
                    'index': i, 'total': total, 'is_last': i == total - 1,
                }
            yield item


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


    # ------------------------------------------------------------------
    # Lifecycle management (TTL, compression, consolidation)
    # ------------------------------------------------------------------

    def purge_expired(self, ttl_days: int = 90, ttl_summary_days: int = 180) -> dict:
        """Purge expired (TTL) memories from the palace."""
        from mempalace_evolve.core.lifecycle import find_ttl_expired, purge_expired as _pe
        collection = self._get_collection()
        if not collection:
            return {"purged": 0, "purged_ids": []}
        expired = find_ttl_expired(collection, ttl_days=ttl_days, ttl_summary_days=ttl_summary_days, wing=self._wing)
        ids = []
        for item_list in expired.values():
            if isinstance(item_list, list):
                ids.extend(item.get("id", "") for item in item_list if isinstance(item, dict))
        if not ids:
            return {"purged": 0, "purged_ids": []}
        result = _pe(collection, ids)
        result["purged_ids"] = ids
        return result

    def compress_old_memories(self, compress_after_days: int = 60, max_chars: int = 800) -> dict:
        """Compress old, unused memories into shorter summaries."""
        from mempalace_evolve.core.lifecycle import find_compress_candidates, compress_candidates
        collection = self._get_collection()
        if not collection:
            return {"candidates": 0, "compressed": 0}
        candidates = find_compress_candidates(collection, compress_after_days=compress_after_days)
        if not candidates:
            return {"candidates": 0, "compressed": 0}
        if self._chroma is None:
            return {"candidates": sum(len(v) for v in candidates.values()), "compressed": 0}
        archive_col = self._chroma._client.get_or_create_collection(name="mempalace_archive", metadata={"hnsw:space": "cosine"})
        result = compress_candidates(collection, candidates, archive_col, max_chars=max_chars)
        return result

    def consolidate(self, dry_run: bool = False) -> dict:
        """Run daily consolidation: deduplicate and merge similar memories."""
        from mempalace_evolve.core.consolidation import consolidate_daily
        return consolidate_daily(wing=self._wing, dry_run=dry_run)

    
    # ——— stats / introspection ———————————————————————————————————————

    def count_memories(self) -> int:
        """Count total memories in this palace wing."""
        try:
            from mempalace_evolve.core.chroma_helper import get_all_metadata
            collection = self._get_collection()
            if not collection:
                return 0
            items = get_all_metadata(collection)
            return len([i for i in items if i.get("metadata", {}).get("wing") == self._wing])
        except Exception:
            return 0

    def list_rooms(self) -> list[str]:
        """List all distinct rooms used in this palace wing."""
        try:
            from mempalace_evolve.core.chroma_helper import get_all_metadata
            collection = self._get_collection()
            if not collection:
                return []
            items = get_all_metadata(collection)
            rooms = set()
            for i in items:
                meta = i.get("metadata", {})
                if meta.get("wing") == self._wing:
                    rooms.add(meta.get("room", "general"))
            return sorted(rooms)
        except Exception:
            return []

    def count_triples(self) -> int:
        """Count total knowledge graph triples."""
        try:
            from mempalace_evolve.core.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            conn = kg._conn()
            row = conn.execute("SELECT COUNT(*) FROM triples").fetchone()
            return row[0] if row else 0
        except Exception:
            return 0

    def close(self) -> None:
        """Release resources held by this palace instance."""
        self._chroma = None
        self._kg = None
        self.stop_auto_evolve()

    @property
    def _collection(self):
        """Lazily-loaded ChromaDB collection. Cached after first access."""
        if self._chroma is None:
            from mempalace_evolve.core.chroma_helper import get_collection
            self._chroma = get_collection(str(self._path / "palace"), create=True)
        return self._chroma

    @_collection.setter
    def _collection(self, value):
        """Allow resetting the collection cache."""
        self._chroma = value

    def _get_collection(self):
        """Backward-compatible alias for @property _collection."""
        return self._collection

    def _ensure_initialized(self) -> None:
        """Ensure all backend services (ChromaDB, KG) are initialized.

        This unified lifecycle hook replaces scattered ad-hoc initialization
        checks throughout the codebase. Call once at the start of any
        public-facing method to guarantee consistent state.
        """
        # Lazy-init core services
        _ = self._collection
        _ = self._kg_store



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
        except Exception as _e:
            logger.warning("Query failed: %s", _e)
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
            except Exception as _e:
                logger.debug("Item skipped", exc_info=_e)
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
        except Exception as _e:
            logger.debug("Silent exception", exc_info=_e)

        return extra

    @property
    def _kg_store(self):
        """Lazily-loaded knowledge graph. Cached after first access."""
        if self._kg is None:
            from mempalace_evolve.core.knowledge_graph import KnowledgeGraph
            self._kg = KnowledgeGraph(str(self._path / "knowledge_graph.sqlite3"))
        return self._kg

    def _get_kg(self):
        """Backward-compatible alias for @property _kg_store."""
        return self._kg_store

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


    def store(self, content, room="general", source=None,
              memory_type=None, metadata=None, tags=None,
              ttl=None):
        """Alias for remember() ? store a single memory."""
        return self.remember(content, room=room, memory_type=memory_type,
                             metadata=metadata, source=source or "",
                             tags=tags, ttl=ttl)
    def batch_remember(
        self,
        memories: list[dict[str, Any]],
    ) -> BatchRememberResult:
        """Store multiple memories in a single batch operation.

        Args:
            memories: List of memory dicts, each with:
                - content (str, required)
                - room (str, default "general")
                - metadata (dict, optional)
                - source (str, optional)
                - ttl (int, seconds until expiry, optional)
                - tags (list[str], optional)

        Returns:
            BatchRememberResult with total/stored/duplicates/ids.
        """
        from mempalace_evolve.core.chroma_helper import batch_add_drawers, _make_drawer_id
        import hashlib

        collection = self._get_collection()
        if collection is None:
            return {"added": 0, "skipped": 0, "ids": []}

        drawers = []
        ids = []
        for mem in memories:
            content_text = str(mem.get("content", ""))
            if not content_text.strip():
                ids.append("")  # placeholder for skipped invalid item
                continue
            room = str(mem.get("room", "general"))
            meta = dict(mem.get("metadata") or {})
            source = str(mem.get("source", ""))

            mtype = meta.get("memory_type") or _ROOM_TYPE_MAP.get(room, EPISODIC)
            meta["memory_type"] = mtype
            meta["recall_count"] = meta.get("recall_count", 0)
            meta["cross_wing_hits"] = meta.get("cross_wing_hits", 0)

            ttl_val = mem.get("ttl")
            if ttl_val is not None:
                meta["expire_at"] = datetime.now(timezone.utc).timestamp() + int(ttl_val)

            tags_val = mem.get("tags")
            if tags_val:
                meta["tags"] = ",".join(tags_val)

            content_hash = hashlib.md5(content_text.encode()).hexdigest()[:8]
            source_key = source or f"batch_{content_hash}"

            drawers.append({
                "wing": self._wing,
                "room": room,
                "content": content_text,
                "source_file": source_key,
                "chunk_index": 0,
                "added_by": "sdk_batch",
                "extra_meta": meta,
            })
            ids.append(_make_drawer_id(self._wing, room, source_key, 0))

        added, skipped = batch_add_drawers(collection, drawers)
        return BatchRememberResult(total=len(memories), stored=added, duplicates=0, ids=[i for i in ids if i])

    def batch_forget(self, drawer_ids) -> BatchForgetResult:
        """Delete multiple memories in a single batch operation."""
        collection = self._get_collection()
        if collection is None:
            return BatchForgetResult(requested=0, deleted=0, not_found=0)
        if not drawer_ids:
            return BatchForgetResult(requested=0, deleted=0, not_found=0)
        try:
            collection.delete(ids=drawer_ids)
            return BatchForgetResult(requested=len(drawer_ids), deleted=len(drawer_ids), not_found=0)
        except Exception as _e:
            logger.debug("Count failed: %s", _e)
            return BatchForgetResult(requested=len(drawer_ids), deleted=0, not_found=0)

    

    def batch_recall(
        self,
        queries: list[str],
        *,
        limit: int = 3,
        room: str | None = None,
        threshold: float = 0.8,
    ) -> BatchRecallResult:
        """Bulk semantic recall: run multiple queries in a single batch.

        Args:
            queries: List of query strings (max 100).
            limit: Max results per query.
            room: Optional room filter applied to every query.
            threshold: Max distance (lower = more similar).

        Returns:
            List of {query: str, memories: list[dict]}.
        """
        results: list[dict[str, Any]] = []
        for q in queries[:100]:
            memories = self.recall(q, limit=limit, room=room, threshold=threshold)
            results.append({"query": q, "memories": memories})
        return BatchRecallResult(results=results)

    def iter_all(
        self,
        batch_size: int = 252,
        *,
        room: str | None = None,
    ):
        """Lazy iterator over all memories (paginated ChromaDB cursor).

        Yields dicts {id, content, room, ...} in batches of `batch_size`.
        Raises RuntimeError if the backend is not available.

        Usage::

            for batch in palace.iter_all(batch_size=100, room="decisions"):
                for mem in batch:
                    print(mem["content"])
        """
        collection = self._get_collection()
        if collection is None:
            raise RuntimeError("ChromaDB collection not available")
        total = collection.count()
        offset = 0
        while offset < total:
            try:
                batch = collection.get(
                    limit=batch_size,
                    offset=offset,
                    include=["metadatas", "documents"],
                )
            except Exception as exc:
                logger.debug("iter_all batch failed at offset %s: %s", offset, exc)
                offset += batch_size
                continue

            ids = batch.get("ids", [])
            docs = batch.get("documents", [])
            metas = batch.get("metadatas", [])
            if not ids:
                break
            result_batch: list[dict[str, Any]] = []
            for i, _id in enumerate(ids):
                entry: dict[str, Any] = {"id": _id}
                if i < len(docs) and docs[i]:
                    entry["content"] = docs[i]
                meta = {}
                if i < len(metas) and metas[i]:
                    meta = dict(metas[i])
                entry["room"] = meta.get("room", "general")
                entry["metadata"] = meta
                if room and entry.get("room") != room:
                    continue
                result_batch.append(entry)
            if result_batch:
                yield result_batch
            offset += batch_size

    def iter_all_items(
        self,
        *,
        room: str | None = None,
    ):
        """Flat iterator — yields individual memory dicts (not batches).

        Convenience wrapper around iter_all for simple loops."""
        for batch in self.iter_all(room=room):
            yield from batch

    def bulk_remember_typed(
        self,
        memories: list[dict[str, Any]],
    ):
        """Typed alias for batch_remember with Pydantic validation.

        This is the v0.3.0 convention — prefer this for new code.
        """
        return self.batch_remember(memories)
    def fuzzy_search(
        self,
        query: str,
        *,
        limit: int = 10,
        room: str | None = None,
        threshold: float = 0.6,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Hybrid search: semantic vector search + metadata filtering.

        Unlike recall(), this returns raw results without KG expansion,
        cross-wing tracking, or working memory cache. Useful for programmatic
        queries where you want precise control over filtering.

        Args:
            query: Search query text.
            limit: Max results.
            room: Optional room filter.
            threshold: Similarity threshold (0-1, lower = stricter).
            metadata_filter: Additional metadata filter dict.

        Returns:
            List of matching memories.
        """
        collection = self._get_collection()
        if collection is None:
            return []

        where_clause: dict = {"wing": self._wing}
        if room:
            where_clause = {"$and": [{"wing": self._wing}, {"room": room}]}
        if metadata_filter:
            if "$and" in where_clause:
                for k, v in metadata_filter.items():
                    where_clause["$and"].append({k: v})
            else:
                combined: dict = {"$and": [where_clause]}
                for k, v in metadata_filter.items():
                    combined["$and"].append({k: v})
                where_clause = combined

        try:
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=where_clause,
            )
        except Exception as e:
            logger.warning("fuzzy_search failed: %s", e)
            return []

        output = []
        if results and results.get("documents"):
            docs = results["documents"][0] or []
            metas = results["metadatas"][0] or [{}] * len(docs)
            dists = results["distances"][0] or [0.0] * len(docs)
            for doc, meta, dist in zip(docs, metas, dists):
                if dist <= threshold:
                    output.append({
                        "content": doc,
                        "metadata": meta,
                        "distance": dist,
                    })
        return output

    def recent(
        self,
        *,
        limit: int = 20,
        room: str | None = None,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Retrieve the most recently stored memories.

        Uses filed_at metadata for sorting (most recent first).

        Args:
            limit: Max results.
            room: Optional room filter.
            offset: Pagination offset.

        Returns:
            List of recent memories.
        """
        collection = self._get_collection()
        if collection is None:
            return []

        where_clause: dict = {"wing": self._wing}
        if room:
            where_clause = {"$and": [{"wing": self._wing}, {"room": room}]}

        try:
            results = collection.get(
                where=where_clause,
                limit=limit + offset,
                include=["metadatas", "documents"],
            )
        except Exception as e:
            logger.warning("recent failed: %s", e)
            return []

        output = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"]):
                meta = results["metadatas"][i] if results["metadatas"] else {}
                doc = results["documents"][i] if results["documents"] else ""
                output.append({
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                    "filed_at": meta.get("filed_at", ""),
                })
            output.sort(key=lambda x: x.get("filed_at", ""), reverse=True)
        return output[offset:offset + limit]

    def search(
        self,
        query: str | None = None,
        *,
        limit: int = 10,
        mode: str = "hybrid",
        room: str | None = None,
        threshold: float = 0.7,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        time_from: float | None = None,
        time_to: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
        expand_kg: bool = False,
    ) -> list[dict[str, Any]]:
        """Unified search that automatically routes to the best query strategy.

        Args:
            query: Natural language query. If None, performs pure metadata filter.
            mode: ``"hybrid"`` (default, semantic + metadata) or ``"semantic"`` or ``"metadata"``.
            limit: Max results.
            room: Filter by room.
            threshold: Max distance (0-1, lower = more similar).
            memory_types: Filter by memory type(s): "semantic", "episodic", "procedural".
            tags: Filter by tags.
            time_from: Minimum filed_at timestamp (epoch seconds).
            time_to: Maximum filed_at timestamp (epoch seconds).
            metadata_filter: Additional metadata key-value filters.
            expand_kg: If True, expand results via knowledge graph.

        Returns:
            List of matching memories.
        """
        if mode == "hybrid" and query:
            return self.advanced_query.hybrid_search(
                query=query,
                limit=limit,
                room=room,
                threshold=threshold,
                memory_types=memory_types,
                tags=tags,
                time_from=time_from,
                time_to=time_to,
                metadata_filter=metadata_filter,
                expand_kg=expand_kg,
            )
        if mode == "semantic" and query:
            # Pure semantic search — no metadata post-filter
            collection = self._get_collection()
            if collection is None:
                return []
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where={"wing": self._wing},
                )
            except Exception as e:
                logger.warning("semantic search failed: %s", e)
                return []
            output = []
            if results and results.get("documents"):
                for doc, meta, dist in zip(
                    results["documents"][0] or [],
                    results["metadatas"][0] or [],
                    results["distances"][0] or [],
                ):
                    if dist <= threshold:
                        output.append({"content": doc, "metadata": meta, "distance": dist})
            return output
        # Fallback: metadata-only filter
        return self.advanced_query.filter_by_metadata(
            limit=limit,
            room=room,
            memory_types=memory_types,
            tags=tags,
            time_from=time_from,
            time_to=time_to,
            metadata_filter=metadata_filter,
        )

    def hybrid_search(
        self,
        query: str,
        *,
        limit: int = 10,
        room: str | None = None,
        threshold: float = 0.7,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        time_from: float | None = None,
        time_to: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
        expand_kg: bool = False,
    ) -> list[dict[str, Any]]:
        """Multi-faceted search combining vector search, metadata filtering, and KG expansion.

        Convenience wrapper around AdvancedQuery.hybrid_search().

        Args:
            query: Natural language query.
            limit: Max results.
            room: Filter by room.
            threshold: Max distance (0-1, lower = more similar).
            memory_types: Filter by memory type(s): "semantic", "episodic", "procedural".
            tags: Filter by tags.
            time_from: Minimum filed_at timestamp (epoch seconds).
            time_to: Maximum filed_at timestamp (epoch seconds).
            metadata_filter: Additional metadata key-value filters.
            expand_kg: If True, expand results via knowledge graph.

        Returns:
            List of matching memories with scores.
        """
        return self.advanced_query.hybrid_search(
            query=query,
            limit=limit,
            room=room,
            threshold=threshold,
            memory_types=memory_types,
            tags=tags,
            time_from=time_from,
            time_to=time_to,
            metadata_filter=metadata_filter,
            expand_kg=expand_kg,
        )

    def filter_by_metadata(
        self,
        *,
        limit: int = 50,
        room: str | None = None,
        memory_types: list[str] | None = None,
        tags: list[str] | None = None,
        time_from: float | None = None,
        time_to: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Pure metadata filter search (no semantic similarity).

        Convenience wrapper around AdvancedQuery.filter_by_metadata().

        Args:
            limit: Max results.
            room: Filter by room.
            memory_types: Filter by memory type(s).
            tags: Filter by tags.
            time_from: Minimum filed_at timestamp.
            time_to: Maximum filed_at timestamp.
            metadata_filter: Additional metadata key-value filters.

        Returns:
            List of matching memories.
        """
        return self.advanced_query.filter_by_metadata(
            limit=limit,
            room=room,
            memory_types=memory_types,
            tags=tags,
            time_from=time_from,
            time_to=time_to,
            metadata_filter=metadata_filter,
        )

    def search_by_metadata(
        self,
        filter: dict[str, Any],
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Search memories by exact metadata field matching.

        Args:
            filter: Metadata filter dict.
            limit: Max results.

        Returns:
            List of matching memories.
        """
        collection = self._get_collection()
        if collection is None:
            return []

        try:
            results = collection.get(
                where=filter,
                limit=limit,
                include=["metadatas", "documents"],
            )
        except Exception as e:
            logger.warning("search_by_metadata failed: %s", e)
            return []

        output = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"]):
                meta = results["metadatas"][i] if results["metadatas"] else {}
                doc = results["documents"][i] if results["documents"] else ""
                output.append({
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                })
        return output

    def stop_auto_evolve(self) -> None:
        """Stop the background auto-evolve thread."""
        if self._evolve_stop:
            self._evolve_stop.set()
            self._evolve_thread = None
            logger.info("Auto-evolve stopped")
