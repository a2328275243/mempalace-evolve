"""Tests for core/chroma_helper.py — ChromaDB wrapper functions."""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from mempalace_evolve.core.chroma_helper import (
    get_collection,
    file_already_mined,
    add_drawer,
    delete_file_drawers,
    delete_by_wing,
    get_all_metadata,
    _make_drawer_id,
)


# ---------------------------------------------------------------------------
# _make_drawer_id
# ---------------------------------------------------------------------------

class TestMakeDrawerId:
    def test_deterministic(self):
        """Same inputs produce same ID."""
        id1 = _make_drawer_id("wing", "room", "/path/file.md", 0)
        id2 = _make_drawer_id("wing", "room", "/path/file.md", 0)
        assert id1 == id2

    def test_different_chunks_differ(self):
        """Different chunk indices produce different IDs."""
        id1 = _make_drawer_id("w", "r", "f.md", 0)
        id2 = _make_drawer_id("w", "r", "f.md", 1)
        assert id1 != id2

    def test_contains_parts(self):
        """ID contains wing and room for traceability."""
        drawer_id = _make_drawer_id("my-wing", "decisions", "doc.md", 0)
        assert drawer_id.startswith("drawer_")
        assert "my-wing" in drawer_id
        assert "decisions" in drawer_id


# ---------------------------------------------------------------------------
# get_collection (mocked chromadb)
# ---------------------------------------------------------------------------

class TestGetCollection:
    @patch("mempalace_evolve.core.chroma_helper.chromadb")
    def test_get_or_create(self, mock_chromadb, tmp_palace):
        """get_collection creates a collection and caches it."""
        mock_client = MagicMock()
        mock_col = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_col
        mock_chromadb.PersistentClient.return_value = mock_client

        col = get_collection(palace_path=tmp_palace, create=True)
        assert col is not None
        mock_client.get_or_create_collection.assert_called_once()

    @patch("mempalace_evolve.core.chroma_helper.chromadb")
    def test_get_no_create(self, mock_chromadb, tmp_palace):
        """get_collection with create=False returns None for missing."""
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = ValueError("does not exist")
        mock_chromadb.PersistentClient.return_value = mock_client

        col = get_collection(palace_path=tmp_palace, create=False)
        assert col is None

    @patch("mempalace_evolve.core.chroma_helper.chromadb")
    def test_caching_returns_same_instance(self, mock_chromadb, tmp_palace):
        """Repeated calls return the cached collection."""
        mock_client = MagicMock()
        mock_col = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_col
        mock_chromadb.PersistentClient.return_value = mock_client

        col1 = get_collection(palace_path=tmp_palace, create=True)
        col2 = get_collection(palace_path=tmp_palace, create=True)
        assert col1 is col2
        # Client should only be created once
        assert mock_chromadb.PersistentClient.call_count == 1

    @patch("mempalace_evolve.core.chroma_helper.chromadb")
    def test_cache_eviction_on_failed_health(self, mock_chromadb, tmp_palace):
        """Cached collection that fails health check is evicted."""
        mock_client = MagicMock()
        mock_col = MagicMock()
        # First count succeeds
        mock_col.count.return_value = 5
        mock_client.get_or_create_collection.return_value = mock_col
        mock_chromadb.PersistentClient.return_value = mock_client

        col1 = get_collection(palace_path=tmp_palace, create=True)
        assert col1 is not None

        # Second call: health check fails
        mock_col.count.side_effect = Exception("connection lost")

        # Force a health check by clearing the last check time
        import mempalace_evolve.core.chroma_helper as ch
        ch._last_health_check.clear()

        col2 = get_collection(palace_path=tmp_palace, create=True)
        # Should create a new collection after eviction
        assert col2 is not None


# ---------------------------------------------------------------------------
# file_already_mined
# ---------------------------------------------------------------------------

class TestFileAlreadyMined:
    def test_returns_true_when_found(self):
        col = MagicMock()
        col.get.return_value = {"ids": ["id1"]}
        assert file_already_mined(col, "path/to/file.md") is True

    def test_returns_false_when_empty(self):
        col = MagicMock()
        col.get.return_value = {"ids": []}
        assert file_already_mined(col, "new_file.md") is False

    def test_returns_false_on_exception(self):
        col = MagicMock()
        col.get.side_effect = Exception("DB error")
        assert file_already_mined(col, "broken.md") is False

    def test_passes_source_file_filter(self):
        col = MagicMock()
        col.get.return_value = {"ids": ["id1"]}
        file_already_mined(col, "/absolute/path/doc.md")
        # Verify the where filter contains the source file
        call_kwargs = col.get.call_args
        assert call_kwargs is not None
        _, kwargs = call_kwargs
        assert kwargs["where"]["source_file"] == "/absolute/path/doc.md"


# ---------------------------------------------------------------------------
# add_drawer
# ---------------------------------------------------------------------------

class TestAddDrawer:
    def test_adds_new_drawer(self):
        """add_drawer adds a doc to the collection and returns True."""
        col = MagicMock()
        col.get.return_value = {"ids": []}  # No existing
        result = add_drawer(col, wing="test-wing", room="decisions",
                            content="important memory", source_file="file.md",
                            chunk_index=0)
        assert result is True
        col.add.assert_called_once()

    def test_skips_duplicate(self):
        """Duplicate ID is detected and add_drawer returns False."""
        col = MagicMock()
        col.get.return_value = {"ids": ["drawer_test-wing_decisions_xxx"]}
        result = add_drawer(col, wing="wing", room="room",
                            content="dup", source_file="f.md", chunk_index=0)
        assert result is False
        col.add.assert_not_called()

    def test_handles_already_exists_exception(self):
        """Exception with 'already exists' is treated as duplicate."""
        col = MagicMock()
        col.get.side_effect = Exception("some error")
        col.add.side_effect = Exception("already exists")
        result = add_drawer(col, wing="w", room="r",
                            content="test", source_file="f.md", chunk_index=0)
        assert result is False

    def test_adds_with_extra_meta(self):
        """Extra metadata is included in the drawer."""
        col = MagicMock()
        col.get.return_value = {"ids": []}

        result = add_drawer(col, wing="w", room="r",
                            content="test", source_file="f.md", chunk_index=0,
                            extra_meta={"importance": 0.9, "category": "design"})

        assert result is True
        # Verify metadata includes extra fields
        call_args = col.add.call_args
        _, kwargs = call_args
        metadata = kwargs["metadatas"][0]
        assert metadata["importance"] == 0.9
        assert metadata["category"] == "design"

    def test_forces_string_types(self):
        """Parameters are force-converted to str."""
        col = MagicMock()
        col.get.return_value = {"ids": []}

        result = add_drawer(col, wing=123, room=456,
                            content=789, source_file=Path("/tmp/f.md"),
                            chunk_index=0)

        assert result is True
        call_args = col.add.call_args
        _, kwargs = call_args
        metadata = kwargs["metadatas"][0]
        assert metadata["wing"] == "123"
        assert metadata["room"] == "456"
        assert kwargs["documents"][0] == "789"

    def test_adds_timestamp_fields(self):
        """Metadata includes filed_at and last_accessed."""
        col = MagicMock()
        col.get.return_value = {"ids": []}

        add_drawer(col, wing="w", room="r",
                   content="c", source_file="f.md", chunk_index=0)

        call_args = col.add.call_args
        _, kwargs = call_args
        meta = kwargs["metadatas"][0]
        assert "filed_at" in meta
        assert "last_accessed" in meta


# ---------------------------------------------------------------------------
# delete_file_drawers
# ---------------------------------------------------------------------------

class TestDeleteFileDrawers:
    def test_deletes_and_returns_count(self):
        col = MagicMock()
        col.get.return_value = {"ids": ["id1", "id2", "id3"]}

        count = delete_file_drawers(col, "file.md")
        assert count == 3
        col.delete.assert_called_once_with(ids=["id1", "id2", "id3"])

    def test_returns_zero_for_empty(self):
        col = MagicMock()
        col.get.return_value = {"ids": []}

        count = delete_file_drawers(col, "empty.md")
        assert count == 0

    def test_returns_zero_on_error(self):
        col = MagicMock()
        col.get.side_effect = Exception("error")

        count = delete_file_drawers(col, "broken.md")
        assert count == 0


# ---------------------------------------------------------------------------
# delete_by_wing
# ---------------------------------------------------------------------------

class TestDeleteByWing:
    def test_deletes_and_returns_count(self):
        col = MagicMock()
        col.get.return_value = {"ids": ["id1", "id2"]}

        count = delete_by_wing(col, "my-wing")
        assert count == 2
        col.delete.assert_called_once_with(ids=["id1", "id2"])

    def test_returns_zero_on_error(self):
        col = MagicMock()
        col.get.side_effect = Exception("error")

        count = delete_by_wing(col, "broken")
        assert count == 0


# ---------------------------------------------------------------------------
# get_all_metadata
# ---------------------------------------------------------------------------

class TestGetAllMetadata:
    def test_returns_empty_for_no_data(self):
        col = MagicMock()
        col.count.return_value = 0
        col.get.return_value = {"ids": [], "metadatas": [], "documents": []}

        items = get_all_metadata(col)
        assert items == []

    def test_returns_all_items(self):
        col = MagicMock()
        col.count.return_value = 2
        col.get.return_value = {
            "ids": ["id1", "id2"],
            "metadatas": [{"wing": "w"}, {"wing": "w2"}],
            "documents": ["doc1", "doc2"],
        }

        items = get_all_metadata(col)
        assert len(items) == 2
        assert items[0]["id"] == "id1"
        assert items[0]["document"] == "doc1"
        assert items[0]["metadata"]["wing"] == "w"

    def test_batching(self):
        """get_all_metadata fetches in batches."""
        col = MagicMock()
        col.count.return_value = 3

        # First batch: 2 items
        # Second batch: 1 item
        col.get.side_effect = [
            {"ids": ["id1", "id2"], "metadatas": [{"w": "a"}, {"w": "b"}],
             "documents": ["d1", "d2"]},
            {"ids": ["id3"], "metadatas": [{"w": "c"}],
             "documents": ["d3"]},
        ]

        items = get_all_metadata(col, batch_size=2)
        assert len(items) == 3
        assert col.get.call_count == 2

    def test_returns_empty_on_error(self):
        col = MagicMock()
        col.count.side_effect = Exception("error")

        items = get_all_metadata(col)
        assert items == []
