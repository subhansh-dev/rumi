#!/usr/bin/env python3
"""
discovery_orchestrator.py — RUMI Autonomous Discovery Orchestrator
=====================================================================

The master orchestrator that connects all scientific capabilities into
a Sakana-style autonomous discovery loop. Unlike the sequential
DiscoveryEngine in scientist/, this runs continuously, learns from
past discoveries, and adapts its strategy.

Inspired by:
  - Sakana AI Scientist v2 (agentic tree search)
  - Bengio's Scientist AI (world model + inference)
  - Open-ended learning systems

Architecture:
  DiscoveryOrchestrator
    ├── discover()           — full autonomous discovery cycle
    ├── explore_topic()      — deep-dive into a specific topic
    ├── compare_topics()     — cross-domain discovery
    ├── review_discoveries() — meta-review of past discoveries
    ├── prioritize_queue()   — intelligent topic prioritization
    ├── learn_from_history() — improve from past cycles
    └── status               — current orchestrator state

Connects:
  brain/scientific_reasoning.py — cognitive reasoning loop
  brain/theory_formation.py     — theory creation & evolution
  brain/causal_reasoner.py      — causal structure learning
  brain/world_model.py          — latent dynamics prediction
  brain/creativity_engine.py    — novel idea generation
  brain/abstraction_engine.py   — cross-domain transfer
  scientist/discovery_engine.py — Sakana-style pipeline
  discovery/hypothesis_engine.py — hypothesis generation
  discovery/hypothesis_tournament.py — tournament selection

Thread-safe. Persistent state in orchestrator_state.json.
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
STATE_FILE = BRAIN_DIR / "orchestrator_state.json"

# ── Configuration ───────────────────────────────────────────────────────────

MAX_QUEUE_SIZE = 50
MAX_DISCOVERY_HISTORY = 200
PRIORITY_DECAY_RATE = 0.95  # Unexplored topics gain priority over time
MIN_PRIORITY_FOR_DISCOVERY = 0.3
CROSS_DOMAIN_BONUS = 0.2  # Priority boost for cross-domain topics
NOVELTY_BOOST = 0.15  # Priority boost for novel areas
MAX_CONCURRENT_DISCOVERIES = 3


def _timestamp() -> str:
    return datetime.now().isoformat()


def _sigmoid(x: float) -> float:
    try:
        return 1.0 / (1.0 + math.exp(-max(-10, min(10, x))))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def _safe_import(module_path: str, class_name: str):
    """Import with graceful fallback."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, class_name)
    except Exception:
        return None


# ── Data Structures ─────────────────────────────────────────────────────────


class DiscoveryTask:
    """A queued discovery task with priority and metadata."""

    def __init__(self, topic: str, domain: str = "general", priority: float = 0.5):
        self.id = str(uuid.uuid4())[:8]
        self.topic = topic
        self.domain = domain
        self.priority = priority
        self.attempts: int = 0
        self.max_attempts: int = 3
        self.status: str = "queued"  # queued | running | completed | failed
        self.results: Optional[Dict[str, Any]] = None
        self.created_at = _timestamp()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id, "topic": self.topic, "domain": self.domain,
            "priority": round(self.priority, 3), "attempts": self.attempts,
            "status": self.status, "created_at": self.created_at,
            "started_at": self.started_at, "completed_at": self.completed_at,
            "error": self.error,
        }


class DiscoveryResult:
    """Result of a complete discovery cycle."""

    def __init__(self, task_id: str, topic: str):
        self.id = str(uuid.uuid4())[:8]
        self.task_id = task_id
        self.topic = topic
        self.observations: List[dict] = []
        self.hypotheses: List[dict] = []
        self.theories: List[dict] = []
        self.predictions: List[dict] = []
        self.confidence: float = 0.0
        self.novelty_score: float = 0.0
        self.insights: List[str] = []
        self.duration_s: float = 0.0
        self.phase_results: Dict[str, Any] = {}
        self.created_at = _timestamp()

    def to_dict(self) -> dict:
        return {
            "id": self.id, "task_id": self.task_id, "topic": self.topic,
            "observations": len(self.observations),
            "hypotheses": len(self.hypotheses),
            "theories": len(self.theories),
            "predictions": len(self.predictions),
            "confidence": round(self.confidence, 3),
            "novelty_score": round(self.novelty_score, 3),
            "insights": self.insights,
            "duration_s": round(self.duration_s, 2),
            "phase_results": self.phase_results,
            "created_at": self.created_at,
        }


class DiscoveryReport:
    """Aggregated report across multiple discovery cycles."""

    def __init__(self):
        self.total_discoveries: int = 0
        self.successful_discoveries: int = 0
        self.failed_discoveries: int = 0
        self.total_theories: int = 0
        self.total_hypotheses: int = 0
        self.avg_confidence: float = 0.0
        self.avg_novelty: float = 0.0
        self.top_insights: List[str] = []
        self.domain_coverage: Dict[str, int] = defaultdict(int)
        self.generated_at = _timestamp()


# ── Discovery Orchestrator ──────────────────────────────────────────────────


class DiscoveryOrchestrator:
    """
    Master orchestrator for autonomous scientific discovery.

    Manages a queue of discovery topics, runs them through the full
    scientific reasoning pipeline, learns from results, and adapts
    strategy over time.
    """

    def __init__(self, llm_fn=None):
        self._lock = threading.RLock()
        self._llm_fn = llm_fn
        self._queue: List[DiscoveryTask] = []
        self._history: List[DiscoveryResult] = []
        self._total_discoveries: int = 0
        self._total_theories: int = 0
        self._total_hypotheses: int = 0
        self._running_task: Optional[DiscoveryTask] = None

        # Brain module references (lazy-loaded)
        self._reasoning_loop = None
        self._theory_engine = None
        self._discovery_engine = None

        self._load_state()
        # print(f"[DiscoveryOrchestrator] Initialized ({self._total_discoveries} prior discoveries)")

    # ── Brain Module Access ─────────────────────────────────────────────

    def _get_reasoning_loop(self):
        if self._reasoning_loop is None:
            cls = _safe_import("brain.scientific_reasoning", "ScientificReasoningLoop")
            if cls:
                self._reasoning_loop = cls(llm_fn=self._llm_fn)
        return self._reasoning_loop

    def _get_theory_engine(self):
        if self._theory_engine is None:
            cls = _safe_import("brain.theory_formation", "TheoryFormationEngine")
            if cls:
                self._theory_engine = cls()
        return self._theory_engine

    def _get_discovery_engine(self):
        if self._discovery_engine is None:
            cls = _safe_import("scientist.discovery_engine", "DiscoveryEngine")
            if cls:
                self._discovery_engine = cls()
        return self._discovery_engine

    async def _llm(self, prompt: str, **kwargs) -> str:
        """Call LLM with graceful fallback."""
        if self._llm_fn:
            return await self._llm_fn(prompt, **kwargs)
        try:
            from discovery.pipeline import LLMStage
            stage = LLMStage("orchestrator", max_retries=2,
                             backoff=[3, 8], providers=["groq", "gemini"])
            result, _ = await stage.call_with_retry(prompt, **kwargs)
            return result or ""
        except Exception:
            return ""

    # ── Queue Management ────────────────────────────────────────────────

    def enqueue(self, topic: str, domain: str = "general", priority: float = 0.5) -> str:
        """Add a discovery topic to the queue. Returns task ID."""
        with self._lock:
            if len(self._queue) >= MAX_QUEUE_SIZE:
                # Remove lowest priority item
                self._queue.sort(key=lambda t: t.priority)
                self._queue.pop(0)

            task = DiscoveryTask(topic, domain, priority)
            self._queue.append(task)
            self._queue.sort(key=lambda t: t.priority, reverse=True)
            return task.id

    def dequeue(self) -> Optional[DiscoveryTask]:
        """Get the highest priority task from the queue."""
        with self._lock:
            if not self._queue:
                return None
            task = self._queue.pop(0)
            task.status = "running"
            task.started_at = _timestamp()
            self._running_task = task
            return task

    def complete_task(self, task_id: str, result: Optional[DiscoveryResult] = None):
        """Mark a task as completed."""
        with self._lock:
            if self._running_task and self._running_task.id == task_id:
                self._running_task.status = "completed"
                self._running_task.completed_at = _timestamp()
                self._running_task.results = result.to_dict() if result else None
                self._running_task = None

    def fail_task(self, task_id: str, error: str):
        """Mark a task as failed."""
        with self._lock:
            if self._running_task and self._running_task.id == task_id:
                self._running_task.status = "failed"
                self._running_task.error = error
                self._running_task.attempts += 1
                # Re-queue if under max attempts
                if self._running_task.attempts < self._running_task.max_attempts:
                    self._running_task.priority *= 0.8  # Slight priority decrease
                    self._running_task.status = "queued"
                    self._queue.append(self._running_task)
                    self._queue.sort(key=lambda t: t.priority, reverse=True)
                self._running_task = None

    # ── Core Discovery ──────────────────────────────────────────────────

    async def discover(self, topic: str, domain: str = "general",
                       data: str = "", context: str = "") -> DiscoveryResult:
        """
        Run a complete autonomous discovery cycle on a topic.

        This is the main entry point. It:
        1. Runs scientific reasoning (observe → hypothesize → predict → test → revise → theorize)
        2. Optionally runs the Sakana-style discovery pipeline
        3. Synthesizes results from both approaches
        4. Learns from the outcome
        """
        task = DiscoveryTask(topic, domain)
        task.status = "running"
        task.started_at = _timestamp()

        result = DiscoveryResult(task.id, topic)
        total_start = time.time()

        print(f"\n{'='*60}")
        print(f"[DiscoveryOrchestrator] DISCOVERY: {topic}")
        print(f"{'='*60}")

        # ── Phase 1: Scientific Reasoning Loop ──
        try:
            reasoning = self._get_reasoning_loop()
            if reasoning:
                cycle = await reasoning.reason(
                    topic=topic, data=data, context=context, domain=domain,
                )
                result.observations = cycle.observations
                result.hypotheses = cycle.hypotheses
                result.theories = cycle.theories_synthesized
                result.predictions = cycle.predictions
                result.insights.extend(cycle.insights)
                result.phase_results["reasoning"] = {
                    "observations": len(cycle.observations),
                    "hypotheses": len(cycle.hypotheses),
                    "theories": len(cycle.theories_synthesized),
                    "duration": cycle.duration_s,
                }
                print(f"  Reasoning: {len(cycle.hypotheses)} hypotheses, {len(cycle.theories_synthesized)} theories")
        except Exception as e:
            result.phase_results["reasoning_error"] = str(e)
            print(f"  Reasoning error: {e}")

        # ── Phase 2: Sakana-style Discovery Pipeline ──
        try:
            de = self._get_discovery_engine()
            if de:
                pipeline_result = de.run_discovery(
                    topic=topic,
                    hypothesis=result.hypotheses[0].get("statement", "") if result.hypotheses else "",
                    run_experiments=True,
                    generate_paper=False,  # Don't auto-generate papers in orchestrator
                    verbose=False,
                )
                result.phase_results["pipeline"] = {
                    "novelty": pipeline_result.get("novelty_check", {}).get("novelty_score", 0),
                    "feynman": bool(pipeline_result.get("feynman_reduction")),
                    "research_team": bool(pipeline_result.get("research_team_session")),
                    "experiment": bool(pipeline_result.get("experiment_result")),
                    "peer_review": bool(pipeline_result.get("peer_review")),
                }
                # Merge insights
                if pipeline_result.get("discoveries"):
                    for d in pipeline_result["discoveries"]:
                        if d.get("insight"):
                            result.insights.append(d["insight"])
                print(f"  Pipeline: novelty={pipeline_result.get('novelty_check', {}).get('novelty_score', 'N/A')}")
        except Exception as e:
            result.phase_results["pipeline_error"] = str(e)
            print(f"  Pipeline error: {e}")

        # ── Phase 3: Theory Synthesis ──
        try:
            te = self._get_theory_engine()
            if te and result.observations:
                theories = te.form_theories(
                    observations=result.observations,
                    domain=domain,
                )
                for theory in theories:
                    result.theories.append({
                        "name": theory.name if hasattr(theory, 'name') else "Theory",
                        "mechanisms": theory.mechanisms if hasattr(theory, 'mechanisms') else [],
                        "confidence": theory.confidence if hasattr(theory, 'confidence') else 0.5,
                        "source": "theory_formation",
                    })
                print(f"  Theory synthesis: {len(theories)} theories formed")
        except Exception as e:
            result.phase_results["synthesis_error"] = str(e)
            print(f"  Synthesis error: {e}")

        # ── Phase 4: Meta-analysis ──
        if result.hypotheses and result.theories:
            try:
                meta = await self._meta_analyze(result)
                result.insights.extend(meta.get("meta_insights", []))
                result.novelty_score = meta.get("novelty_score", 0.5)
                result.confidence = meta.get("overall_confidence", 0.5)
            except Exception as e:
                result.phase_results["meta_error"] = str(e)

        # Calculate final metrics
        result.duration_s = time.time() - total_start
        if result.hypotheses:
            confidences = [h.get("confidence", 0.5) for h in result.hypotheses]
            result.confidence = sum(confidences) / len(confidences)

        # Store result
        with self._lock:
            self._history.append(result)
            if len(self._history) > MAX_DISCOVERY_HISTORY:
                self._history = self._history[-MAX_DISCOVERY_HISTORY:]
            self._total_discoveries += 1
            self._total_theories += len(result.theories)
            self._total_hypotheses += len(result.hypotheses)

        # Complete task
        task.status = "completed"
        task.completed_at = _timestamp()
        task.results = result.to_dict()

        # Save state
        self._save_state()

        print(f"\n[DiscoveryOrchestrator] Complete in {result.duration_s:.1f}s")
        print(f"  Observations: {len(result.observations)}")
        print(f"  Hypotheses: {len(result.hypotheses)}")
        print(f"  Theories: {len(result.theories)}")
        print(f"  Insights: {len(result.insights)}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Novelty: {result.novelty_score:.3f}")

        return result

    async def explore_topic(self, topic: str, depth: int = 3,
                            domain: str = "general") -> List[DiscoveryResult]:
        """
        Deep-dive exploration of a topic with multiple discovery cycles.

        Each cycle builds on the insights from previous cycles, going
        progressively deeper into the topic.
        """
        results = []
        context = ""
        accumulated_insights = []

        for i in range(depth):
            print(f"\n[DiscoveryOrchestrator] Explore depth {i+1}/{depth}: {topic}")

            # Build context from previous cycles
            if accumulated_insights:
                context = "Previous insights:\n" + "\n".join(
                    f"- {ins}" for ins in accumulated_insights[-10:]
                )

            result = await self.discover(topic, domain, context=context)
            results.append(result)
            accumulated_insights.extend(result.insights)

            # If confidence is very high, we've likely converged
            if result.confidence > 0.85:
                print(f"  High confidence ({result.confidence:.2f}) — converged at depth {i+1}")
                break

            # If no new insights, stop
            if not result.insights and i > 0:
                print(f"  No new insights at depth {i+1} — stopping")
                break

        return results

    async def compare_topics(self, topics: List[str],
                             domain: str = "general") -> Dict[str, Any]:
        """
        Cross-domain discovery: run discovery on multiple topics and
        find connections between them.
        """
        results = {}
        for topic in topics:
            results[topic] = await self.discover(topic, domain)

        # Find cross-domain connections
        connections = []
        if len(topics) >= 2:
            try:
                ae = _safe_import("brain.abstraction_engine", "AbstractionEngine")
                if ae:
                    engine = ae()
                    for i, t1 in enumerate(topics):
                        for t2 in topics[i+1:]:
                            analogies = engine.find_analogies(t1, target_domain=t2)
                            if analogies:
                                connections.append({
                                    "topic_1": t1, "topic_2": t2,
                                    "analogies": analogies,
                                })
            except Exception:
                pass

        return {
            "results": {k: v.to_dict() for k, v in results.items()},
            "connections": connections,
            "total_theories": sum(len(r.theories) for r in results.values()),
            "total_insights": sum(len(r.insights) for r in results.values()),
        }

    async def _meta_analyze(self, result: DiscoveryResult) -> Dict[str, Any]:
        """Meta-analysis of discovery results."""
        hyp_descriptions = "\n".join(
            f"- {h.get('statement', '')[:100]} (conf: {h.get('confidence', 0.5):.2f})"
            for h in result.hypotheses[:5]
        )
        theory_descriptions = "\n".join(
            f"- {t.get('name', 'Theory')}: {t.get('description', '')[:100]}"
            for t in result.theories[:3]
        )

        prompt = f"""Meta-analyze this discovery cycle:

Topic: {result.topic}
Hypotheses generated:
{hyp_descriptions or 'None'}

Theories synthesized:
{theory_descriptions or 'None'}

Evaluate:
1. How novel are these findings? (0.0-1.0)
2. How confident should we be in the overall findings? (0.0-1.0)
3. What are the key meta-insights about the discovery process itself?
4. What should be explored next?

Return JSON:
- novelty_score: 0.0-1.0
- overall_confidence: 0.0-1.0
- meta_insights: list of insights about the process
- next_steps: suggested follow-up topics"""

        raw = await self._llm(prompt, json_mode=True, max_tokens=2048)
        parsed = self._parse_json(raw)
        return parsed if isinstance(parsed, dict) else {
            "novelty_score": 0.5, "overall_confidence": 0.5,
            "meta_insights": [], "next_steps": [],
        }

    # ── Priority Management ─────────────────────────────────────────────

    def prioritize_queue(self):
        """Re-prioritize the queue based on accumulated knowledge."""
        with self._lock:
            for task in self._queue:
                # Boost priority for topics we haven't explored
                explored = any(
                    r.topic.lower() == task.topic.lower()
                    for r in self._history
                )
                if not explored:
                    task.priority = min(1.0, task.priority + NOVELTY_BOOST)

                # Boost cross-domain topics
                if task.domain == "cross_domain":
                    task.priority = min(1.0, task.priority + CROSS_DOMAIN_BONUS)

                # Time-based priority recovery
                age_hours = (time.time() - datetime.fromisoformat(task.created_at).timestamp()) / 3600
                task.priority = min(1.0, task.priority * (1 + age_hours * 0.01))

            self._queue.sort(key=lambda t: t.priority, reverse=True)

    def learn_from_history(self):
        """Analyze past discoveries to improve future strategy."""
        if len(self._history) < 3:
            return

        # Calculate domain success rates
        domain_success = defaultdict(lambda: {"total": 0, "confidence_sum": 0.0})
        for r in self._history:
            domain = "general"  # Could extract from topic
            domain_success[domain]["total"] += 1
            domain_success[domain]["confidence_sum"] += r.confidence

        # Identify high-value topic patterns
        high_conf = [r for r in self._history if r.confidence > 0.7]
        low_conf = [r for r in self._history if r.confidence < 0.3]

        print(f"[DiscoveryOrchestrator] Learning: {len(high_conf)} high-conf, {len(low_conf)} low-conf discoveries")

    # ── Utilities ───────────────────────────────────────────────────────

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
        """Save orchestrator state to disk."""
        try:
            state = {
                "total_discoveries": self._total_discoveries,
                "total_theories": self._total_theories,
                "total_hypotheses": self._total_hypotheses,
                "queue": [t.to_dict() for t in self._queue],
                "recent_history": [r.to_dict() for r in self._history[-20:]],
                "saved_at": _timestamp(),
            }
            STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
        except Exception as e:
            print(f"[DiscoveryOrchestrator] Save error: {e}")

    def _load_state(self):
        """Load orchestrator state from disk."""
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text())
                self._total_discoveries = data.get("total_discoveries", 0)
                self._total_theories = data.get("total_theories", 0)
                self._total_hypotheses = data.get("total_hypotheses", 0)
                # Reconstruct queue
                for t in data.get("queue", []):
                    task = DiscoveryTask(t["topic"], t.get("domain", "general"), t.get("priority", 0.5))
                    task.id = t["id"]
                    task.status = t.get("status", "queued")
                    self._queue.append(task)
        except Exception:
            pass

    @property
    def status(self) -> Dict[str, Any]:
        """Current orchestrator status."""
        return {
            "total_discoveries": self._total_discoveries,
            "total_theories": self._total_theories,
            "total_hypotheses": self._total_hypotheses,
            "queue_size": len(self._queue),
            "running_task": self._running_task.to_dict() if self._running_task else None,
            "recent_discoveries": len(self._history),
        }

    def get_report(self) -> DiscoveryReport:
        """Generate an aggregated report of all discoveries."""
        report = DiscoveryReport()
        report.total_discoveries = self._total_discoveries
        report.total_theories = self._total_theories
        report.total_hypotheses = self._total_hypotheses

        if self._history:
            confidences = [r.confidence for r in self._history]
            novelties = [r.novelty_score for r in self._history]
            report.avg_confidence = sum(confidences) / len(confidences)
            report.avg_novelty = sum(novelties) / len(novelties)

            # Collect top insights
            all_insights = []
            for r in self._history:
                all_insights.extend(r.insights)
            report.top_insights = all_insights[:20]

            report.successful_discoveries = sum(1 for r in self._history if r.confidence > 0.5)
            report.failed_discoveries = sum(1 for r in self._history if r.confidence < 0.3)

        return report


# ── Module-level singleton ──────────────────────────────────────────────────

_instance: Optional[DiscoveryOrchestrator] = None
_init_lock = threading.Lock()


def get_discovery_orchestrator(llm_fn=None) -> DiscoveryOrchestrator:
    """Get or create the singleton DiscoveryOrchestrator."""
    global _instance
    if _instance is None:
        with _init_lock:
            if _instance is None:
                _instance = DiscoveryOrchestrator(llm_fn=llm_fn)
    return _instance
