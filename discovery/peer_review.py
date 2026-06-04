"""
peer_review.py — Critical Evaluation for RUMI Discoveries

Structured 6-dimension assessment of the top discovery.
Evaluates novelty, methodology, significance, clarity, limitations,
and reproducibility. Produces an overall score and recommendation.

This is more structured than the skeptic review. The skeptic tries to
destroy. The critical evaluator assesses like a research panel would.
"""

import json
from typing import Dict, Optional
from discovery.json_extract import extract_json


class CriticalEvaluator:
    """
    Structured critical evaluation for scientific discoveries.
    """

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def review(self, theory: dict, mechanisms: list, predictions: list,
               papers: list, topic: str, domain: str,
               adversarial_results: dict = None) -> dict:
        """
        Run a formal peer review on the top discovery.

        Returns:
            {
                "novelty": {"score": 0-10, "comment": "..."},
                "methodology": {"score": 0-10, "comment": "..."},
                "significance": {"score": 0-10, "comment": "..."},
                "clarity": {"score": 0-10, "comment": "..."},
                "limitations": {"score": 0-10, "comment": "..."},
                "reproducibility": {"score": 0-10, "comment": "..."},
                "overall_score": 0-10,
                "recommendation": "accept|minor_revision|major_revision|reject",
                "summary": "...",
                "major_issues": [...],
                "minor_issues": [...],
                "questions_for_authors": [...]
            }
        """
        if not self.llm_call:
            return self._fallback_review()

        # Build theory description
        theory_name = theory.get("name", "Unnamed")
        theory_desc = theory.get("description", "")
        theory_type = theory.get("type", "")
        theory_mechanism = theory.get("mechanism", "")
        theory_explains = theory.get("explains", [])
        theory_fails = theory.get("fails_to_explain", [])
        theory_predictions = theory.get("predictions", [])
        theory_assumptions = theory.get("key_assumptions", [])
        theory_scores = theory.get("scores", {})

        # Build mechanism descriptions
        mech_text = ""
        for m in mechanisms[:5]:
            mech_text += f"\n- [{m.get('type', '?')}] {m.get('name', '?')}: {m.get('description', '')[:150]}"

        # Build prediction descriptions
        pred_text = ""
        for p in predictions[:5]:
            if isinstance(p, dict):
                pred_text += f"\n- [{p.get('type', '?')}] {p.get('statement', '')[:150]}"

        # Build adversarial test context
        adv_text = ""
        if adversarial_results:
            summary = adversarial_results.get("survival_summary", {})
            adv_text = f"""
ADVERSARIAL TEST RESULTS:
  Hidden variables: {summary.get('hidden_variables', {}).get('survived', 0)} survived, {summary.get('hidden_variables', {}).get('killed', 0)} killed
  Mechanisms: {summary.get('mechanisms', {}).get('survived', 0)} survived, {summary.get('mechanisms', {}).get('killed', 0)} killed
  Theories: {summary.get('theories', {}).get('survived', 0)} survived, {summary.get('theories', {}).get('killed', 0)} killed
"""

        prompt = f"""You are a research evaluation panel. Assess this discovery
        thoroughly and fairly. Be rigorous but constructive.

TOPIC: {topic}
DOMAIN: {domain}

THEORY: {theory_name} (type: {theory_type})
Description: {theory_desc[:400]}
Mechanism: {theory_mechanism[:300]}
Explains: {', '.join(str(e)[:60] for e in theory_explains[:5])}
Fails to explain: {', '.join(str(f)[:60] for f in theory_fails[:5])}
Predictions: {pred_text[:500]}
Key assumptions: {', '.join(str(a)[:60] for a in theory_assumptions[:5])}
Current scores: {json.dumps(theory_scores, indent=2)[:300]}

MECHANISMS:
{mech_text[:500]}

{adv_text}

Evaluate on these dimensions (score 0-10 for each):

1. NOVELTY (0-10): Does this say something genuinely new?
   0 = completely known, 10 = revolutionary new insight

2. METHODOLOGY (0-10): Is the reasoning sound? Are there logical gaps?
   0 = fundamentally flawed, 10 = rigorous and well-reasoned

3. SIGNIFICANCE (0-10): Would this matter if true? Would it change the field?
   0 = trivial, 10 = field-changing

4. CLARITY (0-10): Is the discovery well-explained and coherent?
   0 = incomprehensible, 10 = crystal clear

5. LIMITATIONS (0-10): How well does it acknowledge its own weaknesses?
   0 = no awareness, 10 = honest and thorough

6. REPRODUCIBILITY (0-10): Could someone else verify this from the description?
   0 = impossible to verify, 10 = fully reproducible

Also provide:
- recommendation: accept / minor_revision / major_revision / reject
- summary: 2-3 paragraph overall assessment
- major_issues: list of critical problems (if any)
- minor_issues: list of minor problems (if any)
- questions_for_authors: list of questions you'd want answered

Output JSON:
{{
  "novelty": {{"score": N, "comment": "..."}},
  "methodology": {{"score": N, "comment": "..."}},
  "significance": {{"score": N, "comment": "..."}},
  "clarity": {{"score": N, "comment": "..."}},
  "limitations": {{"score": N, "comment": "..."}},
  "reproducibility": {{"score": N, "comment": "..."}},
  "overall_score": N,
  "recommendation": "accept|minor_revision|major_revision|reject",
  "summary": "...",
  "major_issues": ["issue1", "issue2"],
  "minor_issues": ["issue1", "issue2"],
  "questions_for_authors": ["question1", "question2"]
}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=4096)
            if not raw:
                from discovery.llm_client import call_json
                raw = call_json(prompt, max_tokens=4096, provider="auto")

            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = extract_json(raw)
                else:
                    result = raw

                if isinstance(result, dict):
                    # Compute overall score if not provided
                    if "overall_score" not in result:
                        scores = []
                        for dim in ["novelty", "methodology", "significance",
                                    "clarity", "limitations", "reproducibility"]:
                            if dim in result and isinstance(result[dim], dict):
                                scores.append(result[dim].get("score", 5))
                        if scores:
                            result["overall_score"] = round(sum(scores) / len(scores), 1)

                    # Ensure recommendation exists
                    if "recommendation" not in result:
                        overall = result.get("overall_score", 5)
                        if overall >= 7:
                            result["recommendation"] = "accept"
                        elif overall >= 5:
                            result["recommendation"] = "minor_revision"
                        elif overall >= 3:
                            result["recommendation"] = "major_revision"
                        else:
                            result["recommendation"] = "reject"

                    return result

        except Exception as e:
            return self._fallback_review(str(e))

        return self._fallback_review()

    def _fallback_review(self, error=None):
        """Fallback when LLM fails."""
        return {
            "novelty": {"score": 5, "comment": "Review failed"},
            "methodology": {"score": 5, "comment": "Review failed"},
            "significance": {"score": 5, "comment": "Review failed"},
            "clarity": {"score": 5, "comment": "Review failed"},
            "limitations": {"score": 5, "comment": "Review failed"},
            "reproducibility": {"score": 5, "comment": "Review failed"},
            "overall_score": 5.0,
            "recommendation": "major_revision",
            "summary": f"Critical evaluation could not be completed. {f'Error: {error}' if error else ''}",
            "major_issues": ["Review failed — could not evaluate"],
            "minor_issues": [],
            "questions_for_authors": [],
        }
