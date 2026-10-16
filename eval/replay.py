"""
eval/replay.py — replay the DiscoveryScorer on a saved report (offline).

Lets us measure scorer-code changes (e.g. B1/B2) WITHOUT running the full
pipeline: it rebuilds the scorer inputs from a stored report, re-runs the
scorer, and diffs the affected dimensions against what the report recorded.

Caveat: gaps / anomalies / papers / the knowledge graph are NOT stored in the
report, so the replay approximates those inputs. Treat it as a directional
check of the scorer logic, not a byte-exact reproduction.

    python -m eval.replay data/discovery_v2_<ts>.json [more...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from discovery.discovery_scorer import DiscoveryScorer  # noqa: E402


def replay(path) -> dict:
    rep = json.loads(Path(path).read_text(encoding="utf-8"))
    phases = rep.get("phases") or {}
    theory = rep.get("canonical_winner_theory") or \
        (phases.get("theory_competition") or {}).get("winner") or {}
    stored = phases.get("discovery_scoring") or {}
    stored_scores = stored.get("scores") or {}
    theory_scores = theory.get("scores") or {}
    comp = phases.get("computational_verification") or {}

    new = DiscoveryScorer().score(
        theory, [], [], list(theory.get("predictions") or []), [],
        adversarial_results=phases.get("adversarial_test"),
        skeptic_result=phases.get("skeptic_review"),
        critical_eval=phases.get("peer_review"),
        computational_result=comp,
    )

    def llm(dim):  # what the OLD short-circuit would have returned
        v = theory_scores.get(dim)
        return round(v * 100, 1) if isinstance(v, (int, float)) else None

    return {
        "id": Path(path).stem,
        "topic": (rep.get("topic", "") or "")[:60],
        "support_level": comp.get("support_level"),
        "total_computations": comp.get("total_computations"),
        "novelty": {"old_llm_shortcircuit": llm("novelty"),
                    "stored": stored_scores.get("novelty"),
                    "new_measured": new["scores"]["novelty"]},
        "evidence": {"old_llm_shortcircuit": llm("evidence_support"),
                     "stored": stored_scores.get("evidence_strength"),
                     "new_measured": new["scores"]["evidence_strength"]},
        "discovery_score": {"stored": stored.get("discovery_score"),
                            "new_replay": new["discovery_score"]},
    }


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("usage: python -m eval.replay <report.json> [...]")
        return 2
    for p in argv:
        r = replay(p)
        print(f"\n=== {r['id']} — {r['topic']} ===")
        print(f"  computational verification: level={r['support_level']} "
              f"computations={r['total_computations']}")
        for name in ("novelty", "evidence"):
            d = r[name]
            print(f"  {name:<9} old(LLM short-circuit)={str(d['old_llm_shortcircuit']):<6} "
                  f"stored={str(d['stored']):<6} new(measured)={d['new_measured']}")
        print(f"  discovery_score: stored={r['discovery_score']['stored']} "
              f"new_replay={r['discovery_score']['new_replay']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
