# eval/ — RUMI's External Evaluation Harness

A **frozen, out-of-reach** measuring rig. It takes a finished RUMI report as
data and computes the headline quality numbers **RUMI cannot self-report**.

## Why it exists

RUMI currently grades itself. The "discovery score" is built from numbers its
own LLM produces (confidence, novelty), and the Reflexion self-improvement loop
then edits prompts/thresholds to raise those same self-reported numbers. That
is the reward-hacking failure mode documented for autonomous research agents
(Huang et al., 2026: 30.5% spontaneous rate on open-ended research pipelines).

This harness is the countermeasure. The core metrics are **deterministic**
(no LLM), so they cannot drift with model updates and cannot be prompt-gamed.

## The contract

- **External** — the agent must never modify anything under `eval/`. The
  Reflexion loop's `FORBIDDEN_FILES` includes this package, and its module
  finder only searches `discovery/` and `brain/`.
- **Frozen** — weights, thresholds, judge model, and the held-out corpus live
  in `config.json` / `corpus/heldout.json`, not in RUMI.
- **Independent** — the harness never calls RUMI's own scorers.
- **Deterministic** — metrics 1–5 use no model. Only the optional judge does.
- **One-way** — eval reads RUMI output; RUMI may *read back* the score, but
  never the computation or the ground truth.

## Metrics

| metric | what it catches | deterministic |
|---|---|---|
| `citation_validity` | `[N]` citations pointing at no real paper | yes |
| `claim_support_rate` | factual claims with no citation (recomputed independently of RUMI's own grounding) | yes |
| `novelty_vs_archive` | rediscovery of a theory from a prior run (uses RUMI's own persistent archive) | yes |
| `score_consistency` | reported `discovery_score` exceeding the ceiling its own dimension scores allow → **score inflation** | yes |
| `structure_completeness` | missing predictions / falsification criteria / mechanism steps / computation | yes |
| `novelty_vs_heldout` | overlap with held-out known findings (disabled until corpus is populated) | yes |
| `judge_claim_support` | cross-family LLM verdict on whether evidence supports each claim (optional) | no |

`external_score` = weighted sum (`config.json:weights`), 0–100. This is the
number that should be shown as *the* score, not RUMI's self-reported one.

## Flow (continuity)

```
run_discovery.py / main.py / continuous_operation.py
        │
        ▼
run_discovery_pipeline()            (16 phases …)
        │
        ▼
_finalize_report()  ──► eval.harness.run_external_eval(report, papers)
        │                          │
        │                          ├─► eval/ledger.jsonl      (hash-chained, append-only)
        │                          └─► data/discovery_archive.json run["external_score"]
        ▼
   data/discovery_v2_<ts>.json  (now contains report["external_eval"])
```

The score ships **inside** the report, is appended to a tamper-evident ledger,
and is stamped onto the archived run so the next run's `get_archive_context`
can reference it. Nothing is a bolt-on island.

## Usage

Automatically runs inside every pipeline run (see `_finalize_report`).

Re-score any past report fully outside RUMI:

```
python -m eval.harness data/discovery_v2_1783710709.json
python -m eval.harness data/discovery_v2_1783710709.json --judge
```

Run the tests:

```
python -m pytest eval/tests -q
```

## Regression corpus & leaderboard (Phase 0)

Freeze saved reports into a corpus so changes can be measured WITHOUT a full
discovery run. The corpus is trimmed to harness-relevant fields and the
knowledge archive is snapshotted, so scores are deterministic.

```
python -m eval.regression build        # data/discovery_v2_*.json -> frozen fixtures + baseline
python -m eval.regression check        # re-score fixtures, fail on regression
python -m eval.regression leaderboard  # ranked table -> eval/leaderboard.json
```

Corpus: `eval/corpus/regression/` (`reports/`, `baseline.json`, `archive_snapshot.json`).

## Offline scorer replay

Measure scorer **code** changes (not just report changes) without a full run:

```
python -m eval.replay data/discovery_v2_<ts>.json
```

Rebuilds the scorer inputs from a stored report and diffs the affected
dimensions against what the report recorded. Approximate — gaps/anomalies/
papers/graph are not stored in the report.

## Archive backfill

Runs that predate the harness have no `external_score`, which starves the
Reflexion gate. Re-score the saved reports and backfill the archive (marks each
run `external_source="backfill"`; never overwrites a live score):

```
python -m eval.backfill_archive            # dry run
python -m eval.backfill_archive --apply    # write data/discovery_archive.json
```

## Reflexion gate (A2)

The self-improvement loop no longer scores itself on "patches applied". Its
objective is the external score, and every patch must clear a frozen gate:

- **In-cycle gate** (`brain/reflexion.py::_regression_gate`): a provisional
  patch is only committed if `pytest eval/tests` and `eval.regression check`
  still pass in a fresh interpreter. Otherwise it is restored from backup.
- **Cross-cycle gate** (`_evaluate_previous_cycle`): a cycle's patches are
  provisional until a later run of the **same topic** reports an external score.
  If that score regressed past `EXTERNAL_REGRESSION_TOLERANCE` (3 points), the
  patches are reverted.
- **Objective**: `improvement_score` is the external-score delta (or `None` when
  no comparable score exists) — never `applied / total`.
- **Goal-post protection**: `_is_forbidden_path` blocks any patch under `eval/`
  and to the scoring/novelty modules, beyond `FORBIDDEN_FILES`.

## Limitations

- `novelty_vs_heldout` is only as good as the corpus you populate.
- The judge reduces self-preference bias by using a disjoint family, but does
  not eliminate bias; it is opt-in.
- `score_consistency` is a bounded audit (reported vs. dimension ceiling); it
  flags inflation, it does not prove correctness.
- "External" is a policy you enforce. If anything lets the agent write into
  `eval/`, the guarantee is gone.
