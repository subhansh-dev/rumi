"""
Archive continuity — get_archive_context must surface the EXTERNAL score.

eval/README.md promises "one-way continuity: eval -> rumi": the next run should
be able to reference its externally-measured score, not just its self-report.
These tests pin that behaviour.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from discovery import discovery_archive as DA  # noqa: E402


def _write(tmp_path, archive: dict) -> Path:
    p = tmp_path / "arch.json"
    p.write_text(json.dumps(archive), encoding="utf-8")
    return p


def test_context_surfaces_external_score(tmp_path, monkeypatch):
    archive = {
        "runs": [
            {"topic": "dark matter gravitational effects", "domain": "space_astronomy",
             "score": 74.0, "grade": "C", "external_score": 60.4},
            {"topic": "dark matter gravitational effects", "domain": "space_astronomy",
             "score": 39.0, "grade": "F", "external_score": 51.8},
        ],
        "known_theories": [], "known_variables": [], "known_mechanisms": [],
    }
    monkeypatch.setattr(DA, "ARCHIVE_PATH", _write(tmp_path, archive))

    ctx = DA.get_archive_context("dark matter gravitational effects", "space_astronomy")
    assert "external: 60/100" in ctx          # the honest number is shown
    assert "External calibration" in ctx
    assert "self-reported avg" in ctx


def test_context_warns_when_self_report_is_inflated(tmp_path, monkeypatch):
    archive = {
        "runs": [{"topic": "t", "domain": "d", "score": 90.0, "external_score": 40.0}],
        "known_theories": [], "known_variables": [], "known_mechanisms": [],
    }
    monkeypatch.setattr(DA, "ARCHIVE_PATH", _write(tmp_path, archive))
    ctx = DA.get_archive_context("t", "d")
    assert "materially above" in ctx


def test_context_has_no_calibration_without_external_scores(tmp_path, monkeypatch):
    archive = {
        "runs": [{"topic": "t", "domain": "d", "score": 70.0}],
        "known_theories": [], "known_variables": [], "known_mechanisms": [],
    }
    monkeypatch.setattr(DA, "ARCHIVE_PATH", _write(tmp_path, archive))
    ctx = DA.get_archive_context("t", "d")
    assert "External calibration" not in ctx


def test_same_topic_history_flags_regression(tmp_path, monkeypatch):
    archive = {
        "runs": [
            {"topic": "dark matter gravitational effects", "domain": "space_astronomy",
             "score": 21.4, "external_score": 60.4},
            {"topic": "dark matter gravitational effects", "domain": "space_astronomy",
             "score": 62.1, "external_score": 51.8},
        ],
        "known_theories": [], "known_variables": [], "known_mechanisms": [],
    }
    monkeypatch.setattr(DA, "ARCHIVE_PATH", _write(tmp_path, archive))
    ctx = DA.get_archive_context("dark matter gravitational effects", "space_astronomy")
    assert "Same-topic external history (2 run(s))" in ctx
    assert "best 60/100, latest 52/100" in ctx
    assert "REGRESSED" in ctx


def test_no_same_topic_block_for_unrelated_topic(tmp_path, monkeypatch):
    archive = {
        "runs": [{"topic": "protein folding kinetics", "domain": "d",
                  "score": 50.0, "external_score": 50.0}],
        "known_theories": [], "known_variables": [], "known_mechanisms": [],
    }
    monkeypatch.setattr(DA, "ARCHIVE_PATH", _write(tmp_path, archive))
    ctx = DA.get_archive_context("galactic rotation curves", "d")
    assert "Same-topic external history" not in ctx


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
