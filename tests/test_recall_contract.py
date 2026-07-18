"""Contracts shared by the SDK and HTTP recall entry points."""

import pytest

from mempalace_evolve.exceptions import ValidationError


def test_recall_exposes_score_evidence_and_lifecycle_status(palace):
    memory_id = palace.remember(
        "The service uses PostgreSQL for durable data.",
        room="decisions",
        source="architecture-notes",
    )

    result = palace.recall("Which database is durable?", limit=1, threshold=1.0)[0]

    assert result["drawer_id"] == memory_id
    assert result["source"] == "wing"
    assert result["explanation"]["source"] == "architecture-notes"
    assert result["explanation"]["match_reason"] == "semantic_vector_similarity"
    assert result["explanation"]["status"] == "active"
    assert result["explanation"]["is_superseded"] is False
    assert set(result["explanation"]["score"]) == {
        "score", "relevance", "recency", "importance", "status_penalty"
    }


@pytest.mark.parametrize(
    ("method", "args", "message"),
    [
        ("remember", ("",), "content"),
        ("remember", ("valid", ""), "room"),
        ("remember", ("valid",), "ttl"),
        ("recall", ("valid",), "limit"),
    ],
)
def test_sdk_rejects_invalid_boundary_values(palace, method, args, message):
    kwargs = {}
    if method == "remember" and message == "ttl":
        kwargs["ttl"] = 0
    if method == "recall" and message == "limit":
        kwargs["limit"] = 0

    with pytest.raises(ValidationError, match=message):
        getattr(palace, method)(*args, **kwargs)


def test_batch_boundaries_are_rejected(palace):
    with pytest.raises(ValidationError, match="500"):
        palace.batch_remember([{"content": str(index)} for index in range(501)])
    with pytest.raises(ValidationError, match="100"):
        palace.batch_recall([str(index) for index in range(101)])


def test_rest_recall_has_sdk_explanation_and_validation(tmp_palace):
    from fastapi.testclient import TestClient
    from mempalace_evolve.adapters.rest_api import create_app

    client = TestClient(create_app(tmp_palace, wing="contract"))
    stored = client.post("/remember", json={"content": "REST contract memory", "room": "config"})
    assert stored.status_code == 200

    recalled = client.post("/recall", json={"query": "contract memory", "threshold": 1.0})
    assert recalled.status_code == 200
    assert recalled.json()["results"][0]["explanation"]["match_reason"] == "semantic_vector_similarity"

    assert client.post("/recall", json={"query": "", "limit": 0}).status_code == 422
    assert client.post("/remember", json={"content": "x", "ttl": 0}).status_code == 422
