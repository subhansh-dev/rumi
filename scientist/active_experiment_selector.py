"""
active_experiment_selector.py — Bayesian Optimal Experiment Selection

Selects the most informative experiments to run next, using Bayesian
active learning principles. Maximizes information gain per experiment.

Inspired by:
  - Bayesian optimal experimental design
  - GFlowNets' active learning for experiment selection
  - Sequential experiment design in drug discovery

Capabilities:
  [AE-1] Information gain estimation for candidate experiments
  [AE-2] Bayesian hypothesis ranking with uncertainty
  [AE-3] Optimal experiment selection (maximize expected information gain)
  [AE-4] Batch experiment design (parallel informative experiments)
  [AE-5] Adaptive stopping (know when enough experiments have been run)
  [AE-6] Cost-aware experiment selection
  [AE-7] Experiment history tracking and learning
  [AE-8] Surprise detection (flag unexpected results)

Thread-safe. Persistent state in experiment_selector_state.json.
"""

import json
import math
import random
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()
STATE_FILE = SCIENTIST_DIR / "experiment_selector_state.json"


class Hypothesis:
    """A hypothesis with Bayesian posterior."""

    def __init__(self, title: str, description: str = ""):
        self.id = f"H-{int(time.time() * 1000)}-{random.randint(100, 999)}"
        self.title = title
        self.description = description
        # Beta distribution parameters for posterior
        self.alpha = 1.0  # pseudo-successes
        self.beta = 1.0   # pseudo-failures
        self.created_at = datetime.now().isoformat()

    @property
    def mean(self) -> float:
        """Posterior mean probability."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        """Posterior variance."""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))

    @property
    def uncertainty(self) -> float:
        """Posterior uncertainty (entropy-based)."""
        p = self.mean
        if p <= 0 or p >= 1:
            return 0.0
        return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))

    def update(self, success: bool, weight: float = 1.0):
        """Update posterior with new evidence."""
        if success:
            self.alpha += weight
        else:
            self.beta += weight

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "alpha": round(self.alpha, 4),
            "beta": round(self.beta, 4),
            "mean": round(self.mean, 4),
            "variance": round(self.variance, 6),
            "uncertainty": round(self.uncertainty, 4),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Hypothesis":
        h = cls(d["title"], d.get("description", ""))
        h.id = d["id"]
        h.alpha = d.get("alpha", 1.0)
        h.beta = d.get("beta", 1.0)
        h.created_at = d.get("created_at", h.created_at)
        return h


class CandidateExperiment:
    """A candidate experiment that could be run."""

    def __init__(
        self,
        name: str,
        description: str,
        hypotheses_tested: list[str],
        cost: float = 1.0,
        duration_estimate_s: float = 60.0,
    ):
        self.id = f"EXP-{int(time.time() * 1000)}-{random.randint(100, 999)}"
        self.name = name
        self.description = description
        self.hypotheses_tested = hypotheses_tested  # hypothesis IDs
        self.cost = cost  # relative cost (1.0 = baseline)
        self.duration_estimate_s = duration_estimate_s
        # Computed scores
        self.expected_information_gain: float = 0.0
        self.expected_surprise: float = 0.0
        self.utility_score: float = 0.0  # information_gain / cost

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "hypotheses_tested": self.hypotheses_tested,
            "cost": self.cost,
            "duration_estimate_s": self.duration_estimate_s,
            "expected_information_gain": round(self.expected_information_gain, 4),
            "expected_surprise": round(self.expected_surprise, 4),
            "utility_score": round(self.utility_score, 4),
        }


class ExperimentResult:
    """Result of running an experiment."""

    def __init__(self, experiment_id: str):
        self.experiment_id = experiment_id
        self.success: bool = False
        self.metrics: dict = {}
        self.observations: str = ""
        self.surprise_score: float = 0.0
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "success": self.success,
            "metrics": self.metrics,
            "observations": self.observations,
            "surprise_score": round(self.surprise_score, 4),
            "timestamp": self.timestamp,
        }


class ActiveExperimentSelector:
    """
    Bayesian optimal experiment selection engine.

    Selects experiments that maximize expected information gain about
    the hypotheses under investigation, accounting for cost.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._hypotheses: dict[str, Hypothesis] = {}
        self._experiments: list[CandidateExperiment] = []
        self._history: list[dict] = []  # experiment results
        self._round = 0
        self._load_state()

    def _load_state(self):
        with self._lock:
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    self._round = data.get("round", 0)
                    for h in data.get("hypotheses", []):
                        hyp = Hypothesis.from_dict(h)
                        self._hypotheses[hyp.id] = hyp
                    self._history = data.get("history", [])
                except Exception:
                    pass

    def _save_state(self):
        with self._lock:
            data = {
                "round": self._round,
                "hypotheses": [h.to_dict() for h in self._hypotheses.values()],
                "history": self._history,
                "saved_at": datetime.now().isoformat(),
            }
            STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ── Hypothesis Management ─────────────────────────────────────────────────

    def add_hypothesis(self, title: str, description: str = "") -> Hypothesis:
        """Add a hypothesis to track."""
        with self._lock:
            h = Hypothesis(title, description)
            self._hypotheses[h.id] = h
            return h

    def get_hypotheses(self) -> list[dict]:
        """Get all hypotheses with current posteriors."""
        with self._lock:
            return [h.to_dict() for h in self._hypotheses.values()]

    def rank_hypotheses(self) -> list[dict]:
        """Rank hypotheses by posterior mean, with uncertainty."""
        with self._lock:
            ranked = sorted(
                self._hypotheses.values(),
                key=lambda h: h.mean,
                reverse=True,
            )
            return [
                {
                    **h.to_dict(),
                    "rank": i + 1,
                    "credible_interval": [
                        round(max(0, h.mean - 1.96 * math.sqrt(h.variance)), 3),
                        round(min(1, h.mean + 1.96 * math.sqrt(h.variance)), 3),
                    ],
                }
                for i, h in enumerate(ranked)
            ]

    # ── Information Gain Computation ──────────────────────────────────────────

    def compute_information_gain(
        self, experiment: CandidateExperiment
    ) -> float:
        """
        Compute expected information gain of running this experiment.

        Uses entropy reduction: H(posterior) - E[H(posterior | result)]
        """
        total_gain = 0.0

        for hyp_id in experiment.hypotheses_tested:
            hyp = self._hypotheses.get(hyp_id)
            if not hyp:
                continue

            # Current entropy
            H_prior = hyp.uncertainty

            # Expected posterior entropy after experiment
            # P(success) * H(posterior | success) + P(failure) * H(posterior | failure)
            p_success = hyp.mean

            # Simulate success update
            alpha_s = hyp.alpha + 1.0
            beta_s = hyp.beta
            p_post_s = alpha_s / (alpha_s + beta_s)
            H_post_s = self._entropy(p_post_s)

            # Simulate failure update
            alpha_f = hyp.alpha
            beta_f = hyp.beta + 1.0
            p_post_f = alpha_f / (alpha_f + beta_f)
            H_post_f = self._entropy(p_post_f)

            # Expected posterior entropy
            E_H_post = p_success * H_post_s + (1 - p_success) * H_post_f

            # Information gain = reduction in entropy
            gain = H_prior - E_H_post
            total_gain += max(0, gain)

        return total_gain

    def _entropy(self, p: float) -> float:
        """Binary entropy."""
        if p <= 0 or p >= 1:
            return 0.0
        return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))

    def compute_surprise(self, experiment: CandidateExperiment, success: bool) -> float:
        """
        Compute how surprising an outcome would be.
        High surprise = outcome contradicts current beliefs.
        """
        max_surprise = 0.0
        for hyp_id in experiment.hypotheses_tested:
            hyp = self._hypotheses.get(hyp_id)
            if not hyp:
                continue
            p = hyp.mean
            if success:
                surprise = -math.log2(max(p, 0.001))
            else:
                surprise = -math.log2(max(1 - p, 0.001))
            max_surprise = max(max_surprise, surprise)
        return max_surprise

    # ── Experiment Selection ──────────────────────────────────────────────────

    def select_next(
        self,
        candidates: list[CandidateExperiment] | None = None,
        cost_weight: float = 0.3,
    ) -> CandidateExperiment | None:
        """
        Select the single most informative experiment to run next.

        Args:
            candidates: Experiment candidates. Uses stored if None.
            cost_weight: How much to penalize expensive experiments (0-1).
        """
        with self._lock:
            pool = candidates or self._experiments
            if not pool:
                return None

            best = None
            best_utility = -1.0

            for exp in pool:
                ig = self.compute_information_gain(exp)
                exp.expected_information_gain = ig
                # Utility = information gain / cost^weight
                cost_factor = exp.cost ** cost_weight
                exp.utility_score = ig / max(cost_factor, 0.01)
                if exp.utility_score > best_utility:
                    best_utility = exp.utility_score
                    best = exp

            return best

    def select_batch(
        self,
        candidates: list[CandidateExperiment] | None = None,
        batch_size: int = 3,
        cost_weight: float = 0.3,
        diversity_bonus: float = 0.2,
    ) -> list[CandidateExperiment]:
        """
        Select a batch of diverse, informative experiments.

        Uses greedy selection with diversity penalty to avoid redundancy.
        """
        with self._lock:
            pool = list(candidates or self._experiments)
            if not pool:
                return []

            selected: list[CandidateExperiment] = []
            selected_hyp_ids: set[str] = set()

            for _ in range(min(batch_size, len(pool))):
                best = None
                best_score = -1.0

                for exp in pool:
                    if exp in selected:
                        continue
                    ig = self.compute_information_gain(exp)

                    # Diversity bonus: reward testing new hypotheses
                    new_hyps = set(exp.hypotheses_tested) - selected_hyp_ids
                    diversity = len(new_hyps) / max(len(exp.hypotheses_tested), 1)

                    # Cost penalty
                    cost_factor = exp.cost ** cost_weight

                    score = (ig + diversity_bonus * diversity) / max(cost_factor, 0.01)

                    if score > best_score:
                        best_score = score
                        best = exp

                if best:
                    selected.append(best)
                    selected_hyp_ids.update(best.hypotheses_tested)

            return selected

    # ── Result Recording ──────────────────────────────────────────────────────

    def record_result(
        self,
        experiment: CandidateExperiment,
        success: bool,
        metrics: dict | None = None,
        observations: str = "",
        weight: float = 1.0,
    ) -> dict:
        """
        Record the result of an experiment and update hypothesis posteriors.
        """
        with self._lock:
            self._round += 1

            # Compute surprise
            surprise = self.compute_surprise(experiment, success)

            # Update hypotheses
            updated = []
            for hyp_id in experiment.hypotheses_tested:
                hyp = self._hypotheses.get(hyp_id)
                if hyp:
                    hyp.update(success, weight)
                    updated.append(hyp.title)

            # Record in history
            result = {
                "round": self._round,
                "experiment": experiment.name,
                "success": success,
                "surprise": round(surprise, 4),
                "hypotheses_updated": updated,
                "metrics": metrics or {},
                "observations": observations,
                "timestamp": datetime.now().isoformat(),
            }
            self._history.append(result)

            # Alert on high surprise
            if surprise > 3.0:
                result["alert"] = f"HIGH SURPRISE ({surprise:.1f} bits)! Result contradicts expectations."

            self._save_state()
            return result

    # ── Adaptive Stopping ─────────────────────────────────────────────────────

    def should_stop(self, confidence_threshold: float = 0.9, max_uncertainty: float = 0.2) -> dict:
        """
        Check if enough experiments have been run.
        Recommends stopping when hypotheses are confident enough.
        """
        with self._lock:
            if not self._hypotheses:
                return {"stop": False, "reason": "No hypotheses to test"}

            confident_count = 0
            total = len(self._hypotheses)

            for hyp in self._hypotheses.values():
                if hyp.mean > confidence_threshold or hyp.mean < (1 - confidence_threshold):
                    if hyp.uncertainty < max_uncertainty:
                        confident_count += 1

            ratio = confident_count / total if total > 0 else 0

            if ratio >= 0.8:
                return {
                    "stop": True,
                    "reason": f"{confident_count}/{total} hypotheses resolved with high confidence",
                    "rounds": self._round,
                }
            elif self._round > 20:
                return {
                    "stop": True,
                    "reason": f"Maximum rounds ({self._round}) reached",
                    "rounds": self._round,
                }
            else:
                return {
                    "stop": False,
                    "reason": f"{confident_count}/{total} hypotheses resolved (need {int(total * 0.8)})",
                    "rounds": self._round,
                }

    # ── API ───────────────────────────────────────────────────────────────────

    def add_candidate(self, experiment: CandidateExperiment):
        """Add a candidate experiment."""
        with self._lock:
            self._experiments.append(experiment)

    def get_history(self) -> list[dict]:
        with self._lock:
            return list(self._history)

    def get_summary(self) -> dict:
        with self._lock:
            return {
                "round": self._round,
                "hypothesis_count": len(self._hypotheses),
                "experiment_count": len(self._experiments),
                "history_length": len(self._history),
                "top_hypothesis": max(
                    (h.to_dict() for h in self._hypotheses.values()),
                    key=lambda h: h["mean"],
                    default=None,
                ),
                "stopping_recommendation": self.should_stop(),
            }

    def reset(self):
        with self._lock:
            self._hypotheses.clear()
            self._experiments.clear()
            self._history.clear()
            self._round = 0
            self._save_state()


# ── Singleton ─────────────────────────────────────────────────────────────────

_selector: Optional[ActiveExperimentSelector] = None
_selector_lock = threading.Lock()


def get_experiment_selector() -> ActiveExperimentSelector:
    global _selector
    with _selector_lock:
        if _selector is None:
            _selector = ActiveExperimentSelector()
        return _selector
