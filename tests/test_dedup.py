"""Tests for core/dedup.py — similarity deduplication and merging."""

import pytest

from mempalace_evolve.core.dedup import (
    find_similar_memories,
    check_and_deduplicate,
    merge_similar_content,
    text_overlap_similarity,
    DEFAULT_SIMILARITY_THRESHOLD,
    MIN_CONTENT_LENGTH,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _col(palace):
    from mempalace_evolve.core.chroma_helper import get_collection
    return get_collection(str(palace.path / "palace"), create=True)


# ---------------------------------------------------------------------------
# text_overlap_similarity
# ---------------------------------------------------------------------------

class TestTextOverlapSimilarity:
    def test_chinese_text_overlap_without_spaces(self):
        score = text_overlap_similarity("项目使用两阶段检索管线", "两阶段检索管线用于项目记忆")
        assert score > 0.3

    def test_min_overlap_ratio_caps_weak_matches(self):
        score = text_overlap_similarity(
            "alpha beta gamma",
            "alpha delta epsilon",
            min_overlap_ratio=0.5,
        )
        assert score < 0.5


# ---------------------------------------------------------------------------
# find_similar_memories
# ---------------------------------------------------------------------------

class TestFindSimilarMemories:
    def test_empty_content(self, palace):
        result = find_similar_memories(_col(palace), wing="test", content="")
        assert result == []

    def test_very_short_content(self, palace):
        result = find_similar_memories(_col(palace), wing="test", content="Hi")
        assert result == []

    def test_whitespace_only(self, palace):
        result = find_similar_memories(_col(palace), wing="test", content="   ")
        assert result == []

    def test_no_matching_memories(self, palace):
        content = "A unique string that likely does not match anything" * 5
        result = find_similar_memories(_col(palace), wing="test", content=content)
        assert result == []

    def test_room_filter_excludes(self, palace):
        content = "Filtered room test content with enough length" * 3
        palace.remember(content, room="config")
        result = find_similar_memories(
            _col(palace), wing="test", content=content,
            room="nonexistent_room", threshold=0.01,
        )
        assert result == []

    def test_returns_valid_list_when_threshold_low(self, palace):
        content = "This is a test memory with enough length for similarity" * 3
        palace.remember(content, room="general")
        result = find_similar_memories(
            _col(palace), wing="test", content=content, threshold=0.01
        )
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# check_and_deduplicate
# ---------------------------------------------------------------------------

class TestCheckAndDeduplicate:
    def test_empty_content(self, palace):
        result = check_and_deduplicate(_col(palace), wing="test", content="")
        assert result["action"] == "allow"

    def test_short_content_allowed(self, palace):
        result = check_and_deduplicate(_col(palace), wing="test", content="short")
        assert result["action"] == "allow"

    def test_no_similar_allowed(self, palace):
        content = "Unique dedup test string with enough characters" * 3
        result = check_and_deduplicate(_col(palace), wing="test", content=content)
        assert result["action"] == "allow"

    def test_allow_action_with_content(self, palace):
        content = "Dedup allow override test content" * 3
        palace.remember(content, room="general")
        result = check_and_deduplicate(
            _col(palace), wing="test", content=content,
            threshold=0.01, action="allow",
        )
        assert result["action"] == "allow"


# ---------------------------------------------------------------------------
# merge_similar_content
# ---------------------------------------------------------------------------

class TestMergeSimilarContent:
    def test_existing_longer_kept(self):
        existing = "This is a longer detailed memory about a specific topic."
        new = "Shorter text."
        merged = merge_similar_content(existing, new)
        assert existing in merged

    def test_new_longer(self):
        existing = "Short."
        new = "This is a much longer memory with more detail and information."
        merged = merge_similar_content(existing, new)
        assert new in merged

    def test_new_content_appended(self):
        existing = "Base memory content."
        new = "Additional new information."
        merged = merge_similar_content(existing, new)
        assert "Additional new information" in merged

    def test_addon_in_base_not_duplicated(self):
        existing = "Full text about a topic."
        merged = merge_similar_content(existing, existing)
        # When addon is already in base, just return base
        assert "---" not in merged or merged == existing

    def test_truncates_very_long(self):
        existing = "X" * 500
        new = "Y" * 500
        merged = merge_similar_content(existing, new)
        assert len(merged) <= 2003

    def test_merging_adds_separator(self):
        existing = "First version."
        new = "Second version with more info."
        merged = merge_similar_content(existing, new)
        assert "---" in merged


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_default_threshold_is_reasonable(self):
        assert 0.7 <= DEFAULT_SIMILARITY_THRESHOLD <= 1.0

    def test_min_content_length(self):
        assert MIN_CONTENT_LENGTH > 0
