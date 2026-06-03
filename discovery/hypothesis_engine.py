"""Hypothesis generation engine with retry chain, confidence scoring, and persistence."""

import json
import asyncio
import time
import uuid
from datetime import datetime
from pathlib import Path

from discovery.hypothesis_memory import HypothesisMemory
from discovery.contradiction_miner import ContradictionMiner
from discovery.confidence_scorer import ConfidenceScorer
from discovery.pipeline import LLMStage


class HypothesisEngine:
    def __init__(self, memory=None):
        self.memory = memory or HypothesisMemory()
        self.scorer = ConfidenceScorer()
        self.miner = ContradictionMiner()
        self.llm_stage = LLMStage("hypothesis_generation", max_retries=5,
                                   backoff=[3, 5, 8, 12, 20], providers=["groq", "gemini"])

    async def generate(self, graph, topic, domain, run_id, contradictions=None, latent_candidates=None):
        prompt = self._build_prompt(graph, topic, domain, contradictions, latent_candidates)
        raw, provider = await self.llm_stage.call_with_retry(prompt, json_mode=True, max_tokens=16384)

        if not raw:
            return self._fallback_hypothesis(topic, domain, f"LLM unavailable ({provider})")

        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0].strip()

        hypotheses = self._parse(raw)
        if not hypotheses:
            return self._fallback_hypothesis(topic, domain, "Failed to parse LLM output")

        enriched = []
        for h in hypotheses:
            h["id"] = str(uuid.uuid4())
            h["topic"] = topic
            h["domain"] = domain
            h["provider"] = provider
            h["created_at"] = datetime.utcnow().isoformat()
            h["status"] = "draft"

            # Apply scientific formatting cleanup
            h = _clean_scientific_notation(h)

            # Algorithmic confidence scoring
            score_result = self.scorer.score(h, graph, contradictions)
            h["confidence"] = score_result["confidence"]
            h["confidence_components"] = score_result["components"]

            # Dedup against memory
            similar = self.memory.find_similar(h.get("title", ""))
            if similar:
                h["novelty"] = "low"
                h["similar_existing"] = similar
            # Cap default — LLM consistently overestimates novelty
            self._cap_novelty(h)

            # Persist
            self.memory.save_hypothesis(h, run_id)
            enriched.append(h)

        if not enriched:
            return self._fallback_hypothesis(topic, domain, "All hypotheses were duplicates")

        return enriched

    def _cap_novelty(self, h):
        """Prevent LLM from overclaiming novelty — downrank by one level."""
        n = h.get("novelty", "medium")
        order = ["high", "medium", "low"]
        if n == "high":
            h["novelty"] = "medium"
            h["novelty_override"] = "downranked_from_high"
        elif n == "medium":
            h["novelty_override"] = "kept_medium"

    def _build_prompt(self, graph, topic, domain, contradictions, latent_candidates):
        from discovery.domains import get_domain
        domain_cfg = get_domain(domain) or get_domain("general")
        entity_types = ", ".join(sorted(domain_cfg["entity_types"].keys()))
        domain_label = domain_cfg["label"]

        stats = graph.stats() if hasattr(graph, "stats") else {}
        graph_summary = json.dumps({
            "entities": {k: {"type": v["type"], "name": v["name"]} for k, v in
                        (list(graph.entities.items())[:30]) if hasattr(graph, "entities")},
            "relationships": graph.relationships[:30] if hasattr(graph, "relationships") else [],
        }, indent=2, default=str)[:4000]

        contradiction_text = ""
        if contradictions:
            capped_contra = contradictions[:5]
            contradiction_text = "\n=== DETECTED CONTRADICTIONS ===\n" + json.dumps(capped_contra, indent=2, default=str)[:2000]

        latent_text = ""
        if latent_candidates:
            # Cap at top 15 to prevent prompt overflow
            capped = sorted(latent_candidates, key=lambda x: x.get("shared_papers", 0), reverse=True)[:15]
            latent_text = "\n=== LATENT RELATIONSHIP CANDIDATES (top 15) ===\n" + json.dumps(capped, indent=2, default=str)[:3000]

        prompt = f"""You are a rigorous, skeptical AI research scientist in {domain_label}. You NEVER overclaim novelty, NEVER present speculation as fact, and ALWAYS consider contradictory evidence.

Topic: {topic}
Domain: {domain_label}
Entity types: {entity_types}

=== KNOWLEDGE GRAPH ===
{graph_summary}
{contradiction_text}
{latent_text}

=== HYPOTHESIS GENERATION RULES ===
Generate 2-4 hypotheses. For EACH hypothesis you MUST produce ALL 12 fields below.

SCIENTIFIC HUMILITY RULES:
- NEVER claim a hypothesis is "high" novelty unless you are certain it contradicts established literature
- ALWAYS include contradictory evidence and alternative explanations
- NEVER present speculative mechanisms as established fact
- BE CONSERVATIVE with confidence estimates
- PREFER "medium" or "low" novelty over "high"

MECHANISTIC REASONING REQUIREMENTS:
You MUST reason about:
- WHY each relationship exists (causal mechanism, not just correlation)
- HOW environmental conditions modulate the mechanism
- WHEN the mechanism breaks down or reverses
- WHICH variables dominate the system behavior

CROSS-PAPER SYNTHESIS:
Combine evidence from MULTIPLE papers in the graph. Look for:
- Entities that co-occur across papers but have no direct relationship edge
- Chains: A→B in paper 1, B→C in paper 2 → hypothesize A→C
- Contradictory findings that suggest unexplored boundary conditions
- Environmental or contextual variables that might resolve contradictions

BAD (shallow):
"X may be associated with Y in condition Z."

GOOD (mechanistic):
"X phosphorylates Y at residue S473 via PI3K-AKT pathway activation, but only under hypoxic conditions (<5% O2) where HIF-1alpha stabilizes the X-Y complex — this suggests an unexplored O2-dependent regulatory checkpoint."

=== OUTPUT FIELDS (produce ALL 12) ===

1. title: Short, specific testable claim
2. mechanistic_rationale: Deep causal explanation (why, how, when, which conditions)
3. supporting_evidence: List of specific evidence items from the graph papers
4. contradictory_evidence: Evidence AGAINST the hypothesis (must always include at least 1)
5. alternative_explanations: 2-3 alternative mechanistic explanations
6. novelty: "low" | "medium" — never "high" (be conservative)
7. confidence: 0.0-1.0 estimate (be conservative)
8. environmental_constraints: Conditions under which the hypothesis holds vs breaks
9. failure_conditions: Specific scenarios where the mechanism would fail
10. experimental_validation: Detailed experimental design to test
11. observational_requirements: Specific measurements, instruments, detection limits needed
12. source_traceability: PMIDs or specific papers supporting each claim

=== OUTPUT SCHEMA ===
Output ONLY valid JSON as a list:
[{{"title": "string", "mechanistic_rationale": "string", "pattern_type": "bridge_node|contradiction|low_cooccurrence|novel_mechanism|latent_link", "nodes": [{{"name": "string", "type": "{entity_types.replace(', ', '|')}", "definition": "string", "conditions": "string"}}], "edges": [{{"source": "string", "relation": "string", "target": "string", "definition": "string", "papers": ["PMID..."]}}], "supporting_evidence": ["string"], "contradictory_evidence": ["string"], "alternative_explanations": ["string"], "papers": ["PMIDs"], "environmental_constraints": "string", "failure_conditions": ["string"], "experimental_validation": "string", "observational_requirements": "string", "source_traceability": {{"claim": "string", "source": "PMID"}}[], "novelty": "low|medium", "confidence": 0.0}}]"""

        return prompt

    def _parse(self, text):
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                lst = data.get("hypotheses", data.get("results", []))
                return lst if isinstance(lst, list) else [data]
        except json.JSONDecodeError:
            pass
        return []

    def _fallback_hypothesis(self, topic, domain, reason):
        return [{
            "id": str(uuid.uuid4()),
            "title": f"Fallback analysis: {topic[:60]}",
            "mechanistic_rationale": f"Hypothesis generation encountered an issue: {reason}. "
                                     f"The graph still contains valid entities and relationships — "
                                     f"consider exploring {topic} manually via the knowledge graph.",
            "pattern_type": "fallback",
            "confidence": 0.0,
            "nodes": [],
            "edges": [],
            "supporting_evidence": [f"Error: {reason}"],
            "contradictory_evidence": [],
            "alternative_explanations": [],
            "papers": [],
            "environmental_constraints": "",
            "failure_conditions": [],
            "experimental_validation": "N/A — generation failed",
            "observational_requirements": "",
            "source_traceability": [],
            "novelty": "low",
            "topic": topic,
            "domain": domain,
            "provider": "fallback",
            "status": "error",
            "created_at": datetime.utcnow().isoformat(),
        }]

    async def reflect(self, hypothesis, graph=None):
        """Scientific reflection — critique a hypothesis."""
        critique_stage = LLMStage("skeptic_review", max_retries=2, backoff=[3, 10])

        prompt = f"""You are a skeptical AI scientist reviewing a hypothesis. Be adversarial — try to FALSIFY it.

HYPOTHESIS:
Title: {hypothesis.get('title')}
Mechanistic Rationale: {hypothesis.get('mechanistic_rationale') or hypothesis.get('description')}
Pattern type: {hypothesis.get('pattern_type')}
Confidence: {hypothesis.get('confidence')}
Novelty: {hypothesis.get('novelty')}

Supporting Evidence: {json.dumps(hypothesis.get('supporting_evidence', []), indent=2)}
Contradictory Evidence: {json.dumps(hypothesis.get('contradictory_evidence', []), indent=2)}
Alternative Explanations: {json.dumps(hypothesis.get('alternative_explanations', []), indent=2)}
Environmental Constraints: {hypothesis.get('environmental_constraints')}
Failure Conditions: {json.dumps(hypothesis.get('failure_conditions', []), indent=2)}
Experimental Validation: {hypothesis.get('experimental_validation') or hypothesis.get('testability')}
Observational Requirements: {hypothesis.get('observational_requirements')}

Critique for:
1. Logical coherence — does the causal chain hold?
2. Evidence strength — rate each claim strong/weak/absent
3. Alternative mechanisms — what important alternatives are MISSING?
4. Confounders — what unaccounted variables could invalidate the hypothesis?
5. Testability — is the proposed experiment genuinely feasible?
6. Novelty — is this genuinely underexplored or just rephrasing known concepts?
7. Weaknesses — top 3 specific flaws

Output JSON:
{{"critique": "detailed adversarial critique", "weaknesses": ["flaw1", "flaw2", "flaw3"], "revised_confidence": 0.0-1.0, "alternative_explanations": ["alt1", "alt2"], "suggested_fixes": ["fix1", "fix2"], "evidence_rating": "strong|moderate|weak", "recommendation": "accept|revise|reject"}}"""

        raw, provider = await critique_stage.call_with_retry(prompt, json_mode=True)
        if not raw:
            return {"critique": "Reflection unavailable", "weaknesses": ["LLM error"], "revised_confidence": hypothesis.get("confidence", 0.0)}

        try:
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0].strip()
            result = json.loads(raw)
            self.memory.update_critique(hypothesis["id"],
                                         result.get("critique", ""),
                                         json.dumps(result.get("weaknesses", [])))
            return result
        except json.JSONDecodeError:
            return {"critique": "Failed to parse reflection", "weaknesses": [], "revised_confidence": hypothesis.get("confidence", 0.0)}

    async def refine(self, hypothesis, critique, graph=None, domain="general"):
        """Iterative refinement: take a hypothesis + critique, produce a revised hypothesis.

        This is the core of real scientific method — falsification drives revision.
        """
        refine_stage = LLMStage("hypothesis_refinement", max_retries=2, backoff=[3, 10])

        prompt = f"""You are a rigorous AI research scientist. A hypothesis was reviewed and critiqued.
Your job is to produce a REVISED hypothesis that addresses the critique's weaknesses.

ORIGINAL HYPOTHESIS:
Title: {hypothesis.get('title')}
Rationale: {hypothesis.get('mechanistic_rationale') or hypothesis.get('description', '')}
Confidence: {hypothesis.get('confidence')}
Pattern type: {hypothesis.get('pattern_type')}

CRITIQUE:
{json.dumps(critique, indent=2)}

RULES FOR REVISION:
1. Address EACH weakness identified in the critique
2. If the critique says "reject", you must fundamentally rethink the hypothesis
3. If the critique says "revise", fix the specific flaws while keeping the core idea
4. Incorporate suggested fixes from the critique
5. Add alternative explanations that address confounders
6. Strengthen the experimental validation plan
7. Update failure conditions based on weaknesses found

Output ONLY valid JSON with the SAME structure as the original hypothesis:
{{
  "title": "revised concise hypothesis title",
  "mechanistic_rationale": "detailed mechanistic explanation addressing critique weaknesses",
  "pattern_type": "bridge_node|contradiction|low_cooccurrence|novel_mechanism",
  "confidence": 0.0-1.0,
  "supporting_evidence": ["evidence1", "evidence2"],
  "contradictory_evidence": ["counter1"],
  "alternative_explanations": ["alt1 addressing critique confounders"],
  "failure_conditions": ["condition1"],
  "experimental_validation": "how to test this hypothesis",
  "novelty": "high|medium|low",
  "refinement_notes": "what was changed and why based on critique"
}}"""

        raw, provider = await refine_stage.call_with_retry(prompt, json_mode=True, max_tokens=8192)
        if not raw:
            return hypothesis  # Return original if refinement fails

        try:
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0].strip()
            refined = json.loads(raw)

            # Preserve metadata from original
            refined["id"] = hypothesis.get("id", "")
            refined["topic"] = hypothesis.get("topic", "")
            refined["domain"] = domain
            refined["provider"] = provider
            refined["created_at"] = hypothesis.get("created_at", "")
            refined["status"] = "refined"
            refined["parent_id"] = hypothesis.get("id", "")
            refined["refinement_count"] = hypothesis.get("refinement_count", 0) + 1

            # Re-score confidence algorithmically
            score_result = self.scorer.score(refined, graph, None)
            refined["confidence"] = score_result["confidence"]
            refined["confidence_components"] = score_result["components"]

            # Clean formatting
            refined = _clean_scientific_notation(refined)

            # Persist the refined version
            self.memory.save_hypothesis(refined, hypothesis.get("topic", ""))

            return refined
        except (json.JSONDecodeError, KeyError):
            return hypothesis  # Return original on parse failure


def _clean_scientific_notation(h):
    """Clean Unicode/scientific formatting in all text fields of a hypothesis."""
    import re
    replacements = {
        "??m": "μm",
        "??": "'",
        "??": "'",
        "—": " — ",
        "–": "-",
        "−": "-",
    }
    def _clean(text):
        if not isinstance(text, str):
            return text
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _walk(obj):
        if isinstance(obj, dict):
            return {k: _walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_walk(item) for item in obj]
        if isinstance(obj, str):
            return _clean(obj)
        return obj

    return _walk(h)
