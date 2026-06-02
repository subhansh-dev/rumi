"""
continuous_operation.py — RUMI runs forever, self-directed.

RUMI doesn't stop. It:
1. Picks its own research topics (curiosity-driven)
2. Discovers new hypotheses
3. Tests them
4. Evolves theories based on evidence
5. Learns from failures
6. Publishes results
7. Sleeps and wakes up smarter

This is the brain that makes RUMI autonomous.
"""

import json
import os
import time
import random
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path


# Research frontier — topics RUMI wants to explore
RESEARCH_FRONTIER = {
    "cosmology": [
        "Hubble tension resolution via early dark energy",
        "Dark energy equation of state w(z) deviation from -1",
        "Neutrino mass ordering from CMB lensing",
        "Primordial magnetic field generation mechanism",
        "Cosmic lithium problem resolution",
        "Dark matter self-interaction cross-section",
        "CMB anomaly at ell<30 (hemispherical asymmetry)",
        "Reionization optical depth tau tension",
        "Sigma-8 tension between CMB and weak lensing",
        "Baryon acoustic oscillation scale evolution",
    ],
    "particle_physics": [
        "Muon g-2 anomaly explanation",
        "Dark photon search strategy",
        "Sterile neutrino mass range",
        "Axion-like particle coupling bounds",
        "Proton radius puzzle resolution",
        "Neutron lifetime discrepancy",
        "Fifth force from dark sector",
        "Baryogenesis mechanism beyond leptogenesis",
    ],
    "materials_science": [
        "Room-temperature superconductor mechanism",
        "Topological insulator surface state stability",
        "Quantum spin liquid candidate materials",
        "Moiré flat band superconductivity",
        "2D material bandgap engineering",
        "Phonon engineering for thermoelectrics",
        "Defect engineering for quantum emitters",
        "Amorphous solid thermal transport",
    ],
    "biology": [
        "Origin of life: RNA world vs metabolism-first",
        "Protein folding speed limit",
        "Neural code: rate vs temporal",
        "Epigenetic inheritance mechanism",
        "Microbiome-brain axis signal pathway",
        "Aging: program vs damage accumulation",
        "Convergent evolution molecular basis",
        "Horizontal gene transfer frequency",
    ],
    "climate": [
        "Cloud feedback sign and magnitude",
        "Carbon cycle feedback sensitivity",
        "Tipping point interaction network",
        "Aerosol indirect effect magnitude",
        "Ocean heat uptake efficiency",
        "Permafrost thaw rate under warming",
        "Methane clathrate stability threshold",
        "Ice sheet collapse timescale",
    ],
    "information_theory": [
        "Quantum advantage boundary in computation",
        "Thermodynamic cost of computation minimum",
        "Consciousness: integrated information theory vs global workspace",
        "Language model emergence mechanism",
        "Scaling laws origin and limits",
        "Hallucination mechanism in transformers",
        "Mechanistic interpretability of circuits",
    ],
}


@dataclass
class ResearchState:
    """RUMI's current research state."""
    current_topic: str = ""
    current_domain: str = ""
    current_phase: str = "idle"  # idle, selecting, hypothesis, simulation, debate, publication
    hypotheses_tested: int = 0
    theories_accepted: int = 0
    theories_rejected: int = 0
    theories_revised: int = 0
    total_cycles: int = 0
    start_time: str = ""
    last_activity: str = ""
    topic_history: List[dict] = field(default_factory=list)
    discovery_log: List[dict] = field(default_factory=list)
    failure_log: List[dict] = field(default_factory=list)
    evolution_log: List[dict] = field(default_factory=list)


class CuriosityEngine:
    """
    RUMI's curiosity — decides what to research next.

    Uses a weighted random selection based on:
    - How many times each topic has been explored (less explored = more curious)
    - How recently each topic was explored (older = more curious)
    - How promising previous results were (more promising = more curious)
    - Random novelty factor (exploration)
    """

    def __init__(self):
        self.exploration_counts = {}  # topic -> count
        self.exploration_times = {}   # topic -> last_time
        self.promising_topics = {}    # topic -> score

    def select_topic(self, frontier: dict = None) -> tuple:
        """Select the next research topic."""
        frontier = frontier or RESEARCH_FRONTIER

        # Flatten all topics
        all_topics = []
        for domain, topics in frontier.items():
            for topic in topics:
                all_topics.append((domain, topic))

        # Compute weights
        weights = []
        for domain, topic in all_topics:
            key = f"{domain}:{topic}"

            # Base weight
            w = 1.0

            # Penalize frequently explored topics
            count = self.exploration_counts.get(key, 0)
            w *= 1.0 / (1.0 + count)

            # Boost unexplored topics
            if count == 0:
                w *= 2.0

            # Boost recently promising topics
            if key in self.promising_topics:
                w *= 1.0 + self.promising_topics[key]

            # Random novelty factor
            w *= random.uniform(0.5, 1.5)

            weights.append(max(0.01, w))

        # Weighted random selection
        total = sum(weights)
        r = random.uniform(0, total)
        cumulative = 0
        for i, (domain, topic) in enumerate(all_topics):
            cumulative += weights[i]
            if cumulative >= r:
                key = f"{domain}:{topic}"
                self.exploration_counts[key] = self.exploration_counts.get(key, 0) + 1
                self.exploration_times[key] = datetime.now().isoformat()
                return domain, topic

        # Fallback
        domain, topic = random.choice(all_topics)
        return domain, topic

    def update_promising(self, topic_key: str, score: float):
        """Update how promising a topic is."""
        self.promising_topics[topic_key] = score

    def get_stats(self) -> dict:
        """Get curiosity engine statistics."""
        return {
            "topics_explored": len(self.exploration_counts),
            "total_explorations": sum(self.exploration_counts.values()),
            "most_explored": max(self.exploration_counts.items(), key=lambda x: x[1])[0] if self.exploration_counts else None,
            "most_promising": max(self.promising_topics.items(), key=lambda x: x[1])[0] if self.promising_topics else None,
        }


class TheoryEvolution:
    """
    Tracks how theories evolve over time.

    Theories aren't static — they evolve:
    1. Initial hypothesis
    2. Critique identifies flaws
    3. Revision addresses flaws
    4. New evidence supports/refutes
    5. Final theory or rejection

    This tracks the full lineage.
    """

    def __init__(self):
        self.theories = {}  # theory_id -> lineage
        self.next_id = 1

    def create_theory(self, hypothesis: str, domain: str, source: str = "hypothesis") -> str:
        """Create a new theory entry."""
        theory_id = f"T{self.next_id:04d}"
        self.next_id += 1

        self.theories[theory_id] = {
            "id": theory_id,
            "domain": domain,
            "lineage": [{
                "version": 1,
                "hypothesis": hypothesis,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "score": 0.0,
                "verdict": "pending",
            }],
            "current_version": 1,
            "status": "active",
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }

        return theory_id

    def evolve_theory(self, theory_id: str, revision: str,
                      score: float, verdict: str, reason: str = "") -> dict:
        """Evolve a theory based on new evidence."""
        if theory_id not in self.theories:
            return {"error": f"Theory {theory_id} not found"}

        theory = self.theories[theory_id]
        version = theory["current_version"] + 1
        theory["current_version"] = version

        evolution_entry = {
            "version": version,
            "hypothesis": revision,
            "source": "debate_revision",
            "timestamp": datetime.now().isoformat(),
            "score": score,
            "verdict": verdict,
            "reason": reason,
        }

        theory["lineage"].append(evolution_entry)
        theory["last_updated"] = datetime.now().isoformat()

        if verdict == "accept":
            theory["status"] = "accepted"
        elif verdict == "reject":
            theory["status"] = "rejected"

        return evolution_entry

    def get_theory(self, theory_id: str) -> Optional[dict]:
        """Get theory by ID."""
        return self.theories.get(theory_id)

    def get_active_theories(self) -> List[dict]:
        """Get all active theories."""
        return [t for t in self.theories.values() if t["status"] == "active"]

    def get_best_theories(self, top_n: int = 10) -> List[dict]:
        """Get theories with highest scores."""
        scored = []
        for t in self.theories.values():
            latest = t["lineage"][-1]
            scored.append({
                "id": t["id"],
                "domain": t["domain"],
                "hypothesis": latest["hypothesis"],
                "score": latest["score"],
                "verdict": latest["verdict"],
                "versions": t["current_version"],
                "status": t["status"],
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]

    def get_stats(self) -> dict:
        """Get evolution statistics."""
        statuses = {}
        for t in self.theories.values():
            s = t["status"]
            statuses[s] = statuses.get(s, 0) + 1

        return {
            "total_theories": len(self.theories),
            "statuses": statuses,
            "avg_versions": sum(t["current_version"] for t in self.theories.values()) / max(1, len(self.theories)),
        }


class MemoryManager:
    """
    RUMI's long-term memory — persists across sessions.

    Stores:
    - Successful theories
    - Failed hypotheses (learn from failures)
    - Cross-domain analogies that worked
    - Research frontier updates
    - Performance metrics
    """

    def __init__(self, memory_dir: str = ""):
        self.memory_dir = memory_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "memory"
        )
        os.makedirs(self.memory_dir, exist_ok=True)

    def save_session(self, state: ResearchState, theories: dict, discoveries: list):
        """Save session state to disk."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_file = os.path.join(self.memory_dir, f"session_{timestamp}.json")

        data = {
            "timestamp": timestamp,
            "state": asdict(state),
            "theories": {k: v for k, v in theories.items()},
            "discoveries": discoveries,
        }

        with open(session_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        return session_file

    def load_latest_session(self) -> Optional[dict]:
        """Load the most recent session."""
        session_files = sorted([
            f for f in os.listdir(self.memory_dir) if f.startswith("session_")
        ], reverse=True)

        if not session_files:
            return None

        with open(os.path.join(self.memory_dir, session_files[0])) as f:
            return json.load(f)

    def save_discovery(self, discovery: dict):
        """Save a discovery to the knowledge base."""
        kb_file = os.path.join(self.memory_dir, "knowledge_base.jsonl")
        discovery["timestamp"] = datetime.now().isoformat()

        with open(kb_file, 'a') as f:
            f.write(json.dumps(discovery, default=str) + "\n")

    def get_discoveries(self, domain: str = "", min_score: float = 0) -> list:
        """Retrieve discoveries from knowledge base."""
        kb_file = os.path.join(self.memory_dir, "knowledge_base.jsonl")
        if not os.path.exists(kb_file):
            return []

        discoveries = []
        with open(kb_file) as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    if domain and d.get("domain") != domain:
                        continue
                    if d.get("score", 0) >= min_score:
                        discoveries.append(d)

        return discoveries

    def get_stats(self) -> dict:
        """Get memory statistics."""
        kb_file = os.path.join(self.memory_dir, "knowledge_base.jsonl")
        session_files = [f for f in os.listdir(self.memory_dir) if f.startswith("session_")]

        discoveries = 0
        if os.path.exists(kb_file):
            with open(kb_file) as f:
                discoveries = sum(1 for line in f if line.strip())

        return {
            "sessions_stored": len(session_files),
            "discoveries_stored": discoveries,
            "memory_dir": self.memory_dir,
        }


class ContinuousOperation:
    """
    The autonomous loop — RUMI runs forever.

    Each cycle:
    1. SELECT topic (curiosity engine)
    2. HYPOTHESIZE (LLM generates hypothesis)
    3. SIMULATE (Monte Carlo tests)
    4. DEBATE (multi-agent critique)
    5. EVOLVE (update theory)
    6. PUBLISH (save results)
    7. MEMORY (persist to disk)
    8. SLEEP (rate limit)
    9. REPEAT
    """

    def __init__(self, pipeline=None, memory_dir: str = ""):
        self.curiosity = CuriosityEngine()
        self.evolution = TheoryEvolution()
        self.memory = MemoryManager(memory_dir)
        self.pipeline = pipeline

        self.state = ResearchState(
            start_time=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat(),
        )

        self.running = False
        self.cycle_count = 0

    def run_cycle(self, llm_fn=None, paper_search_fn=None) -> dict:
        """
        Run one complete research cycle.

        Returns:
            {
                "cycle": int,
                "topic": str,
                "domain": str,
                "theory_id": str,
                "hypothesis": str,
                "simulation_score": float,
                "debate_verdict": str,
                "final_score": float,
                "verdict": str,
            }
        """
        self.cycle_count += 1
        self.state.total_cycles = self.cycle_count

        # 1. SELECT topic
        domain, topic = self.curiosity.select_topic()
        self.state.current_topic = topic
        self.state.current_domain = domain
        self.state.current_phase = "selecting"

        # 2. HYPOTHESIZE
        self.state.current_phase = "hypothesis"
        if self.pipeline and llm_fn:
            try:
                result = self.pipeline.run(topic, domain)
                hypothesis = result.get("hypothesis", f"Hypothesis about {topic}")
                literature = result.get("literature_context", {})
            except Exception as e:
                hypothesis = f"Hypothesis about {topic}: mechanism involves {domain} principles"
                literature = {}
        else:
            hypothesis = f"Hypothesis about {topic}"
            literature = {}

        # Create theory entry
        theory_id = self.evolution.create_theory(hypothesis, domain, "curiosity")

        # 3. SIMULATE
        self.state.current_phase = "simulation"
        simulation_score = 50.0
        simulation_result = {}

        if self.pipeline:
            try:
                from .simulation_pipeline import SimulationPipeline
                sim = SimulationPipeline()
                # Extract parameters from hypothesis
                params = self._extract_params_from_hypothesis(hypothesis)
                sim_result = sim.run(hypothesis, domain, params)
                simulation_score = sim_result.score
                simulation_result = {
                    "score": sim_result.score,
                    "predictions": sim_result.predictions,
                    "passed": sim_result.passed_consistency,
                }
            except Exception as e:
                simulation_result = {"error": str(e)}

        # 4. DEBATE
        self.state.current_phase = "debate"
        debate_verdict = "revise"
        debate_score = simulation_score

        if llm_fn:
            try:
                from .multi_agent_debate import MultiAgentDebate
                debate = MultiAgentDebate()
                debate_result = debate.run_debate(
                    hypothesis=hypothesis,
                    topic=topic,
                    literature=json.dumps(literature) if literature else "",
                    simulation=json.dumps(simulation_result),
                    llm_fn=llm_fn,
                )
                debate_verdict = debate_result.final_verdict
                debate_score = debate_result.synthesizer_score
            except Exception as e:
                debate_result = None

        # 5. EVOLVE
        self.state.current_phase = "evolution"
        final_score = (simulation_score + debate_score) / 2

        if debate_verdict == "accept":
            self.state.theories_accepted += 1
        elif debate_verdict == "reject":
            self.state.theories_rejected += 1
        else:
            self.state.theories_revised += 1

        self.evolution.evolve_theory(
            theory_id, hypothesis, final_score, debate_verdict,
            reason=f"Simulation: {simulation_score:.0f}, Debate: {debate_score:.0f}"
        )

        self.curiosity.update_promising(f"{domain}:{topic}", final_score / 100)

        # 6. PUBLISH
        self.state.current_phase = "publication"
        discovery = {
            "cycle": self.cycle_count,
            "topic": topic,
            "domain": domain,
            "theory_id": theory_id,
            "hypothesis": hypothesis,
            "simulation_score": simulation_score,
            "debate_verdict": debate_verdict,
            "final_score": final_score,
            "verdict": debate_verdict,
        }

        self.state.discovery_log.append(discovery)
        self.state.hypotheses_tested += 1

        # 7. MEMORY
        self.memory.save_discovery(discovery)
        self.state.last_activity = datetime.now().isoformat()
        self.state.current_phase = "idle"

        # Add to topic history
        self.state.topic_history.append({
            "cycle": self.cycle_count,
            "domain": domain,
            "topic": topic,
            "score": final_score,
            "verdict": debate_verdict,
            "timestamp": datetime.now().isoformat(),
        })

        return discovery

    def run_continuous(self, max_cycles: int = 100, llm_fn=None,
                       paper_search_fn=None, callback=None) -> dict:
        """
        Run continuous research loop.

        Args:
            max_cycles: Maximum number of cycles
            llm_fn: LLM function
            paper_search_fn: Paper search function
            callback: Called after each cycle with the result

        Returns:
            Summary statistics
        """
        self.running = True
        start = time.time()

        for i in range(max_cycles):
            if not self.running:
                break

            try:
                result = self.run_cycle(llm_fn, paper_search_fn)

                if callback:
                    callback(result)

                # Save state periodically
                if i % 10 == 0:
                    self.memory.save_session(
                        self.state,
                        self.evolution.theories,
                        self.state.discovery_log
                    )

            except Exception as e:
                self.state.failure_log.append({
                    "cycle": self.cycle_count,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })

        # Final save
        self.memory.save_session(
            self.state,
            self.evolution.theories,
            self.state.discovery_log
        )

        elapsed = time.time() - start

        return {
            "total_cycles": self.cycle_count,
            "elapsed_seconds": round(elapsed, 1),
            "hypotheses_tested": self.state.hypotheses_tested,
            "theories_accepted": self.state.theories_accepted,
            "theories_rejected": self.state.theories_rejected,
            "theories_revised": self.state.theories_revised,
            "best_theories": self.evolution.get_best_theories(5),
            "curiosity_stats": self.curiosity.get_stats(),
            "evolution_stats": self.evolution.get_stats(),
            "memory_stats": self.memory.get_stats(),
        }

    def stop(self):
        """Stop the continuous loop."""
        self.running = False

    def get_status(self) -> dict:
        """Get current status."""
        return {
            "running": self.running,
            "cycle": self.cycle_count,
            "phase": self.state.current_phase,
            "topic": self.state.current_topic,
            "domain": self.state.current_domain,
            "accepted": self.state.theories_accepted,
            "rejected": self.state.theories_rejected,
            "revised": self.state.theories_revised,
        }

    def _extract_params_from_hypothesis(self, hypothesis: str) -> dict:
        """Extract numeric parameters from hypothesis text."""
        import re
        params = {}
        # Look for patterns like "X = 123" or "X: 123"
        for match in re.finditer(r'(\w+)\s*[=:]\s*([\d.]+(?:e[+-]?\d+)?)', hypothesis):
            try:
                params[match.group(1)] = float(match.group(2))
            except ValueError:
                pass
        return params
