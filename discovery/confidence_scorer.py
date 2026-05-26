"""Evidence-weighted confidence scoring for hypotheses."""

from math import log2
from collections import defaultdict


class ConfidenceScorer:
    def __init__(self):
        self.weights = {
            "paper_count": 0.35,
            "citation_impact": 0.20,
            "recency": 0.15,
            "replication": 0.20,
            "contradiction_penalty": 0.10,
        }

    def score(self, hypothesis, graph=None, contradictions=None):
        paper_count = self._score_paper_count(hypothesis)
        citation = self._score_citation_impact(hypothesis, graph)
        recency = self._score_recency(hypothesis, graph)
        replication = self._score_replication(hypothesis)
        contradiction_penalty = self._score_contradiction_penalty(hypothesis, contradictions or [])

        raw = (
            paper_count * self.weights["paper_count"]
            + citation * self.weights["citation_impact"]
            + recency * self.weights["recency"]
            + replication * self.weights["replication"]
            - contradiction_penalty * self.weights["contradiction_penalty"]
        )

        final = max(0.0, min(1.0, raw))

        return {
            "confidence": round(final, 3),
            "components": {
                "paper_count": round(paper_count, 3),
                "citation_impact": round(citation, 3),
                "recency": round(recency, 3),
                "replication": round(replication, 3),
                "contradiction_penalty": round(contradiction_penalty, 3),
            },
            "weights": self.weights,
        }

    def _score_paper_count(self, hypothesis):
        papers = hypothesis.get("papers", [])
        edges = hypothesis.get("edges", [])
        edge_papers = set()
        for e in edges:
            ps = e.get("papers", [])
            if isinstance(ps, list):
                edge_papers.update(ps)
        all_papers = set(papers) | edge_papers
        n = len(all_papers)
        if n == 0:
            return 0.1
        return min(1.0, log2(n + 1) / 5.0)

    def _score_citation_impact(self, hypothesis, graph):
        if not graph or not hasattr(graph, "entities"):
            return 0.5
        papers = hypothesis.get("papers", [])
        if not papers:
            return 0.3
        # Count how many times entities from this hypothesis appear in the graph
        counts = 0
        nodes = hypothesis.get("nodes", [])
        for node in nodes:
            name = node.get("name", "")
            for eid, ent in graph.entities.items():
                if ent.get("name", "").lower() == name.lower():
                    counts += len(ent.get("papers", []))
        return min(1.0, counts / 20.0)

    def _score_recency(self, hypothesis, graph):
        import time
        papers = hypothesis.get("papers", [])
        if not papers:
            return 0.5
        current_year = 2026
        years = []
        for p in papers:
            if isinstance(p, str) and p.startswith("PMID"):
                # Try to extract year from entity data
                try:
                    pmid = p.replace("PMID ", "").strip()
                    if graph and hasattr(graph, "papers"):
                        paper_data = graph.papers.get(pmid, {})
                        yr = paper_data.get("year", "")
                        if yr:
                            years.append(int(yr))
                except (ValueError, TypeError):
                    continue
        if not years:
            return 0.5
        avg_year = sum(years) / len(years)
        age = current_year - avg_year
        recency = max(0.0, 1.0 - (age / 15.0))
        return recency

    def _score_replication(self, hypothesis):
        edges = hypothesis.get("edges", [])
        if not edges:
            return 0.3
        replication_counts = []
        for e in edges:
            papers = e.get("papers", [])
            if isinstance(papers, list) and len(papers) >= 2:
                replication_counts.append(min(1.0, len(papers) / 5.0))
        if not replication_counts:
            return 0.3
        return sum(replication_counts) / len(replication_counts)

    def _score_contradiction_penalty(self, hypothesis, contradictions):
        if not contradictions:
            return 0.0
        nodes = hypothesis.get("nodes", [])
        if not nodes:
            return 0.0
        node_names = set(n.get("name", "").lower() for n in nodes)
        max_severity = 0.0
        for c in contradictions:
            a = c.get("entity_a", "").lower()
            b = c.get("entity_b", "").lower()
            if a in node_names or b in node_names:
                max_severity = max(max_severity, c.get("severity", 0))
        return max_severity
