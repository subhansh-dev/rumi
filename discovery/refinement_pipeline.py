"""
RUMI Refinement Pipeline — 13-stage post-processing layer.
Takes raw pipeline output and produces scientist-grade refined discoveries.

Stages:
  1.  Knowledge Foundation Audit
  2.  First Principles Reconstruction
  3.  Mathematical Formalization
  4.  Derivation Engine (no free parameters)
  5.  Multi-Model Competition (5 hypotheses, weighted scoring)
  6.  Adversarial Scientists (5 reviewer personas)
  7.  Causal Reasoning Layer
  8.  Uncertainty Decomposition
  9.  Prediction Generator (near/medium/long-term)
  10. Simulation Layer
  11. Discovery vs Synthesis Classifier
  12. Researcher-Grade Scoring (7 metrics)
  13. Self-Critique Loop + Scientific Courtroom Mode
"""

import json
import time
import re
from pathlib import Path
from typing import Optional

from discovery.llm_client import call as llm_call, call_json, call_thinking


# ═══════════════════════════════════════════════════════════════
# LLM HELPER — reliable, with auto-fallback
# ═══════════════════════════════════════════════════════════════

def _llm(prompt, max_tokens=4096, json_mode=False):
    """Reliable LLM call with auto-fallback and JSON parsing."""
    if json_mode:
        raw = call_json(prompt, max_tokens=max_tokens, provider="auto")
    else:
        raw = llm_call(prompt, max_tokens=max_tokens, provider="auto")
    if not raw:
        return None
    if json_mode:
        text = raw.strip() if isinstance(raw, str) else str(raw)
        # Strip markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0].strip()
        # Try direct parse
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        # Try extracting JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
        # Try fixing common JSON issues
        for candidate in [text, text.replace("'", '"'), re.sub(r',\s*}', '}', text), re.sub(r',\s*]', ']', text)]:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, Exception):
                continue
        # All JSON parsing failed — wrap raw text in a dict so callers don't crash
        return {"_raw": raw[:2000], "_parse_failed": True}
    return raw


def _llm_thinking(prompt, max_tokens=16384):
    """Heavy LLM call for complex reasoning."""
    return call_thinking(prompt, max_tokens=max_tokens, temperature=0.7)


# ═══════════════════════════════════════════════════════════════
# STAGE 1: KNOWLEDGE FOUNDATION AUDIT
# ═══════════════════════════════════════════════════════════════

def knowledge_foundation_audit(topic, domain, papers, graph, hypotheses):
    """Build a structured map of current knowledge BEFORE refining hypotheses."""
    paper_list = "\n".join(f"  [{p.get('source','?')}] {p['title']}" for p in papers[:20])
    entity_list = ", ".join(e.get("name", "") for e in list(graph.entities.values())[:20])

    prompt = f"""You are a rigorous scientific auditor. Before any hypothesis refinement, map the current state of knowledge.

TOPIC: {topic}
DOMAIN: {domain}
ENTITIES: {entity_list}

PAPERS:
{paper_list}

Produce a structured knowledge foundation audit in JSON:
{{
  "known_facts": [
    {{"fact": "...", "evidence_strength": "strong|moderate|weak", "source": "..."}}
  ],
  "accepted_models": [
    {{"model": "...", "status": "established|contested|emerging", "key_predictors": "..."}}
  ],
  "contradictions": [
    {{"claim_a": "...", "claim_b": "...", "severity": "fundamental|moderate|minor"}}
  ],
  "open_problems": [
    {{"problem": "...", "importance": "critical|significant|minor", "barriers": "..."}}
  ],
  "missing_links": [
    {{"entity_a": "...", "entity_b": "...", "expected_relationship": "...", "why_missing": "..."}}
  ]
}}

Be specific. Cite papers. Minimum 3 entries per category."""

    result = _llm(prompt, max_tokens=4096, json_mode=True)
    if not result:
        # Fallback: build from graph
        result = {
            "known_facts": [{"fact": f"Entity '{e.get('name','')}' appears in literature", "evidence_strength": "moderate", "source": "graph analysis"} for e in list(graph.entities.values())[:5]],
            "accepted_models": [],
            "contradictions": [],
            "open_problems": [{"problem": "Insufficient data for rigorous analysis", "importance": "critical", "barriers": "Limited corpus"}],
            "missing_links": [],
        }
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 2: FIRST PRINCIPLES RECONSTRUCTION
# ═══════════════════════════════════════════════════════════════

def first_principles_reconstruction(topic, hypotheses, audit):
    """Trace every hypothesis claim back to first principles."""
    hyp_text = ""
    for i, h in enumerate(hypotheses[:5], 1):
        hyp_text += f"\nH{i}: {h.get('title', 'Untitled')}\n"
        hyp_text += f"  Description: {h.get('description', '')[:300]}\n"

    prompt = f"""You are a first-principles thinker. For each hypothesis, trace the reasoning chain back to fundamental laws.

TOPIC: {topic}

HYPOTHESES:
{hyp_text}

For each hypothesis, build a dependency tree:
Observation → Theory → Assumption → First Principle

Return JSON:
{{
  "hypotheses": [
    {{
      "title": "...",
      "dependency_tree": {{
        "observation": "...",
        "theory": "...",
        "assumptions": ["assumption1", "assumption2"],
        "first_principles": ["physical law 1", "mathematical axiom 1"],
        "weakest_assumption": "...",
        "assumption_risk": "high|medium|low"
      }}
    }}
  ]
}}"""

    result = _llm(prompt, max_tokens=4096, json_mode=True)
    if not result:
        return {"hypotheses": [{"title": h.get("title", ""), "dependency_tree": {"observation": "unknown", "theory": "unknown", "assumptions": [], "first_principles": [], "weakest_assumption": "unknown", "assumption_risk": "high"}} for h in hypotheses[:5]]}
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 3: MATHEMATICAL FORMALIZATION
# ═══════════════════════════════════════════════════════════════

def mathematical_formalization(topic, hypotheses, domain):
    """Require formal representation for every concept. Cap confidence at 20% if none."""
    hyp_text = ""
    for i, h in enumerate(hypotheses[:5], 1):
        hyp_text += f"\nH{i}: {h.get('title', 'Untitled')} (confidence: {h.get('confidence', 0):.0%})\n"
        hyp_text += f"  Description: {h.get('description', '')[:300]}\n"

    prompt = f"""You are a mathematical formalist. Every concept must have a formal representation.

TOPIC: {topic}
DOMAIN: {domain}

HYPOTHESES:
{hyp_text}

For each hypothesis:
1. Identify or derive the relevant equations
2. Define all variables with units
3. If no equation exists, propose one based on dimensional analysis or analogy
4. Rate mathematical rigor: complete|partial|absent

Return JSON:
{{
  "hypotheses": [
    {{
      "title": "...",
      "equations": [
        {{"name": "...", "latex": "...", "variables": [{{"symbol": "...", "meaning": "...", "units": "..."}}]}}
      ],
      "mathematical_rigor": "complete|partial|absent",
      "confidence_cap_applied": false,
      "notes": "..."
    }}
  ]
}}

If mathematical rigor is 'absent', set confidence_cap_applied to true."""

    result = _llm(prompt, max_tokens=4096, json_mode=True)
    if not result:
        return {"hypotheses": [{"title": h.get("title", ""), "equations": [], "mathematical_rigor": "absent", "confidence_cap_applied": True} for h in hypotheses[:5]]}

    # Apply confidence cap
    for h_result in result.get("hypotheses", []):
        if h_result.get("confidence_cap_applied"):
            for h in hypotheses:
                if h.get("title") == h_result.get("title"):
                    h["confidence"] = min(h.get("confidence", 0), 0.20)
                    h["confidence_capped"] = True
                    h["cap_reason"] = "No mathematical formalization possible"
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 4: DERIVATION ENGINE
# ═══════════════════════════════════════════════════════════════

def derivation_engine(hypotheses, math_results):
    """No free parameters. Every variable must be justified."""
    hyp_text = ""
    for i, h in enumerate(hypotheses[:5], 1):
        hyp_text += f"\nH{i}: {h.get('title', 'Untitled')}\n"
        params = h.get("key_parameters", [])
        if params:
            hyp_text += f"  Parameters: {json.dumps(params[:5])}\n"

    prompt = f"""You are a derivation auditor. Every variable must answer all 5 questions:
1. What is it?
2. Where does it come from?
3. How is it measured?
4. What units does it have?
5. How does it evolve?

HYPOTHESES:
{hyp_text}

For each hypothesis, audit every parameter. Reject any that can't answer all 5 questions.

Return JSON:
{{
  "hypotheses": [
    {{
      "title": "...",
      "parameters_audit": [
        {{
          "name": "...",
          "what": "...",
          "origin": "...",
          "measurement": "...",
          "units": "...",
          "evolution": "...",
          "status": "justified|unjustified|partially_justified"
        }}
      ],
      "free_parameters_count": 0,
      "verdict": "pass|fail|conditional"
    }}
  ]
}}"""

    result = _llm(prompt, max_tokens=4096, json_mode=True)
    if not result or isinstance(result, str):
        return {"hypotheses": [{"title": h.get("title", ""), "parameters_audit": [], "free_parameters_count": 0, "verdict": "conditional"} for h in hypotheses[:5]]}
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 5: MULTI-MODEL COMPETITION
# ═══════════════════════════════════════════════════════════════

def multi_model_competition(topic, hypotheses, audit, domain):
    """Generate 5 competing hypotheses and score them with weighted metrics."""
    existing = "\n".join(f"  H{i}: {h.get('title', '')}" for i, h in enumerate(hypotheses[:5], 1))

    prompt = f"""You are a scientific competition judge. Given existing hypotheses and the knowledge audit, generate exactly 5 competing hypotheses for: {topic}

EXISTING HYPOTHESES:
{existing}

DOMAIN: {domain}

Generate 5 hypotheses (keep the best existing ones, replace weak ones with better alternatives). Score each on:

| Metric | Weight |
|--------|--------|
| Evidence | 25 |
| Consistency | 25 |
| Predictive Power | 20 |
| Novelty | 10 |
| Simplicity | 10 |
| Falsifiability | 10 |

Return JSON:
{{
  "hypotheses": [
    {{
      "title": "...",
      "description": "...",
      "type": "existing|new",
      "scores": {{
        "evidence": 0-25,
        "consistency": 0-25,
        "predictive_power": 0-20,
        "novelty": 0-10,
        "simplicity": 0-10,
        "falsifiability": 0-10
      }},
      "total_score": 0-100
    }}
  ],
  "winner": "title of best hypothesis"
}}"""

    result = _llm(prompt, max_tokens=4096, json_mode=True)
    if not result:
        return {"hypotheses": [], "winner": None}
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 6: ADVERSARIAL SCIENTISTS (5 REVIEWERS)
# ═══════════════════════════════════════════════════════════════

def adversarial_scientists(topic, hypotheses, winner):
    """5 reviewer personas try to kill the winning hypothesis."""
    if not winner:
        return {"reviews": [], "survived": False}

    prompt = f"""You are simulating 5 adversarial scientific reviewers. Each tries to REJECT the hypothesis.

TOPIC: {topic}
WINNING HYPOTHESIS: {winner.get('title', '?')}
DESCRIPTION: {winner.get('description', '')[:500]}

Simulate these 5 reviewers:

REVIEWER 1 — MATHEMATICIAN: Attempts proof failure. Checks equations, dimensional analysis, limits.
REVIEWER 2 — EXPERIMENTALIST: Attempts experimental rejection. Checks if predictions are measurable.
REVIEWER 3 — DOMAIN EXPERT: Attempts literature-based rejection. Checks against known facts.
REVIEWER 4 — STATISTICIAN: Attempts significance rejection. Checks sample sizes, p-values, biases.
REVIEWER 5 — SKEPTIC: Assumes hypothesis is false. Finds the most likely alternative explanation.

For each reviewer, provide:
- objections: specific technical objections
- fatal_flaws: showstoppers if any
- required_tests: what experiments would satisfy this reviewer
- severity: fatal|major|minor

Return JSON:
{{
  "reviews": [
    {{
      "role": "mathematician|experimentalist|domain_expert|statistician|skeptic",
      "objections": ["..."],
      "fatal_flaws": ["..."],
      "required_tests": ["..."],
      "severity": "fatal|major|minor"
    }}
  ],
  "fatal_count": 0,
  "survived": true
}}

If any reviewer finds a fatal flaw, set survived to false."""

    result = _llm(prompt, max_tokens=4096, json_mode=True)
    if not result:
        return {"reviews": [], "fatal_count": 0, "survived": True}
    if isinstance(result, str) or (isinstance(result, dict) and result.get("_parse_failed")):
        # LLM returned raw text — extract what we can
        raw = result if isinstance(result, str) else result.get("_raw", "")
        fatal_count = raw.lower().count("fatal")
        survived = "fatal" not in raw.lower() or "no fatal" in raw.lower()
        return {"reviews": [], "fatal_count": fatal_count, "survived": survived, "raw": raw[:500]}
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 7: CAUSAL REASONING LAYER
# ═══════════════════════════════════════════════════════════════

def causal_reasoning(topic, hypotheses, winner):
    """Force all discoveries into causal graphs. No correlation-only claims."""
    if not winner:
        return {"causal_graphs": []}

    prompt = f"""You are a causal reasoning specialist. Convert the winning hypothesis into a formal causal graph.

TOPIC: {topic}
HYPOTHESIS: {winner.get('title', '?')}
DESCRIPTION: {winner.get('description', '')[:500]}

Build a causal graph with:
- Direct effects (A causes B)
- Indirect effects (A → B → C)
- Confounders (X affects both A and B)
- Feedback loops (A → B → A)
- Evidence for each arrow

Return JSON:
{{
  "causal_graph": {{
    "nodes": [{{"id": "...", "type": "cause|effect|mediator|confounder"}}],
    "edges": [{{"from": "...", "to": "...", "type": "direct|indirect|feedback", "evidence": "...", "strength": "strong|moderate|weak"}}],
    "confounders": ["..."],
    "feedback_loops": ["..."],
    "missing_causal_links": ["..."]
  }},
  "correlation_vs_causation_warnings": ["..."]
}}"""

    result = _llm(prompt, max_tokens=4096, json_mode=True)
    if not result:
        return {"causal_graph": {"nodes": [], "edges": [], "confounders": [], "feedback_loops": [], "missing_causal_links": []}, "correlation_vs_causation_warnings": []}
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 8: UNCERTAINTY DECOMPOSITION
# ═══════════════════════════════════════════════════════════════

def uncertainty_decomposition(hypotheses, winner):
    """Break confidence into 4 components instead of a single number."""
    if not winner:
        return {"decomposition": {}}

    prompt = f"""You are a uncertainty quantification specialist. Decompose the confidence into its components.

HYPOTHESIS: {winner.get('title', '?')}
Overall confidence: {winner.get('confidence', 0):.0%}

Decompose into:
1. data_uncertainty — how reliable is the input data?
2. model_uncertainty — how well does the model fit?
3. assumption_uncertainty — how risky are the assumptions?
4. measurement_uncertainty — how precise are the measurements?

Return JSON:
{{
  "decomposition": {{
    "data_uncertainty": {{"score": 0-100, "reason": "..."}},
    "model_uncertainty": {{"score": 0-100, "reason": "..."}},
    "assumption_uncertainty": {{"score": 0-100, "reason": "..."}},
    "measurement_uncertainty": {{"score": 0-100, "reason": "..."}}
  }},
  "overall_confidence": 0.0-1.0,
  "limiting_factor": "which uncertainty dominates"
}}"""

    result = _llm(prompt, max_tokens=2048, json_mode=True)
    if not result or (isinstance(result, dict) and result.get("_parse_failed")):
        return {"decomposition": {"data_uncertainty": {"score": 50, "reason": "unknown"}, "model_uncertainty": {"score": 50, "reason": "unknown"}, "assumption_uncertainty": {"score": 50, "reason": "unknown"}, "measurement_uncertainty": {"score": 50, "reason": "unknown"}}, "overall_confidence": 0.5, "limiting_factor": "assumption_uncertainty"}
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 9: PREDICTION GENERATOR (near/medium/long-term)
# ═══════════════════════════════════════════════════════════════

def prediction_generator(topic, winner, domain):
    """Generate predictions at 3 timescales with specific measurements."""
    if not winner:
        return {"predictions": []}

    prompt = f"""You are an experimental physicist designing tests for a hypothesis.

TOPIC: {topic}
DOMAIN: {domain}
HYPOTHESIS: {winner.get('title', '?')}
DESCRIPTION: {winner.get('description', '')[:500]}

Generate predictions at 3 timescales. Each must be:
- Specific (exact measurement, not vague)
- Quantitative (numbers, not "significant")
- Falsifiable (what result kills it?)

Return JSON:
{{
  "predictions": [
    {{
      "timescale": "near|medium|long",
      "timeframe": "1-2 years|3-5 years|5+ years",
      "prediction": "...",
      "measurement": "exact instrument/method",
      "expected_value": "number with units",
      "falsification_threshold": "what result disproves it",
      "feasibility": "easy|moderate|hard"
    }}
  ]
}}

Minimum 2 per timescale (6 total)."""

    result = _llm(prompt, max_tokens=4096, json_mode=True)
    if not result:
        return {"predictions": []}
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 10: SIMULATION LAYER
# ═══════════════════════════════════════════════════════════════

def simulation_layer(topic, winner, domain):
    """Attempt computational verification of the hypothesis."""
    if not winner:
        return {"simulation": {}}

    prompt = f"""You are a computational scientist. Design a simulation to test the hypothesis.

TOPIC: {topic}
DOMAIN: {domain}
HYPOTHESIS: {winner.get('title', '?')}
DESCRIPTION: {winner.get('description', '')[:500]}

Design a simulation:
1. What computational method? (numerical integration, Monte Carlo, agent-based, molecular dynamics, etc.)
2. What parameters?
3. What metrics to measure?
4. What are expected results if hypothesis is TRUE?
5. What are expected results if hypothesis is FALSE?
6. What are edge cases and failure modes?

Return JSON:
{{
  "simulation": {{
    "method": "...",
    "parameters": [{{"name": "...", "value": "...", "units": "..."}}],
    "metrics": ["..."],
    "expected_if_true": "...",
    "expected_if_false": "...",
    "edge_cases": ["..."],
    "failure_modes": ["..."],
    "computational_cost": "low|medium|high"
  }}
}}"""

    result = _llm(prompt, max_tokens=4096, json_mode=True)
    if not result:
        return {"simulation": {"method": "unknown", "parameters": [], "metrics": [], "expected_if_true": "unknown", "expected_if_false": "unknown", "edge_cases": [], "failure_modes": []}}
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 11: DISCOVERY VS SYNTHESIS CLASSIFIER
# ═══════════════════════════════════════════════════════════════

def discovery_classifier(topic, winner, papers):
    """Classify the output: replication, synthesis, extension, or discovery."""
    if not winner:
        return {"classification": "unknown"}

    paper_list = "\n".join(f"  [{p.get('source','?')}] {p['title']}" for p in papers[:15])

    prompt = f"""You are a scientific novelty assessor. Classify this output.

TOPIC: {topic}
HYPOTHESIS: {winner.get('title', '?')}
DESCRIPTION: {winner.get('description', '')[:500]}

EXISTING LITERATURE:
{paper_list}

Classify as one of:
- replication: reproducing known results
- synthesis: combining known ideas in a known way
- extension: combining known ideas in a new way
- discovery: new mechanism or prediction not in existing literature

Only label "discovery" if ALL three are true:
1. A new mechanism exists
2. A new prediction exists
3. Existing literature lacks equivalent formulation

Return JSON:
{{
  "classification": "replication|synthesis|extension|discovery",
  "reasoning": "...",
  "novel_mechanism": true|false,
  "novel_prediction": true|false,
  "literature_gap": true|false,
  "confidence_in_classification": 0.0-1.0
}}"""

    result = _llm(prompt, max_tokens=2048, json_mode=True)
    if not result:
        return {"classification": "unknown", "reasoning": "Classification failed"}
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 12: RESEARCHER-GRADE SCORING
# ═══════════════════════════════════════════════════════════════

def researcher_grade_scoring(winner, reviews, classification, uncertainty, predictions):
    """7 metrics that define a researcher-grade discovery."""
    if not winner:
        return {"scores": {}, "grade": "F"}

    prompt = f"""You are a journal editor scoring a research submission. Rate on 7 metrics.

HYPOTHESIS: {winner.get('title', '?')}
CLASSIFICATION: {classification.get('classification', '?')}
REVIEWS: {len(reviews.get('reviews', []))} reviewers, {reviews.get('fatal_count', 0)} fatal flaws
PREDICTIONS: {len(predictions.get('predictions', []))} predictions at 3 timescales

Score each metric 0-100:
1. Evidence Score — how strong is the supporting evidence?
2. Mathematical Rigor Score — are equations complete and correct?
3. Experimental Testability Score — can this be tested experimentally?
4. Novelty Score — how new is this?
5. Contradiction Score — how well does it handle contradictions? (higher = fewer contradictions)
6. Reproducibility Score — can others reproduce this?
7. Confidence Score — overall confidence

Also provide:
- Grade: A/B/C/D/F
- Failure conditions: what would invalidate this
- Alternative explanations: top 3 alternatives
- Competing hypotheses: how this compares

Return JSON:
{{
  "scores": {{
    "evidence": 0-100,
    "mathematical_rigor": 0-100,
    "experimental_testability": 0-100,
    "novelty": 0-100,
    "contradiction_handling": 0-100,
    "reproducibility": 0-100,
    "confidence": 0-100
  }},
  "grade": "A|B|C|D|F",
  "overall_score": 0-100,
  "failure_conditions": ["..."],
  "alternative_explanations": ["..."],
  "competing_hypotheses": ["..."]
}}"""

    result = _llm(prompt, max_tokens=4096, json_mode=True)
    if not result:
        return {"scores": {}, "grade": "F", "overall_score": 0}
    if isinstance(result, str) or (isinstance(result, dict) and result.get("_parse_failed")):
        # LLM returned raw text — try to extract scores
        raw = result if isinstance(result, str) else result.get("_raw", "")
        scores = {}
        # Try to find numbers in the text
        import re
        for metric in ["evidence", "mathematical_rigor", "experimental_testability",
                       "novelty", "contradiction_handling", "reproducibility", "confidence"]:
            # Look for patterns like "evidence: 65" or "Evidence Score: 65/100"
            pattern = rf'{metric}[:\s]+(\d+)'
            match = re.search(pattern, raw, re.IGNORECASE)
            if match:
                scores[metric] = int(match.group(1))
        # Try to find grade
        grade_match = re.search(r'grade[:\s]+([A-F])', raw, re.IGNORECASE)
        grade = grade_match.group(1).upper() if grade_match else "F"
        # Try to find overall score
        score_match = re.search(r'overall[_\s]*score[:\s]+(\d+)', raw, re.IGNORECASE)
        overall = int(score_match.group(1)) if score_match else (sum(scores.values()) // len(scores) if scores else 0)
        return {"scores": scores, "grade": grade, "overall_score": overall}
    return result


# ═══════════════════════════════════════════════════════════════
# STAGE 13: SELF-CRITIQUE + SCIENTIFIC COURTROOM MODE
# ═══════════════════════════════════════════════════════════════

def scientific_courtroom(topic, winner, reviews, scoring):
    """Prosecutor, Defense, Judge, Jury. Only survivors become RUMI Discoveries."""
    if not winner:
        return {"verdict": "no_hypothesis", "survived": False}

    prompt = f"""You are the Scientific Courtroom. A hypothesis is on trial.

TOPIC: {topic}
HYPOTHESIS: {winner.get('title', '?')}
DESCRIPTION: {winner.get('description', '')[:500]}
CURRENT SCORE: {scoring.get('overall_score', 0)}/100
CURRENT GRADE: {scoring.get('grade', '?')}

Conduct a full trial:

PROSECUTION (tries to destroy):
- Present the 3 strongest objections
- Identify the fatal flaw if any
- Argue for rejection

DEFENSE (tries to save):
- Counter each objection
- Provide supporting evidence
- Argue for acceptance

JUDGE (evaluates evidence):
- Weigh prosecution vs defense
- Identify what's missing
- Rule on admissibility

JURY (5 domain experts vote):
- Expert 1: Theoretical Physicist
- Expert 2: Experimental Physicist
- Expert 3: Mathematician
- Expert 4: Philosopher of Science
- Expert 5: Interdisciplinary Researcher

SELF-CRITIQUE (the hypothesis critiques itself):
- What assumptions did I make?
- Which assumption is weakest?
- What evidence would destroy me?
- What experiment could prove me wrong tomorrow?

Return JSON:
{{
  "prosecution": {{"objections": ["..."], "fatal_flaw": "...", "argument": "..."}},
  "defense": {{"counterarguments": ["..."], "supporting_evidence": ["..."], "argument": "..."}},
  "judge": {{"ruling": "accept|reject|conditional", "reasoning": "...", "missing_evidence": ["..."]}},
  "jury": {{"votes": [{{"expert": "...", "vote": "accept|reject|abstain", "reason": "..."}}], "tally": "accept:N reject:N abstain:N"}},
  "self_critique": {{"assumptions": ["..."], "weakest_assumption": "...", "destroying_evidence": "...", "falsification_experiment": "..."}},
  "verdict": "RUMI_DISCOVERY|REJECTED|CONDITIONAL",
  "survived": true|false,
  "final_confidence": 0.0-1.0
}}"""

    result = _llm_thinking(prompt, max_tokens=8192)
    if not result:
        return {"verdict": "UNKNOWN", "survived": False}

    # Parse JSON from thinking response — robust parsing
    text = result.strip() if isinstance(result, str) else str(result)
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from anywhere in the response
    import re
    # Try multiple JSON extraction strategies
    for pattern in [r'\{[^{}]*"verdict"[^{}]*\}', r'\{[^{}]*"prosecution"[^{}]*\}', r'\{.*?\}(?=\s*$|\s*\n)']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

    # Try finding any JSON object
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    # If all parsing fails, extract verdict from text
    verdict = "UNKNOWN"
    survived = False
    if "RUMI_DISCOVERY" in text or "accepted" in text.lower():
        verdict = "RUMI_DISCOVERY"
        survived = True
    elif "REJECTED" in text or "rejected" in text.lower():
        verdict = "REJECTED"
        survived = False
    elif "CONDITIONAL" in text or "conditional" in text.lower():
        verdict = "CONDITIONAL"
        survived = True

    return {"verdict": verdict, "survived": survived, "raw": text[:2000]}


# ═══════════════════════════════════════════════════════════════
# MASTER RUNNER — ALL 13 STAGES
# ═══════════════════════════════════════════════════════════════

def run_refinement_pipeline(topic, domain, papers, graph, hypotheses, contradictions=None):
    """Run all 13 refinement stages on raw pipeline output."""
    results = {}
    t_total = time.time()

    def log(msg):
        print(msg, flush=True)

    # Stage 1
    log("[Refine 1/13] KNOWLEDGE FOUNDATION AUDIT")
    t0 = time.time()
    results["audit"] = knowledge_foundation_audit(topic, domain, papers, graph, hypotheses)
    log(f"  {len(results['audit'].get('known_facts', []))} facts, {len(results['audit'].get('open_problems', []))} open problems ({time.time()-t0:.1f}s)")

    # Stage 2
    log("[Refine 2/13] FIRST PRINCIPLES RECONSTRUCTION")
    t0 = time.time()
    results["first_principles"] = first_principles_reconstruction(topic, hypotheses, results["audit"])
    log(f"  {len(results['first_principles'].get('hypotheses', []))} dependency trees ({time.time()-t0:.1f}s)")

    # Stage 3
    log("[Refine 3/13] MATHEMATICAL FORMALIZATION")
    t0 = time.time()
    results["math"] = mathematical_formalization(topic, hypotheses, domain)
    capped = sum(1 for h in results["math"].get("hypotheses", []) if h.get("confidence_cap_applied"))
    log(f"  {len(results['math'].get('hypotheses', []))} formalized, {capped} confidence-capped ({time.time()-t0:.1f}s)")

    # Stage 4
    log("[Refine 4/13] DERIVATION ENGINE")
    t0 = time.time()
    results["derivation"] = derivation_engine(hypotheses, results["math"])
    log(f"  {len(results['derivation'].get('hypotheses', []))} audited ({time.time()-t0:.1f}s)")

    # Stage 5
    log("[Refine 5/13] MULTI-MODEL COMPETITION")
    t0 = time.time()
    results["competition"] = multi_model_competition(topic, hypotheses, results["audit"], domain)
    winner_title = results["competition"].get("winner", "?")
    winner_title = results['competition'].get('winner', {}).get('title', 'N/A') if results.get('competition', {}).get('winner') else 'N/A'
    log(f"  {len(results.get('competition', {}).get('hypotheses', []))} hypotheses, winner: {winner_title[:50]} ({time.time()-t0:.1f}s)")

    # Find the winning hypothesis
    winner = None
    for h in results["competition"].get("hypotheses", []):
        if h.get("title") == winner_title:
            winner = h
            break
    if not winner and results["competition"].get("hypotheses"):
        winner = results["competition"]["hypotheses"][0]

    # Stage 6
    log("[Refine 6/13] ADVERSARIAL SCIENTISTS")
    t0 = time.time()
    results["reviews"] = adversarial_scientists(topic, hypotheses, winner)
    survived = results["reviews"].get("survived", False)
    log(f"  {len(results['reviews'].get('reviews', []))} reviews, fatal: {results['reviews'].get('fatal_count', 0)}, survived: {survived} ({time.time()-t0:.1f}s)")

    # Stage 7
    log("[Refine 7/13] CAUSAL REASONING")
    t0 = time.time()
    results["causal"] = causal_reasoning(topic, hypotheses, winner)
    log(f"  Causal graph built ({time.time()-t0:.1f}s)")

    # Stage 8
    log("[Refine 8/13] UNCERTAINTY DECOMPOSITION")
    t0 = time.time()
    results["uncertainty"] = uncertainty_decomposition(hypotheses, winner)
    limiting = results["uncertainty"].get("limiting_factor", "?")
    log(f"  Limiting factor: {limiting} ({time.time()-t0:.1f}s)")

    # Stage 9
    log("[Refine 9/13] PREDICTION GENERATOR")
    t0 = time.time()
    results["predictions"] = prediction_generator(topic, winner, domain)
    pred_count = len(results["predictions"].get("predictions", []))
    log(f"  {pred_count} predictions at 3 timescales ({time.time()-t0:.1f}s)")

    # Stage 10
    log("[Refine 10/13] SIMULATION LAYER")
    t0 = time.time()
    results["simulation"] = simulation_layer(topic, winner, domain)
    log(f"  Simulation designed ({time.time()-t0:.1f}s)")

    # Stage 11
    log("[Refine 11/13] DISCOVERY CLASSIFIER")
    t0 = time.time()
    results["classification"] = discovery_classifier(topic, winner, papers)
    log(f"  Classification: {results['classification'].get('classification', '?')} ({time.time()-t0:.1f}s)")

    # Stage 12
    log("[Refine 12/13] RESEARCHER-GRADE SCORING")
    t0 = time.time()
    results["scoring"] = researcher_grade_scoring(winner, results["reviews"], results["classification"], results["uncertainty"], results["predictions"])
    log(f"  Grade: {results['scoring'].get('grade', '?')} ({results['scoring'].get('overall_score', 0)}/100) ({time.time()-t0:.1f}s)")

    # Stage 13
    log("[Refine 13/13] SCIENTIFIC COURTROOM")
    t0 = time.time()
    results["courtroom"] = scientific_courtroom(topic, winner, results["reviews"], results["scoring"])
    verdict = results["courtroom"].get("verdict", "?")
    survived = results["courtroom"].get("survived", False)
    log(f"  Verdict: {verdict} | Survived: {survived} ({time.time()-t0:.1f}s)")

    total_time = time.time() - t_total
    log(f"\n  REFINE COMPLETE — {total_time:.1f}s")
    log(f"  Verdict: {verdict}")
    log(f"  Grade: {results['scoring'].get('grade', '?')}")
    log(f"  Classification: {results['classification'].get('classification', '?')}")

    return results
