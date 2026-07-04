# RUMI Theory Revision Feedback Loop — Design Document

**Date:** 2026-06-30
**Status:** Design

---

## Problem

The pipeline has three review/assessment phases — Adversarial Test (8.5), Critical Evaluation (8.6), and Skeptic Review (11) — but **none of them actually improve the things they assess**. They score, attack, diagnose weaknesses, and assign verdicts, but the output is stored in the report and never fed back to revise theories, mechanisms, or predictions. The 3 exploration loops regenerated from scratch each iteration rather than using review feedback as explicit revision constraints.

This means:
- A theory that gets "weakened" by adversarial testing enters the next loop unchanged
- Critical evaluation's "major issues" are recorded but never addressed
- Skeptic review's improvement suggestions are informational only
- The loops converge by score stagnation, not by actually fixing identified problems

---

## Solution: Dual Feedback Loop (In-Loop + Post-Loop)

Two revision points:
1. **Phase 8.7 (In-Loop):** After adversarial test + critical evaluation, inside each of the 3 loops. Revises weakened/killed theories using test verdicts.
2. **Phase 11.5 (Post-Loop):** After skeptic review. Final polish pass on the winner + top theories using skeptic feedback.

Each produces a **tracked revision** stored in a new `revised_theories` report section with before/after comparison.

---

## Architecture

```
Current loop:
  Phase 6:  Mechanisms
  Phase 7:  Predictions  
  Phase 8:  Theory Competition → theories[0..N], winner
  Phase 8.3: Abstraction
  Phase 8.5: Adversarial Test → verdicts, falsifications, existing_theory matches
  Phase 8.6: Critical Evaluation → major_issues, recommendation, dimension scores
  Phase 8.7: ← NEW: Theory Revision ← uses 8.5 + 8.6 output
  ───────────────────→ next loop iteration (revised theories injected into Phase 8)

Post-loop:
  Phase 11:  Skeptic Review → weaknesses, improvement_suggestions
  Phase 11.5: ← NEW: Post-Skeptic Revision ← uses 11 output
  Phase 12:  Discovery Scoring
```

### Phase 8.7 — In-Loop Revision

**Inputs:**
- `theories` (current list of all theories)
- `winner` (current best theory)
- `adversarial_test` results (from Phase 8.5): per-theory verdicts, existing theory matches, falsification conditions
- `critical_evaluation` results (from Phase 8.6): major_issues, minor_issues, dimension scores, recommendation
- `mechanisms` (current list)
- `accepted_preds`

**Process:**
1. Collect all theories where `adversarial_verdict` is "weakened" or "killed"
2. Collect the winner theory if critical evaluation is "major_revision" or "reject"
3. For each target theory, build a revision prompt containing:
   - Original theory name, description, mechanism
   - Adversarial verdict + existing theory match + falsification condition
   - Critical eval issues
   - Domain ontology for grounding
4. LLM generates a revised theory that addresses each issue specifically
5. The revised theory retains provenance back to the original (name includes "Revised: " prefix)
6. If the winner theory was revised, it replaces winner; otherwise revised theories are added alongside originals
7. The next loop's Phase 8 (Theory Competition) includes revised theories as candidates

**Output structure (per theory):**
```python
{
    "original_name": "Exosomal microRNA Hormesis Hypothesis",
    "original_score": 0.61,
    "revision_round": 1,  # 1 for loop 1, 2 for loop 2
    "trigger": {
        "adversarial_verdict": "weakened",
        "adversarial_reason": "Existing theory: GLP-1 receptor agonists' effects...",
        "falsification": "If administration does not result in...",
        "critical_eval_issues": ["Lack of empirical evidence", "Incomplete predictions"],
        "critical_eval_score": 5.33,
    },
    "revised": {
        "name": "Revised: Exosomal microRNA Hormesis Hypothesis",
        "description": "...",
        "mechanism": "...",
        "type": "causal_pathway",
        "predictions": [...],
        "scores": {"overall": 0.69},  # updated by theory competition
    },
    "improvements_made": [
        "Added empirical grounding from GLP-1 cardiovascular outcome trials",
        "Included specific miRNA candidates (miR-21, miR-126) with measurement methods",
    ],
    "unresolved_issues": [
        "Requires in vitro validation in endothelial cell culture",
    ],
    "delta_score": +0.08,  # computed after theory competition re-scoring
}
```

**Report section (new):**
```python
report["phases"]["theory_revision"] = {
    "revision_rounds": [
        {
            "loop": 1,
            "strategy": "exploratory",
            "theories_targeted": 3,
            "theories_revised": 2,
            "winner_was_revised": True,
        }
    ],
    "all_revisions": [ ... ],  # list of all revision records across loops
}
```

### Phase 11.5 — Post-Skeptic Revision

**Inputs:**
- `winner` (best theory after all loops)
- `theories` (final list)
- `skeptic_review` results: weaknesses, improvement_suggestions, failure_conditions, recommendation

**Process:**
1. If skeptic recommendation is "revise", create a final revised version of the winner
2. The revision prompt includes skeptic's strengths (keep these), weaknesses (fix these), failure_conditions (address these), improvement_suggestions
3. The revised theory is labeled as "Skeptic-Refined: [name]"
4. If score delta > threshold, it becomes the new canonical winner

**Output:** Same structure as Phase 8.7 revisions, but with `trigger.skeptic_review` filled instead.

### Report Display

A dedicated **"Theory Revisions"** section in the final report with:

```
=== Theory Revisions ===

Loop 1 (exploratory):
  Revised: Exosomal microRNA Hormesis Hypothesis
    Original: 0.61 → Revised: 0.69 (+0.08)
    Improvements:
      ✓ Added empirical grounding from CVOT trials
      ✓ Included specific miRNA candidates with measurement methods
    Unresolved:
      ✗ Requires in vitro validation

  Revised: Endothelial cAMP-PKA-eNOS Pathway
    Original: 0.58 → Revised: 0.55 (-0.03) [regression, keep original]

Post-Skeptic Refinement:
  Skeptic-Refined: Dynamic Homeostatic Shift Theory
    Original: 0.64 → Refined: 0.71 (+0.07)
    Addressed skeptic concerns:
      ✓ Clarified causal direction between GLP-1R activation and NO production
      ✓ Added specific dose-response predictions
```

---

## Implementation Plan

### Files to create:
1. `discovery/theory_revision.py` — TheoryRevisionEngine class with `revise_theories()` method

### Files to modify:
1. `discovery/discovery_pipeline_v2.py`:
   - Insert Phase 8.7 call after Phase 8.6 inside the main loop
   - Pass revision results into next loop iteration (inject into `theories` list before Phase 8)
   - Insert Phase 11.5 call after Phase 11
   - Add revision data to the final report structure

2. `discovery/discovery_scorer.py` — Minor: recognize "Revised:" prefix theories and compute delta scores

3. `discovery/output.py` or report generation — Add "Theory Revisions" section to terminal output and JSON report

### TheoryRevisionEngine API:

```python
class TheoryRevisionEngine:
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
        Returns { "revisions": [...], "revised_theories": [...], "winner_replaced": bool }
        """

    def post_skeptic_revision(
        self,
        winner: dict,
        skeptic_result: dict,
        domain: str,
        topic: str,
    ) -> dict:
        """
        Final polish pass using skeptic review feedback.
        Returns { "revision": {...}, "winner_updated": bool }
        """
```

### Revision Prompt Strategy

The LLM prompt for revision must be structured to force specific, grounded improvements — not generic "this needs more research" hand-waving:

```
You are revising a scientific theory based on peer review feedback.

ORIGINAL THEORY: {name}
DESCRIPTION: {description}
ORIGINAL SCORE: {score}

ADVERSARIAL TEST VERDICT: {verdict} ({reason})
EXISTING THEORY MATCH: {existing_theory}
FALSIFICATION CONDITION: {falsification}

CRITICAL EVALUATION ISSUES:
{bullet list of major/minor issues}

YOUR TASK: Produce a revised version that addresses EVERY issue above.
For each issue, include a specific, concrete improvement (not generic).

RULES:
- Do NOT change the core hypothesis — strengthen it
- Add specific empirical references from published literature where possible
- If falsification condition was identified, address it explicitly
- If existing theory explains the same thing, explain why your theory adds value
- Include at least one new testable prediction that addresses the identified weakness

Output JSON:
{
  "revised_name": "...",
  "revised_description": "...",
  "improvements_made": ["imp1", "imp2"],
  "unresolved_issues": ["issue1"],
  "new_predictions": ["pred1"],
  "revised_mechanism": "..."
}
```

---

## Constraints

1. **Provenance is mandatory.** Every revision must trace back to its original. The `original_name` and `revision_round` fields are not optional.
2. **No infinite loops.** Max 1 revision per loop iteration (so max 3 in-loop revisions total + 1 post-skeptic). If a revision scores lower than the original, keep the original — report it as "regression, kept original."
3. **Do not revise known science.** Theories classified as `rediscovery` or `well_known` should not be revised — they are already explained by existing literature.
4. **Minimal LLM cost.** Only revise theories that actually have actionable feedback (killed/weakened + major issues). If all theories survived with high scores and critical eval says "accept," skip revision.
5. **Revision doesn't replace the original in the report.** Both are preserved. The report shows original and revised side by side with delta.

---

## Edge Cases

| Case | Behavior |
|------|----------|
| All theories survived, critical eval "accept" | Skip revision entirely |
| Revision scores lower than original | Keep original, tag revision as "regression" |
| LLM fails during revision | Log error, skip that theory, continue with others |
| Same theory revised across multiple loops | Each revision is a separate entry with increasing `revision_round` |
| Skeptic says "reject" | Still attempt revision (reject ≠ unfixable), but mark it as "high risk" |
| Theory name already has "Revised:" prefix from prior loop | Replace the prefix with "Revised v2:" etc. |
