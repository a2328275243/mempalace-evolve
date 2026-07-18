"""Deterministic retrieval-quality gate for core memory safety properties."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mempalace_evolve import MemPalace


CASES = json.loads((Path(__file__).parent / "fixtures" / "recall_eval_cases.json").read_text())


def test_fixed_eval_set_recalls_expected_decision(tmp_palace):
    case = next(item for item in CASES if item["name"] == "decision_recall")
    palace = MemPalace(tmp_palace, wing=case["wing"])
    palace.remember(case["content"], room=case["room"])

    results = palace.recall(case["query"], threshold=1.0)

    assert any(case["must_contain"] in result["content"] for result in results)


def test_fixed_eval_set_prevents_cross_wing_leakage(tmp_palace):
    case = next(item for item in CASES if item["name"] == "isolation_secret")
    private = MemPalace(tmp_palace, wing=case["wing"])
    other = MemPalace(tmp_palace, wing="other-team")
    private.remember(case["content"], room=case["room"])

    results = other.recall(case["query"], threshold=1.0)

    assert all(case["content"] not in result["content"] for result in results)


def test_expired_memory_is_not_recalled(tmp_palace):
    palace = MemPalace(tmp_palace, wing="quality")
    memory_id = palace.remember("Expired API token policy", room="config", ttl=60)
    collection = palace._get_collection()
    existing = collection.get(ids=[memory_id], include=["documents", "metadatas"])
    metadata = existing["metadatas"][0]
    metadata["expire_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).timestamp()
    collection.update(ids=[memory_id], documents=existing["documents"], metadatas=[metadata])

    assert palace.recall("API token policy", threshold=1.0) == []


def test_superseded_fact_is_explained(tmp_palace):
    palace = MemPalace(tmp_palace, wing="quality")
    memory_id = palace.remember("Production database is MySQL.", room="decisions")
    collection = palace._get_collection()
    existing = collection.get(ids=[memory_id], include=["documents", "metadatas"])
    metadata = existing["metadatas"][0]
    metadata.update({"status": "superseded", "superseded_by": "Production database is PostgreSQL."})
    collection.update(ids=[memory_id], documents=existing["documents"], metadatas=[metadata])

    result = palace.recall("production database", threshold=1.0)[0]

    assert result["explanation"]["is_superseded"] is True
    assert result["explanation"]["superseded_by"] == "Production database is PostgreSQL."
    assert result["explanation"]["score"]["status_penalty"] == -0.4


def test_stats_reports_lifecycle_distribution(tmp_palace):
    palace = MemPalace(tmp_palace, wing="quality")
    palace.remember("Active memory", room="config")
    expired_id = palace.remember("Expired memory", room="temporary", ttl=60)
    collection = palace._get_collection()
    existing = collection.get(ids=[expired_id], include=["documents", "metadatas"])
    metadata = existing["metadatas"][0]
    metadata["expire_at"] = (datetime.now(timezone.utc) - timedelta(seconds=1)).timestamp()
    collection.update(ids=[expired_id], documents=existing["documents"], metadatas=[metadata])

    lifecycle = palace.stats()["lifecycle"]

    assert lifecycle["active"] == 1
    assert lifecycle["expired"] == 1
