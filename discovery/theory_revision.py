"""
theory_revision.py — Theory Revision Feedback Loop for RUMI Discovery Pipeline

Feeds adversarial test, critical evaluation, and skeptic review results
back into theory revision. Produces tracked before/after revisions with
provenance (original -> revised mapping).

Phase 8.7: In-loop revision (after adversarial + critical eval)
Phase 11.5: Post-skeptic revision (after skeptic review)
"""

import json
from typing import Dict, List, Optional


class TheoryRevisionEngine:
    """
    Revises theories based on peer review feedback.
    Two entry points: revise_theories() for in-loop, post_skeptic_revision() for final polish.
    """

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def revise_theories(
        self,
        theories: list,
        winner: dict,
        adversarial_results: dict,
        critical_eval: dict,
        mechanisms: list,
        predictions: list,
        domain: str,
        topic: str,
        papers: list,
        revision_round: int,
    ) -> dict:
        """
        Revise theories based on adversarial + critical evaluation feedback.

        Returns:
            {
                "revisions": [...],           # all revision records
                "revised_theories": [...],    # theory dicts ready for next loop
                "winner_replaced": bool,      # whether winner was swapped
                "summary": { "targeted": N, "revised": N, "skipped": N }
            }
        """
        if not self.llm_call:
            return self._empty_result()

        targets = self._collect_revision_targets(theories, winner, adversarial_results, critical_eval)
        if not targets:
            return self._empty_result()

        revisions = []
        revised_theories = []
        winner_replaced = False

        for target in targets:
            theory = target["theory"]
            trigger = target["trigger"]

            if theory.get("is_novel_vs_known") in ("well_known", "rediscovery"):
                continue

            revision = self._revise_single_theory(
                theory, trigger, mechanisms, predictions, domain, topic, papers, revision_round
            )
            if revision:
                revisions.append(revision)
                revised = revision.get("revised", {})
                if revised:
                    revised["_revision_source"] = theory.get("name", "")
                    revised["_is_revision"] = True
                    revised_theories.append(revised)

                    if theory.get("name") == winner.get("name"):
                        winner_replaced = True

        for rev in revisions:
            orig_score = rev.get("original_score", 0)
            rev_score = rev.get("revised", {}).get("scores", {}).get("overall", 0)
            # delta_score is computed after theory competition scores the revised theory
            # At generation time, rev_score is 0 (not yet scored) — mark as pending
            if rev_score and rev_score > 0:
                rev["delta_score"] = round(rev_score - orig_score, 3)
            else:
                rev["delta_score"] = 0
                rev["delta_pending"] = True  # will be scored in next loop's theory competition

        return {
            "revisions": revisions,
            "revised_theories": revised_theories,
            "winner_replaced": winner_replaced,
            "summary": {
                "targeted": len(targets),
                "revised": len(revisions),
                "skipped": len(targets) - len(revisions),
            },
        }

    def post_skeptic_revision(
        self,
        winner: dict,
        skeptic_result: dict,
        domain: str,
        topic: str,
    ) -> dict:
        """
        Final polish pass on the winner using skeptic review feedback.

        Returns:
            {
                "revision": {...} or None,
                "revised_theory": {...} or None,
                "winner_updated": bool
            }
        """
        if not self.llm_call or not winner or not skeptic_result:
            return {"revision": None, "revised_theory": None, "winner_updated": False}

        weaknesses = skeptic_result.get("weaknesses", [])
        improvement_suggestions = skeptic_result.get("improvement_suggestions", [])
        failure_conditions = skeptic_result.get("failure_conditions", [])
        strengths = skeptic_result.get("strengths", [])
        recommendation = skeptic_result.get("recommendation", "")

        if not weaknesses and not improvement_suggestions:
            return {"revision": None, "revised_theory": None, "winner_updated": False}

        if winner.get("is_novel_vs_known") in ("well_known", "rediscovery"):
            return {"revision": None, "revised_theory": None, "winner_updated": False}

        revision = self._revise_with_skeptic_feedback(
            winner, strengths, weaknesses, improvement_suggestions,
            failure_conditions, recommendation, domain, topic
        )

        if not revision:
            return {"revision": None, "revised_theory": None, "winner_updated": False}

        revised = revision.get("revised", {})
        if revised:
            revised["_revision_source"] = winner.get("name", "")
            revised["_is_revision"] = True
            revised["_is_skeptic_refined"] = True

        return {
            "revision": revision,
            "revised_theory": revised,
            "winner_updated": revised is not None,
        }

    # -- Internal helpers --

    def _collect_revision_targets(self, theories, winner, adversarial_results, critical_eval):
        """Identify which theories need revision based on review feedback."""
        targets = []

        theory_tests = {}
        if adversarial_results:
            for t in adversarial_results.get("theory_tests", []):
                theory_tests[t.get("name", "")] = t

        crit_issues = []
        if critical_eval:
            crit_issues = critical_eval.get("major_issues", []) + critical_eval.get("minor_issues", [])
            crit_score = critical_eval.get("overall_score", 10)
            crit_rec = critical_eval.get("recommendation", "accept")
        else:
            crit_score = 10
            crit_rec = "accept"

        for theory in theories:
            name = theory.get("name", "")
            test = theory_tests.get(name, {})
            verdict = test.get("verdict", "survived")

            needs_revision = False
            trigger = {
                "adversarial_verdict": verdict,
                "adversarial_reason": test.get("reasoning", ""),
                "existing_theory": test.get("existing_theory", ""),
                "falsification": test.get("falsification", ""),
                "critical_eval_issues": crit_issues if name == winner.get("name") else [],
                "critical_eval_score": crit_score,
            }

            if verdict in ("challenged", "superseded"):
                needs_revision = True
            elif name == winner.get("name") and crit_rec in ("major_revision", "reject"):
                needs_revision = True

            if needs_revision:
                targets.append({"theory": theory, "trigger": trigger})

        return targets

    def _revise_single_theory(self, theory, trigger, mechanisms, predictions, domain, topic, papers, revision_round):
        """Revise a single theory based on adversarial + critical eval feedback."""
        name = theory.get("name", "Unnamed")
        desc = theory.get("description", theory.get("mechanism", ""))
        mechanism = theory.get("mechanism", "")
        original_score = theory.get("scores", {}).get("overall", 0)

        paper_ctx = ""
        for p in papers[:5]:
            if isinstance(p, dict):
                paper_ctx += f"\n- [{p.get('title', '')}] {p.get('abstract', '')[:200]}"

        issues_text = ""
        if trigger.get("critical_eval_issues"):
            # Safety: convert dicts to strings
            raw_issues = trigger["critical_eval_issues"]
            str_issues = []
            for issue in raw_issues:
                if isinstance(issue, dict):
                    str_issues.append(issue.get("issue", issue.get("description", str(issue))))
                else:
                    str_issues.append(str(issue))
            issues_text = "\n".join(f"  - {issue}" for issue in str_issues)
        else:
            issues_text = "  No specific issues identified."

        prompt = f"""You are revising a scientific theory based on peer review feedback.

ORIGINAL THEORY: {name}
DESCRIPTION: {desc[:500]}
MECHANISM: {mechanism[:300] if mechanism else "None specified"}
ORIGINAL SCORE: {original_score}

ADVERSARIAL TEST:
  Verdict: {trigger.get('adversarial_verdict', 'survived')}
  Reasoning: {trigger.get('adversarial_reason', 'N/A')}
  Existing Theory Match: {trigger.get('existing_theory', 'None known')}
  Falsification Condition: {trigger.get('falsification', 'N/A')}

CRITICAL EVALUATION ISSUES (score: {trigger.get('critical_eval_score', 'N/A')}/10):
{issues_text}

DOMAIN: {domain}
TOPIC: {topic}

EXISTING LITERATURE:
{paper_ctx[:1500] if paper_ctx else "No papers available"}

YOUR TASK: Produce a revised version that addresses EVERY issue above.
For each issue, include a specific, concrete improvement (not generic).

RULES:
- Do NOT change the core hypothesis — strengthen it
- Add specific empirical references from published literature where possible
- If falsification condition was identified, address it explicitly
- If existing theory explains the same thing, explain why your theory adds value
- Include at least one new testable prediction that addresses the identified weakness

Output JSON:
{{
  "revised_name": "Revised: {name}" or "Revised v2: {name}" if already revised,
  "revised_description": "...",
  "revised_mechanism": "...",
  "improvements_made": ["imp1", "imp2"],
  "unresolved_issues": ["issue1"],
  "new_predictions": ["pred1"]
}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=4096)
            if not raw:
                return None

            if isinstance(raw, str):
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                    raw = raw.rsplit("```", 1)[0].strip()

            result = json.loads(raw) if isinstance(raw, str) else raw

            if not isinstance(result, dict) or not result.get("revised_description"):
                return None

            revised = dict(theory)
            revised["name"] = result.get("revised_name", f"Revised: {name}")
            revised["description"] = result.get("revised_description", desc)
            revised["mechanism"] = result.get("revised_mechanism", mechanism)
            revised["type"] = theory.get("type", "causal_pathway")
            revised["predictions"] = theory.get("predictions", []) + [
                {"prediction": p, "type": "revision_addition"} for p in result.get("new_predictions", [])
            ]

            return {
                "original_name": name,
                "original_score": original_score,
                "revision_round": revision_round,
                "trigger": trigger,
                "revised": revised,
                "improvements_made": result.get("improvements_made", []),
                "unresolved_issues": result.get("unresolved_issues", []),
                "delta_score": 0,
            }

        except Exception as e:
            print(f"  [WARN] Theory revision failed for '{name[:40]}': {e}", flush=True)
            return None

    def _revise_with_skeptic_feedback(self, winner, strengths, weaknesses, suggestions, failure_conditions, recommendation, domain, topic):
        """Revise the winner theory based on skeptic review feedback."""
        name = winner.get("name", "Unnamed")
        desc = winner.get("description", winner.get("mechanism", ""))
        mechanism = winner.get("mechanism", "")
        original_score = winner.get("scores", {}).get("overall", 0)

        strengths_text = "\n".join(f"  + {s}" for s in strengths[:5]) if strengths else "  None identified"
        weaknesses_text = "\n".join(f"  - {w}" for w in weaknesses[:5]) if weaknesses else "  None identified"
        suggestions_text = "\n".join(f"  * {s}" for s in suggestions[:5]) if suggestions else "  None"
        failures_text = "\n".join(f"  ! {f}" for f in failure_conditions[:5]) if failure_conditions else "  None"

        prompt = f"""You are doing a FINAL REVISION of a scientific theory based on skeptic review.

THEORY: {name}
DESCRIPTION: {desc[:500]}
MECHANISM: {mechanism[:300] if mechanism else "None"}
SCORE: {original_score}
SKEPTIC RECOMMENDATION: {recommendation}

STRENGTHS (keep these):
{strengths_text}

WEAKNESSES (fix these):
{weaknesses_text}

IMPROVEMENT SUGGESTIONS:
{suggestions_text}

FAILURE CONDITIONS (address these):
{failures_text}

DOMAIN: {domain}
TOPIC: {topic}

RULES:
- Keep ALL strengths — do not weaken what already works
- Address EVERY weakness with a concrete fix
- Address every failure condition explicitly
- If skeptic says "reject", explain why the theory still has merit after revision
- Add specific empirical references where possible

Output JSON:
{{
  "revised_name": "Skeptic-Refined: {name}",
  "revised_description": "...",
  "revised_mechanism": "...",
  "improvements_made": ["imp1", "imp2"],
  "unresolved_issues": ["issue1"],
  "new_predictions": ["pred1"]
}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=4096)
            if not raw:
                return None

            if isinstance(raw, str):
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                    raw = raw.rsplit("```", 1)[0].strip()

            result = json.loads(raw) if isinstance(raw, str) else raw

            if not isinstance(result, dict) or not result.get("revised_description"):
                return None

            revised = dict(winner)
            revised["name"] = result.get("revised_name", f"Skeptic-Refined: {name}")
            revised["description"] = result.get("revised_description", desc)
            revised["mechanism"] = result.get("revised_mechanism", mechanism)
            revised["predictions"] = winner.get("predictions", []) + [
                {"prediction": p, "type": "skeptic_refinement"} for p in result.get("new_predictions", [])
            ]

            return {
                "original_name": name,
                "original_score": original_score,
                "revision_round": 0,
                "trigger": {
                    "skeptic_recommendation": recommendation,
                    "skeptic_weaknesses": weaknesses,
                    "skeptic_suggestions": suggestions,
                    "failure_conditions": failure_conditions,
                },
                "revised": revised,
                "improvements_made": result.get("improvements_made", []),
                "unresolved_issues": result.get("unresolved_issues", []),
                "delta_score": 0,
            }

        except Exception as e:
            print(f"  [WARN] Skeptic revision failed: {e}", flush=True)
            return None

    def _empty_result(self):
        return {
            "revisions": [],
            "revised_theories": [],
            "winner_replaced": False,
            "summary": {"targeted": 0, "revised": 0, "skipped": 0},
        }
