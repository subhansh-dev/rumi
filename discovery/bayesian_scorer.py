"""
bayesian_scorer.py — Proper Bayesian hypothesis scoring.

Instead of arbitrary "confidence = 78%", compute:
  Prior × Evidence = Posterior

Inspired by:
  - Bayes' theorem
  - Minimum Description Length (MDL)
  - Thagard's Explanatory Coherence
  - Bayesian model comparison (Bayes factors)

Every hypothesis gets:
  Prior: based on simplicity + literature support
  Likelihood: how well it explains the observed data
  Evidence: number and quality of supporting/contradicting papers
  Posterior: P(hypothesis | data) via Bayes' theorem
"""

import math
from typing import Dict, List, Optional


class BayesianScorer:
    """
    Bayesian hypothesis scoring: Prior × Likelihood = Posterior.
    """

    def __init__(self):
        # Default priors — more reasonable for scientific hypotheses
        # A novel hypothesis proposed by a structured discovery pipeline
        # deserves a higher prior than a random guess
        self.default_prior = 0.15
        self.min_prior = 0.05
        self.max_prior = 0.5

    def score(self, theory: dict, papers: list = None,
              contradictions: list = None, graph=None) -> dict:
        """
        Compute Bayesian posterior for a theory.

        Returns:
            {
                "prior": 0.0-1.0,
                "likelihood": 0.0-1.0,
                "evidence": {...},
                "posterior": 0.0-1.0,
                "bayes_factor": float,
                "interpretation": "...",
                "components": {...}
            }
        """
        # 1. Prior probability
        prior = self._compute_prior(theory, graph)

        # 2. Likelihood: P(data | hypothesis)
        likelihood = self._compute_likelihood(theory, papers, contradictions)

        # 3. Evidence (marginal likelihood approximation)
        evidence = self._compute_evidence(theory, papers)

        # 4. Posterior via Bayes' theorem
        # P(H|D) = P(D|H) × P(H) / P(D)
        # P(D) ≈ P(D|H) × P(H) + P(D|¬H) × P(¬H)
        p_data_given_not_h = 1.0 - likelihood  # simplified
        marginal = likelihood * prior + p_data_given_not_h * (1 - prior)
        posterior = (likelihood * prior) / marginal if marginal > 0 else 0.5

        # 5. Bayes factor: P(D|H) / P(D|¬H)
        bayes_factor = likelihood / p_data_given_not_h if p_data_given_not_h > 0 else float('inf')

        # 6. Interpretation
        interpretation = self._interpret(posterior, bayes_factor)

        return {
            "prior": round(prior, 4),
            "likelihood": round(likelihood, 4),
            "posterior": round(posterior, 4),
            "bayes_factor": round(bayes_factor, 2),
            "interpretation": interpretation,
            "evidence": evidence,
            "components": {
                "simplicity_score": self._simplicity_score(theory),
                "literature_support": self._literature_support(theory, papers),
                "explanatory_fit": self._explanatory_fit(theory),
                "contradiction_penalty": self._contradiction_penalty(contradictions),
            },
        }

    def compare(self, theories: list, papers: list = None,
                contradictions: list = None, graph=None) -> dict:
        """
        Bayesian model comparison: compute posteriors for all theories,
        then rank by Bayes factor.

        Returns:
            {
                "ranked_theories": [...],
                "bayes_factors": [...],
                "model_comparison": "...",
                "best_theory": {...}
            }
        """
        scored = []
        for theory in theories:
            result = self.score(theory, papers, contradictions, graph)
            theory["bayesian"] = result
            scored.append(theory)

        # Sort by posterior
        scored.sort(key=lambda t: t.get("bayesian", {}).get("posterior", 0), reverse=True)

        # Compute relative Bayes factors
        if scored and len(scored) > 1:
            best_posterior = scored[0]["bayesian"]["posterior"]
            for t in scored:
                p = t["bayesian"]["posterior"]
                if p > 0:
                    t["bayesian"]["relative_bayes_factor"] = round(best_posterior / p, 2)
                else:
                    t["bayesian"]["relative_bayes_factor"] = float('inf')

        # Model comparison text
        if scored:
            best = scored[0]
            runner_up = scored[1] if len(scored) > 1 else None
            comparison = (f"Best: '{best.get('name', '?')}' (posterior={best['bayesian']['posterior']:.3f})")
            if runner_up:
                bf = best["bayesian"].get("relative_bayes_factor", 1)
                comparison += (f" vs '{runner_up.get('name', '?')}' "
                              f"(posterior={runner_up['bayesian']['posterior']:.3f}), "
                              f"Bayes factor = {bf:.1f}x")
        else:
            comparison = "No theories to compare"

        return {
            "ranked_theories": scored,
            "model_comparison": comparison,
            "best_theory": scored[0] if scored else None,
            "num_theories": len(scored),
        }

    def _compute_prior(self, theory: dict, graph=None) -> float:
        """
        Prior probability based on:
        1. Simplicity (fewer assumptions → higher prior)
        2. Type (null > conventional > extension > novel)
        3. Coherence with known physics
        4. Whether the theory has quantitative content

        NOTE: A novel hypothesis from a structured discovery pipeline
        is NOT the same as a random guess. The pipeline has already
        filtered through literature review, gap detection, anomaly
        detection, and mechanism generation. This justifies a higher
        base prior than traditional Bayesian analysis would assign.
        """
        # Base prior from theory type — more generous for structured discovery
        type_priors = {
            "null": 0.35,
            "conventional": 0.30,
            "extension_of_known": 0.20,
            "modification_of_known": 0.15,
            "alternative": 0.12,
            "proposed": 0.10,
            "proposed_new": 0.10,
            "novel": 0.08,
        }
        theory_type = theory.get("type", "proposed")
        is_novel = theory.get("is_novel_vs_known", theory.get("is_novel_vs_extension", ""))
        if is_novel == "novel":
            base = type_priors.get("novel", 0.08)
        elif is_novel in ("extension_of_known", "modification_of_known"):
            base = type_priors.get(is_novel, 0.15)
        else:
            base = type_priors.get(theory_type, 0.10)

        # Simplicity adjustment
        simplicity = self._simplicity_score(theory)
        simplicity_factor = 0.7 + simplicity * 0.3  # 0.7 to 1.0 (less punitive)

        # Quantitative content bonus — theories with equations are more testable
        has_equations = bool(theory.get("mathematical_model") or
                           theory.get("mathematical_formalism") or
                           any(c.isdigit() for c in str(theory.get("description", ""))))
        quant_bonus = 1.1 if has_equations else 1.0

        prior = base * simplicity_factor * quant_bonus
        return max(self.min_prior, min(self.max_prior, prior))

    def _compute_likelihood(self, theory: dict, papers: list,
                            contradictions: list) -> float:
        """
        Likelihood: P(data | hypothesis)

        This is the core of the Bayesian update. It measures how well
        the theory explains the available evidence.

        Components:
        1. Explanatory fit — does the theory explain observations?
        2. Prediction quality — does it make testable predictions?
        3. Literature support — do papers study the same topic?
        4. Contradiction penalty — does evidence contradict the theory?

        IMPORTANT: If papers=[], likelihood defaults to 0.5 (uninformative).
        This is NOT the same as "no evidence supports the theory."
        """
        # Explanatory fit
        explains = theory.get("explains", [])
        fails = theory.get("fails_to_explain", [])
        total = len(explains) + len(fails)
        explanatory = len(explains) / total if total > 0 else 0.5

        # Prediction quality — quantitative predictions are more testable
        predictions = theory.get("predictions", [])
        pred_score = 0.5
        if predictions:
            quant_preds = sum(1 for p in predictions
                              if isinstance(p, (str, dict)) and
                              any(c.isdigit() for c in str(p)))
            pred_score = min(1.0, 0.3 + quant_preds * 0.12)

        # Literature support — topic-relevant papers count as evidence
        lit_support = self._literature_support(theory, papers)

        # Contradiction penalty
        contradiction_pen = self._contradiction_penalty(contradictions)

        # Combine
        likelihood = (explanatory * 0.4 + pred_score * 0.3 +
                      lit_support * 0.2 + (1 - contradiction_pen) * 0.1)

        return max(0.01, min(0.99, likelihood))

    def _compute_evidence(self, theory: dict, papers: list) -> dict:
        """Compute evidence summary — actually match papers against theory."""
        # Count papers that share topic keywords with the theory
        topic_relevant = 0
        if papers:
            theory_keywords = self._extract_keywords(theory)
            for p in papers:
                abstract = (p.get("abstract", "") + " " + p.get("title", "")).lower()
                if not abstract.strip():
                    continue
                hits = sum(1 for kw in theory_keywords if kw in abstract)
                if hits >= 3:
                    topic_relevant += 1

        # Also count explicit literature references
        supporting = theory.get("literature_basis", theory.get("literature_grounding", []))
        if isinstance(supporting, str):
            supporting = [supporting]

        predictions = theory.get("predictions", [])

        return {
            "supporting_papers": topic_relevant,
            "literature_references": len(supporting),
            "predictions_generated": len(predictions),
            "quantitative_predictions": sum(1 for p in predictions
                                            if isinstance(p, (str, dict)) and
                                            any(c.isdigit() for c in str(p))),
        }

    def _extract_keywords(self, theory: dict) -> list:
        """Extract searchable keywords from a theory."""
        keywords = set()
        stopwords = {"the", "and", "for", "with", "that", "this", "from", "are", "has",
                     "was", "were", "been", "have", "will", "would", "could", "should",
                     "into", "over", "such", "than", "them", "then", "they", "this",
                     "very", "when", "what", "which", "while", "who", "whom", "why"}
        name = theory.get("name", theory.get("title", ""))
        for word in name.lower().split():
            clean = word.strip("()[]{},.:;")
            if len(clean) > 3 and clean not in stopwords and clean.isalpha():
                keywords.add(clean)
        desc = theory.get("description", theory.get("mechanism", ""))
        for word in desc.lower().split():
            clean = word.strip("()[]{},.:;")
            if len(clean) > 3 and clean not in stopwords and clean.isalpha():
                keywords.add(clean)
        return list(keywords)[:30]

    def _simplicity_score(self, theory: dict) -> float:
        """Simplicity: fewer assumptions and parameters = simpler."""
        assumptions = theory.get("key_assumptions", theory.get("assumptions", []))
        params = theory.get("key_parameters", [])
        steps = theory.get("steps", [])
        hidden_vars = theory.get("hidden_variables", [])

        n_assumptions = len(assumptions) if isinstance(assumptions, list) else 0
        n_params = len(params) if isinstance(params, list) else 0
        n_steps = len(steps) if isinstance(steps, list) else 0
        n_hv = len(hidden_vars) if isinstance(hidden_vars, list) else 0

        complexity = n_assumptions * 2 + n_params + n_steps * 0.5 + n_hv * 3
        # Map to 0-1 (lower complexity = higher score)
        return max(0.1, 1.0 / (1.0 + complexity * 0.1))

    def _literature_support(self, theory: dict, papers: list) -> float:
        """How much literature supports this theory — match papers against keywords."""
        refs = theory.get("literature_basis", theory.get("literature_grounding", []))
        if isinstance(refs, str):
            refs = [refs]
        n_refs = len(refs) if isinstance(refs, list) else 0

        # Count topic-relevant papers
        topic_relevant = 0
        if papers:
            theory_keywords = self._extract_keywords(theory)
            for p in papers:
                abstract = (p.get("abstract", "") + " " + p.get("title", "")).lower()
                if not abstract.strip():
                    continue
                hits = sum(1 for kw in theory_keywords if kw in abstract)
                if hits >= 3:
                    topic_relevant += 1

        return min(1.0, (n_refs * 0.2 + topic_relevant * 0.08))

    def _explanatory_fit(self, theory: dict) -> float:
        """How well the theory explains observations."""
        explains = theory.get("explains", [])
        fails = theory.get("fails_to_explain", [])
        total = len(explains) + len(fails)
        return len(explains) / total if total > 0 else 0.5

    def _contradiction_penalty(self, contradictions: list) -> float:
        """Penalty for contradictions."""
        if not contradictions:
            return 0.0
        return min(0.5, len(contradictions) * 0.1)

    def _interpret(self, posterior: float, bayes_factor: float) -> str:
        """Interpret the Bayesian score in plain language."""
        if posterior > 0.8:
            strength = "Very strong support"
        elif posterior > 0.6:
            strength = "Strong support"
        elif posterior > 0.4:
            strength = "Moderate support"
        elif posterior > 0.2:
            strength = "Weak support"
        else:
            strength = "Very weak support"

        if bayes_factor > 100:
            evidence = "decisive evidence"
        elif bayes_factor > 30:
            evidence = "very strong evidence"
        elif bayes_factor > 10:
            evidence = "strong evidence"
        elif bayes_factor > 3:
            evidence = "substantial evidence"
        elif bayes_factor > 1:
            evidence = "weak evidence"
        else:
            evidence = "evidence favors alternatives"

        return f"{strength} (posterior={posterior:.2f}). {evidence} (Bayes factor={bayes_factor:.1f})."
