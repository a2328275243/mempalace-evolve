"""Advanced query module for MemPalace: hybrid search, filter enhancement, and result post-processing.

Provides:
- Hybrid search (semantic + keyword + metadata filter)
- Filter enhancement (time range, room, memory type, tags)
- Result scoring and ranking
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from mempalace_evolve.core.chroma_helper import get_collection

logger = logging.getLogger("mempalace.advanced_query")


class AdvancedQuery:
    """Advanced query builder for MemPalace with hybrid search and filter enhancement."""

    def __init__(self, palace):
        self._palace = palace
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            self._collection = self._palace._get_collection()
        return self._collection

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
        """Unified search router. Delegates to hybrid_search or filter_by_metadata.

        Args:
            query: Natural language query. None triggers metadata-only mode.
            mode: ``"hybrid"`` (default), ``"semantic"``, or ``"metadata"``.
            limit, room, threshold, memory_types, tags, time_from, time_to,
            metadata_filter, expand_kg: Same as hybrid_search.

        Returns:
            List of matching memories.
        """
        if mode == "hybrid" and query:
            return self.hybrid_search(
                query=query, limit=limit, room=room, threshold=threshold,
                memory_types=memory_types, tags=tags, time_from=time_from,
                time_to=time_to, metadata_filter=metadata_filter, expand_kg=expand_kg,
            )
        if mode == "semantic" and query:
            collection = self._get_collection()
            if collection is None:
                return []
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where={"wing": self._palace._wing},
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
        return self.filter_by_metadata(
            limit=limit, room=room, memory_types=memory_types, tags=tags,
            time_from=time_from, time_to=time_to, metadata_filter=metadata_filter,
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
        """Multi-faceted search combining semantic vector search, metadata filtering, and optional KG expansion.

        Args:
            query: Natural language query.
            limit: Max results to return.
            room: Filter by room.
            threshold: Max distance (0-1, lower = more similar).
            memory_types: Filter by memory type(s): "semantic", "episodic", "procedural".
            tags: Filter by tags (memories must have at least one matching tag).
            time_from: Minimum filed_at timestamp (epoch seconds).
            time_to: Maximum filed_at timestamp (epoch seconds).
            metadata_filter: Additional metadata key-value filters.
            expand_kg: If True, expand results via knowledge graph relationships.

        Returns:
            List of matching memories with scores.
        """
        collection = self._get_collection()
        if collection is None:
            return []

        # Build where clause
        where_parts: list[dict] = [{"wing": self._palace._wing}]

        if room:
            where_parts.append({"room": room})

        if memory_types:
            if len(memory_types) == 1:
                where_parts.append({"memory_type": memory_types[0]})
            else:
                or_parts = [{"memory_type": mt} for mt in memory_types]
                where_parts.append({"$or": or_parts})

        if metadata_filter:
            for k, v in metadata_filter.items():
                where_parts.append({k: v})

        if tags:
            # ChromaDB doesn't support array contains, so we check via metadata string
            tag_or = [{"tags": tag} for tag in tags]
            where_parts.append({"$or": tag_or} if len(tag_or) > 1 else tag_or[0])

        # Time range filters use filed_at stored as string in metadata
        # We apply them post-query since ChromaDB doesn't support range comparison natively

        where_clause = where_parts[0] if len(where_parts) == 1 else {"$and": where_parts}

        try:
            results = collection.query(
                query_texts=[query],
                n_results=limit * 2,
                where=where_clause,
            )
        except Exception as e:
            logger.warning("hybrid_search query failed: %s", e)
            return []

        output = []
        seen_ids = set()
        if results and results.get("documents"):
            docs = results["documents"][0] or []
            metas = results["metadatas"][0] or [{}] * len(docs)
            dists = results["distances"][0] or [0.0] * len(docs)
            ids = results["ids"][0] or []
            for doc, meta, dist, did in zip(docs, metas, dists, ids):
                if dist > threshold:
                    continue

                # Post-filter: time range
                if time_from is not None or time_to is not None:
                    filed_at_str = meta.get("filed_at", "")
                    if filed_at_str:
                        try:
                            filed_ts = datetime.fromisoformat(filed_at_str).timestamp()
                        except (ValueError, TypeError):
                            filed_ts = None
                    else:
                        filed_ts = None

                    if time_from is not None and (filed_ts is None or filed_ts < time_from):
                        continue
                    if time_to is not None and (filed_ts is None or filed_ts > time_to):
                        continue

                # Post-filter: tags (if tags list is provided)
                if tags:
                    meta_tags_str = meta.get("tags", "")
                    meta_tags = [t.strip() for t in meta_tags_str.split(",") if t.strip()]
                    if not any(t in meta_tags for t in tags):
                        continue

                score = self._compute_score(dist, meta)
                output.append({
                    "content": doc,
                    "metadata": meta,
                    "distance": dist,
                    "_score": score,
                })
                seen_ids.add(did)

        # Optional KG expansion
        if expand_kg and output:
            try:
                kg_extra = self._palace._kg_expand(output, seen_ids, limit)
                output.extend(kg_extra)
            except Exception:
                pass

        # Sort by score descending
        output.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return output[:limit]

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

        Useful for programmatic queries where you know the exact fields.

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
        collection = self._get_collection()
        if collection is None:
            return []

        where_parts: list[dict] = [{"wing": self._palace._wing}]
        if room:
            where_parts.append({"room": room})
        if memory_types:
            if len(memory_types) == 1:
                where_parts.append({"memory_type": memory_types[0]})
            else:
                where_parts.append({"$or": [{"memory_type": mt} for mt in memory_types]})
        if metadata_filter:
            for k, v in metadata_filter.items():
                where_parts.append({k: v})
        if tags:
            tag_or = [{"tags": tag} for tag in tags]
            where_parts.append({"$or": tag_or} if len(tag_or) > 1 else tag_or[0])

        where_clause = where_parts[0] if len(where_parts) == 1 else {"$and": where_parts}

        try:
            results = collection.get(
                where=where_clause,
                limit=limit,
                include=["metadatas", "documents"],
            )
        except Exception as e:
            logger.warning("filter_by_metadata failed: %s", e)
            return []

        output = []
        if results and results.get("ids"):
            for i, doc_id in enumerate(results["ids"]):
                meta = results["metadatas"][i] if results["metadatas"] else {}
                doc = results["documents"][i] if results["documents"] else ""

                # Post-filter: time range
                if time_from is not None or time_to is not None:
                    filed_at_str = meta.get("filed_at", "")
                    if filed_at_str:
                        try:
                            filed_ts = datetime.fromisoformat(filed_at_str).timestamp()
                        except (ValueError, TypeError):
                            filed_ts = None
                    else:
                        filed_ts = None
                    if time_from is not None and (filed_ts is None or filed_ts < time_from):
                        continue
                    if time_to is not None and (filed_ts is None or filed_ts > time_to):
                        continue

                # Post-filter: tags
                if tags:
                    meta_tags_str = meta.get("tags", "")
                    meta_tags = [t.strip() for t in meta_tags_str.split(",") if t.strip()]
                    if not any(t in meta_tags for t in tags):
                        continue

                output.append({
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                })
        return output

    def _compute_score(self, distance: float, meta: dict) -> float:
        """Compute a composite score from distance and metadata signals."""
        relevance = 1.0 - distance
        importance = float(meta.get("importance", meta.get("recall_count", 0))) / 10.0
        return relevance + importance * 0.3


__all__ = ["AdvancedQuery"]

