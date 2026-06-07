"""
mechanism_discovery.py — RUMI Mechanism Discovery Engine

For every unexplained correlation, search for:
- conservation_laws
- intermediate_variables
- latent_variables
- energy_flow
- information_flow
- causal_paths

Generate mechanism candidates, simulate each, reject unsupported ones.
"""

import json
from typing import List, Dict, Optional
from discovery.json_extract import extract_json


class MechanismDiscoveryEngine:
    """
    Discover mechanisms for unexplained correlations.
    """

    def __init__(self, graph=None, llm_call=None):
        self.graph = graph
        self.llm_call = llm_call

    def discover_mechanisms(self, correlations: list, topic: str, domain: str,
                           papers: list = None) -> dict:
        """
        For each unexplained correlation, propose mechanism candidates.

        Args:
            correlations: list of {"entity_a": ..., "entity_b": ..., "relation": ..., "evidence": ...}
            topic: research topic
            domain: scientific domain
            papers: supporting papers

        Returns:
            {
                "mechanisms": [
                    {
                        "correlation": "A correlates with B",
                        "candidates": [
                            {
                                "name": "Mechanism name",
                                "type": "conservation_law|intermediate_variable|latent_variable|energy_flow|information_flow|causal_path",
                                "causal_chain": ["step1", "step2", "step3"],
                                "inputs": ["what goes in"],
                                "outputs": ["what comes out"],
                                "state_variables": ["variables that change"],
                                "observables": ["what we can measure"],
                                "conservation_law": "if applicable",
                                "energy_flow": "if applicable",
                                "information_flow": "if applicable",
                                "confidence": 0.0-1.0,
                                "status": "speculative|supported|verified"
                            }
                        ]
                    }
                ]
            }
        """
        if not self.llm_call:
            return {"mechanisms": [], "error": "No LLM client available"}

        results = []

        for corr in correlations[:5]:
            entity_a = corr.get("entity_a", "")
            entity_b = corr.get("entity_b", "")
            relation = corr.get("relation", "")
            evidence = corr.get("evidence", "")

            prompt = f"""You are a mechanistic scientist. For this unexplained correlation, propose mechanism candidates.

CORRELATION: {entity_a} {relation} {entity_b}
EVIDENCE: {evidence}
TOPIC: {topic}
DOMAIN: {domain}

For each mechanism candidate, provide:
1. name: descriptive name
2. type: conservation_law | intermediate_variable | latent_variable | energy_flow | information_flow | causal_path
3. causal_chain: step-by-step mechanism (minimum 3 steps)
4. inputs: what goes into the mechanism
5. outputs: what comes out
6. state_variables: variables that change during the mechanism
7. observables: what we can measure to verify this mechanism
8. conservation_law: if applicable (e.g., "energy conservation", "charge conservation")
9. energy_flow: if applicable (e.g., "kinetic → potential → thermal")
10. information_flow: if applicable (e.g., "signal → processing → response")
11. confidence: 0.0-1.0
12. status: speculative | supported | verified

Generate 2-3 mechanism candidates for this correlation.

CRITICAL: Output ONLY valid JSON. No prose, no explanation, no markdown.

Output JSON:
{{
  "correlation": "{entity_a} {relation} {entity_b}",
  "candidates": [
    {{
      "name": "Mechanism name",
      "type": "conservation_law|intermediate_variable|latent_variable|energy_flow|information_flow|causal_path",
      "causal_chain": ["step1", "step2", "step3"],
      "inputs": ["input1"],
      "outputs": ["output1"],
      "state_variables": ["var1"],
      "observables": ["observable1"],
      "conservation_law": "",
      "energy_flow": "",
      "information_flow": "",
      "confidence": 0.5,
      "status": "speculative"
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
                        # Use extract_json which has brace-counting parser
                        result = extract_json(raw, expected_key="candidates")
                        if result is None:
                            result = extract_json(raw)  # try without expected_key
                    else:
                        result = raw

                    # Accept both "candidates" and "mechanisms" as the key
                    candidates_key = None
                    if isinstance(result, dict):
                        if "candidates" in result:
                            candidates_key = "candidates"
                        elif "mechanisms" in result:
                            candidates_key = "mechanisms"

                    if candidates_key:
                        # Validate candidates — require causal_chain, observables optional
                        valid_candidates = []
                        for c in result[candidates_key]:
                            chain = c.get("causal_chain") or c.get("steps") or []
                            if len(chain) >= 2:
                                # Ensure name exists
                                if not c.get("name"):
                                    c["name"] = f"Mechanism: {c.get('type', 'causal_pathway')}"
                                valid_candidates.append(c)
                        result["candidates"] = valid_candidates
                        results.append(result)
            except Exception:
                continue

        return {"mechanisms": results}

    def discover_from_graph(self, topic: str, domain: str) -> dict:
        """
        Discover mechanisms from graph structure — find unexplained correlations.
        """
        if not self.graph:
            return {"mechanisms": []}

        entities = self.graph.entities if hasattr(self.graph, 'entities') else {}
        relationships = self.graph.relationships if hasattr(self.graph, 'relationships') else []

        # Find unexplained correlations
        correlations = []

        # Look for entities that co-occur but lack causal explanation
        for r in relationships:
            src_id = r.get("source", "")
            tgt_id = r.get("target", "")
            rel = r.get("relation", "")

            # Check if this relationship has a causal explanation
            has_causal = any(kw in rel.lower() for kw in [
                "causes", "leads to", "produces", "generates", "triggers", "mediates"
            ])

            if not has_causal and src_id and tgt_id:
                # Use human-readable names instead of entity IDs
                src_name = entities.get(src_id, {}).get("name", src_id)
                tgt_name = entities.get(tgt_id, {}).get("name", tgt_id)
                correlations.append({
                    "entity_a": src_name,
                    "entity_b": tgt_name,
                    "relation": rel,
                    "evidence": f"Graph relationship: {src_name} --[{rel}]--> {tgt_name}",
                })

        if not correlations:
            return {"mechanisms": []}

        # Use LLM to discover mechanisms for top correlations
        if self.llm_call:
            return self.discover_mechanisms(correlations[:5], topic, domain)

        return {"mechanisms": []}
