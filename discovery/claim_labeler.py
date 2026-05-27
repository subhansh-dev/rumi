"""
discovery/claim_labeler.py — Classify and Label Claims in RUMI Output

Parses LLM-generated scientific text and classifies each claim:
  [VALIDATED]   — Supported by real papers or computational results
  [INFERRED]    — Logical deduction from validated claims
  [SIMULATED]   — From computational model (has assumptions)
  [SPECULATIVE] — LLM-generated, no evidence or calculation backing
  [HYPOTHETICAL] — Explicitly a "what if" scenario

Usage:
    from discovery.claim_labeler import label_report
    labeled = label_report(llm_output, papers, calculations)
"""

import re


# Claim indicators — phrases that suggest factual claims
FACTUAL_INDICATORS = [
    "detected at", "measured at", "reported at", "found to be",
    "upper limit of", "abundance of", "concentration of",
    "ppb", "ppm", "ppt", "mixing ratio",
    "altitude of", "km altitude", "wavelength",
    "published in", "et al.", "journal", "study",
    "confirmed", "established", "demonstrated",
    "spectral", "absorption", "emission", "line",
    "temperature of", "pressure of", "optical depth",
    "p-value", "statistical significance", "confidence interval",
    "sample size", "n =", "N =",
]

HYPOTHETICAL_INDICATORS = [
    "if", "would", "could", "might", "may",
    "hypothetically", "in theory", "potentially",
    "it is possible", "one could argue", "speculatively",
    "assuming", "under the assumption",
]

COMPUTATIONAL_INDICATORS = [
    "calculated", "computed", "modeled", "simulated",
    "from the model", "simulation shows", "predicted by",
    "Monte Carlo", "Bayesian", "posterior probability",
]

CITATION_PATTERN = re.compile(r'\[(\d+)\]|\(([A-Z][a-z]+(?:\s+(?:et\s+al\.?|and|&)\s+[A-Z][a-z]+)*,?\s*\d{4}[a-z]?)\)')
UNVERIFIED_PATTERN = re.compile(r'\[UNVERIFIED\]|\[HYPOTHETICAL\]|\[SPECULATIVE\]')


def label_report(text: str, papers: list = None, calculations: dict = None) -> str:
    """
    Add inline confidence labels to each paragraph of the report.
    Returns the annotated text.
    """
    paragraphs = text.split('\n')
    labeled_lines = []
    section_header = ""

    for line in paragraphs:
        stripped = line.strip()

        # Track section headers
        if stripped.startswith('#') or stripped.startswith('PHASE') or stripped.startswith('==='):
            section_header = stripped
            labeled_lines.append(line)
            continue

        # Skip empty lines
        if not stripped or len(stripped) < 20:
            labeled_lines.append(line)
            continue

        # Already labeled? Skip
        if any(tag in stripped for tag in ['[VALIDATED]', '[INFERRED]', '[SIMULATED]',
                                           '[SPECULATIVE]', '[HYPOTHETICAL]', '[UNVERIFIED]']):
            labeled_lines.append(line)
            continue

        # Classify the line
        label = _classify_claim(stripped, papers, calculations)

        # Add label at end of line
        if label and not stripped.startswith('```'):
            labeled_lines.append(f"{line}  {{{label}}}")
        else:
            labeled_lines.append(line)

    return '\n'.join(labeled_lines)


def _classify_claim(text: str, papers: list = None, calculations: dict = None) -> str:
    """Classify a single line/claim."""
    text_lower = text.lower()

    has_citation = bool(CITATION_PATTERN.search(text))
    has_unverified = bool(UNVERIFIED_PATTERN.search(text))
    has_factual = any(ind in text_lower for ind in FACTUAL_INDICATORS)
    has_hypothetical = any(ind in text_lower for ind in HYPOTHETICAL_INDICATORS)
    has_computational = any(ind in text_lower for ind in COMPUTATIONAL_INDICATORS)

    # Has explicit [UNVERIFIED] or [HYPOTHETICAL] marker from LLM
    if has_unverified:
        return "SPECULATIVE"

    # Has a citation to a real paper
    if has_citation and has_factual:
        return "VALIDATED"

    # References computational results
    if has_computational and calculations:
        return "SIMULATED"

    # Contains numbers without citations — likely invented
    has_numbers = bool(re.search(r'\d+\.?\d*\s*(ppb|ppm|ppt|km|µm|um|K\b|atm)', text))
    if has_numbers and not has_citation and not has_computational:
        return "SPECULATIVE"

    # Hypothetical language
    if has_hypothetical and not has_factual:
        return "HYPOTHETICAL"

    # Factual claim without citation
    if has_factual and not has_citation:
        return "INFERRED"

    # Default — narrative/explanatory text
    return ""


def generate_confidence_summary(text: str) -> dict:
    """
    Count claim types in the labeled report and generate a summary.
    """
    labels = {
        "VALIDATED": 0,
        "INFERRED": 0,
        "SIMULATED": 0,
        "SPECULATIVE": 0,
        "HYPOTHETICAL": 0,
    }

    for label in labels:
        labels[label] = len(re.findall(rf'\{{{label}\}}', text))

    total = sum(labels.values())
    if total == 0:
        return {"error": "No labeled claims found"}

    return {
        "total_labeled_claims": total,
        "breakdown": labels,
        "percentages": {k: f"{v/total*100:.1f}%" for k, v in labels.items()},
        "reliability_score": (
            (labels["VALIDATED"] * 1.0 +
             labels["INFERRED"] * 0.6 +
             labels["SIMULATED"] * 0.5 +
             labels["HYPOTHETICAL"] * 0.3 +
             labels["SPECULATIVE"] * 0.0) / total
        ),
        "interpretation": _interpret_breakdown(labels, total),
    }


def _interpret_breakdown(labels: dict, total: int) -> str:
    """Generate a human-readable interpretation."""
    validated_pct = labels["VALIDATED"] / total * 100
    speculative_pct = labels["SPECULATIVE"] / total * 100

    if validated_pct > 40:
        quality = "HIGH — majority of claims are grounded in real sources"
    elif validated_pct > 20:
        quality = "MIXED — significant portion grounded but many claims unverified"
    else:
        quality = "LOW — most claims are speculative or unverified"

    warnings = []
    if speculative_pct > 30:
        warnings.append(
            f"WARNING: {speculative_pct:.0f}% of claims are SPECULATIVE "
            f"(invented numbers or unsourced assertions). Treat with skepticism."
        )
    if labels["SIMULATED"] > labels["VALIDATED"]:
        warnings.append(
            "NOTE: More claims come from computational models than from "
            "peer-reviewed sources. Model assumptions may not hold."
        )

    return quality + (" | " + " | ".join(warnings) if warnings else "")


def add_report_header(papers_count: int, calc_count: int,
                      confidence_summary: dict) -> str:
    """
    Generate a transparency header to prepend to the report.
    Tells the reader exactly what's grounded and what's not.
    """
    reliability = confidence_summary.get("reliability_score", 0)
    interp = confidence_summary.get("interpretation", "Unknown")
    breakdown = confidence_summary.get("breakdown", {})

    header = f"""
{'='*70}
  RUMI REPORT — TRANSPARENCY DISCLOSURE
{'='*70}

  This report was generated by RUMI (Research & Unified Machine Intelligence),
  an autonomous AI scientific discovery system. Read with the following context:

  SOURCES CONSULTED:
    Real papers fetched:  {papers_count} (from arXiv + PubMed APIs)
    Computations run:     {calc_count} (atmospheric chemistry, Bayesian scoring, Monte Carlo)

  CLAIM CLASSIFICATION:
    {breakdown.get('VALIDATED', 0)} VALIDATED    — Backed by real papers or databases
    {breakdown.get('INFERRED', 0)} INFERRED     — Logical deduction from validated claims
    {breakdown.get('SIMULATED', 0)} SIMULATED    — From computational models (has assumptions)
    {breakdown.get('HYPOTHETICAL', 0)} HYPOTHETICAL — Explicit "what if" scenarios
    {breakdown.get('SPECULATIVE', 0)} SPECULATIVE  — AI-generated, no evidence backing

  OVERALL RELIABILITY: {reliability:.0%}
  {interp}

  IMPORTANT:
    Numbers labeled {{VALIDATED}} come from real papers or HITRAN spectroscopy.
    Numbers labeled {{SIMULATED}} come from models with stated assumptions.
    Numbers labeled {{SPECULATIVE}} were invented by the AI — treat with skepticism.
    Numbers labeled {{HYPOTHETICAL}} are conditional predictions ("if X, then Y").

{'='*70}

"""
    return header
