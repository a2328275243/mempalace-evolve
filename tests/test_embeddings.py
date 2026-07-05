"""Tests for core/embeddings.py — embedding function singleton, hashing, fallback."""

import pytest

from mempalace_evolve.core.embeddings import (
    _hash_embed,
    CachedEmbeddingFunction,
    get_cached_ef,
    get_ef_status,
    EMBEDDING_DIM,
)


# ---------------------------------------------------------------------------
# _hash_embed
# ---------------------------------------------------------------------------

class TestHashEmbed:
    def test_returns_correct_dimension(self):
        embeddings = _hash_embed(["hello", "world"])
        assert len(embeddings) == 2
        assert len(embeddings[0]) == EMBEDDING_DIM
        assert len(embeddings[1]) == EMBEDDING_DIM

    def test_deterministic(self):
        a = _hash_embed(["test"])
        b = _hash_embed(["test"])
        assert a == b

    def test_different_inputs(self):
        a = _hash_embed(["hello"])
        b = _hash_embed(["world"])
        assert a != b

    def test_single_input(self):
        embeddings = _hash_embed(["single"])
        assert len(embeddings) == 1

    def test_empty_input(self):
        embeddings = _hash_embed([])
        assert embeddings == []

    def test_normalized_to_unit_length(self):
        embeddings = _hash_embed(["test text"])
        for vec in embeddings:
            norm = sum(v * v for v in vec)
            assert norm == pytest.approx(1.0, rel=0.01)

    def test_all_values_in_range(self):
        embeddings = _hash_embed(["range test"])
        for vec in embeddings:
            for val in vec:
                assert -1.0 <= val <= 1.0

    def test_many_texts(self):
        texts = [f"text_{i}" for i in range(20)]
        embeddings = _hash_embed(texts)
        assert len(embeddings) == 20


# ---------------------------------------------------------------------------
# CachedEmbeddingFunction
# ---------------------------------------------------------------------------

class TestCachedEmbeddingFunction:
    def test_singleton(self):
        ef1 = get_cached_ef()
        ef2 = get_cached_ef()
        assert ef1 is ef2

    def test_name(self):
        ef = get_cached_ef()
        assert "onnx-minilm" in ef.name().lower()

    def test_default_space(self):
        ef = get_cached_ef()
        assert ef.default_space() == "cosine"

    def test_supported_spaces(self):
        ef = get_cached_ef()
        spaces = ef.supported_spaces()
        assert "cosine" in spaces
        assert isinstance(spaces, list)

    def test_is_legacy(self):
        ef = get_cached_ef()
        assert isinstance(ef.is_legacy(), bool)

    def test_call_returns_embeddings(self):
        ef = get_cached_ef()
        result = ef(["test", "hello"])
        assert len(result) == 2
        assert len(result[0]) == EMBEDDING_DIM

    def test_embed_query(self):
        ef = get_cached_ef()
        result = ef.embed_query(["query test"])
        assert len(result) == 1
        assert len(result[0]) == EMBEDDING_DIM

    def test_embed_with_retries(self):
        ef = get_cached_ef()
        result = ef.embed_with_retries(["retry test"])
        assert len(result) == 1

    def test_is_fallback_boolean(self):
        ef = get_cached_ef()
        assert isinstance(ef.is_fallback, bool)

    def test_get_config(self):
        ef = get_cached_ef()
        config = ef.get_config()
        assert "model_name" in config

    def test_validate_config(self):
        ef = get_cached_ef()
        config = ef.get_config()
        assert ef.validate_config(config) is True
        assert ef.validate_config({"model_name": "unknown"}) is False

    def test_validate_config_update(self):
        ef = get_cached_ef()
        config = ef.get_config()
        assert ef.validate_config_update(config, config) is True

    def test_build_from_config(self):
        ef = get_cached_ef()
        config = ef.get_config()
        ef2 = ef.build_from_config(config)
        assert ef2 is ef

    def test_call_count_increments(self):
        ef = get_cached_ef()
        count_before = ef._call_count
        ef(["counting test"])
        assert ef._call_count > count_before


# ---------------------------------------------------------------------------
# get_ef_status
# ---------------------------------------------------------------------------

class TestEfStatus:
    def test_returns_dict(self):
        status = get_ef_status()
        assert isinstance(status, dict)

    def test_has_expected_keys(self):
        status = get_ef_status()
        assert "loaded" in status
        assert "fallback" in status
        assert "load_time_s" in status
        assert "call_count" in status
        assert "error" in status

    def test_loaded_is_boolean(self):
        status = get_ef_status()
        assert isinstance(status["loaded"], bool)

    def test_call_count_non_negative(self):
        status = get_ef_status()
        assert status["call_count"] >= 0


# ---------------------------------------------------------------------------
# EMBEDDING_DIM constant
# ---------------------------------------------------------------------------

class TestConstants:
    def test_embedding_dim(self):
        assert EMBEDDING_DIM == 384
