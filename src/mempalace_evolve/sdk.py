"""High-level SDK for mempalace-evolve.

Usage:
    from mempalace_evolve import MemPalace

    palace = MemPalace("~/my-project")
    palace.remember("JWT is used for auth", room="decisions")
    results = palace.recall("how does auth work?")
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
        # Working memory: session-level cache to avoid repeated searches
        self._working_memory: list[dict] = []
        self._working_memory_topic: str = ""

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
        memory_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        source: str = "",
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

        collection = self._get_collection()
        if collection is None:
            raise StorageError("Failed to initialize ChromaDB collection")

        # Merge memory_type into metadata
        extra_meta = dict(metadata) if metadata else {}
        extra_meta["memory_type"] = mtype
        extra_meta["recall_count"] = extra_meta.get("recall_count", 0)
        extra_meta["cross_wing_hits"] = extra_meta.get("cross_wing_hits", 0)

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
        )
        drawer_id = _make_drawer_id(self._wing, room, source_key, chunk_index)
        logger.debug("Stored memory %s in %s/%s", drawer_id, self._wing, room)

        # --- Similarity dedup: check for similar memories before storing ---
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
                return drawer_id  # Return ID but mark as duplicate
            elif dedup_result["action"] == "merge":
                # TODO: implement merge logic
                pass

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
        except Exception:
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
        # Working memory cache: if same topic, return cached results
        from difflib import SequenceMatcher
        topic_sim = SequenceMatcher(None, query, self._working_memory_topic).ratio()
        if topic_sim > 0.8 and self._working_memory:
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
        except Exception:
            pass  # procedural search is best-effort

        # --- Feedback loop: touch recalled memories ---
        if output:
            recalled_ids = list(seen_ids)[:limit]
            try:
                from mempalace_evolve.core.lifecycle import touch_drawers
                touch_drawers(collection, recalled_ids)
            except Exception:
                pass

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
        except Exception:
            pass

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
        except Exception:
            pass  # contradiction detection is best-effort

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
