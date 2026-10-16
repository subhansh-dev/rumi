"""Regression tests for the external eval harness. No network required."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval import metrics as M  # noqa: E402
from eval import harness as H  # noqa: E402


def _report(reported_score: float = 40.0) -> dict:
    return {
        "topic": "Test topic about quantum widgets",
        "domain": "physics",
        "mode": "full",
        "summary_text": "Finding A [1]. Uncited thing happened [9].",
        "observability": {"accessibility_rate": 0.9},
        "canonical_winner_theory": {
            "name": "Widget Resonance Model",
            "description": "A novel mechanism shows the device detected a signal [1] and the value increases with load.",
            "predictions": [
                {"statement": "Signal peaks at 3.2 K [1]", "falsification": "no peak below 5 K"},
                {"statement": "Resistance falls", "falsification": "none"},
            ],
        },
        "phases": {
            "mechanism_generation": {"mechanism_details": [{"name": "m"}]},
            "computational_verification": {"chain": []},
            "discovery_scoring": {
                "discovery_score": reported_score,
                "grade": "F",
                "adversarial_penalty": 0,
                "scores": {"novelty": 40, "explanatory_power": 40, "predictive_power": 40,
                           "falsifiability": 40, "simplicity": 40, "evidence_strength": 40,
                           "mathematical_rigor": 40},
                "weights_used": {"novelty": 0.25, "explanatory_power": 0.20,
                                 "predictive_power": 0.15, "falsifiability": 0.12,
                                 "simplicity": 0.08, "evidence_strength": 0.12,
                                 "mathematical_rigor": 0.08},
            },
        },
    }


def test_citation_validity_flags_out_of_range():
    res = M.citation_validity(_report(), papers=[{"title": "p1"}])
    assert res["out_of_range"] == [9]
    assert res["value"] < 1.0


def test_citation_validity_none_papers():
    assert M.citation_validity(_report(), None)["value"] is None


def test_score_consistency_flags_inflation():
    # dims give base 40; report claims 90 -> inflation
    res = M.score_consistency(_report(reported_score=90.0), tolerance=3.0)
    assert res["inflation"] > 0
    assert res["value"] < 1.0
    # consistent report
    ok = M.score_consistency(_report(reported_score=39.0), tolerance=3.0)
    assert ok["inflation"] == 0
    assert ok["value"] == 1.0


def test_structure_completeness_bounds():
    res = M.structure_completeness(_report())
    assert 0.0 <= res["value"] <= 1.0
    assert res["checks"]["has_falsification"] is True


def test_novelty_vs_archive_isolated(tmp_path):
    archive = tmp_path / "archive.json"
    archive.write_text(json.dumps({"known_theories": [
        {"name": "Other unrelated idea about magnetars", "description": "totally different",
         "run_topic": "something else"}
    ]}), encoding="utf-8")
    res = M.novelty_vs_archive(_report(), current_topic="Test topic about quantum widgets",
                               archive_path=archive)
    assert res["value"] is not None and 0.0 <= res["value"] <= 1.0


def test_run_external_eval_writes_ledger(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    result = H.run_external_eval(_report(reported_score=88.0), papers=[{"title": "p1", "abstract": "device"}],
                                 ledger_path=ledger)
    assert result["external_score"] >= 0
    assert "score_inflation" in result["flags"]
    assert ledger.exists()
    row = json.loads(ledger.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert row["prev_hash"] == "GENESIS"
    assert len(row["hash"]) == 64


def test_ledger_hash_chain(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    H.run_external_eval(_report(), papers=[], ledger_path=ledger)
    H.run_external_eval(_report(), papers=[], ledger_path=ledger)
    rows = [json.loads(l) for l in ledger.read_text(encoding="utf-8").strip().splitlines()]
    assert rows[1]["prev_hash"] == rows[0]["hash"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
