#!/usr/bin/env python3
"""
theory_formation.py — RUMI Theory Formation Engine
=====================================================

Inspired by Yoshua Bengio's Scientist AI: a world model that generates
EXPLANATORY THEORIES from observations, not just predictions.

Core concepts:
  - Theory = a set of causal relationships + boundary conditions + predictions
  - Theories are scored by: explanatory power, predictive accuracy, simplicity, falsifiability
  - Theories evolve: revision, merger,淘汰 through evidence
  - Uncertainty is explicit: every theory has calibrated confidence intervals

This is the bridge between Bengio's "world model that explains" and
Sakana's "autonomous discovery pipeline." It turns observations into
understanding.

Architecture:
  TheoryFormationEngine
    ├── observe()           — ingest new observations
    ├── form_theories()     — generate explanatory theories
    ├── compare_theories()  — score and rank competing theories
    ├── revise_theory()     — update theory given new evidence
    ├── predict()           — make predictions from best theory
    ├── falsify()           — attempt to disprove a theory
    └── synthesize()        — merge compatible theories
"""

import json
import math
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


BRAIN_DIR = Path(__file__).parent.resolve()
THEORY_FILE = BRAIN_DIR / "theory_data.json"

# Configuration
MAX_THEORIES = 100
MAX_OBSERVATIONS = 500
MIN_EVIDENCE_FOR_THEORY = 3
THEORY_DECAY_DAYS = 30.0
OCCAM_PENALTY = 0.1  # Penalty per additional mechanism in a theory
FALSIFICATION_THRESHOLD = 0.3  # Below this confidence, theory is falsified


def _timestamp() -> str:
    return datetime.now().isoformat()


def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-max(-10, min(10, x))))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


class Theory:
    """A scientific theory: causal relationships + boundary conditions + predictions."""

    def __init__(self, name: str, domain: str = "general"):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.domain = domain
        self.mechanisms: List[Dict[str, Any]] = []  # causal mechanisms
        self.boundary_conditions: List[str] = []  # when the theory applies
        self.predictions: List[Dict[str, Any]] = []  # testable predictions
        self.supporting_evidence: List[Dict[str, Any]] = []
        self.contradicting_evidence: List[Dict[str, Any]] = []
        self.confidence: float = 0.5
        self.explanatory_power: float = 0.0
        self.simplicity_score: float = 0.0
        self.falsifiability_score: float = 0.0
        self.created_at = _timestamp()
        self.last_updated = _timestamp()
        self.revision_count = 0
        self.status = "draft"  # draft | active | falsified | superseded

    def add_mechanism(self, cause: str, effect: str, conditions: str = "",
                      strength: float = 0.5, evidence: str = ""):
        """Add a causal mechanism to the theory."""
        self.mechanisms.append({
            "cause": cause,
            "effect": effect,
            "conditions": conditions,
            "strength": round(max(0.0, min(1.0, strength)), 3),
            "evidence": evidence,
            "added_at": _timestamp(),
        })
        self.last_updated = _timestamp()

    def add_prediction(self, prediction: str, testable: bool = True,
                       confidence: float = 0.5):
        """Add a testable prediction."""
        self.predictions.append({
            "prediction": prediction,
            "testable": testable,
            "confidence": round(max(0.0, min(1.0, confidence)), 3),
            "tested": False,
            "result": None,
            "added_at": _timestamp(),
        })
        self.last_updated = _timestamp()

    def add_supporting_evidence(self, evidence: str, strength: float = 0.5,
                                 source: str = ""):
        """Record evidence that supports this theory."""
        self.supporting_evidence.append({
            "evidence": evidence,
            "strength": round(max(0.0, min(1.0, strength)), 3),
            "source": source,
            "timestamp": _timestamp(),
        })
        self._update_confidence()
        self.last_updated = _timestamp()

    def add_contradicting_evidence(self, evidence: str, severity: float = 0.5,
                                    source: str = ""):
        """Record evidence that contradicts this theory."""
        self.contradicting_evidence.append({
            "evidence": evidence,
            "severity": round(max(0.0, min(1.0, severity)), 3),
            "source": source,
            "timestamp": _timestamp(),
        })
        self._update_confidence()
        self.last_updated = _timestamp()

    def _update_confidence(self):
        """Recalibrate confidence based on evidence balance."""
        support = sum(e["strength"] for e in self.supporting_evidence)
        contra = sum(e["severity"] for e in self.contradicting_evidence)
        total = support + contra + 0.01  # avoid division by zero

        # Base confidence from evidence ratio
        evidence_ratio = support / total

        # Occam's razor penalty: more mechanisms = lower confidence
        complexity_penalty = len(self.mechanisms) * OCCAM_PENALTY

        # Falsifiability bonus: theories with testable predictions get a boost
        testable = sum(1 for p in self.predictions if p.get("testable"))
        falsifiability_bonus = min(0.2, testable * 0.05)

        self.confidence = max(0.0, min(1.0,
            evidence_ratio - complexity_penalty + falsifiability_bonus
        ))
        self.explanatory_power = round(support / max(1, len(self.supporting_evidence)), 3)
        self.simplicity_score = round(max(0.0, 1.0 - len(self.mechanisms) * 0.15), 3)
        self.falsifiability_score = round(min(1.0, testable * 0.2), 3)

    def record_prediction_result(self, prediction_index: int, result: bool,
                                  details: str = ""):
        """Record whether a prediction was confirmed or refuted."""
        if 0 <= prediction_index < len(self.predictions):
            pred = self.predictions[prediction_index]
            pred["tested"] = True
            pred["result"] = result
            pred["details"] = details
            pred["tested_at"] = _timestamp()

            if result:
                self.add_supporting_evidence(
                    f"Prediction confirmed: {pred['prediction']}",
                    strength=pred["confidence"],
                    source="experiment"
                )
            else:
                self.add_contradicting_evidence(
                    f"Prediction refuted: {pred['prediction']}",
                    severity=1.0 - pred["confidence"],
                    source="experiment"
                )

            if self.confidence < FALSIFICATION_THRESHOLD:
                self.status = "falsified"

            self.revision_count += 1
            self.last_updated = _timestamp()

    def get_score(self) -> float:
        """Composite theory score: confidence × explanatory power × simplicity."""
        return round(
            self.confidence * 0.5 +
            self.explanatory_power * 0.25 +
            self.simplicity_score * 0.15 +
            self.falsifiability_score * 0.10,
            4
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "mechanisms": self.mechanisms,
            "boundary_conditions": self.boundary_conditions,
            "predictions": self.predictions,
            "supporting_evidence": self.supporting_evidence[-20:],
            "contradicting_evidence": self.contradicting_evidence[-20:],
            "confidence": round(self.confidence, 4),
            "explanatory_power": self.explanatory_power,
            "simplicity_score": self.simplicity_score,
            "falsifiability_score": self.falsifiability_score,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "revision_count": self.revision_count,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Theory":
        t = cls(d.get("name", "unknown"), d.get("domain", "general"))
        t.id = d.get("id", t.id)
        t.mechanisms = d.get("mechanisms", [])
        t.boundary_conditions = d.get("boundary_conditions", [])
        t.predictions = d.get("predictions", [])
        t.supporting_evidence = d.get("supporting_evidence", [])
        t.contradicting_evidence = d.get("contradicting_evidence", [])
        t.confidence = d.get("confidence", 0.5)
        t.explanatory_power = d.get("explanatory_power", 0.0)
        t.simplicity_score = d.get("simplicity_score", 0.0)
        t.falsifiability_score = d.get("falsifiability_score", 0.0)
        t.created_at = d.get("created_at", _timestamp())
        t.last_updated = d.get("last_updated", _timestamp())
        t.revision_count = d.get("revision_count", 0)
        t.status = d.get("status", "draft")
        return t


class TheoryFormationEngine:
    """
    Bengio-inspired theory formation engine.

    Maintains a population of competing theories, forms new theories from
    observations, compares them, revises them based on evidence, and
    synthesizes compatible theories into unified explanations.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._theories: Dict[str, Theory] = {}
        self._observations: List[Dict[str, Any]] = []
        self._theory_comparisons: List[Dict[str, Any]] = []
        self._synthesis_log: List[Dict[str, Any]] = []
        self._stats = {
            "theories_formed": 0,
            "theories_falsified": 0,
            "theories_superseded": 0,
            "predictions_made": 0,
            "predictions_confirmed": 0,
            "predictions_refuted": 0,
            "syntheses_performed": 0,
            "observations_ingested": 0,
        }
        self._load()
        print(f"[TheoryFormation] Initialized with {len(self._theories)} theories")

    # ── Persistence ─────────────────────────────────────────────────────

    def _load(self):
        if not THEORY_FILE.exists():
            self._save()
            return
        try:
            raw = THEORY_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            for tid, t_dict in data.get("theories", {}).items():
                self._theories[tid] = Theory.from_dict(t_dict)
            self._observations = data.get("observations", [])[-MAX_OBSERVATIONS:]
            self._stats.update(data.get("stats", {}))
            print(f"[TheoryFormation] Loaded {len(self._theories)} theories")
        except (json.JSONDecodeError, IOError) as e:
            print(f"[TheoryFormation] Load failed, starting fresh: {e}")

    def _save(self):
        try:
            data = {
                "version": 1,
                "updated": _timestamp(),
                "theories": {tid: t.to_dict() for tid, t in self._theories.items()},
                "observations": self._observations[-MAX_OBSERVATIONS:],
                "stats": self._stats,
            }
            THEORY_FILE.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8"
            )
        except IOError as e:
            print(f"[TheoryFormation] Save failed: {e}")

    # ── Observation Ingestion ───────────────────────────────────────────

    def observe(self, observation: Dict[str, Any]):
        """
        Ingest a new observation. Observations are the raw material
        for theory formation.

        observation: {
            "phenomenon": str,       # what was observed
            "context": str,          # conditions
            "variables": dict,       # measured values
            "source": str,           # where this came from
            "unexpected": bool,      # was this surprising?
        }
        """
        with self._lock:
            observation["timestamp"] = _timestamp()
            self._observations.append(observation)
            if len(self._observations) > MAX_OBSERVATIONS:
                self._observations = self._observations[-MAX_OBSERVATIONS:]
            self._stats["observations_ingested"] += 1

            # If unexpected, flag for theory formation
            if observation.get("unexpected", False):
                print(f"[TheoryFormation] Unexpected observation: "
                      f"{observation.get('phenomenon', '?')[:80]}")

            self._save()

    # ── Theory Formation ────────────────────────────────────────────────

    def form_theories(self, domain: str = "general",
                      llm_call=None) -> List[Theory]:
        """
        Generate explanatory theories from accumulated observations.

        Uses the LLM to identify patterns, propose causal mechanisms,
        and formulate testable predictions.

        Args:
            domain: scientific domain for the theories
            llm_call: callable(prompt) -> str for LLM inference

        Returns: list of newly formed Theory objects
        """
        with self._lock:
            if len(self._observations) < MIN_EVIDENCE_FOR_THEORY:
                print(f"[TheoryFormation] Need ≥{MIN_EVIDENCE_FOR_THEORY} "
                      f"observations, have {len(self._observations)}")
                return []

            # Group observations by phenomenon
            by_phenomenon = defaultdict(list)
            for obs in self._observations:
                phen = obs.get("phenomenon", "unknown")
                by_phenomenon[phen].append(obs)

            # Find phenomena with enough observations to theorize about
            candidates = {k: v for k, v in by_phenomenon.items()
                         if len(v) >= MIN_EVIDENCE_FOR_THEORY}

            if not candidates:
                return []

            new_theories = []

            for phenomenon, observations in candidates.items():
                # Check if we already have a theory for this
                existing = [t for t in self._theories.values()
                          if phenomenon.lower() in t.name.lower()
                          and t.status == "active"]

                if existing:
                    # Revise existing theory instead of forming new one
                    for theory in existing:
                        self._revise_with_new_evidence(theory, observations)
                    continue

                # Form new theory
                theory = self._form_theory_from_observations(
                    phenomenon, observations, domain, llm_call
                )
                if theory:
                    new_theories.append(theory)
                    self._theories[theory.id] = theory
                    self._stats["theories_formed"] += 1

            self._save()
            return new_theories

    def _form_theory_from_observations(self, phenomenon: str,
                                        observations: List[Dict],
                                        domain: str,
                                        llm_call=None) -> Optional[Theory]:
        """Form a single theory from observations of a phenomenon."""
        theory = Theory(f"Theory of {phenomenon}", domain)

        # Extract variables and their relationships
        all_variables = set()
        for obs in observations:
            vars_dict = obs.get("variables", {})
            all_variables.update(vars_dict.keys())

        # Find correlations between variables
        correlations = self._find_correlations(observations, all_variables)

        # Build mechanisms from correlations
        for (var_a, var_b), corr_strength in correlations.items():
            if abs(corr_strength) > 0.3:
                direction = "increases" if corr_strength > 0 else "decreases"
                conditions = self._find_conditions(observations, var_a, var_b)
                theory.add_mechanism(
                    cause=var_a,
                    effect=f"{direction} {var_b}",
                    conditions=conditions,
                    strength=abs(corr_strength),
                    evidence=f"Correlation observed across {len(observations)} instances"
                )

        # Generate predictions from mechanisms
        for mech in theory.mechanisms:
            pred = f"If {mech['cause']} is manipulated, {mech['effect']} should change"
            theory.add_prediction(pred, testable=True, confidence=mech["strength"])

        # Use LLM for deeper theory formation if available
        if llm_call and len(observations) >= 3:
            try:
                llm_theory = self._llm_form_theory(
                    phenomenon, observations, domain, llm_call
                )
                if llm_theory:
                    # Merge LLM insights into theory
                    for mech in llm_theory.get("mechanisms", []):
                        theory.add_mechanism(
                            cause=mech.get("cause", ""),
                            effect=mech.get("effect", ""),
                            conditions=mech.get("conditions", ""),
                            strength=mech.get("strength", 0.5),
                            evidence="LLM-inferred mechanism"
                        )
                    for pred in llm_theory.get("predictions", []):
                        theory.add_prediction(pred, testable=True, confidence=0.5)
                    for bc in llm_theory.get("boundary_conditions", []):
                        theory.boundary_conditions.append(bc)
            except Exception as e:
                print(f"[TheoryFormation] LLM theory formation failed: {e}")

        # Add supporting evidence from observations
        for obs in observations:
            theory.add_supporting_evidence(
                obs.get("phenomenon", "observation"),
                strength=0.5,
                source=obs.get("source", "observation")
            )

        theory.status = "active"
        theory._update_confidence()

        if not theory.mechanisms:
            return None

        return theory

    def _find_correlations(self, observations: List[Dict],
                           variables: set) -> Dict[Tuple[str, str], float]:
        """Find correlations between variables across observations."""
        correlations = {}
        var_list = sorted(variables)

        for i, var_a in enumerate(var_list):
            for var_b in var_list[i+1:]:
                values_a = []
                values_b = []
                for obs in observations:
                    vars_dict = obs.get("variables", {})
                    va = vars_dict.get(var_a)
                    vb = vars_dict.get(var_b)
                    if va is not None and vb is not None:
                        try:
                            values_a.append(float(va))
                            values_b.append(float(vb))
                        except (TypeError, ValueError):
                            continue

                if len(values_a) >= 3:
                    # Pearson correlation
                    n = len(values_a)
                    mean_a = sum(values_a) / n
                    mean_b = sum(values_b) / n
                    cov = sum((a - mean_a) * (b - mean_b)
                             for a, b in zip(values_a, values_b)) / n
                    std_a = math.sqrt(sum((a - mean_a)**2 for a in values_a) / n)
                    std_b = math.sqrt(sum((b - mean_b)**2 for b in values_b) / n)
                    if std_a > 0 and std_b > 0:
                        r = cov / (std_a * std_b)
                        correlations[(var_a, var_b)] = round(r, 3)

        return correlations

    def _find_conditions(self, observations: List[Dict],
                         var_a: str, var_b: str) -> str:
        """Find conditions under which the relationship holds."""
        contexts = set()
        for obs in observations:
            ctx = obs.get("context", "")
            if ctx:
                contexts.add(ctx[:100])
        if contexts:
            return "; ".join(list(contexts)[:3])
        return "general conditions"

    def _llm_form_theory(self, phenomenon: str, observations: List[Dict],
                          domain: str, llm_call) -> Optional[dict]:
        """Use LLM to form a deeper theory from observations."""
        obs_summary = json.dumps(observations[:10], indent=2, default=str)

        prompt = (
            f"You are a scientific theory formation engine. Given these "
            f"observations about '{phenomenon}' in the domain of {domain}, "
            f"form a coherent explanatory theory.\n\n"
            f"Observations:\n{obs_summary[:3000]}\n\n"
            f"Output JSON:\n"
            f'{{"mechanisms": [{{"cause": "...", "effect": "...", "conditions": "...", "strength": 0.5}}], '
            f'"predictions": ["testable prediction 1", ...], '
            f'"boundary_conditions": ["when theory applies", ...], '
            f'"core_insight": "one sentence summary"}}'
        )

        try:
            result = llm_call(prompt)
            if result:
                # Try to parse JSON from response
                result = result.strip()
                if result.startswith("```"):
                    result = result.split("\n", 1)[1] if "\n" in result else result[3:]
                    result = result.rsplit("```", 1)[0].strip()
                return json.loads(result)
        except Exception:
            pass
        return None

    # ── Theory Comparison ───────────────────────────────────────────────

    def compare_theories(self, phenomenon: str) -> List[Dict[str, Any]]:
        """
        Compare competing theories for the same phenomenon.
        Returns ranked list with scores and explanations.
        """
        with self._lock:
            relevant = [
                t for t in self._theories.values()
                if phenomenon.lower() in t.name.lower()
                or any(phenomenon.lower() in m.get("cause", "").lower()
                      or phenomenon.lower() in m.get("effect", "").lower()
                      for m in t.mechanisms)
            ]

            if not relevant:
                return []

            ranked = []
            for theory in relevant:
                score = theory.get_score()
                ranked.append({
                    "theory_id": theory.id,
                    "name": theory.name,
                    "score": score,
                    "confidence": theory.confidence,
                    "explanatory_power": theory.explanatory_power,
                    "simplicity": theory.simplicity_score,
                    "falsifiability": theory.falsifiability_score,
                    "mechanism_count": len(theory.mechanisms),
                    "evidence_count": len(theory.supporting_evidence),
                    "contradiction_count": len(theory.contradicting_evidence),
                    "status": theory.status,
                    "predictions_tested": sum(1 for p in theory.predictions if p.get("tested")),
                    "predictions_confirmed": sum(1 for p in theory.predictions if p.get("result")),
                })

            ranked.sort(key=lambda x: x["score"], reverse=True)

            self._theory_comparisons.append({
                "phenomenon": phenomenon,
                "theories_compared": len(ranked),
                "best_theory": ranked[0]["name"] if ranked else None,
                "timestamp": _timestamp(),
            })
            self._save()

            return ranked

    # ── Theory Revision ─────────────────────────────────────────────────

    def revise_theory(self, theory_id: str, new_evidence: Dict[str, Any],
                      llm_call=None) -> Optional[Theory]:
        """
        Revise a theory given new evidence. May strengthen, weaken,
        or fundamentally alter the theory.
        """
        with self._lock:
            theory = self._theories.get(theory_id)
            if not theory:
                return None

            supports = new_evidence.get("supports", True)
            evidence_text = new_evidence.get("evidence", "")
            strength = new_evidence.get("strength", 0.5)
            source = new_evidence.get("source", "experiment")

            if supports:
                theory.add_supporting_evidence(evidence_text, strength, source)
            else:
                theory.add_contradicting_evidence(evidence_text, strength, source)

            # If confidence dropped significantly, attempt revision
            if theory.confidence < 0.4 and llm_call:
                revised = self._llm_revise_theory(theory, new_evidence, llm_call)
                if revised:
                    # Update mechanisms
                    theory.mechanisms = revised.get("mechanisms", theory.mechanisms)
                    theory.boundary_conditions = revised.get(
                        "boundary_conditions", theory.boundary_conditions
                    )
                    theory.revision_count += 1
                    theory.last_updated = _timestamp()

            if theory.confidence < FALSIFICATION_THRESHOLD:
                theory.status = "falsified"
                self._stats["theories_falsified"] += 1

            self._save()
            return theory

    def _revise_with_new_evidence(self, theory: Theory,
                                   observations: List[Dict]):
        """Revise a theory with batch observations."""
        for obs in observations:
            theory.add_supporting_evidence(
                obs.get("phenomenon", "observation"),
                strength=0.5,
                source=obs.get("source", "observation")
            )

    def _llm_revise_theory(self, theory: Theory, new_evidence: Dict,
                            llm_call) -> Optional[dict]:
        """Use LLM to revise a weakened theory."""
        prompt = (
            f"This theory has been weakened by new evidence. Revise it.\n\n"
            f"Theory: {theory.name}\n"
            f"Current mechanisms: {json.dumps(theory.mechanisms, indent=2)}\n"
            f"New evidence: {json.dumps(new_evidence, indent=2)}\n"
            f"Confidence: {theory.confidence}\n\n"
            f"Suggest revised mechanisms and boundary conditions.\n"
            f'Output JSON: {{"mechanisms": [...], "boundary_conditions": [...]}}'
        )
        try:
            result = llm_call(prompt)
            if result:
                result = result.strip()
                if result.startswith("```"):
                    result = result.split("\n", 1)[1] if "\n" in result else result[3:]
                    result = result.rsplit("```", 1)[0].strip()
                return json.loads(result)
        except Exception:
            pass
        return None

    # ── Prediction ──────────────────────────────────────────────────────

    def predict(self, phenomenon: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make predictions from the best theory for a phenomenon.
        Returns predictions with confidence intervals.
        """
        with self._lock:
            ranked = self.compare_theories(phenomenon)
            if not ranked:
                return {"predictions": [], "confidence": 0.0,
                        "theory": None, "uncertainty": 1.0}

            best = ranked[0]
            theory = self._theories.get(best["theory_id"])
            if not theory:
                return {"predictions": [], "confidence": 0.0,
                        "theory": None, "uncertainty": 1.0}

            predictions = []
            for pred in theory.predictions:
                if not pred.get("tested"):
                    predictions.append({
                        "prediction": pred["prediction"],
                        "confidence": pred["confidence"],
                        "uncertainty": 1.0 - pred["confidence"],
                    })

            return {
                "predictions": predictions,
                "confidence": theory.confidence,
                "theory": theory.name,
                "theory_id": theory.id,
                "mechanism_count": len(theory.mechanisms),
                "uncertainty": 1.0 - theory.confidence,
                "explanatory_power": theory.explanatory_power,
            }

    # ── Falsification ───────────────────────────────────────────────────

    def falsify(self, theory_id: str, llm_call=None) -> Dict[str, Any]:
        """
        Attempt to falsify a theory by finding contradictions,
        proposing critical experiments, and identifying weaknesses.
        """
        with self._lock:
            theory = self._theories.get(theory_id)
            if not theory:
                return {"error": "Theory not found"}

            weaknesses = []
            critical_experiments = []

            # Find untested predictions (falsification targets)
            untested = [p for p in theory.predictions if not p.get("tested")]
            for pred in untested:
                critical_experiments.append({
                    "experiment": f"Test: {pred['prediction']}",
                    "expected_to_falsify": pred["confidence"] < 0.5,
                    "priority": 1.0 - pred["confidence"],
                })

            # Identify internal contradictions
            for i, m1 in enumerate(theory.mechanisms):
                for m2 in theory.mechanisms[i+1:]:
                    if m1.get("effect", "").lower() == m2.get("effect", "").lower():
                        if m1.get("cause", "") != m2.get("cause", ""):
                            weaknesses.append({
                                "type": "competing_mechanisms",
                                "detail": f"Both '{m1['cause']}' and '{m2['cause']}' "
                                         f"claim to cause '{m1['effect']}'",
                                "severity": "medium",
                            })

            # Check for missing boundary conditions
            if not theory.boundary_conditions:
                weaknesses.append({
                    "type": "no_boundary_conditions",
                    "detail": "Theory has no stated boundary conditions — "
                             "it may be over-generalized",
                    "severity": "medium",
                })

            # Use LLM for deeper falsification analysis
            if llm_call:
                try:
                    llm_analysis = self._llm_falsify(theory, llm_call)
                    if llm_analysis:
                        weaknesses.extend(llm_analysis.get("weaknesses", []))
                        critical_experiments.extend(
                            llm_analysis.get("critical_experiments", [])
                        )
                except Exception:
                    pass

            # Sort experiments by priority
            critical_experiments.sort(
                key=lambda x: x.get("priority", 0), reverse=True
            )

            return {
                "theory": theory.name,
                "theory_id": theory.id,
                "current_confidence": theory.confidence,
                "weaknesses": weaknesses,
                "critical_experiments": critical_experiments[:5],
                "evidence_balance": {
                    "supporting": len(theory.supporting_evidence),
                    "contradicting": len(theory.contradicting_evidence),
                },
                "falsification_status": (
                    "falsified" if theory.status == "falsified"
                    else "vulnerable" if theory.confidence < 0.4
                    else "robust" if theory.confidence > 0.7
                    else "uncertain"
                ),
            }

    def _llm_falsify(self, theory: Theory, llm_call) -> Optional[dict]:
        """Use LLM to find weaknesses and propose critical experiments."""
        prompt = (
            f"Attempt to falsify this scientific theory.\n\n"
            f"Theory: {theory.name}\n"
            f"Mechanisms: {json.dumps(theory.mechanisms, indent=2)}\n"
            f"Boundary conditions: {theory.boundary_conditions}\n"
            f"Supporting evidence: {len(theory.supporting_evidence)} items\n"
            f"Contradicting evidence: {len(theory.contradicting_evidence)} items\n\n"
            f"Find:\n"
            f"1. Logical weaknesses in the causal chain\n"
            f"2. Missing confounders or alternative explanations\n"
            f"3. Critical experiments that could disprove the theory\n"
            f"4. Boundary conditions that are too broad\n\n"
            f'Output JSON: {{"weaknesses": [{{"type": "...", "detail": "...", "severity": "low|medium|high"}}], '
            f'"critical_experiments": [{{"experiment": "...", "expected_to_falsify": true, "priority": 0.5}}]}}'
        )
        try:
            result = llm_call(prompt)
            if result:
                result = result.strip()
                if result.startswith("```"):
                    result = result.split("\n", 1)[1] if "\n" in result else result[3:]
                    result = result.rsplit("```", 1)[0].strip()
                return json.loads(result)
        except Exception:
            pass
        return None

    # ── Theory Synthesis ────────────────────────────────────────────────

    def synthesize(self, theory_ids: List[str], llm_call=None) -> Optional[Theory]:
        """
        Merge compatible theories into a unified explanation.
        Keeps the best mechanisms from each, resolves contradictions.
        """
        with self._lock:
            theories = [self._theories.get(tid) for tid in theory_ids]
            theories = [t for t in theories if t is not None]

            if len(theories) < 2:
                return None

            # Find common domain
            domains = set(t.domain for t in theories)
            domain = domains.pop() if len(domains) == 1 else "interdisciplinary"

            # Create unified theory
            unified = Theory(
                f"Synthesis: {' + '.join(t.name for t in theories[:3])}",
                domain
            )

            # Merge mechanisms (deduplicate by cause-effect pair)
            seen_mechanisms = set()
            for theory in theories:
                for mech in theory.mechanisms:
                    key = (mech.get("cause", ""), mech.get("effect", ""))
                    if key not in seen_mechanisms:
                        seen_mechanisms.add(key)
                        unified.add_mechanism(
                            cause=mech["cause"],
                            effect=mech["effect"],
                            conditions=mech.get("conditions", ""),
                            strength=mech.get("strength", 0.5),
                            evidence=f"From {theory.name}"
                        )

                # Merge boundary conditions
                for bc in theory.boundary_conditions:
                    if bc not in unified.boundary_conditions:
                        unified.boundary_conditions.append(bc)

                # Merge supporting evidence
                for ev in theory.supporting_evidence[-5:]:
                    unified.add_supporting_evidence(
                        ev.get("evidence", ""),
                        strength=ev.get("strength", 0.5),
                        source=f"From {theory.name}"
                    )

            # Use LLM for intelligent synthesis if available
            if llm_call:
                try:
                    llm_synthesis = self._llm_synthesize(theories, llm_call)
                    if llm_synthesis:
                        for mech in llm_synthesis.get("novel_mechanisms", []):
                            unified.add_mechanism(
                                cause=mech.get("cause", ""),
                                effect=mech.get("effect", ""),
                                conditions=mech.get("conditions", ""),
                                strength=mech.get("strength", 0.5),
                                evidence="Synthesized insight"
                            )
                        for pred in llm_synthesis.get("unified_predictions", []):
                            unified.add_prediction(pred, testable=True, confidence=0.5)
                except Exception:
                    pass

            unified.status = "active"
            unified._update_confidence()

            # Store and mark originals as superseded
            self._theories[unified.id] = unified
            for theory in theories:
                theory.status = "superseded"
                self._stats["theories_superseded"] += 1

            self._synthesis_log.append({
                "input_theories": [t.id for t in theories],
                "unified_theory": unified.id,
                "mechanism_count": len(unified.mechanisms),
                "timestamp": _timestamp(),
            })
            self._stats["syntheses_performed"] += 1
            self._save()

            return unified

    def _llm_synthesize(self, theories: List[Theory],
                        llm_call) -> Optional[dict]:
        """Use LLM to intelligently synthesize theories."""
        theory_descriptions = []
        for t in theories:
            theory_descriptions.append(
                f"Theory: {t.name}\n"
                f"Mechanisms: {json.dumps(t.mechanisms, indent=2)}\n"
                f"Confidence: {t.confidence}"
            )

        prompt = (
            f"Synthesize these scientific theories into a unified explanation.\n\n"
            f"{''.join(theory_descriptions)}\n\n"
            f"Find:\n"
            f"1. Novel mechanisms that emerge from combining theories\n"
            f"2. Unified predictions that follow from the synthesis\n"
            f"3. How contradictions between theories can be resolved\n\n"
            f'Output JSON: {{"novel_mechanisms": [...], "unified_predictions": [...], '
            f'"contradiction_resolutions": [...]}}'
        )
        try:
            result = llm_call(prompt)
            if result:
                result = result.strip()
                if result.startswith("```"):
                    result = result.split("\n", 1)[1] if "\n" in result else result[3:]
                    result = result.rsplit("```", 1)[0].strip()
                return json.loads(result)
        except Exception:
            pass
        return None

    # ── Query & Stats ───────────────────────────────────────────────────

    def get_active_theories(self) -> List[Theory]:
        """Get all active (non-falsified, non-superseded) theories."""
        with self._lock:
            return [t for t in self._theories.values() if t.status == "active"]

    def get_theory(self, theory_id: str) -> Optional[Theory]:
        """Get a specific theory by ID."""
        with self._lock:
            return self._theories.get(theory_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        with self._lock:
            active = sum(1 for t in self._theories.values() if t.status == "active")
            falsified = sum(1 for t in self._theories.values() if t.status == "falsified")
            superseded = sum(1 for t in self._theories.values() if t.status == "superseded")
            avg_confidence = (
                sum(t.confidence for t in self._theories.values()) /
                max(1, len(self._theories))
            )
            return {
                **self._stats,
                "total_theories": len(self._theories),
                "active_theories": active,
                "falsified_theories": falsified,
                "superseded_theories": superseded,
                "avg_confidence": round(avg_confidence, 3),
                "total_observations": len(self._observations),
            }

    def format_for_prompt(self, max_chars: int = 1500) -> str:
        """Format theory state for system prompt injection."""
        with self._lock:
            stats = self.get_stats()
            if stats["total_theories"] == 0:
                return ""

            parts = [
                "[THEORY FORMATION ENGINE — Active Scientific Theories]",
                f"  Theories: {stats['active_theories']} active, "
                f"{stats['falsified_theories']} falsified, "
                f"{stats['superseded_theories']} superseded",
                f"  Avg confidence: {stats['avg_confidence']:.0%}",
                f"  Observations: {stats['total_observations']}",
            ]

            # Top active theories
            active = sorted(
                [t for t in self._theories.values() if t.status == "active"],
                key=lambda t: t.get_score(),
                reverse=True
            )[:3]

            if active:
                parts.append("  Top theories:")
                for t in active:
                    parts.append(
                        f"    {t.name} (conf={t.confidence:.0%}, "
                        f"mechanisms={len(t.mechanisms)}, "
                        f"score={t.get_score():.2f})"
                    )

            result = "\n".join(parts)
            if len(result) > max_chars:
                result = result[:max_chars].rsplit("\n", 1)[0] + "\n  [...]"
            return result


# ── Singleton ───────────────────────────────────────────────────────────

_theory_engine = None
_theory_lock = threading.Lock()


def get_theory_formation_engine() -> TheoryFormationEngine:
    """Get singleton TheoryFormationEngine instance."""
    global _theory_engine
    if _theory_engine is None:
        with _theory_lock:
            if _theory_engine is None:
                _theory_engine = TheoryFormationEngine()
    return _theory_engine
