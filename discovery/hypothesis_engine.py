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
        self.llm_stage = LLMStage("hypothesis_generation", max_retries=3,
                                   backoff=[3, 8, 20], providers=["groq", "gemini"])

    async def generate(self, graph, topic, domain, run_id, contradictions=None, latent_candidates=None):
        prompt = self._build_prompt(graph, topic, domain, contradictions, latent_candidates)
        raw, provider = await self.llm_stage.call_with_retry(prompt, json_mode=True, max_tokens=16384)

        if not raw:
            return self._fallback_hypothesis(topic, domain, f"LLM unavailable ({provider})")

        raw = raw.strip()
        # Strip markdown code block if present
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

            # Algorithmic confidence scoring
            score_result = self.scorer.score(h, graph, contradictions)
            h["confidence"] = score_result["confidence"]
            h["confidence_components"] = score_result["components"]

            # Dedup against memory
            similar = self.memory.find_similar(h.get("title", ""))
            if similar:
                h["novelty"] = "low"
                h["similar_existing"] = similar
            else:
                h["novelty"] = h.get("novelty", "medium")

            # Persist
            self.memory.save_hypothesis(h, run_id)
            enriched.append(h)

        if not enriched:
            return self._fallback_hypothesis(topic, domain, "All hypotheses were duplicates")

        return enriched

    def _build_prompt(self, graph, topic, domain, contradictions, latent_candidates):
        from discovery.domains import get_domain
        domain_cfg = get_domain(domain) or get_domain("general")
        entity_types = ", ".join(sorted(domain_cfg["entity_types"].keys()))
        domain_label = domain_cfg["label"]

        stats = graph.stats() if hasattr(graph, "stats") else {}
        graph_summary = json.dumps({
            "entities": {k: {"type": v["type"], "name": v["name"]} for k, v in
                        (list(graph.entities.items())[:60]) if hasattr(graph, "entities")},
            "relationships": graph.relationships[:80] if hasattr(graph, "relationships") else [],
        }, indent=2, default=str)

        contradiction_text = ""
        if contradictions:
            contradiction_text = "\n=== DETECTED CONTRADICTIONS ===\n" + json.dumps(contradictions, indent=2, default=str)

        latent_text = ""
        if latent_candidates:
            latent_text = "\n=== LATENT RELATIONSHIP CANDIDATES ===\n" + json.dumps(latent_candidates, indent=2, default=str)

        return f"""You are an AI research scientist in {domain_label} generating novel scientific hypotheses.

Topic: {topic}
Domain: {domain_label}
Entity types: {entity_types}

=== KNOWLEDGE GRAPH ===
{graph_summary}
{contradiction_text}
{latent_text}

=== HYPOTHESIS GENERATION RULES ===
Generate 2-4 hypotheses. For EACH hypothesis:

1. IDENTIFY a testable, non-obvious scientific claim
2. DEFINE all entities involved (name, type, role)
3. SPECIFY mechanistic relationships (NOT just "X associated with Y" — explain HOW)
4. ESTIMATE confidence based on evidence strength
5. DESCRIBE how to experimentally test it
6. RATE novelty (high = not obviously in literature, medium = plausible extension, low = well-known)

DO NOT generate:
- Generic literature summaries
- Obvious known facts
- Untestable claims
- Vague "further research needed" statements

=== OUTPUT SCHEMA ===
Output ONLY valid JSON as a list:
[{{"title": "string", "description": "string", "pattern_type": "bridge_node|contradiction|low_cooccurrence|novel_mechanism|latent_link", "nodes": [{{"name": "string", "type": "{entity_types.replace(', ', '|')}", "definition": "string", "conditions": "string"}}], "edges": [{{"source": "string", "relation": "string", "target": "string", "definition": "string", "papers": ["PMID..."]}}], "evidence": ["string"], "papers": ["PMIDs"], "testability": "string — detailed experimental design", "novelty": "high|medium|low"}}]"""

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
            "description": f"Hypothesis generation encountered an issue: {reason}. "
                           f"The graph still contains valid entities and relationships — "
                           f"consider exploring {topic} manually via the knowledge graph.",
            "pattern_type": "fallback",
            "confidence": 0.0,
            "nodes": [],
            "edges": [],
            "evidence": [f"Error: {reason}"],
            "papers": [],
            "testability": "N/A — generation failed",
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

        prompt = f"""You are a skeptical AI scientist reviewing a hypothesis.

HYPOTHESIS:
Title: {hypothesis.get('title')}
Description: {hypothesis.get('description')}
Pattern type: {hypothesis.get('pattern_type')}
Confidence: {hypothesis.get('confidence')}

Nodes: {json.dumps(hypothesis.get('nodes', []), indent=2)}
Edges: {json.dumps(hypothesis.get('edges', []), indent=2)}
Evidence: {json.dumps(hypothesis.get('evidence', []), indent=2)}
Testability: {hypothesis.get('testability')}

Critique this hypothesis for:
1. Logical coherence — does the reasoning hold?
2. Evidence strength — are the cited claims well-supported?
3. Alternative explanations — what else could explain the observations?
4. Testability — is the proposed experiment feasible?
5. Novelty — is this genuinely new or already known?
6. Weaknesses — what are the top 3 specific weaknesses?

Output JSON:
{{"critique": "detailed critique", "weaknesses": ["weakness1", "weakness2", "weakness3"], "revised_confidence": 0.0-1.0, "alternative_explanations": ["alt1", "alt2"], "suggested_fixes": ["fix1", "fix2"]}}"""

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
