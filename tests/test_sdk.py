"""Tests for the core SDK: remember, recall, forget, knowledge graph."""

import json


class TestRemember:
    def test_store_and_return_id(self, palace):
        drawer_id = palace.remember("PostgreSQL is the main database", room="decisions")
        assert drawer_id
        assert drawer_id.startswith("drawer_")

    def test_different_content_gets_different_id(self, palace):
        id1 = palace.remember("Use Redis for caching", room="config")
        id2 = palace.remember("Use FastAPI for API layer", room="config")
        assert id1 != id2

    def test_chinese_content(self, palace):
        drawer_id = palace.remember("数据库使用PostgreSQL，ORM用SQLAlchemy", room="decisions")
        assert drawer_id

    def test_custom_metadata(self, palace):
        drawer_id = palace.remember(
            "Important decision",
            room="decisions",
            metadata={"priority": "high"},
            source="meeting_notes",
        )
        assert drawer_id


class TestRecall:
    def test_recall_stored_memory(self, palace):
        palace.remember("JWT tokens are used for authentication", room="decisions")
        results = palace.recall("authentication method")
        assert len(results) >= 1
        assert "JWT" in results[0]["content"]

    def test_recall_chinese(self, palace):
        palace.remember("项目使用 FastAPI 框架，数据库是 PostgreSQL", room="architecture")
        results = palace.recall("用了什么框架")
        assert len(results) >= 1
        assert "FastAPI" in results[0]["content"]

    def test_recall_empty(self, palace):
        results = palace.recall("nonexistent_query_xyz_12345")
        assert results == []

    def test_recall_room_filter(self, palace):
        palace.remember("This is a decision", room="decisions")
        palace.remember("This is an error fix", room="errors")
        results = palace.recall("decision", room="decisions")
        assert all(r["metadata"].get("room") == "decisions" for r in results)

    def test_recall_limit(self, palace):
        for i in range(10):
            palace.remember(f"Memory item number {i}", room="general")
        results = palace.recall("Memory item", limit=3)
        assert len(results) <= 3


class TestForget:
    def test_forget_existing(self, palace):
        drawer_id = palace.remember("Temporary data to delete", room="general")
        ok = palace.forget(drawer_id)
        assert ok is True

    def test_forget_nonexistent(self, palace):
        # ChromaDB delete on non-existent IDs doesn't raise — it's a no-op
        ok = palace.forget("nonexistent_id_xyz")
        # Accept either True (no-op) or False (explicit check)
        assert isinstance(ok, bool)

    def test_forget_then_recall_gone(self, palace):
        drawer_id = palace.remember("Data that will be removed", room="general")
        palace.forget(drawer_id)
        # After deletion, recall should not find it (or find it with low relevance)
        results = palace.recall("Data that will be removed")
        contents = [r["content"] for r in results]
        assert "Data that will be removed" not in contents


class TestKnowledgeGraph:
    def test_add_and_query(self, palace):
        palace.add_fact("project", "uses", "FastAPI")
        palace.add_fact("project", "uses", "PostgreSQL")
        rels = palace.query_entity("project")
        assert len(rels) >= 2
        objects = [r["object"] for r in rels]
        assert "FastAPI" in objects
        assert "PostgreSQL" in objects

    def test_query_empty_entity(self, palace):
        rels = palace.query_entity("nonexistent_entity_xyz")
        assert rels == []
