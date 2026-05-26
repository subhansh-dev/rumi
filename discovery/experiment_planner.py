"""Experiment planner — designs experimental proposals for hypotheses."""

import json
from discovery.pipeline import LLMStage


class ExperimentPlanner:
    def __init__(self):
        self.stage = LLMStage("experiment_planner", max_retries=2, backoff=[3, 10])

    async def plan(self, hypothesis):
        prompt = f"""You are an experimental scientist designing a study to test a hypothesis.

HYPOTHESIS:
Title: {hypothesis.get('title')}
Description: {hypothesis.get('description')}
Nodes: {json.dumps(hypothesis.get('nodes', []), indent=2)}
Edges: {json.dumps(hypothesis.get('edges', []), indent=2)}
Evidence: {json.dumps(hypothesis.get('evidence', []), indent=2)}
Testability: {hypothesis.get('testability', 'Not specified')}

Design a detailed experiment. Include:
1. Experimental design — in vitro, in vivo, or computational approach
2. Key variables — independent, dependent, controlled
3. Control groups — positive and negative controls
4. Expected outcomes — what would confirm vs. disconfirm the hypothesis
5. Key measurements — what to measure and how
6. Biomarkers — relevant biomarkers or readouts
7. Failure points — what could go wrong and contingency plans

Output JSON:
{{"experiment_type": "in_vitro|in_vivo|computational|clinical", "design": "detailed description", "variables": {{"independent": ["var1"], "dependent": ["var2"], "controlled": ["var3"]}}, "control_groups": ["control1"], "expected_outcomes": {{"confirm": "what would confirm", "disconfirm": "what would disprove"}}, "key_measurements": [{{"what": "measurement", "how": "method"}}], "biomarkers": ["biomarker1"], "failure_points": [{{"risk": "something", "contingency": "plan"}}], "timeline_estimate": "weeks/months", "estimated_cost": "low|medium|high"}}"""

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
            "experiment_type": "computational",
            "design": "Experimental planning unavailable",
            "variables": {"independent": [], "dependent": [], "controlled": []},
            "control_groups": [],
            "expected_outcomes": {"confirm": "", "disconfirm": ""},
            "key_measurements": [],
            "biomarkers": [],
            "failure_points": [],
            "timeline_estimate": "N/A",
            "estimated_cost": "medium",
        }
