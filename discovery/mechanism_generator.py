"""
mechanism_generator.py — Generate CAUSAL MECHANISMS, not just correlations.

The difference between a research assistant and a discovery engine:
  Research assistant: "X is associated with Y"
  Discovery engine: "X causes Y through mechanism Z, where intermediate step W converts signal"

This module generates causal explanations by:
1. Building causal pathways from graph structure
2. Using Pearl's causal hierarchy (association → intervention → counterfactual)
3. Applying analogical reasoning from known mechanisms
4. LLM-powered creative mechanism synthesis
"""

import json
from typing import List, Dict, Optional


class MechanismGenerator:
    """
    Generate causal mechanisms that explain observed relationships.
    """

    def __init__(self, graph=None, llm_call=None):
        self.graph = graph
        self.llm_call = llm_call

    def generate_mechanisms(self, hidden_variables: list, gaps: list,
                            anomalies: list, topic: str, domain: str,
                            papers: list = None) -> dict:
        """
        Generate causal mechanisms for the proposed hidden variables and observed gaps.

        Returns:
            {
                "mechanisms": [
                    {
                        "name": "...",
                        "type": "causal_pathway|feedback_loop|emergent_property|threshold_effect|cascade",
                        "description": "...",
                        "steps": ["step1", "step2", ...],
                        "inputs": [...],
                        "outputs": [...],
                        "hidden_variable": "...",  # if applicable
                        "explains": [...],
                        "confidence": 0.0-1.0,
                        "causal_level": "association|intervention|counterfactual",
                        "predictions": [...]
                    }
                ]
            }
        """
        if not self.llm_call:
            return {"mechanisms": [], "error": "No LLM client available"}

        # Build context
        hv_text = self._format_hidden_variables(hidden_variables[:5])
        gap_text = self._format_gaps(gaps[:4])
        anomaly_text = self._format_anomalies(anomalies[:4])
        graph_context = self._build_graph_context()

        paper_context = ""
        if papers:
            for p in papers[:5]:
                abstract = p.get("abstract", "")[:250]
                if abstract:
                    paper_context += f"\n- [{p.get('title', '?')}] {abstract}\n"

        # Get existing causal relationships from graph
        causal_context = self._extract_causal_chains()

        prompt = f"""You are a mechanistic scientist — you explain HOW things work, not just THAT they correlate.

TOPIC: {topic}
DOMAIN: {domain}

HIDDEN VARIABLES PROPOSED:
{hv_text}

KNOWLEDGE GAPS:
{gap_text}

ANOMALIES:
{anomaly_text}

EXISTING CAUSAL CHAINS IN KNOWLEDGE GRAPH:
{causal_context}

PAPERS:
{paper_context}

Your task: generate CAUSAL MECHANISMS that explain the observations.

A mechanism is NOT just "X causes Y." A mechanism is:
  "X activates pathway P with rate constant k1, which produces intermediate I
   at concentration [I] = k1[X]/k2, which converts to effect Y when [I] > threshold"

Before generating mechanisms, think through this structured reasoning:

<discovery_reasoning>
1. WHAT DO I KNOW? — List the key observations, anomalies, and gaps from the context.
2. WHAT COULD EXPLAIN THIS? — Brainstorm at least 5 possible mechanisms (including conventional ones).
3. WHICH ARE MOST PROMISING? — Rank by: (a) explains the most observations, (b) has existing evidence, (c) is testable.
4. WHAT EQUATIONS APPLY? — For each promising mechanism, identify what known equations could govern it.
5. CAN I DERIVE ANYTHING? — If any equation can be derived from first principles, do the derivation.
6. WHAT WOULD FALSIFY EACH? — For each mechanism, state what observation would kill it.
</discovery_reasoning>

REQUIREMENTS — prefer quantitative, derive when possible:
1. PREFER quantitative relationships (equations, rates, thresholds). If no equation exists
   yet, provide the physical quantity and how it couples to observables.
2. Ground in existing literature when possible. For novel mechanisms, state what known
   physics it extends or combines.
3. DERIVATION: If an equation can be derived from known physics, SHOW THE DERIVATION.
   Don't just state the result — show the steps. Example:
     "From Newton's second law and the gravitational force law:
      F = ma = GMm/r² → a = GM/r² → for M = 10³⁰ kg, r = 7×10⁸ m: a ≈ 0.006 m/s²"
   A derived value is stronger than an estimated one.
4. PREFER predictions with MAGNITUDE. If no magnitude is possible, state the direction
   and what measurement would constrain it.
5. Identify the KEY PARAMETER that controls the mechanism and its expected range.
6. Distinguish: is this a KNOWN mechanism applied in new context, or genuinely NOVEL?
   Also classify: is this NEW synthesis of existing data, or NEW physics?
7. EPISTEMIC LABELING: For every key_parameter, label its source:
   - "cited": the value/range comes from a specific paper (cite it)
   - "derived": the value is CALCULATED from other parameters — show the derivation
   - "estimated": your best physical estimate, NOT from literature — state reasoning
   NEVER present an estimated value as cited. Transparency > confidence.

For each mechanism, provide:
1. A clear name (descriptive, not creative)
2. Type (causal_pathway, feedback_loop, emergent_property, threshold_effect, cascade)
3. Step-by-step causal chain (minimum 3 steps, each with quantitative content)
4. Mathematical model: equations governing the mechanism, rate constants, thresholds
5. Literature grounding: what existing mechanisms is this based on?
6. Inputs and outputs (with expected magnitudes)
7. Which hidden variable it instantiates (if any)
8. Quantitative predictions with expected magnitudes
9. Key parameter to measure and its expected range
10. Falsification: specific quantitative threshold

Output JSON:
{{
  "mechanisms": [
    {{
      "name": "Descriptive Mechanism Name",
      "type": "causal_pathway|feedback_loop|emergent_property|threshold_effect|cascade",
      "description": "Detailed description with quantitative content",
      "steps": [
        "Step 1: Initial trigger — [what happens] with [quantitative detail]",
        "Step 2: Intermediate process — [rate/threshold/concentration]",
        "Step 3: Final effect — [magnitude of effect]"
      ],
      "mathematical_model": "Equations governing this mechanism (e.g. rate equations, thresholds)",
      "derivation": "If the equation can be derived from known physics, show the derivation steps here. Otherwise state 'not derivable — estimated from [reasoning]'",
      "classification": "new_synthesis|new_physics|new_context_for_known|replication",
      "key_parameters": [
        {{"name": "parameter_name", "expected_value": "order of magnitude or range", "units": "units", "source": "cited|derived|estimated", "source_detail": "paper citation or derivation basis or estimation rationale"}}
      ],
      "literature_basis": ["cite 2-3 related known mechanisms or papers"],
      "is_novel_vs_known": "novel|extension_of_known|new_context_for_known",
      "inputs": ["what goes in (with magnitude)"],
      "outputs": ["what comes out (with magnitude)"],
      "hidden_variable": "which hidden variable this explains (if any)",
      "explains": ["observation 1", "anomaly 2"],
      "confidence": 0.0-1.0,
      "causal_level": "association|intervention|counterfactual",
      "predictions": [
        "If you intervene on X by amount A, Y should change by amount B",
        "Counterfactual: if X hadn't happened, Y would differ by amount C"
      ],
      "key_parameter_to_measure": "What single measurement would confirm this?",
      "falsification": "Specific quantitative observation that disproves this"
    }}
  ]
}}

Generate 3-5 mechanisms. Each must have at least 3 causal steps. 
Prefer mechanisms that make counterfactual predictions (most powerful causal level)."""

        try:
            raw = self.llm_call(prompt, max_tokens=8192)
            # Fallback: if primary provider fails, try the other
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
                    for m in result.get("mechanisms", []):
                        m.setdefault("name", "Unnamed Mechanism")
                        m.setdefault("type", "causal_pathway")
                        m.setdefault("steps", [])
                        m.setdefault("confidence", 0.5)
                        m.setdefault("causal_level", "association")
                        m.setdefault("predictions", [])
                        # Ensure minimum 2 steps
                        if len(m["steps"]) < 2:
                            m["steps"] = [m.get("description", "Unknown mechanism")]
                        # Validate epistemic labels on key_parameters
                        self._validate_parameter_sources(m, papers or [])
                    return result

        except Exception as e:
            return {"mechanisms": [], "error": str(e)}

        return {"mechanisms": []}

    def generate_from_graph_paths(self, topic: str, domain: str) -> dict:
        """
        Generate mechanisms by analyzing existing graph paths and 
        proposing extensions/completions.
        """
        if not self.graph or not self.llm_call:
            return {"mechanisms": []}

        entities = self.graph.entities if hasattr(self.graph, 'entities') else {}
        relationships = self.graph.relationships if hasattr(self.graph, 'relationships') else []

        # Find incomplete causal chains
        incomplete = self._find_incomplete_chains(entities, relationships)

        if not incomplete:
            return {"mechanisms": []}

        prompt = f"""You have a knowledge graph with {len(entities)} entities and {len(relationships)} relationships.
Topic: {topic}, Domain: {domain}

INCOMPLETE CAUSAL CHAINS (paths that exist but are missing steps):
{json.dumps(incomplete[:5], indent=2)}

For each incomplete chain, propose the MISSING MECHANISM STEPS that would complete it.

Output JSON:
{{
  "mechanisms": [
    {{
      "name": "...",
      "description": "...",
      "completes_chain": "A → ? → B",
      "proposed_steps": ["A activates X", "X converts to Y", "Y inhibits B"],
      "confidence": 0.0-1.0,
      "predictions": ["..."]
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

        return {"mechanisms": []}

    def _find_incomplete_chains(self, entities: dict, relationships: list) -> list:
        """
        Find paths where the causal chain is broken — A leads to D
        but the intermediate steps B, C are missing.
        """
        from collections import defaultdict

        adj = defaultdict(list)
        for rel in relationships:
            adj[rel["source"]].append({
                "target": rel["target"],
                "relation": rel.get("relation", "related_to")
            })

        incomplete = []
        checked = set()

        # Find pairs connected by long paths but missing intermediates
        for eid in entities:
            direct_neighbors = {r["target"] for r in adj.get(eid, set())}

            # Check 2-hop neighbors
            for hop1 in adj.get(eid, set()):
                for hop2 in adj.get(hop1["target"], set()):
                    target = hop2["target"]
                    if target == eid:
                        continue
                    key = (eid, target)
                    if key in checked:
                        continue
                    checked.add(key)

                    # If there's a 2-hop path but no direct connection
                    if target not in direct_neighbors:
                        a_name = entities.get(eid, {}).get("name", eid)
                        c_name = entities.get(target, {}).get("name", target)
                        b_name = entities.get(hop1["target"], {}).get("name", hop1["target"])

                        incomplete.append({
                            "start": a_name,
                            "end": c_name,
                            "known_intermediate": b_name,
                            "path": f"{a_name} --{hop1['relation']}--> {b_name} --{hop2['relation']}--> {c_name}",
                            "gap": f"Is there a more direct mechanism from {a_name} to {c_name}?",
                        })

        return incomplete[:6]

    def _extract_causal_chains(self) -> str:
        """Extract existing causal chains from the graph for context."""
        if not self.graph:
            return "No graph available."

        relationships = self.graph.relationships if hasattr(self.graph, 'relationships') else []
        entities = self.graph.entities if hasattr(self.graph, 'entities') else {}

        CAUSAL = {"causes", "activates", "inhibits", "produces", "enables",
                  "prevents", "induces", "triggers", "mediates", "regulates"}

        chains = []
        for rel in relationships:
            if rel.get("relation", "").lower() in CAUSAL:
                src = entities.get(rel["source"], {}).get("name", rel["source"])
                tgt = entities.get(rel["target"], {}).get("name", rel["target"])
                rel_name = rel.get("relation", "?")
                conf = rel.get("confidence", 0.5)
                chains.append(f"  {src} --{rel_name}--> {tgt} (conf: {conf:.2f})")

        if not chains:
            return "No causal relationships found in graph."

        return "Existing causal relationships:\n" + "\n".join(chains[:15])

    def _format_hidden_variables(self, hvs: list) -> str:
        if not hvs:
            return "No hidden variables proposed yet."
        text = ""
        for i, hv in enumerate(hvs, 1):
            text += f"\n{i}. {hv.get('name', '?')} ({hv.get('type', '?')})\n"
            text += f"   {hv.get('description', '')[:200]}\n"
            text += f"   Predictions: {hv.get('predictions', [])}\n"
        return text

    def _format_gaps(self, gaps: list) -> str:
        if not gaps:
            return "No gaps."
        return "\n".join(f"- [{g.get('type', '?')}] {g.get('reason', '')[:150]}" for g in gaps)

    def _format_anomalies(self, anomalies: list) -> str:
        if not anomalies:
            return "No anomalies."
        return "\n".join(f"- [{a.get('type', '?')}] {a.get('reason', '')[:150]}" for a in anomalies)

    def _build_graph_context(self) -> str:
        if not self.graph:
            return "No graph."
        entities = self.graph.entities if hasattr(self.graph, 'entities') else {}
        relationships = self.graph.relationships if hasattr(self.graph, 'relationships') else {}
        return f"Graph: {len(entities)} entities, {len(relationships)} relationships"

    def _validate_parameter_sources(self, mechanism: dict, papers: list):
        """
        Validate epistemic labels on key_parameters.
        If LLM claims 'cited' but the value isn't traceable to provided papers,
        downgrade to 'estimated'. This prevents hallucinated citations.
        """
        # Build searchable text from paper abstracts and titles
        paper_text = ""
        for p in papers:
            if isinstance(p, dict):
                paper_text += " " + p.get("title", "") + " " + p.get("abstract", "")
        paper_text = paper_text.lower()

        # Also check literature_basis from the mechanism itself
        lit_basis = mechanism.get("literature_basis", [])
        lit_text = " ".join(str(x) for x in lit_basis).lower()

        combined_context = paper_text + " " + lit_text

        key_params = mechanism.get("key_parameters", [])
        if not key_params:
            return

        for kp in key_params:
            if not isinstance(kp, dict):
                continue

            source = kp.get("source", "")
            source_detail = kp.get("source_detail", "")
            expected_value = str(kp.get("expected_value", ""))
            param_name = kp.get("name", "")

            # Ensure source field exists
            if not source:
                kp["source"] = "estimated"
                kp["source_detail"] = "No source label provided — defaulting to estimated"
                continue

            # If claimed 'cited', verify the citation is traceable
            if source == "cited":
                # Check if source_detail references a real paper
                if not source_detail:
                    kp["source"] = "estimated"
                    kp["source_detail"] = "Claimed cited but no citation provided — downgraded to estimated"
                    continue

                # Check if any keywords from the citation appear in our papers
                citation_words = set(source_detail.lower().split())
                # Remove common words
                stop_words = {"the", "a", "an", "in", "of", "to", "for", "and", "or", "by", "et", "al", "from"}
                citation_words -= stop_words
                citation_words = {w for w in citation_words if len(w) > 3}

                if citation_words:
                    matches = sum(1 for w in citation_words if w in combined_context)
                    # If less than 20% of citation words appear in our papers, it's suspicious
                    if matches < max(1, len(citation_words) * 0.2):
                        kp["source"] = "estimated"
                        kp["source_detail"] = f"Claimed cited ('{source_detail[:80]}') but could not verify against provided literature — downgraded to estimated. Original claim preserved."
                        kp["original_source_claim"] = source_detail

            # If 'derived', verify there's a derivation basis
            elif source == "derived":
                if not source_detail:
                    kp["source"] = "estimated"
                    kp["source_detail"] = "Claimed derived but no derivation shown — downgraded to estimated"

            # 'estimated' is always valid — no validation needed
