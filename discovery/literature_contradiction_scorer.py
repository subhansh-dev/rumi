"""
literature_contradiction_scorer.py — Score theories by literature support AND rejection.

Instead of just "confidence = 78%", ask:
  - What papers SUPPORT this theory?
  - What papers CONTRADICT this theory?
  - What's the ratio?

A theory with 5 supporting papers and 2 contradicting is very different
from one with 0 supporting and 0 contradicting (unknown).

This module uses the knowledge graph and paper abstracts to score
literature alignment.
"""

import json
from typing import Dict, List, Optional
from collections import defaultdict


class LiteratureContradictionScorer:
    """
    Score hypotheses by literature support vs rejection.
    """

    def __init__(self, graph=None, llm_call=None):
        self.graph = graph
        self.llm_call = llm_call

    def score(self, theory: dict, papers: list = None) -> dict:
        """
        Score a theory's literature alignment.

        Returns:
            {
                "supporting_papers": [...],
                "contradicting_papers": [...],
                "support_score": 0.0-1.0,
                "contradiction_score": 0.0-1.0,
                "net_alignment": -1.0 to 1.0,
                "literature_verdict": "supported|contradicted|mixed|unknown"
            }
        """
        if not papers:
            return {
                "supporting_papers": [],
                "contradicting_papers": [],
                "support_score": 0.0,
                "contradiction_score": 0.0,
                "net_alignment": 0.0,
                "literature_verdict": "unknown",
            }

        # Algorithmic check: match theory keywords against paper abstracts
        support_hits = []
        contradict_hits = []

        theory_text = self._extract_theory_keywords(theory)

        for p in papers:
            abstract = (p.get("abstract", "") + " " + p.get("title", "")).lower()
            if not abstract.strip():
                continue

            # Check for support signals
            support_signals = [
                "consistent with", "supports", "confirms", "validates",
                "in agreement", "corroborates", "consistent", "agrees",
                "successfully explains", "accounts for", "reproduces",
            ]
            # Check for contradiction signals
            contradict_signals = [
                "contradicts", "inconsistent", "rules out", "excludes",
                "incompatible", "challenges", "refutes", "disproves",
                "fails to explain", "cannot account", "at odds with",
                "tension with", "discrepancy", "disagreement",
            ]

            support_count = sum(1 for s in support_signals if s in abstract)
            contradict_count = sum(1 for s in contradict_signals if s in abstract)

            # Check if any theory keywords appear in the paper
            keyword_hits = sum(1 for kw in theory_text if kw in abstract)

            if keyword_hits > 0:
                if support_count > contradict_count:
                    support_hits.append({
                        "title": p.get("title", "?")[:80],
                        "source": p.get("source", "?"),
                        "support_signals": support_count,
                        "keyword_hits": keyword_hits,
                    })
                elif contradict_count > support_count:
                    contradict_hits.append({
                        "title": p.get("title", "?")[:80],
                        "source": p.get("source", "?"),
                        "contradict_signals": contradict_count,
                        "keyword_hits": keyword_hits,
                    })

        # Also check graph for contradictions
        graph_contradictions = self._check_graph_contradictions(theory)

        total_papers = len(papers)
        support_score = len(support_hits) / max(1, total_papers)
        contradiction_score = (len(contradict_hits) + len(graph_contradictions)) / max(1, total_papers)

        # Net alignment: positive = supported, negative = contradicted
        net = support_score - contradiction_score

        # Verdict
        if net > 0.3:
            verdict = "supported"
        elif net < -0.3:
            verdict = "contradicted"
        elif abs(net) < 0.1 and (support_hits or contradict_hits):
            verdict = "mixed"
        else:
            verdict = "unknown"

        return {
            "supporting_papers": support_hits,
            "contradicting_papers": contradict_hits,
            "graph_contradictions": graph_contradictions,
            "support_score": round(support_score, 3),
            "contradiction_score": round(contradiction_score, 3),
            "net_alignment": round(net, 3),
            "literature_verdict": verdict,
            "total_papers_checked": total_papers,
        }

    def _extract_theory_keywords(self, theory: dict) -> list:
        """Extract searchable keywords from a theory."""
        keywords = set()

        # From name
        name = theory.get("name", "")
        for word in name.lower().split():
            if len(word) > 3 and word not in ("the", "and", "for", "with", "that", "this"):
                keywords.add(word)

        # From description
        desc = theory.get("description", theory.get("mechanism", ""))
        for word in desc.lower().split():
            if len(word) > 5 and word.isalpha():
                keywords.add(word)

        # From hidden variables
        for hv in theory.get("hidden_variables", []):
            if isinstance(hv, str):
                for word in hv.lower().split():
                    if len(word) > 4:
                        keywords.add(word)

        return list(keywords)[:20]

    def _check_graph_contradictions(self, theory: dict) -> list:
        """Check if the theory contradicts relationships in the knowledge graph."""
        if not self.graph:
            return []

        contradictions = []
        entities = self.graph.entities if hasattr(self.graph, 'entities') else {}
        relationships = self.graph.relationships if hasattr(self.graph, 'relationships') else []

        theory_text = json.dumps(theory).lower()

        # Check if theory proposes something that contradicts graph relationships
        OPPOSITES = {
            "activates": "inhibits", "inhibits": "activates",
            "increases": "decreases", "decreases": "increases",
        }

        for rel in relationships:
            src = entities.get(rel["source"], {}).get("name", "").lower()
            tgt = entities.get(rel["target"], {}).get("name", "").lower()
            rel_type = rel.get("relation", "").lower()

            # If the theory mentions both entities but proposes the opposite relation
            if src in theory_text and tgt in theory_text:
                opposite = OPPOSITES.get(rel_type)
                if opposite and opposite in theory_text:
                    contradictions.append({
                        "graph_relation": f"{src} --{rel_type}--> {tgt}",
                        "theory_proposes": opposite,
                        "severity": "high",
                    })

        return contradictions[:5]
