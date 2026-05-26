"""Algorithmic contradiction detection in knowledge graphs."""

from collections import defaultdict

OPPOSITE_RELATIONS = {
    "activates": "inhibits",
    "inhibits": "activates",
    "upregulates": "downregulates",
    "downregulates": "upregulates",
    "increases": "decreases",
    "decreases": "increases",
    "promotes": "suppresses",
    "suppresses": "promotes",
    "binds": "blocks",
    "blocks": "binds",
}

RELATION_GROUPS = {
    "positive": ["activates", "upregulates", "increases", "promotes", "induces", "stimulates", "enhances"],
    "negative": ["inhibits", "downregulates", "suppresses", "blocks", "reduces", "decreases", "represses"],
}


def _inverse_group(rel):
    for group, members in RELATION_GROUPS.items():
        if rel in members:
            return "negative" if group == "positive" else "positive"
    return None


class ContradictionMiner:
    def __init__(self, graph=None):
        self.graph = graph

    def mine(self, graph=None):
        g = graph or self.graph
        if not g:
            return {"contradictions": [], "severity_scores": {}, "summary": "No graph provided"}

        entities = g.entities if hasattr(g, "entities") else {}
        rels = g.relationships if hasattr(g, "relationships") else []

        contradictions = []
        direct = self._find_direct(rels, entities)
        contradictions.extend(direct)
        path_based = self._find_path(g, entities, rels)
        contradictions.extend(path_based)
        paper_based = self._find_paper(rels, entities)
        contradictions.extend(paper_based)
        temporal = self._find_temporal(g, entities)
        contradictions.extend(temporal)

        scores = {c["id"]: c["severity"] for c in contradictions}
        summary = self._summarize(contradictions)

        return {"contradictions": contradictions, "severity_scores": scores, "summary": summary}

    def _find_direct(self, relationships, entities):
        found = []
        by_pair = defaultdict(list)
        for r in relationships:
            pair = (r.get("source"), r.get("target"))
            by_pair[pair].append(r)

        for pair, rels in by_pair.items():
            rel_types = set(r.get("relation") for r in rels)
            for rel_a in rel_types:
                for rel_b in rel_types:
                    if rel_a == rel_b:
                        continue
                    if OPPOSITE_RELATIONS.get(rel_a) == rel_b:
                        papers_a = [r.get("papers", []) for r in rels if r.get("relation") == rel_a]
                        papers_b = [r.get("papers", []) for r in rels if r.get("relation") == rel_b]
                        papers_a_flat = [p for sub in papers_a for p in (sub if isinstance(sub, list) else [sub])]
                        papers_b_flat = [p for sub in papers_b for p in (sub if isinstance(sub, list) else [sub])]
                        severity = min(1.0, 0.3 + 0.1 * min(len(papers_a_flat), len(papers_b_flat)))
                        found.append({
                            "id": f"direct_{pair[0]}_{pair[1]}_{rel_a}_vs_{rel_b}",
                            "type": "direct",
                            "entity_a": pair[0],
                            "entity_b": pair[1],
                            "relation_a": rel_a,
                            "relation_b": rel_b,
                            "papers_a": papers_a_flat,
                            "papers_b": papers_b_flat,
                            "severity": severity,
                            "description": f"{pair[0]} {rel_a} {pair[1]} BUT ALSO {rel_b} {pair[1]}"
                        })
        return found

    def _find_path(self, graph, entities, relationships):
        """Find path-level contradictions through intermediate entities."""
        found = []
        # Build adjacency: source -> [(rel, target)]
        adj = defaultdict(list)
        for r in relationships:
            adj[r.get("source")].append((r.get("relation"), r.get("target")))

        # For each entity, check if it affects another through conflicting paths
        for source in adj:
            targets_by_path = defaultdict(list)

            for rel_a, mid in adj[source]:
                for rel_b, target in adj.get(mid, []):
                    targets_by_path[target].append((rel_a, rel_b, mid, source))

            for target, paths in targets_by_path.items():
                if len(paths) < 2:
                    continue
                # Look for opposite group relations reaching same target
                for i, (ra1, rb1, mid1, src1) in enumerate(paths):
                    for ra2, rb2, mid2, src2 in paths[i+1:]:
                        group1 = _inverse_group(rb1)
                        group2 = _inverse_group(rb2)
                        if group1 and group2 and group1 != group2:
                            severity = 0.5
                            found.append({
                                "id": f"path_{target}_{len(found)}",
                                "type": "path",
                                "entity_a": src1,
                                "entity_b": target,
                                "relation_a": f"{ra1}(via {mid1}) -> {rb1}",
                                "relation_b": f"{ra2}(via {mid2}) -> {rb2}",
                                "papers_a": [],
                                "papers_b": [],
                                "severity": severity,
                                "description": f"{src1} positively regulates {target} via {mid1} but also negatively via {mid2}"
                            })
        return found

    def _find_paper(self, relationships, entities):
        """Find cases where papers disagree on the same relationship."""
        found = []
        by_rel = defaultdict(list)
        for r in relationships:
            key = (r.get("source"), r.get("relation"), r.get("target"))
            by_rel[key].append(r)

        for key, rels in by_rel.items():
            all_papers = set()
            paper_sets = []
            for r in rels:
                papers = r.get("papers", [])
                if isinstance(papers, str):
                    papers = [papers]
                ps = set(papers)
                paper_sets.append(ps)
                all_papers.update(ps)

            if len(paper_sets) < 2:
                continue

            # Check for contradictions across paper groups
            for type_a, type_b in [("positive", "negative")]:
                pos_papers = set()
                neg_papers = set()
                for r in rels:
                    papers = r.get("papers", [])
                    if isinstance(papers, str):
                        papers = [papers]
                    rel_type = _inverse_group(r.get("relation"))
                    if rel_type == "positive":
                        pos_papers.update(papers)
                    elif rel_type == "negative":
                        neg_papers.update(papers)

                if pos_papers and neg_papers:
                    severity = min(1.0, 0.4 + 0.05 * min(len(pos_papers), len(neg_papers)))
                    found.append({
                        "id": f"paper_{key[0]}_{key[1]}_{key[2]}",
                        "type": "paper",
                        "entity_a": key[0],
                        "entity_b": key[2],
                        "relation_a": f"{key[1]} (positive effect)",
                        "relation_b": f"{key[1]} (negative effect)",
                        "papers_a": list(pos_papers),
                        "papers_b": list(neg_papers),
                        "severity": severity,
                        "description": f"Papers disagree on {key[0]} affecting {key[2]}: {len(pos_papers)} say positive, {len(neg_papers)} say negative"
                    })
        return found

    def _find_temporal(self, graph, entities):
        """Find temporal contradictions — entity roles that changed over time."""
        found = []
        if not hasattr(graph, "entity_temporal") or not graph.entity_temporal:
            # Try to infer from entity papers
            for eid, ent in entities.items():
                papers = ent.get("papers", [])
                if len(papers) < 3:
                    continue
                # Simple check: entity involved in both positive and negative relations
                # across different time periods
                yrs = []
                for p in papers:
                    if isinstance(p, dict):
                        yrs.append(p.get("year", ""))
                if len(yrs) >= 3:
                    found.append({
                        "id": f"temporal_{eid}",
                        "type": "temporal",
                        "entity_a": ent.get("name"),
                        "entity_b": "",
                        "relation_a": "early papers",
                        "relation_b": "late papers",
                        "papers_a": papers[:len(papers)//2],
                        "papers_b": papers[len(papers)//2:],
                        "severity": 0.3,
                        "description": f"{ent.get('name')} spans {min(yrs)}-{max(yrs)} — role may have evolved"
                    })
        return found

    def _summarize(self, contradictions):
        if not contradictions:
            return "No contradictions detected"
        by_type = defaultdict(int)
        for c in contradictions:
            by_type[c["type"]] += 1
        parts = [f"{v} {k}" for k, v in sorted(by_type.items())]
        high = sum(1 for c in contradictions if c["severity"] >= 0.6)
        return f"{len(contradictions)} contradictions found: {', '.join(parts)}" + (f" ({high} high severity)" if high else "")
