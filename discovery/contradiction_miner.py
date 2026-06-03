"""Algorithmic contradiction detection in knowledge graphs."""

from collections import defaultdict

OPPOSITE_RELATIONS = {
    # Biomedical
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
    # Physics / general
    "supports": "contradicts",
    "contradicts": "supports",
    "predicts": "refutes",
    "refutes": "predicts",
    "confirms": "challenges",
    "challenges": "confirms",
    "validates": "invalidates",
    "invalidates": "validates",
    "compatible": "incompatible",
    "incompatible": "compatible",
    "consistent_with": "inconsistent_with",
    "inconsistent_with": "consistent_with",
    "allows": "forbids",
    "forbids": "allows",
    "enables": "prevents",
    "prevents": "enables",
    "requires": "excludes",
    "excludes": "requires",
}

RELATION_GROUPS = {
    "positive": ["activates", "upregulates", "increases", "promotes", "induces", "stimulates",
                  "enhances", "supports", "predicts", "confirms", "validates", "compatible",
                  "consistent_with", "allows", "enables", "requires"],
    "negative": ["inhibits", "downregulates", "suppresses", "blocks", "reduces", "decreases",
                  "represses", "contradicts", "refutes", "challenges", "invalidates",
                  "incompatible", "inconsistent_with", "forbids", "prevents", "excludes"],
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

        # Also find scientific tensions (competing theories, conflicting evidence)
        tensions = self._find_scientific_tensions(g, entities, rels)
        contradictions.extend(tensions)

        scores = {c["id"]: c["severity"] for c in contradictions}
        summary = self._summarize(contradictions)

        return {"contradictions": contradictions, "severity_scores": scores, "summary": summary}

    def _find_scientific_tensions(self, graph, entities, rels):
        """Find scientific tensions — competing theories, conflicting evidence."""
        tensions = []

        # 1. Find entities with multiple competing explanations
        entity_types = {}
        for eid, edata in entities.items():
            etype = edata.get("type", "unknown")
            if etype not in entity_types:
                entity_types[etype] = []
            entity_types[etype].append(edata.get("name", ""))

        # 2. Find relationships that suggest tension
        # Look for entities connected to many others (potential competing explanations)
        connection_count = {}
        for r in rels:
            src = r.get("source", "")
            tgt = r.get("target", "")
            connection_count[src] = connection_count.get(src, 0) + 1
            connection_count[tgt] = connection_count.get(tgt, 0) + 1

        # Hub entities with many connections often have competing explanations
        hubs = [(name, count) for name, count in connection_count.items() if count >= 3]
        hubs.sort(key=lambda x: x[1], reverse=True)

        for hub_name, hub_count in hubs[:3]:
            # Find what connects to this hub
            connected = set()
            for r in rels:
                if r.get("source") == hub_name:
                    connected.add(r.get("target", ""))
                elif r.get("target") == hub_name:
                    connected.add(r.get("source", ""))

            if len(connected) >= 2:
                tensions.append({
                    "id": f"tension_hub_{hub_name.replace(' ', '_')}",
                    "type": "scientific_tension",
                    "entity_a": hub_name,
                    "entity_b": ", ".join(list(connected)[:3]),
                    "relation_a": "hub_connects",
                    "relation_b": "multiple_explanations",
                    "papers_a": [],
                    "papers_b": [],
                    "severity": 0.4,
                    "summary": f"'{hub_name}' is a hub entity connecting {len(connected)} other entities. "
                              f"This suggests competing explanations may exist for its role in the system.",
                    "tension_type": "competing_explanations",
                })

        # 3. Find entities with high degree that might have conflicting roles
        for eid, edata in entities.items():
            name = edata.get("name", "")
            papers = edata.get("papers", [])
            if len(papers) >= 2:
                # Check if this entity appears in multiple contexts
                contexts = set()
                for r in rels:
                    if r.get("source") == name or r.get("target") == name:
                        contexts.add(r.get("relation", ""))

                if len(contexts) >= 2:
                    tensions.append({
                        "id": f"tension_context_{name.replace(' ', '_')}",
                        "type": "contextual_tension",
                        "entity_a": name,
                        "entity_b": "multiple_contexts",
                        "relation_a": list(contexts)[0] if contexts else "unknown",
                        "relation_b": list(contexts)[1] if len(contexts) > 1 else "unknown",
                        "papers_a": papers[:2],
                        "papers_b": [],
                        "severity": 0.3,
                        "summary": f"'{name}' appears in {len(contexts)} different contexts ({', '.join(list(contexts)[:3])}). "
                                  f"This may indicate competing roles or explanations.",
                        "tension_type": "contextual_conflict",
                    })

        return tensions

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
        """Find cases where different papers disagree on the relationship between the same entities."""
        found = []
        # Group by (source, target) — NOT by (source, relation, target)
        # This lets us detect when different papers say different things about the same pair
        by_pair = defaultdict(list)
        for r in relationships:
            pair = (r.get("source"), r.get("target"))
            by_pair[pair].append(r)

        for pair, rels in by_pair.items():
            if len(rels) < 2:
                continue

            # Collect papers for each relation type on this pair
            rel_papers = defaultdict(set)
            for r in rels:
                papers = r.get("papers", [])
                if isinstance(papers, str):
                    papers = [papers]
                rel_type = r.get("relation", "")
                rel_papers[rel_type].update(papers)

            # Check if any two relations on this pair are opposites
            for rel_a, papers_a in rel_papers.items():
                for rel_b, papers_b in rel_papers.items():
                    if rel_a >= rel_b:  # avoid duplicates
                        continue
                    if OPPOSITE_RELATIONS.get(rel_a) == rel_b or \
                       _inverse_group(rel_a) and _inverse_group(rel_b) and _inverse_group(rel_a) != _inverse_group(rel_b):
                        # Papers disagree: some say rel_a, others say rel_b
                        # Only count if they come from different papers
                        overlap = papers_a & papers_b
                        only_a = papers_a - papers_b
                        only_b = papers_b - papers_a
                        if only_a or only_b:
                            severity = min(1.0, 0.4 + 0.05 * min(len(only_a) + len(overlap), len(only_b) + len(overlap)))
                            found.append({
                                "id": f"paper_{pair[0]}_{pair[1]}_{rel_a}_vs_{rel_b}",
                                "type": "paper",
                                "entity_a": pair[0],
                                "entity_b": pair[1],
                                "relation_a": rel_a,
                                "relation_b": rel_b,
                                "papers_a": list(papers_a),
                                "papers_b": list(papers_b),
                                "severity": severity,
                                "description": f"Papers disagree: {pair[0]} {rel_a} {pair[1]} (papers: {len(papers_a)}) BUT ALSO {rel_b} {pair[1]} (papers: {len(papers_b)})"
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
