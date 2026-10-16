"""
eval/harness.py — the External Evaluation Harness orchestrator.

Computes the frozen, external quality score for a finished RUMI report, appends
a hash-chained ledger row, and stamps the score back onto the run RUMI already
saved to its archive (one-way continuity: eval -> rumi).

Typical wiring: called once from discovery_pipeline_v2._finalize_report() just
before the report JSON is written, so the score ships inside the report.

Standalone use (proves it runs fully outside RUMI):
    python -m eval.harness data/discovery_v2_<ts>.json
    python -m eval.harness data/discovery_v2_<ts>.json --judge
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

try:  # imported as a package
    from . import metrics as M
    from . import judge as J
except ImportError:  # run directly
    import metrics as M  # type: ignore
    import judge as J  # type: ignore

EVAL_DIR = Path(__file__).resolve().parent
CONFIG_PATH = EVAL_DIR / "config.json"
LEDGER_PATH = EVAL_DIR / "ledger.jsonl"
_ARCHIVE_PATH = EVAL_DIR.parent / "data" / "discovery_archive.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _grade(score: float) -> str:
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    if score >= 50:
        return "C"
    if score >= 35:
        return "D"
    return "F"


def _last_hash(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        if lines:
            return json.loads(lines[-1]).get("hash", "") or "GENESIS"
    except Exception:
        pass
    return "GENESIS"


def _hash_payload(prev_hash: str, payload: dict) -> str:
    blob = prev_hash + json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _append_ledger(result: dict, ledger_path: Path) -> dict:
    """Append one tamper-evident row. Each row commits to the previous hash."""
    prev = _last_hash(ledger_path)
    payload = {k: v for k, v in result.items() if k != "hash"}
    payload["prev_hash"] = prev
    payload["hash"] = _hash_payload(prev, payload)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, default=str) + "\n")
    return payload


def _stamp_archive(topic: str, external_score: float) -> None:
    """One-way continuity: record the external score on the run just archived."""
    try:
        archive = json.loads(_ARCHIVE_PATH.read_text(encoding="utf-8"))
        for run in reversed(archive.get("runs", [])):
            if str(run.get("topic", "")).strip() == str(topic).strip():
                run["external_score"] = external_score
                run["external_eval_at"] = datetime.now().isoformat()
                break
        _ARCHIVE_PATH.write_text(json.dumps(archive, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass


def _compute_flags(metrics: dict, cfg: dict) -> list[str]:
    flags: list[str] = []
    th = cfg.get("thresholds", {})
    cv = metrics.get("citation_validity", {})
    if cv.get("value") is None:
        flags.append("no_citations")
    elif cv.get("out_of_range"):
        flags.append("invalid_citations")
    csr = metrics.get("claim_support_rate", {})
    if csr.get("value") is None:
        flags.append("no_claims")
    elif isinstance(csr.get("value"), (int, float)) and csr["value"] < th.get("min_claim_support", 0.5):
        flags.append("ungrounded_claims")
    nv = metrics.get("novelty_vs_archive", {})
    if isinstance(nv.get("max_overlap"), (int, float)) and nv["max_overlap"] >= th.get("rediscovery_overlap", 0.5):
        flags.append("rediscovery_vs_archive")
    sc = metrics.get("score_consistency", {})
    if isinstance(sc.get("inflation"), (int, float)) and sc["inflation"] > 0:
        flags.append("score_inflation")
    st = metrics.get("structure_completeness", {})
    if isinstance(st.get("value"), (int, float)) and st["value"] < th.get("min_structure", 0.6):
        flags.append("incomplete_structure")
    return flags


def run_external_eval(report: dict, papers: list | None = None, domain: str | None = None,
                      use_judge: bool | None = None, ledger_path: Path | None = None,
                      stamp_archive: bool = True, archive_path: Path | None = None) -> dict:
    """Compute the external score for one report. Never raises for a valid dict."""
    cfg = load_config()
    domain = domain or report.get("domain", "")

    metrics = {
        "citation_validity": M.citation_validity(report, papers),
        "claim_support_rate": M.claim_support_rate(report, papers),
        "novelty_vs_archive": M.novelty_vs_archive(report, report.get("topic", ""),
                                                   archive_path=archive_path),
        "score_consistency": M.score_consistency(
            report, cfg.get("thresholds", {}).get("score_inflation_tolerance", 3.0)
        ),
        "structure_completeness": M.structure_completeness(report),
        "novelty_vs_heldout": M.novelty_vs_heldout(report),
    }

    want_judge = use_judge if use_judge is not None else bool(cfg.get("judge", {}).get("enabled", False))
    judge = None
    if want_judge:
        try:
            judge = J.judge_claims(report, papers, cfg.get("judge", {}))
            if judge and judge.get("value") is not None:
                metrics["judge_claim_support"] = judge
        except Exception as e:
            judge = {"value": None, "error": str(e)}

    flags = _compute_flags(metrics, cfg)
    if judge and isinstance(judge.get("value"), (int, float)) and \
            judge["value"] < cfg.get("thresholds", {}).get("min_claim_support", 0.5):
        flags.append("judge_unsupported")

    weights = cfg.get("weights", {})
    policy = cfg.get("missing_metric_policy", "zero")
    num = den = 0.0
    for k, w in weights.items():
        v = metrics.get(k, {}).get("value")
        if isinstance(v, (int, float)):
            num += v * w
            den += w
        elif policy == "exclude":
            continue          # weight drops out (renormalizes)
        else:                 # "zero": weight still counts, value contributes 0
            den += w          # -> omission can NEVER raise the score
    external_score = round((num / den) * 100, 1) if den else 0.0

    result = {
        "harness_version": cfg.get("harness_version", "?"),
        "frozen": cfg.get("frozen", True),
        "timestamp": datetime.now().isoformat(),
        "topic": report.get("topic", ""),
        "domain": domain,
        "mode": report.get("mode", ""),
        "external_score": external_score,
        "grade": _grade(external_score),
        "metrics": metrics,
        "flags": flags,
        "weights_used": weights,
        "judge": judge,
        "note": "Computed by eval/harness.py — outside the agent's control. Do NOT let the agent edit eval/.",
    }

    _append_ledger(result, ledger_path or LEDGER_PATH)
    if stamp_archive:
        _stamp_archive(report.get("topic", ""), external_score)
    return result


def _extract_papers(report: dict) -> list | None:
    """Best-effort: pull the paper list out of a saved report for re-scoring."""
    for key in ("papers", "paper_list"):
        if isinstance(report.get(key), list):
            return report[key]
    lit = (report.get("phases") or {}).get("literature") or {}
    for key in ("papers", "paper_list", "sources"):
        if isinstance(lit.get(key), list):
            return lit[key]
    return None


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score a RUMI discovery report externally.")
    ap.add_argument("report", help="Path to data/discovery_v2_<ts>.json")
    ap.add_argument("--judge", action="store_true", help="Enable the frozen cross-family judge")
    ap.add_argument("--ledger", default=str(LEDGER_PATH), help="Ledger path (append-only)")
    args = ap.parse_args(argv)

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    result = run_external_eval(
        report,
        papers=_extract_papers(report),
        domain=report.get("domain", ""),
        use_judge=args.judge,
        ledger_path=Path(args.ledger),
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
