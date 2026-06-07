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
    # Novelty is weighted highest — a discovery engine must produce NEW knowledge
    # Mathematical rigor is lower — not all discoveries need equations (theoretical work is valid)
    DEFAULT_WEIGHTS = {
        "novelty": 0.25,
        "explanatory_power": 0.20,
        "predictive_power": 0.15,
        "falsifiability": 0.12,
        "simplicity": 0.08,
        "evidence_strength": 0.12,
        "mathematical_rigor": 0.08,
    }

    def __init__(self, weights: dict = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def score(self, theory: dict, gaps: list = None, anomalies: list = None,
              predictions: list = None, papers: list = None,
              graph=None,
              adversarial_results: dict = None,
              skeptic_result: dict = None,
              critical_eval: dict = None) -> dict:
        """
        Score a theory/hypothesis on all discovery dimensions.

        Args:
            theory: The theory dict (from TheoryCompetition or MechanismGenerator)
            gaps: Knowledge gaps this theory addresses
            anomalies: Anomalies this theory explains
            predictions: Testable predictions generated
            papers: Supporting papers
            graph: Knowledge graph for evidence analysis
            adversarial_results: Results from Phase 8.5 adversarial test
            skeptic_result: Results from Phase 11 skeptic review
            critical_eval: Results from Phase 8.6 critical evaluation

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
        # Guard against None inputs
        gaps = gaps or []
        anomalies = anomalies or []
        predictions = predictions or []
        papers = papers or []

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

        # Cap dimensions for known science — old theories shouldn't score high
        novelty_verdict = theory.get("is_novel_vs_known", theory.get("novelty_verdict", ""))
        if novelty_verdict in ("well_known", "rediscovery"):
            # Known theories have predictions because they're OLD, not because they're good
            predictive = min(predictive, 40)
            falsifiability = min(falsifiability, 40)
            explanatory = min(explanatory, 50)

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

        # ── Adversarial penalty — reduce score based on adversarial results ──
        adversarial_penalty = 0
        adversarial_details = []

        # Evidence strength floor — cap score if evidence is too weak
        if evidence < 20:
            discovery_score = min(discovery_score, 50)
            adversarial_details.append(f"Evidence floor: {evidence:.0f}/100 -> capped at 50")

        # Known science penalty — if novelty verdict says well_known/rediscovery, penalize
        novelty_verdict = theory.get("is_novel_vs_known", theory.get("novelty_verdict", ""))
        if novelty_verdict in ("well_known", "rediscovery"):
            adversarial_penalty += 20
            adversarial_details.append(f"Known science penalty: {novelty_verdict} (-20)")
        elif novelty_verdict == "refinement":
            adversarial_penalty += 5
            adversarial_details.append(f"Refinement penalty: not fully novel (-5)")

        # Adversarial test results (Phase 8.5)
        if adversarial_results:
            summary = adversarial_results.get("survival_summary", {})
            for category in ["theories", "mechanisms", "hidden_variables"]:
                cat_summary = summary.get(category, {})
                killed = cat_summary.get("killed", 0)
                started = cat_summary.get("started", 0)
                if started > 0 and killed > 0:
                    kill_ratio = killed / started
                    penalty = kill_ratio * 20  # up to 20 points for all killed
                    adversarial_penalty += penalty
                    adversarial_details.append(f"Adversarial {category}: {killed}/{started} killed (-{penalty:.0f})")

        # Skeptic review results (Phase 11)
        if skeptic_result:
            rec = skeptic_result.get("recommendation", "unknown")
            conf = skeptic_result.get("revised_confidence", 0)
            if rec == "reject":
                adversarial_penalty += 15
                adversarial_details.append(f"Skeptic: reject (-15)")
            elif rec == "revise":
                adversarial_penalty += 2
                adversarial_details.append(f"Skeptic: revise (-2)")
            if conf < 0.2:
                discovery_score = min(discovery_score, 65)
                adversarial_details.append(f"Skeptic confidence {conf:.0%} -> capped at 65")

        # Critical evaluation results (Phase 8.6)
        if critical_eval:
            eval_score = critical_eval.get("overall_score", 10)
            if eval_score < 3:
                adversarial_penalty += 5
                adversarial_details.append(f"Critical eval {eval_score}/10 (-5)")
            elif eval_score < 5:
                adversarial_penalty += 2
                adversarial_details.append(f"Critical eval {eval_score}/10 (-2)")

        # Tournament reliability — penalize algorithmic fallback
        if theory.get("tournament_status") == "algorithmic_fallback":
            adversarial_penalty += 10
            adversarial_details.append("Tournament algorithmic fallback (-10)")

        # Apply penalty
        discovery_score = max(0, discovery_score - adversarial_penalty)

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
            "adversarial_penalty": round(adversarial_penalty, 1),
            "adversarial_details": adversarial_details,
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
        """Score novelty at COMPONENT level — a theory can be novel in parts.

        A theory that builds on known work but introduces a new mechanism,
        new prediction, or new variable IS novel in those components.
        We reward novelty where it exists, not penalize for building on foundations.
        """
        # Use competition scores if available
        if "novelty" in theory_scores:
            return theory_scores["novelty"] * 100

        novelty_verdict = theory.get("is_novel_vs_known", theory.get("novelty_verdict", ""))
        novelty_score = theory.get("novelty_score", 0)

        # Component-level scoring
        score = 40  # base — every theory starts with some novelty potential

        # Component 1: Novel hidden variables (+5 each, max +20)
        hvs = theory.get("hidden_variables") or []
        novel_hvs = sum(1 for h in hvs if isinstance(h, dict) and h.get("type") not in ("known", "established"))
        score += min(20, novel_hvs * 5)

        # Component 2: Novel predictions (+8 each, max +25)
        predictions = theory.get("predictions") or []
        novel_preds = sum(1 for p in predictions
                          if isinstance(p, dict) and p.get("novelty") == "novel")
        score += min(25, novel_preds * 8)

        # Component 3: New mechanism type
        theory_type = theory.get("type", "")
        if theory_type in ("counterfactual", "novel_mechanism"):
            score += 15
        elif theory_type in ("proposed", "alternative"):
            score += 10

        # Component 4: Theory has description with novel content indicators
        desc = theory.get("description", theory.get("mechanism", ""))
        novel_indicators = ["novel", "new mechanism", "proposed", "unexplored", "unprecedented",
                           "first time", "never before", "not yet", "unknown"]
        if any(kw in desc.lower() for kw in novel_indicators):
            score += 10

        # Component 5: Penalize "exotic physics soup" — combining popular speculative ideas
        soup_indicators = [
            "dark photon", "sterile neutrino", "dark energy coupling", "dark matter decay",
            "primordial black hole", "axion", "wimp", "kaluza-klein", "string theory",
            "supersymmetry", "extra dimension", "brane", "moduli"
        ]
        soup_count = sum(1 for kw in soup_indicators if kw in desc.lower())
        if soup_count >= 3:
            score -= 15  # penalty for combining 3+ popular speculative ideas
        elif soup_count >= 2:
            score -= 8   # penalty for combining 2 popular speculative ideas

        # Component 5: Mathematical novelty
        math_model = theory.get("mathematical_model", "")
        if math_model:
            score += 10

        # Component 6: Constructed variable bonus — theory introduces NEW named parameters
        # Look for Greek letters or invented variable names (not standard symbols)
        import re
        custom_vars = re.findall(r'[A-Z][a-z]*_[A-Z][a-z]*|[a-z]{2,}_[a-z]{2,}', desc)
        if custom_vars:
            score += min(10, len(custom_vars) * 3)  # bonus for constructed variables

        # Apply verdict as modifier (not as hard score)
        if novelty_verdict == "well_known":
            score = min(score, 30)  # cap but don't zero out
        elif novelty_verdict == "rediscovery":
            score = min(score, 40)
        elif novelty_verdict == "refinement":
            score = min(score, 85)  # refinement with novel parts can score high
        elif novelty_verdict == "novel":
            score = max(score, 70)  # ensure novel theories score high

        # Blend with numeric novelty score if available
        if novelty_score > 0:
            score = (score + novelty_score * 100) / 2

        return min(100.0, max(10.0, score))

    def _score_explanatory(self, theory: dict, gaps: list, anomalies: list,
                           explains: list, fails: list) -> float:
        """Score how many observations this theory explains."""
        # Count what it explicitly explains
        num_explains = len(explains)

        # Also count predictions and hidden variables as implicit explanations
        # A theory with predictions IS explaining what should be observed
        predictions = theory.get("predictions") or []
        hidden_vars = theory.get("hidden_variables") or []
        mechanisms = theory.get("steps") or theory.get("causal_chain") or []
        implicit_explains = len(predictions) + len(hidden_vars) + len(mechanisms)

        # Bonus for explaining gaps and anomalies
        gap_bonus = min(20, len(gaps) * 4) if gaps else 0
        anomaly_bonus = min(25, len(anomalies) * 5) if anomalies else 0

        # Penalty for failures to explain — reduced
        fail_penalty = len(fails) * 3

        # Combine explicit + implicit explanations
        total_explains = num_explains + min(implicit_explains, 5)  # cap implicit at 5

        base = 40 + total_explains * 6 + gap_bonus + anomaly_bonus - fail_penalty
        return max(15.0, min(100.0, base))

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
        """Score evidence strength — quality-weighted, includes predictions."""
        # Use competition scores if available
        if "evidence_support" in theory_scores:
            return theory_scores["evidence_support"] * 100

        base = 25

        # Quality-weighted paper scoring
        if papers:
            paper_quality = self._score_literature_quality(papers)
            base += min(35, paper_quality * 35)

        # Graph evidence — density and connectivity
        if graph:
            entities = graph.entities if hasattr(graph, 'entities') else {}
            relationships = graph.relationships if hasattr(graph, 'relationships') else {}
            if entities:
                density = len(relationships) / max(1, len(entities))
                base += min(15, density * 8)
                # Bonus for well-connected theory entities
                theory_name = theory.get("name", "").lower()
                for eid, ent in entities.items():
                    if theory_name and theory_name[:20] in ent.get("name", "").lower():
                        paper_count = len(ent.get("papers", []))
                        base += min(5, paper_count * 2)
                        break

        # Prediction quality — more predictions with numbers = stronger evidence
        predictions = theory.get("predictions") or []
        quant_preds = sum(1 for p in predictions
                          if isinstance(p, dict) and any(c.isdigit() for c in str(p.get("statement", ""))))
        base += min(15, quant_preds * 5)

        # Mechanism steps
        steps = theory.get("steps") or theory.get("causal_chain") or []
        base += min(10, len(steps) * 2)

        # Hidden variables with evidence
        hvs = theory.get("hidden_variables") or []
        base += min(5, len(hvs) * 2)

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
        """Score mathematical rigor — domain-aware, uses math engine when available.

        Some domains are inherently mathematical (physics, materials science).
        Others are more observational/theoretical (ecology, neuroscience).
        Purely theoretical discoveries shouldn't be penalized for lacking equations.
        """
        # Use math engine score if available (from Phase 9 verification)
        math_engine_score = theory.get("math_engine_score", 0)
        if math_engine_score > 0:
            return min(100.0, max(10.0, float(math_engine_score)))

        desc = theory.get("description", theory.get("mechanism", ""))
        math_model = theory.get("mathematical_model", "")
        theory_type = theory.get("type", "")

        # Theoretical discoveries get a baseline — not penalized for lacking equations
        if theory_type in ("theoretical", "conceptual", "framework", "hypothesis"):
            base = 50  # theoretical work is valid without equations
        else:
            base = 30  # empirical/mechanistic work should have some math

        # Check for equations/formulas
        has_equation = any(kw in desc.lower() for kw in [
            "equation", "formula", "=", "derivation", "rate constant",
            "threshold", "concentration", "flux", "amplitude", "cross-section",
            "sigma", "alpha", "beta", "gamma", "lambda", "omega",
        ]) or bool(math_model)

        # Check for quantitative content (numbers with units)
        import re
        quantitative_matches = re.findall(r'\d+\.?\d*\s*[×x]?\s*10[\^⁰-⁹-]+\s*\w+|\d+\.?\d*\s*(?:eV|GeV|MeV|nm|Å|K|Mpc|km/s|cm|g|kg|mol|M|nM|μM)', desc)
        has_quantitative = len(quantitative_matches) > 0 or any(c.isdigit() for c in desc)

        # Check for derivation
        has_derivation = any(kw in desc.lower() for kw in [
            "derived from", "follows from", "based on", "framework",
            "by definition", "substituting", "solving for", "integrating"
        ])

        # Check for assumptions stated
        has_assumptions = any(kw in desc.lower() for kw in [
            "assuming", "assumption", "given that", "under condition",
            "in the limit", "approximation", "perturbative"
        ])

        # Check for key parameters with values
        params = theory.get("key_parameters") or []
        has_params = isinstance(params, (list, dict)) and len(params) > 0

        if has_equation:
            base += 25
        if has_quantitative:
            base += 15
        if has_derivation:
            base += 15
        if has_assumptions:
            base += 5
        if has_params:
            base += 10
        if math_model:
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
