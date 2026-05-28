"""
RUMI Space Discovery — Full 12-Phase Pipeline (Groq-first)
"""
import json, sys, time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from discovery.llm_client import call_thinking, is_available, get_status

TOPIC = "Phosphine (PH3) detection in Venus atmosphere: biosignature vs geological origin"

status = get_status()
print("=" * 70)
print("  RUMI SCIENTIST AI — SPACE DISCOVERY")
print("=" * 70)
print(f"  Topic: {TOPIC}")
print(f"  Provider: {status['primary'].upper()}")
print(f"  Groq={status['groq']['available']} | Gemini={status['gemini']['available']}")
print("=" * 70)
print()

PROMPT = f"""You are RUMI — Research & Unified Machine Intelligence, an autonomous cognitive AI for scientific research.

Run your FULL 12-PHASE SCIENTIST AI PIPELINE on this space/astronomy topic:

"{TOPIC}"

Be specific, cite real papers, propose testable ideas. Focus on REAL science.

PHASE 1 -- Literature Review: Current state of phosphine detection on Venus. Greaves et al. 2020, Villanueva et al. 2021, follow-up observations, EnVision and DAVINCI missions.

PHASE 2 -- Knowledge Graph: Map key entities (PH3, Venus, H2SO4 clouds, ALMA, JWST, DAVINCI, EnVision, SO2, volcanic sources, UV photochemistry) and relationships. Identify gaps.

PHASE 3 -- Novelty Assessment: What remains genuinely unresolved?

PHASE 4 -- Hypothesis Generation: 3 specific, testable, falsifiable hypotheses about PH3 origin on Venus. At least one non-obvious.

PHASE 5 -- Experiment Design: Observational/simulation experiments. Instruments (ALMA, JWST MIRI, DAVINCI probe), wavelengths, sensitivity requirements.

PHASE 6 -- Active Experiment Selection: Which hypothesis to test first?

PHASE 7 -- Execution Protocol: Definitive detection/non-detection campaign.

PHASE 8 -- Analysis Plan: Distinguish geological vs biological PH3 using spectral signatures, isotopic ratios, altitude profiling.

PHASE 9 -- Expected Results: Quantitative predictions for each hypothesis.

PHASE 10 -- Paper Generation: Full abstract + key findings for Nature Astronomy.

PHASE 11 -- Peer Review: Brutal self-critique. What would reviewers flag?

PHASE 12 -- Knowledge Update: Most likely explanation based on all evidence? Confidence level? What single observation would change your mind?
"""

print("[RUNNING] 12-phase pipeline on Groq llama-3.3-70b...")
print()

t0 = time.time()
result = call_thinking(PROMPT, max_tokens=32768, temperature=0.7)
elapsed = time.time() - t0

if not result:
    print("[ERROR] LLM call failed.")
    sys.exit(1)

result = result.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

print("=" * 70)
print(f"  COMPLETE — {elapsed:.1f}s")
print("=" * 70)
print()
print(result)

out = BASE / "data" / "space_discovery_groq.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    f"# RUMI Space Discovery — {TOPIC}\n\n"
    f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    f"Duration: {elapsed:.1f}s\n"
    f"Provider: Groq (llama-3.3-70b-versatile)\n\n---\n\n"
    + result, encoding="utf-8"
)
print(f"\nSaved to: {out}")
