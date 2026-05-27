"""
RUMI Grounded Discovery — Full pipeline with real citations,
computational modeling, and claim labeling.

This is how RUMI should run: grounded, not hallucinating.
"""
import json
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from discovery.llm_client import call_thinking, is_available, get_status
from discovery.citation_grounding import fetch_papers, build_citation_context, ground_claims
from discovery.computational import run_all_calculations, format_calculations_for_prompt
from discovery.claim_labeler import label_report, generate_confidence_summary, add_report_header


def run_grounded_discovery(topic: str, domain: str = "space_astronomy"):
    """
    Run a full grounded discovery pipeline:
    1. Fetch real papers from arXiv + PubMed
    2. Run computational models
    3. Build grounded prompt with real data
    4. Generate report via LLM
    5. Label every claim
    6. Add transparency header
    """
    status = get_status()
    print("=" * 70)
    print("  RUMI — GROUNDED SCIENTIFIC DISCOVERY")
    print("=" * 70)
    print(f"  Topic: {topic}")
    print(f"  Provider: {status['primary'].upper()}")
    print("=" * 70)

    # ── PHASE 1: Fetch real papers ──
    print("\n[1/5] Fetching real papers from arXiv + PubMed...")
    papers = fetch_papers(topic, max_arxiv=8, max_pubmed=8)
    print(f"  Found {len(papers)} papers")
    for p in papers[:5]:
        print(f"    [{p['source']}] {p['citation_key']} — {p['title'][:80]}")

    citation_context = build_citation_context(papers)

    # ── PHASE 2: Run computations ──
    print("\n[2/5] Running computational models...")
    calculations = run_all_calculations(topic)
    calc_context = format_calculations_for_prompt(calculations)
    print(f"  Ran {len(calculations)} calculations")

    # ── PHASE 3: Build grounded prompt ──
    print("\n[3/5] Building grounded prompt...")
    prompt = _build_grounded_prompt(topic, domain, citation_context, calc_context)

    # ── PHASE 4: Generate via LLM ──
    print("\n[4/5] Generating 12-phase report via LLM...")
    t0 = time.time()
    raw_output = call_thinking(prompt, max_tokens=32768, temperature=0.7)
    elapsed = time.time() - t0

    if not raw_output:
        print("[ERROR] LLM call failed.")
        return None

    raw_output = raw_output.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    print(f"  Generated in {elapsed:.1f}s ({len(raw_output)} chars)")

    # ── PHASE 5: Label claims ──
    print("\n[5/5] Labeling claims...")
    labeled_output = label_report(raw_output, papers, calculations)

    # Ground citations
    grounding = ground_claims(raw_output, papers)
    print(f"  Citations found: {grounding['total_citations']}")
    print(f"  Uncited factual claims: {len(grounding['uncited_claims'])}")
    print(f"  Grounding score: {grounding['grounding_score']:.2f}")

    # Generate confidence summary
    confidence = generate_confidence_summary(labeled_output)
    print(f"  Reliability score: {confidence.get('reliability_score', 0):.0%}")

    # Build transparency header
    header = add_report_header(
        papers_count=len(papers),
        calc_count=len(calculations),
        confidence_summary=confidence,
    )

    # ── Assemble final report ──
    full_report = header + labeled_output

    # Add references section
    if papers:
        full_report += "\n\n" + "=" * 70 + "\n  REFERENCES (Real papers fetched)\n" + "=" * 70 + "\n\n"
        for i, p in enumerate(papers, 1):
            authors = ", ".join(p.get("authors", [])[:3])
            if len(p.get("authors", [])) > 3:
                authors += " et al."
            full_report += f"  [{i}] {p['citation_key']} ({p.get('year', 'n/a')})\n"
            full_report += f"      {p['title']}\n"
            full_report += f"      {authors}\n"
            full_report += f"      {p['url']}\n\n"

    # Add computation details
    if calculations:
        full_report += "\n" + "=" * 70 + "\n  COMPUTATIONAL DETAILS\n" + "=" * 70 + "\n\n"
        full_report += json.dumps(calculations, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 70)
    print(f"  COMPLETE — {elapsed:.1f}s")
    print("=" * 70)
    print(f"  Papers cited: {grounding['total_citations']}/{len(papers)}")
    print(f"  Claims: {confidence.get('breakdown', {})}")
    print(f"  Reliability: {confidence.get('reliability_score', 0):.0%}")
    print(f"  {confidence.get('interpretation', '')}")
    print("=" * 70)

    return full_report


def _build_grounded_prompt(topic: str, domain: str,
                           citation_context: str, calc_context: str) -> str:
    """Build a prompt that forces the LLM to use real sources and numbers."""

    return f"""You are RUMI — Research & Unified Machine Intelligence.

Run a 12-phase scientific analysis on: "{topic}"

CRITICAL RULES:
1. CITE REAL PAPERS using [1], [2], etc. from the paper list below.
2. USE REAL NUMBERS from the computational results below.
3. When no paper supports a claim, mark it [UNVERIFIED].
4. When making a prediction, mark it [HYPOTHETICAL].
5. Never invent paper titles, authors, or numerical values.
6. Every number must trace to a computational result or a cited paper.

{citation_context}

{calc_context}

PHASE 1 -- Literature Review: What do the papers above actually say? Cite each claim.

PHASE 2 -- Knowledge Graph: Map entities from the papers. Identify gaps in the literature.

PHASE 3 -- Novelty Assessment: What do the papers NOT cover? What's genuinely unresolved?

PHASE 4 -- Hypothesis Generation: Propose hypotheses grounded in the cited literature.

PHASE 5 -- Experiment Design: Use the computational results (spectral lines, JWST sensitivity, etc.) to design realistic experiments.

PHASE 6 -- Active Experiment Selection: Which experiment is most feasible given the computed constraints?

PHASE 7 -- Execution Protocol: Use real instrument specs and computed detection thresholds.

PHASE 8 -- Analysis Plan: How would you distinguish hypotheses using the computed Bayesian posteriors?

PHASE 9 -- Expected Results: Use the Monte Carlo uncertainty ranges for predictions. State the confidence interval.

PHASE 10 -- Paper Generation: Write an abstract grounded in the cited papers and computed values.

PHASE 11 -- Peer Review: What are the weaknesses of this analysis? What assumptions are weakest?

PHASE 12 -- Knowledge Update: What does the evidence actually support? Give Bayesian posterior probabilities.
"""


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RUMI Grounded Discovery")
    parser.add_argument("--topic", default="Phosphine (PH3) detection in Venus atmosphere: biosignature vs geological origin")
    parser.add_argument("--domain", default="space_astronomy")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    report = run_grounded_discovery(args.topic, args.domain)

    if report:
        # Print to console
        print("\n\n" + report)

        # Save
        out_path = args.output or str(BASE / "data" / "grounded_discovery_report.md")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(report, encoding="utf-8")
        print(f"\n\nSaved to: {out_path}")
