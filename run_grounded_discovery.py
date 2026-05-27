"""
RUMI Grounded Discovery — Full pipeline with domain-aware
real citations, computational modeling, and claim labeling.

Supports all 15 RUMI domains with domain-specific calculations.
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
from discovery.domain_computational import run_domain_calculations, format_for_prompt, DOMAIN_COMPUTATIONS
from discovery.claim_labeler import label_report, generate_confidence_summary, add_report_header


# ── Domain detection from topic keywords ──
DOMAIN_KEYWORDS = {
    "space_astronomy": ["phosphine", "venus", "exoplanet", "mars", "jupiter", "black hole",
                        "neutron star", "pulsar", "galaxy", "telescope", "nasa", "jwst",
                        "spectral", "atmosphere", "biosignature", "cosmolog"],
    "neuroscience": ["neuron", "brain", "neurotransmitter", "dopamine", "serotonin",
                     "synaptic", "cortex", "hippocampus", "consciousness", "fmri",
                     "receptor signaling", "neural circuit", "action potential"],
    "drug_discovery": ["drug", "inhibitor", "kinase", "antibiotic", "cancer", "pharma",
                       "therapeutic", "binding affinity", "clinical trial", "ic50", "ec50"],
    "materials_science": ["perovskite", "battery", "catalyst", "bandgap", "nanomaterial",
                          "graphene", "2d material", "solar cell", "semiconductor", "alloy"],
    "climate_energy": ["climate", "carbon", "emission", "renewable", "solar", "wind",
                       "greenhouse", "warming", "co2", "temperature"],
    "ecology": ["species", "biodiversity", "ecosystem", "conservation", "habitat",
                "extinction", "population", "invasion", "endangered"],
    "physics": ["quantum", "particle", "higgs", "gravity", "wave", "boson",
                "fermion", "relativity", "dark matter", "entanglement"],
    "computer_science": ["neural network", "llm", "transformer", "algorithm", "machine learning",
                         "deep learning", "dataset", "benchmark", "architecture"],
    "public_health": ["vaccine", "pandemic", "epidemic", "disease", "mortality",
                      "prevalence", "intervention", "clinical", "public health"],
    "chemistry": ["reaction", "synthesis", "catalysis", "compound", "organic",
                  "inorganic", "analytical", "spectroscopy", "electrochemistry"],
    "mathematics": ["theorem", "proof", "conjecture", "prime", "topology",
                    "optimization", "sequence", "algebra", "geometry"],
}


def detect_domain(topic: str) -> str:
    """Auto-detect domain from topic text."""
    topic_lower = topic.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in topic_lower)
        if score > 0:
            scores[domain] = score
    if scores:
        return max(scores, key=scores.get)
    return "general"


def run_grounded_discovery(topic: str, domain: str = ""):
    """
    Full grounded discovery pipeline with domain awareness.
    """
    if not domain:
        domain = detect_domain(topic)

    status = get_status()
    print("=" * 70)
    print("  RUMI — GROUNDED SCIENTIFIC DISCOVERY")
    print("=" * 70)
    print(f"  Topic: {topic}")
    print(f"  Domain: {domain}")
    print(f"  Provider: {status['primary'].upper()}")
    print(f"  Domain-specific calculations: {domain in DOMAIN_COMPUTATIONS or domain == 'space_astronomy'}")
    print("=" * 70)

    # ── PHASE 1: Fetch real papers ──
    print("\n[1/5] Fetching real papers from arXiv + PubMed...")
    papers = fetch_papers(topic, max_arxiv=5, max_pubmed=5)
    print(f"  Found {len(papers)} papers")
    for p in papers[:3]:
        print(f"    [{p['source']}] {p['citation_key']} — {p['title'][:70]}")
    citation_context = build_citation_context(papers)

    # ── PHASE 2: Run computations ──
    print("\n[2/5] Running computations...")
    calculations = {}

    # Domain-specific calculations
    if domain in DOMAIN_COMPUTATIONS or domain == "space_astronomy":
        print(f"  Domain: {domain}")
        domain_calcs = run_domain_calculations(domain, topic)
        calculations.update(domain_calcs)
        print(f"  {len(domain_calcs)} domain-specific calculations")

    # Generic Bayesian scoring (always)
    from discovery.computational import score_venus_ph3_hypotheses, monte_carlo_ph3_lifetime
    if domain == "space_astronomy":
        space_calcs = run_all_calculations(topic)
        calculations.update(space_calcs)

    print(f"  Total: {len(calculations)} calculations")
    calc_context = format_for_prompt(calculations) or format_calculations_for_prompt(calculations)

    # ── PHASE 3: Build grounded prompt ──
    print("\n[3/5] Building grounded prompt...")
    prompt = _build_prompt(topic, domain, citation_context, calc_context)

    # ── PHASE 4: Generate via LLM ──
    print("\n[4/5] Generating report via LLM...")
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
    grounding = ground_claims(raw_output, papers)
    confidence = generate_confidence_summary(labeled_output)
    header = add_report_header(len(papers), len(calculations), confidence)

    # Assemble
    full_report = header + labeled_output

    if papers:
        full_report += "\n\n" + "=" * 70 + "\n  REFERENCES (Real papers)\n" + "=" * 70 + "\n\n"
        for i, p in enumerate(papers, 1):
            authors = ", ".join(p.get("authors", [])[:3])
            if len(p.get("authors", [])) > 3:
                authors += " et al."
            full_report += f"  [{i}] {p['citation_key']} ({p.get('year', 'n/a')})\n"
            full_report += f"      {p['title']}\n      {authors}\n      {p['url']}\n\n"

    if calculations:
        full_report += "\n" + "=" * 70 + "\n  COMPUTATIONAL DETAILS\n" + "=" * 70 + "\n\n"
        full_report += json.dumps(calculations, indent=2, default=str)

    print("\n" + "=" * 70)
    print(f"  COMPLETE — {elapsed:.1f}s")
    print(f"  Reliability: {confidence.get('reliability_score', 0):.0%}")
    print(f"  Claims: {confidence.get('breakdown', {})}")
    print(f"  Citations: {grounding['total_citations']}/{len(papers)}")
    print("=" * 70)

    return full_report


def _build_prompt(topic, domain, citation_context, calc_context):
    """Build domain-aware grounded prompt."""
    domain_instructions = {
        "drug_discovery": "Focus on molecular mechanisms, binding affinities, Lipinski rules, clinical trial design.",
        "materials_science": "Focus on bandgap, formation energy, synthesis routes, characterization methods.",
        "neuroscience": "Focus on neural circuits, receptor pharmacology, electrophysiology, imaging methods.",
        "climate_energy": "Focus on radiative forcing, emission scenarios, policy effectiveness, energy metrics.",
        "ecology": "Focus on population dynamics, biodiversity indices, conservation genetics, ecosystem services.",
        "physics": "Focus on theoretical predictions, experimental verification, fundamental constants.",
        "computer_science": "Focus on algorithm complexity, benchmark results, scaling laws, architecture design.",
        "public_health": "Focus on epidemiological measures (RR, OR, NNT), study design, intervention effectiveness.",
        "chemistry": "Focus on reaction mechanisms, thermodynamics, kinetics, analytical methods.",
        "mathematics": "Focus on theorems, proofs, convergence rates, computational complexity.",
        "space_astronomy": "Focus on atmospheric chemistry, spectroscopy, mission design, habitability.",
    }

    domain_note = domain_instructions.get(domain, "General scientific analysis.")

    return f"""You are RUMI — Research & Unified Machine Intelligence.

Run a 12-phase analysis on: "{topic}"
Domain: {domain}

CRITICAL RULES:
1. Cite papers using [1], [2], etc. from the list below.
2. Use real numbers from the computational results below.
3. Mark unsourced claims as [UNVERIFIED].
4. Mark predictions as [HYPOTHETICAL].
5. Never invent paper titles, authors, or numerical values.
6. Every number must trace to a computation or citation.
7. {domain_note}

{citation_context}

{calc_context}

PHASE 1 -- Literature Review (cite real papers)
PHASE 2 -- Knowledge Graph (entities from papers)
PHASE 3 -- Novelty Assessment (gaps in literature)
PHASE 4 -- Hypothesis Generation (grounded in citations)
PHASE 5 -- Experiment Design (use computed values)
PHASE 6 -- Active Experiment Selection (feasibility)
PHASE 7 -- Execution Protocol (real specs)
PHASE 8 -- Analysis Plan (statistical methods)
PHASE 9 -- Expected Results (use computed ranges + confidence intervals)
PHASE 10 -- Paper Abstract (grounded in citations + computed values)
PHASE 11 -- Peer Review (weakest assumptions)
PHASE 12 -- Knowledge Update (evidence-based conclusion)
"""


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RUMI Grounded Discovery")
    parser.add_argument("--topic", default="Phosphine (PH3) detection in Venus atmosphere")
    parser.add_argument("--domain", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    report = run_grounded_discovery(args.topic, args.domain)
    if report:
        print("\n\n" + report[:3000] + "\n\n... [truncated for console] ...")
        out_path = args.output or str(BASE / "data" / "grounded_discovery_report.md")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(report, encoding="utf-8")
        print(f"\nSaved to: {out_path}")
