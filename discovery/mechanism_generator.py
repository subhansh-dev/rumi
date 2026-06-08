"""
import sys as _sys
if _sys.platform == "win32":
    try:
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
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
                            papers: list = None, archive_context: str = "",
                            constraint: dict = None) -> dict:
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

        # Build constraint text for Track B (curiosity-driven) pipeline
        # SOFT constraint: encourages novel mechanisms without forbidding existing ones
        constraint_text = ""
        if constraint and isinstance(constraint, dict):
            forbidden = constraint.get("forbidden_theories", [])
            required = constraint.get("required_properties", [])
            direction = constraint.get("novelty_direction", "")
            custom_prompt = constraint.get("constraint_prompt", "")

            if forbidden or required or custom_prompt:
                constraint_text = "\n\n" + "=" * 60 + "\n"
                constraint_text += "CURIOSITY-DRIVEN DISCOVERY — Novel Mechanisms\n"
                constraint_text += "=" * 60 + "\n\n"
                constraint_text += f"Core Question: {constraint.get('core_question', topic)}\n\n"

                if forbidden:
                    constraint_text += "KNOWN THEORIES IN THIS SPACE (for reference, not reproduction):\n"
                    for f_theory in forbidden:
                        constraint_text += f"  - {f_theory}\n"
                    constraint_text += "\nThese are well-known. Your goal is to go BEYOND them with novel mechanisms.\n"
                    constraint_text += "If you reference any of these, you MUST extend them with a genuinely new element.\n\n"

                if required:
                    constraint_text += "DESIRABLE PROPERTIES (aim for these, but not all are mandatory):\n"
                    for prop in required:
                        constraint_text += f"  + {prop}\n"
                    constraint_text += "\n"

                if direction:
                    constraint_text += f"NOVELTY DIRECTION: {direction}\n\n"

                if custom_prompt:
                    constraint_text += custom_prompt + "\n\n"

                constraint_text += "Your task: Generate mechanisms from FIRST PRINCIPLES. Prefer novel approaches over well-known ones.\n"
                constraint_text += "It is OK to reference known theories if you extend them with new elements.\n"

        prompt = f"""You are a mechanistic scientist — you DERIVE how things work from first principles.

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

{archive_context}

PAPERS:
{paper_context}
{constraint_text}

Your task: DERIVE causal mechanisms from first principles. Do NOT just describe — DERIVE.

A mechanism WITHOUT derivation is HAND-WAVING. A mechanism WITH derivation is SCIENCE.

Before generating mechanisms, think through this structured reasoning:

<discovery_reasoning>
1. WHAT DO I KNOW? — List the key observations, anomalies, and gaps from the context.
2. WHAT COULD EXPLAIN THIS? — Brainstorm at least 5 possible mechanisms (including conventional ones).
3. WHICH ARE MOST PROMISING? — Rank by: (a) explains the most observations, (b) has existing evidence, (c) is testable.
4. WHAT EQUATIONS APPLY? — For each promising mechanism, identify what known equations could govern it.
5. CAN I DERIVE ANYTHING? — If any equation can be derived from first principles, do the derivation.
6. WHAT WOULD FALSIFY EACH? — For each mechanism, state what observation would kill it.
</discovery_reasoning>

CRITICAL REQUIREMENT — EVERY MECHANISM MUST HAVE A DERIVATION:

For EACH mechanism, you MUST provide a step-by-step derivation that shows HOW you got from first principles to the result. A mechanism without derivation will be REJECTED.

DERIVATION TEMPLATE (you MUST follow this structure):

Step 1: STARTING ASSUMPTIONS
  - State every assumption explicitly
  - BAD: "Assume the viscosity is high" (vague = REJECTED)
  - GOOD: "Assume DM self-interaction cross-section sigma/m = 0.1-10 cm2/g (PDG 2023)"

Step 2: GOVERNING EQUATION
  - Write the equation that governs the mechanism
  - BAD: "The rate depends on temperature" (no equation = REJECTED)
  - GOOD: "From Boltzmann transport theory: df/dt = C[f,f] where C is the collision operator"

Step 3: DERIVATION STEPS
  - Show each mathematical step from the governing equation to the result
  - BAD: "Therefore viscosity = rho * v * l" (no derivation = REJECTED)
  - GOOD: "Taking the Chapman-Enskog expansion of C[f,f]:
    eta = (5/16) * sqrt(pi*m*k_B*T) / (pi*sigma^2*Omega^{2,2})
    where Omega^{2,2} is the collision integral"

Step 4: TRANSPORT COEFFICIENTS
  - Derive or cite every coefficient — NEVER assume
  - BAD: "eta_DM ~ 1e28 cm2/s" (assumed = REJECTED)
  - GOOD: "From Step 3 with sigma/m = 1 cm2/g, T = 1 keV, n = 1e-3 cm^-3:
    eta_DM = 5.2e27 cm2/s (derived)"

Step 5: NUMERICAL CHECK
  - Plug in numbers and verify the result is physically reasonable
  - BAD: "The effect is significant" (no numbers = REJECTED)
  - GOOD: "For rho_DM = 0.3 GeV/cm3, v = 200 km/s, l = 1 kpc:
    eta_DM * |dv/dr| ~ 1e-30 g/cm/s2 (compare to gravity ~ 1e-8 g/cm/s2)"

EXAMPLE OF A COMPLETE MECHANISM:

Mechanism: Viscous Dark-Matter Halo Core Formation

Step 1 (Assumptions):
  - DM self-interaction cross-section: sigma/m = 1 cm2/g (consistent with Bullet Cluster)
  - DM density in halo center: rho = 0.3 GeV/cm3
  - DM velocity dispersion: v = 200 km/s

Step 2 (Governing equation):
  - From kinetic theory: eta = (1/3) * n * m * v * l_mean_free
  - Mean free path: l = 1/(n * sigma) = m/(rho * sigma)

Step 3 (Derivation):
  - Substituting: eta = (1/3) * (rho/m) * m * v * m/(rho * sigma)
  - Simplifying: eta = v * m / (3 * sigma)
  - With sigma/m = 1 cm2/g: eta = v / (3 * (sigma/m)) = 200 km/s / (3 * 1 cm2/g)

Step 4 (Transport coefficient):
  - eta_DM = 2e5 cm/s / (3 * 1 cm2/g) = 6.7e4 g/(cm*s)
  - This is ~10^10 times smaller than water viscosity — very fluid

Step 5 (Numerical check):
  - Core formation timescale: t_core = R^2 / (eta/rho) = (1 kpc)^2 / (6.7e4/0.3) ~ 10 Gyr
  - This is comparable to the age of the universe — consistent with observed cores

REQUIREMENTS:
1. EVERY mechanism MUST have Steps 1-5 above. Missing any step = REJECTED.
2. EVERY coefficient MUST be derived or cited — NEVER assumed.
3. EVERY prediction MUST follow from the derivation — NOT from intuition.
4. Distinguish: is this a KNOWN mechanism applied in new context, or genuinely NOVEL?
5. EPISTEMIC LABELING: For every parameter:
   - "cited": value from a specific paper (cite it)
   - "derived": CALCULATED from other parameters — show derivation
   - "estimated": physical estimate — state reasoning
   NEVER present an estimated value as cited.

For each mechanism, provide:
1. A clear name (descriptive, not creative)
2. Type (causal_pathway, feedback_loop, emergent_property, threshold_effect, cascade)
3. Step-by-step derivation (Steps 1-5 above — REQUIRED)
4. Mathematical model: equations from the derivation
5. Literature grounding: what existing mechanisms is this based on?
6. Inputs and outputs (with expected magnitudes from derivation)
7. Which hidden variable it instantiates (if any)
8. Quantitative predictions (derived from the math, not guessed)
9. Key parameter to measure and its expected range
10. Falsification: specific quantitative threshold

CRITICAL REQUIREMENTS — FAILURE TO FOLLOW = REJECTION:

1. EVERY mechanism MUST contain Steps 1-5 (assumptions, governing equation, derivation, transport coefficients, numerical check).
   If you skip any step, the mechanism is INCOMPLETE and will be REJECTED.
   BAD: "The coupling coefficient quantifies how efficiently..." (no derivation = REJECTED)
   GOOD: "mu_ec = sigma_s / (rho_B * v_A^2) where sigma_s ~ 10^15 dyn/cm^2"
   BAD: "The binding affinity is low" (no equation = REJECTED)
   GOOD: "Kd = k_off / k_on ~ 10 nM where k_on ~ 10^6 M^-1 s^-1"

2. EVERY step in the causal chain MUST include a quantitative value (number with units).
   BAD: "The temperature increases" (no value = REJECTED)
   GOOD: "The temperature increases from T1 = 300K to T2 = 1500K"

3. EVERY mechanism MUST be a PHYSICAL, CHEMICAL, or BIOLOGICAL process.
   BAD: "Funding-driven organizational activation" (not science = REJECTED)
   BAD: "Market-driven resource allocation" (not science = REJECTED)
   GOOD: "Photon-graviton conversion via kinetic mixing"

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
        {{"name": "parameter_name", "expected_value": "order of magnitude or range", "units": "units", "source": "cited|derived|estimated", "source_detail": "paper citation or derivation basis or estimation rationale", "derivation_chain": ["step 1: start from equation X", "step 2: substitute values", "step 3: result = Z — leave empty if source is not derived"]}}
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
            if raw:
                print(f"    [DEBUG] mechanisms: LLM returned {len(raw)} chars", flush=True)
            # Fallback: if primary provider fails, try the other
            if not raw:
                try:
                    from discovery.llm_client import call_json
                    raw = call_json(prompt, max_tokens=8192, provider="auto")
                    if raw:
                        print(f"    [DEBUG] mechanisms: call_json returned {len(raw)} chars", flush=True)
                except Exception:
                    pass
            if not raw:
                print(f"    [WARN] mechanisms: LLM returned None on all providers", flush=True)
            if raw:
                from discovery.json_extract import extract_json
                result = extract_json(raw, expected_key="mechanisms")
                if result is None and isinstance(raw, str):
                    print(f"    [WARN] mechanisms: JSON extraction failed ({len(raw)} chars)", flush=True)
                    print(f"    [DEBUG] raw[:500]: {repr(raw[:500])}", flush=True)
                elif result:
                    mechs = result.get("mechanisms", [])
                    print(f"    [DEBUG] mechanisms: extracted {len(mechs)} items, keys={list(result.keys())}", flush=True)
                    if not mechs:
                        print(f"    [DEBUG] raw[:500]: {repr(raw[:500])}", flush=True)

                if isinstance(result, dict):
                    valid_mechanisms = []
                    for m in result.get("mechanisms", []):
                        # Skip schema-like objects (type: "object" with no real content)
                        if m.get("type") == "object" and not m.get("description") and not m.get("steps"):
                            continue
                        # Extract name from multiple possible fields
                        if not m.get("name") or m.get("name") in ("Unnamed Mechanism", "", "object"):
                            m["name"] = (
                                m.get("mechanism_name") or
                                m.get("correlation") or
                                m.get("description", "")[:60] or
                                m.get("type", "causal_pathway")
                            )
                        # Skip if name is still generic
                        if m.get("name") in ("object", "causal_pathway", ""):
                            continue
                        # Reject non-scientific mechanisms
                        desc_lower = (m.get("description", "") + " " + m.get("name", "")).lower()
                        non_scientific = [
                            "funding", "organizational", "market", "economic", "political",
                            "social", "management", "administrative", "bureaucratic",
                            "funding-driven", "market-driven", "resource allocation",
                        ]
                        if any(term in desc_lower for term in non_scientific):
                            continue
                        m.setdefault("type", "causal_pathway")
                        m.setdefault("steps", [])
                        m.setdefault("confidence", 0.5)
                        m.setdefault("causal_level", "association")
                        m.setdefault("predictions", [])
                        # Ensure minimum 2 steps
                        if len(m["steps"]) < 2:
                            desc = m.get("description", m.get("mechanism", ""))
                            m["steps"] = [desc] if desc else ["Mechanism to be determined"]
                        # Validate epistemic labels on key_parameters
                        self._validate_parameter_sources(m, papers or [])
                        valid_mechanisms.append(m)
                    result["mechanisms"] = valid_mechanisms
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
                    raw = call_json(prompt, max_tokens=4096, provider="auto")
                except Exception:
                    pass
            if raw:
                from discovery.json_extract import extract_json
                result = extract_json(raw, expected_key="mechanisms")
                if result is None and isinstance(raw, str):
                    print(f"    [WARN] mechanisms (causal): JSON extraction failed ({len(raw)} chars)", flush=True)
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
            src = rel.get("source")
            tgt = rel.get("target")
            if src and tgt:
                adj[src].append({
                    "target": tgt,
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
                try:
                    conf_str = f"{float(conf):.2f}"
                except (ValueError, TypeError):
                    conf_str = str(conf)
                chains.append(f"  {src} --{rel_name}--> {tgt} (conf: {conf_str})")

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
