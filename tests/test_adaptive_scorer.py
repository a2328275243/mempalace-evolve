"""Tests for core/adaptive_scorer.py — confidence computation and wing baselines."""

import json
import math
import tempfile
from pathlib import Path

import pytest

from mempalace_evolve.core.adaptive_scorer import (
    compute_confidence,
    adjust_scores,
    get_baselines_path,
    update_wing_baseline,
    get_wing_adjusted_confidence,
)


# ---------------------------------------------------------------------------
# compute_confidence
# ---------------------------------------------------------------------------

class TestComputeConfidence:
    def test_empty_distances(self):
        result = compute_confidence([])
        assert result["f_dist"] == 0.0
        assert result["f_gap"] == 0.0
        assert result["confidence"] == 0.0
        assert result["suggested_threshold"] == 0.7

    def test_nearly_identical_distances(self):
        result = compute_confidence([0.05])
        assert result["f_dist"] == 1.0
        assert result["confidence"] == 1.0

    def test_moderate_distance(self):
        result = compute_confidence([0.5, 0.65])
        assert 0 < result["f_dist"] < 1.0
        assert result["confidence"] > 0

    def test_large_distance_low_confidence(self):
        result = compute_confidence([1.2])
        assert result["f_dist"] < 0.5

    def test_returns_all_keys(self):
        result = compute_confidence([0.3, 0.5])
        expected_keys = {"f_dist", "f_gap", "confidence", "suggested_threshold"}
        assert set(result.keys()) == expected_keys

    def test_f_gap_large_gap(self):
        result = compute_confidence([0.3, 0.6])
        assert result["f_gap"] == 1.0  # gap > 0.15

    def test_f_gap_medium_gap(self):
        result = compute_confidence([0.3, 0.4])
        assert 0.6 <= result["f_gap"] <= 1.0  # gap ~0.1

    def test_f_gap_small_gap(self):
        result = compute_confidence([0.3, 0.32])
        assert 0.2 <= result["f_gap"] < 0.8  # gap ~0.02

    def test_f_gap_tiny_gap(self):
        result = compute_confidence([0.3, 0.305])
        assert result["f_gap"] == 0.2  # gap <= 0.01

    def test_single_result_high_f_gap(self):
        result = compute_confidence([0.4])
        assert result["f_gap"] == 1.0

    def test_suggested_threshold_range(self):
        result = compute_confidence([0.6])
        assert 0.5 <= result["suggested_threshold"] <= 0.9

    def test_high_confidence_raises_threshold(self):
        high = compute_confidence([0.1, 0.4])
        low = compute_confidence([1.8, 1.85])
        assert high["suggested_threshold"] >= low["suggested_threshold"]

    def test_f_dist_rate_of_change(self):
        """Verify f_dist follows the expected piecewise function."""
        d01 = compute_confidence([0.1])["f_dist"]
        d04 = compute_confidence([0.4])["f_dist"]
        d09 = compute_confidence([0.9])["f_dist"]
        # Near identical is max
        assert d01 == 1.0
        # 0.4 is in the linear decay zone
        assert d04 < 1.0
        # Further is even lower
        assert d09 < d04


# ---------------------------------------------------------------------------
# adjust_scores
# ---------------------------------------------------------------------------

class TestAdjustScores:
    def test_empty_results(self):
        conf = compute_confidence([0.3, 0.5])
        assert adjust_scores([], conf) == []

    def test_high_confidence_preserves_order(self):
        results = [
            {"similarity": 0.9, "id": "a"},
            {"similarity": 0.7, "id": "b"},
            {"similarity": 0.5, "id": "c"},
        ]
        conf = {"confidence": 0.95}
        adjusted = adjust_scores(results, conf)
        assert adjusted[0]["adjusted_similarity"] >= adjusted[-1]["adjusted_similarity"]

    def test_low_confidence_compresses_scores(self):
        results = [
            {"similarity": 0.9, "id": "a"},
            {"similarity": 0.5, "id": "b"},
        ]
        conf = {"confidence": 0.1}
        adjusted = adjust_scores(results, conf)
        mean_sim = (0.9 + 0.5) / 2
        # Low confidence → scores pulled toward mean
        for r in adjusted:
            assert abs(r["adjusted_similarity"] - mean_sim) < 0.1

    def test_adds_adjusted_similarity_key(self):
        results = [{"similarity": 0.8, "id": "x"}]
        conf = {"confidence": 0.5}
        adjusted = adjust_scores(results, conf)
        assert "adjusted_similarity" in adjusted[0]

    def test_sorts_descending(self):
        results = [
            {"similarity": 0.3, "id": "c"},
            {"similarity": 0.9, "id": "a"},
            {"similarity": 0.6, "id": "b"},
        ]
        conf = {"confidence": 0.7}
        adjusted = adjust_scores(results, conf)
        sims = [r["adjusted_similarity"] for r in adjusted]
        assert sims == sorted(sims, reverse=True)

    def test_no_confidence_key_uses_default(self):
        results = [{"similarity": 0.8, "id": "a"}]
        adjusted = adjust_scores(results, {"f_dist": 0.5, "f_gap": 0.5})
        assert adjusted[0]["adjusted_similarity"] > 0

    def test_all_same_similarity(self):
        results = [
            {"similarity": 0.5, "id": "a"},
            {"similarity": 0.5, "id": "b"},
        ]
        conf = {"confidence": 0.5}
        adjusted = adjust_scores(results, conf)
        assert adjusted[0]["adjusted_similarity"] == adjusted[1]["adjusted_similarity"]


# ---------------------------------------------------------------------------
# update_wing_baseline / get_wing_adjusted_confidence
# ---------------------------------------------------------------------------

class TestWingBaselines:
    def test_baselines_path_can_be_overridden(self, monkeypatch, tmp_path):
        path = tmp_path / "runtime" / "baselines.json"
        monkeypatch.setenv("MEMPALACE_ADAPTIVE_BASELINES_PATH", str(path))

        assert get_baselines_path() == path
        update_wing_baseline("isolated_wing", [0.4, 0.6])

        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "isolated_wing" in data

    def test_update_wing_baseline_empty_distances(self):
        # Should not crash
        update_wing_baseline("test_wing", [])
        # After empty update, baseline should still not have meaningful data
        conf = get_wing_adjusted_confidence("test_wing", [0.3, 0.5])
        assert conf["f_dist"] > 0

    def test_get_wing_adjusted_confidence_no_baseline(self):
        conf = get_wing_adjusted_confidence("non_existent_wing", [0.3, 0.5])
        assert "f_dist" in conf
        assert "f_gap" in conf
        assert "suggested_threshold" in conf

    def test_update_then_adjust(self):
        # Update baseline multiple times to simulate data accumulation
        for _ in range(5):
            update_wing_baseline("sparse_wing", [0.8, 0.85, 0.9])
        conf = get_wing_adjusted_confidence("sparse_wing", [0.8, 0.85])
        assert "wing_baseline_avg" in conf
        assert conf["wing_baseline_count"] >= 5
        # High avg distances → lowered threshold
        assert conf["suggested_threshold"] <= 0.71

    def test_dense_wing_raises_threshold(self):
        for _ in range(5):
            update_wing_baseline("dense_wing", [0.15, 0.25, 0.35])
        conf = get_wing_adjusted_confidence("dense_wing", [0.15, 0.25])
        assert "wing_baseline_avg" in conf
        assert conf["wing_baseline_count"] >= 5

    def test_baseline_avg_tracks_moving_average(self):
        update_wing_baseline("moving_wing", [0.5, 0.6])
        conf1 = get_wing_adjusted_confidence("moving_wing", [0.5, 0.6])
        avg_before = conf1.get("wing_baseline_avg", 0.5)
        # Update with lower distances
        for _ in range(10):
            update_wing_baseline("moving_wing", [0.2, 0.3])
        conf2 = get_wing_adjusted_confidence("moving_wing", [0.2, 0.3])
        assert conf2.get("wing_baseline_avg", 0.5) < avg_before
