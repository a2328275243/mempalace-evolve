"""Tests for export.py — JSON and Markdown export functions."""

import json
import tempfile
from pathlib import Path

import pytest

from mempalace_evolve.export import export_json, export_markdown


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _col(palace):
    from mempalace_evolve.core.chroma_helper import get_collection
    return get_collection(str(palace.path / "palace"), create=True)


# ---------------------------------------------------------------------------
# export_json
# ---------------------------------------------------------------------------

class TestExportJson:
    def test_empty_collection(self, palace):
        result = export_json(_col(palace))
        assert result["count"] == 0
        assert result["wing"] == "all"
        assert result["memories"] == []

    def test_single_memory(self, palace):
        palace.remember("Test memory for export", room="general")
        result = export_json(_col(palace))
        assert result["count"] >= 1

    def test_returns_expected_keys(self, palace):
        result = export_json(_col(palace))
        assert "exported_at" in result
        assert "wing" in result
        assert "count" in result
        assert "memories" in result

    def test_memory_has_expected_keys(self, palace):
        palace.remember("Key check", room="decisions")
        result = export_json(_col(palace))
        mem = result["memories"][0]
        assert "id" in mem
        assert "content" in mem
        assert "wing" in mem
        assert "room" in mem
        assert "source_file" in mem
        assert "filed_at" in mem
        assert "metadata" in mem

    def test_preserves_full_metadata(self, palace):
        palace.remember(
            "Export metadata fidelity test",
            room="config",
            metadata={"priority": "high"},
            source="export-source",
            ttl=3600,
            tags=["export", "parity"],
        )
        result = export_json(_col(palace), wing="test")
        mem = next(m for m in result["memories"] if m["content"] == "Export metadata fidelity test")
        assert mem["source_file"] == "export-source"
        assert mem["metadata"]["priority"] == "high"
        assert mem["metadata"]["source_file"] == "export-source"
        assert mem["metadata"]["tags"] == "export,parity"
        assert "expire_at" in mem["metadata"]

    def test_wing_filter(self, palace):
        palace.remember("Wing test", room="general")
        result = export_json(_col(palace), wing="test")
        assert result["wing"] == "test"
        assert result["count"] >= 1

    def test_nonexistent_wing_filter(self, palace):
        result = export_json(_col(palace), wing="nonexistent")
        assert result["wing"] == "nonexistent"

    def test_file_output(self, palace, tmp_palace):
        palace.remember("File output test", room="general")
        col = _col(palace)
        out_file = Path(tmp_palace) / "export.json"
        result = export_json(col, output=str(out_file))
        assert out_file.exists()
        parsed = json.loads(out_file.read_text())
        assert parsed["count"] >= 1


# ---------------------------------------------------------------------------
# export_markdown
# ---------------------------------------------------------------------------

class TestExportMarkdown:
    def test_empty_collection(self, palace):
        md = export_markdown(_col(palace))
        assert "0 memories" in md

    def test_single_memory(self, palace):
        palace.remember("Markdown memory", room="general")
        md = export_markdown(_col(palace))
        assert "Markdown memory" in md

    def test_contains_room_headers(self, palace):
        palace.remember("Room test", room="decisions")
        md = export_markdown(_col(palace))
        assert "## decisions" in md

    def test_multiple_rooms_grouped(self, palace):
        palace.remember("General memory", room="general")
        palace.remember("Decision memory", room="decisions")
        md = export_markdown(_col(palace))
        assert "## general" in md
        assert "## decisions" in md

    def test_wing_in_title(self, palace):
        md = export_markdown(_col(palace), wing="test")
        assert "test" in md

    def test_file_output(self, palace, tmp_palace):
        palace.remember("File markdown test", room="general")
        col = _col(palace)
        out_file = Path(tmp_palace) / "export.md"
        md = export_markdown(col, output=str(out_file))
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "File markdown test" in content

    def test_content_preview_shown(self, palace):
        long_content = "X" * 300
        palace.remember(long_content, room="general")
        md = export_markdown(_col(palace))
        assert "X" in md
