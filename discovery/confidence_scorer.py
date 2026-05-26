"""Evidence-weighted confidence scoring for hypotheses — calibrated for differentiation."""

from math import log2
from collections import defaultdict


class ConfidenceScorer:
    def __init__(self):
        self.weights = {
            "paper_count": 0.25,
            "citation_impact": 0.15,
            "recency": 0.10,
            "replication": 0.15,
            "mechanistic_coherence": 0.15,
            "contradiction_penalty": 0.10,
            "novelty_penalty": 0.05,
            "evidence_density": 0.05,
        }

    def score(self, hypothesis, graph=None, contradictions=None):
        paper_count = self._score_paper_count(hypothesis)
        citation = self._score_citation_impact(hypothesis, graph)
        recency = self._score_recency(hypothesis, graph)
        replication = self._score_replication(hypothesis)
        mech_coherence = self._score_mechanistic_coherence(hypothesis)
        contradiction_penalty = self._score_contradiction_penalty(hypothesis, contradictions or [])
        novelty_penalty = self._score_novelty_penalty(hypothesis)
        evidence_density = self._score_evidence_density(hypothesis)

        raw = (
            paper_count * self.weights["paper_count"]
            + citation * self.weights["citation_impact"]
            + recency * self.weights["recency"]
            + replication * self.weights["replication"]
            + mech_coherence * self.weights["mechanistic_coherence"]
            + evidence_density * self.weights["evidence_density"]
            - contradiction_penalty * self.weights["contradiction_penalty"]
            - novelty_penalty * self.weights["novelty_penalty"]
        )

        final = max(0.0, min(1.0, raw))

        return {
            "confidence": round(final, 3),
            "components": {
                "paper_count": round(paper_count, 3),
                "citation_impact": round(citation, 3),
                "recency": round(recency, 3),
                "replication": round(replication, 3),
                "mechanistic_coherence": round(mech_coherence, 3),
                "contradiction_penalty": round(contradiction_penalty, 3),
                "novelty_penalty": round(novelty_penalty, 3),
                "evidence_density": round(evidence_density, 3),
            },
            "weights": self.weights,
        }

    def _score_paper_count(self, hypothesis):
        papers = hypothesis.get("papers", [])
        supporting = hypothesis.get("supporting_evidence", hypothesis.get("evidence", []))
        edges = hypothesis.get("edges", [])
        edge_papers = set()
        for e in edges:
            ps = e.get("papers", [])
            if isinstance(ps, list):
                edge_papers.update(ps)
        all_papers = set(papers) | edge_papers
        n = len(all_papers)
        if n == 0:
            # Use evidence items count as proxy
            ev = len(supporting)
            if ev == 0:
                return 0.05
            return min(0.3, ev * 0.05)
        return min(1.0, log2(n + 1) / 5.0)

    def _score_citation_impact(self, hypothesis, graph):
        if not graph or not hasattr(graph, "entities"):
            return 0.3
        papers = hypothesis.get("papers", [])
        supporting = hypothesis.get("supporting_evidence", hypothesis.get("evidence", []))
        if not papers and not supporting:
            return 0.2
        counts = 0
        nodes = hypothesis.get("nodes", [])
        for node in nodes:
            name = node.get("name", "")
            for eid, ent in graph.entities.items():
                if ent.get("name", "").lower() == name.lower():
                    counts += len(ent.get("papers", []))
        return min(1.0, counts / 15.0)

    def _score_recency(self, hypothesis, graph):
        import time
        papers = hypothesis.get("papers", [])
        if not papers:
            return 0.4
        current_year = 2026
        years = []
        for p in papers:
            if isinstance(p, str) and p.startswith("PMID"):
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
            return 0.4
        avg_year = sum(years) / len(years)
        age = current_year - avg_year
        recency = max(0.0, 1.0 - (age / 15.0))
        return recency

    def _score_replication(self, hypothesis):
        edges = hypothesis.get("edges", [])
        if not edges:
            supporting = hypothesis.get("supporting_evidence", hypothesis.get("evidence", []))
            if len(supporting) >= 2:
                return min(0.5, len(supporting) * 0.1)
            return 0.2
        replication_counts = []
        for e in edges:
            papers = e.get("papers", [])
            if isinstance(papers, list) and len(papers) >= 2:
                replication_counts.append(min(1.0, len(papers) / 5.0))
        if not replication_counts:
            return 0.2
        return sum(replication_counts) / len(replication_counts)

    def _score_mechanistic_coherence(self, hypothesis):
        """Score how detailed the mechanistic reasoning is."""
        rationale = hypothesis.get("mechanistic_rationale", hypothesis.get("description", ""))
        if not rationale:
            return 0.2
        # Count mechanistic signal words
        mech_signals = ["because", "via", "through", "by", "causes", "leads to",
                        "triggers", "phosphorylates", "activates", "inhibits",
                        "regulates", "binds", "catalyzes", "mediates", "promotes",
                        "suppresses", "blocks", "reduces", "increases", "modulates"]
        signals = sum(1 for w in mech_signals if w in rationale.lower())
        # Count conditional language
        cond_signals = ["if", "when", "under", "only", "dependent", "conditions",
                        "requires", "in the presence", "in the absence"]
        conds = sum(1 for w in cond_signals if w in rationale.lower())
        # Count entities with definitions
        nodes = hypothesis.get("nodes", [])
        defined = sum(1 for n in nodes if n.get("definition") or n.get("conditions"))
        total_nodes = len(nodes) or 1

        raw = (signals * 0.05) + (conds * 0.05) + (defined / total_nodes * 0.2)
        return min(1.0, raw)

    def _score_novelty_penalty(self, hypothesis):
        """Novel hypotheses (less evidence) score lower confidence."""
        novelty = hypothesis.get("novelty", "medium")
        if novelty == "high":
            return 0.3
        if novelty == "medium":
            return 0.1
        return 0.0

    def _score_evidence_density(self, hypothesis):
        """Score based on amount of specific evidence provided."""
        supporting = hypothesis.get("supporting_evidence", hypothesis.get("evidence", []))
        contradictory = hypothesis.get("contradictory_evidence", [])
        alt_explanations = hypothesis.get("alternative_explanations", [])
        failure_conditions = hypothesis.get("failure_conditions", [])
        source_trace = hypothesis.get("source_traceability", [])

        n_evidence = len(supporting)
        n_contra = len(contradictory)
        n_alt = len(alt_explanations)
        n_fail = len(failure_conditions)
        n_trace = len(source_trace) if isinstance(source_trace, list) else 0

        # More evidence items + contradictions + alt explanations = richer hypothesis
        score = (n_evidence * 0.04) + (n_contra * 0.02) + (n_alt * 0.02) + (n_fail * 0.02) + (n_trace * 0.01)
        return min(1.0, score)

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
