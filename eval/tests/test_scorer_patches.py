"""
Tests for the B1/B2 scorer hardening (no network required).

  B1: Phase-9 computational verification now feeds evidence_strength.
  B2: the novelty dimension no longer short-circuits to the competition's
      self-reported number.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from discovery.discovery_scorer import DiscoveryScorer  # noqa: E402


def _scorer():
    return DiscoveryScorer()


# ── B2 ────────────────────────────────────────────────────────────────────
def test_novelty_ignores_self_reported_competition_score():
    s = _scorer()
    theory = {
        "name": "T", "description": "a new mechanism", "type": "novel_mechanism",
        "hidden_variables": [{"type": "novel"}], "predictions": [],
    }
    got = s._score_novelty(theory, {"novelty": 0.99})
    # Old behaviour returned theory_scores["novelty"] * 100 == 99.0
    assert got != 99.0
    # The self-reported value must no longer change the measured dimension.
    assert s._score_novelty(theory, {}) == got


# ── B1 ────────────────────────────────────────────────────────────────────
def test_evidence_folds_in_computational_verification():
    s = _scorer()
    theory = {"name": "T", "description": "x"}
    base = s._score_evidence(theory, [], None, {"evidence_support": 0.9})
    strong = s._score_evidence(
        theory, [], None, {"evidence_support": 0.9},
        {"support_level": "strong", "support_score": 0.9, "total_computations": 9})
    insufficient = s._score_evidence(
        theory, [], None, {"evidence_support": 0.9},
        {"support_level": "insufficient", "support_score": 0.1, "total_computations": 9})
    assert strong > base
    assert insufficient < base


def test_evidence_unchanged_without_computations():
    s = _scorer()
    theory = {"name": "T"}
    base = s._score_evidence(theory, [], None, {"evidence_support": 0.5})
    same = s._score_evidence(
        theory, [], None, {"evidence_support": 0.5},
        {"support_level": "strong", "support_score": 1.0, "total_computations": 0})
    assert base == same


def test_score_wires_computational_result_into_evidence():
    s = _scorer()
    theory = {"name": "T", "description": "x", "scores": {"evidence_support": 0.5}}
    strong = s.score(theory, computational_result={
        "support_level": "strong", "support_score": 1.0, "total_computations": 9})
    weak = s.score(theory, computational_result={
        "support_level": "insufficient", "support_score": 0.0, "total_computations": 9})
    assert strong["scores"]["evidence_strength"] > weak["scores"]["evidence_strength"]


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
