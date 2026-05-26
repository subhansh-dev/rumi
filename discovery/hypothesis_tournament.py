"""Multi-generation hypothesis tournament with crossover, mutation, and fitness selection.

Inspired by Google DeepMind's Co-Scientist (Generation -> Reflection -> Ranking -> Evolution)
and Sakana AI's evolutionary hypothesis discovery.
"""

import json
import asyncio
from datetime import datetime
from discovery.pipeline import LLMStage
from discovery.skeptic_agent import SkepticAgent
from discovery.novelty_detector import NoveltyDetector
from discovery.hypothesis_memory import HypothesisMemory


class HypothesisTournament:
    def __init__(self, memory=None):
        self.memory = memory or HypothesisMemory()
        self.evolve_stage = LLMStage("tournament_evolution", max_retries=2, providers=["groq", "gemini"])
        self.crossover_stage = LLMStage("tournament_crossover", max_retries=2, providers=["groq", "gemini"])
        self.skeptic = SkepticAgent()
        self.novelty = NoveltyDetector(memory)

    async def run(self, hypotheses, graph, topic, domain, generations=3, population_size=6):
        """Run multi-generation tournament evolution on hypotheses.

        Each generation:
        1. Scores all hypotheses (confidence * novelty * skeptic rating)
        2. Selects top performers as parents
        3. Crosses over parents to create offspring
        4. Mutates offspring for diversity
        5. Keeps top N survivors for next generation
        """
        if not hypotheses or len(hypotheses) < 2:
            return hypotheses

        population = list(hypotheses)

        for gen in range(generations):
            scored = await self._score_population(population, graph, gen)

            survivors = self._select_survivors(scored, population_size)

            if len(survivors) >= 2 and gen < generations - 1:
                offspring = await self._generate_offspring(
                    survivors, graph, topic, domain, gen
                )
                population = survivors + offspring
            else:
                population = survivors

            if len(population) >= 2:
                population = self._select_survivors(
                    await self._score_population(population, graph, gen + 0.5),
                    max(population_size, len(survivors))
                )

        final = await self._score_population(population, graph, generations)
        ranked = sorted(final, key=lambda h: h.get("_fitness", 0), reverse=True)
        for i, h in enumerate(ranked):
            h.pop("_fitness", None)
            h.pop("_skeptic_result", None)
            if "skeptic_review" in h.get("critique", ""):
                h["critique"] = ""
            h["tournament_rank"] = i + 1
            h["tournament_generations"] = generations

        return ranked

    async def _score_population(self, hypotheses, graph, gen_id):
        """Score each hypothesis using confidence + novelty + skeptic rating."""
        scored = []
        for h in hypotheses:
            fitness = h.get("confidence", 0.3) * 1.0

            novelty_val = {"low": 0.3, "medium": 0.6, "high": 0.9}.get(
                h.get("novelty", "medium"), 0.5
            )
            fitness = fitness * 0.5 + novelty_val * 0.3

            if gen_id is not None:
                try:
                    review = await self.skeptic.review(h)
                    if review.get("recommendation") == "accept":
                        fitness *= 1.1
                    elif review.get("recommendation") == "reject":
                        fitness *= 0.5
                    h["_skeptic_result"] = review
                except Exception:
                    pass

            if gen_id is not None and isinstance(gen_id, int):
                try:
                    nv = await self.novelty.check(h, graph)
                    prob = nv.get("novelty_probability", 0.3)
                    fitness = fitness * 0.7 + prob * 0.3
                except Exception:
                    pass

            h["_fitness"] = round(fitness, 4)
            scored.append(h)

        return scored

    def _select_survivors(self, scored, target_size):
        """Tournament selection: keep top performers + random wildcards."""
        scored.sort(key=lambda h: h.get("_fitness", 0), reverse=True)
        top_n = max(2, target_size * 3 // 4)
        survivors = scored[:top_n]
        return survivors

    async def _generate_offspring(self, parents, graph, topic, domain, gen):
        """Create offspring through crossover + mutation of parent pairs."""
        offspring = []
        parent_pairs = []
        for i in range(len(parents)):
            for j in range(i + 1, len(parents)):
                if len(parent_pairs) >= 3:
                    break
                parent_pairs.append((parents[i], parents[j]))
            if len(parent_pairs) >= 3:
                break

        for p1, p2 in parent_pairs:
            child = await self._crossover(p1, p2, topic, domain, gen)
            if child:
                child["_parent_ids"] = [p1.get("id"), p2.get("id")]
                child["_generation"] = gen + 1
                child["domain"] = domain
                child["topic"] = topic
                child["created_at"] = datetime.utcnow().isoformat()
                try:
                    self.memory.save_hypothesis(child, f"tournament_gen{gen+1}")
                except Exception:
                    pass
                offspring.append(child)

        return offspring

    async def _crossover(self, parent_a, parent_b, topic, domain, gen):
        """Combine two hypotheses using LLM crossover."""
        prompt = f"""You are an evolutionary hypothesis scientist. Your task is to create a NEW, IMPROVED hypothesis by combining the best elements of two parent hypotheses.

PARENT A:
Title: {parent_a.get('title')}
Mechanism: {parent_a.get('mechanistic_rationale', '')}
Pattern: {parent_a.get('pattern_type')}
Novelty: {parent_a.get('novelty')}
Confidence: {parent_a.get('confidence')}

PARENT B:
Title: {parent_b.get('title')}
Mechanism: {parent_b.get('mechanistic_rationale', '')}
Pattern: {parent_b.get('pattern_type')}
Novelty: {parent_b.get('novelty')}
Confidence: {parent_b.get('confidence')}

EVOLUTION RULES:
1. The child MUST be DIFFERENT from both parents — no simple rephrasing
2. Combine the strongest mechanism from each parent into a unified causal chain
3. If the parents contradict each other, hypothesize a RESOLUTION mechanism
4. Add at least one new altnerative explanation not present in either parent
5. Identify at least one failure condition unique to the combined mechanism
6. The child should have novelty "medium" or "high" — never "low"
7. Child confidence should NOT exceed either parent's confidence (be conservative)

OUTPUT JSON with these 12 fields:
{{"title": "string", "mechanistic_rationale": "string", "pattern_type": "bridge_node|contradiction|low_cooccurrence|novel_mechanism|latent_link", "nodes": [{{"name": "string", "type": "string", "definition": "string", "conditions": "string"}}], "edges": [{{"source": "string", "relation": "string", "target": "string", "definition": "string", "papers": ["PMID..."]}}], "supporting_evidence": ["string"], "contradictory_evidence": ["string"], "alternative_explanations": ["string"], "papers": ["PMIDs"], "environmental_constraints": "string", "failure_conditions": ["string"], "experimental_validation": "string", "observational_requirements": "string", "source_traceability": [{{"claim": "string", "source": "PMID"}}], "novelty": "low|medium|high", "confidence": 0.0}}"""

        raw, provider = await self.crossover_stage.call_with_retry(prompt, json_mode=True)
        if not raw:
            return None

        try:
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0].strip()
            child = json.loads(raw)
            child["provider"] = provider
            return child
        except (json.JSONDecodeError, KeyError):
            return None
