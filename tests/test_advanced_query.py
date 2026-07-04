"""Tests for AdvancedQuery integration and hybrid search."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mempalace_evolve import MemPalace


# Use module-scoped fixture to keep ChromaDB alive for all tests,
# avoiding Windows temp file cleanup issues.
@pytest.fixture(scope="module")
def palace_dir():
    d = tempfile.mkdtemp(prefix="mempalace_aq_")
    yield Path(d)


@pytest.fixture(scope="module")
def palace(palace_dir):
    p = MemPalace(str(palace_dir), wing="test-wing")
    yield p


class TestAdvancedQueryProperty:
    def test_property_exists(self, palace):
        aq = palace.advanced_query
        assert aq is not None
        assert aq._palace is palace

    def test_property_cached(self, palace):
        aq1 = palace.advanced_query
        aq2 = palace.advanced_query
        assert aq1 is aq2


class TestHybridSearch:
    def test_hybrid_search_returns_list(self, palace):
        results = palace.hybrid_search("nothing")
        assert isinstance(results, list)

    def test_hybrid_search_finds_memory(self, palace):
        palace.remember("Paris is the capital of France", room="facts")
        results = palace.hybrid_search("capital of France")
        assert len(results) >= 1
        assert "Paris" in results[0]["content"]

    def test_room_filter_works(self, palace):
        palace.remember("E=mc^2", room="science")
        palace.remember("Pizza is delicious", room="food")
        results = palace.hybrid_search("equation", room="science")
        assert len(results) >= 1
        assert "E=mc^2" in results[0]["content"]

    def test_limit_works(self, palace):
        for i in range(5):
            palace.remember(f"Memory {i} about something", room="test")
        results = palace.hybrid_search("something", limit=3)
        assert len(results) <= 3

    def test_threshold_filters(self, palace):
        palace.remember("Red apple", room="fruits")
        results = palace.hybrid_search("Red apple", threshold=0.1)
        assert len(results) >= 1

    def test_expand_kg_no_error(self, palace):
        palace.remember("Alice knows Bob", room="people")
        palace.add_fact("Alice", "knows", "Bob")
        results = palace.hybrid_search("Alice", expand_kg=True)
        assert isinstance(results, list)


class TestFilterByMetadata:
    def test_basic_filter(self, palace):
        palace.remember("Important decision", room="decisions")
        results = palace.filter_by_metadata(room="decisions")
        assert len(results) >= 1
        assert "decision" in results[0]["content"]

    def test_no_match(self, palace):
        results = palace.filter_by_metadata(room="nonexistent")
        assert results == []
