"""
test_stage.py — Adversarial Test Stage for RUMI Discovery Pipeline

Aggressively attacks every discovery with three questions:
1. What existing theory already explains this?
2. Can any new variable be removed?
3. What observation would falsify it?

This is NOT a review. This is an attack. The goal is to kill weak
discoveries before they waste scoring/review time. Surviving this
stage means the discovery has genuine merit.
"""

import json
from typing import List, Dict, Optional


class AdversarialTest:
    """
    Attack every discovery. Kill weak ones. Strengthen survivors.
    """

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def test_discoveries(
        self,
        hidden_variables: list,
        mechanisms: list,
        theories: list,
        papers: list,
        topic: str,
        domain: str,
        gaps: list = None,
        anomalies: list = None,
    ) -> dict:
        """
        Run adversarial tests on all discoveries.

        Returns:
            {
                "hidden_variable_tests": [
                    {
                        "name": "...",
                        "existing_theory": "What existing theory explains this?",
                        "can_remove": true/false,
                        "removal_reason": "Why it can/cannot be removed",
                        "falsification": "What observation would falsify this",
                        "survived": true/false,
                        "attack_score": 0.0-1.0,
                        "verdict": "survived|weakened|killed"
                    }
                ],
                "mechanism_tests": [...],
                "theory_tests": [...],
                "survival_summary": {
                    "hidden_variables": {"started": N, "survived": N, "killed": N},
                    "mechanisms": {"started": N, "survived": N, "killed": N},
                    "theories": {"started": N, "survived": N, "killed": N},
                }
            }
        """
        if not self.llm_call:
            return self._fallback_test(hidden_variables, mechanisms, theories)

        results = {
            "hidden_variable_tests": [],
            "mechanism_tests": [],
            "theory_tests": [],
        }

        # Build paper context
        paper_context = ""
        for p in papers[:8]:
            if isinstance(p, dict):
                title = p.get("title", "")
                abstract = p.get("abstract", "")[:200]
                paper_context += f"\n- [{title}] {abstract}"

        # Test hidden variables
        if hidden_variables:
            results["hidden_variable_tests"] = self._test_items(
                hidden_variables, "hidden_variable", paper_context, topic, domain
            )

        # Test mechanisms
        if mechanisms:
            results["mechanism_tests"] = self._test_items(
                mechanisms, "mechanism", paper_context, topic, domain
            )

        # Test theories
        if theories:
            results["theory_tests"] = self._test_items(
                theories, "theory", paper_context, topic, domain
            )

        # Build survival summary
        results["survival_summary"] = {
            "hidden_variables": self._count_survival(
                results["hidden_variable_tests"], len(hidden_variables)
            ),
            "mechanisms": self._count_survival(
                results["mechanism_tests"], len(mechanisms)
            ),
            "theories": self._count_survival(
                results["theory_tests"], len(theories)
            ),
        }

        return results

    def _test_items(
        self,
        items: list,
        item_type: str,
        paper_context: str,
        topic: str,
        domain: str,
    ) -> list:
        """Test a list of items (HV, mechanisms, or theories) adversarially."""
        tests = []

        for item in items[:5]:  # Cap at 5 to control token usage
            name = item.get("name", "Unnamed")
            desc = item.get("description", item.get("mechanism", ""))
            type_label = item.get("type", "")
            key_params = item.get("key_parameters", [])

            # Format key parameters
            param_text = ""
            for kp in key_params[:3]:
                if isinstance(kp, dict):
                    pname = kp.get("name", "")
                    pval = kp.get("expected_value", kp.get("value", ""))
                    psource = kp.get("source", "unknown")
                    param_text += f"\n  - {pname} = {pval} [{psource}]"

            prompt = f"""You are a ruthless scientific adversary. Your job is to DESTROY this discovery.
If it survives your attack, it's strong. If it doesn't, it should be killed.

TOPIC: {topic}
DOMAIN: {domain}

THE {item_type.upper()} UNDER ATTACK:
Name: {name}
Type: {type_label}
Description: {desc[:400]}
Key Parameters: {param_text if param_text else "None"}

EXISTING LITERATURE:
{paper_context[:1500]}

ATTACK WITH THESE THREE QUESTIONS:

1. EXISTING THEORY: What existing theory, mechanism, or known phenomenon already explains
   the same observations this {item_type} tries to explain? Be specific — cite papers or
   well-established results. If nothing exists, say "No known theory explains this."

2. VARIABLE REMOVAL: Can any new variable, entity, or parameter in this {item_type} be
   REMOVED while still explaining the observations? If the same effect can be achieved
   with fewer assumptions, the discovery is WEAK. Explain which variables are essential
   and which are unnecessary.

3. FALSIFICATION: What specific, measurable observation would FALSIFY this {item_type}?
   Be quantitative — "if we observe X > Y, this is wrong." If you cannot specify a
   falsification, the {item_type} is unfalsifiable and should be KILLED.

Output JSON:
{{
  "existing_theory": "What existing theory explains this (or 'None known')",
  "existing_theory_strength": "strong|moderate|weak|none",
  "can_remove_variables": true/false,
  "removable_variables": ["var1", "var2"] or [],
  "removal_reason": "Why they can be removed (or why all are essential)",
  "essential_variables": ["var1"] or [],
  "falsification": "Specific quantitative observation that would disprove this",
  "falsification_quality": "strong|moderate|weak|none",
  "survived": true/false,
  "attack_score": 0.0-1.0,
  "verdict": "survived|weakened|killed",
  "reasoning": "Why this survived or was killed (2-3 sentences)"
}}"""

            try:
                raw = self.llm_call(prompt, max_tokens=2048)
                if not raw:
                    from discovery.llm_client import call_json
                    raw = call_json(prompt, max_tokens=2048, provider="gemini")

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
                        result["name"] = name
                        result["item_type"] = item_type
                        # Determine verdict based on attack results
                        result = self._determine_verdict(result)
                        tests.append(result)
                        continue

            except Exception as e:
                pass

            # Fallback if LLM fails
            tests.append({
                "name": name,
                "item_type": item_type,
                "existing_theory": "Test failed — could not evaluate",
                "existing_theory_strength": "unknown",
                "can_remove_variables": False,
                "removable_variables": [],
                "removal_reason": "Test failed",
                "essential_variables": [],
                "falsification": "Test failed — could not evaluate",
                "falsification_quality": "unknown",
                "survived": True,  # benefit of the doubt
                "attack_score": 0.5,
                "verdict": "untested",
                "reasoning": "Adversarial test failed due to LLM error",
            })

        return tests

    def _determine_verdict(self, result: dict) -> dict:
        """Determine the final verdict based on attack results."""
        existing_strength = result.get("existing_theory_strength", "none")
        can_remove = result.get("can_remove_variables", False)
        falsification_quality = result.get("falsification_quality", "none")

        score = 0.5  # start neutral

        # Question 1: Existing theory
        if existing_strength == "strong":
            score -= 0.3  # strong existing theory = bad for novelty
        elif existing_strength == "moderate":
            score -= 0.15
        elif existing_strength == "weak":
            score += 0.05  # weak existing theory = supports novelty
        elif existing_strength == "none":
            score += 0.15  # no existing theory = genuinely novel

        # Question 2: Variable removal
        if can_remove:
            removable = len(result.get("removable_variables", []))
            essential = len(result.get("essential_variables", []))
            if removable > essential:
                score -= 0.25  # more removable than essential = weak
            else:
                score -= 0.1  # some can be removed but most are essential
        else:
            score += 0.1  # all variables are essential = strong

        # Question 3: Falsification
        if falsification_quality == "strong":
            score += 0.2  # strongly falsifiable = good science
        elif falsification_quality == "moderate":
            score += 0.1
        elif falsification_quality == "weak":
            score -= 0.1
        elif falsification_quality == "none":
            score -= 0.3  # unfalsifiable = bad

        # Clamp
        score = max(0.0, min(1.0, score))

        result["attack_score"] = round(score, 2)

        # Determine verdict
        if score >= 0.6:
            result["verdict"] = "survived"
            result["survived"] = True
        elif score >= 0.35:
            result["verdict"] = "weakened"
            result["survived"] = True  # survives but weakened
        else:
            result["verdict"] = "killed"
            result["survived"] = False

        return result

    def _count_survival(self, tests: list, started: int) -> dict:
        """Count survival stats."""
        survived = sum(1 for t in tests if t.get("verdict") == "survived")
        weakened = sum(1 for t in tests if t.get("verdict") == "weakened")
        killed = sum(1 for t in tests if t.get("verdict") == "killed")
        untested = sum(1 for t in tests if t.get("verdict") == "untested")
        return {
            "started": started,
            "survived": survived,
            "weakened": weakened,
            "killed": killed,
            "untested": untested,
        }

    def _fallback_test(self, hidden_variables, mechanisms, theories):
        """Fallback when no LLM available — mark all as untested."""
        return {
            "hidden_variable_tests": [
                {"name": hv.get("name", "?"), "verdict": "untested", "survived": True}
                for hv in hidden_variables
            ],
            "mechanism_tests": [
                {"name": m.get("name", "?"), "verdict": "untested", "survived": True}
                for m in mechanisms
            ],
            "theory_tests": [
                {"name": t.get("name", "?"), "verdict": "untested", "survived": True}
                for t in theories
            ],
            "survival_summary": {
                "hidden_variables": {"started": len(hidden_variables), "survived": 0, "weakened": 0, "killed": 0, "untested": len(hidden_variables)},
                "mechanisms": {"started": len(mechanisms), "survived": 0, "weakened": 0, "killed": 0, "untested": len(mechanisms)},
                "theories": {"started": len(theories), "survived": 0, "weakened": 0, "killed": 0, "untested": len(theories)},
            },
        }
