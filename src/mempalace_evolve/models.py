"""Pydantic data models for mempalace-evolve.

Structured schemas for memories, knowledge-graph triples, review cards,
palace configurations, and batch results. All public APIs that currently
return raw dicts should eventually return or accept these models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Memory / Drawer models
# ---------------------------------------------------------------------------


class MemoryEntry(BaseModel):
    """A single memory entry stored in a palace drawer."""

    model_config = ConfigDict(extra="allow")

    id: str | None = Field(default=None, description="ChromaDB drawer_id")
    content: str = Field(..., min_length=1)
    room: str = Field(default="general")
    wing: str = Field(default="default")
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    distance: float | None = Field(default=None, description="Cosine distance from query")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    recall_count: int = Field(default=0, ge=0)
    review_due_at: datetime | None = None
    review_interval_days: int | None = None


class BatchRememberInput(BaseModel):
    """Input for bulk memory creation."""

    content: str = Field(..., min_length=1)
    room: str = Field(default="general")
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchRememberResult(BaseModel):
    """Result of a batch_remember operation."""

    total: int = Field(default=0)
    stored: int = Field(default=0)
    duplicates: int = Field(default=0)
    ids: list[str] = Field(default_factory=list)

    def __getitem__(self, key):
        if key in ("added", "stored"):
            return self.stored
        if key == "total":
            return self.total
        if key == "ids":
            return self.ids
        if key == "duplicates":
            return self.duplicates
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self):
        return self.stored or self.total

    def __iter__(self):
        return iter(self.ids)


class BatchForgetResult(BaseModel):
    """Result of a batch_forget operation."""

    requested: int = Field(default=0)
    deleted: int = Field(default=0)
    not_found: int = Field(default=0)

    def __getitem__(self, key):
        if key == "deleted":
            return self.deleted
        if key == "requested":
            return self.requested
        if key == "not_found":
            return self.not_found
        raise KeyError(key)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


# ---------------------------------------------------------------------------
# Knowledge Graph models
# ---------------------------------------------------------------------------


class Triple(BaseModel):
    """Subject-predicate-object triple in the knowledge graph."""

    subject: str = Field(..., min_length=1)
    predicate: str = Field(..., min_length=1)
    obj: str = Field(..., min_length=1)


class GraphTraversalResult(BaseModel):
    """Result of a graph_traverse call."""

    start_entity: str
    max_depth: int
    nodes: list[str] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)


class KGStats(BaseModel):
    """Knowledge graph statistics."""

    total_triples: int = 0
    total_entities: int = 0
    total_relations: int = 0


class QueryEntityResult(BaseModel):
    """Result of query_entity 鈥?one side of relations for an entity."""

    entity: str
    outgoing: list[Triple] = Field(default_factory=list)
    incoming: list[Triple] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Review & Scoring models
# ---------------------------------------------------------------------------


class ReviewCard(BaseModel):
    """A memory due for spaced-repetition review."""

    id: str
    content: str
    room: str
    due_since: datetime | None = None
    review_count: int = 0
    next_interval_days: int | None = None


class ConfidenceInfo(BaseModel):
    """Adaptive scoring confidence breakdown."""

    distance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    gap_score: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ScoredMemory(BaseModel):
    """A memory with its importance score."""

    id: str
    content: str
    room: str
    score: float = Field(..., ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Configuration model (minimal Pydantic wrapper)
# ---------------------------------------------------------------------------


class PalaceConfig(BaseModel):
    """Typed configuration for a MemPalace instance."""

    model_config = ConfigDict(extra="allow")

    palace_path: str = Field(default="~/.mempalace")
    wing: str = Field(default="default")
    rooms: list[str] = Field(default_factory=lambda: ["general"])
    auto_evolve: bool = False
    evolve_interval: int = Field(default=300, ge=30)
    llm_enabled: bool = False
    embedding_model: str = "all-MiniLM-L6-v2"
    collection_prefix: str = "drawer"
    max_per_room: int = Field(default=1000, ge=1)
    scoring_weight_distance: float = Field(default=0.6, ge=0.0, le=1.0)
    scoring_weight_gap: float = Field(default=0.4, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Stats / Health models
# ---------------------------------------------------------------------------


class PalaceStats(BaseModel):
    """Aggregate statistics for a palace."""

    total_memories: int = 0
    total_rooms: int = 0
    total_triples: int = 0
    wing: str = "default"
    palace_path: str = "~/.mempalace"


class DoctorReport(BaseModel):
    """Installation and dependency health report."""

    ok: bool = True
    python_version: str = ""
    chromadb_version: str = ""
    pydantic_version: str = ""
    chroma_ok: bool = True
    onnx_ok: bool = True
    issues: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Unified Data Model (Roadmap Month 2-3): Source, Chunk, WikiPage, Citation
# ---------------------------------------------------------------------------


class SourceID(str):
    """Opaque source identifier: sha256(content, filename, ingest_time)."""


class Citation(BaseModel):
    """A reference that ties a generated fact or wiki section back to its source."""

    source_id: str = Field(..., min_length=1)
    chunk_ids: list[str] = Field(default_factory=list)
    snippet: str = Field(default="", description="Brief excerpt for traceability")


class Source(BaseModel):
    """An ingested document (file, note, AI chat) that feeds the knowledge base."""

    source_id: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    kind: str = Field(default="file", description="file | note | chat | web_page")
    hash: str = Field(default="", description="Content hash for incremental indexing")
    chunk_count: int = Field(default=0, ge=0)
    last_indexed: datetime | None = None
    last_modified: datetime | None = None
    status: str = Field(default="pending", description="pending | indexed | stale | archived")


class Chunk(BaseModel):
    """A contiguous slice of a source, stored as a vector drawer."""

    chunk_id: str = Field(..., min_length=1)
    source_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    start_line: int = Field(default=0, ge=0)
    end_line: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WikiPage(BaseModel):
    """A generated wiki page built from promoted memories and sources."""

    title: str = Field(..., min_length=1)
    slug: str = Field(..., min_length=1)
    sections: list[dict[str, str]] = Field(
        default_factory=list, description="List of {heading, content, citations}"
    )
    citations: list[Citation] = Field(default_factory=list)
    last_built: datetime | None = None
    auto_generated: bool = Field(default=True)


class IngestResult(BaseModel):
    """Result of a single ingest operation."""

    source_id: str
    path: str
    chunks_created: int = 0
    chunks_skipped: int = 0
    status: str = Field(default="ok", description="ok | skipped | error")
    error: str | None = None


class IngestSummary(BaseModel):
    """Summary of a multi-file ingest batch."""

    total_files: int = 0
    indexed: int = 0
    skipped: int = 0
    errors: int = 0
    results: list[IngestResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Bulk / Iterator models (v0.3.0)
# ---------------------------------------------------------------------------


class BatchRecallInput(BaseModel):
    """Input for bulk semantic recall."""

    queries: list[str] = Field(..., min_length=1, max_length=100)
    limit: int = Field(default=3, ge=1, le=20)


class BatchRecallResult(BaseModel):
    """Result of a batch_recall call 鈥?list of (query 鈫?memories)."""

    results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Each entry: {query, memories: [{content, distance, ...}]}",
    )


class IterationProgress(BaseModel):
    """Progress snapshot during a long-running iteration."""

    total: int = 0
    processed: int = 0
    errors: int = 0
    elapsed_seconds: float = 0.0
