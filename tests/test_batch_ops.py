"""Tests for batch operations, export/import round-trip, and SDK model returns."""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest


class TestBatchRemember:
    """batch_remember returns typed BatchRememberResult."""

    def test_batch_remember_returns_model(self, palace):
        from mempalace_evolve.models import BatchRememberResult
        result = palace.batch_remember([
            {"content": "Memory A for batch", "room": "general"},
            {"content": "Memory B for batch", "room": "general"},
        ])
        assert isinstance(result, BatchRememberResult)
        assert result.stored == 2
        assert result.total == 2
        assert len(result.ids) == 2

    def test_batch_remember_empty_content_skipped(self, palace):
        from mempalace_evolve.models import BatchRememberResult
        result = palace.batch_remember([
            {"content": "", "room": "general"},
            {"content": "   ", "room": "general"},
            {"content": "Valid content", "room": "general"},
        ])
        assert isinstance(result, BatchRememberResult)
        assert result.stored == 1

    def test_batch_remember_with_metadata(self, palace):
        result = palace.batch_remember([{
            "content": "Tagged memory",
            "room": "decisions",
            "metadata": {"priority": "high"},
            "tags": ["important", "review"],
            "source": "meeting_notes",
        }])
        assert result.stored == 1
        recalled = palace.recall("Tagged memory", limit=1)
        assert len(recalled) >= 1

    def test_batch_remember_recallable(self, palace):
        palace.batch_remember([
            {"content": "Batch recall test A", "room": "dev"},
            {"content": "Batch recall test B", "room": "dev"},
            {"content": "Batch recall test C", "room": "dev"},
        ])
        results = palace.recall("Batch recall test", limit=5)
        assert len(results) >= 1

    def test_batch_remember_large(self, palace):
        memories = [{"content": f"Large batch item {i}", "room": "general"} for i in range(50)]
        result = palace.batch_remember(memories)
        assert result.stored == 50


class TestBatchForget:
    def test_batch_forget_returns_model(self, palace):
        from mempalace_evolve.models import BatchForgetResult
        r = palace.batch_remember([
            {"content": "To forget A", "room": "general"},
            {"content": "To forget B", "room": "general"},
        ])
        result = palace.batch_forget(r.ids)
        assert isinstance(result, BatchForgetResult)
        assert result.requested == 2
        assert result.deleted == 2

    def test_batch_forget_empty_ids(self, palace):
        from mempalace_evolve.models import BatchForgetResult
        result = palace.batch_forget([])
        assert isinstance(result, BatchForgetResult)
        assert result.deleted == 0

    def test_batch_forget_nonexistent_ids(self, palace):
        from mempalace_evolve.models import BatchForgetResult
        result = palace.batch_forget(["drawer_nonexistent_zzz_01", "drawer_nonexistent_zzz_02"])
        assert isinstance(result, BatchForgetResult)
        # ChromaDB delete on non-existent IDs is a no-op but doesn't error
        assert result.requested == 2


class TestBatchRecall:
    def test_batch_recall_returns_model(self, palace):
        from mempalace_evolve.models import BatchRecallResult
        palace.batch_remember([
            {"content": "Python is great for data science", "room": "dev"},
            {"content": "Rust is great for systems programming", "room": "dev"},
        ])
        result = palace.batch_recall(
            ["Python data science", "Rust systems"], limit=2, threshold=0.0,
        )
        assert isinstance(result, BatchRecallResult)
        assert hasattr(result, "results")
        assert isinstance(result.results, list)

    def test_batch_recall_multiple_queries(self, palace):
        palace.batch_remember([
            {"content": "FastAPI web framework", "room": "backend"},
            {"content": "React UI library", "room": "frontend"},
            {"content": "PostgreSQL database", "room": "backend"},
        ])
        result = palace.batch_recall(
            ["backend technology", "frontend tool"], limit=3, threshold=0.0,
        )
        from mempalace_evolve.models import BatchRecallResult
        assert isinstance(result, BatchRecallResult)
        assert len(result.results) == 2

    def test_batch_recall_room_filter(self, palace):
        palace.batch_remember([
            {"content": "Backend decision A", "room": "backend"},
            {"content": "Backend decision B", "room": "backend"},
            {"content": "Frontend design C", "room": "frontend"},
        ])
        result = palace.batch_recall(
            ["decision"], limit=5, room="backend", threshold=0.0,
        )
        assert len(result.results) >= 1


class TestExportImportRoundtrip:
    def test_export_then_import_wrapper_format(self, palace):
        palace.remember("Export-import test content A", room="decisions")
        palace.remember("Export-import test content B", room="decisions")
        export_data = palace.export(format="json")
        assert "memories" in export_data
        assert export_data["count"] >= 2
        import uuid
        tmp = Path(tempfile.gettempdir()) / f"test_mempalace_{uuid.uuid4().hex[:8]}"
        try:
            from mempalace_evolve.sdk import MemPalace
            fresh = MemPalace(str(tmp), wing="test")
            result = fresh.import_memories(export_data)
            assert result["added"] >= 2
            recalled = fresh.recall("Export-import test content")
            assert len(recalled) >= 1
        finally:
            import shutil
            shutil.rmtree(str(tmp), ignore_errors=True)

    def test_import_memories_from_export_file(self, palace, tmp_palace):
        palace.remember("File export test content", room="decisions")
        out_path = Path(tmp_palace) / "my_export.json"
        palace.export(format="json", output=str(out_path))
        assert out_path.exists()
        import uuid
        tmp = Path(tempfile.gettempdir()) / f"test_mempalace_{uuid.uuid4().hex[:8]}"
        try:
            from mempalace_evolve.sdk import MemPalace
            fresh = MemPalace(str(tmp), wing="test")
            result = fresh.import_memories(str(out_path))
            assert result["added"] >= 1
        finally:
            import shutil
            shutil.rmtree(str(tmp), ignore_errors=True)

    def test_import_memories_list_format(self, palace):
        items = [{"content": "List import A", "room": "general"}, {"content": "List import B", "room": "general"}]
        result = palace.import_memories(items)
        assert result["added"] >= 2

    def test_import_memories_preserves_metadata_fields(self, palace):
        result = palace.import_memories([{
            "content": "Imported metadata parity memory",
            "room": "config",
            "metadata": {"priority": "high"},
            "source": "import-source",
            "ttl": 3600,
            "tags": ["imported", "parity"],
        }])
        assert result["added"] == 1

        col = palace._get_collection()
        batch = col.get(where={"source_file": "import-source"}, include=["metadatas"])
        meta = batch["metadatas"][0]
        assert meta["priority"] == "high"
        assert meta["source_file"] == "import-source"
        assert meta["tags"] == "imported,parity"
        assert meta["expire_at"] > datetime.now(timezone.utc).timestamp()

    def test_import_memories_uses_export_source_file(self, palace):
        result = palace.import_memories([{
            "content": "Imported source_file parity memory",
            "room": "config",
            "source_file": "exported-source",
            "metadata": {"origin": "export"},
        }])
        assert result["added"] == 1

        col = palace._get_collection()
        batch = col.get(where={"source_file": "exported-source"}, include=["metadatas"])
        meta = batch["metadatas"][0]
        assert meta["source_file"] == "exported-source"
        assert meta["origin"] == "export"

    def test_import_memories_returns_stats(self, palace):
        result = palace.import_memories([{"content": "Stats test import", "room": "general"}])
        assert "added" in result
        assert "total" in result or "skipped" in result


class TestModelRoundtrip:
    def test_batch_remember_result_serializable(self, palace):
        result = palace.batch_remember([{"content": "Serializable test", "room": "general"}])
        d = result.model_dump()
        assert d["stored"] == 1
        assert d["total"] == 1
        assert len(d["ids"]) == 1

    def test_batch_forget_result_serializable(self, palace):
        r = palace.batch_remember([{"content": "For serializable forget", "room": "general"}])
        result = palace.batch_forget(r.ids)
        d = result.model_dump()
        assert d["requested"] == 1
        assert d["deleted"] == 1

    def test_batch_recall_result_serializable(self, palace):
        palace.batch_remember([{"content": "Recall model test", "room": "dev"}])
        result = palace.batch_recall(["Recall model"], limit=1, threshold=0.0)
        d = result.model_dump()
        assert "results" in d
