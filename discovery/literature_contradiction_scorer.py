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

        Scoring philosophy:
        - Papers that share topic keywords = IMPLICIT support (they study the same thing)
        - Papers with explicit support signals = STRONG support
        - Papers with explicit contradiction signals = CONTRADICTION
        - A theory with 0 explicit support but 20 topic-relevant papers is NOT unsupported

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
        topic_relevant_hits = []  # papers that share topic keywords (implicit support)

        theory_keywords = self._extract_theory_keywords(theory)

        for p in papers:
            abstract = (p.get("abstract", "") + " " + p.get("title", "")).lower()
            if not abstract.strip():
                continue

            # Check for explicit support signals
            support_signals = [
                "consistent with", "supports", "confirms", "validates",
                "in agreement", "corroborates", "consistent", "agrees",
                "successfully explains", "accounts for", "reproduces",
                "demonstrates", "shows that", "we find", "we report",
                "our results suggest", "evidence for", "observation of",
            ]
            # Check for contradiction signals
            contradict_signals = [
                "contradicts", "inconsistent", "rules out", "excludes",
                "incompatible", "challenges", "refutes", "disproves",
                "fails to explain", "cannot account", "at odds with",
                "tension with", "discrepancy", "disagreement",
                "however,", "but", "nevertheless", "in contrast",
            ]

            support_count = sum(1 for s in support_signals if s in abstract)
            contradict_count = sum(1 for s in contradict_signals if s in abstract)

            # Check if any theory keywords appear in the paper
            keyword_hits = sum(1 for kw in theory_keywords if kw in abstract)

            if keyword_hits >= 3:
                # Strong topic relevance — this paper studies the same area
                topic_relevant_hits.append({
                    "title": p.get("title", "?")[:80],
                    "source": p.get("source", "?"),
                    "keyword_hits": keyword_hits,
                    "citation_count": p.get("citation_count", 0),
                })

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

        # Support score: explicit support + implicit topic relevance
        # Topic-relevant papers count as 0.3 support each (they study the same thing)
        explicit_support = len(support_hits) / max(1, total_papers)
        implicit_support = min(0.4, len(topic_relevant_hits) * 0.05)  # cap at 0.4
        support_score = min(1.0, explicit_support + implicit_support)

        contradiction_score = (len(contradict_hits) + len(graph_contradictions)) / max(1, total_papers)

        # Net alignment: positive = supported, negative = contradicted
        net = support_score - contradiction_score

        # Verdict
        if net > 0.2:
            verdict = "supported"
        elif net < -0.2:
            verdict = "contradicted"
        elif abs(net) < 0.1 and (support_hits or contradict_hits):
            verdict = "mixed"
        elif topic_relevant_hits:
            verdict = "topic_relevant"  # papers exist on this topic
        else:
            verdict = "unknown"

        return {
            "supporting_papers": support_hits,
            "contradicting_papers": contradict_hits,
            "topic_relevant_papers": topic_relevant_hits[:10],
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
        stopwords = {"the", "and", "for", "with", "that", "this", "from", "are", "has",
                     "was", "were", "been", "have", "will", "would", "could", "should",
                     "into", "over", "such", "than", "them", "then", "they", "this",
                     "very", "when", "what", "which", "while", "who", "whom", "why"}

        # From name
        name = theory.get("name", "")
        for word in name.lower().split():
            clean = word.strip("()[]{},.:;")
            if len(clean) > 3 and clean not in stopwords and clean.isalpha():
                keywords.add(clean)

        # From description
        desc = theory.get("description", theory.get("mechanism", ""))
        for word in desc.lower().split():
            clean = word.strip("()[]{},.:;")
            if len(clean) > 3 and clean not in stopwords and clean.isalpha():
                keywords.add(clean)

        # From hidden variables
        for hv in theory.get("hidden_variables", []):
            if isinstance(hv, str):
                for word in hv.lower().split():
                    clean = word.strip("()[]{},.:;")
                    if len(clean) > 3 and clean not in stopwords:
                        keywords.add(clean)

        return list(keywords)[:30]

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
