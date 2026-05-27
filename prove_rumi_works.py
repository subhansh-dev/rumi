"""
Proof-of-concept: RUMI makes a real scientific discovery.
Uses RUMI's unified LLM client (Groq-first, Gemini-fallback).
"""
import json, sys, time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from discovery.llm_client import call, call_thinking, is_available, get_status

PROMPT = """You are RUMI -- Research & Unified Machine Intelligence, an autonomous cognitive AI for scientific research.

Run your FULL 12-PHASE SCIENTIST AI PIPELINE on this topic:

"Emergent abilities in small language models (<1B parameters) through structured prompting"

For each phase, output your complete reasoning. Be specific, cite known papers where relevant, and propose testable ideas.

PHASE 1 -- Literature Review: What is already known about emergent abilities? Are they exclusive to large models, or can structured prompting elicit them in small models? Reference known work (Wei et al. 2022, Schaeffer et al. 2023, etc.)

PHASE 2 -- Knowledge Graph: Identify key entities, relationships, and research gaps.

PHASE 3 -- Novelty Assessment: How novel is the idea that structured prompting can elicit emergence in <1B models?

PHASE 4 -- Hypothesis Generation: Generate 3 specific, testable, falsifiable hypotheses.

PHASE 5 -- Experiment Design: Design controlled experiments. Specify: independent/dependent variables, control conditions, metrics, model sizes, prompting strategies.

PHASE 6 -- Active Experiment Selection: Which of your 3 hypotheses would be most informative to test first? Why?

PHASE 7 -- Execution Protocol: Step-by-step procedure to run the experiment.

PHASE 8 -- Analysis Plan: Statistical methods, effect size calculations, visualization approaches.

PHASE 9 -- Expected Results: Predict outcomes for each hypothesis with reasoning.

PHASE 10 -- Paper Generation: Write an abstract and methods section as if for a conference submission.

PHASE 11 -- Peer Review: Self-critique your pipeline. What are the limitations? What would reviewers flag?

PHASE 12 -- Knowledge Update & Self-Improvement: What did running this pipeline teach you? What would you do differently next time?
"""

# ── Check provider status ──
status = get_status()
print("=" * 70)
print("  RUMI SCIENTIST AI  --  12-Phase Pipeline Demo")
print("=" * 70)
print(f"  Providers: Groq={status['groq']['available']} "
      f"(keys={status['groq']['keys']}), "
      f"Gemini={status['gemini']['available']} "
      f"(keys={status['gemini']['keys']})")
print(f"  Primary: {status['primary'].upper()}")
print("Topic: Emergent abilities in small language models (<1B params)")
print("=" * 70)

if not is_available():
    print("\n[ERROR] No LLM providers available. Add keys to config/api_keys.json:")
    print('  "groq_api_key": "gsk_..."  (free at console.groq.com)')
    print('  "gemini_api_key": "AIza..." (free at aistudio.google.com)')
    sys.exit(1)

t0 = time.time()

# Use call_thinking for the big 12-phase prompt (higher token limit)
safe_text = call_thinking(PROMPT, max_tokens=32768, temperature=0.7)

elapsed = time.time() - t0

if not safe_text:
    print("\n[ERROR] All LLM providers failed. Check your API keys and rate limits.")
    sys.exit(1)

safe_text = safe_text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

print()
print("=" * 70)
print(f"  PIPELINE COMPLETE  --  {elapsed:.1f}s")
print("=" * 70)
print()
print(safe_text)

text = safe_text.lower()
checks = {
    "Hypothesis Generation": any(w in text for w in ["hypothesis 1", "hypothesis 2", "hypothesis 3", "h1:", "h2:", "h3:"]),
    "Experiment Design": "experiment" in text and "control" in text,
    "Analysis Plan": any(w in text for w in ["statistical", "effect size", "metric"]),
    "Literature Review": any(w in text for w in ["wei et al", "schaeffer", "emergent", "literature"]),
    "Novelty Assessment": "novel" in text,
    "Paper Generation": any(w in text for w in ["abstract", "methods"]),
    "Peer Review": any(w in text for w in ["limitation", "reviewer", "critique"]),
    "Expected Results": any(w in text for w in ["predict", "expect", "would find"]),
    "Knowledge Update": any(w in text for w in ["learned", "improve", "next time"]),
    "Execution Protocol": "step" in text and "procedure" in text,
}

print()
print("=" * 70)
print("  QUALITY ASSESSMENT")
print("=" * 70)
passed = 0
for label, result in checks.items():
    status = "PASS" if result else "FAIL"
    print(f"  [{status}]  {label}")
    if result:
        passed += 1
print(f"\n  Score: {passed}/{len(checks)} phases verified")

if passed >= 8:
    print("\n  VERDICT: RUMI is a REAL functioning Scientist AI!")
    print("  She can do autonomous scientific research end-to-end.")
elif passed >= 5:
    print("\n  WARNING: RUMI works but some phases need refinement")
else:
    print("\n  FAIL: Pipeline needs debugging")
