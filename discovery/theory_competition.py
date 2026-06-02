"""
theory_competition.py — Generate and evaluate COMPETING explanations.

Single-hypothesis bias is the #1 failure mode of automated discovery.
Real science works by comparing multiple explanations and selecting
the best one.

Inspired by:
  - Thagard's Explanatory Coherence theory
  - Bayesian model comparison (Bayes factors)
  - Minimum Description Length (MDL)
  - Lipton's Inference to the Best Explanation (IBE)

The competition evaluates theories on:
1. Explanatory power — how many observations explained
2. Predictive power — how many testable predictions generated
3. Simplicity — Occam's razor (fewer assumptions = better)
4. Novelty — does it say something new?
5. Falsifiability — can it be disproven?
6. Evidence support — what existing evidence supports it?
7. Coherence — does it fit with established knowledge?
"""

import json
import math
from typing import List, Dict, Optional


class TheoryCompetition:
    """
    Generate competing explanations and evaluate them against each other.
    """

    def __init__(self, graph=None, llm_call=None):
        self.graph = graph
        self.llm_call = llm_call

    def compete(self, mechanisms: list, hidden_variables: list,
                anomalies: list, gaps: list, topic: str, domain: str,
                papers: list = None) -> dict:
        """
        Run theory competition: generate alternatives and score all.

        Returns:
            {
                "theories": [
                    {
                        "name": "...",
                        "description": "...",
                        "type": "proposed|alternative|conventional|null",
                        "mechanism": "...",
                        "hidden_variables": [...],
                        "scores": {
                            "explanatory_power": 0.0-1.0,
                            "predictive_power": 0.0-1.0,
                            "simplicity": 0.0-1.0,
                            "novelty": 0.0-1.0,
                            "falsifiability": 0.0-1.0,
                            "evidence_support": 0.0-1.0,
                            "coherence": 0.0-1.0,
                            "overall": 0.0-1.0
                        },
                        "explains": [...],
                        "fails_to_explain": [...],
                        "predictions": [...]
                    }
                ],
                "winner": {...},
                "competition_analysis": "..."
            }
        """
        if not self.llm_call:
            return {"theories": [], "winner": None, "error": "No LLM client"}

        # Format inputs
        mech_list = mechanisms[:5] if isinstance(mechanisms, list) else mechanisms.get("mechanisms", [])[:5]
        hv_list = hidden_variables[:5] if isinstance(hidden_variables, list) else hidden_variables.get("hidden_variables", [])[:5]

        mech_text = self._format_list(mech_list, "mechanism")
        hv_text = self._format_list(hv_list, "hidden variable")
        anomaly_text = self._format_list(anomalies[:4] if anomalies else [], "anomaly")
        gap_text = self._format_list(gaps[:4] if gaps else [], "gap")

        prompt = f"""You are evaluating competing scientific explanations for a discovery problem.

TOPIC: {topic}
DOMAIN: {domain}

PROPOSED MECHANISMS:
{mech_text}

PROPOSED HIDDEN VARIABLES:
{hv_text}

ANOMALIES TO EXPLAIN:
{anomaly_text}

KNOWLEDGE GAPS:
{gap_text}

Generate 3-5 COMPETING THEORIES that explain the same observations. Include:
1. The proposed mechanism(s) above as Theory A
2. At least 2 ALTERNATIVE explanations that could explain the same anomalies
3. A NULL hypothesis (conventional explanation that doesn't require new mechanisms)
4. At least 1 CREATIVE alternative from a different domain

For each theory, score it on these dimensions (0.0-1.0):
- explanatory_power: How many observations does it explain?
- predictive_power: How many testable predictions does it generate?
- simplicity: Occam's razor — fewer assumptions = higher score
- novelty: Does it say something genuinely new?
- falsifiability: Can it be definitively disproven?
- evidence_support: How much existing evidence supports it?
- coherence: Does it fit with established scientific knowledge?

Output JSON:
{{
  "theories": [
    {{
      "name": "Theory Name",
      "description": "One-paragraph description",
      "type": "proposed|alternative|conventional|null",
      "mechanism": "How this theory explains the observations",
      "hidden_variables": ["any hidden variables it proposes"],
      "scores": {{
        "explanatory_power": 0.0-1.0,
        "predictive_power": 0.0-1.0,
        "simplicity": 0.0-1.0,
        "novelty": 0.0-1.0,
        "falsifiability": 0.0-1.0,
        "evidence_support": 0.0-1.0,
        "coherence": 0.0-1.0,
        "overall": 0.0-1.0
      }},
      "explains": ["which observations this explains"],
      "fails_to_explain": ["which observations this does NOT explain"],
      "predictions": ["key predictions"],
      "key_assumptions": ["what this theory assumes"]
    }}
  ],
  "competition_analysis": "Why the winner is best and what the runner-ups lack",
  "discriminating_experiments": ["experiments that would distinguish between the top 2 theories"]
}}

Be HARSHER on the proposed theories — they need to earn their place. 
The null hypothesis often has high evidence_support but low novelty."""

        try:
            raw = self.llm_call(prompt, max_tokens=8192)
            if not raw:
                try:
                    from discovery.llm_client import call_json
                    raw = call_json(prompt, max_tokens=8192, provider="gemini")
                except Exception:
                    pass
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = json.loads(raw)
                else:
                    result = raw

                if isinstance(result, dict):
                    theories = result.get("theories", [])

                    # Compute weighted overall scores
                    WEIGHTS = {
                        "explanatory_power": 0.25,
                        "predictive_power": 0.20,
                        "simplicity": 0.10,
                        "novelty": 0.10,
                        "falsifiability": 0.15,
                        "evidence_support": 0.10,
                        "coherence": 0.10,
                    }

                    for theory in theories:
                        scores = theory.get("scores", {})
                        # Recompute overall with our weights
                        weighted = sum(
                            scores.get(dim, 0.5) * weight
                            for dim, weight in WEIGHTS.items()
                        )
                        scores["overall"] = round(weighted, 3)
                        theory["scores"] = scores

                    # Sort by overall score
                    theories.sort(key=lambda t: t.get("scores", {}).get("overall", 0),
                                  reverse=True)

                    winner = theories[0] if theories else None

                    result["theories"] = theories
                    result["winner"] = winner
                    result["weights"] = WEIGHTS

                    return result

        except Exception as e:
            return {"theories": [], "winner": None, "error": str(e)}

        return {"theories": [], "winner": None}

    def score_theory(self, theory: dict, observations: list,
                     alternatives: list = None) -> dict:
        """
        Score a single theory against observations and alternatives.
        Uses Thagard's explanatory coherence principles.
        """
        explains = theory.get("explains", [])
        fails = theory.get("fails_to_explain", [])
        predictions = theory.get("predictions", [])
        assumptions = theory.get("key_assumptions", [])

        # Explanatory power: what fraction of observations explained
        total_obs = len(observations) if observations else max(1, len(explains) + len(fails))
        explanatory = len(explains) / total_obs if total_obs > 0 else 0.5

        # Predictive power: more predictions = better (diminishing returns)
        predictive = min(1.0, len(predictions) * 0.2)

        # Simplicity: fewer assumptions = better (penalize complexity)
        simplicity = max(0.1, 1.0 - len(assumptions) * 0.15)

        # Contradiction penalty: theories that contradict evidence are worse
        contradiction_penalty = len(fails) * 0.1

        scores = {
            "explanatory_power": round(explanatory, 3),
            "predictive_power": round(predictive, 3),
            "simplicity": round(simplicity, 3),
            "contradiction_penalty": round(contradiction_penalty, 3),
        }

        return scores

    def _format_list(self, items: list, item_type: str) -> str:
        if not items:
            return f"No {item_type}s available."
        text = ""
        for i, item in enumerate(items, 1):
            if isinstance(item, dict):
                name = item.get("name", item.get("observation", item.get("reason", "?")))
                desc = item.get("description", item.get("mechanism", ""))[:200]
                text += f"\n{i}. {name}\n   {desc}\n"
            else:
                text += f"\n{i}. {str(item)[:200]}\n"
        return text
