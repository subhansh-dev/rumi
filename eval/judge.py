"""
eval/judge.py — frozen, cross-family claim judge (optional).

Pinned to a provider family DISJOINT from RUMI's generator (cerebras) and
scorer (groq), so it does not inherit the same-model self-preference bias that
the literature documents. Disabled by default: the core harness has zero
network dependency, this is strictly an add-on.
"""
from __future__ import annotations

import json
import re

_CIT = re.compile(r"\[(\d+)\]")
_WORD_RE = re.compile(r"[a-z0-9]{3,}")
_STOP = {"the", "and", "for", "with", "that", "this", "from", "are", "has",
         "was", "were", "been", "have", "will", "would", "could", "should",
         "into", "over", "such", "than", "them", "then", "they", "using"}


def _tokens(text) -> set[str]:
    return {w for w in _WORD_RE.findall(str(text or "").lower()) if w not in _STOP}


def _pick_claims(report: dict, max_claims: int) -> list[str]:
    w = report.get("canonical_winner_theory") or {}
    if not isinstance(w, dict):
        w = {}
    out: list[str] = []
    desc = str(w.get("description", w.get("mechanism", "")))
    for s in re.split(r"(?<=[.!?])\s+", desc):
        s = s.strip()
        if len(s) >= 40 and (_CIT.search(s) or re.search(r"\d", s)):
            out.append(s)
    for p in (w.get("predictions") or []):
        st = p.get("statement", p.get("description", "")) if isinstance(p, dict) else str(p)
        if st:
            out.append(str(st))
    return out[:max_claims]


def _best_abstract(claim: str, papers: list | None) -> str:
    if not papers:
        return ""
    ct = _tokens(claim)
    best, score = "", 0
    for p in papers:
        if not isinstance(p, dict):
            continue
        ab = str(p.get("abstract", "")).strip()
        if not ab:
            continue
        j = len(ct & _tokens(ab))
        if j > score:
            score, best = j, ab
    return best[:1200]


def judge_claims(report: dict, papers: list | None, cfg: dict) -> dict:
    """Ask a pinned cross-family model whether each claim is supported."""
    try:
        from discovery.llm_client import call
    except Exception as e:  # pragma: no cover - env dependent
        return {"value": None, "error": f"llm_client unavailable: {e}"}

    claims = _pick_claims(report, int(cfg.get("sample_claims", 5)))
    if not claims:
        return {"value": None, "reason": "no claims to judge"}
    provider = cfg.get("provider", "nvidia")
    results = []
    for c in claims:
        ev = _best_abstract(c, papers)
        prompt = (
            "You are a strict scientific verifier. Does the EVIDENCE support the CLAIM?\n"
            'Respond ONLY with JSON: {"support":"yes|partial|no","reason":"<12 words>"}\n\n'
            f"EVIDENCE:\n{ev}\n\nCLAIM:\n{c}"
        )
        raw = None
        try:
            raw = call(prompt, json_mode=True, max_tokens=256, temperature=0.0, provider=provider)
        except Exception:
            raw = None
        support = "no"
        if raw:
            d = {}
            try:
                from discovery.json_extract import extract_json
                d = extract_json(raw)
            except Exception:
                try:
                    d = json.loads(raw)
                except Exception:
                    d = {}
            if isinstance(d, dict):
                support = str(d.get("support", "no")).lower().strip()
        results.append({"claim": c[:140], "support": support, "evidence_found": bool(ev)})

    vals = {"yes": 1.0, "partial": 0.5, "no": 0.0}
    score = sum(vals.get(r["support"], 0.0) for r in results) / len(results)
    return {"value": round(score, 3), "n": len(results), "provider": provider, "details": results}
