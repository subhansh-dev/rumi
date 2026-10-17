"""
eval/backfill_archive.py — stamp external scores onto past archived runs.

eval/harness.py stamps `external_score` onto archive runs going forward. Runs
that predate it have none, which starves the Reflexion gate
(brain/reflexion.py::_external_context) and any same-topic external comparison.
This re-scores the saved reports with the frozen harness and backfills the
archive, marking each backfilled run with `external_source="backfill"` so live
scores stay distinguishable.

    python -m eval.backfill_archive            # dry run (report only)
    python -m eval.backfill_archive --apply    # write data/discovery_archive.json

Scores are best-effort: papers are not stored in the report, so citation/claim
metrics may read lower than a live run. The backfill never runs a discovery.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

try:
    from .harness import run_external_eval
except ImportError:  # direct execution
    from harness import run_external_eval  # type: ignore

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
_LEDGER = Path(tempfile.gettempdir()) / "rumi_backfill_ledger.jsonl"


def _epoch_from_name(path: Path) -> int | None:
    try:
        return int(path.stem.split("_")[-1])
    except Exception:
        return None


def _run_epoch(run: dict) -> int | None:
    ts = run.get("timestamp")
    if not ts:
        return None
    try:
        return int(datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp())
    except Exception:
        return None


def _load_reports() -> list:
    out = []
    for p in sorted(DATA_DIR.glob("discovery_v2_*.json")):
        try:
            rep = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        out.append({"path": p, "topic": rep.get("topic", ""),
                    "epoch": _epoch_from_name(p), "report": rep})
    return out


def _score(report: dict) -> float | None:
    try:
        res = run_external_eval(report, papers=None, ledger_path=_LEDGER,
                                stamp_archive=False)
        return res.get("external_score")
    except Exception:
        return None


def backfill(apply: bool = False) -> dict:
    archive = json.loads(ARCHIVE_PATH.read_text(encoding="utf-8"))
    runs = archive.get("runs", [])
    reports = _load_reports()

    by_topic: dict = {}
    for r in reports:
        by_topic.setdefault(r["topic"], []).append(r)

    score_cache: dict = {}
    stamped = 0
    skipped_no_topic_match = 0
    already = sum(1 for r in runs if isinstance(r.get("external_score"), (int, float)))

    for run in runs:
        topic = run.get("topic", "")
        cands = by_topic.get(topic)
        if not cands:
            skipped_no_topic_match += 1
            continue
        if isinstance(run.get("external_score"), (int, float)):
            continue  # never overwrite a live-stamped score

        if len(cands) == 1:
            best = cands[0]
        else:
            r_epoch = _run_epoch(run)
            if r_epoch is None:
                best = max(cands, key=lambda c: c["epoch"] or 0)
            else:
                best = min(cands, key=lambda c: abs((c["epoch"] or 0) - r_epoch))

        key = str(best["path"])
        if key not in score_cache:
            score_cache[key] = _score(best["report"])
        score = score_cache[key]
        if score is None:
            continue

        run["external_score"] = score
        run["external_source"] = "backfill"
        run["external_eval_at"] = datetime.now().isoformat()
        stamped += 1

    if apply and stamped:
        backup = ARCHIVE_PATH.with_suffix(".json.bak")
        shutil.copy2(ARCHIVE_PATH, backup)
        ARCHIVE_PATH.write_text(json.dumps(archive, indent=2, default=str),
                                encoding="utf-8")

    return {
        "runs": len(runs),
        "already_stamped": already,
        "newly_stamped": stamped,
        "runs_without_topic_match": skipped_no_topic_match,
        "coverage_after": f"{already + stamped}/{len(runs)}",
        "applied": bool(apply and stamped),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Backfill external scores into the archive")
    ap.add_argument("--apply", action="store_true", help="write the archive (default: dry run)")
    args = ap.parse_args(argv)
    summary = backfill(apply=args.apply)
    print(json.dumps(summary, indent=2))
    if not args.apply:
        print("\n(dry run — pass --apply to write data/discovery_archive.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
