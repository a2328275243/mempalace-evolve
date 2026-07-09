"""REST API adapter — universal HTTP interface for any agent.

Start with:
    mempalace-server --port 8765

Or programmatically:
    from mempalace_evolve.adapters.rest_api import create_app
    app = create_app("/path/to/palace")
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Any

def create_app(palace_path: str | None = None, wing: str = "global", api_key: str | None = None):
    """Create a FastAPI app exposing MemPalace as REST endpoints.

    Args:
        palace_path: Path to palace directory.
        wing: Wing/project name.
        api_key: Optional API key. If set, all requests must include
                 header "X-API-Key: <key>".
    """
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.responses import JSONResponse, StreamingResponse
        from pydantic import BaseModel, Field
    except ImportError:
        raise ImportError(
            "REST API requires fastapi. Install with: pip install mempalace-evolve[api]"
        )

    from mempalace_evolve.sdk import MemPalace
    import threading

    palace = MemPalace(palace_path, wing=wing)
    _write_lock = threading.Lock()
    app = FastAPI(
        title="MemPalace Evolve API",
        version="0.2.0",
        description="Self-evolving memory palace for AI agents",
    )

    # API key middleware
    if api_key:
        @app.middleware("http")
        async def check_api_key(request: Request, call_next):
            if request.url.path == "/health":
                return await call_next(request)
            key = request.headers.get("X-API-Key", "")
            # Use constant-time comparison to prevent timing attacks
            if not secrets.compare_digest(key, api_key):
                return JSONResponse(status_code=401, content={"error": "Invalid API key"})
            return await call_next(request)

    # -- pydantic models --------------------------------------------------

    class RememberRequest(BaseModel):
        content: str
        room: str = "general"
        metadata: dict[str, Any] | None = None
        source: str = ""
        ttl: int | None = None
        tags: list[str] | None = None

    class RecallRequest(BaseModel):
        query: str
        limit: int = 5
        room: str | None = None

    class FactRequest(BaseModel):
        subject: str
        predicate: str
        object: str

    class EvolveRequest(BaseModel):
        transcript: str | None = None

    class DigestRequest(BaseModel):
        messages: list[dict] | None = None
        transcript: str | None = None

    class QueryEntityV2Request(BaseModel):
        entity: str
        as_of: str | None = None

    class QueryPathRequest(BaseModel):
        start_entity: str
        end_entity: str
        max_depth: int = 4

    class RecallStreamRequest(BaseModel):
        query: str
        limit: int = 5
        room: str | None = None
        threshold: float = 0.8
        hybrid: bool = True

    class ScoreRequest(BaseModel):
        pass

    class TopMemoriesRequest(BaseModel):
        n: int = 10

    class FindSimilarRequest(BaseModel):
        content: str
        room: str | None = None
        threshold: float = 0.85

    class MarkReviewedRequest(BaseModel):
        drawer_id: str

    class SnoozeRequest(BaseModel):
        drawer_id: str
        days: int = 1


    class PurgeRequest(BaseModel):
        ttl_days: int = 90
        ttl_summary_days: int = 180

    class CompressRequest(BaseModel):
        compress_after_days: int = 60
        max_chars: int = 800

    class ConsolidateRequest(BaseModel):
        dry_run: bool = False

    class BatchForgetRequest(BaseModel):
        drawer_ids: list[str]

    # -- existing endpoints -----------------------------------------------

    @app.post("/remember")
    def remember(req: RememberRequest):
        with _write_lock:
            drawer_id = palace.remember(
                req.content,
                room=req.room,
                metadata=req.metadata,
                source=req.source,
                ttl=req.ttl,
                tags=req.tags,
            )
        return {"drawer_id": drawer_id, "status": "stored"}

    @app.post("/recall")
    def recall(req: RecallRequest):
        results = palace.recall(req.query, limit=req.limit, room=req.room)
        return {"results": results, "count": len(results)}

    @app.post("/forget/{drawer_id}")
    def forget(drawer_id: str):
        with _write_lock:
            ok = palace.forget(drawer_id)
        if not ok:
            raise HTTPException(404, "Memory not found")
        return {"status": "deleted"}

    @app.post("/kg/add")
    def add_fact(req: FactRequest):
        with _write_lock:
            palace.add_fact(req.subject, req.predicate, req.object)
        return {"status": "added"}

    @app.post("/kg/query/{entity}")
    def query_entity(entity: str, direction: str = "both"):
        results = palace.query_entity(entity, direction=direction)
        return {"entity": entity, "relations": results}

    # -- NEW: query_entity_v2 --------------------------------------------

    @app.post("/kg/query_v2")
    def query_entity_v2_endpoint(req: QueryEntityV2Request):
        """Structured entity query with separate incoming/outgoing lists."""
        result = palace.query_entity_v2(req.entity, as_of=req.as_of)
        return result

    # -- NEW: query_path -------------------------------------------------

    @app.post("/kg/path")
    def query_path_endpoint(req: QueryPathRequest):
        """Shortest path between two entities in the knowledge graph."""
        path = palace.query_path(req.start_entity, req.end_entity, max_depth=req.max_depth)
        return {"path": path, "length": len(path)}

    # -- NEW: recall_stream (SSE) ----------------------------------------

    @app.post("/recall_stream")
    async def recall_stream_endpoint(req: RecallStreamRequest):
        """Stream recall results via SSE (Server-Sent Events)."""

        async def event_generator():
            for item in palace.recall_stream(
                req.query,
                limit=req.limit,
                room=req.room,
                threshold=req.threshold,
                hybrid=req.hybrid,
            ):
                yield f"data: {__import__('json').dumps(item, ensure_ascii=False, default=str)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # -- NEW: FSRS / spaced repetition endpoints -------------------------

    @app.get("/review/due")
    def get_due_for_review():
        """Get all memories due for spaced repetition review."""
        due = palace.get_due_for_review()
        return {"due": due, "count": len(due)}

    @app.post("/review/mark")
    def mark_reviewed_endpoint(req: MarkReviewedRequest):
        """Mark a memory as reviewed (FSRS state update)."""
        ok = palace.mark_reviewed(req.drawer_id)
        if not ok:
            raise HTTPException(404, "Memory not found or review failed")
        return {"status": "reviewed", "drawer_id": req.drawer_id}

    @app.post("/review/snooze")
    def snooze_endpoint(req: SnoozeRequest):
        """Snooze a memory for N days."""
        ok = palace.snooze_memory(req.drawer_id, days=req.days)
        if not ok:
            raise HTTPException(404, "Memory not found")
        return {"status": "snoozed", "drawer_id": req.drawer_id, "days": req.days}

    # -- NEW: scoring / importance ---------------------------------------

    @app.post("/score")
    def score_memories_endpoint():
        """Run auto-scoring across all memories."""
        with _write_lock:
            result = palace.score_memories()
        return result

    @app.post("/top")
    def top_memories_endpoint(req: TopMemoriesRequest):
        """Get top N most important memories."""
        top = palace.top_memories(n=req.n)
        return {"top": top, "count": len(top)}

    @app.post("/similar")
    def find_similar_endpoint(req: FindSimilarRequest):
        """Find memories semantically similar to given content."""
        similar = palace.find_similar(req.content, room=req.room, threshold=req.threshold)
        return {"similar": similar, "count": len(similar)}

    # -- lifecycle endpoints ---------------------------------------------

    @app.post("/lifecycle/purge")
    def purge_expired_endpoint(req: PurgeRequest):
        """Purge expired (TTL) memories."""
        with _write_lock:
            result = palace.purge_expired(
                ttl_days=req.ttl_days,
                ttl_summary_days=req.ttl_summary_days,
            )
        return result

    @app.post("/lifecycle/compress")
    def compress_old_memories_endpoint(req: CompressRequest):
        """Compress old unused memories."""
        with _write_lock:
            result = palace.compress_old_memories(
                compress_after_days=req.compress_after_days,
                max_chars=req.max_chars,
            )
        return result

    @app.post("/lifecycle/consolidate")
    def consolidate_endpoint(req: ConsolidateRequest):
        """Run daily consolidation: deduplicate and merge."""
        with _write_lock:
            result = palace.consolidate(dry_run=req.dry_run)
        return result

    @app.post("/forget/batch")
    def batch_forget_endpoint(req: BatchForgetRequest):
        """Delete multiple memories in batch."""
        with _write_lock:
            results = []
            for drawer_id in req.drawer_ids:
                ok = palace.forget(drawer_id)
                results.append({"drawer_id": drawer_id, "status": "deleted" if ok else "not_found"})
        return {"results": results, "count": len(results)}

    @app.get("/stats")
    def get_stats():
        """Get palace statistics."""
        try:
            stats = {
                "total_memories": palace.count_memories(),
                "rooms": palace.list_rooms(),
                "kg_triples": palace.count_triples(),
                "wing": palace.wing,
                "palace_path": str(palace.path),
            }
        except Exception as e:
            stats = {"error": str(e)}
        return stats

    # -- existing endpoints -----------------------------------------------

    @app.post("/evolve")
    def evolve(req: EvolveRequest):
        with _write_lock:
            report = palace.evolve(transcript=req.transcript)
        return report

    @app.post("/digest")
    def digest(req: DigestRequest):
        conversation = req.messages or req.transcript or ""
        with _write_lock:
            result = palace.digest(conversation)
        return result

    @app.get("/export")
    def export(format: str = "json"):
        return palace.export(format=format)

    @app.get("/health")
    def health():
        return {"status": "ok", "palace_path": str(palace.path), "wing": palace.wing}

    return app

def serve(host: str = "0.0.0.0", port: int = 8765, palace_path: str | None = None,
          api_key: str | None = None):
    """Start the REST API server."""
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "Server requires uvicorn. Install with: pip install mempalace-evolve[api]"
        )

    app = create_app(palace_path, api_key=api_key)
    uvicorn.run(app, host=host, port=port)

