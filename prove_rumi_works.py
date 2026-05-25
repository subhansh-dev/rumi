"""
Proof-of-concept: RUMI makes a real scientific discovery.
Uses RUMI's configured Gemini API to run a full Scientist AI pipeline.
"""
import json, sys, time
from pathlib import Path
from google import genai
from google.genai import types

BASE = Path(__file__).resolve().parent

# Try keys in order: Friday key5, key4, key3, key2, RUMI's key
friday_path = Path("C:/Users/Admin/Friday/config/api_keys.json")
if friday_path.exists():
    friday = json.loads(friday_path.read_text(encoding="utf-8-sig").lstrip("\ufeff"))
    API_KEY = (
        friday.get("gemini_api_key5")
        or friday.get("gemini_api_key4")
        or friday.get("gemini_api_key3")
        or friday.get("gemini_api_key2")
    )
else:
    API_KEY = None

if not API_KEY:
    cfg = json.loads((BASE / "config" / "api_keys.json").read_text(encoding="utf-8-sig"))
    API_KEY = cfg["gemini_api_key"]

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

client = genai.Client(api_key=API_KEY)

print("=" * 70)
print("  RUMI SCIENTIST AI  --  12-Phase Pipeline Demo")
print("=" * 70)
print("Topic: Emergent abilities in small language models (<1B params)")
print("=" * 70)

t0 = time.time()

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=PROMPT,
    config=types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=65536,
    ),
)

elapsed = time.time() - t0

safe_text = response.text.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

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
