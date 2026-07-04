"""Tests for the source ingestion subsystem."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mempalace_evolve import MemPalace
from mempalace_evolve.models import IngestResult, IngestSummary
from mempalace_evolve.ingest import (
    scan_directory,
    ingest_file,
    ingest_directory,
    list_sources,
)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory(prefix="mp_ingest_", ignore_cleanup_errors=True) as tmp:
        yield Path(tmp)


@pytest.fixture
def sample_dir(temp_dir):
    """Create sample text files for ingestion tests."""
    d = temp_dir
    (d / "notes.txt").write_text("This is a sample note.\nIt has multiple lines.\n", encoding="utf-8")
    (d / "config.json").write_text('{"key": "value", "enabled": true}\n', encoding="utf-8")
    (d / "code.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    (d / "readme.md").write_text("# Project\n\nDescription here.\n", encoding="utf-8")
    sub = d / "subdir"
    sub.mkdir()
    (sub / "deep.txt").write_text("Deep file content.", encoding="utf-8")
    return d


class TestScanDirectory:
    def test_scan_all_files(self, sample_dir):
        entries = scan_directory(str(sample_dir))
        assert len(entries) >= 4
        assert all(isinstance(e, Path) for e in entries)

    def test_scan_with_ignore(self, sample_dir):
        entries = scan_directory(str(sample_dir))
        names = [e.name for e in entries]
        assert ".git" not in names
        assert "__pycache__" not in names

    def test_scan_nonexistent_dir(self):
        with pytest.raises(NotADirectoryError):
            scan_directory("/nonexistent/path/xyz")

    def test_scan_empty_dir(self, temp_dir):
        entries = scan_directory(str(temp_dir))
        assert entries == []


class TestIngestFile:
    @pytest.fixture
    def palace(self, temp_dir):
        p = MemPalace(str(temp_dir / "palace"), wing="test")
        yield p

    def test_ingest_text_file(self, temp_dir, palace):
        path = temp_dir / "test.txt"
        path.write_text("Hello world", encoding="utf-8")
        result = ingest_file(str(path), palace, room="test")
        assert isinstance(result, IngestResult)
        assert result.path == str(path)
        assert result.status == "ok"
        assert result.chunks_created >= 1

    def test_ingest_nonexistent_file(self, palace):
        result = ingest_file("/nonexistent/file.txt", palace, room="test")
        assert isinstance(result, IngestResult)
        assert result.status == "error"

    def test_ingest_binary_file(self, temp_dir, palace):
        path = temp_dir / "data.bin"
        path.write_bytes(b"\x00\x01\x02\x03")
        result = ingest_file(str(path), palace, room="test")
        assert isinstance(result, IngestResult)
        assert result.status == "error"


class TestIngestDirectory:
    @pytest.fixture
    def palace(self, temp_dir):
        p = MemPalace(str(temp_dir / "palace"), wing="test")
        yield p

    def test_ingest_directory_all(self, sample_dir, palace):
        summary = ingest_directory(str(sample_dir), palace, room="sources")
        assert isinstance(summary, IngestSummary)
        assert summary.total_files >= 4

    def test_ingest_returns_summary(self, sample_dir, palace):
        summary = ingest_directory(str(sample_dir), palace, room="sources")
        assert isinstance(summary, IngestSummary)
        assert len(summary.results) >= 4
        for r in summary.results:
            assert isinstance(r, IngestResult)
            assert hasattr(r, "path")

    def test_ingest_empty_dir(self, temp_dir, palace):
        summary = ingest_directory(str(temp_dir), palace, room="sources")
        assert isinstance(summary, IngestSummary)
        assert summary.total_files == 0


class TestListSources:
    def test_list_sources_returns_list(self, temp_dir):
        sources = list_sources(str(temp_dir))
        assert isinstance(sources, list)
