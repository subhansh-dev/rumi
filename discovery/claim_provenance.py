"""
discovery/claim_provenance.py — Full Provenance Tracking for Every Claim

Every claim in RUMI's output gets:
  - SOURCE: which paper or computation it came from
  - INFERENCE: the logical steps from evidence to claim
  - CONFIDENCE: propagated through the chain
  - PROVENANCE: exactly WHY this claim exists

Usage:
    from discovery.claim_provenance import ProvenanceTracker
    tracker = ProvenanceTracker(papers, calculations)
    report = tracker.process_report(raw_llm_output)
    print(report)  # Full report with provenance annotations
"""

import re
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


# ══════════════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ProvenanceSource:
    """Where a claim came from."""
    type: str  # "paper", "computation", "inference", "assumption"
    ref: str   # Citation key, calculation name, or description
    detail: str  # Specific finding, formula, or logical step
    confidence: float  # 0.0-1.0
    url: str = ""  # Link to source if available

@dataclass
class ProvenanceChain:
    """Full chain from evidence to claim."""
    claim: str  # The claim text
    label: str  # VALIDATED, INFERRED, SIMULATED, SPECULATIVE, HYPOTHETICAL
    sources: list = field(default_factory=list)  # List of ProvenanceSource
    inference_steps: list = field(default_factory=list)  # Logical steps
    confidence: float = 0.0  # Propagated confidence
    confidence_breakdown: dict = field(default_factory=dict)
    query: str = ""  # "show me why" answer

    def to_dict(self):
        return {
            "claim": self.claim[:200],
            "label": self.label,
            "sources": [asdict(s) for s in self.sources],
            "inference_steps": self.inference_steps,
            "confidence": round(self.confidence, 3),
            "confidence_breakdown": self.confidence_breakdown,
            "why": self.query,
        }


# ══════════════════════════════════════════════════════════════════════
#  PROVENANCE TRACKER
# ══════════════════════════════════════════════════════════════════════

class ProvenanceTracker:
    def __init__(self, papers: list, calculations: dict):
        self.papers = papers
        self.calculations = calculations
        self.claim_chains = []

        # Build lookup tables
        self._paper_map = {}  # citation_num -> paper
        for i, p in enumerate(papers, 1):
            self._paper_map[str(i)] = p

        self._calc_map = {}  # calculation_name -> result
        for name, result in calculations.items():
            if isinstance(result, dict):
                self._calc_map[name.lower()] = result
                # Also store without domain prefix
                short = name.split("_", 1)[-1] if "_" in name else name
                self._calc_map[short.lower()] = result

    def process_report(self, text: str) -> str:
        """
        Parse the full LLM report, annotate each claim with provenance.
        Returns the annotated report with provenance blocks.
        """
        paragraphs = text.split('\n')
        annotated_lines = []
        current_section = ""
        claim_id = 0

        for line in paragraphs:
            stripped = line.strip()

            # Track section headers
            if stripped.startswith('PHASE') or stripped.startswith('#') or stripped.startswith('**PHASE'):
                current_section = stripped
                annotated_lines.append(line)
                continue

            # Skip empty / short lines
            if not stripped or len(stripped) < 25:
                annotated_lines.append(line)
                continue

            # Skip already-annotated lines
            if '{VALIDATED}' in stripped or '{INFERRED}' in stripped or \
               '{SIMULATED}' in stripped or '{SPECULATIVE}' in stripped or \
               '{HYPOTHETICAL}' in stripped or '[UNVERIFIED]' in stripped:
                # Still extract provenance even for pre-labeled lines
                chain = self._build_provenance(stripped, current_section)
                if chain and chain.sources:
                    claim_id += 1
                    annotated_lines.append(line)
                    annotated_lines.append(self._format_provenance(chain, claim_id))
                else:
                    annotated_lines.append(line)
                continue

            # Classify and build provenance
            chain = self._build_provenance(stripped, current_section)

            if chain:
                claim_id += 1
                # Add inline label
                label = chain.label
                if label:
                    line = f"{line}  {{{label}}}"
                annotated_lines.append(line)
                # Add provenance block
                annotated_lines.append(self._format_provenance(chain, claim_id))
            else:
                annotated_lines.append(line)

        # Add provenance summary
        summary = self._build_summary()
        annotated_lines.append("\n" + summary)

        return '\n'.join(annotated_lines)

    def _build_provenance(self, text: str, section: str) -> Optional[ProvenanceChain]:
        """Build full provenance chain for a single claim."""
        sources = []
        inference_steps = []
        confidences = []

        # ── Find paper citations ──
        paper_refs = re.findall(r'\[(\d+)\]', text)
        for ref in paper_refs:
            paper = self._paper_map.get(ref)
            if paper:
                src = ProvenanceSource(
                    type="paper",
                    ref=paper.get("citation_key", f"[{ref}]"),
                    detail=paper.get("title", "")[:120],
                    confidence=0.85,  # Peer-reviewed paper confidence
                    url=paper.get("url", ""),
                )
                sources.append(src)
                confidences.append(("paper_citation", 0.85))

        # ── Find computational references ──
        text_lower = text.lower()
        for calc_name, calc_result in self._calc_map.items():
            if calc_name in text_lower or calc_name.replace("_", " ") in text_lower:
                if isinstance(calc_result, dict) and "value" in calc_result:
                    src = ProvenanceSource(
                        type="computation",
                        ref=calc_name,
                        detail=f"{calc_result.get('value', '?')} {calc_result.get('units', '')} "
                               f"({calc_result.get('label', 'unknown')})",
                        confidence=calc_result.get("confidence", 0.5),
                    )
                    sources.append(src)
                    confidences.append(("computation", calc_result.get("confidence", 0.5)))

        # ── Check for specific number claims ──
        number_matches = re.findall(
            r'(\d+\.?\d*)\s*(ppb|ppm|ppt|km|µm|um|K\b|atm|eV|GPa|hours?|W/m²|%)',
            text
        )
        for value, unit in number_matches:
            # Check if this number comes from a calculation
            matched_calc = None
            for calc_name, calc_result in self._calc_map.items():
                if isinstance(calc_result, dict):
                    calc_val = calc_result.get("value")
                    if calc_val is not None and isinstance(calc_val, (int, float)):
                        if abs(float(value) - calc_val) / max(abs(calc_val), 1e-10) < 0.1:
                            matched_calc = calc_result
                            break

            if matched_calc:
                confidences.append(("number_from_calc", matched_calc.get("confidence", 0.5)))
            elif sources:  # Number with a paper citation
                confidences.append(("number_with_citation", 0.7))
            else:
                confidences.append(("number_no_source", 0.1))

        # ── Determine label ──
        has_citation = bool(paper_refs)
        has_computation = any(s.type == "computation" for s in sources)
        has_unverified = "[UNVERIFIED]" in text
        has_hypothetical = any(w in text_lower for w in
                              ["would", "could", "might", "if ", "hypothetical",
                               "assuming", "potentially", "in theory"])
        has_numbers = bool(number_matches)

        if has_unverified:
            label = "SPECULATIVE"
        elif has_citation and has_computation:
            label = "VALIDATED"
        elif has_citation:
            label = "VALIDATED" if has_numbers else "INFERRED"
        elif has_computation:
            label = "SIMULATED"
        elif has_hypothetical:
            label = "HYPOTHETICAL"
        elif has_numbers and not has_citation:
            label = "SPECULATIVE"
        else:
            label = "INFERRED"

        # ── Build inference chain ──
        if sources:
            for i, src in enumerate(sources):
                if src.type == "paper":
                    inference_steps.append(
                        f"Evidence from {src.ref}: \"{src.detail[:80]}\""
                    )
                elif src.type == "computation":
                    inference_steps.append(
                        f"Computed via {src.ref}: {src.detail}"
                    )

        if not sources and not inference_steps:
            return None

        # ── Calculate propagated confidence ──
        confidence = self._propagate_confidence(confidences, sources)

        # ── Build "why" explanation ──
        why_parts = []
        for src in sources:
            if src.type == "paper":
                why_parts.append(f"paper {src.ref} ({src.detail[:60]})")
            elif src.type == "computation":
                why_parts.append(f"calculation {src.ref} = {src.detail}")
        if not why_parts:
            why_parts.append("no grounded source — claim is speculative")

        chain = ProvenanceChain(
            claim=text[:200],
            label=label,
            sources=sources,
            inference_steps=inference_steps,
            confidence=confidence,
            confidence_breakdown=dict(confidences),
            query=" → ".join(why_parts),
        )

        self.claim_chains.append(chain)
        return chain

    def _propagate_confidence(self, confidences: list, sources: list) -> float:
        """
        Propagate confidence through the inference chain.
        Rule: weakest link determines overall confidence.
        """
        if not confidences:
            return 0.1

        values = [c[1] for c in confidences]

        # Weakest link (min) weighted by source count
        weakest = min(values)
        source_bonus = min(0.1, len(sources) * 0.03)

        # If we have both paper and computation, boost confidence
        has_paper = any(s.type == "paper" for s in sources)
        has_calc = any(s.type == "computation" for s in sources)
        multi_source_bonus = 0.1 if (has_paper and has_calc) else 0

        final = min(1.0, weakest + source_bonus + multi_source_bonus)
        return round(final, 3)

    def _format_provenance(self, chain: ProvenanceChain, claim_id: int) -> str:
        """Format a provenance block for display."""
        lines = [f"    ┌─ PROVENANCE #{claim_id} ─────────────────────────────────────"]

        # Sources
        for src in chain.sources:
            if src.type == "paper":
                lines.append(f"    │  SOURCE: {src.ref} (confidence: {src.confidence:.0%})")
                lines.append(f"    │    \"{src.detail[:80]}\"")
                if src.url:
                    lines.append(f"    │    {src.url}")
            elif src.type == "computation":
                lines.append(f"    │  CALC:   {src.ref} = {src.detail} (confidence: {src.confidence:.0%})")

        # Inference steps
        if chain.inference_steps:
            lines.append(f"    │  INFERENCE CHAIN:")
            for i, step in enumerate(chain.inference_steps, 1):
                lines.append(f"    │    {i}. {step[:100]}")

        # Confidence
        lines.append(f"    │  CONFIDENCE: {chain.confidence:.0%}")
        if chain.confidence_breakdown:
            for name, val in chain.confidence_breakdown.items():
                lines.append(f"    │    {name}: {val:.0%}")

        # Why
        lines.append(f"    │  WHY: {chain.query[:120]}")
        lines.append(f"    └──────────────────────────────────────────────────")

        return "\n".join(lines)

    def _build_summary(self) -> str:
        """Build a provenance summary of all tracked claims."""
        if not self.claim_chains:
            return ""

        total = len(self.claim_chains)
        by_label = {}
        by_source_type = {"paper": 0, "computation": 0, "inference": 0, "assumption": 0}
        total_confidence = 0

        for chain in self.claim_chains:
            by_label[chain.label] = by_label.get(chain.label, 0) + 1
            for src in chain.sources:
                by_source_type[src.type] = by_source_type.get(src.type, 0) + 1
            total_confidence += chain.confidence

        avg_confidence = total_confidence / total if total > 0 else 0

        lines = [
            "=" * 70,
            "  PROVENANCE SUMMARY",
            "=" * 70,
            "",
            f"  Total claims tracked: {total}",
            f"  Average confidence:  {avg_confidence:.0%}",
            "",
            "  By label:",
        ]
        for label, count in sorted(by_label.items()):
            pct = count / total * 100
            lines.append(f"    {label:15s} {count:3d} ({pct:.0f}%)")

        lines.append("")
        lines.append("  Source distribution:")
        for stype, count in sorted(by_source_type.items()):
            if count > 0:
                lines.append(f"    {stype:15s} {count:3d} references")

        # Top provenance chains (highest confidence)
        top = sorted(self.claim_chains, key=lambda c: c.confidence, reverse=True)[:5]
        if top:
            lines.append("")
            lines.append("  Strongest claims (highest confidence):")
            for i, chain in enumerate(top, 1):
                lines.append(f"    {i}. [{chain.label}] {chain.claim[:80]}...")
                lines.append(f"       Confidence: {chain.confidence:.0%} | {chain.query[:80]}")

        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════
#  CONVENIENCE
# ══════════════════════════════════════════════════════════════════════

def add_provenance(text: str, papers: list, calculations: dict) -> str:
    """One-call convenience: add provenance tracking to a report."""
    tracker = ProvenanceTracker(papers, calculations)
    return tracker.process_report(text)


def get_provenance_json(text: str, papers: list, calculations: dict) -> str:
    """Get provenance data as JSON for programmatic use."""
    tracker = ProvenanceTracker(papers, calculations)
    tracker.process_report(text)
    return json.dumps(
        [chain.to_dict() for chain in tracker.claim_chains],
        indent=2, default=str,
    )
