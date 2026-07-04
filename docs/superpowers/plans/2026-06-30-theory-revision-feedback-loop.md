# Theory Revision Feedback Loop — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Feed adversarial test + critical evaluation + skeptic review results back into theory revision, producing tracked before/after revisions in the report.

**Architecture:** New `TheoryRevisionEngine` class in `discovery/theory_revision.py` with two entry points: `revise_theories()` for in-loop Phase 8.7, and `post_skeptic_revision()` for Phase 11.5. Pipeline integration via 3 insertion points in `discovery_pipeline_v2.py`.

**Tech Stack:** Python, existing `llm_call` / `call_json` from `discovery.llm_client`, `extract_json` from `discovery.json_extract`.

---

### Task 1: Create theory_revision.py

**Files:**
- Create: `discovery/theory_revision.py`

- [ ] **Step 1: Write the TheoryRevisionEngine module**

```python
"""
theory_revision.py — Theory Revision Feedback Loop for RUMI Discovery Pipeline

Feeds adversarial test, critical evaluation, and skeptic review results
back into theory revision. Produces tracked before/after revisions with
provenance (original → revised mapping).

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

        # 1. Collect theories that need revision
        targets = self._collect_revision_targets(theories, winner, adversarial_results, critical_eval)
        if not targets:
            return self._empty_result()

        revisions = []
        revised_theories = []
        winner_replaced = False

        for target in targets:
            theory = target["theory"]
            trigger = target["trigger"]

            # Skip known science — no point revising textbook knowledge
            if theory.get("is_novel_vs_known") in ("well_known", "rediscovery"):
                continue

            revision = self._revise_single_theory(
                theory, trigger, mechanisms, predictions, domain, topic, papers, revision_round
            )
            if revision:
                revisions.append(revision)
                revised = revision.get("revised", {})
                if revised:
                    # Tag as revised for theory competition
                    revised["_revision_source"] = theory.get("name", "")
                    revised["_is_revision"] = True
                    revised_theories.append(revised)

                    # If winner was revised, track it
                    if theory.get("name") == winner.get("name"):
                        winner_replaced = True

        # Compute delta scores if possible
        for rev in revisions:
            orig_score = rev.get("original_score", 0)
            rev_score = rev.get("revised", {}).get("scores", {}).get("overall", 0)
            rev["delta_score"] = round(rev_score - orig_score, 3) if rev_score else 0

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

        recommendation = skeptic_result.get("recommendation", "")
        weaknesses = skeptic_result.get("weaknesses", [])
        improvement_suggestions = skeptic_result.get("improvement_suggestions", [])
        failure_conditions = skeptic_result.get("failure_conditions", [])
        strengths = skeptic_result.get("strengths", [])

        # Only revise if there's something to fix
        if not weaknesses and not improvement_suggestions:
            return {"revision": None, "revised_theory": None, "winner_updated": False}

        # Skip known science
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

    # ── Internal ─────────────────────────────────────────────────

    def _collect_revision_targets(self, theories, winner, adversarial_results, critical_eval):
        """Identify which theories need revision based on review feedback."""
        targets = []

        # Map theory names to their adversarial verdicts
        theory_tests = {}
        if adversarial_results:
            for t in adversarial_results.get("theory_tests", []):
                theory_tests[t.get("name", "")] = t

        # Map critical eval issues
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

            # Target: challenged/superseded theories, or winner if critical eval is bad
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

        # Build paper context for grounding
        paper_ctx = ""
        for p in papers[:5]:
            if isinstance(p, dict):
                paper_ctx += f"\n- [{p.get('title', '')}] {p.get('abstract', '')[:200]}"

        # Build issues text
        issues_text = ""
        if trigger.get("critical_eval_issues"):
            issues_text = "\n".join(f"  - {issue}" for issue in trigger["critical_eval_issues"])
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

            # Build revised theory dict
            revised = dict(theory)  # copy original
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
                "delta_score": 0,  # computed later
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
                "revision_round": 0,  # post-loop
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
```

- [ ] **Step 2: Verify module imports cleanly**

Run: `cd C:\Users\Admin\Desktop\rumi && python -c "from discovery.theory_revision import TheoryRevisionEngine; print('OK')"`
Expected: `OK`

---

### Task 2: Integrate Phase 8.7 into pipeline loop

**Files:**
- Modify: `discovery/discovery_pipeline_v2.py` (lines ~2155-2198, after Critical Evaluation, before convergence check)

- [ ] **Step 1: Add import at top of pipeline file**

After line ~83 (`from discovery.cross_validation import CrossValidator`), add:
```python
from discovery.theory_revision import TheoryRevisionEngine
```

- [ ] **Step 2: Insert Phase 8.7 after Phase 8.6**

After the Critical Evaluation block (after line ~2156 where `report["errors"].append(f"Phase 8.6: {e}")` ends), before the convergence/regression detection block, insert:

```python
        # ══════════════════════════════════════════════════════════════
        # PHASE 8.7: THEORY REVISION — Feed review feedback into improvements
        # ══════════════════════════════════════════════════════════════
        print("\n[Phase 8.7/12] THEORY REVISION — Revising based on review feedback...", flush=True)
        _current_phase["name"] = "theory_revision"
        try:
            revision_engine = TheoryRevisionEngine(llm_call=_truncated_llm)
            rev_result = revision_engine.revise_theories(
                theories=theories,
                winner=winner or {},
                adversarial_results=report.get("phases", {}).get("adversarial_test", {}),
                critical_eval=report.get("phases", {}).get("peer_review", {}),
                mechanisms=mechanisms,
                predictions=accepted_preds,
                domain=domain,
                topic=topic,
                papers=papers,
                revision_round=_li + 1,
            )
            rev_summary = rev_result.get("summary", {})
            rev_count = rev_summary.get("revised", 0)
            targeted_count = rev_summary.get("targeted", 0)
            if rev_count > 0:
                print(f"  [Theory Revision] {targeted_count} targeted -> {rev_count} revised", flush=True)
                for rev in rev_result.get("revisions", []):
                    orig_name = rev.get("original_name", "?")[:40]
                    revised_name = rev.get("revised", {}).get("name", "?")[:40]
                    delta = rev.get("delta_score", 0)
                    delta_str = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
                    print(f"    {orig_name} -> {revised_name} (delta: {delta_str})", flush=True)
            else:
                print(f"  [Theory Revision] No revisions needed (all survived or no actionable feedback)", flush=True)

            # Inject revised theories into the theory pool for next loop iteration
            revised_theories = rev_result.get("revised_theories", [])
            if revised_theories:
                # Add revised theories alongside originals (don't remove originals)
                theories.extend(revised_theories)

            # Store revision data in report
            if _li == 0:
                report["phases"]["theory_revision"] = {
                    "revision_rounds": [],
                    "all_revisions": [],
                }
            report["phases"]["theory_revision"]["revision_rounds"].append({
                "loop": _li + 1,
                "strategy": _lab,
                "theories_targeted": targeted_count,
                "theories_revised": rev_count,
                "winner_was_revised": rev_result.get("winner_replaced", False),
            })
            report["phases"]["theory_revision"]["all_revisions"].extend(rev_result.get("revisions", []))

        except Exception as e:
            print(f"  [WARN] Theory revision failed: {e}", flush=True)
```

- [ ] **Step 3: Verify pipeline still parses**

Run: `cd C:\Users\Admin\Desktop\rumi && python -c "from discovery.discovery_pipeline_v2 import run_discovery_pipeline; print('OK')"`
Expected: `OK`

---

### Task 3: Integrate Phase 11.5 (Post-Skeptic Revision)

**Files:**
- Modify: `discovery/discovery_pipeline_v2.py` (after Phase 11 Skeptic Review, before Phase 12 Scoring)

- [ ] **Step 1: Insert Phase 11.5 after skeptic review**

After the skeptic review block ends (after the `report["phases"]["skeptic_review"]` assignment around line ~2655), before the Phase 11.6 cross-validation section, insert:

```python
    # ══════════════════════════════════════════════════════════════
    # PHASE 11.5: POST-SKEPTIC REVISION — Final polish on winner
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 11.5/12] POST-SKEPTIC REVISION — Final refinement...", flush=True)
    try:
        revision_engine = TheoryRevisionEngine(llm_call=_truncated_llm)
        post_skeptic = revision_engine.post_skeptic_revision(
            winner=winner or (theories[0] if theories else {}),
            skeptic_result=skeptic_result,
            domain=domain,
            topic=topic,
        )
        if post_skeptic.get("winner_updated"):
            revised_theory = post_skeptic["revised_theory"]
            print(f"  [Skeptic Revision] Winner refined: {revised_theory.get('name', '?')[:50]}", flush=True)
            # Replace winner with skeptic-refined version
            if winner:
                # Store original winner in revision history
                if "theory_revision" not in report.get("phases", {}):
                    report["phases"]["theory_revision"] = {"revision_rounds": [], "all_revisions": []}
                report["phases"]["theory_revision"]["all_revisions"].append(post_skeptic["revision"])
                winner = revised_theory
                # Also update in theories list
                for i, t in enumerate(theories):
                    if t.get("name") == winner.get("_revision_source"):
                        theories[i] = revised_theory
                        break
            else:
                winner = revised_theory
        else:
            print(f"  [Skeptic Revision] No revision needed", flush=True)
    except Exception as e:
        print(f"  [WARN] Post-skeptic revision failed: {e}", flush=True)
```

- [ ] **Step 2: Verify pipeline still parses**

Run: `cd C:\Users\Admin\Desktop\rumi && python -c "from discovery.discovery_pipeline_v2 import run_discovery_pipeline; print('OK')"`
Expected: `OK`

---

### Task 4: Add Theory Revisions section to terminal output

**Files:**
- Modify: `discovery/discovery_pipeline_v2.py` (in the RESULTS SUMMARY section, after score/grade output)

- [ ] **Step 1: Add revisions summary to terminal output**

After the existing results summary section (around line ~371 where `print(f"  Time: {total_time:.0f}s")` is), add:

```python
    # -- Theory Revisions summary --
    rev_data = report.get("phases", {}).get("theory_revision", {})
    all_revisions = rev_data.get("all_revisions", [])
    if all_revisions:
        print(f"\n{'='*70}")
        print("THEORY REVISIONS")
        print(f"{'='*70}")
        for round_info in rev_data.get("revision_rounds", []):
            loop_num = round_info.get("loop", "?")
            strategy = round_info.get("strategy", "?")
            targeted = round_info.get("theories_targeted", 0)
            revised = round_info.get("theories_revised", 0)
            print(f"\n  Loop {loop_num} ({strategy}): {targeted} targeted -> {revised} revised")
        for rev in all_revisions:
            orig_name = rev.get("original_name", "?")[:45]
            revised_name = rev.get("revised", {}).get("name", "?")[:45]
            orig_score = rev.get("original_score", 0)
            delta = rev.get("delta_score", 0)
            delta_str = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
            improvements = rev.get("improvements_made", [])
            unresolved = rev.get("unresolved_issues", [])
            print(f"\n  {orig_name}")
            print(f"    -> {revised_name}")
            print(f"    Score: {orig_score:.3f} -> {orig_score + delta:.3f} ({delta_str})")
            if improvements:
                for imp in improvements[:2]:
                    print(f"      + {imp[:70]}")
            if unresolved:
                for iss in unresolved[:1]:
                    print(f"      - {iss[:70]}")
```

---

### Task 5: End-to-end verification

- [ ] **Step 1: Dry-run import chain**

Run: `cd C:\Users\Admin\Desktop\rumi && python -c "from discovery.theory_revision import TheoryRevisionEngine; from discovery.discovery_pipeline_v2 import run_discovery_pipeline; print('All imports OK')"`
Expected: `All imports OK`

- [ ] **Step 2: Run a quick discovery to verify Phase 8.7 and 11.5 execute**

Run: `cd C:\Users\Admin\Desktop\rumi && python run_discovery.py --cause "Why does aspirin reduce cancer risk?" --domain drug_discovery --mode quick`
Expected: Pipeline completes, phases 8.7 and 11.5 appear in output (or say "no revisions needed" if all theories survived cleanly)
