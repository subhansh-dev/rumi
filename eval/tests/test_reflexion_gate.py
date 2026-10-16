"""
Tests for the A2 Reflexion hardening (no network required).

A2 changes Reflexion's objective from the self-reported "patches applied" count
to the EXTERNAL score, gates patches on the frozen tests/corpus, and reverts a
cycle whose patches regressed the external score on the same topic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from brain import reflexion as R  # noqa: E402


def _make_improver(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "HISTORY_FILE", tmp_path / "hist.json")
    monkeypatch.setattr(R, "PATCHES_DIR", tmp_path / "patches")
    monkeypatch.setattr(R, "ARCHIVE_FILE", tmp_path / "arch.json")
    monkeypatch.setattr(R, "BRAIN_DIR", tmp_path / "brain")
    (tmp_path / "brain").mkdir(exist_ok=True)
    return R.RecursiveImprover(llm_fn=None)


# ── goal-post protection ──────────────────────────────────────────────────
def test_forbidden_paths_block_eval_and_scoring():
    assert R._is_forbidden_path(ROOT / "eval" / "regression.py")
    assert R._is_forbidden_path(ROOT / "eval" / "config.json")
    assert R._is_forbidden_path(ROOT / "discovery" / "discovery_scorer.py")
    assert R._is_forbidden_path(ROOT / "discovery" / "theory_competition.py")
    assert not R._is_forbidden_path(ROOT / "discovery" / "hypothesis_engine.py")


# ── external context reads only harness-stamped scores ────────────────────
def test_external_context_reads_archive(tmp_path, monkeypatch):
    arch = {"runs": [
        {"topic": "T", "domain": "physics", "external_score": 40.0},
        {"topic": "T", "domain": "physics", "external_score": 55.0},
        {"topic": "U", "domain": "physics", "external_score": 70.0},
    ]}
    f = tmp_path / "arch.json"
    f.write_text(json.dumps(arch), encoding="utf-8")
    monkeypatch.setattr(R, "ARCHIVE_FILE", f)

    ctx = R._external_context({"query": "T", "domain": "physics"})
    assert ctx["same_topic_scores"] == [40.0, 55.0]
    assert ctx["same_topic_last"] == 55.0
    assert ctx["same_topic_count"] == 2
    assert ctx["domain_avg"] == round((40 + 55 + 70) / 3, 1)


# ── objective is the external signal, not applied/total ───────────────────
def test_objective_is_external_not_applied_count():
    s = R.RecursiveImprover._external_improvement_score
    # No comparable measurement -> unknown (None), never a self-reported number.
    assert s({}, {"status": "n/a"}) is None
    # A regression drives it to 0.
    assert s({}, {"status": "reverted"}) == 0.0
    # Kept + improved -> the external delta fraction.
    assert s({}, {"status": "kept", "score_before": 50.0, "score_after": 60.0}) == 0.2
    # Fallback to the same-topic external trend.
    assert s({"same_topic_scores": [40.0, 50.0]}, {"status": "n/a"}) == 0.25


# ── previous cycle is reverted on a same-topic external regression ────────
def test_previous_cycle_reverts_on_regression(tmp_path, monkeypatch):
    impr = _make_improver(tmp_path, monkeypatch)
    target = tmp_path / "mod.py"
    target.write_text("x = 2\n", encoding="utf-8")          # "patched" state
    (tmp_path / "patches").mkdir(exist_ok=True)
    (tmp_path / "patches" / "mod_backup.backup").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "arch.json").write_text(json.dumps({"runs": [
        {"topic": "T", "domain": "d", "external_score": 40.0},
        {"topic": "T", "domain": "d", "external_score": 60.0},
        {"topic": "T", "domain": "d", "external_score": 55.0},   # regressed
    ]}), encoding="utf-8")

    impr._history = [{"timestamp": "t", "result": {
        "verification_pending": True, "topic": "T", "external_before": 60.0,
        "external_context": {"topic": "T", "same_topic_count": 2},
        "applied_patches": [{"file": "mod.py", "backup": "mod_backup.backup",
                             "description": "d", "commit": "abc"}],
    }}]

    gate = impr._evaluate_previous_cycle()
    assert gate["status"] == "reverted"
    assert target.read_text(encoding="utf-8") == "x = 1\n"   # restored from backup


def test_previous_cycle_kept_when_not_regressed(tmp_path, monkeypatch):
    impr = _make_improver(tmp_path, monkeypatch)
    target = tmp_path / "mod.py"
    target.write_text("x = 2\n", encoding="utf-8")
    (tmp_path / "arch.json").write_text(json.dumps({"runs": [
        {"topic": "T", "domain": "d", "external_score": 40.0},
        {"topic": "T", "domain": "d", "external_score": 44.0},   # improved
    ]}), encoding="utf-8")
    impr._history = [{"timestamp": "t", "result": {
        "verification_pending": True, "topic": "T", "external_before": 40.0,
        "external_context": {"topic": "T", "same_topic_count": 1},
        "applied_patches": [{"file": "mod.py", "backup": "b.backup",
                             "description": "d", "commit": "abc"}],
    }}]
    gate = impr._evaluate_previous_cycle()
    assert gate["status"] == "kept"
    assert target.read_text(encoding="utf-8") == "x = 2\n"   # untouched


def test_regression_gate_disabled_is_skipped(tmp_path, monkeypatch):
    impr = _make_improver(tmp_path, monkeypatch)
    monkeypatch.setattr(R, "REGRESSION_GATE_ENABLED", False)
    assert impr._regression_gate()["status"] == "skipped"


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
