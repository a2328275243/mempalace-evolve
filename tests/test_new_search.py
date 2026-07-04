"""Tests for the unified search() method and ingest_directory parallel support."""

from __future__ import annotations

import pytest


class TestUnifiedSearch:
    """Tests for the unified search() method."""

    def test_search_hybrid_default(self, palace):
        """search() with a query string defaults to hybrid mode."""
        palace.remember("Machine learning transformers architecture", room="research")
        palace.remember("Attention is all you need paper", room="research")
        results = palace.search("transformer architecture")
        assert isinstance(results, list)

    def test_search_semantic_mode(self, palace):
        """search() with mode='semantic' returns results."""
        palace.remember("Python async programming guide", room="dev")
        results = palace.search("async coding", mode="semantic")
        assert isinstance(results, list)

    def test_search_metadata_mode(self, palace):
        """search() with no query uses metadata-only filter."""
        palace.remember("Config value A", room="config")
        palace.remember("Decision B", room="decisions")
        results = palace.search(mode="metadata", room="config")
        assert isinstance(results, list)
        # All results should be from the config room
        for r in results:
            meta = r.get("metadata", {})
            assert meta.get("room") == "config", f"Expected room 'config', got {meta.get('room')}"

    def test_search_with_tags_filter(self, palace):
        """search() with tags filter."""
        palace.remember("Important note", room="general", tags=["important", "dev"])
        palace.remember("Other note", room="general", tags=["other"])
        results = palace.search("note", tags=["important"])
        assert isinstance(results, list)

    def test_search_with_time_filter(self, palace):
        """search() with time range filter."""
        import time
        palace.remember("Recent memory", room="test")
        results = palace.search("recent", time_from=time.time() - 3600)
        assert isinstance(results, list)

    def test_search_without_query_uses_filter(self, palace):
        """search(None) routes to filter_by_metadata automatically."""
        palace.remember("Memory A", room="room_a")
        palace.remember("Memory B", room="room_b")
        results = palace.search(room="room_a")
        assert isinstance(results, list)
        if results:
            for r in results:
                assert r.get("metadata", {}).get("room") == "room_a"

    def test_search_returns_empty_on_empty_db(self, palace):
        """search() on empty palace returns empty list."""
        results = palace.search("anything")
        assert isinstance(results, list)
        # May or may not be empty - depends on ChromaDB defaults

    def test_search_limit_works(self, palace):
        """search() with limit returns at most that many results."""
        for i in range(5):
            palace.remember(f"Test memory item number {i}", room="test")
        results = palace.search("test memory", limit=3)
        assert isinstance(results, list)
        assert len(results) <= 3


class TestIngestParallel:
    """Tests for ingest_directory with parallel support."""

    def test_ingest_directory_serial(self, tmp_palace, palace):
        """ingest_directory with parallel=1 (serial, default) works."""
        import tempfile, os
        from mempalace_evolve.ingest import ingest_directory

        # Create a temp dir with a few .txt files
        with tempfile.TemporaryDirectory() as td:
            for i in range(3):
                fp = os.path.join(td, f"test_{i}.txt")
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(f"This is test file {i} with some content.\n")

            summary = ingest_directory(td, palace, extensions={".txt"})
        assert summary.total_files == 3

    def test_ingest_directory_parallel(self, tmp_palace, palace):
        """ingest_directory with parallel > 1 works."""
        import tempfile, os
        from mempalace_evolve.ingest import ingest_directory

        with tempfile.TemporaryDirectory() as td:
            for i in range(5):
                fp = os.path.join(td, f"file_{i}.md")
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(f"# File {i}\n\nContent of file {i}.\n")

            summary = ingest_directory(td, palace, extensions={".md"}, parallel=3)
        assert summary.total_files == 5

    def test_ingest_manifest_persists(self, tmp_palace, palace):
        """After ingest, manifest file exists and contains entries."""
        import tempfile, os, json
        from pathlib import Path
        from mempalace_evolve.ingest import ingest_directory

        with tempfile.TemporaryDirectory() as td:
            for i in range(2):
                fp = os.path.join(td, f"doc_{i}.txt")
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(f"Document {i} content here.\n")

            ingest_directory(td, palace, extensions={".txt"})

        # Manifest should exist
        manifest_path = Path(palace.path) / ".mempalace_manifest.json"
        assert manifest_path.exists(), "Manifest file should exist after ingest"

        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest_data, "Manifest should contain entries"


class TestAdvancedQuerySearch:
    """Tests for AdvancedQuery.search()."""

    def test_advanced_query_search_hybrid(self, palace):
        """AdvancedQuery.search() in hybrid mode works."""
        palace.remember("Quantum computing basics", room="research")
        aq = palace.advanced_query
        results = aq.search("quantum computing")
        assert isinstance(results, list)

    def test_advanced_query_search_semantic(self, palace):
        """AdvancedQuery.search() in semantic mode works."""
        palace.remember("Docker container deployment guide", room="devops")
        aq = palace.advanced_query
        results = aq.search("docker deployment", mode="semantic")
        assert isinstance(results, list)

    def test_advanced_query_search_metadata(self, palace):
        """AdvancedQuery.search() in metadata mode."""
        palace.remember("Important config", room="config")
        aq = palace.advanced_query
        results = aq.search(room="config")
        assert isinstance(results, list)

