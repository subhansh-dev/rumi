"""
discovery/diversity_sampler.py — reward-proportional (GFlowNet-style) selection.

These pin the two properties the module actually claims: (1) sampling
probability proportional to reward, and (2) sequential niching keeps a distinct
candidate ahead of a near-duplicate. They also guard the low-temperature
underflow regression (rewards here are <= 1, so R ** (1/T) collapses to zero).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from discovery.diversity_sampler import (  # noqa: E402
    content_words,
    flow_probabilities,
    gflownet_select,
    marginal_diversity,
    population_diversity,
    theory_distance,
)


def test_flow_probabilities_proportional_at_temperature_one():
    # P ∝ R  ->  [1, 2, 4] / 7
    probs = flow_probabilities([1.0, 2.0, 4.0], temperature=1.0)
    assert probs[0] < probs[1] < probs[2]
    assert abs(probs[0] - 1 / 7) < 1e-9
    assert abs(probs[2] - 4 / 7) < 1e-9
    assert abs(sum(probs) - 1.0) < 1e-9


def test_flow_probabilities_argmax_at_low_temperature():
    probs = flow_probabilities([1.0, 2.0, 4.0], temperature=1e-3)
    assert probs[2] > 0.999


def test_flow_probabilities_uniform_at_high_temperature():
    probs = flow_probabilities([1.0, 2.0, 4.0], temperature=1e6)
    assert max(probs) - min(probs) < 1e-3


def test_distance_identical_zero_disjoint_one():
    a = {"name": "modified gravity", "description": "galactic rotation curves"}
    assert theory_distance(a, dict(a)) == 0.0
    b = {"name": "primordial black holes", "description": "microlensing surveys"}
    assert theory_distance(a, b) > 0.9


def test_content_words_drops_stopwords_and_short_tokens():
    words = content_words("The gravitational effects of dark matter are real")
    assert "the" not in words and "are" not in words
    assert "gravitational" in words and "matter" in words


def test_marginal_diversity_empty_set_is_one():
    assert marginal_diversity({"name": "x", "description": "y"}, []) == 1.0


def test_gflownet_select_is_a_permutation_and_seed_reproducible():
    theories = [{"name": f"t{i}", "description": f"distinct idea number {i}",
                 "scores": {"overall": 0.5 + i * 0.01}} for i in range(6)]
    o1 = gflownet_select(theories, seed=7)
    o2 = gflownet_select(theories, seed=7)
    assert o1 == o2
    assert sorted(o1) == list(range(6))


def test_gflownet_select_low_temperature_is_greedy_argmax():
    theories = [
        {"name": "a", "description": "alpha", "scores": {"overall": 0.2}},
        {"name": "b", "description": "beta", "scores": {"overall": 0.9}},
        {"name": "c", "description": "gamma", "scores": {"overall": 0.4}},
    ]
    assert gflownet_select(theories, seed=0, temperature=1e-6)[0] == 1


def test_niching_prefers_distinct_over_near_duplicate():
    dup_a = {"name": "Modified gravity",
             "description": "modified gravity galactic rotation curves",
             "scores": {"overall": 0.8}}
    dup_b = {"name": "Modified gravity",
             "description": "modified gravity galactic rotation curves",
             "scores": {"overall": 0.8}}
    distinct = {"name": "Primordial black holes",
                "description": "primordial black hole microlensing surveys",
                "scores": {"overall": 0.75}}
    theories = [dup_a, dup_b, distinct]

    def reward(t):
        return t["scores"]["overall"]

    def second_is_distinct(dw):
        hits = sum(
            1 for s in range(300)
            if gflownet_select(theories, reward_fn=reward, seed=s,
                               temperature=1.0, diversity_weight=dw)[1] == 2
        )
        return hits / 300

    plain, niched = second_is_distinct(0.0), second_is_distinct(3.0)
    assert niched > plain + 0.1, (plain, niched)


def test_population_diversity_mean_distance():
    theories = [
        {"name": "a", "description": "alpha beta gamma delta"},
        {"name": "b", "description": "epsilon zeta eta theta"},
    ]
    rep = population_diversity(theories)
    assert rep["n"] == 2
    assert rep["mean_pairwise_distance"] == rep["min_distance"]
    assert rep["mean_pairwise_distance"] > 0.5


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
