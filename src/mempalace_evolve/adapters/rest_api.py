"""REST API adapter — universal HTTP interface for any agent.

Start with:
    mempalace-server --port 8765

Or programmatically:
    from mempalace_evolve.adapters.rest_api import create_app
    app = create_app("/path/to/palace")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def create_app(palace_path: str | None = None, wing: str = "global"):
    """Create a FastAPI app exposing MemPalace as REST endpoints."""
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
    except ImportError:
        raise ImportError(
            "REST API requires fastapi. Install with: pip install mempalace-evolve[api]"
        )

    from mempalace_evolve.sdk import MemPalace

    palace = MemPalace(palace_path, wing=wing)
    app = FastAPI(
        title="MemPalace Evolve API",
        version="0.1.0",
        description="Self-evolving memory palace for AI agents",
    )

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
        ok = palace.forget(drawer_id)
        if not ok:
            raise HTTPException(404, "Memory not found")
        return {"status": "deleted"}

    @app.post("/kg/add")
    def add_fact(req: FactRequest):
        palace.add_fact(req.subject, req.predicate, req.object)
        return {"status": "added"}

    @app.post("/kg/query/{entity}")
    def query_entity(entity: str, direction: str = "both"):
        results = palace.query_entity(entity, direction=direction)
        return {"entity": entity, "relations": results}

    @app.post("/evolve")
    def evolve(req: EvolveRequest):
        report = palace.evolve(transcript=req.transcript)
        return report

    @app.get("/health")
    def health():
        return {"status": "ok", "palace_path": str(palace.path), "wing": palace.wing}

    return app


def serve(host: str = "0.0.0.0", port: int = 8765, palace_path: str | None = None):
    """Start the REST API server."""
    try:
        import uvicorn
    except ImportError:
        raise ImportError(
            "Server requires uvicorn. Install with: pip install mempalace-evolve[api]"
        )

    app = create_app(palace_path)
    uvicorn.run(app, host=host, port=port)
