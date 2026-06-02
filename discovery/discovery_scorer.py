"""
discovery_scorer.py — Score hypotheses on genuine discovery potential.

This is the final quality gate. Every hypothesis gets scored on 6 dimensions:

1. NOVELTY (0-100): Has literature already proposed this?
   - Check against PubMed, hypothesis memory, knowledge graph
   - Penalize restatements of known ideas

2. EXPLANATORY POWER (0-100): How many observations explained?
   - Count gaps and anomalies the hypothesis addresses
   - Reward explanations of multiple phenomena

3. PREDICTIVE POWER (0-100): How many testable predictions?
   - More predictions = better (with quality filter)
   - Counterfactual predictions score highest

4. FALSIFIABILITY (0-100): Can it be disproven?
   - Specific predictions with clear falsification criteria
   - Penalize unfalsifiable claims

5. SIMPLICITY (0-100): Occam's razor
   - Fewer hidden variables = simpler
   - Fewer assumptions = simpler
   - Penalize unnecessary complexity

6. EVIDENCE STRENGTH (0-100): What existing evidence supports it?
   - Paper citations
   - Graph relationship support
   - Experimental validation

FINAL SCORE = weighted combination
"""

import math
from typing import Dict, List, Optional


class DiscoveryScorer:
    """
    Score hypotheses on genuine discovery potential.
    """

    # Default weights (sum to 1.0)
    DEFAULT_WEIGHTS = {
        "novelty": 0.20,
        "explanatory_power": 0.25,
        "predictive_power": 0.20,
        "falsifiability": 0.15,
        "simplicity": 0.10,
        "evidence_strength": 0.10,
    }

    def __init__(self, weights: dict = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def score(self, theory: dict, gaps: list = None, anomalies: list = None,
              predictions: list = None, papers: list = None,
              graph=None) -> dict:
        """
        Score a theory/hypothesis on all discovery dimensions.

        Args:
            theory: The theory dict (from TheoryCompetition or MechanismGenerator)
            gaps: Knowledge gaps this theory addresses
            anomalies: Anomalies this theory explains
            predictions: Testable predictions generated
            papers: Supporting papers
            graph: Knowledge graph for evidence analysis

        Returns:
            {
                "scores": {
                    "novelty": 0-100,
                    "explanatory_power": 0-100,
                    "predictive_power": 0-100,
                    "falsifiability": 0-100,
                    "simplicity": 0-100,
                    "evidence_strength": 0-100
                },
                "weighted_scores": {...},
                "discovery_score": 0-100,
                "grade": "A|B|C|D|F",
                "summary": "...",
                "strengths": [...],
                "weaknesses": [...]
            }
        """
        # Extract theory components
        explains = theory.get("explains", [])
        fails = theory.get("fails_to_explain", [])
        assumptions = theory.get("key_assumptions", [])
        hidden_vars = theory.get("hidden_variables", [])
        mechanism_steps = theory.get("steps", theory.get("mechanism", ""))
        if isinstance(mechanism_steps, str):
            mechanism_steps = [mechanism_steps]
        theory_predictions = theory.get("predictions", [])
        theory_scores = theory.get("scores", {})

        # Merge predictions
        all_predictions = (predictions or []) + [
            {"statement": p, "type": "extracted"} if isinstance(p, str) else p
            for p in theory_predictions
        ]

        # 1. NOVELTY
        novelty = self._score_novelty(theory, theory_scores)

        # 2. EXPLANATORY POWER
        explanatory = self._score_explanatory(theory, gaps, anomalies, explains, fails)

        # 3. PREDICTIVE POWER
        predictive = self._score_predictive(all_predictions)

        # 4. FALSIFIABILITY
        falsifiability = self._score_falsifiability(all_predictions, theory)

        # 5. SIMPLICITY
        simplicity = self._score_simplicity(hidden_vars, assumptions, mechanism_steps)

        # 6. EVIDENCE STRENGTH
        evidence = self._score_evidence(theory, papers, graph, theory_scores)

        scores = {
            "novelty": round(novelty, 1),
            "explanatory_power": round(explanatory, 1),
            "predictive_power": round(predictive, 1),
            "falsifiability": round(falsifiability, 1),
            "simplicity": round(simplicity, 1),
            "evidence_strength": round(evidence, 1),
        }

        # Weighted scores
        weighted = {
            dim: round(score * self.weights.get(dim, 0) / 100.0, 3)
            for dim, score in scores.items()
        }

        # Final discovery score (0-100)
        discovery_score = sum(weighted.values()) * 100.0

        # Grade
        if discovery_score >= 80:
            grade = "A"
        elif discovery_score >= 65:
            grade = "B"
        elif discovery_score >= 50:
            grade = "C"
        elif discovery_score >= 35:
            grade = "D"
        else:
            grade = "F"

        # Strengths and weaknesses
        strengths = []
        weaknesses = []
        for dim, score in scores.items():
            if score >= 70:
                strengths.append(f"{dim}: {score:.0f}/100")
            elif score < 40:
                weaknesses.append(f"{dim}: {score:.0f}/100")

        summary = self._generate_summary(theory, scores, discovery_score, grade)

        return {
            "scores": scores,
            "weighted_scores": weighted,
            "discovery_score": round(discovery_score, 1),
            "grade": grade,
            "summary": summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "weights_used": self.weights,
        }

    def rank_theories(self, theories: list, gaps: list = None,
                      anomalies: list = None, papers: list = None,
                      graph=None) -> list:
        """
        Score and rank multiple theories. Returns sorted list with scores.
        """
        scored = []
        for theory in theories:
            predictions = theory.get("predictions", [])
            result = self.score(theory, gaps, anomalies, predictions, papers, graph)
            theory["discovery_score"] = result["discovery_score"]
            theory["discovery_grade"] = result["grade"]
            theory["discovery_scores"] = result["scores"]
            theory["discovery_summary"] = result["summary"]
            scored.append(theory)

        scored.sort(key=lambda t: t.get("discovery_score", 0), reverse=True)
        return scored

    def _score_novelty(self, theory: dict, theory_scores: dict) -> float:
        """Score how novel this theory is."""
        # Use competition scores if available
        if "novelty" in theory_scores:
            return theory_scores["novelty"] * 100

        # Heuristic: check theory type
        theory_type = theory.get("type", "unknown")
        type_novelty = {
            "proposed": 70,
            "alternative": 60,
            "conventional": 30,
            "null": 10,
            "unknown": 50,
        }
        base = type_novelty.get(theory_type, 50)

        # Boost for hidden variables (novel entities)
        hvs = theory.get("hidden_variables", [])
        if hvs:
            base += min(15, len(hvs) * 5)

        # Boost for novel predictions
        predictions = theory.get("predictions", [])
        novel_preds = sum(1 for p in predictions
                          if isinstance(p, dict) and p.get("novelty") == "novel")
        base += min(15, novel_preds * 5)

        return min(100.0, base)

    def _score_explanatory(self, theory: dict, gaps: list, anomalies: list,
                           explains: list, fails: list) -> float:
        """Score how many observations this theory explains."""
        # Count what it explains
        num_explains = len(explains)

        # Bonus for explaining gaps and anomalies
        gap_bonus = 0
        if gaps:
            gap_bonus = min(20, len(gaps) * 4)
        anomaly_bonus = 0
        if anomalies:
            anomaly_bonus = min(25, len(anomalies) * 5)

        # Penalty for failures to explain
        fail_penalty = len(fails) * 10

        base = 30 + num_explains * 8 + gap_bonus + anomaly_bonus - fail_penalty
        return max(5.0, min(100.0, base))

    def _score_predictive(self, predictions: list) -> float:
        """Score predictive power."""
        if not predictions:
            return 10.0

        num_preds = len(predictions)

        # Quality bonus for specific prediction types
        type_bonus = {
            "counterfactual": 15,
            "interventional": 12,
            "novel": 10,
            "correlational": 5,
        }

        quality_bonus = 0
        for p in predictions:
            ptype = p.get("type", "correlational") if isinstance(p, dict) else "correlational"
            quality_bonus += type_bonus.get(ptype, 5)

        base = 20 + num_preds * 8 + quality_bonus
        return min(100.0, base)

    def _score_falsifiability(self, predictions: list, theory: dict) -> float:
        """Score how falsifiable the theory is."""
        if not predictions:
            return 20.0

        # Count predictions with explicit falsification criteria
        falsifiable_count = 0
        for p in predictions:
            if isinstance(p, dict):
                fals = p.get("falsification", "")
                if fals and len(str(fals)) > 10 and "not specified" not in str(fals).lower():
                    falsifiable_count += 1

        # Check for unfalsifiable claims
        description = str(theory.get("description", ""))
        unfalsifiable_words = ["always", "never", "impossible to test",
                               "cannot be observed", "beyond measurement"]
        penalty = sum(5 for w in unfalsifiable_words if w in description.lower())

        base = 30 + falsifiable_count * 15 - penalty
        return max(10.0, min(100.0, base))

    def _score_simplicity(self, hidden_vars: list, assumptions: list,
                          mechanism_steps: list) -> float:
        """Score simplicity (Occam's razor)."""
        # Penalty for hidden variables
        hv_penalty = len(hidden_vars) * 8

        # Penalty for assumptions
        assumption_penalty = len(assumptions) * 6

        # Penalty for complex mechanisms (more steps = more complex)
        step_penalty = max(0, len(mechanism_steps) - 3) * 5

        # But bonus for concise mechanisms (fewer steps that still explain a lot)
        if len(mechanism_steps) >= 2 and len(hidden_vars) <= 2:
            elegance_bonus = 10
        else:
            elegance_bonus = 0

        base = 80 - hv_penalty - assumption_penalty - step_penalty + elegance_bonus
        return max(10.0, min(100.0, base))

    def _score_evidence(self, theory: dict, papers: list, graph,
                        theory_scores: dict) -> float:
        """Score evidence strength."""
        # Use competition scores if available
        if "evidence_support" in theory_scores:
            return theory_scores["evidence_support"] * 100

        base = 30

        # Papers supporting the theory
        if papers:
            base += min(30, len(papers) * 5)

        # Graph evidence
        if graph:
            entities = graph.entities if hasattr(graph, 'entities') else {}
            relationships = graph.relationships if hasattr(graph, 'relationships') else {}
            # More graph connections = more evidence
            if entities:
                density = len(relationships) / max(1, len(entities))
                base += min(20, density * 10)

        # Mechanism steps (more steps with evidence = stronger)
        steps = theory.get("steps", [])
        base += min(20, len(steps) * 4)

        return min(100.0, base)

    def _generate_summary(self, theory: dict, scores: dict,
                          discovery_score: float, grade: str) -> str:
        """Generate human-readable summary."""
        name = theory.get("name", "Unnamed theory")
        theory_type = theory.get("type", "unknown")

        best_dim = max(scores, key=scores.get)
        worst_dim = min(scores, key=scores.get)

        summary = (f"'{name}' ({theory_type}) scores {discovery_score:.0f}/100 "
                   f"(Grade: {grade}). "
                   f"Strongest: {best_dim} ({scores[best_dim]:.0f}/100). "
                   f"Weakest: {worst_dim} ({scores[worst_dim]:.0f}/100).")

        if grade in ("A", "B"):
            summary += " This is a strong discovery candidate."
        elif grade == "C":
            summary += " Promising but needs stronger evidence or predictions."
        else:
            summary += " Needs significant improvement before presenting as discovery."

        return summary
