# BUG REPORT: MissingVariableGenerator JSON Extraction Failure

## Summary
MissingVariableGenerator's LLM returns prose/markdown instead of JSON in ~30% of runs.
json_extract.py's regex fallback fails to extract nested JSON, causing the entire phase to
produce 0 hidden variables. This cascades: empty hidden variables → empty mechanisms →
empty predictions → low score (35/100 instead of 84/100).

## Severity: HIGH — single point of failure that degrades entire pipeline output

## Reproduction
- Run: `python run_discovery.py "dark energy expansion of the universe and the cosmological constant problem" --domain cosmology --mode full`
- Log file: `rumi_space2.log`
- Debug output: `[WARN] hidden_variables: JSON extraction failed (11767 chars)`
- First 500 chars of LLM output (from log):
```
**Hidden‑Variable Discovery Report**  
*Topic:* Dark‑energy driven expansion & the cosmological‑constant (Λ) problem  
*Domain:* Cosmology (knowledge‑graph of 194 entities, 1 714 relationships)

---

## 1. What Gaps & Anomalies Need Explanation?

| # | Type | Description (graph‑level) | Why it matters for Λ / Dark‑Energy |
|---|------|----------------------------|------------------------------------|
| 1 | **Orphan Observation** | The term **"puzzle"** appears in a single paper but has **zero ...
```
- The LLM returned a full markdown report with tables, headers, and sections — NOT JSON.

## Expected Behavior
extract_json() should handle prose-wrapped JSON or the prompt should force JSON-only output.

## Root Cause Analysis

### Problem 1: _regex_extract_json pattern fails on nested JSON
Location: `discovery/json_extract.py` line 104

```python
pattern = r'\{[^{}]*"' + re.escape(expected_key) + r'"\s*:\s*\[[\s\S]*?\]\s*\}'
```

This pattern uses `[^{}]*` which means "any chars except { or }". But the expected output
is `{"hidden_variables": [{...}, {...}]}` — the inner objects contain `{` and `}` which
breaks the pattern. It will NEVER match nested JSON objects.

Fix: Use a balanced brace matching approach or a recursive regex:
```python
# Instead of [^{}]*, use a pattern that handles one level of nesting
pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*"' + re.escape(expected_key) + r'"\s*:\s*\[.*?\]\s*\}'
```

Or better: use a brace-counting parser instead of regex for nested JSON extraction.

### Problem 2: Line 114 greedy regex is too aggressive
```python
matches = list(re.finditer(r'\{[\s\S]{30,}?\}', text))
```

This non-greedy `{30,}?` with `[\s\S]` matches from the FIRST `{` to the FIRST `}`,
which for nested JSON means it matches `{**Hidden‑Variable...}` (the markdown bold syntax
contains `{` and `}` characters from the LLM's formatting). It should use balanced brace
counting instead.

### Problem 3: No prompt enforcement for JSON-only output
Location: `discovery/missing_variable_generator.py` lines ~100-196

The prompt says "Output JSON:" followed by the schema, but doesn't explicitly say
"OUTPUT ONLY VALID JSON. NO PROSE, NO MARKDOWN, NO EXPLANATION." Some LLMs (especially
Cerebras/Groq models used by RUMI) will produce markdown reports when the topic is complex.

Fix: Add explicit instruction at the end of the prompt:
```
CRITICAL: Output ONLY the JSON object below. No markdown, no headers, no prose, no tables.
Start your response with { and end with }. Nothing else.
```

### Problem 4: No retry on JSON extraction failure
Location: `discovery/missing_variable_generator.py` lines 212-234

When `extract_json()` returns None, the code prints a warning and falls through to return
empty results. It should retry with a stronger "JSON only" prompt before giving up.

Fix:
```python
if result is None:
    # Retry with explicit JSON-only instruction
    retry_prompt = prompt + "\n\nCRITICAL: You returned markdown last time. Return ONLY valid JSON. No markdown. Start with { end with }."
    raw2 = self.llm_call(retry_prompt, max_tokens=8192)
    if raw2:
        result = extract_json(raw2, expected_key="hidden_variables")
        if result:
            print(f"    [RETRY] hidden_variables: extraction succeeded on retry", flush=True)
```

## Fix Priority Order
1. **Fix _regex_extract_json** (Problem 1+2) — this is the immediate blocker
2. **Add retry logic** (Problem 4) — cheap safety net
3. **Strengthen prompt** (Problem 3) — prevents the issue from occurring

## Impact
- Before fix: MissingVariableGenerator fails → HypothesisEngine fallback → empty `[?] ?`
- After fix: MissingVariableGenerator succeeds → real hidden variables with derivations
- Expected score improvement: 35/100 → 80+/100 (based on CRISPR run comparison)

## Files to Modify
- `discovery/json_extract.py` — fix _regex_extract_json (lines 100-120)
- `discovery/missing_variable_generator.py` — add retry logic (lines 212-234), strengthen prompt (lines 100-196)

## Context
- RUMI uses Cerebras as primary LLM (~2s response), Gemini + Groq as fallback
- Cerebras models tend to produce markdown-formatted responses for complex scientific topics
- The CRISPR run succeeded because Cerebras happened to return JSON that time
- This is a probabilistic failure — ~30% of runs hit it depending on topic complexity
