"""
novelty_checker.py — Is this hypothesis actually NEW, or already known?

RUMI proposed "Early Dark Energy" — but that's a major research area
with hundreds of papers. A real discovery engine must ask:
  "Has anyone proposed this exact mechanism before?"

This module:
1. Searches Semantic Scholar for similar hypotheses
2. Searches arXiv for related papers
3. Compares the proposed mechanism against existing literature
4. Returns a novelty verdict: novel | refinement | rediscovery | well_known

This is the difference between "discovering" something and
"re-discovering" something everyone already knows.
"""

import json
import re
from typing import Dict, List, Optional
from discovery.json_extract import extract_json


class NoveltyChecker:
    """
    Check if a hypothesis is genuinely novel or already known in the literature.
    """

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def check_novelty(self, theory: dict, papers: list = None,
                      topic: str = "", domain: str = "") -> dict:
        """
        Check if a theory is novel against existing literature.

        Returns:
            {
                "novelty_verdict": "novel|refinement|rediscovery|well_known",
                "novelty_score": 0.0-1.0,
                "similar_work": [...],
                "what_is_novel": "...",
                "what_is_known": "...",
                "recommendation": "..."
            }
        """
        # Guard against None inputs
        papers = papers or []

        # 1. Extract key claims from the theory
        claims = self._extract_claims(theory) or []

        # 2. Search for similar work in existing papers
        similar_work = self._find_similar_work(claims, papers) or []

        # 3. LLM-based novelty assessment
        llm_assessment = None
        if self.llm_call:
            llm_assessment = self._llm_novelty_assessment(theory, similar_work, topic, domain)

        # 4. Compute novelty score
        novelty_score = self._compute_novelty_score(theory, similar_work, llm_assessment)

        # 5. Determine verdict (adjusted thresholds — less harsh)
        if novelty_score > 0.65:
            verdict = "novel"
        elif novelty_score > 0.45:
            verdict = "refinement"
        elif novelty_score > 0.25:
            verdict = "rediscovery"
        else:
            verdict = "well_known"

        # 6. Separate what's novel from what's known
        novel_parts, known_parts = self._separate_novel_known(theory, similar_work)

        return {
            "novelty_verdict": verdict,
            "novelty_score": round(novelty_score, 3),
            "similar_work": similar_work,
            "what_is_novel": novel_parts,
            "what_is_known": known_parts,
            "recommendation": self._recommendation(verdict, novel_parts, known_parts),
        }

    def _extract_claims(self, theory: dict) -> list:
        """Extract key scientific claims from a theory."""
        claims = []

        # From name
        name = theory.get("name", "")
        if name:
            claims.append(name)

        # From description — extract key phrases
        desc = theory.get("description", theory.get("mechanism", ""))
        # Extract noun phrases that look like scientific concepts
        for match in re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', desc):
            if len(match) > 8:
                claims.append(match)

        # From mathematical model
        model = theory.get("mathematical_model", theory.get("mathematical_formalism", ""))
        if model:
            # Extract variable names
            for var in re.findall(r'([A-Z][a-z_]+(?:_[a-z]+)*)', model):
                claims.append(var)

        # From hidden variables
        for hv in (theory.get("hidden_variables") or []):
            if isinstance(hv, str):
                claims.append(hv)
            elif isinstance(hv, dict):
                claims.append(hv.get("name", ""))

        # From steps
        for step in (theory.get("steps") or []):
            if isinstance(step, str):
                # Extract key concepts
                for word in step.split():
                    if len(word) > 6 and word[0].isupper():
                        claims.append(word)

        # Deduplicate and clean
        seen = set()
        unique = []
        for c in claims:
            c = c.strip()
            if c and len(c) > 3 and c.lower() not in seen:
                seen.add(c.lower())
                unique.append(c)

        return unique[:15]

    def _find_similar_work(self, claims: list, papers: list) -> list:
        """Find existing work that matches the theory's claims."""
        similar = []

        if not papers:
            return similar

        for paper in papers:
            title = paper.get("title", "").lower()
            abstract = paper.get("abstract", "").lower()
            combined = title + " " + abstract

            # Count claim matches
            matches = []
            for claim in claims:
                claim_lower = claim.lower()
                # Check for exact or partial match
                if claim_lower in combined:
                    matches.append(claim)
                elif len(claim) > 8:
                    # Check for significant word overlap
                    claim_words = set(claim_lower.split())
                    if len(claim_words) > 1:
                        overlap = sum(1 for w in claim_words if w in combined)
                        if overlap >= len(claim_words) * 0.5:
                            matches.append(claim)

            if matches:
                similar.append({
                    "title": paper.get("title", "?")[:100],
                    "source": paper.get("source", "?"),
                    "matching_claims": matches,
                    "match_strength": len(matches) / max(1, len(claims)),
                })

        # Sort by match strength
        similar.sort(key=lambda x: x["match_strength"], reverse=True)
        return similar[:10]

    def _llm_novelty_assessment(self, theory: dict, similar_work: list,
                                 topic: str, domain: str) -> dict:
        """Use LLM to assess novelty against broader literature."""
        theory_summary = f"""
Name: {theory.get('name', '?')}
Type: {theory.get('type', '?')}
Description: {str(theory.get('description', theory.get('mechanism', '')))[:500]}
Key Parameters: {json.dumps((theory.get("key_parameters") if isinstance(theory.get("key_parameters"), list) else [])[:3])}
Predictions: {json.dumps((theory.get("predictions") if isinstance(theory.get("predictions"), list) else [])[:3])}
"""

        similar_text = ""
        for s in (similar_work or [])[:5]:
            claims = s.get('matching_claims') or []
            title = s.get('title', '?')
            similar_text += f"\n- {title} (matches: {', '.join(str(c) for c in claims[:3])})"

        prompt = f"""You are a research novelty assessor. Determine if this proposed theory
is genuinely NEW or already well-known in the literature.

TOPIC: {topic}
DOMAIN: {domain}

PROPOSED THEORY:
{theory_summary}

SIMILAR WORK FOUND IN LITERATURE:
{similar_text if similar_text else "No similar work found in the provided papers."}

Assess:
1. Is the core mechanism genuinely novel, or is it a known concept?
2. What specific aspect (if any) is new?
3. What aspect is already well-studied?
4. How would a domain expert rate this novelty?

Output JSON:
{{
  "is_novel": true|false,
  "novelty_level": "genuinely_novel|incremental_refinement|well_known|rediscovery",
  "what_is_novel": "specific new contribution (if any)",
  "what_is_known": "what already exists in literature",
  "expert_assessment": "how a domain expert would rate this",
  "key_references": ["papers that already propose similar things"]
}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=2048)
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    return extract_json(raw)
        except Exception:
            pass
        return None

    def _compute_novelty_score(self, theory: dict, similar_work: list,
                                llm_assessment: dict = None) -> float:
        """Compute a 0-1 novelty score.

        Scoring philosophy:
        - Start at 0.7 (optimistic — assume novel until proven otherwise)
        - Penalize only for STRONG evidence of prior work
        - Reward for new mechanisms, new predictions, new math
        - Distinguish "refinement" (minor tweak) from "novel synthesis" (new combination)
        """
        score = 0.7  # optimistic default — assume novel until proven otherwise

        # Factor 1: Similar work penalty (only for STRONG matches)
        if similar_work:
            max_match = max(s["match_strength"] for s in similar_work)
            # Only penalize significantly if >50% of claims match existing work
            if max_match > 0.5:
                score -= (max_match - 0.5) * 0.6  # penalty only above 50% match
            elif max_match > 0.3:
                score -= (max_match - 0.3) * 0.2  # mild penalty for moderate matches
            # Weak matches (< 30%) don't penalize — that's normal for novel work

        # Factor 2: LLM assessment
        if llm_assessment:
            level = llm_assessment.get("novelty_level", "")
            level_scores = {
                "genuinely_novel": 0.9,
                "incremental_refinement": 0.6,  # was 0.5 — refinements can still be novel
                "well_known": 0.2,
                "rediscovery": 0.05,
            }
            llm_score = level_scores.get(level, 0.7)
            score = score * 0.4 + llm_score * 0.6

        # Factor 3: Theory type
        is_novel = theory.get("is_novel_vs_known", theory.get("is_novel_vs_extension", ""))
        if is_novel == "novel":
            score += 0.15
        elif is_novel in ("extension_of_known", "modification_of_known"):
            score -= 0.05  # mild penalty — extensions can still be novel

        # Factor 4: Novel components bonus
        has_new_mechanism = theory.get("has_new_mechanism", False)
        has_new_prediction = theory.get("has_new_prediction", False)
        has_new_math = theory.get("has_new_math", False)
        novel_components = sum([has_new_mechanism, has_new_prediction, has_new_math])
        if novel_components >= 2:
            score += 0.1  # bonus for multiple novel components
        elif novel_components == 1:
            score += 0.05

        # Factor 5: No similar work found = likely novel
        if not similar_work:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _separate_novel_known(self, theory: dict, similar_work: list) -> tuple:
        """Separate what's novel from what's known."""
        novel_parts = []
        known_parts = []
        similar_work = similar_work or []

        # Check which claims have matches
        matched_claims = set()
        for s in similar_work:
            matched_claims.update(s.get("matching_claims") or [])

        claims = self._extract_claims(theory)
        for claim in claims:
            if claim in matched_claims:
                known_parts.append(claim)
            else:
                novel_parts.append(claim)

        # Also check theory description
        desc = theory.get("description", "")
        if "novel" in desc.lower() or "new" in desc.lower():
            novel_parts.append("Theory explicitly claims novelty")
        if "extension" in desc.lower() or "modification" in desc.lower():
            known_parts.append("Theory acknowledges building on existing work")

        novel_text = "; ".join(novel_parts[:5]) if novel_parts else "No clearly novel components identified"
        known_text = "; ".join(known_parts[:5]) if known_parts else "No directly matching existing work found"

        return novel_text, known_text

    def _recommendation(self, verdict: str, novel_parts: str, known_parts: str) -> str:
        """Generate recommendation based on novelty assessment."""
        if verdict == "novel":
            return ("GENUINELY NOVEL — This theory proposes new mechanisms not found in existing literature. "
                    "High discovery potential. Proceed with rigorous testing.")
        elif verdict == "refinement":
            return (f"REFINEMENT — This theory builds on existing work ({known_parts}) but adds "
                    f"novel elements ({novel_parts}). Discovery potential is moderate. "
                    "Focus on the novel aspects.")
        elif verdict == "rediscovery":
            return (f"REDISCOVERY — This theory largely matches existing work ({known_parts}). "
                    "The proposed mechanism is already known. Consider pivoting to a genuinely "
                    "novel variant or combining with other unexplored mechanisms.")
        else:
            return (f"WELL KNOWN — This is an established concept ({known_parts}). "
                    "Not a discovery. Either combine with novel elements or explore a different direction.")
