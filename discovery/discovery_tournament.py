"""
discovery_tournament.py — Evolutionary hypothesis selection.

Generate 20 hypotheses → simulate → score → eliminate worst →
mutate survivors → repeat.

Inspired by:
  - Genetic algorithms
  - GFlowNet-style diverse hypothesis evolution
  - AI Scientist's iterative idea refinement

The tournament produces fewer but MUCH stronger hypotheses,
each having survived multiple rounds of elimination.
"""

import json
import random
import copy
from typing import Dict, List, Optional
from discovery.json_extract import extract_json


class DiscoveryTournament:
    """
    Evolutionary tournament for hypothesis selection.
    """

    def __init__(self, llm_call=None, simulator=None, scorer=None):
        self.llm_call = llm_call
        self.simulator = simulator
        self.scorer = scorer

    def run(self, seed_hypotheses: list, topic: str, domain: str,
            generations: int = 3, population_size: int = 8,
            papers: list = None, graph=None) -> dict:
        """
        Run the tournament.

        Args:
            seed_hypotheses: Initial hypotheses from gap/anomaly analysis
            topic: Research topic
            domain: Research domain
            generations: Number of evolution rounds
            population_size: How many to keep per generation
            papers: Literature for evidence checking
            graph: Knowledge graph

        Returns:
            {
                "generations": [...],
                "survivors": [...],
                "eliminated": [...],
                "winner": {...},
                "tournament_stats": {...}
            }
        """
        # Initialize population with seeds + LLM-generated variants
        population = list(seed_hypotheses)
        if self.llm_call:
            generated = self._generate_variants(seed_hypotheses, topic, domain,
                                                 target_count=population_size * 2)
            population.extend(generated)

        # Cap initial population
        population = population[:population_size * 3]

        generations_log = []
        all_eliminated = []

        for gen in range(generations):
            # 1. Score all hypotheses
            scored = self._score_population(population, papers, graph)

            # 2. Sort by score
            scored.sort(key=lambda h: h.get("_tournament_score", 0), reverse=True)

            # 3. Log generation
            gen_log = {
                "generation": gen + 1,
                "population_size": len(scored),
                "top_score": scored[0].get("_tournament_score", 0) if scored else 0,
                "bottom_score": scored[-1].get("_tournament_score", 0) if scored else 0,
                "mean_score": sum(h.get("_tournament_score", 0) for h in scored) / max(1, len(scored)),
            }
            generations_log.append(gen_log)

            # 4. Eliminate worst (keep top population_size)
            survivors = scored[:population_size]
            eliminated = scored[population_size:]
            all_eliminated.extend(eliminated)

            # 5. Mutate survivors (if not last generation)
            if gen < generations - 1 and self.llm_call:
                mutants = self._mutate(survivors, topic, domain, len(eliminated))
                population = survivors + mutants
            else:
                population = survivors

        # Final ranking
        final_scored = self._score_population(population, papers, graph)
        final_scored.sort(key=lambda h: h.get("_tournament_score", 0), reverse=True)

        # Clean up internal scores
        for h in final_scored:
            h.pop("_tournament_score", None)

        winner = final_scored[0] if final_scored else None

        return {
            "generations": generations_log,
            "survivors": final_scored,
            "eliminated_count": len(all_eliminated),
            "winner": winner,
            "tournament_stats": {
                "generations_run": generations,
                "initial_population": len(seed_hypotheses),
                "final_population": len(final_scored),
                "winner_score": winner.get("_tournament_score", winner.get("confidence", 0)) if winner else 0,
                "winner_name": winner.get("name", "?") if winner else "?",
            },
        }

    def _generate_variants(self, seeds: list, topic: str, domain: str,
                           target_count: int = 16) -> list:
        """Use LLM to generate hypothesis variants."""
        if not self.llm_call:
            return []

        seed_text = ""
        for i, s in enumerate(seeds[:5], 1):
            name = s.get("name", "?")
            desc = s.get("description", s.get("mechanism", ""))[:200]
            seed_text += f"\n{i}. {name}: {desc}"

        prompt = f"""You are a scientific hypothesis generator. Given these seed hypotheses,
generate {target_count} VARIANT hypotheses that explore different directions.

TOPIC: {topic}
DOMAIN: {domain}

SEED HYPOTHESES:
{seed_text}

Generate variants that:
1. Explore different mechanisms (not just parameter tweaks)
2. Include cross-domain analogies
3. Include null hypotheses (conventional explanations)
4. Include deliberately simple explanations
5. Include deliberately bold/speculative explanations

Each variant MUST include:
- name (descriptive)
- type (proposed|alternative|conventional|null)
- description (with at least one equation)
- key_parameters (with expected values)
- predictions (with numbers)

Output JSON:
{{
  "hypotheses": [
    {{
      "name": "descriptive name",
      "type": "proposed|alternative|conventional|null",
      "description": "description with equations",
      "key_parameters": [{{"name": "p", "expected_value": "v", "units": "u"}}],
      "predictions": ["prediction with numbers"],
      "is_novel_vs_known": "novel|extension_of_known|modification_of_known"
    }}
  ]
}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=8192)
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = extract_json(raw)
                    return result.get("hypotheses", [])
        except Exception:
            pass
        return []

    def _score_population(self, population: list, papers: list,
                          graph=None) -> list:
        """Score all hypotheses in the population."""
        for h in population:
            score = 10.0  # base score — every hypothesis starts with something

            # Factor 1: Explanatory power
            explains = h.get("explains") or h.get("supporting_evidence") or []
            fails = h.get("fails_to_explain") or h.get("contradictory_evidence") or []
            total = len(explains) + len(fails)
            if total > 0:
                score += (len(explains) / total) * 25
            elif h.get("description"):
                score += 10  # has description = has some explanatory content

            # Factor 2: Predictions (more = better, quantitative = better)
            predictions = h.get("predictions") or []
            quant_preds = sum(1 for p in predictions
                              if isinstance(p, (str, dict)) and
                              any(c.isdigit() for c in str(p)))
            score += min(20, quant_preds * 5)
            if predictions:
                score += 5  # bonus for having any predictions

            # Factor 3: Mathematical formalism
            model = h.get("mathematical_model", h.get("mathematical_formalism", ""))
            if model and any(c.isdigit() for c in str(model)):
                score += 15

            # Factor 4: Key parameters with values
            params = h.get("key_parameters") or []
            if isinstance(params, list) and params:
                score += min(10, len(params) * 3)
            elif isinstance(params, dict) and params:
                score += min(10, len(params) * 3)

            # Factor 5: Literature grounding
            lit = h.get("literature_basis", h.get("literature_grounding", h.get("papers", [])))
            if isinstance(lit, list) and lit:
                score += min(10, len(lit) * 3)

            # Factor 6: Simplicity (penalize excessive complexity)
            assumptions = h.get("key_assumptions") or []
            if isinstance(assumptions, list) and len(assumptions) > 5:
                score -= 5

            # Factor 7: Type bonus
            type_bonus = {
                "null": 5,
                "conventional": 3,
                "alternative": 8,
                "proposed": 10,
                "counterfactual": 12,
            }
            score += type_bonus.get(h.get("type", ""), 5)

            # Factor 8: Description quality (longer = more detailed)
            desc = h.get("description", h.get("mechanistic_rationale", ""))
            if len(desc) > 200:
                score += 5
            if len(desc) > 500:
                score += 5

            h["_tournament_score"] = round(max(0, score), 2)

        return population

    def _mutate(self, survivors: list, topic: str, domain: str,
                count: int = 5) -> list:
        """Mutate survivors to create new variants."""
        if not self.llm_call or not survivors:
            return []

        survivor_text = ""
        for i, s in enumerate(survivors[:3], 1):
            name = s.get("name", "?")
            desc = s.get("description", s.get("mechanism", ""))[:150]
            score = s.get("_tournament_score", 0)
            survivor_text += f"\n{i}. {name} (score: {score}): {desc}"

        prompt = f"""You are mutating scientific hypotheses to create new variants.

TOPIC: {topic}
DOMAIN: {domain}

TOP SURVIVORS:
{survivor_text}

Create {count} MUTATIONS by:
1. Combining elements from different survivors
2. Inverting assumptions (what if the opposite were true?)
3. Scaling parameters to extremes (much larger or smaller)
4. Applying cross-domain analogies
5. Removing one key assumption from each survivor

Each mutation must have:
- name, type, description (with equations), key_parameters, predictions

Output JSON:
{{
  "hypotheses": [
    {{
      "name": "mutation name",
      "type": "proposed|alternative|conventional|null",
      "description": "description with equations",
      "key_parameters": [{{"name": "p", "expected_value": "v", "units": "u"}}],
      "predictions": ["prediction with numbers"]
    }}
  ]
}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=4096)
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = extract_json(raw)
                    return result.get("hypotheses", [])
        except Exception:
            pass
        return []
