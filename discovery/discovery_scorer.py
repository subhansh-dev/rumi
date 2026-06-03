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

        # 7. MATHEMATICAL RIGOR — penalize theories without equations
        math_rigor = self._score_mathematical_rigor(theory, mechanism_steps)

        scores = {
            "novelty": round(novelty, 1),
            "explanatory_power": round(explanatory, 1),
            "predictive_power": round(predictive, 1),
            "falsifiability": round(falsifiability, 1),
            "simplicity": round(simplicity, 1),
            "evidence_strength": round(evidence, 1),
            "mathematical_rigor": round(math_rigor, 1),
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

        # Penalty for failures to explain — halved
        # Honest acknowledgment of limits is good science, not a flaw
        fail_penalty = len(fails) * 5

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
        """Score simplicity (Occam's razor) — balanced, not punitive.

        Complex theories can be correct (Standard Model has 17+ particles).
        We penalize unnecessary complexity, not ambition.
        """
        # Soft penalties — half the old values
        hv_penalty = len(hidden_vars) * 4
        assumption_penalty = len(assumptions) * 3
        step_penalty = max(0, len(mechanism_steps) - 3) * 3

        # Bonus for elegance (concise but powerful)
        elegance_bonus = 0
        if len(mechanism_steps) >= 2 and len(hidden_vars) <= 2:
            elegance_bonus = 10

        # Bonus for ambitious theories that explain more
        ambition_bonus = min(15, len(hidden_vars) * 3) if len(hidden_vars) > 2 else 0

        base = 80 - hv_penalty - assumption_penalty - step_penalty + elegance_bonus + ambition_bonus
        return max(10.0, min(100.0, base))

    def _score_evidence(self, theory: dict, papers: list, graph,
                        theory_scores: dict) -> float:
        """Score evidence strength — quality-weighted."""
        # Use competition scores if available
        if "evidence_support" in theory_scores:
            return theory_scores["evidence_support"] * 100

        base = 30

        # Quality-weighted paper scoring (not just count)
        if papers:
            paper_quality = self._score_literature_quality(papers)
            # Quality score contributes up to 40 points (up from 30)
            base += min(40, paper_quality * 40)

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
        base += min(10, len(steps) * 2)

        return min(100.0, base)

    @staticmethod
    def _score_literature_quality(papers: list) -> float:
        """Score literature quality on 0-1 scale.

        Factors:
        - Citation count (log-scaled, capped)
        - Influential citations (weighted 3x)
        - Recency (newer papers get bonus)
        - Abstract availability (quality signal)
        - Citation network score (from 2-hop walk)
        """
        if not papers:
            return 0.0

        import math
        scores = []
        for p in papers:
            if not isinstance(p, dict):
                continue
            q = 0.0

            # Citation count (log-scaled: 10 citations = 0.3, 100 = 0.5, 1000 = 0.7)
            cites = p.get("citation_count", 0) or 0
            if cites > 0:
                q += min(0.4, math.log10(cites + 1) / 10)

            # Influential citations (weighted 3x)
            inf_cites = p.get("influential_citations", 0) or 0
            if inf_cites > 0:
                q += min(0.2, math.log10(inf_cites + 1) / 15)

            # Recency bonus (papers from last 5 years get bonus)
            try:
                year = int(p.get("year", 0) or 0)
                if year >= 2021:
                    q += 0.15  # Recent
                elif year >= 2015:
                    q += 0.05  # Moderately recent
            except (ValueError, TypeError):
                pass

            # Abstract availability (quality signal)
            abstract = p.get("abstract", "")
            if abstract and len(abstract) > 100:
                q += 0.1

            # Citation network centrality (from 2-hop walk)
            network_score = p.get("citation_network_score", 0)
            if network_score > 0:
                q += min(0.15, network_score * 0.05)

            scores.append(min(1.0, q))

        if not scores:
            return 0.0

        # Return weighted average — top papers contribute more
        scores.sort(reverse=True)
        # Top 10 papers matter most
        top_scores = scores[:10]
        return sum(top_scores) / max(len(top_scores), 1)

    def _score_mathematical_rigor(self, theory: dict, mechanism_steps: list) -> float:
        """Score mathematical rigor — penalize theories without equations."""
        desc = theory.get("description", theory.get("mechanism", ""))
        math_model = theory.get("mathematical_model", "")

        # Check for equations/formulas
        has_equation = any(kw in desc.lower() for kw in [
            "equation", "formula", "=", "derivation", "rate constant",
            "threshold", "concentration", "flux", "amplitude"
        ]) or bool(math_model)

        # Check for quantitative content
        has_numbers = any(c.isdigit() for c in desc)

        # Check for derivation
        has_derivation = any(kw in desc.lower() for kw in [
            "derived from", "follows from", "based on", "framework"
        ])

        # Check for assumptions stated
        has_assumptions = any(kw in desc.lower() for kw in [
            "assuming", "assumption", "given that", "under condition"
        ])

        base = 20  # Start low
        if has_equation:
            base += 30
        if has_numbers:
            base += 20
        if has_derivation:
            base += 20
        if has_assumptions:
            base += 10

        return min(100.0, max(10.0, base))

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
