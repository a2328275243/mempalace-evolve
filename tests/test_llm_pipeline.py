"""Tests for the LLM-backed memory consolidation pipeline."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from mempalace_evolve.core.llm.client import LLMClient, LLMConfig, get_llm_client, reset_llm_client
from mempalace_evolve.core.llm.types import (
    CandidateMemory,
    ExtractionResult,
    ReviewVerdict,
    ReviewBatchResult,
    ConsolidationPlan,
    MergeGroup,
    DailySummary,
    EvolutionReport,
    EvolutionStep,
)
from mempalace_evolve.core.llm.pipeline import (
    extract_candidates,
    review_candidates,
    consolidate_memories,
    summarize_daily,
    run_llm_pipeline,
)


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_llm():
    """Reset the global LLM client singleton before each test."""
    reset_llm_client()
    yield
    reset_llm_client()


@pytest.fixture
def sample_transcript():
    return """
User: We need to decide on a caching strategy for the API.
Dev: I think Redis is the best option — we already use it for sessions.
User: Let's go with Redis then. Set TTL to 3600 seconds.
Dev: We should also add rate limiting using the same Redis instance.
User: Good idea. The project uses FastAPI so we can use the fastapi-limiter library.
Dev: I'll add that to the config today.
User: Also, remember we switched from PostgreSQL to SQLite for dev environments.
"""


@pytest.fixture
def sample_candidates():
    return [
        {
            "content": "Decided to use Redis for caching with TTL 3600",
            "type": "decision",
            "room": "decisions",
            "score": 0.9,
            "entities": ["Redis", "caching"],
        },
        {
            "content": "FastAPI rate limiting uses fastapi-limiter library",
            "type": "semantic",
            "room": "config",
            "score": 0.7,
            "entities": ["FastAPI", "fastapi-limiter"],
        },
        {
            "content": "hello world",
            "type": "episodic",
            "room": "general",
            "score": 0.1,
            "entities": [],
        },
        {
            "content": "Dev environments use SQLite instead of PostgreSQL",
            "type": "semantic",
            "room": "config",
            "score": 0.6,
            "entities": ["SQLite", "PostgreSQL"],
        },
    ]


@pytest.fixture
def sample_memories():
    return [
        {
            "id": "mem-001",
            "content": "We use Redis for caching with TTL 3600",
            "room": "decisions",
            "filed_at": "2025-07-01T10:00:00Z",
            "importance": 0.9,
        },
        {
            "id": "mem-002",
            "content": "Redis caching with TTL set to 3600 seconds",
            "room": "decisions",
            "filed_at": "2025-07-01T11:00:00Z",
            "importance": 0.85,
        },
        {
            "id": "mem-003",
            "content": "FastAPI uses fastapi-limiter for rate limiting",
            "room": "config",
            "filed_at": "2025-07-01T10:30:00Z",
            "importance": 0.7,
        },
    ]


@pytest.fixture
def mock_llm_response():
    """Factory fixture for creating mock LLM responses."""
    def _make(data: dict) -> dict:
        return {
            "choices": [{
                "message": {
                    "content": __import__("json").dumps(data, ensure_ascii=False),
                },
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        }
    return _make


# ── LLM Client Tests ──────────────────────────────────────────────────

class TestLLMConfig:
    def test_from_env_with_no_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            config = LLMConfig.from_env()
            assert config.api_key is None
            assert config.model == "gpt-4o-mini"

    def test_from_env_with_openai_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}, clear=True):
            config = LLMConfig.from_env()
            assert config.api_key == "sk-test-key"

    def test_from_env_with_llm_api_key(self):
        with patch.dict(os.environ, {"LLM_API_KEY": "llm-test-key"}, clear=True):
            config = LLMConfig.from_env()
            assert config.api_key == "llm-test-key"

    def test_from_env_custom_settings(self):
        env = {
            "OPENAI_API_KEY": "sk-test",
            "LLM_BASE_URL": "https://custom.api.com/v1",
            "LLM_MODEL": "gpt-4o",
            "LLM_TEMPERATURE": "0.5",
            "LLM_MAX_TOKENS": "2048",
            "LLM_TIMEOUT_MS": "60000",
            "LLM_MAX_RETRIES": "3",
        }
        with patch.dict(os.environ, env, clear=True):
            config = LLMConfig.from_env()
            assert config.base_url == "https://custom.api.com/v1"
            assert config.model == "gpt-4o"
            assert config.temperature == 0.5
            assert config.max_tokens == 2048
            assert config.timeout_ms == 60000
            assert config.max_retries == 3


class TestLLMClient:
    def test_not_available_without_key(self):
        client = LLMClient(LLMConfig(api_key=None))
        assert not client.available

    def test_available_with_key(self):
        client = LLMClient(LLMConfig(api_key="sk-test"))
        assert client.available

    def test_available_from_env(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-env-key"}, clear=True):
            client = LLMClient()
            assert client.available

    def test_generate_structured_returns_none_when_unavailable(self):
        client = LLMClient(LLMConfig(api_key=None))
        result = client.generate_structured(
            system_prompt="test",
            prompt="test",
            response_model=ExtractionResult,
        )
        assert result is None

    def test_generate_text_returns_none_when_unavailable(self):
        client = LLMClient(LLMConfig(api_key=None))
        result = client.generate_text(
            system_prompt="test",
            prompt="test",
        )
        assert result is None

    def test_generate_structured_with_valid_response(self, mock_llm_response):
        with patch("httpx.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = mock_llm_response({
                "candidates": [],
                "summary": "Test summary",
            })

            client = LLMClient(LLMConfig(api_key="sk-test"))
            result = client.generate_structured(
                system_prompt="test",
                prompt="test",
                response_model=ExtractionResult,
            )
            assert result is not None
            assert isinstance(result, ExtractionResult)
            assert result.summary == "Test summary"
            assert client.usage.total_calls == 1

    def test_generate_structured_handles_json_error(self, mock_llm_response):
        with patch("httpx.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = mock_llm_response(
                "not valid json"
            )
            # Override content to be invalid JSON
            mock_post.return_value.json.return_value["choices"][0]["message"]["content"] = "invalid json"

            client = LLMClient(LLMConfig(api_key="sk-test", max_retries=0))
            result = client.generate_structured(
                system_prompt="test",
                prompt="test",
                response_model=ExtractionResult,
            )
            assert result is None

    def test_generate_structured_retries_on_failure(self):
        with patch("httpx.post") as mock_post:
            # Fail twice, succeed on third
            import httpx
            mock_post.side_effect = [
                httpx.RequestError("connection error"),
                httpx.RequestError("connection error"),
                httpx.RequestError("connection error"),
            ]

            client = LLMClient(LLMConfig(api_key="sk-test", max_retries=2))
            result = client.generate_structured(
                system_prompt="test",
                prompt="test",
                response_model=ExtractionResult,
            )
            assert result is None
            assert mock_post.call_count == 3  # 1 initial + 2 retries

    def test_parse_json_strips_markdown_fences(self):
        client = LLMClient(LLMConfig(api_key="sk-test"))
        raw = '```json\n{"candidates": [], "summary": "test"}\n```'
        result = client._parse_json(raw, ExtractionResult)
        assert result is not None
        assert result.summary == "test"

    def test_estimated_cost(self):
        client = LLMClient(LLMConfig(api_key="sk-test"))
        client.usage.add(prompt_tokens=1000, completion_tokens=500, duration_ms=200)
        cost = client.usage.estimated_cost_usd("gpt-4o-mini")
        # 1000/1M * 0.15 + 500/1M * 0.60 = 0.00015 + 0.00030 = 0.00045
        assert 0.0004 < cost < 0.0005


# ── Pipeline Step Tests (no LLM) ──────────────────────────────────────

class TestPipelineWithoutLLM:
    """Test that pipeline steps gracefully return None when LLM is unavailable."""

    def test_extract_candidates_no_llm(self):
        result = extract_candidates("some transcript", client=LLMClient(LLMConfig(api_key=None)))
        assert result is None

    def test_review_candidates_no_llm(self, sample_candidates):
        result = review_candidates(sample_candidates, client=LLMClient(LLMConfig(api_key=None)))
        assert result is None

    def test_consolidate_memories_no_llm(self, sample_memories):
        result = consolidate_memories(sample_memories, client=LLMClient(LLMConfig(api_key=None)))
        assert result is None

    def test_summarize_daily_no_llm(self, sample_memories):
        result = summarize_daily(sample_memories, client=LLMClient(LLMConfig(api_key=None)))
        assert result is None

    def test_extract_candidates_empty_transcript(self):
        result = extract_candidates("", client=LLMClient(LLMConfig(api_key=None)))
        assert result is not None  # Empty result is fine
        assert len(result.candidates) == 0

    def test_extract_candidates_none_transcript(self):
        result = extract_candidates(None, client=LLMClient(LLMConfig(api_key=None)))
        assert result is not None
        assert len(result.candidates) == 0

    def test_review_candidates_empty_list(self):
        result = review_candidates([], client=LLMClient(LLMConfig(api_key=None)))
        assert result is not None
        assert len(result.verdicts) == 0

    def test_consolidate_few_memories(self):
        result = consolidate_memories(
            [{"id": "m1", "content": "test"}],
            client=LLMClient(LLMConfig(api_key=None)),
        )
        assert result is not None
        assert len(result.merges) == 0
        assert "Too few" in result.reason

    def test_summarize_daily_empty_memories(self):
        result = summarize_daily([], client=LLMClient(LLMConfig(api_key=None)))
        assert result is not None
        assert result.total_memories == 0


# ── Pipeline Step Tests (mock LLM) ────────────────────────────────────

class TestExtractCandidates:
    def test_extracts_candidates_with_mock_llm(self, sample_transcript, mock_llm_response):
        with patch("httpx.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = mock_llm_response({
                "candidates": [
                    {
                        "content": "Decided to use Redis for caching with TTL 3600",
                        "memory_type": "decision",
                        "room": "decisions",
                        "importance": 0.9,
                        "entities": ["Redis", "caching"],
                        "temporal_context": None,
                    },
                    {
                        "content": "Dev environments switched from PostgreSQL to SQLite",
                        "memory_type": "semantic",
                        "room": "config",
                        "importance": 0.7,
                        "entities": ["PostgreSQL", "SQLite"],
                        "temporal_context": None,
                    },
                ],
                "summary": "Discussion about caching strategy and dev environment configuration.",
            })

            client = LLMClient(LLMConfig(api_key="sk-test"))
            result = extract_candidates(sample_transcript, client=client)
            assert result is not None
            assert isinstance(result, ExtractionResult)
            assert len(result.candidates) == 2
            assert result.candidates[0].room == "decisions"
            assert result.candidates[0].importance == 0.9
            assert result.summary is not None


class TestReviewCandidates:
    def test_reviews_with_mock_llm(self, sample_candidates, mock_llm_response):
        with patch("httpx.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = mock_llm_response({
                "verdicts": [
                    {
                        "action": "promote",
                        "importance_score": 0.9,
                        "reasoning": "Critical architecture decision.",
                        "contradictions": [],
                        "suggested_room": "decisions",
                        "entities": ["Redis", "caching"],
                    },
                    {
                        "action": "promote",
                        "importance_score": 0.7,
                        "reasoning": "Useful config detail.",
                        "contradictions": [],
                        "suggested_room": "config",
                        "entities": ["FastAPI", "fastapi-limiter"],
                    },
                    {
                        "action": "drop",
                        "importance_score": 0.05,
                        "reasoning": "Trivial content.",
                        "contradictions": [],
                        "suggested_room": "general",
                        "entities": [],
                    },
                    {
                        "action": "promote",
                        "importance_score": 0.6,
                        "reasoning": "Important environment config.",
                        "contradictions": [],
                        "suggested_room": "config",
                        "entities": ["SQLite", "PostgreSQL"],
                    },
                ],
            })

            client = LLMClient(LLMConfig(api_key="sk-test"))
            result = review_candidates(sample_candidates, client=client)
            assert result is not None
            assert isinstance(result, ReviewBatchResult)
            assert len(result.verdicts) == 4
            assert result.verdicts[0].action == "promote"
            assert result.verdicts[2].action == "drop"


class TestConsolidateMemories:
    def test_consolidates_duplicates(self, sample_memories, mock_llm_response):
        with patch("httpx.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = mock_llm_response({
                "merges": [
                    {
                        "keep_id": "mem-001",
                        "merge_ids": ["mem-002"],
                        "merged_content": "We use Redis for caching with TTL set to 3600 seconds.",
                        "reason": "Near-duplicate of Redis caching decision.",
                    },
                ],
                "stalls": [],
                "reason": "Found 1 duplicate pair to merge.",
            })

            client = LLMClient(LLMConfig(api_key="sk-test"))
            result = consolidate_memories(sample_memories, client=client)
            assert result is not None
            assert isinstance(result, ConsolidationPlan)
            assert len(result.merges) == 1
            assert result.merges[0].keep_id == "mem-001"
            assert "mem-002" in result.merges[0].merge_ids


class TestSummarizeDaily:
    def test_summarizes_with_mock_llm(self, sample_memories, mock_llm_response):
        with patch("httpx.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            mock_post.return_value.json.return_value = mock_llm_response({
                "date": "2025-07-01",
                "total_memories": 3,
                "by_room": {"decisions": 2, "config": 1},
                "key_decisions": ["Use Redis for caching with TTL 3600"],
                "key_observations": ["FastAPI uses fastapi-limiter"],
                "action_items": [],
                "conflicts_resolved": 0,
                "narrative": "Today we finalized caching strategy and documented rate limiting config.",
            })

            client = LLMClient(LLMConfig(api_key="sk-test"))
            result = summarize_daily(sample_memories, date_str="2025-07-01", client=client)
            assert result is not None
            assert isinstance(result, DailySummary)
            assert result.total_memories == 3
            assert result.by_room["decisions"] == 2
            assert "Redis" in result.key_decisions[0]


# ── Type Validation Tests ─────────────────────────────────────────────

class TestTypeValidation:
    """Test that Pydantic models validate correctly."""

    def test_candidate_memory_validation(self):
        valid = CandidateMemory(content="Test memory")
        assert valid.importance == 0.5
        assert valid.room == "general"

        with pytest.raises(ValueError):
            CandidateMemory(content="Test", importance=1.5)

    def test_review_verdict_validation(self):
        valid = ReviewVerdict(action="promote")
        assert valid.importance_score == 0.5

        with pytest.raises(ValueError):
            ReviewVerdict(action="invalid_action")

    def test_extraction_result_serialization(self):
        result = ExtractionResult(
            candidates=[
                CandidateMemory(
                    content="Test fact",
                    memory_type="semantic",
                    room="general",
                    importance=0.7,
                    entities=["test"],
                ),
            ],
            summary="Test summary",
        )
        data = result.model_dump()
        assert data["candidates"][0]["content"] == "Test fact"
        assert data["summary"] == "Test summary"

    def test_evolution_report_serialization(self):
        report = EvolutionReport(
            steps=[
                EvolutionStep(step="extract", status="success", details={"count": 5}),
                EvolutionStep(step="review", status="success", details={"promoted": 3}),
            ],
            promoted=3,
            merged=2,
            dropped=1,
            duration_ms=1500,
            llm_used=True,
        )
        data = report.model_dump()
        assert data["promoted"] == 3
        assert data["llm_used"] is True
        assert len(data["steps"]) == 2


# ── SDK Integration Tests ─────────────────────────────────────────────

class TestSDKLLMIntegration:
    """Test that the SDK properly integrates LLM features."""

    def test_sdk_llm_enabled_from_env(self, tmp_palace):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            from mempalace_evolve.sdk import MemPalace
            palace = MemPalace(tmp_palace)
            assert palace._llm_enabled is True

    def test_sdk_llm_disabled_by_default(self, tmp_palace):
        with patch.dict(os.environ, {}, clear=True):
            from mempalace_evolve.sdk import MemPalace
            palace = MemPalace(tmp_palace)
            assert palace._llm_enabled is False

    def test_sdk_llm_enabled_explicit(self, tmp_palace):
        from mempalace_evolve.sdk import MemPalace
        palace = MemPalace(tmp_palace, llm_enabled=True)
        assert palace._llm_enabled is True

    def test_sdk_llm_disabled_explicit(self, tmp_palace):
        from mempalace_evolve.sdk import MemPalace
        palace = MemPalace(tmp_palace, llm_enabled=False)
        assert palace._llm_enabled is False

    def test_evolve_skips_llm_when_disabled(self, tmp_palace):
        from mempalace_evolve.sdk import MemPalace
        palace = MemPalace(tmp_palace, llm_enabled=False)
        report = palace.evolve()
        assert isinstance(report, dict)
        assert "promoted" in report
        # LLM should not be present
        assert "llm" not in report
