#!/usr/bin/env python3
"""
scientific_reasoning.py — RUMI Scientific Reasoning Loop
==========================================================

The cognitive engine for scientific discovery. Implements a multi-pass
reasoning cycle inspired by the scientific method, Bengio's System 2
deep learning, and Sakana's autonomous discovery pipeline.

Cycle: Observe → Hypothesize → Predict → Test → Revise → Theorize

Each phase uses the appropriate brain module:
  - Observe:    curiosity + world_model (detect anomalies, encode observations)
  - Hypothesize: creativity_engine + abstraction_engine (generate explanations)
  - Predict:    world_model + causal_reasoner (simulate outcomes)
  - Test:       discovery pipeline (execute experiments, gather evidence)
  - Revise:     theory_formation (update theories with new evidence)
  - Theorize:   theory_formation + abstraction_engine (synthesize knowledge)

This is the "System 2" layer — slow, deliberate, multi-pass reasoning
that goes beyond pattern matching to genuine understanding.

Architecture:
  ScientificReasoningLoop
    ├── observe()         — detect what's interesting/unexplained
    ├── hypothesize()     — generate candidate explanations
    ├── predict()         — derive testable predictions from hypotheses
    ├── test()            — design and run experiments
    ├── revise()          — update beliefs based on evidence
    ├── theorize()        — synthesize into coherent theories
    ├── reason()          — full cycle: observe→hypothesize→predict→test→revise→theorize
    └── reflect()         — meta-cognitive review of reasoning quality

Thread-safe. Persistent state in scientific_reasoning_state.json.
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
STATE_FILE = BRAIN_DIR / "scientific_reasoning_state.json"

# ── Configuration ───────────────────────────────────────────────────────────

MAX_CYCLES_PER_SESSION = 10
MIN_NOVELTY_FOR_HYPOTHESIS = 0.3
PREDICTION_CONFIDENCE_THRESHOLD = 0.4
MAX_HYPOTHESES_PER_CYCLE = 5
EVIDENCE_WEIGHT_PRIOR = 1.0
REVISION_LEARNING_RATE = 0.15
MAX_REASONING_HISTORY = 100


def _timestamp() -> str:
    return datetime.now().isoformat()


def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-max(-10, min(10, x))))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def _safe_import(module_path: str, class_name: str):
    """Import a brain module with graceful fallback."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)
    except Exception:
        return None


# ── Data Structures ─────────────────────────────────────────────────────────


class Observation:
    """A scientific observation — something interesting or unexplained."""

    def __init__(self, phenomenon: str, context: str = "", domain: str = "general"):
        self.id = str(uuid.uuid4())[:8]
        self.phenomenon = phenomenon
        self.context = context
        self.domain = domain
        self.anomaly_score: float = 0.0  # How surprising/unexplained
        self.features: Dict[str, Any] = {}
        self.timestamp = _timestamp()

    def to_dict(self) -> dict:
        return {
            "id": self.id, "phenomenon": self.phenomenon,
            "context": self.context, "domain": self.domain,
            "anomaly_score": round(self.anomaly_score, 3),
            "features": self.features, "timestamp": self.timestamp,
        }


class Hypothesis:
    """A candidate explanation for an observation."""

    def __init__(self, statement: str, observation_id: str, domain: str = "general"):
        self.id = str(uuid.uuid4())[:8]
        self.statement = statement
        self.observation_id = observation_id
        self.domain = domain
        self.mechanisms: List[str] = []
        self.supporting_evidence: List[Dict[str, Any]] = []
        self.contradicting_evidence: List[Dict[str, Any]] = []
        self.predictions: List[Dict[str, Any]] = []
        self.confidence: float = 0.5
        self.novelty: float = 0.5
        self.falsifiability: float = 0.5
        self.parsimony: float = 0.5
        self.created_at = _timestamp()
        self.revised_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "statement": self.statement,
            "observation_id": self.observation_id, "domain": self.domain,
            "mechanisms": self.mechanisms,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "predictions": self.predictions,
            "confidence": round(self.confidence, 3),
            "novelty": round(self.novelty, 3),
            "falsifiability": round(self.falsifiability, 3),
            "parsimony": round(self.parsimony, 3),
            "created_at": self.created_at, "revised_at": self.revised_at,
        }


class Prediction:
    """A testable prediction derived from a hypothesis."""

    def __init__(self, statement: str, hypothesis_id: str, test_method: str = ""):
        self.id = str(uuid.uuid4())[:8]
        self.statement = statement
        self.hypothesis_id = hypothesis_id
        self.test_method = test_method
        self.expected_outcome: str = ""
        self.actual_outcome: str = ""
        self.confidence_before: float = 0.5
        self.confidence_after: float = 0.5
        self.tested: bool = False
        self.result: str = "pending"  # pending | confirmed | refuted | inconclusive
        self.created_at = _timestamp()
        self.tested_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "statement": self.statement,
            "hypothesis_id": self.hypothesis_id,
            "test_method": self.test_method,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "confidence_before": round(self.confidence_before, 3),
            "confidence_after": round(self.confidence_after, 3),
            "tested": self.tested, "result": self.result,
            "created_at": self.created_at, "tested_at": self.tested_at,
        }


class ReasoningCycle:
    """Record of a complete reasoning cycle."""

    def __init__(self, cycle_num: int, topic: str):
        self.id = str(uuid.uuid4())[:8]
        self.cycle_num = cycle_num
        self.topic = topic
        self.phase_durations: Dict[str, float] = {}
        self.observations: List[dict] = []
        self.hypotheses: List[dict] = []
        self.predictions: List[dict] = []
        self.revisions: List[dict] = []
        self.theories_synthesized: List[dict] = []
        self.insights: List[str] = []
        self.confidence_delta: float = 0.0  # Net change in understanding
        self.started_at = _timestamp()
        self.completed_at: Optional[str] = None
        self.duration_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id, "cycle_num": self.cycle_num, "topic": self.topic,
            "phase_durations": self.phase_durations,
            "observations": self.observations, "hypotheses": self.hypotheses,
            "predictions": self.predictions, "revisions": self.revisions,
            "theories_synthesized": self.theories_synthesized,
            "insights": self.insights,
            "confidence_delta": round(self.confidence_delta, 3),
            "started_at": self.started_at, "completed_at": self.completed_at,
            "duration_s": round(self.duration_s, 2),
        }


# ── Scientific Reasoning Loop ───────────────────────────────────────────────


class ScientificReasoningLoop:
    """
    Multi-pass scientific reasoning engine.

    Integrates RUMI's brain modules into a coherent scientific discovery
    pipeline. Each reasoning cycle produces observations, hypotheses,
    predictions, tests, revisions, and synthesized theories.
    """

    def __init__(self, llm_fn=None):
        """
        Args:
            llm_fn: async callable(prompt, **kwargs) -> str for LLM calls.
                    If None, attempts to import from discovery.pipeline.
        """
        self._lock = threading.RLock()
        self._llm_fn = llm_fn
        self._cycle_count: int = 0
        self._history: List[ReasoningCycle] = []
        self._active_observations: List[Observation] = []
        self._active_hypotheses: List[Hypothesis] = []
        self._active_predictions: List[Prediction] = []
        self._insights: List[str] = []
        self._topic_context: str = ""

        # Brain module references (lazy-loaded)
        self._theory_engine = None
        self._causal_reasoner = None
        self._world_model = None
        self._creativity_engine = None
        self._abstraction_engine = None
        self._curiosity_module = None

        self._load_state()
        print(f"[ScientificReasoning] Initialized ({self._cycle_count} prior cycles)")

    # ── Brain Module Access ─────────────────────────────────────────────

    def _get_theory_engine(self):
        if self._theory_engine is None:
            cls = _safe_import("brain.theory_formation", "TheoryFormationEngine")
            if cls:
                self._theory_engine = cls()
        return self._theory_engine

    def _get_causal_reasoner(self):
        if self._causal_reasoner is None:
            cls = _safe_import("brain.causal_reasoner", "CausalReasoner")
            if cls:
                self._causal_reasoner = cls()
        return self._causal_reasoner

    def _get_world_model(self):
        if self._world_model is None:
            cls = _safe_import("brain.world_model", "WorldModel")
            if cls:
                self._world_model = cls()
        return self._world_model

    def _get_creativity_engine(self):
        if self._creativity_engine is None:
            cls = _safe_import("brain.creativity_engine", "CreativityEngine")
            if cls:
                self._creativity_engine = cls()
        return self._creativity_engine

    def _get_abstraction_engine(self):
        if self._abstraction_engine is None:
            cls = _safe_import("brain.abstraction_engine", "AbstractionEngine")
            if cls:
                self._abstraction_engine = cls()
        return self._abstraction_engine

    def _get_curiosity(self):
        if self._curiosity_module is None:
            cls = _safe_import("brain.curiosity", "CuriosityModule")
            if cls:
                self._curiosity_module = cls()
        return self._curiosity_module

    async def _llm(self, prompt: str, **kwargs) -> str:
        """Call LLM with graceful fallback."""
        if self._llm_fn:
            return await self._llm_fn(prompt, **kwargs)
        # Try importing pipeline LLM
        try:
            from discovery.pipeline import LLMStage
            stage = LLMStage("scientific_reasoning", max_retries=2,
                             backoff=[3, 8], providers=["groq", "gemini"])
            result, _ = await stage.call_with_retry(prompt, **kwargs)
            return result or ""
        except Exception:
            return ""

    # ── Phase 1: Observe ────────────────────────────────────────────────

    async def observe(self, data: str, context: str = "", domain: str = "general") -> List[Observation]:
        """
        Detect interesting/unexplained phenomena in data.

        Uses world_model to detect anomalies (high prediction error) and
        curiosity module to prioritize novel observations.
        """
        t0 = time.time()
        observations = []

        # Use LLM to identify interesting phenomena
        prompt = f"""Analyze the following data and identify phenomena that are:
1. Surprising or unexpected
2. Unexplained by common knowledge
3. Potentially indicating deeper patterns
4. Worth investigating scientifically

Data: {data[:3000]}
Context: {context[:1000]}
Domain: {domain}

For each phenomenon, provide:
- phenomenon: what you observed
- anomaly_score: 0.0-1.0 (how surprising)
- features: key characteristics
- why_interesting: why this warrants investigation

Return JSON array of observations."""

        raw = await self._llm(prompt, json_mode=True, max_tokens=4096)
        parsed = self._parse_json(raw)

        if isinstance(parsed, list):
            for item in parsed[:MAX_HYPOTHESES_PER_CYCLE]:
                obs = Observation(
                    phenomenon=item.get("phenomenon", "Unknown"),
                    context=context or item.get("why_interesting", ""),
                    domain=domain,
                )
                obs.anomaly_score = float(item.get("anomaly_score", 0.5))
                obs.features = item.get("features", {}) if isinstance(item.get("features"), dict) else {}
                observations.append(obs)
        elif isinstance(parsed, dict):
            obs = Observation(
                phenomenon=parsed.get("phenomenon", data[:200]),
                context=context, domain=domain,
            )
            obs.anomaly_score = float(parsed.get("anomaly_score", 0.5))
            observations.append(obs)

        # Feed to world model for anomaly detection
        wm = self._get_world_model()
        if wm:
            for obs in observations:
                try:
                    wm.encode_experience({
                        "type": "observation",
                        "content": obs.phenomenon,
                        "domain": domain,
                        "context": context,
                    })
                except Exception:
                    pass

        # Store observations
        with self._lock:
            self._active_observations.extend(observations)

        elapsed = time.time() - t0
        print(f"[ScientificReasoning] observe(): {len(observations)} observations in {elapsed:.1f}s")
        return observations

    # ── Phase 2: Hypothesize ────────────────────────────────────────────

    async def hypothesize(self, observations: Optional[List[Observation]] = None,
                          domain: str = "general") -> List[Hypothesis]:
        """
        Generate candidate explanations for observations.

        Uses creativity_engine for novel hypotheses and abstraction_engine
        for cross-domain analogies.
        """
        t0 = time.time()
        observations = observations or self._active_observations
        if not observations:
            print("[ScientificReasoning] hypothesize(): no observations to explain")
            return []

        obs_descriptions = "\n".join(
            f"- [{o.id}] {o.phenomenon} (anomaly: {o.anomaly_score:.2f})"
            for o in observations[:10]
        )

        prompt = f"""You are a scientist trying to explain the following observations:

{obs_descriptions}

For each observation, generate up to {MAX_HYPOTHESES_PER_CYCLE} hypotheses that:
1. Provide a MECHANISTIC explanation (how does this work?)
2. Are FALSIFIABLE (what evidence would disprove them?)
3. Are PARSIMONIOUS (simplest explanation that fits)
4. Are NOVEL (not just restating the observation)
5. Have CLEAR BOUNDARY CONDITIONS (when does this apply?)

For each hypothesis provide:
- statement: the hypothesis
- observation_id: which observation it explains
- mechanisms: list of causal mechanisms
- falsifiability: 0.0-1.0 (how easy to disprove)
- parsimony: 0.0-1.0 (simplicity)
- novelty: 0.0-1.0 (how original)

Return JSON array."""

        raw = await self._llm(prompt, json_mode=True, max_tokens=6144)
        parsed = self._parse_json(raw)

        hypotheses = []
        obs_map = {o.id: o for o in observations}

        items = parsed if isinstance(parsed, list) else [parsed] if isinstance(parsed, dict) else []
        for item in items[:MAX_HYPOTHESES_PER_CYCLE]:
            obs_id = item.get("observation_id", observations[0].id if observations else "")
            h = Hypothesis(
                statement=item.get("statement", ""),
                observation_id=obs_id,
                domain=domain,
            )
            h.mechanisms = item.get("mechanisms", [])
            h.falsifiability = _sigmoid(float(item.get("falsifiability", 0.5)))
            h.parsimony = _sigmoid(float(item.get("parsimony", 0.5)))
            h.novelty = _sigmoid(float(item.get("novelty", 0.5)))

            # Boost novelty using creativity engine
            ce = self._get_creativity_engine()
            if ce and h.statement:
                try:
                    creative_score = ce.evaluate_novelty(h.statement)
                    if creative_score:
                        h.novelty = max(h.novelty, creative_score)
                except Exception:
                    pass

            # Score confidence
            h.confidence = self._score_hypothesis(h)
            hypotheses.append(h)

        # Use abstraction engine for cross-domain analogies
        ae = self._get_abstraction_engine()
        if ae and observations:
            try:
                for obs in observations[:2]:
                    analogies = ae.find_analogies(obs.phenomenon, target_domain=domain)
                    if analogies:
                        for ana in analogies[:2]:
                            h = Hypothesis(
                                statement=f"By analogy: {ana}",
                                observation_id=obs.id,
                                domain=domain,
                            )
                            h.novelty = 0.8  # Cross-domain = high novelty
                            h.confidence = self._score_hypothesis(h)
                            hypotheses.append(h)
            except Exception:
                pass

        with self._lock:
            self._active_hypotheses.extend(hypotheses)

        elapsed = time.time() - t0
        print(f"[ScientificReasoning] hypothesize(): {len(hypotheses)} hypotheses in {elapsed:.1f}s")
        return hypotheses

    def _score_hypothesis(self, h: Hypothesis) -> float:
        """Score hypothesis quality (Occam's razor applied)."""
        base = (h.falsifiability * 0.3 + h.parsimony * 0.3 + h.novelty * 0.2 + 0.2)
        # Occam's penalty for complex mechanisms
        complexity_penalty = len(h.mechanisms) * 0.05
        return _sigmoid(base - complexity_penalty)

    # ── Phase 3: Predict ────────────────────────────────────────────────

    async def predict(self, hypotheses: Optional[List[Hypothesis]] = None) -> List[Prediction]:
        """
        Derive testable predictions from hypotheses.

        Uses world_model for trajectory simulation and causal_reasoner
        for interventional predictions.
        """
        t0 = time.time()
        hypotheses = hypotheses or self._active_hypotheses
        if not hypotheses:
            print("[ScientificReasoning] predict(): no hypotheses to predict from")
            return []

        predictions = []
        for h in hypotheses[:MAX_HYPOTHESES_PER_CYCLE]:
            prompt = f"""Given this scientific hypothesis:
"{h.statement}"

Mechanisms: {', '.join(h.mechanisms) if h.mechanisms else 'unknown'}

Generate 1-2 testable predictions that:
1. Follow LOGICALLY from the hypothesis
2. Are SPECIFIC (observable, measurable)
3. Are DISTINGUISHING (would differentiate this from alternatives)
4. Include a TEST METHOD (how to verify)

For each prediction:
- statement: what will happen
- expected_outcome: specific expected result
- test_method: how to test this
- confidence: 0.0-1.0 (how likely given the hypothesis)

Return JSON array."""

            raw = await self._llm(prompt, json_mode=True, max_tokens=2048)
            parsed = self._parse_json(raw)
            items = parsed if isinstance(parsed, list) else [parsed] if isinstance(parsed, dict) else []

            for item in items[:2]:
                pred = Prediction(
                    statement=item.get("statement", ""),
                    hypothesis_id=h.id,
                    test_method=item.get("test_method", ""),
                )
                pred.expected_outcome = item.get("expected_outcome", "")
                pred.confidence_before = _sigmoid(float(item.get("confidence", 0.5)))
                predictions.append(pred)
                h.predictions.append(pred.to_dict())

        # Use world model to simulate predictions
        wm = self._get_world_model()
        if wm:
            for pred in predictions[:5]:
                try:
                    trajectory = wm.imagine_trajectory(
                        start_state={"hypothesis": pred.statement},
                        steps=3,
                    )
                    if trajectory:
                        pred.confidence_before = max(pred.confidence_before,
                                                     trajectory.get("confidence", 0.5))
                except Exception:
                    pass

        # Use causal reasoner for interventional predictions
        cr = self._get_causal_reasoner()
        if cr:
            for pred in predictions[:3]:
                try:
                    causal_pred = cr.predict_intervention(pred.statement)
                    if causal_pred:
                        pred.confidence_before = max(pred.confidence_before,
                                                     causal_pred.get("confidence", 0.5))
                except Exception:
                    pass

        with self._lock:
            self._active_predictions.extend(predictions)

        elapsed = time.time() - t0
        print(f"[ScientificReasoning] predict(): {len(predictions)} predictions in {elapsed:.1f}s")
        return predictions

    # ── Phase 4: Test ───────────────────────────────────────────────────

    async def test(self, predictions: Optional[List[Prediction]] = None,
                   evidence: Optional[str] = None) -> List[Prediction]:
        """
        Test predictions against evidence.

        If evidence is provided, evaluate predictions against it.
        Otherwise, design experiments to test predictions.
        """
        t0 = time.time()
        predictions = predictions or self._active_predictions
        if not predictions:
            print("[ScientificReasoning] test(): no predictions to test")
            return []

        tested = []
        for pred in predictions[:MAX_HYPOTHESES_PER_CYCLE]:
            if evidence:
                # Evaluate prediction against provided evidence
                prompt = f"""A scientific prediction was made:
Prediction: "{pred.statement}"
Expected outcome: "{pred.expected_outcome}"
Test method: "{pred.test_method}"

New evidence observed:
{evidence[:3000]}

Evaluate:
1. Does the evidence CONFIRM, REFUTE, or leave INCONCLUSIVE the prediction?
2. What is the confidence in this evaluation (0.0-1.0)?
3. What specific aspects of the evidence are most relevant?

Return JSON:
- result: "confirmed" | "refuted" | "inconclusive"
- confidence: 0.0-1.0
- reasoning: why
- relevant_evidence: key evidence points"""

                raw = await self._llm(prompt, json_mode=True, max_tokens=2048)
                parsed = self._parse_json(raw)

                if isinstance(parsed, dict):
                    pred.actual_outcome = evidence[:500]
                    pred.result = parsed.get("result", "inconclusive")
                    pred.confidence_after = _sigmoid(float(parsed.get("confidence", 0.5)))
                    pred.tested = True
                    pred.tested_at = _timestamp()
                    tested.append(pred)

                    # Update hypothesis confidence
                    self._update_hypothesis_from_test(pred)
            else:
                # Design experiment to test this prediction
                prompt = f"""Design an experiment to test this prediction:
"{pred.statement}"
Expected: "{pred.expected_outcome}"
Method: "{pred.test_method}"

Provide:
- experiment_type: "computational" | "literature" | "logical" | "observational"
- steps: list of concrete steps
- success_criteria: what result confirms the prediction
- failure_criteria: what result refutes it
- estimated_time: rough time estimate

Return JSON."""

                raw = await self._llm(prompt, json_mode=True, max_tokens=2048)
                parsed = self._parse_json(raw)
                if isinstance(parsed, dict):
                    pred.test_method = json.dumps(parsed, indent=2)
                    tested.append(pred)

        elapsed = time.time() - t0
        print(f"[ScientificReasoning] test(): {len(tested)} predictions processed in {elapsed:.1f}s")
        return tested

    def _update_hypothesis_from_test(self, pred: Prediction):
        """Update hypothesis confidence based on test result."""
        with self._lock:
            for h in self._active_hypotheses:
                if h.id == pred.hypothesis_id:
                    if pred.result == "confirmed":
                        boost = (pred.confidence_after - pred.confidence_before) * 0.3
                        h.confidence = min(1.0, h.confidence + boost)
                        h.supporting_evidence.append({
                            "prediction_id": pred.id,
                            "result": pred.result,
                            "confidence": pred.confidence_after,
                            "timestamp": _timestamp(),
                        })
                    elif pred.result == "refuted":
                        penalty = (pred.confidence_before + 0.1) * 0.4
                        h.confidence = max(0.0, h.confidence - penalty)
                        h.contradicting_evidence.append({
                            "prediction_id": pred.id,
                            "result": pred.result,
                            "confidence": pred.confidence_after,
                            "timestamp": _timestamp(),
                        })
                    h.revised_at = _timestamp()
                    break

    # ── Phase 5: Revise ─────────────────────────────────────────────────

    async def revise(self, hypotheses: Optional[List[Hypothesis]] = None) -> List[Dict[str, Any]]:
        """
        Revise hypotheses based on accumulated evidence.

        Uses theory_formation engine for structured revision.
        """
        t0 = time.time()
        hypotheses = hypotheses or self._active_hypotheses
        revisions = []

        te = self._get_theory_engine()

        for h in hypotheses[:MAX_HYPOTHESES_PER_CYCLE]:
            if not h.supporting_evidence and not h.contradicting_evidence:
                continue

            # Calculate evidence balance
            support_strength = sum(e.get("confidence", 0.5) for e in h.supporting_evidence)
            contra_strength = sum(e.get("confidence", 0.5) for e in h.contradicting_evidence)
            evidence_ratio = support_strength / max(support_strength + contra_strength, 0.01)

            old_confidence = h.confidence

            if te:
                # Use theory formation engine for structured revision
                try:
                    theory = te.form_theories(
                        observations=[{
                            "phenomenon": h.statement,
                            "evidence": h.supporting_evidence + h.contradicting_evidence,
                        }],
                        domain=h.domain,
                    )
                    if theory:
                        h.confidence = theory[0].confidence if hasattr(theory[0], 'confidence') else evidence_ratio
                except Exception:
                    h.confidence = _sigmoid(evidence_ratio * 2 - 1)
            else:
                # Bayesian-style update
                prior = h.confidence
                likelihood = evidence_ratio
                h.confidence = _sigmoid(prior * likelihood / max((prior * likelihood + (1 - prior) * (1 - likelihood)), 0.01))

            h.revised_at = _timestamp()

            # LLM-assisted revision for significant changes
            if abs(h.confidence - old_confidence) > 0.15:
                prompt = f"""A scientific hypothesis has been revised based on evidence:

Original hypothesis: "{h.statement}"
Old confidence: {old_confidence:.2f}
New confidence: {h.confidence:.2f}
Supporting evidence: {len(h.supporting_evidence)} pieces
Contradicting evidence: {len(h.contradicting_evidence)} pieces

Provide a REVISED hypothesis that:
1. Accounts for the evidence
2. Preserves what's supported
3. Modifies what's contradicted
4. Identifies remaining gaps

Return JSON:
- revised_statement: the improved hypothesis
- changes: what changed and why
- remaining_uncertainties: what's still unknown"""

                raw = await self._llm(prompt, json_mode=True, max_tokens=2048)
                parsed = self._parse_json(raw)
                if isinstance(parsed, dict) and parsed.get("revised_statement"):
                    revisions.append({
                        "hypothesis_id": h.id,
                        "original": h.statement,
                        "revised": parsed["revised_statement"],
                        "changes": parsed.get("changes", ""),
                        "remaining_uncertainties": parsed.get("remaining_uncertainties", []),
                        "confidence_change": h.confidence - old_confidence,
                    })
                    h.statement = parsed["revised_statement"]

        elapsed = time.time() - t0
        print(f"[ScientificReasoning] revise(): {len(revisions)} revisions in {elapsed:.1f}s")
        return revisions

    # ── Phase 6: Theorize ───────────────────────────────────────────────

    async def theorize(self, hypotheses: Optional[List[Hypothesis]] = None,
                       domain: str = "general") -> List[Dict[str, Any]]:
        """
        Synthesize confirmed hypotheses into coherent theories.

        Uses theory_formation engine to merge compatible hypotheses
        and abstraction_engine to find unifying principles.
        """
        t0 = time.time()
        hypotheses = hypotheses or self._active_hypotheses

        # Filter to high-confidence hypotheses
        strong = [h for h in hypotheses if h.confidence >= 0.5]
        if not strong:
            print("[ScientificReasoning] theorize(): no strong hypotheses to theorize")
            return []

        theories = []
        te = self._get_theory_engine()

        if te:
            try:
                # Feed observations to theory formation engine
                observations = []
                for h in strong:
                    obs_entry = {
                        "phenomenon": h.statement,
                        "domain": h.domain,
                        "mechanisms": h.mechanisms,
                        "evidence": h.supporting_evidence,
                        "confidence": h.confidence,
                    }
                    observations.append(obs_entry)

                formed = te.form_theories(observations=observations, domain=domain)
                for theory in formed:
                    theories.append({
                        "name": theory.name if hasattr(theory, 'name') else "Synthesized Theory",
                        "mechanisms": theory.mechanisms if hasattr(theory, 'mechanisms') else [],
                        "predictions": theory.predictions if hasattr(theory, 'predictions') else [],
                        "confidence": theory.confidence if hasattr(theory, 'confidence') else 0.5,
                        "source_hypotheses": [h.id for h in strong],
                    })
            except Exception as e:
                print(f"[ScientificReasoning] theory formation error: {e}")

        # Use abstraction engine for unifying principles
        ae = self._get_abstraction_engine()
        if ae and len(strong) >= 2:
            try:
                concepts = [h.statement for h in strong[:5]]
                patterns = ae.find_common_patterns(concepts)
                if patterns:
                    theories.append({
                        "name": "Unifying Pattern",
                        "mechanisms": patterns if isinstance(patterns, list) else [str(patterns)],
                        "predictions": [],
                        "confidence": 0.4,
                        "source_hypotheses": [h.id for h in strong],
                        "type": "pattern_synthesis",
                    })
            except Exception:
                pass

        # LLM synthesis
        if len(strong) >= 2:
            hyp_descriptions = "\n".join(
                f"- [{h.id}] {h.statement} (confidence: {h.confidence:.2f})"
                for h in strong
            )
            prompt = f"""Synthesize these confirmed hypotheses into a coherent scientific theory:

{hyp_descriptions}

Create a UNIFIED theory that:
1. Explains all the hypotheses under one framework
2. Identifies the deep structure connecting them
3. Makes novel predictions beyond the individual hypotheses
4. Specifies boundary conditions

Return JSON:
- name: theory name
- description: full theory description
- unifying_principle: what connects the hypotheses
- mechanisms: list of causal mechanisms
- novel_predictions: predictions beyond the input hypotheses
- boundary_conditions: when does this theory apply
- confidence: 0.0-1.0"""

            raw = await self._llm(prompt, json_mode=True, max_tokens=4096)
            parsed = self._parse_json(raw)
            if isinstance(parsed, dict) and parsed.get("description"):
                theories.append({
                    "name": parsed.get("name", "LLM-Synthesized Theory"),
                    "description": parsed.get("description", ""),
                    "unifying_principle": parsed.get("unifying_principle", ""),
                    "mechanisms": parsed.get("mechanisms", []),
                    "novel_predictions": parsed.get("novel_predictions", []),
                    "boundary_conditions": parsed.get("boundary_conditions", []),
                    "confidence": _sigmoid(float(parsed.get("confidence", 0.5))),
                    "source_hypotheses": [h.id for h in strong],
                    "type": "llm_synthesis",
                })

        elapsed = time.time() - t0
        print(f"[ScientificReasoning] theorize(): {len(theories)} theories in {elapsed:.1f}s")
        return theories

    # ── Full Reasoning Cycle ────────────────────────────────────────────

    async def reason(self, topic: str, data: str = "", context: str = "",
                     domain: str = "general", evidence: str = "") -> ReasoningCycle:
        """
        Execute a complete scientific reasoning cycle:
        Observe → Hypothesize → Predict → Test → Revise → Theorize

        Args:
            topic: what we're investigating
            data: raw data/observations to analyze
            context: background context
            domain: scientific domain
            evidence: evidence for testing (if available)

        Returns:
            ReasoningCycle with all results from the cycle.
        """
        with self._lock:
            self._cycle_count += 1
            cycle_num = self._cycle_count

        cycle = ReasoningCycle(cycle_num, topic)
        self._topic_context = topic
        total_start = time.time()

        print(f"\n{'='*60}")
        print(f"[ScientificReasoning] CYCLE {cycle_num}: {topic}")
        print(f"{'='*60}")

        # Phase 1: Observe
        t = time.time()
        if data:
            observations = await self.observe(data, context, domain)
        else:
            # Use curiosity to generate observations from topic
            observations = await self.observe(topic, context, domain)
        cycle.phase_durations["observe"] = time.time() - t
        cycle.observations = [o.to_dict() for o in observations]

        # Phase 2: Hypothesize
        t = time.time()
        hypotheses = await self.hypothesize(observations, domain)
        cycle.phase_durations["hypothesize"] = time.time() - t
        cycle.hypotheses = [h.to_dict() for h in hypotheses]

        # Phase 3: Predict
        t = time.time()
        predictions = await self.predict(hypotheses)
        cycle.phase_durations["predict"] = time.time() - t
        cycle.predictions = [p.to_dict() for p in predictions]

        # Phase 4: Test (if evidence available)
        t = time.time()
        if evidence:
            tested = await self.test(predictions, evidence)
            cycle.phase_durations["test"] = time.time() - t

        # Phase 5: Revise
        t = time.time()
        revisions = await self.revise(hypotheses)
        cycle.phase_durations["revise"] = time.time() - t
        cycle.revisions = revisions

        # Phase 6: Theorize
        t = time.time()
        theories = await self.theorize(hypotheses, domain)
        cycle.phase_durations["theorize"] = time.time() - t
        cycle.theories_synthesized = theories

        # Calculate net confidence change
        if hypotheses:
            avg_initial = sum(h.confidence for h in hypotheses) / len(hypotheses)
            # After revision, recalculate
            revised_confidences = []
            for h in hypotheses:
                if h.supporting_evidence or h.contradicting_evidence:
                    revised_confidences.append(h.confidence)
            if revised_confidences:
                avg_final = sum(revised_confidences) / len(revised_confidences)
                cycle.confidence_delta = avg_final - avg_initial

        # Extract insights
        cycle.insights = self._extract_insights(observations, hypotheses, theories)

        cycle.completed_at = _timestamp()
        cycle.duration_s = time.time() - total_start

        # Store in history
        with self._lock:
            self._history.append(cycle)
            if len(self._history) > MAX_REASONING_HISTORY:
                self._history = self._history[-MAX_REASONING_HISTORY:]

        # Save state
        self._save_state()

        print(f"\n[ScientificReasoning] Cycle {cycle_num} complete in {cycle.duration_s:.1f}s")
        print(f"  Observations: {len(observations)}, Hypotheses: {len(hypotheses)}")
        print(f"  Predictions: {len(predictions)}, Theories: {len(theories)}")
        print(f"  Confidence delta: {cycle.confidence_delta:+.3f}")
        if cycle.insights:
            print(f"  Key insights: {len(cycle.insights)}")

        return cycle

    # ── Meta-cognition ──────────────────────────────────────────────────

    async def reflect(self, cycle: Optional[ReasoningCycle] = None) -> Dict[str, Any]:
        """
        Meta-cognitive review of reasoning quality.

        Evaluates the reasoning process itself, not just the results.
        """
        cycle = cycle or (self._history[-1] if self._history else None)
        if not cycle:
            return {"status": "no cycle to reflect on"}

        prompt = f"""Reflect on this scientific reasoning cycle:

Topic: {cycle.topic}
Observations: {len(cycle.observations)}
Hypotheses: {len(cycle.hypotheses)}
Predictions: {len(cycle.predictions)}
Theories: {len(cycle.theories_synthesized)}
Confidence delta: {cycle.confidence_delta:.3f}
Duration: {cycle.duration_s:.1f}s

Hypotheses generated:
{json.dumps([h.get('statement', '')[:100] for h in cycle.hypotheses[:5]], indent=2)}

Theories synthesized:
{json.dumps([t.get('name', '') for t in cycle.theories_synthesized[:3]], indent=2)}

Evaluate:
1. Were the observations sufficiently diverse and surprising?
2. Were hypotheses creative yet plausible?
3. Were predictions specific and testable?
4. Did the revision process actually improve understanding?
5. Do the theories represent genuine insight or just restatement?
6. What was the biggest weakness in this reasoning cycle?
7. What should be done differently next time?

Return JSON:
- overall_quality: 0.0-1.0
- strengths: list of what went well
- weaknesses: list of what could improve
- recommendations: specific improvements for next cycle
- meta_insight: one key insight about the reasoning process itself"""

        raw = await self._llm(prompt, json_mode=True, max_tokens=2048)
        parsed = self._parse_json(raw)

        reflection = parsed if isinstance(parsed, dict) else {
            "overall_quality": 0.5,
            "meta_insight": "Unable to parse reflection",
        }

        # Store insight
        if reflection.get("meta_insight"):
            with self._lock:
                self._insights.append(reflection["meta_insight"])

        return reflection

    # ── Utilities ───────────────────────────────────────────────────────

    def _extract_insights(self, observations, hypotheses, theories) -> List[str]:
        """Extract key insights from a reasoning cycle."""
        insights = []

        # High-anomaly observations
        for obs in observations:
            if obs.anomaly_score > 0.7:
                insights.append(f"High anomaly detected: {obs.phenomenon[:100]}")

        # High-confidence hypotheses
        for h in hypotheses:
            if h.confidence > 0.7:
                insights.append(f"Strong hypothesis: {h.statement[:100]}")

        # Novel theories
        for t in theories:
            if t.get("confidence", 0) > 0.6:
                insights.append(f"Theory formed: {t.get('name', 'Unnamed')}")

        return insights[:10]

    def _parse_json(self, raw: str) -> Any:
        """Robust JSON parsing from LLM output."""
        if not raw:
            return None
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0].strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to find JSON in the text
            for start_char, end_char in [('[', ']'), ('{', '}')]:
                start = raw.find(start_char)
                end = raw.rfind(end_char)
                if start != -1 and end != -1 and end > start:
                    try:
                        return json.loads(raw[start:end + 1])
                    except json.JSONDecodeError:
                        continue
            return None

    # ── Persistence ─────────────────────────────────────────────────────

    def _save_state(self):
        """Save reasoning state to disk."""
        try:
            state = {
                "cycle_count": self._cycle_count,
                "history": [c.to_dict() for c in self._history[-20:]],
                "insights": self._insights[-50:],
                "saved_at": _timestamp(),
            }
            STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
        except Exception as e:
            print(f"[ScientificReasoning] Save error: {e}")

    def _load_state(self):
        """Load reasoning state from disk."""
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text())
                self._cycle_count = data.get("cycle_count", 0)
                self._insights = data.get("insights", [])
        except Exception:
            pass

    @property
    def status(self) -> Dict[str, Any]:
        """Current status of the reasoning loop."""
        return {
            "cycle_count": self._cycle_count,
            "active_observations": len(self._active_observations),
            "active_hypotheses": len(self._active_hypotheses),
            "active_predictions": len(self._active_predictions),
            "total_insights": len(self._insights),
            "last_cycle": self._history[-1].to_dict() if self._history else None,
        }


# ── Module-level singleton ──────────────────────────────────────────────────

_instance: Optional[ScientificReasoningLoop] = None
_init_lock = threading.Lock()


def get_scientific_reasoning_loop(llm_fn=None) -> ScientificReasoningLoop:
    """Get or create the singleton ScientificReasoningLoop."""
    global _instance
    if _instance is None:
        with _init_lock:
            if _instance is None:
                _instance = ScientificReasoningLoop(llm_fn=llm_fn)
    return _instance
