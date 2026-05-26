"""Scientific skeptic agent — critiques hypotheses for rigor."""

import json
from discovery.pipeline import LLMStage


class SkepticAgent:
    def __init__(self):
        self.stage = LLMStage("skeptic", max_retries=2, backoff=[3, 10])

    async def review(self, hypothesis, contradictions=None):
        contradictions_text = ""
        if contradictions:
            contradictions_text = "\nKnown contradictions: " + json.dumps(contradictions[:3], indent=2)

        prompt = f"""You are a skeptical scientific reviewer. Critique this hypothesis rigorously.

HYPOTHESIS:
Title: {hypothesis.get('title')}
Description: {hypothesis.get('description')}
Pattern: {hypothesis.get('pattern_type')}
Confidence: {hypothesis.get('confidence')}

Nodes: {json.dumps(hypothesis.get('nodes', []), indent=2)}
Edges: {json.dumps(hypothesis.get('edges', []), indent=2)}
Evidence: {json.dumps(hypothesis.get('evidence', []), indent=2)}
Testability: {hypothesis.get('testability')}{contradictions_text}

Analyze:
1. Logical flaws — identify specific logical gaps or leaps
2. Evidence quality — rate each cited support: strong/weak/absent
3. Alternative mechanisms — propose 2-3 alternative explanations
4. Confounders — what variables might confound the proposed relationship?
5. Methodological issues — how would you improve the experimental design?

Output JSON:
{{"critique": "detailed multi-paragraph critique", "logical_flaws": ["flaw1", "flaw2"], "alternative_mechanisms": ["alt1", "alt2"], "confounders": ["confounder1"], "evidence_rating": "strong|moderate|weak", "suggested_improvements": ["improvement1"], "recommendation": "accept|revise|reject"}}"""

        raw, provider = await self.stage.call_with_retry(prompt, json_mode=True)
        if not raw:
            return self._default()

        try:
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                raw = raw.rsplit("```", 1)[0].strip()
            return json.loads(raw)
        except json.JSONDecodeError:
            return self._default()

    def _default(self):
        return {
            "critique": "Review unavailable",
            "logical_flaws": ["LLM review failed"],
            "alternative_mechanisms": [],
            "confounders": [],
            "evidence_rating": "weak",
            "suggested_improvements": ["Retry review"],
            "recommendation": "revise",
        }
