"""
peer_reviewer.py — Automated Scientific Peer Review

Evaluates research papers and experimental findings against quality criteria.
Inspired by AI Scientist's automated reviewer and academic peer review standards.

Evaluation Dimensions:
  [PR-1] Novelty — Is the work original? Does it advance the field?
  [PR-2] Soundness — Are the methods correct? Are claims supported by evidence?
  [PR-3] Clarity — Is the paper well-written and clearly presented?
  [PR-4] Reproducibility — Are experiments described in sufficient detail?
  [PR-5] Significance — How important are the findings?

Each dimension scored 1-5 (1=weak, 5=outstanding).
Overall recommendation: accept, weak accept, borderline, weak reject, reject.

Thread-safe. Stateless.
"""

import json
import math
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()


class PeerReviewer:
    """
    Automated peer review system for scientific papers and findings.
    Uses heuristic analysis of content quality, structure, and completeness.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._review_count = 0

    def review_paper(
        self,
        title: str,
        abstract: str,
        hypothesis: str,
        methodology: str,
        results: dict,
        conclusions: str,
        experiment_logs: Optional[dict] = None,
    ) -> dict:
        """
        Perform a comprehensive peer review of a paper / research finding.

        Args:
            title: Paper title
            abstract: Paper abstract
            hypothesis: Research hypothesis
            methodology: Methodology description
            results: Experimental results dict
            conclusions: Conclusion text
            experiment_logs: Optional experiment execution logs for reproducibility check

        Returns:
            Dict with scores, comments, and recommendation
        """
        with self._lock:
            self._review_count += 1

            # Score each dimension
            novelty = self._score_novelty(title, abstract, hypothesis)
            soundness = self._score_soundness(methodology, results)
            clarity = self._score_clarity(title, abstract, conclusions)
            reproducibility = self._score_reproducibility(methodology, experiment_logs)
            significance = self._score_significance(results, conclusions)

            # Overall score (weighted average)
            weights = {
                "novelty": 0.25,
                "soundness": 0.25,
                "clarity": 0.15,
                "reproducibility": 0.15,
                "significance": 0.20,
            }

            overall = (
                novelty * weights["novelty"]
                + soundness * weights["soundness"]
                + clarity * weights["clarity"]
                + reproducibility * weights["reproducibility"]
                + significance * weights["significance"]
            )

            # Recommendation
            recommendation = self._get_recommendation(overall)

            # Detailed comments
            comments = self._generate_comments(
                novelty, soundness, clarity, reproducibility, significance,
                title, hypothesis, results,
            )

            # Strengths and weaknesses
            strengths, weaknesses = self._identify_strengths_weaknesses(
                novelty, soundness, clarity, reproducibility, significance,
                title, abstract, methodology, results,
            )

            return {
                "review_id": f"REV-{int(time.time() * 1000)}",
                "title": title,
                "scores": {
                    "novelty": round(novelty, 1),
                    "soundness": round(soundness, 1),
                    "clarity": round(clarity, 1),
                    "reproducibility": round(reproducibility, 1),
                    "significance": round(significance, 1),
                    "overall": round(overall, 2),
                },
                "recommendation": recommendation,
                "comments": comments,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "reviewed_at": datetime.now().isoformat(),
            }

    def _score_novelty(self, title: str, abstract: str, hypothesis: str) -> float:
        """Score novelty (1-5)."""
        text = f"{title} {abstract} {hypothesis}".lower()
        score = 3.0  # baseline

        # Novelty indicators
        novel_indicators = [
            "novel", "new", "first", "introduce", "propose", "novel approach",
            "unprecedented", "breakthrough", "innovative", "original",
            "state-of-the-art", "beyond", "challenges", "redefines",
        ]
        for word in novel_indicators:
            if word in text:
                score += 0.3

        # Extends existing work
        extension_indicators = [
            "extends", "builds upon", "improves", "enhances", "generalizes",
            "extends previous", "based on", "inspired by",
        ]
        for phrase in extension_indicators:
            if phrase in text:
                score += 0.1

        # Incremental indicators
        incremental = [
            "incremental", "minor", "small improvement", "also applies",
            "similar to", "same as",
        ]
        for phrase in incremental:
            if phrase in text:
                score -= 0.5

        # Lack of novelty indicators
        if any(w in text for w in ["preliminary", "early stage", "work in progress"]):
            score -= 0.5

        return max(1.0, min(5.0, score))

    def _score_soundness(self, methodology: str, results: dict) -> float:
        """Score methodological soundness (1-5)."""
        score = 3.0
        text = methodology.lower()

        # Strong methodology indicators
        strong_indicators = [
            "cross-validation", "k-fold", "bootstrap", "statistical test",
            "hypothesis test", "effect size", "confidence interval",
            "control group", "randomized", "blinded", "replication",
            "power analysis", "significance level", "multiple comparisons",
            "ablation", "sensitivity analysis", "robustness check",
        ]
        for word in strong_indicators:
            if word in text:
                score += 0.2

        # Results with multiple metrics strengthen soundness
        if results:
            numeric_count = sum(1 for v in results.values() if isinstance(v, (int, float)))
            if numeric_count >= 3:
                score += 0.3
            if numeric_count >= 5:
                score += 0.3

        # Weakness indicators
        weak_indicators = [
            "no evaluation", "not tested", "preliminary", "untested",
            "no baseline", "no comparison", "anecdotal",
        ]
        for word in weak_indicators:
            if word in text:
                score -= 0.5

        if any(w in text for w in ["small sample", "limited data", "n=1", "single run"]):
            score -= 0.3

        # Check for statistical rigor
        if any(w in text for w in ["p-value", "p <", "p =", "p >"]):
            score += 0.4
        if "effect size" in text:
            score += 0.3

        return max(1.0, min(5.0, score))

    def _score_clarity(self, title: str, abstract: str, conclusions: str) -> float:
        """Score clarity and writing quality (1-5)."""
        score = 3.0

        # Title quality
        if 10 <= len(title) <= 100:
            score += 0.2
        if "?" not in title and "!" not in title:
            score += 0.1

        # Abstract structure
        abstract_lower = abstract.lower()
        if any(w in abstract_lower for w in ["we show", "we find", "we demonstrate", "we present"]):
            score += 0.3
        if any(w in abstract_lower for w in ["however", "although", "despite", "while"]):
            score += 0.2
        if len(abstract) > 100:
            score += 0.2

        # Conclusions quality
        conclusions_lower = conclusions.lower()
        if len(conclusions) > 100:
            score += 0.2
        if any(w in conclusions_lower for w in ["future work", "limitation", "further research"]):
            score += 0.3
        if any(w in conclusions_lower for w in ["we show", "we demonstrate", "our results"]):
            score += 0.2

        # Penalize very short or missing sections
        if len(abstract) < 50:
            score -= 0.5
        if len(conclusions) < 50:
            score -= 0.3

        return max(1.0, min(5.0, score))

    def _score_reproducibility(self, methodology: str, experiment_logs: Optional[dict]) -> float:
        """Score reproducibility (1-5)."""
        score = 3.0
        text = methodology.lower()

        # Reproducibility indicators
        repro_indicators = [
            "code available", "open source", "github", "repository",
            "random seed", "seed=", "reproducibility", "docker",
            "hyperparameters", "configuration", "parameters",
            "training details", "implementation details",
            "dataset available", "public dataset", "benchmark",
            "environment", "requirements", "dependencies",
        ]
        for word in repro_indicators:
            if word in text:
                score += 0.25

        # Standard metrics make reproduction easier
        standard_metrics = [
            "accuracy", "f1", "precision", "recall", "mse", "rmse",
            "auc", "perplexity", "bleu",
        ]
        for metric in standard_metrics:
            if metric in text:
                score += 0.15

        # Experiment logs available boosts reproducibility
        if experiment_logs:
            score += 0.5
            if experiment_logs.get("status") == "completed":
                score += 0.3
            if experiment_logs.get("results"):
                score += 0.2

        return max(1.0, min(5.0, score))

    def _score_significance(self, results: dict, conclusions: str) -> float:
        """Score significance of findings (1-5)."""
        score = 3.0

        if not results:
            return 2.0

        # High performance indicates significance
        for key, value in results.items():
            if isinstance(value, (int, float)):
                if key in ("accuracy", "f1_score", "precision", "recall", "r2"):
                    if value > 0.9:
                        score += 0.5
                    elif value > 0.8:
                        score += 0.3
                    elif value < 0.3:
                        score -= 0.3

        # Statistical significance
        conclusions_lower = conclusions.lower()
        if "significant" in conclusions_lower:
            score += 0.3
        if "practical" in conclusions_lower or "real-world" in conclusions_lower:
            score += 0.3
        if "limitation" in conclusions_lower or "future work" in conclusions_lower:
            score += 0.2

        # Effect size
        if results.get("cohens_d"):
            d = results["cohens_d"]
            if d > 0.8:
                score += 0.5
            elif d > 0.5:
                score += 0.3

        # Number of experiments/metrics
        numeric_count = sum(1 for v in results.values() if isinstance(v, (int, float)))
        if numeric_count >= 3:
            score += 0.2

        return max(1.0, min(5.0, score))

    def _get_recommendation(self, overall: float) -> str:
        """Convert overall score to recommendation."""
        if overall >= 4.0:
            return "accept"
        elif overall >= 3.5:
            return "weak_accept"
        elif overall >= 2.5:
            return "borderline"
        elif overall >= 1.5:
            return "weak_reject"
        else:
            return "reject"

    def _generate_comments(
        self, novelty: float, soundness: float, clarity: float,
        reproducibility: float, significance: float,
        title: str, hypothesis: str, results: dict,
    ) -> str:
        """Generate reviewer comments based on scores."""
        comments = []

        if novelty >= 4:
            comments.append("The work presents a novel approach that advances the field.")
        elif novelty <= 2:
            comments.append("The novelty is limited; the work appears incremental.")

        if soundness >= 4:
            comments.append("The methodology is rigorous and well-justified.")
        elif soundness <= 2:
            comments.append("The methodology needs strengthening — consider adding more rigorous evaluation.")

        if clarity >= 4:
            comments.append("The paper is clearly written and well-structured.")
        elif clarity <= 2:
            comments.append("Clarity could be improved — consider restructuring and adding more detail.")

        if reproducibility >= 4:
            comments.append("Experimental details are sufficient for reproduction.")
        elif reproducibility <= 2:
            comments.append("Reproducibility is a concern — please provide more implementation details.")

        if significance >= 4:
            comments.append("The findings have significant implications for the field.")
        elif significance <= 2:
            comments.append("The significance of the findings is limited in its current form.")

        # Result-specific comments
        if results:
            if results.get("accuracy", 0) > 0.9:
                comments.append("The reported accuracy is impressively high.")
            elif results.get("accuracy", 0) < 0.5 and "accuracy" in results:
                comments.append("The reported accuracy is relatively low — discuss potential reasons.")

        if not comments:
            comments.append("The paper presents solid work with room for improvement in several areas.")

        return " ".join(comments)

    def _identify_strengths_weaknesses(
        self, novelty: float, soundness: float, clarity: float,
        reproducibility: float, significance: float,
        title: str, abstract: str, methodology: str, results: dict,
    ) -> tuple[list[str], list[str]]:
        """Identify specific strengths and weaknesses."""
        strengths = []
        weaknesses = []

        # Strengths
        if novelty >= 3.5:
            strengths.append("Novel approach or application")
        if soundness >= 3.5:
            strengths.append("Rigorous methodology")
        if clarity >= 3.5:
            strengths.append("Well-written and clearly presented")
        if reproducibility >= 3.5:
            strengths.append("Good experimental details for reproducibility")
        if significance >= 3.5:
            strengths.append("Significant findings with practical implications")

        if results:
            for key, value in results.items():
                if isinstance(value, float) and value > 0.85:
                    strengths.append(f"Strong results ({key}: {value:.1%})")

        # Weaknesses
        if novelty < 2.5:
            weaknesses.append("Limited novelty — work is incremental")
        if soundness < 2.5:
            weaknesses.append("Methodological concerns — consider additional validation")
        if clarity < 2.5:
            weaknesses.append("Clarity issues — paper needs restructuring")
        if reproducibility < 2.5:
            weaknesses.append("Insufficient detail for reproduction")
        if significance < 2.5:
            weaknesses.append("Limited significance of findings")

        if not results:
            weaknesses.append("No quantitative experimental results reported")

        if not strengths:
            strengths.append("The work addresses a relevant topic")

        return strengths, weaknesses

    def review_findings(
        self,
        findings: list[str],
        methodology: str = "",
        confidence: float = 0.5,
    ) -> dict:
        """
        Review a set of research findings (lighter review).
        Useful for quick quality assessment of hypotheses or claims.
        """
        score = 3.0

        # Number of findings
        if len(findings) >= 5:
            score += 0.5
        elif len(findings) >= 3:
            score += 0.2

        # Confidence adjustment
        score += (confidence - 0.5) * 2

        # Methodology quality
        if methodology:
            method_lower = methodology.lower()
            if any(w in method_lower for w in ["experiment", "analysis", "study", "evaluation"]):
                score += 0.3
            if any(w in method_lower for w in ["statistical", "quantitative", "measurement"]):
                score += 0.3

        score = max(1.0, min(5.0, score))

        return {
            "review_id": f"REV-{int(time.time() * 1000)}",
            "findings_count": len(findings),
            "quality_score": round(score, 1),
            "recommendation": self._get_recommendation(score),
            "comment": (
                f"This set of findings has been evaluated. "
                f"Quality score: {score:.1f}/5.0. "
                f"{'Strong set of findings.' if score >= 3.5 else 'Findings have room for improvement.'}"
            ),
            "reviewed_at": datetime.now().isoformat(),
        }

    def get_stats(self) -> dict:
        """Get peer reviewer statistics."""
        with self._lock:
            return {
                "total_reviews": self._review_count,
                "status": "ready",
            }


# ── Singleton ──────────────────────────────────────────────────

_peer_reviewer = None
_reviewer_lock = threading.Lock()


def get_peer_reviewer() -> PeerReviewer:
    global _peer_reviewer
    if _peer_reviewer is None:
        with _reviewer_lock:
            if _peer_reviewer is None:
                _peer_reviewer = PeerReviewer()
    return _peer_reviewer
