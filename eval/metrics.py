"""
eval/metrics.py — deterministic, external quality metrics for RUMI reports.

These functions take a finished discovery report as DATA and return numbers.
They never call RUMI's own scorers and never let RUMI influence the result.
Keeping the core metrics deterministic (no LLM) means the headline numbers
cannot drift with model updates and cannot be gamed by prompt edits.

Every metric returns a dict with at least a "value" key (float in [0,1] or
None when it cannot be computed) plus supporting detail.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
ARCHIVE_PATH = _REPO_ROOT / "data" / "discovery_archive.json"
_HELDOUT_PATH = Path(__file__).resolve().parent / "corpus" / "heldout.json"

_CITATION_RE = re.compile(r"\[(\d+)\]")
_WORD_RE = re.compile(r"[a-z0-9]{3,}")
_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "are", "has", "was",
    "were", "been", "have", "will", "would", "could", "should", "into", "over",
    "such", "than", "them", "then", "they", "using", "which", "when", "where",
    "its", "their", "there", "these", "those", "also", "may", "can", "not",
}


class _Missing(dict):
    """Safe wrapper so nested .get chains never explode."""

    def get(self, key, default=None):  # noqa: D401
        return super().get(key, default)


def _get(d: Any, key: str) -> Any:
    return d.get(key) if isinstance(d, dict) else None


def _as_list(x: Any) -> list:
    return x if isinstance(x, list) else []


def _tokens(text: Any) -> set[str]:
    return {w for w in _WORD_RE.findall(str(text or "").lower()) if w not in _STOP}


def _sentences(text: Any) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", str(text or ""))
    return [s.strip() for s in raw if len(s.strip()) >= 30]


def _winner(report: dict) -> dict:
    w = report.get("canonical_winner_theory")
    if isinstance(w, dict):
        return w
    w = (_get(report.get("phases"), "theory_competition") or {}).get("winner")
    return w if isinstance(w, dict) else {}


def _winner_text(report: dict) -> str:
    w = _winner(report)
    parts = [str(w.get("name", "")), str(w.get("description", w.get("mechanism", "")))]
    for p in _as_list(w.get("predictions"))[:8]:
        parts.append(p.get("statement", p.get("description", "")) if isinstance(p, dict) else str(p))
    return "\n".join(x for x in parts if x)


# ──────────────────────────────────────────────────────────────────────────
#  Metric 1 — citation validity (deterministic)
# ──────────────────────────────────────────────────────────────────────────
def citation_validity(report: dict, papers: list | None) -> dict:
    """Fraction of [N] citations in the report that point at a real paper."""
    text = report.get("summary_text", "") or ""
    nums = [int(n) for n in _CITATION_RE.findall(text)]
    if not nums:
        return {"value": None, "total": 0, "valid": 0, "out_of_range": [],
                "reason": "no citations present (weight forfeited under zero-policy)"}
    if papers is None:
        return {"value": None, "total": len(nums), "reason": "papers not provided"}
    n_papers = len(papers)
    valid = [n for n in nums if 1 <= n <= n_papers]
    bad = sorted({n for n in nums if not (1 <= n <= n_papers)})
    return {
        "value": round(len(valid) / len(nums), 3),
        "total": len(nums),
        "valid": len(valid),
        "out_of_range": bad[:20],
        "n_papers": n_papers,
    }


# ──────────────────────────────────────────────────────────────────────────
#  Metric 2 — claim support rate (deterministic; independent recompute)
# ──────────────────────────────────────────────────────────────────────────
_CLAIM_VERBS = (
    "detected", "found", "reported", "measured", "observed", "showed",
    "demonstrated", "confirmed", "established", "increases", "decreases",
    "causes", "leads to", "results in", "predicts", "predict", "reduces",
    "enhances", "inhibits", "correlates", "drives", "induces",
)


def _rumi_uncited(report: dict) -> dict:
    cg = _get(report.get("phases"), "claim_grounding") or {}
    return {"cited": cg.get("cited_papers"), "uncited": cg.get("uncited_claims")}


def claim_support_rate(report: dict, papers: list | None) -> dict:
    """Fraction of factual claim-sentences in the winner that carry a citation.

    Recomputed independently — it does NOT trust RUMI's own claim_grounding.
    RUMI's number is reported alongside so a mismatch is visible.
    """
    claims = []
    for s in _sentences(_winner_text(report)):
        low = s.lower()
        if any(v in low for v in _CLAIM_VERBS) or re.search(r"\d", s):
            claims.append(s)
    rumi = _rumi_uncited(report)
    if not claims:
        return {"value": None, "total": 0, "supported": 0, "unsupported": [],
                "reason": "no factual claims detected", "rumi_uncited": rumi}
    supported = [s for s in claims if _CITATION_RE.search(s) or "[COMPUTED]" in s]
    unsupported = [s for s in claims if s not in supported]
    return {
        "value": round(len(supported) / len(claims), 3),
        "total": len(claims),
        "supported": len(supported),
        "unsupported": [s[:160] for s in unsupported[:10]],
        "rumi_uncited": rumi,
    }


# ──────────────────────────────────────────────────────────────────────────
#  Metric 3 — novelty vs the persistent archive (continuity; deterministic)
# ──────────────────────────────────────────────────────────────────────────
def novelty_vs_archive(report: dict, current_topic: str = "", archive_path: Path | None = None) -> dict:
    """1 - max token-overlap between the winner and PRIOR runs' theories.

    Uses RUMI's own cross-run archive, so continuity is measured against real
    history. Theories from the CURRENT run's topic are excluded (the archive is
    already written before this runs).
    """
    path = archive_path or ARCHIVE_PATH
    try:
        archive = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        archive = {}
    w = _winner(report)
    wtok = _tokens(f"{w.get('name', '')} {w.get('description', w.get('mechanism', ''))}")
    topic = (current_topic or report.get("topic", "") or "").strip()
    if not wtok:
        return {"value": None, "reason": "no winner text", "max_overlap": 0.0, "match": None}
    prior = [
        t for t in _as_list(archive.get("known_theories"))
        if isinstance(t, dict) and (str(t.get("run_topic", "")).strip() != topic)
    ]
    best, match = 0.0, None
    for t in prior:
        ttok = _tokens(f"{t.get('name', '')} {t.get('description', '')}")
        if not ttok:
            continue
        j = len(wtok & ttok) / max(1, len(wtok | ttok))
        if j > best:
            best, match = j, t.get("name")
    return {
        "value": round(1.0 - best, 3),
        "max_overlap": round(best, 3),
        "match": match,
        "compared_against": len(prior),
    }


# ──────────────────────────────────────────────────────────────────────────
#  Metric 4 — score consistency / inflation audit (deterministic)
# ──────────────────────────────────────────────────────────────────────────
def score_consistency(report: dict, tolerance: float = 3.0) -> dict:
    """Audit RUMI's own discovery_score against its own dimension scores.

    Recomputes sum(dimension * weight) from the STORED per-dimension scores and
    the STORED weights, then checks that the reported score does not exceed the
    ceiling its own dimensions allow. A reported score above that ceiling is
    the classic "score inflation" exploit.
    """
    ds = _get(report.get("phases"), "discovery_scoring") or {}
    reported = float(ds.get("discovery_score", 0) or 0)
    dims = ds.get("scores") or {}
    weights = ds.get("weights_used") or {}
    if not dims or not weights:
        return {"value": None, "reason": "no dimension scores stored", "reported": reported}
    recomputed = sum(float(dims.get(d, 0) or 0) * float(weights.get(d, 0) or 0) for d in weights)
    inflation = max(0.0, reported - (recomputed + tolerance))
    value = 1.0 if inflation <= 0 else max(0.0, 1.0 - inflation / 25.0)
    return {
        "value": round(value, 3),
        "reported": round(reported, 1),
        "recomputed_base": round(recomputed, 1),
        "inflation": round(inflation, 1),
        "tolerance": tolerance,
        "adversarial_penalty": ds.get("adversarial_penalty", 0),
        "domain_weighted_score": ds.get("domain_weighted_score"),
        "grade": ds.get("grade"),
    }


# ──────────────────────────────────────────────────────────────────────────
#  Metric 5 — structural completeness (deterministic)
# ──────────────────────────────────────────────────────────────────────────
def structure_completeness(report: dict) -> dict:
    """Fraction of a minimal scientific contract present in the output."""
    phases = report.get("phases") or {}
    w = _winner(report)
    preds = _as_list(w.get("predictions"))
    checks = {
        "winner_named": bool(str(w.get("name", "")).strip()),
        "winner_described": len(str(w.get("description", w.get("mechanism", "")))) > 40,
        "has_predictions": len(preds) >= 1,
        "has_falsification": any(
            isinstance(p, dict)
            and str(p.get("falsification", p.get("falsification_criterion", ""))).strip().lower()
            not in ("", "none", "test failed")
            for p in preds
        ),
        "has_mechanism_steps": bool(phases.get("mechanism_generation")),
        "has_computation": bool(phases.get("computational_verification")),
        "has_observability": bool(report.get("observability")),
    }
    value = sum(1 for v in checks.values() if v) / len(checks)
    return {"value": round(value, 3), "checks": checks}


# ──────────────────────────────────────────────────────────────────────────
#  Metric 6 — novelty vs the held-out corpus (opt-in; scaffolding)
# ──────────────────────────────────────────────────────────────────────────
def novelty_vs_heldout(report: dict, heldout_path: Path | None = None) -> dict:
    """1 - max overlap with held-out known findings. Disabled when corpus empty."""
    path = heldout_path or _HELDOUT_PATH
    try:
        corpus = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"value": None, "reason": "no heldout corpus file"}
    entries = _as_list(corpus.get("entries"))
    if not entries:
        return {"value": None, "reason": "heldout corpus empty (populate to enable)"}
    w = _winner(report)
    wtok = _tokens(f"{w.get('name', '')} {w.get('description', '')}")
    if not wtok:
        return {"value": None, "reason": "no winner text"}
    best, match = 0.0, None
    for e in entries:
        etok = {str(x).lower() for x in _as_list(e.get("key_terms"))}
        if not etok:
            continue
        j = len(wtok & etok) / max(1, len(wtok | etok))
        if j > best:
            best, match = j, e.get("topic")
    return {"value": round(1.0 - best, 3), "max_overlap": round(best, 3), "match": match}
