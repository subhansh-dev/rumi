"""Experiment planner — designs experimental proposals for hypotheses."""

import json
from discovery.pipeline import LLMStage


class ExperimentPlanner:
    def __init__(self):
        self.stage = LLMStage("experiment_planner", max_retries=2, backoff=[3, 10])

    async def plan(self, hypothesis):
        mech = hypothesis.get("mechanistic_rationale", hypothesis.get("description", ""))
        supporting = hypothesis.get("supporting_evidence", hypothesis.get("evidence", []))
        contradictory = hypothesis.get("contradictory_evidence", [])
        alt_explanations = hypothesis.get("alternative_explanations", [])
        env_constraints = hypothesis.get("environmental_constraints", "")
        failure_conditions = hypothesis.get("failure_conditions", [])
        testability = hypothesis.get("experimental_validation", hypothesis.get("testability", "Not specified"))
        obs_requirements = hypothesis.get("observational_requirements", "")

        prompt = f"""You are an experimental scientist designing a rigorous study to test a hypothesis.

HYPOTHESIS:
Title: {hypothesis.get('title')}
Mechanistic Rationale: {mech}

Supporting Evidence: {json.dumps(supporting, indent=2)}
Contradictory Evidence: {json.dumps(contradictory, indent=2)}
Alternative Explanations: {json.dumps(alt_explanations, indent=2)}
Environmental Constraints: {env_constraints}
Failure Conditions: {json.dumps(failure_conditions, indent=2)}
Current Validation Idea: {testability}
Observational Requirements: {obs_requirements}

Nodes: {json.dumps(hypothesis.get('nodes', []), indent=2)}
Edges: {json.dumps(hypothesis.get('edges', []), indent=2)}

Design a detailed experiment. Include:
1. Experimental design — in vitro, in vivo, computational, or observational approach
2. Key variables — independent, dependent, controlled (be specific)
3. Control groups — positive and negative controls including sham/placebo
4. Expected outcomes — what would confirm vs. disconfirm, including null result handling
5. Key measurements — what to measure, with what instrument, detection limits
6. Biomarkers or readouts — specific measurable endpoints
7. Sample size / statistical power considerations
8. Failure points — what could go wrong and contingency plans
9. How to distinguish from alternative explanations
10. Domain-appropriate methodology

Output JSON:
{{"experiment_type": "in_vitro|in_vivo|computational|observational|clinical", "design": "detailed step-by-step description", "variables": {{"independent": ["var1 with units"], "dependent": ["var2 with units"], "controlled": ["var3 with units"], "confounders": ["confounder1"]}}, "control_groups": ["positive control", "negative control"], "expected_outcomes": {{"confirm": "what would confirm", "disconfirm": "what would disprove", "null_result": "what if no effect"}}, "key_measurements": [{{"what": "measurement", "how": "method/instrument", "detection_limit": "value"}}], "biomarkers": ["specific biomarker"], "sample_size_rationale": "statistical power estimate", "failure_points": [{{"risk": "specific risk", "contingency": "backup plan"}}], "timeline_estimate": "weeks/months", "estimated_cost": "low|medium|high"}}"""

        raw, provider = await self.stage.call_with_retry(prompt, json_mode=True, max_tokens=4096)
        if not raw:
            return self._default()

        try:
            if not raw.strip():
                return self._default()
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0].strip()
            return json.loads(text)
        except json.JSONDecodeError:
            return self._default()

    def _default(self):
        return {
            "experiment_type": "computational",
            "design": "Experimental planning unavailable",
            "variables": {"independent": [], "dependent": [], "controlled": [], "confounders": []},
            "control_groups": [],
            "expected_outcomes": {"confirm": "", "disconfirm": "", "null_result": ""},
            "key_measurements": [],
            "biomarkers": [],
            "sample_size_rationale": "",
            "failure_points": [],
            "timeline_estimate": "N/A",
            "estimated_cost": "medium",
        }
