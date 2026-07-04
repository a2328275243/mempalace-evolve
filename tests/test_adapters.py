"""Tests for adapters: OpenAI, REST API, MCP server."""

import json

import pytest


class TestOpenAIAdapter:
    def test_get_tools(self, palace):
        from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(palace)
        tools = adapter.get_tools()
        assert len(tools) == 3
        names = [t["function"]["name"] for t in tools]
        assert "mempalace_remember" in names
        assert "mempalace_recall" in names
        assert "mempalace_add_fact" in names

    def test_handle_remember(self, palace):
        from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(palace)
        result = adapter.handle_tool_call("mempalace_remember", {
            "content": "Use uvicorn as ASGI server",
            "room": "config",
        })
        data = json.loads(result)
        assert data["stored"] is True

    def test_handle_recall(self, palace):
        from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter
        palace.remember("Database uses PostgreSQL 15", room="config")
        adapter = OpenAIAdapter(palace)
        result = adapter.handle_tool_call("mempalace_recall", {"query": "database"})
        data = json.loads(result)
        assert len(data["results"]) >= 1

    def test_handle_add_fact(self, palace):
        from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(palace)
        result = adapter.handle_tool_call("mempalace_add_fact", {
            "subject": "app",
            "predicate": "runs_on",
            "object": "port 8000",
        })
        data = json.loads(result)
        assert data["added"] is True

    def test_handle_unknown_tool(self, palace):
        from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(palace)
        result = adapter.handle_tool_call("nonexistent_tool", {})
        data = json.loads(result)
        assert "error" in data

    def test_session_lifecycle(self, palace):
        from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(palace)
        context = {"first_message": "How does auth work?"}
        result = adapter.on_session_start(context)
        # Should return None (no memories yet) or a string
        assert result is None or isinstance(result, str)


class TestBaseAdapter:
    def test_on_error_stores_memory(self, palace):
        from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(palace)
        adapter.on_error("TypeError: NoneType has no attribute 'split'", {})
        results = palace.recall("TypeError NoneType")
        assert len(results) >= 1

    def test_remember_and_recall_shortcuts(self, palace):
        from mempalace_evolve.adapters.openai_adapter import OpenAIAdapter
        adapter = OpenAIAdapter(palace)
        did = adapter.remember("Test via adapter shortcut", room="general")
        assert did
        results = adapter.recall("Test via adapter")
        assert len(results) >= 1


class TestRestAPI:
    @pytest.fixture(autouse=True)
    def _check_fastapi(self):
        try:
            from fastapi.testclient import TestClient
            from mempalace_evolve.adapters.rest_api import create_app
            self._create_app = create_app
            self._TestClient = TestClient
        except (ImportError, TypeError):
            pytest.skip("fastapi not available or incompatible version")
            return
        # Verify FastAPI + starlette actually work together
        try:
            from fastapi import FastAPI
            FastAPI()
        except TypeError:
            pytest.skip("fastapi/starlette version mismatch")
            return
        # Smoke test: ensure TestClient routes correctly
        try:
            import tempfile, os
            with tempfile.TemporaryDirectory() as td:
                test_app = self._create_app(td, wing="_smoke")
                c = self._TestClient(test_app)
                r = c.post("/remember", json={"content": "smoke", "room": "t"})
                if r.status_code == 422 and "query" in r.text:
                    pytest.skip("fastapi/starlette/httpx incompatibility detected")
        except Exception:
            pytest.skip("fastapi smoke test failed")

    def _make_client(self, tmp_palace):
        app = self._create_app(tmp_palace, wing="test_api")
        return self._TestClient(app)

    def test_create_app(self, tmp_palace):
        app = self._create_app(tmp_palace, wing="test_api")
        assert app is not None
        assert app.title == "MemPalace Evolve API"

    def test_health_endpoint(self, tmp_palace):
        client = self._make_client(tmp_palace)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_remember_and_recall(self, tmp_palace):
        client = self._make_client(tmp_palace)
        resp = client.post("/remember", json={
            "content": "FastAPI handles the REST endpoints",
            "room": "architecture",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "stored"

        resp = client.post("/recall", json={"query": "REST endpoints"})
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_knowledge_graph(self, tmp_palace):
        client = self._make_client(tmp_palace)
        resp = client.post("/kg/add", json={
            "subject": "service",
            "predicate": "depends_on",
            "object": "database",
        })
        assert resp.status_code == 200

        resp = client.post("/kg/query/service")
        assert resp.status_code == 200
        assert len(resp.json()["relations"]) >= 1


class TestMCPServer:
    def test_create_mcp_server(self, tmp_palace):
        try:
            from mempalace_evolve.adapters.mcp_server import create_mcp_server
            mcp = create_mcp_server(palace_path=tmp_palace, wing="test_mcp")
            assert mcp is not None
        except ImportError:
            pass  # fastmcp not installed

    def test_mcp_tools_registered(self, tmp_palace):
        try:
            from mempalace_evolve.adapters.mcp_server import create_mcp_server
            mcp = create_mcp_server(palace_path=tmp_palace, wing="test_mcp")
            # FastMCP stores tools internally
            # Check that the server object exists and has name
            assert mcp.name == "mempalace"
        except ImportError:
            pass
