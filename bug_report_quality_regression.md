# BUG REPORT: RUMI Discovery Quality Regression — 84/100 → 50/100

## Summary
Every RUMI discovery run before June 4 scored 78-84/100 consistently. After commit 9a13722
("feat: 13 discovery features + 16-phase pipeline"), scores dropped to 35-62/100. Four root
causes identified. All are in `discovery/discovery_pipeline_v2.py`.

## Severity: CRITICAL — single commit broke all discovery output quality

## Affected File
`discovery/discovery_pipeline_v2.py`

---

## ROOT CAUSE #1 (KILLER) — json_mode changed from True to False

### The Problem
The `_truncated_llm()` wrapper now calls the LLM with `json_mode=False`, which means
the API returns freeform markdown text instead of structured JSON. Every downstream module
then fails to parse the response.

### Old Code (commit e9d6a84, line ~438):
```python
def _truncated_llm(prompt, max_tokens=4096, **kwargs):
    ...
    r = call_json(prompt, max_tokens=max_tokens, provider="auto")
```
`call_json` = `call(prompt, json_mode=True, ...)` → **API returns structured JSON**

### Current Code (commit 9a13722, lines 791/798/813):
```python
def _truncated_llm(prompt, max_tokens=4096, **kwargs):
    ...
    r = llm_call(prompt, json_mode=False, max_tokens=max_tokens, provider=provider)
```
`llm_call` = `call` with `json_mode=False` → **API returns freeform text**

### Evidence from logs
Every run now shows:
```
[WARN] hidden_variables: JSON extraction failed (10205 chars)
[WARN] LLM batch: JSON extraction failed (15736 chars)
[WARN] creative batch: JSON extraction failed (16028 chars)
```
The retry logic sometimes recovers, but often the LLM returns markdown prose that
`json_extract.py` cannot parse, especially with nested JSON objects.

### Fix
In `_truncated_llm()` (line 782), change ALL three `llm_call` invocations from
`json_mode=False` to `json_mode=True`:

Line 791:
```python
# BEFORE:
r = llm_call(prompt, json_mode=False, max_tokens=max_tokens, provider=provider)
# AFTER:
r = llm_call(prompt, json_mode=True, max_tokens=max_tokens, provider=provider)
```

Line 798:
```python
# BEFORE:
r = llm_call(prompt, json_mode=False, max_tokens=max_tokens, provider="auto")
# AFTER:
r = llm_call(prompt, json_mode=True, max_tokens=max_tokens, provider="auto")
```

Line 813:
```python
# BEFORE:
r = llm_call(prompt, json_mode=False, max_tokens=max_tokens, provider="auto")
# AFTER:
r = llm_call(prompt, json_mode=True, max_tokens=max_tokens, provider="auto")
```

---

## ROOT CAUSE #2 — Graph persistence pollutes all runs with stale data

### The Problem
Line 217 changed from `persist=False` to `persist=True`:
```python
graph = KnowledgeGraph(persist=True)  # Load previous graph
```

This means every run loads ALL entities from ALL previous runs. A cosmology run loads
entities from TRAPPIST-1, primordial black holes, CRISPR, etc. The pruning logic (lines
235-253) only removes entities with ≤1 paper reference and caps at 200 per run — not
enough when the graph has 1000+ stale entities.

### Impact
- Gap detection finds irrelevant gaps from unrelated topics
- Anomaly detection finds irrelevant anomalies
- Mechanism generation references entities from wrong domains
- Prompt context is filled with irrelevant entity/relationship data

### Fix
Option A: Revert to `persist=False` (simplest, matches the 78-84 scoring era)
```python
graph = KnowledgeGraph(persist=False)
```

Option B: More aggressive pruning — remove entities NOT referenced by current run's papers:
```python
# After building graph from current papers, prune everything not referenced
current_paper_ids = set(p.get("id", "") for p in papers)
for eid in list(graph.entities.keys()):
    ent = graph.entities[eid]
    ent_papers = set(ent.get("papers", []))
    if not (ent_papers & current_paper_ids):
        del graph.entities[eid]
```

---

## ROOT CAUSE #3 — Archive context bloats prompts past truncation limit

### The Problem
New code (lines 279-333) injects into every prompt:
1. Discovery archive from past runs (~500-1000 chars)
2. 20+ prior hypotheses from HypothesisMemory (~1500-2500 chars)
3. Domain-specific research templates (~500-1000 chars)

Total: ~2500-4500 chars of extra context per prompt.

Combined with the 8000-char truncation limit (line 784):
```python
if len(prompt) > 8000:
    prompt = prompt[:7500] + "\n\n[Context truncated]"
```

The actual topic-specific content (gaps, anomalies, entities, papers) gets truncated
to make room for archive context. The LLM sees stale prior hypotheses instead of
current research context.

### Evidence
The MissingVariableGenerator prompt includes gaps, anomalies, graph context, papers,
AND archive context. With 25 gaps + 11 anomalies + 162 entities + 86 papers + archive,
the prompt easily exceeds 8000 chars. The truncation cuts the most important part
(the current topic context) while preserving the archive prefix.

### Fix
Option A: Remove archive context injection entirely (simplest)
```python
# Comment out or remove lines 279-333
```

Option B: Move archive context to the END of prompts (gets truncated first)
```python
# Instead of inserting archive_context in the middle of prompts,
# append it at the very end so the 8000-char truncation cuts it first
```

Option C: Filter archive by topic similarity (not just domain)
```python
# Only include prior hypotheses with >0.7 topic similarity, not 0.3
topic_similar = hyp_mem.find_similar(topic, threshold=0.7)
```

---

## ROOT CAUSE #4 — Phase-specific LLM routing sends creative work to fast models

### The Problem
Lines 759-775 route phases to specific providers:
```python
PHASE_PROVIDERS = {
    "missing_variables": "cerebras",     # CREATIVE phase → fast/cheap model
    "mechanism_generation": "cerebras",  # CREATIVE phase → fast/cheap model
    "theory_competition": "groq",        # CREATIVE phase → fast/cheap model
    ...
}
```

The old code used `provider="auto"` for everything, which tried Cerebras first but
fell back to Gemini (better reasoning) when Cerebras failed or produced poor output.
The new routing LOCKS creative phases to Cerebras/Groq, which are faster but produce
less rigorous scientific output (no equations, no derivations, weaker reasoning).

### Evidence
CRISPR run (before routing change): Hidden variables had Boltzmann, Stokes-Einstein,
Michaelis-Menten derivations. Score: 84/100.

Current runs: Hidden variables are simple floats with no derivations. Score: 50-62/100.

### Fix
Route creative phases to `auto` (lets the system pick the best available model):
```python
PHASE_PROVIDERS = {
    # Extraction phases — fast models OK
    "literature": "groq",
    "knowledge_graph": "groq",
    "gap_detection": "groq",
    "anomaly_detection": "groq",
    "prediction_engine": "groq",
    "adversarial_test": "groq",
    "scoring": "groq",
    # Creative/reasoning phases — let auto-routing pick best available
    "missing_variables": "auto",
    "mechanism_generation": "auto",
    "theory_competition": "auto",
    "critical_evaluation": "auto",
    "skeptic_review": "auto",
}
```

---

## Fix Priority Order
1. **json_mode** (Root Cause #1) — 3 line changes, immediate impact
2. **Graph persistence** (Root Cause #2) — 1 line change (persist=False)
3. **Archive context** (Root Cause #3) — comment out lines 279-333
4. **Phase routing** (Root Cause #4) — change creative phases to "auto"

## Expected Impact
After all 4 fixes: scores should return to 78-84/100 range (matching pre-June-4 baseline).

## Testing
After applying fixes, run:
```bash
python run_discovery.py "CRISPR gene editing off-target effects" --domain drug_discovery --mode full
```
Expected score: 78-84/100. If below 70, something else is wrong.

## Context
- Pre-June-4 pipeline (e9d6a84): consistent 78-84/100 across all topics
- Post-June-4 pipeline (9a13722): 35-62/100 across all topics
- Engine priority revert (done) helped slightly but didn't fix the core issues
- The 4 root causes above are ADDITIVE — each one degrades quality independently
