"""Scientific skeptic agent — adversarial critique of hypotheses for rigor."""

import json
from discovery.pipeline import LLMStage
from discovery.json_extract import extract_json


class SkepticAgent:
    def __init__(self):
        self.stage = LLMStage("skeptic", max_retries=2, backoff=[3, 10])

    async def review(self, hypothesis, contradictions=None):
        contradictions_text = ""
        if contradictions:
            contradictions_text = "\nKnown contradictions: " + json.dumps(contradictions[:3], indent=2)

        mech = hypothesis.get("mechanistic_rationale", hypothesis.get("description", ""))
        supporting = hypothesis.get("supporting_evidence", hypothesis.get("evidence", []))
        contradictory = hypothesis.get("contradictory_evidence", [])
        alt = hypothesis.get("alternative_explanations", [])
        env = hypothesis.get("environmental_constraints", "")
        failures = hypothesis.get("failure_conditions", [])
        testability = hypothesis.get("experimental_validation", hypothesis.get("testability", ""))
        obs = hypothesis.get("observational_requirements", "")

        prompt = f"""You are an adversarial skeptical scientific reviewer. Your job is to FALSIFY this hypothesis — find every reason it might be wrong.

HYPOTHESIS:
Title: {hypothesis.get('title')}
Mechanistic Rationale: {mech}
Pattern: {hypothesis.get('pattern_type')}
Confidence: {hypothesis.get('confidence')}
Novelty: {hypothesis.get('novelty')}

Supporting Evidence: {json.dumps(supporting, indent=2)}
Contradictory Evidence Already Listed: {json.dumps(contradictory, indent=2)}
Alternative Explanations Listed: {json.dumps(alt, indent=2)}
Environmental Constraints: {env}
Failure Conditions Listed: {json.dumps(failures, indent=2)}
Experimental Validation: {testability}
Observational Requirements: {obs}
Nodes: {json.dumps(hypothesis.get('nodes', []), indent=2)}
Edges: {json.dumps(hypothesis.get('edges', []), indent=2)}{contradictions_text}

Analyze rigorously:
1. Logical flaws — specific gaps, leaps, or fallacies in the mechanistic chain
2. Evidence quality — rate each piece of supporting/contradictory evidence as strong/moderate/weak
3. Missing alternative mechanisms — what important alternative explanations are NOT listed?
4. Confounders — what unaccounted variables could explain the observations?
5. Methodological critique — how would you redesign the experiment to be more rigorous?
6. Novelty assessment — is this genuinely underexplored, or does it rephrase known concepts?
7. Top 3 weaknesses — the most damaging specific flaws

Output JSON:
{{"critique": "detailed adversarial critique (2-3 paragraphs)", "logical_flaws": ["flaw1", "flaw2"], "evidence_ratings": [{{"claim": "specific claim", "rating": "strong|moderate|weak", "reason": "why"}}], "alternative_mechanisms": ["alt1", "alt2"], "confounders": ["confounder1"], "methodological_critique": "specific improvements", "novelty_assessment": "independent assessment", "weaknesses": ["top weakness 1", "top weakness 2", "top weakness 3"], "recommendation": "accept|revise|reject", "revised_confidence": 0.0-1.0}}"""

        raw, provider = await self.stage.call_with_retry(prompt, json_mode=True)
        if not raw:
            return self._default()

        try:
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0].strip()
            return extract_json(raw)
        except json.JSONDecodeError:
            return self._default()

    def _default(self):
        return {
            "critique": "Review unavailable",
            "logical_flaws": ["LLM review failed"],
            "alternative_mechanisms": [],
            "confounders": [],
            "evidence_ratings": [],
            "methodological_critique": "",
            "novelty_assessment": "unknown",
            "weaknesses": ["Review unavailable"],
            "recommendation": "revise",
            "revised_confidence": 0.3,
        }
