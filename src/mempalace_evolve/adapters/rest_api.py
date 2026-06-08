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
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel
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
        version="0.1.0",
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

    class RememberRequest(BaseModel):
        content: str
        room: str = "general"
        metadata: dict[str, Any] | None = None
        source: str = ""

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

    @app.post("/remember")
    def remember(req: RememberRequest):
        with _write_lock:
            drawer_id = palace.remember(
                req.content, room=req.room, metadata=req.metadata, source=req.source
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

    @app.post("/evolve")
    def evolve(req: EvolveRequest):
        with _write_lock:
            report = palace.evolve(transcript=req.transcript)
        return report

    class DigestRequest(BaseModel):
        messages: list[dict] | None = None
        transcript: str | None = None

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
