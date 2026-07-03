"""Tests for core/layers.py — Layer0, Layer1, Layer2, Layer3, MemoryStack."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from mempalace_evolve.core.layers import (
    Layer0,
    Layer1,
    Layer2,
    Layer3,
    MemoryStack,
)


# ---------------------------------------------------------------------------
# Layer0
# ---------------------------------------------------------------------------

class TestLayer0:
    def test_render_from_file(self, tmp_palace):
        """Layer0 reads identity.txt content."""
        ident = Path(tmp_palace) / "identity.txt"
        ident.write_text("Alice the Agent", encoding="utf-8")
        layer = Layer0(identity_path=str(ident))
        text = layer.render()
        assert "Alice" in text

    def test_render_empty_on_missing(self):
        """Layer0 returns empty string when file is missing."""
        layer = Layer0(identity_path="/nonexistent/identity.txt")
        text = layer.render()
        assert text == ""

    def test_render_caches_result(self, tmp_palace):
        """Layer0 caches the rendered text."""
        ident = Path(tmp_palace) / "identity.txt"
        ident.write_text("cached identity", encoding="utf-8")
        layer = Layer0(identity_path=str(ident))
        first = layer.render()
        # Delete file and ensure cache is used
        ident.unlink()
        second = layer.render()
        assert second == first

    def test_token_estimate(self, tmp_palace):
        """token_estimate returns len(text) // 4."""
        ident = Path(tmp_palace) / "identity.txt"
        ident.write_text("Hello World!", encoding="utf-8")
        layer = Layer0(identity_path=str(ident))
        estimate = layer.token_estimate()
        assert estimate == len("Hello World!") // 4

    def test_token_estimate_empty(self):
        """token_estimate returns 0 when no identity file."""
        layer = Layer0(identity_path="/nonexistent/identity.txt")
        assert layer.token_estimate() == 0


# ---------------------------------------------------------------------------
# Layer1 (mocked ChromaDB)
# ---------------------------------------------------------------------------

class TestLayer1:
    def make_mock_col(self, documents=None, metadatas=None, ids=None, count=0):
        """Create a mock ChromaDB Collection with get/query/count."""
        col = MagicMock()
        col.count.return_value = count
        if count > 0:
            col.get.return_value = {
                "ids": ids or [f"id{i}" for i in range(count)],
                "documents": documents or [f"doc{i}" for i in range(count)],
                "metadatas": metadatas or [
                    {"wing": "test", "room": "general", "importance": "0.8"}
                    for _ in range(count)
                ],
            }
        else:
            col.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        return col

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_generate_empty_palace(self, mock_get_collection, tmp_palace):
        """Layer1 generates placeholder when collection is empty."""
        col = self.make_mock_col(count=0)
        mock_get_collection.return_value = col
        layer = Layer1(palace_path=str(tmp_palace))
        text = layer.generate()
        assert "Palace 为空" in text or "empty" in text.lower()

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_generate_with_data(self, mock_get_collection, tmp_palace):
        """Layer1 fetches high-importance drawers and formats them."""
        docs = ["memory about project X", "memory about config Y"]
        metas = [
            {"wing": "wing-a", "room": "decisions", "importance": "0.9", "source_file": "file1.md"},
            {"wing": "wing-b", "room": "config", "importance": "0.7", "source_file": "file2.md"},
        ]
        ids = ["id1", "id2"]
        col = self.make_mock_col(documents=docs, metadatas=metas, ids=ids, count=2)
        mock_get_collection.return_value = col
        layer = Layer1(palace_path=str(tmp_palace))
        text = layer.generate(force_refresh=True)
        assert "L1" in text
        assert "memory about" in text

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_generate_none_collection(self, mock_get_collection, tmp_palace):
        """Layer1 returns empty when get_collection returns None."""
        mock_get_collection.return_value = None
        layer = Layer1(palace_path=str(tmp_palace))
        text = layer.generate(force_refresh=True)
        # Should handle gracefully
        assert isinstance(text, str)
        assert len(text) > 0

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_generate_and_update_wing(self, mock_get_collection, tmp_palace):
        """Layer1 accepts a wing filter which affects fetch calls."""
        col = self.make_mock_col(
            documents=["wing-specific memory"],
            metadatas=[{"wing": "my-project", "room": "room1", "importance": "0.9", "source_file": "f.md"}],
            ids=["id1"],
            count=1,
        )
        mock_get_collection.return_value = col
        layer = Layer1(palace_path=str(tmp_palace), wing="my-project")
        text = layer.generate(force_refresh=True)
        assert "L1" in text

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_cache_ttl(self, mock_get_collection, tmp_palace):
        """Layer1 caches results within TTL."""
        col = self.make_mock_col(
            documents=["cached text"],
            metadatas=[{"wing": "t", "room": "r", "importance": "0.9", "source_file": "f.md"}],
            ids=["id1"],
            count=1,
        )
        mock_get_collection.return_value = col

        layer = Layer1(palace_path=str(tmp_palace))
        text1 = layer.generate(force_refresh=True)
        text2 = layer.generate(force_refresh=False)

        # At this point the get_collection should have only been called once
        # (the force_refresh=True call), the second call uses the cache
        assert mock_get_collection.call_count == 1
        assert text1 == text2


# ---------------------------------------------------------------------------
# Layer2 (mocked ChromaDB)
# ---------------------------------------------------------------------------

class TestLayer2:
    def make_mock_col(self, documents=None, metadatas=None, ids=None, count=0):
        col = MagicMock()
        col.count.return_value = count
        if count > 0:
            col.get.return_value = {
                "ids": ids or [f"id{i}" for i in range(count)],
                "documents": documents or [f"doc{i}" for i in range(count)],
                "metadatas": metadatas or [
                    {"wing": "w", "room": "r", "source_file": "f.md"}
                    for _ in range(count)
                ],
            }
        else:
            col.get.return_value = {"ids": [], "documents": [], "metadatas": []}
        return col

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_retrieve_no_collection(self, mock_get_collection, tmp_palace):
        mock_get_collection.return_value = None
        layer = Layer2(palace_path=str(tmp_palace))
        text = layer.retrieve()
        assert "Palace 不可用" in text or "not available" in text.lower()

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_retrieve_no_results(self, mock_get_collection, tmp_palace):
        col = self.make_mock_col(count=0)
        mock_get_collection.return_value = col
        layer = Layer2(palace_path=str(tmp_palace))
        text = layer.retrieve(wing="unknown")
        assert "无匹配结果" in text or "no matches" in text.lower()

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_retrieve_with_wing(self, mock_get_collection, tmp_palace):
        col = self.make_mock_col(
            documents=["relevant document"],
            metadatas=[{"wing": "my-wing", "room": "decisions", "source_file": "f.md"}],
            ids=["id1"],
            count=1,
        )
        mock_get_collection.return_value = col
        layer = Layer2(palace_path=str(tmp_palace))
        text = layer.retrieve(wing="my-wing")
        assert "L2" in text
        assert "relevant document" in text or "my-wing" in text

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_retrieve_with_wing_and_room(self, mock_get_collection, tmp_palace):
        col = self.make_mock_col(
            documents=["room-specific memory"],
            metadatas=[{"wing": "w", "room": "r", "source_file": "f.md"}],
            ids=["id1"],
            count=1,
        )
        mock_get_collection.return_value = col
        layer = Layer2(palace_path=str(tmp_palace))
        text = layer.retrieve(wing="w", room="r")
        assert "room-specific" in text

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_retrieve_query_exception(self, mock_get_collection, tmp_palace):
        col = MagicMock()
        col.get.side_effect = Exception("DB error")
        mock_get_collection.return_value = col
        layer = Layer2(palace_path=str(tmp_palace))
        text = layer.retrieve(wing="x")
        assert "查询失败" in text or "failed" in text.lower() or "error" in text


# ---------------------------------------------------------------------------
# Layer3 (mocked ChromaDB)
# ---------------------------------------------------------------------------

class TestLayer3:
    def make_mock_query_result(self, documents=None, metadatas=None, ids=None,
                               distances=None, count=0):
        if count == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        return {
            "ids": [ids or [f"id{i}" for i in range(count)]],
            "documents": [documents or [f"result {i}" for i in range(count)]],
            "metadatas": [metadatas or [
                {"wing": "w", "room": "r", "source_file": "f.md"}
                for _ in range(count)
            ]],
            "distances": [distances or [0.5 + i * 0.1 for i in range(count)]],
        }

    def make_mock_col(self, count=0):
        col = MagicMock()
        col.count.return_value = count
        if count > 0:
            col.query.return_value = self.make_mock_query_result(
                count=count,
                ids=[f"id{i}" for i in range(count)],
                distances=[0.5 + i * 0.1 for i in range(count)],
            )
        else:
            col.query.return_value = self.make_mock_query_result(count=0)
        return col

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_search_empty_palace(self, mock_get_collection, tmp_palace):
        col = self.make_mock_col(count=0)
        mock_get_collection.return_value = col
        layer = Layer3(palace_path=str(tmp_palace))
        text = layer.search("test query")
        assert "无结果" in text.lower() or "no results" in text.lower()

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_search_with_results(self, mock_get_collection, tmp_palace):
        docs = ["Alice wrote the design doc", "Bob reviewed the PR"]
        metas = [
            {"wing": "dev", "room": "decisions", "source_file": "doc.md"},
            {"wing": "dev", "room": "review", "source_file": "review.md"},
        ]
        col = MagicMock()
        col.count.return_value = 2
        col.query.return_value = self.make_mock_query_result(
            documents=docs, metadatas=metas,
            ids=["id1", "id2"], distances=[0.3, 0.6], count=2,
        )
        mock_get_collection.return_value = col
        layer = Layer3(palace_path=str(tmp_palace))
        text = layer.search("design document")
        assert "Alice" in text or "design doc" in text
        assert "L3" in text

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_search_raw_returns_list(self, mock_get_collection, tmp_palace):
        docs = ["result text"]
        metas = [{"wing": "w", "room": "r", "source_file": "f.md"}]
        col = MagicMock()
        col.count.return_value = 1
        col.query.return_value = self.make_mock_query_result(
            documents=docs, metadatas=metas,
            ids=["id1"], distances=[0.4], count=1,
        )
        mock_get_collection.return_value = col
        layer = Layer3(palace_path=str(tmp_palace))
        results = layer.search_raw("query")
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["text"] == "result text"

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_search_raw_superseded_filtered(self, mock_get_collection, tmp_palace):
        """Superseded items are filtered out of search_raw results."""
        col = MagicMock()
        col.count.return_value = 1
        col.query.return_value = self.make_mock_query_result(
            documents=["superseded doc"],
            metadatas=[{"wing": "w", "room": "r", "source_file": "f.md", "status": "superseded"}],
            ids=["id1"], distances=[0.4], count=1,
        )
        mock_get_collection.return_value = col
        layer = Layer3(palace_path=str(tmp_palace))
        results = layer.search_raw("query")
        assert len(results) == 0

    def test_search_bundled_default(self, tmp_palace):
        """search_bundled returns dict with direct_hits and bundles keys."""
        layer = Layer3(palace_path=str(tmp_palace))
        # Without a collection, it should return empty lists
        result = layer.search_bundled("test")
        assert isinstance(result, dict)
        assert "direct_hits" in result
        assert "bundles" in result


# ---------------------------------------------------------------------------
# MemoryStack
# ---------------------------------------------------------------------------

class TestMemoryStack:
    @patch("mempalace_evolve.core.layers.get_collection")
    def test_status(self, mock_get_collection, tmp_palace):
        col = MagicMock()
        col.count.return_value = 42
        mock_get_collection.return_value = col
        stack = MemoryStack(palace_path=str(tmp_palace), identity_path=str(Path(tmp_palace) / "id.txt"))
        status = stack.status()
        assert status["total_drawers"] == 42
        assert "palace_path" in status
        assert "l0_tokens" in status

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_wake_up(self, mock_get_collection, tmp_palace):
        """wake_up returns identity + layer1 context."""
        col = MagicMock()
        col.count.return_value = 0
        mock_get_collection.return_value = col
        ident = Path(tmp_palace) / "id.txt"
        ident.write_text("Agent Name", encoding="utf-8")
        stack = MemoryStack(palace_path=str(tmp_palace), identity_path=str(ident))
        result = stack.wake_up()
        assert "Agent" in result

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_recall(self, mock_get_collection, tmp_palace):
        col = MagicMock()
        col.count.return_value = 2
        col.get.return_value = {"ids": ["1","2"], "documents": ["d1","d2"], "metadatas": [{"wing":"w","room":"r","source_file":"f"},{"wing":"w","room":"r","source_file":"f"}]}
        mock_get_collection.return_value = col
        stack = MemoryStack(palace_path=str(tmp_palace))
        result = stack.recall(wing="w", room="r")
        assert "L2" in result

    @patch("mempalace_evolve.core.layers.get_collection")
    def test_search(self, mock_get_collection, tmp_palace):
        col = MagicMock()
        col.count.return_value = 1
        col.query.return_value = {"ids":[["id1"]],"documents":[["found doc"]],"metadatas":[[{"wing":"w","room":"r","source_file":"f"}]],"distances":[[0.5]]}
        mock_get_collection.return_value = col
        stack = MemoryStack(palace_path=str(tmp_palace))
        result = stack.search("test query")
        assert "L3" in result
        assert "found doc" in result
