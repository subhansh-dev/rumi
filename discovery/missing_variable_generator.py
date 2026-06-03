"""
missing_variable_generator.py — Propose HIDDEN VARIABLES that explain gaps.

This is the core of abductive reasoning: "What unseen factor could explain this?"

Historical examples:
  - Dark matter: observation (galaxies rotate too fast) → hidden variable (invisible mass)
  - Neutrino: observation (missing energy in beta decay) → hidden variable (undetected particle)
  - Helicobacter pylori: observation (ulcers unexplained) → hidden variable (bacterial infection)
  - Oxygen: observation (combustion fails in sealed containers) → hidden variable (dephlogisticated air)

The pattern is always:
  1. We observe something anomalous
  2. Current explanations fail
  3. We propose an unseen entity/process/variable
  4. If that variable exists, it should make specific predictions

This module uses:
  - Graph analysis to find "missing middle" between disconnected observations
  - LLM reasoning to propose creative hidden variables
  - Cross-domain analogy to transfer hidden variable patterns
"""

import json
from typing import List, Dict, Optional


class MissingVariableGenerator:
    """
    Generate candidate hidden variables that could explain knowledge gaps and anomalies.
    """

    def __init__(self, graph=None, llm_call=None):
        self.graph = graph
        self.llm_call = llm_call

    def generate(self, gaps: list, anomalies: list, topic: str,
                 domain: str, papers: list = None) -> dict:
        """
        Generate missing variable candidates from gaps and anomalies.

        Args:
            gaps: output from KnowledgeGapDetector.detect_gaps()["top_gaps"]
            anomalies: output from AnomalyDetector.detect_anomalies()["top_anomalies"]
            topic: research topic
            domain: research domain
            papers: list of paper dicts for context

        Returns:
            {
                "hidden_variables": [
                    {
                        "name": "...",
                        "type": "entity|process|force|field|mechanism|condition",
                        "description": "...",
                        "explains_gaps": [...],
                        "explains_anomalies": [...],
                        "reasoning_type": "abductive|analogical|causal|structural",
                        "confidence": 0.0-1.0,
                        "predictions": ["..."],
                        "analogies": ["historical parallel"]
                    }
                ],
                "reasoning_chains": [...]
            }
        """
        if not self.llm_call:
            return {"hidden_variables": [], "reasoning_chains": [],
                    "error": "No LLM client available"}

        # Build context for LLM
        gap_text = self._format_gaps(gaps[:6])
        anomaly_text = self._format_anomalies(anomalies[:6])

        # Get graph context
        graph_context = self._build_graph_context()

        # Build paper context
        paper_text = ""
        if papers:
            for p in papers[:6]:
                abstract = p.get("abstract", "")[:300]
                if abstract:
                    paper_text += f"\n- {p.get('title', '?')}: {abstract}\n"

        prompt = f"""You are a brilliant scientific theorist specializing in discovering hidden variables.

TOPIC: {topic}
DOMAIN: {domain}

KNOWLEDGE GAPS IDENTIFIED:
{gap_text}

ANOMALIES IDENTIFIED:
{anomaly_text}

GRAPH CONTEXT:
{graph_context}

RELEVANT PAPERS:
{paper_text}

Your task: propose HIDDEN VARIABLES — unseen entities, processes, forces, or conditions
that could explain the gaps and anomalies above.

Before proposing hidden variables, think through this structured reasoning:

<discovery_reasoning>
1. WHAT GAPS EXIST? — List the knowledge gaps and anomalies that need explanation.
2. WHAT'S MISSING? — What unseen entity, process, or force could fill these gaps?
3. WHAT EXISTS ALREADY? — Are there known concepts that partially explain this?
4. WHAT WOULD THE MATH LOOK LIKE? — For each proposed variable, what equations would govern it?
5. CAN I DERIVE THE EQUATIONS? — If the variable connects to known physics, derive the relationship.
6. HOW WOULD I MEASURE IT? — What experiment would confirm or refute this variable?
</discovery_reasoning>

REQUIREMENTS — PREFER quantitative, but don't reject qualitative:
1. PREFER mathematical formalism. If you can derive an equation from first principles or
   combine known relations, DO the derivation — show your work, don't just state the result.
   If no equation is possible yet, provide: (a) the physical quantity involved,
   (b) how it couples to observables, (c) expected order of magnitude.
   A qualitative proposal with clear testability beats no proposal.
2. Ground in existing literature when possible. If the variable is truly novel and has no
   direct literature precedent, state what KNOWN concepts it extends or combines.
3. PREFER predictions with NUMBERS. If no numbers are possible, state the DIRECTION
   and what measurement would constrain it.
4. Distinguish clearly: is this a NEW entity, or an EXTENSION of a known mechanism?
5. State what PARAMETER or COUPLING CONSTANT would need to be measured.
6. DERIVATION: If the equation can be derived from known physics, SHOW THE DERIVATION.
   Don't just state "F = ma" — show how you got there from the mechanism steps.

Think like the scientists who discovered:
- Dark matter: Zwicky (1933) proposed invisible mass. He calculated: visible mass gives
  velocity dispersion ~80 km/s, but observed ~160 km/s. Required mass-to-light ratio M/L ~ 500.
  The hypothesis was specific: missing mass, quantified, testable.
- Neutrino: Pauli (1930) proposed to save energy conservation in beta decay. Specific:
  spin-1/2 particle, mass < electron, interacts only weakly. Quantitative from day one.
- H. pylori: Marshall & Warren (1984) proposed bacteria cause ulcers. They cultured the
  bacterium, measured its prevalence (found in >90% of duodenal ulcers), and Marshall
  drank the culture to prove causation. Quantitative evidence.

DO NOT produce vague names like "Quantum Flux" or "Cosmic Viscosity" without:
  - The specific physical/mathematical quantity involved
  - How it couples to observable phenomena
  - Its expected magnitude based on the anomaly being explained
  - Existing literature on similar or related concepts

For each hidden variable, provide:
1. A clear name (descriptive, not creative)
2. Its type (entity, process, force, field, mechanism, condition)
3. A detailed description with at least one equation or quantitative relationship
4. Mathematical formalism: equations, coupling constants, parameter ranges
5. Literature grounding: what existing papers/concepts relate to this?
6. Which specific gaps and anomalies it explains
7. Quantitative predictions with expected magnitudes
8. How to distinguish this from existing known mechanisms
9. What experiment would measure the key parameter

Output JSON:
{{
  "hidden_variables": [
    {{
      "name": "Descriptive Name (not creative — say what it IS)",
      "type": "entity|process|force|field|mechanism|condition",
      "description": "Detailed description with physical/mathematical content",
      "mathematical_formalism": "Equations, relationships, parameter definitions. Prefer equations but qualitative is OK if testable.",
      "derivation": "If the equation can be derived from known physics, show derivation steps. Otherwise state 'not derivable — estimated from [reasoning]'.",
      "coupling_constants": "What parameters define this? What are their expected magnitudes?",
      "literature_grounding": "cite 2-3 existing papers or concepts this builds on",
      "is_novel_vs_extension": "novel|extension_of_known|modification_of_known",
      "explains_gaps": ["gap1 description", "gap2 description"],
      "explains_anomalies": ["anomaly1 description", "anomaly2 description"],
      "reasoning_type": "abductive|analogical|causal|structural",
      "confidence": 0.0-1.0,
      "predictions": [
        "If this variable exists, then [specific observable] should change by [quantitative magnitude]",
        "Another prediction with numbers"
      ],
      "key_parameter_to_measure": "What single measurement would confirm or refute this?",
      "falsification": "Specific observation with quantitative threshold that disproves this"
    }}
  ],
  "reasoning_chains": [
    {{
      "chain": "Observation A (magnitude X) + Gap B + No current explanation → Propose C with parameter P = expected value",
      "type": "abductive"
    }}
  ]
}}

Generate 2-3 hidden variables. Quality over quantity. Each MUST have equations and
quantitative predictions. Reject any proposal that is just a fancy name without math."""

        try:
            raw = self.llm_call(prompt, max_tokens=8192)
            if not raw:
                try:
                    from discovery.llm_client import call_json
                    raw = call_json(prompt, max_tokens=8192, provider="gemini")
                except Exception:
                    pass
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = json.loads(raw)
                else:
                    result = raw

                if isinstance(result, dict):
                    # Validate and enrich
                    for hv in result.get("hidden_variables", []):
                        hv.setdefault("name", "Unnamed Variable")
                        hv.setdefault("type", "unknown")
                        hv.setdefault("confidence", 0.5)
                        hv.setdefault("predictions", [])
                        hv.setdefault("explains_gaps", [])
                        hv.setdefault("explains_anomalies", [])
                        hv.setdefault("reasoning_type", "abductive")
                    return result

        except Exception as e:
            return {"hidden_variables": [], "reasoning_chains": [],
                    "error": str(e)}

        return {"hidden_variables": [], "reasoning_chains": []}

    def generate_from_graph(self, topic: str, domain: str) -> dict:
        """
        Generate hidden variables directly from graph structure analysis.
        No separate gap/anomaly inputs needed — analyzes graph directly.
        """
        if not self.graph or not self.llm_call:
            return {"hidden_variables": [], "reasoning_chains": []}

        entities = self.graph.entities if hasattr(self.graph, 'entities') else {}
        relationships = self.graph.relationships if hasattr(self.graph, 'relationships') else []

        # Find "missing middle" patterns:
        # A correlates with C, B correlates with C, but A and B aren't connected
        # → Propose hidden variable D that connects A and B through C
        missing_middles = self._find_missing_middles(entities, relationships)

        # Find "explanatory voids":
        # Multiple effects in the graph with no common cause
        explanatory_voids = self._find_explanatory_voids(entities, relationships)

        # Build context
        context = f"""TOPIC: {topic}
DOMAIN: {domain}

MISSING MIDDLES (entities that should be connected):
{json.dumps(missing_middles[:5], indent=2)}

EXPLANATORY VOIDS (effects without common causes):
{json.dumps(explanatory_voids[:5], indent=2)}

GRAPH SUMMARY:
- {len(entities)} entities, {len(relationships)} relationships
- Entity types: {dict(self._type_counts(entities))}

Propose hidden variables that could fill these structural gaps."""

        prompt = f"""You are analyzing a knowledge graph for a scientific discovery system.

{context}

For each structural gap, propose a hidden variable that could bridge it.

Output JSON:
{{
  "hidden_variables": [
    {{
      "name": "...",
      "type": "entity|process|force|field|mechanism|condition",
      "description": "...",
      "bridges": ["entity_a → hidden_var → entity_b"],
      "confidence": 0.0-1.0,
      "predictions": ["If this exists, then..."],
      "reasoning": "Why this variable is needed"
    }}
  ]
}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=4096)
            if not raw:
                try:
                    from discovery.llm_client import call_json
                    raw = call_json(prompt, max_tokens=4096, provider="gemini")
                except Exception:
                    pass
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = json.loads(raw)
                else:
                    result = raw
                if isinstance(result, dict):
                    return result
        except Exception:
            pass

        return {"hidden_variables": [], "reasoning_chains": []}

    def _find_missing_middles(self, entities: dict, relationships: list) -> list:
        """
        Find cases where A→?→C should exist but the middle is missing.
        
        Pattern: Two entities are both connected to common neighbors,
        but there's no direct or mediated connection between them.
        This suggests a hidden mediator.
        """
        from collections import defaultdict

        adj = defaultdict(set)
        for rel in relationships:
            adj[rel["source"]].add(rel["target"])
            adj[rel["target"]].add(rel["source"])

        middles = []
        checked = set()

        for eid in entities:
            neighbors = adj.get(eid, set())
            if len(neighbors) < 2:
                continue
            neighbors_list = list(neighbors)
            for i in range(len(neighbors_list)):
                for j in range(i + 1, len(neighbors_list)):
                    a, b = neighbors_list[i], neighbors_list[j]
                    if a == b or (a, b) in checked or (b, a) in checked:
                        continue
                    checked.add((a, b))

                    # Check if a and b are connected
                    if b not in adj.get(a, set()):
                        a_name = entities.get(a, {}).get("name", a)
                        b_name = entities.get(b, {}).get("name", b)
                        eid_name = entities.get(eid, {}).get("name", eid)

                        middles.append({
                            "entity_a": a_name,
                            "entity_b": b_name,
                            "common_neighbor": eid_name,
                            "reason": f"'{a_name}' and '{b_name}' are both connected to "
                                      f"'{eid_name}' but not to each other. A hidden variable "
                                      f"mediating between them may exist.",
                        })

        return middles[:8]

    def _find_explanatory_voids(self, entities: dict, relationships: list) -> list:
        """
        Find clusters of effects/observations with no common cause.
        
        Pattern: Multiple downstream entities (effects) exist,
        but no upstream entity (cause) connects them.
        """
        from collections import defaultdict

        CAUSAL_UPSTREAM = {"causes", "produces", "induces", "triggers",
                           "activates", "enables", "initiates"}
        CAUSAL_DOWNSTREAM = {"causes", "produces", "induces", "triggers",
                             "affects", "influences", "modulates"}

        # Find entities that are only targets (effects) and never sources (causes)
        is_source = set()
        is_target = set()
        for rel in relationships:
            if rel.get("relation", "").lower() in CAUSAL_DOWNSTREAM:
                is_source.add(rel["source"])
                is_target.add(rel["target"])

        pure_effects = is_target - is_source

        if len(pure_effects) < 2:
            return []

        # Group pure effects by what they're near in the graph
        effect_names = []
        for eid in pure_effects:
            name = entities.get(eid, {}).get("name", eid)
            etype = entities.get(eid, {}).get("type", "unknown")
            effect_names.append({"name": name, "type": etype, "id": eid})

        voids = []
        if len(effect_names) >= 2:
            voids.append({
                "effects": [e["name"] for e in effect_names[:6]],
                "effect_types": list(set(e["type"] for e in effect_names)),
                "reason": f"These {len(effect_names)} entities are effects/observations "
                          f"with no identified common cause. A hidden causal factor "
                          f"may explain them all.",
            })

        return voids

    def _format_gaps(self, gaps: list) -> str:
        if not gaps:
            return "No gaps detected."
        text = ""
        for i, g in enumerate(gaps, 1):
            text += f"\n{i}. [{g.get('type', '?')}] {g.get('reason', g.get('description', ''))}\n"
            text += f"   Confidence: {g.get('confidence', g.get('gap_score', '?'))}\n"
        return text

    def _format_anomalies(self, anomalies: list) -> str:
        if not anomalies:
            return "No anomalies detected."
        text = ""
        for i, a in enumerate(anomalies, 1):
            text += f"\n{i}. [{a.get('type', '?')}] {a.get('reason', a.get('observation', ''))}\n"
            text += f"   Confidence: {a.get('confidence', a.get('anomaly_score', '?'))}\n"
        return text

    def _build_graph_context(self) -> str:
        if not self.graph:
            return "No graph available."
        entities = self.graph.entities if hasattr(self.graph, 'entities') else {}
        relationships = self.graph.relationships if hasattr(self.graph, 'relationships') else {}
        types = self._type_counts(entities)
        rel_types = self._relation_counts(relationships)
        return (f"Entities: {len(entities)} ({dict(types.most_common(5))})\n"
                f"Relationships: {len(relationships)} ({dict(rel_types.most_common(5))})")

    def _type_counts(self, entities):
        from collections import Counter
        return Counter(e.get("type", "unknown") for e in entities.values())

    def _relation_counts(self, relationships):
        from collections import Counter
        return Counter(r.get("relation", "unknown") for r in relationships)
