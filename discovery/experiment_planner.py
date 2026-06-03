"""Experiment planner — designs experimental proposals for top theories.

Generates concrete validation plans: what experiments to run,
what data to collect, what would confirm/disconfirm the theory.
"""

import json


class ExperimentPlanner:
    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def plan(self, theory: dict, mechanisms: list = None,
             predictions: list = None, papers: list = None,
             topic: str = "", domain: str = "") -> dict:
        """Generate a detailed experimental validation plan for a theory.

        Args:
            theory: The top theory to validate
            mechanisms: Supporting mechanisms
            predictions: Theory's predictions
            papers: Available literature
            topic: Research topic
            domain: Research domain

        Returns:
            Experimental plan with design, variables, controls, etc.
        """
        if not self.llm_call:
            return self._default()

        mech_text = ""
        for m in (mechanisms or [])[:3]:
            steps = m.get("steps", [])
            mech_text += f"\n- {m.get('name', '?')}: {' → '.join(str(s) for s in steps[:3])}"

        pred_text = ""
        for p in (predictions or [])[:5]:
            pred_text += f"\n- [{p.get('type', '?')}] {p.get('statement', '')[:150]}"

        failure_conditions = theory.get("failure_conditions", [])
        if isinstance(failure_conditions, str):
            failure_conditions = [failure_conditions]

        prompt = f"""You are an experimental scientist designing a rigorous study to validate a theory.

TOPIC: {topic}
DOMAIN: {domain}

THEORY: {theory.get('name', '?')}
DESCRIPTION: {theory.get('description', theory.get('mechanism', ''))[:400]}

CAUSAL MECHANISMS:
{mech_text or 'None specified'}

TESTABLE PREDICTIONS:
{pred_text or 'None specified'}

FAILURE CONDITIONS: {json.dumps(failure_conditions[:3])}
KEY ASSUMPTIONS: {json.dumps(theory.get('key_assumptions', [])[:3])}

Design a concrete experimental validation plan. Include:

1. EXPERIMENT TYPE: in_vitro | in_vivo | computational | observational | clinical | simulation
2. DESIGN: Step-by-step experimental procedure
3. VARIABLES: independent (manipulated), dependent (measured), controlled, confounders
4. CONTROLS: positive control, negative control, sham/placebo if applicable
5. EXPECTED OUTCOMES:
   - Confirm: What observation would support the theory?
   - Disconfirm: What observation would disprove it?
   - Null: What if no effect is observed?
6. KEY MEASUREMENTS: What to measure, with what method, detection limits
7. SAMPLE SIZE: Statistical power considerations
8. FAILURE POINTS: What could go wrong + contingency plans
9. TIMELINE: Estimated duration
10. COST: low | medium | high
11. DISCRIMINATING POWER: How well does this experiment distinguish this theory from alternatives?

Output JSON:
{{"experiment_type": "...", "design": "detailed procedure", "variables": {{"independent": [...], "dependent": [...], "controlled": [...], "confounders": [...]}}, "control_groups": [...], "expected_outcomes": {{"confirm": "...", "disconfirm": "...", "null_result": "..."}}, "key_measurements": [{{"what": "...", "how": "...", "detection_limit": "..."}}], "sample_size_rationale": "...", "failure_points": [{{"risk": "...", "contingency": "..."}}], "timeline_estimate": "...", "estimated_cost": "low|medium|high", "discriminating_power": "high|medium|low"}}"""

        raw = self.llm_call(prompt, max_tokens=4096, phase="critical_evaluation")
        if not raw:
            return self._default()

        try:
            if isinstance(raw, str):
                text = raw.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    text = text.rsplit("```", 1)[0].strip()
                return json.loads(text)
            return raw if isinstance(raw, dict) else self._default()
        except json.JSONDecodeError:
            return self._default()

    def plan_for_top_theories(self, theories: list, mechanisms: list = None,
                               predictions: list = None, papers: list = None,
                               topic: str = "", domain: str = "",
                               max_plans: int = 3) -> list:
        """Generate validation plans for top N theories."""
        plans = []
        for t in (theories or [])[:max_plans]:
            if not isinstance(t, dict) or not t.get("name"):
                continue
            try:
                plan = self.plan(t, mechanisms, predictions, papers, topic, domain)
                plan["theory_name"] = t.get("name", "?")
                plan["theory_score"] = t.get("scores", {}).get("overall", 0)
                plans.append(plan)
            except Exception:
                continue
        return plans

    def _default(self):
        return {
            "experiment_type": "computational",
            "design": "Experimental planning unavailable",
            "variables": {"independent": [], "dependent": [], "controlled": [], "confounders": []},
            "control_groups": [],
            "expected_outcomes": {"confirm": "", "disconfirm": "", "null_result": ""},
            "key_measurements": [],
            "sample_size_rationale": "",
            "failure_points": [],
            "timeline_estimate": "N/A",
            "estimated_cost": "medium",
            "discriminating_power": "low",
        }
