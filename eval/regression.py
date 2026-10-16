"""
eval/regression.py — frozen regression corpus + leaderboard for RUMI.

Turns saved discovery reports into a FROZEN corpus the harness can re-score, so
any change to the harness, the report schema, or the pipeline can be measured
(score before vs after) WITHOUT running a full discovery again.

    python -m eval.regression build        # build fixtures + baseline from data/
    python -m eval.regression check        # re-score fixtures, diff vs baseline
    python -m eval.regression leaderboard  # print the ranked leaderboard

The corpus is deliberately trimmed to only the fields the harness reads, and
the knowledge archive is snapshotted, so scores are deterministic and
reproducible from a fresh clone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from .harness import run_external_eval, load_config
except ImportError:  # direct execution
    from harness import run_external_eval, load_config  # type: ignore

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

EVAL_DIR = Path(__file__).resolve().parent
REPO = EVAL_DIR.parent
DATA_DIR = REPO / "data"
ARCHIVE_PATH = DATA_DIR / "discovery_archive.json"

CORPUS_DIR = EVAL_DIR / "corpus" / "regression"
FIXTURE_DIR = CORPUS_DIR / "reports"
BASELINE_PATH = CORPUS_DIR / "baseline.json"
ARCHIVE_SNAPSHOT = CORPUS_DIR / "archive_snapshot.json"
CORPUS_LEDGER = CORPUS_DIR / "_score_ledger.jsonl"
LEADERBOARD_PATH = EVAL_DIR / "leaderboard.json"


def _trim(report: dict) -> dict:
    """Keep only the fields the harness actually reads (keeps the corpus tiny)."""
    phases = report.get("phases") or {}
    ds = phases.get("discovery_scoring") or {}
    ds_lean = {k: ds.get(k) for k in (
        "discovery_score", "grade", "scores", "weights_used",
        "adversarial_penalty", "domain_weighted_score") if k in ds}
    cv = phases.get("computational_verification") or {}
    cv_lean = {k: cv.get(k) for k in (
        "total_computations", "support_score", "support_level") if k in cv}
    return {
        "topic": report.get("topic", ""),
        "domain": report.get("domain", ""),
        "mode": report.get("mode", ""),
        "summary_text": report.get("summary_text", "") or "",
        "observability": report.get("observability") or {},
        "canonical_winner_theory": report.get("canonical_winner_theory") or {},
        "phases": {
            "discovery_scoring": ds_lean,
            "computational_verification": cv_lean,
            "mechanism_generation": {"present": bool(phases.get("mechanism_generation"))},
        },
    }


def _score(fixture: dict) -> dict:
    return run_external_eval(
        fixture,
        papers=None,
        ledger_path=CORPUS_LEDGER,
        stamp_archive=False,
        archive_path=ARCHIVE_SNAPSHOT if ARCHIVE_SNAPSHOT.exists() else None,
    )


def build(verbose: bool = True) -> dict:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    # Freeze the archive so novelty scores are deterministic across build/check.
    if ARCHIVE_PATH.exists():
        ARCHIVE_SNAPSHOT.write_text(ARCHIVE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    reports = sorted(DATA_DIR.glob("discovery_v2_*.json"))
    entries = []
    for rp in reports:
        try:
            raw = json.loads(rp.read_text(encoding="utf-8"))
        except Exception:
            continue
        fx = _trim(raw)
        fid = rp.stem
        fp = FIXTURE_DIR / f"{fid}.json"
        fp.write_text(json.dumps(fx, indent=2, ensure_ascii=False), encoding="utf-8")
        res = _score(fx)
        entries.append({
            "id": fid,
            "file": f"reports/{fid}.json",
            "sha256": hashlib.sha256(fp.read_bytes()).hexdigest(),
            "topic": (fx.get("topic", "") or "")[:120],
            "domain": fx.get("domain", ""),
            "external_score": res["external_score"],
            "grade": res["grade"],
            "internal_score": (fx["phases"]["discovery_scoring"] or {}).get("discovery_score"),
            "flags": res["flags"],
        })

    baseline = {
        "harness_version": load_config().get("harness_version", "?"),
        "count": len(entries),
        "entries": entries,
    }
    BASELINE_PATH.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"Built regression corpus: {len(entries)} fixtures -> {FIXTURE_DIR}")
        print(f"Baseline written: {BASELINE_PATH}")
    return baseline


def check(tolerance: float = 1.0, verbose: bool = True) -> int:
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    regressions = []
    for e in baseline["entries"]:
        fx = json.loads((CORPUS_DIR / e["file"]).read_text(encoding="utf-8"))
        res = _score(fx)
        delta = round(res["external_score"] - e["external_score"], 1)
        status = "ok"
        if delta < -tolerance:
            status = "REGRESSION"
            regressions.append((e["id"], e["external_score"], res["external_score"], delta))
        elif delta > tolerance:
            status = "improved"
        if verbose:
            print(f"  {status:>10}  {e['id']:<26} {e['external_score']:>6} -> {res['external_score']:>6}  ({delta:+})")
    if verbose:
        print(f"\n{len(regressions)} regression(s) beyond +/-{tolerance}")
    return 1 if regressions else 0


def leaderboard(verbose: bool = True) -> list:
    rows = []
    for fp in sorted(FIXTURE_DIR.glob("*.json")):
        fx = json.loads(fp.read_text(encoding="utf-8"))
        res = _score(fx)
        rows.append({
            "id": fp.stem,
            "external_score": res["external_score"],
            "grade": res["grade"],
            "internal_score": (fx["phases"]["discovery_scoring"] or {}).get("discovery_score"),
            "flags": res["flags"],
            "domain": fx.get("domain", ""),
            "topic": (fx.get("topic", "") or "")[:100],
        })
    rows.sort(key=lambda r: r["external_score"], reverse=True)
    LEADERBOARD_PATH.write_text(
        json.dumps({"count": len(rows), "rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    if verbose:
        print(f"{'#':>3}  {'ext':>5}  {'gr':>2}  {'int':>5}  {'domain':<16}  topic")
        for i, r in enumerate(rows, 1):
            print(f"{i:>3}  {r['external_score']:>5}  {r['grade']:>2}  {str(r['internal_score']):>5}  "
                  f"{r['domain'][:16]:<16}  {r['topic'][:44]}")
        print(f"\nLeaderboard written: {LEADERBOARD_PATH}")
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="RUMI regression corpus + leaderboard")
    ap.add_argument("cmd", choices=["build", "check", "leaderboard"])
    ap.add_argument("--tolerance", type=float, default=1.0)
    args = ap.parse_args(argv)
    if args.cmd == "build":
        build()
        return 0
    if args.cmd == "check":
        return check(tolerance=args.tolerance)
    leaderboard()
    return 0


if __name__ == "__main__":
    sys.exit(main())
