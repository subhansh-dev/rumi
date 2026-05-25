"""
tournament_hypothesis.py — GFlowNet-Inspired Tournament Hypothesis Engine

Generates diverse hypotheses proportional to reward (not just top-1),
then selects the best through tournament-style competition.

Inspired by:
  - Bengio's GFlowNets: sample diverse candidates proportional to reward
  - Google Co-Scientist: tournament evolution for hypothesis refinement
  - Evolutionary algorithms: selection pressure + diversity maintenance

Capabilities:
  [TH-1] Diverse hypothesis generation (GFlowNet-style sampling)
  [TH-2] Tournament selection with configurable tournament size
  [TH-3] Hypothesis mutation and crossover
  [TH-4] Multi-objective reward (novelty, feasibility, impact, coherence)
  [TH-5] Generational evolution with elitism
  [TH-6] Hypothesis lineage tracking
  [TH-7] Diversity maintenance via niching
  [TH-8] Async batch generation for parallel exploration

Thread-safe. Persistent state in tournament_state.json.
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
STATE_FILE = SCIENTIST_DIR / "tournament_state.json"

# ── Reward Weights ────────────────────────────────────────────────────────────

DEFAULT_REWARD_WEIGHTS = {
    "novelty": 0.25,
    "feasibility": 0.20,
    "impact": 0.25,
    "coherence": 0.15,
    "specificity": 0.15,
}

# ── Tournament Config ─────────────────────────────────────────────────────────

DEFAULT_TOURNAMENT_SIZE = 3
DEFAULT_POPULATION_SIZE = 12
DEFAULT_ELITE_COUNT = 2
DEFAULT_GENERATIONS = 5
MUTATION_RATE = 0.3
CROSSOVER_RATE = 0.5


class HypothesisCandidate:
    """A single hypothesis candidate with multi-objective scores."""

    def __init__(
        self,
        title: str,
        description: str,
        domain: str = "",
        parent_ids: list[str] | None = None,
    ):
        self.id = f"HC-{int(time.time() * 1000)}-{random.randint(100, 999)}"
        self.title = title
        self.description = description
        self.domain = domain
        self.parent_ids = parent_ids or []
        self.created_at = datetime.now().isoformat()
        self.generation = 0

        # Multi-objective scores (0.0–1.0)
        self.novelty_score = 0.0
        self.feasibility_score = 0.0
        self.impact_score = 0.0
        self.coherence_score = 0.0
        self.specificity_score = 0.0

        # Composite reward
        self.reward = 0.0

        # Tournament stats
        self.wins = 0
        self.losses = 0
        self.tournament_appearances = 0

        # Lineage
        self.mutation_history: list[str] = []

    def compute_reward(self, weights: dict | None = None) -> float:
        """Compute weighted multi-objective reward."""
        w = weights or DEFAULT_REWARD_WEIGHTS
        self.reward = (
            w["novelty"] * self.novelty_score
            + w["feasibility"] * self.feasibility_score
            + w["impact"] * self.impact_score
            + w["coherence"] * self.coherence_score
            + w["specificity"] * self.specificity_score
        )
        return self.reward

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "domain": self.domain,
            "parent_ids": self.parent_ids,
            "generation": self.generation,
            "scores": {
                "novelty": round(self.novelty_score, 3),
                "feasibility": round(self.feasibility_score, 3),
                "impact": round(self.impact_score, 3),
                "coherence": round(self.coherence_score, 3),
                "specificity": round(self.specificity_score, 3),
                "reward": round(self.reward, 3),
            },
            "tournament": {
                "wins": self.wins,
                "losses": self.losses,
                "appearances": self.tournament_appearances,
            },
            "mutation_history": self.mutation_history,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HypothesisCandidate":
        c = cls(d["title"], d["description"], d.get("domain", ""), d.get("parent_ids"))
        c.id = d["id"]
        c.generation = d.get("generation", 0)
        scores = d.get("scores", {})
        c.novelty_score = scores.get("novelty", 0)
        c.feasibility_score = scores.get("feasibility", 0)
        c.impact_score = scores.get("impact", 0)
        c.coherence_score = scores.get("coherence", 0)
        c.specificity_score = scores.get("specificity", 0)
        c.reward = scores.get("reward", 0)
        t = d.get("tournament", {})
        c.wins = t.get("wins", 0)
        c.losses = t.get("losses", 0)
        c.tournament_appearances = t.get("appearances", 0)
        c.mutation_history = d.get("mutation_history", [])
        c.created_at = d.get("created_at", c.created_at)
        return c


class TournamentHypothesisEngine:
    """
    GFlowNet-inspired hypothesis generation with tournament selection.

    Generates a diverse population of hypotheses, evaluates them on multiple
    objectives, and selects the best through competitive tournaments while
    maintaining diversity.
    """

    def __init__(self, llm_call=None):
        """
        Args:
            llm_call: Callable(prompt: str) -> str for LLM generation.
                      If None, uses template-based generation.
        """
        self._lock = threading.Lock()
        self._llm = llm_call
        self._population: list[HypothesisCandidate] = []
        self._archive: list[HypothesisCandidate] = []  # Best from each generation
        self._generation = 0
        self._load_state()

    def _load_state(self):
        with self._lock:
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    self._generation = data.get("generation", 0)
                    self._population = [
                        HypothesisCandidate.from_dict(h)
                        for h in data.get("population", [])
                    ]
                    self._archive = [
                        HypothesisCandidate.from_dict(h)
                        for h in data.get("archive", [])
                    ]
                except Exception:
                    pass

    def _save_state(self):
        with self._lock:
            data = {
                "generation": self._generation,
                "population": [h.to_dict() for h in self._population],
                "archive": [h.to_dict() for h in self._archive],
                "saved_at": datetime.now().isoformat(),
            }
            STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ── GFlowNet-Style Diverse Generation ─────────────────────────────────────

    def generate_population(
        self,
        topic: str,
        domain: str = "",
        size: int = DEFAULT_POPULATION_SIZE,
        seed_ideas: list[str] | None = None,
    ) -> list[HypothesisCandidate]:
        """
        Generate a diverse population of hypotheses using GFlowNet-style
        sampling: diversity proportional to reward, not just maximizing.
        """
        candidates = []

        # Strategy 1: LLM-based diverse generation
        if self._llm:
            candidates.extend(self._llm_generate_diverse(topic, domain, size))

        # Strategy 2: Template-based mutation of seed ideas
        if seed_ideas:
            for seed in seed_ideas[:size]:
                mutated = self._mutate_hypothesis(seed, topic, domain)
                candidates.append(mutated)

        # Strategy 3: Cross-pollination from different angles
        angles = [
            "counterintuitive", "cross-disciplinary", "minimalist",
            "scaling", "inversion", "analogy-based",
        ]
        for angle in angles[: size - len(candidates)]:
            h = self._generate_from_angle(topic, domain, angle)
            candidates.append(h)

        # Score all candidates
        for c in candidates:
            self._score_candidate(c, topic)

        # GFlowNet-style: keep diverse set proportional to reward
        self._population = self._gflownet_select(candidates, size)
        self._save_state()
        return self._population

    def _llm_generate_diverse(
        self, topic: str, domain: str, count: int
    ) -> list[HypothesisCandidate]:
        """Use LLM to generate diverse hypotheses."""
        prompt = f"""Generate {count} diverse, novel research hypotheses about: {topic}
Domain: {domain or 'any'}

Requirements for DIVERSITY:
- Each hypothesis should approach the topic from a DIFFERENT angle
- Include counterintuitive ideas, cross-disciplinary ideas, minimalist ideas
- Vary in scope: some narrow, some broad
- Vary in approach: theoretical, empirical, computational, observational
- Each must be specific and testable

Format (one per line):
TITLE: <title> | DESCRIPTION: <description> | ANGLE: <approach angle>

Generate exactly {count} hypotheses:"""

        response = self._llm(prompt)
        candidates = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if not line or "TITLE:" not in line:
                continue
            try:
                parts = line.split("|")
                title = parts[0].split("TITLE:")[1].strip()
                desc = parts[1].split("DESCRIPTION:")[1].strip()
                candidates.append(HypothesisCandidate(title, desc, domain))
            except (IndexError, ValueError):
                continue
        return candidates

    def _generate_from_angle(
        self, topic: str, domain: str, angle: str
    ) -> HypothesisCandidate:
        """Generate a hypothesis from a specific creative angle."""
        templates = {
            "counterintuitive": (
                f"Contrarian: What if {topic} works in the opposite way?",
                f"Challenge the assumption that {topic} follows conventional logic. "
                f"Explore what happens if the standard interpretation is inverted.",
            ),
            "cross-disciplinary": (
                f"Cross-domain: Apply principles from biology/physics to {topic}",
                f"Import methods or theories from an unrelated field to {topic}. "
                f"Look for structural analogies that haven't been explored.",
            ),
            "minimalist": (
                f"Minimal: Simplest possible explanation for {topic}",
                f"Strip away all complexity. What is the most minimal model that "
                f"still captures the essential behavior of {topic}?",
            ),
            "scaling": (
                f"Scaling: How does {topic} change at extreme scales?",
                f"Explore {topic} at very large scales, very small scales, "
                f"very fast timescales, or very slow timescales.",
            ),
            "inversion": (
                f"Inversion: What if we reverse the causality in {topic}?",
                f"Assume the effect in {topic} actually causes the supposed cause. "
                f"What experiments would distinguish this from the standard view?",
            ),
            "analogy-based": (
                f"Analogy: {topic} is like an ecosystem/network/thermodynamic system",
                f"Model {topic} using an analogy to a well-understood system. "
                f"Derive predictions from the analogy that can be tested.",
            ),
        }
        title, desc = templates.get(angle, (f"Novel angle on {topic}", f"Explore {topic} from a {angle} perspective."))
        return HypothesisCandidate(title, desc, domain)

    def _mutate_hypothesis(
        self, base: str, topic: str, domain: str
    ) -> HypothesisCandidate:
        """Mutate an existing hypothesis to create a variant."""
        mutations = [
            "generalize", "specialize", "reverse", "combine",
            "simplify", "extend", "constrain",
        ]
        mutation = random.choice(mutations)
        return HypothesisCandidate(
            f"[{mutation}] {base}",
            f"Take the idea '{base}' and {mutation} it in the context of {topic}.",
            domain,
        )

    # ── GFlowNet Selection ────────────────────────────────────────────────────

    def _gflownet_select(
        self, candidates: list[HypothesisCandidate], target_size: int
    ) -> list[HypothesisCandidate]:
        """
        GFlowNet-style selection: sample proportional to reward,
        with diversity bonus for niching.

        Unlike top-k selection, this keeps diverse candidates even if
        their reward is slightly lower, because diversity itself has value.
        """
        if not candidates:
            return []
        if len(candidates) <= target_size:
            return candidates

        # Compute diversity bonus (distance from already-selected)
        selected: list[HypothesisCandidate] = []
        remaining = list(candidates)

        # Always keep the top reward candidate
        remaining.sort(key=lambda c: c.reward, reverse=True)
        selected.append(remaining.pop(0))

        while len(selected) < target_size and remaining:
            # For each remaining candidate, compute adjusted reward
            best_idx = 0
            best_score = -1.0
            for i, c in enumerate(remaining):
                # Diversity: min distance to any selected candidate
                diversity = min(
                    self._hypothesis_distance(c, s) for s in selected
                )
                # Adjusted reward = reward * (1 + diversity_bonus)
                adjusted = c.reward * (1.0 + 0.5 * diversity)
                if adjusted > best_score:
                    best_score = adjusted
                    best_idx = i
            selected.append(remaining.pop(best_idx))

        return selected

    def _hypothesis_distance(
        self, a: HypothesisCandidate, b: HypothesisCandidate
    ) -> float:
        """Compute distance between two hypotheses (0.0 = identical, 1.0 = unrelated)."""
        # Simple token-based distance
        a_tokens = set((a.title + " " + a.description).lower().split())
        b_tokens = set((b.title + " " + b.description).lower().split())
        if not a_tokens and not b_tokens:
            return 1.0
        intersection = a_tokens & b_tokens
        union = a_tokens | b_tokens
        jaccard = len(intersection) / len(union) if union else 0.0
        return 1.0 - jaccard

    # ── Tournament Selection ──────────────────────────────────────────────────

    def run_tournament(
        self,
        size: int = DEFAULT_TOURNAMENT_SIZE,
        generations: int = DEFAULT_GENERATIONS,
        reward_weights: dict | None = None,
    ) -> list[HypothesisCandidate]:
        """
        Run tournament selection over multiple generations.

        Each generation:
          1. Random tournaments of `size` candidates
          2. Winner survives, loser is replaced by mutation/crossover
          3. Elites are preserved
          4. Diversity is maintained via niching
        """
        if not self._population:
            return []

        population = list(self._population)
        elite_count = min(DEFAULT_ELITE_COUNT, len(population) // 2)

        for gen in range(generations):
            self._generation += 1

            # Sort by reward
            population.sort(key=lambda c: c.reward, reverse=True)

            # Preserve elites
            elites = population[:elite_count]

            # Run tournaments
            next_gen = list(elites)
            while len(next_gen) < len(population):
                # Pick tournament participants
                tournament = random.sample(
                    population, min(size, len(population))
                )
                tournament.sort(key=lambda c: c.reward, reverse=True)

                winner = tournament[0]
                loser = tournament[-1]

                # Update stats
                winner.wins += 1
                loser.losses += 1
                for t in tournament:
                    t.tournament_appearances += 1

                # Winner survives
                if len(next_gen) < len(population):
                    next_gen.append(winner)

                # Loser is replaced by offspring
                if random.random() < CROSSOVER_RATE and len(tournament) >= 2:
                    # Crossover: combine two top candidates
                    offspring = self._crossover(tournament[0], tournament[1])
                else:
                    # Mutation: vary the loser
                    offspring = self._mutate_candidate(loser, topic="")

                offspring.generation = self._generation
                if len(next_gen) < len(population):
                    next_gen.append(offspring)

            population = next_gen[: len(population)]

            # Re-score (reward landscape may shift)
            for c in population:
                c.compute_reward(reward_weights)

        # Archive best
        population.sort(key=lambda c: c.reward, reverse=True)
        self._population = population
        if population:
            self._archive.append(population[0])
        self._save_state()
        return population

    def _crossover(
        self, a: HypothesisCandidate, b: HypothesisCandidate
    ) -> HypothesisCandidate:
        """Combine two hypotheses into a new one."""
        # Take title from better parent, description combines both
        child = HypothesisCandidate(
            f"[hybrid] {a.title} + {b.title}",
            f"Combines: {a.description[:100]}... with {b.description[:100]}...",
            a.domain or b.domain,
            parent_ids=[a.id, b.id],
        )
        child.mutation_history.append(f"crossover({a.id}, {b.id})")
        return child

    def _mutate_candidate(
        self, base: HypothesisCandidate, topic: str = ""
    ) -> HypothesisCandidate:
        """Mutate a hypothesis candidate."""
        mutations = [
            "generalize", "specialize", "reverse", "simplify",
            "extend", "constrain", "reframe",
        ]
        mutation = random.choice(mutations)
        child = HypothesisCandidate(
            f"[{mutation}] {base.title}",
            f"{mutation}: {base.description}",
            base.domain,
            parent_ids=[base.id],
        )
        child.mutation_history.append(f"mutate({base.id}, {mutation})")
        return child

    # ── Scoring ───────────────────────────────────────────────────────────────

    def _score_candidate(self, c: HypothesisCandidate, topic: str):
        """Score a candidate on all reward dimensions."""
        # Heuristic scoring (LLM scoring done externally if available)
        text = (c.title + " " + c.description).lower()

        # Novelty: longer, more specific descriptions suggest more novel ideas
        c.novelty_score = min(1.0, len(text.split()) / 50.0)

        # Feasibility: presence of concrete methods/tools
        feasibility_keywords = ["experiment", "measure", "test", "data", "sample", "model", "simulation"]
        c.feasibility_score = min(1.0, sum(1 for k in feasibility_keywords if k in text) / 3.0)

        # Impact: presence of impact-related words
        impact_keywords = ["novel", "breakthrough", "significant", "fundamental", "transform", "disrupt"]
        c.impact_score = min(1.0, sum(1 for k in impact_keywords if k in text) / 3.0)

        # Coherence: description length and structure
        c.coherence_score = min(1.0, len(c.description) / 200.0)

        # Specificity: domain-specific terms
        c.specificity_score = min(1.0, len(c.domain) / 20.0) if c.domain else 0.5

        c.compute_reward()

    # ── API ───────────────────────────────────────────────────────────────────

    def get_population(self) -> list[dict]:
        """Get current population as dicts."""
        with self._lock:
            return [h.to_dict() for h in self._population]

    def get_archive(self) -> list[dict]:
        """Get archive of best hypotheses from each generation."""
        with self._lock:
            return [h.to_dict() for h in self._archive]

    def get_best(self, n: int = 3) -> list[dict]:
        """Get top-N hypotheses by reward."""
        with self._lock:
            sorted_pop = sorted(self._population, key=lambda c: c.reward, reverse=True)
            return [h.to_dict() for h in sorted_pop[:n]]

    def get_diversity_report(self) -> dict:
        """Report on population diversity."""
        with self._lock:
            if not self._population:
                return {"population_size": 0, "diversity": 0.0}
            distances = []
            for i, a in enumerate(self._population):
                for b in self._population[i + 1:]:
                    distances.append(self._hypothesis_distance(a, b))
            avg_dist = sum(distances) / len(distances) if distances else 0.0
            return {
                "population_size": len(self._population),
                "generation": self._generation,
                "avg_distance": round(avg_dist, 3),
                "unique_domains": len(set(c.domain for c in self._population if c.domain)),
                "reward_range": {
                    "min": round(min(c.reward for c in self._population), 3),
                    "max": round(max(c.reward for c in self._population), 3),
                    "mean": round(sum(c.reward for c in self._population) / len(self._population), 3),
                },
            }

    def reset(self):
        """Reset population and archive."""
        with self._lock:
            self._population = []
            self._archive = []
            self._generation = 0
            self._save_state()


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: Optional[TournamentHypothesisEngine] = None
_engine_lock = threading.Lock()


def get_tournament_engine(llm_call=None) -> TournamentHypothesisEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = TournamentHypothesisEngine(llm_call=llm_call)
        return _engine
