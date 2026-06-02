"""
knowledge_gap_detector.py — Find what's MISSING in the knowledge graph.

Discovery starts with gaps: what is unexplained, what is disconnected,
what observations lack causal mechanisms. This module analyzes graph
structure to find:

1. Structural holes — disconnected clusters that should be connected
2. Orphan observations — entities with no causal explanation
3. Weak bridges — connections that exist but are poorly supported
4. Missing mechanisms — effects without causes, correlates without mechanisms
5. Explanation deficits — observations the literature acknowledges but can't explain

Inspired by:
  - Burt's Structural Holes theory (social network analysis)
  - Pat Langley's methodology for gap-driven discovery
  - DARPA Big Mechanism: building causal models from fragments
"""

import json
import math
from collections import defaultdict, Counter
from typing import List, Dict, Optional, Tuple


class KnowledgeGapDetector:
    """
    Algorithmic + LLM gap detection on knowledge graphs.
    Pure algorithmic where possible, LLM for semantic gap analysis.
    """

    def __init__(self, graph=None, llm_call=None):
        """
        Args:
            graph: KnowledgeGraph instance (discovery/graph.py)
            llm_call: callable(prompt, ...) for LLM calls. If None, algorithmic only.
        """
        self.graph = graph
        self.llm_call = llm_call

    def detect_gaps(self, topic: str = "", domain: str = "") -> dict:
        """
        Run all gap detection methods and return unified results.

        Returns:
            {
                "structural_holes": [...],
                "orphan_observations": [...],
                "weak_bridges": [...],
                "missing_mechanisms": [...],
                "explanation_deficits": [...],
                "summary": {...},
                "top_gaps": [...]  # ranked by importance
            }
        """
        if not self.graph:
            return {"error": "No graph provided", "top_gaps": []}

        entities = self.graph.entities if hasattr(self.graph, 'entities') else {}
        relationships = self.graph.relationships if hasattr(self.graph, 'relationships') else []
        papers = self.graph.papers if hasattr(self.graph, 'papers') else {}

        # Algorithmic analysis
        structural_holes = self._find_structural_holes(entities, relationships)
        orphan_observations = self._find_orphan_observations(entities, relationships)
        weak_bridges = self._find_weak_bridges(entities, relationships)
        missing_mechanisms = self._find_missing_mechanisms(entities, relationships)
        explanation_deficits = self._find_explanation_deficits(entities, relationships, papers)

        # Rank all gaps
        all_gaps = []
        for gap in structural_holes:
            all_gaps.append({**gap, "type": "structural_hole", "source": "algorithmic"})
        for gap in orphan_observations:
            all_gaps.append({**gap, "type": "orphan_observation", "source": "algorithmic"})
        for gap in weak_bridges:
            all_gaps.append({**gap, "type": "weak_bridge", "source": "algorithmic"})
        for gap in missing_mechanisms:
            all_gaps.append({**gap, "type": "missing_mechanism", "source": "algorithmic"})
        for gap in explanation_deficits:
            all_gaps.append({**gap, "type": "explanation_deficit", "source": "algorithmic"})

        # Score and rank
        for gap in all_gaps:
            gap["gap_score"] = self._score_gap(gap, entities, relationships)

        all_gaps.sort(key=lambda g: g["gap_score"], reverse=True)

        summary = {
            "total_gaps": len(all_gaps),
            "structural_holes": len(structural_holes),
            "orphan_observations": len(orphan_observations),
            "weak_bridges": len(weak_bridges),
            "missing_mechanisms": len(missing_mechanisms),
            "explanation_deficits": len(explanation_deficits),
            "avg_gap_score": sum(g["gap_score"] for g in all_gaps) / max(1, len(all_gaps)),
            "graph_density": self._compute_density(entities, relationships),
        }

        return {
            "structural_holes": structural_holes,
            "orphan_observations": orphan_observations,
            "weak_bridges": weak_bridges,
            "missing_mechanisms": missing_mechanisms,
            "explanation_deficits": explanation_deficits,
            "summary": summary,
            "top_gaps": all_gaps[:10],
        }

    def _find_structural_holes(self, entities: dict, relationships: list) -> list:
        """
        Find disconnected clusters that SHOULD be connected.
        
        Structural holes = gaps between densely connected subgraphs.
        In science, these often represent cross-disciplinary opportunities.

        Algorithm:
        1. Build adjacency graph
        2. Find connected components
        3. For each pair of components, check if they share entity types
        4. If they share types but no edges = structural hole
        """
        if not entities:
            return []

        # Build adjacency
        adj = defaultdict(set)
        for rel in relationships:
            adj[rel["source"]].add(rel["target"])
            adj[rel["target"]].add(rel["source"])

        # Find connected components (BFS)
        visited = set()
        components = []
        for eid in entities:
            if eid not in visited:
                component = set()
                queue = [eid]
                while queue:
                    node = queue.pop(0)
                    if node in visited:
                        continue
                    visited.add(node)
                    component.add(node)
                    for neighbor in adj.get(node, set()):
                        if neighbor not in visited:
                            queue.append(neighbor)
                components.append(component)

        if len(components) < 2:
            return []

        # For each pair of components, check for shared entity types
        holes = []
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                comp_a = components[i]
                comp_b = components[j]

                types_a = set()
                types_b = set()
                names_a = []
                names_b = []

                for eid in comp_a:
                    e = entities.get(eid, {})
                    types_a.add(e.get("type", "unknown"))
                    names_a.append(e.get("name", eid))

                for eid in comp_b:
                    e = entities.get(eid, {})
                    types_b.add(e.get("type", "unknown"))
                    names_b.append(e.get("name", eid))

                shared_types = types_a & types_b
                if shared_types:
                    # Structural hole: shared types but disconnected
                    holes.append({
                        "description": f"Disconnected clusters share types: {', '.join(shared_types)}",
                        "cluster_a": names_a[:5],
                        "cluster_b": names_b[:5],
                        "shared_types": list(shared_types),
                        "confidence": 0.7 + 0.05 * len(shared_types),
                        "reason": f"These {len(comp_a)} and {len(comp_b)} entities share type(s) "
                                  f"{', '.join(shared_types)} but have no connecting relationships. "
                                  f"This may indicate an unexplored cross-domain connection.",
                    })

        return holes[:5]  # Top 5 structural holes

    def _find_orphan_observations(self, entities: dict, relationships: list) -> list:
        """
        Find entities that appear in papers but have no causal/explanatory links.
        
        An orphan observation = something that was studied but never explained.
        These are often the starting points of major discoveries.
        
        Examples:
        - "galaxies rotate too fast" (observation, no mechanism)
        - "strange repeated DNA sequences" (observation, no function)
        """
        if not entities:
            return []

        # Build sets of entities that appear in relationships
        entities_in_rels = set()
        entity_causal_targets = set()  # entities that are EXPLAINED by something
        entity_causal_sources = set()  # entities that EXPLAIN something

        CAUSAL_RELATIONS = {
            "causes", "activates", "inhibits", "produces", "enables",
            "prevents", "induces", "triggers", "mediates", "regulates",
            "upregulates", "downregulates", "promotes", "suppresses",
        }

        for rel in relationships:
            entities_in_rels.add(rel["source"])
            entities_in_rels.add(rel["target"])
            if rel.get("relation", "").lower() in CAUSAL_RELATIONS:
                entity_causal_targets.add(rel["target"])
                entity_causal_sources.add(rel["source"])

        orphans = []
        for eid, entity in entities.items():
            name = entity.get("name", eid)
            etype = entity.get("type", "unknown")
            num_papers = len(entity.get("papers", []))

            # Check if entity is an observation without explanation
            if eid in entities and eid not in entity_causal_targets:
                # Entity exists but nothing explains it
                if etype in ("phenomenon", "disease", "disorder", "effect",
                             "observation", "anomaly", "symptom", "process"):
                    orphans.append({
                        "entity": name,
                        "entity_type": etype,
                        "papers": num_papers,
                        "confidence": min(0.9, 0.4 + 0.1 * num_papers),
                        "reason": f"'{name}' is a {etype} mentioned in {num_papers} paper(s) "
                                  f"but has no causal/explanatory mechanism in the graph. "
                                  f"It is observed but not explained.",
                    })

            # Check if entity has papers but zero relationships at all
            if eid not in entities_in_rels and num_papers > 0:
                if etype not in ("method", "technique", "tool", "concept"):
                    orphans.append({
                        "entity": name,
                        "entity_type": etype,
                        "papers": num_papers,
                        "confidence": 0.5 + 0.08 * num_papers,
                        "reason": f"'{name}' appears in {num_papers} paper(s) but has zero "
                                  f"relationships in the knowledge graph. It may represent "
                                  f"an isolated finding that needs causal integration.",
                    })

        orphans.sort(key=lambda x: x["confidence"], reverse=True)
        return orphans[:8]

    def _find_weak_bridges(self, entities: dict, relationships: list) -> list:
        """
        Find connections that exist but are poorly supported.
        
        A weak bridge = relationship supported by only 1 paper, or with low confidence.
        These are often preliminary findings that need more evidence,
        OR they represent genuinely novel connections that the field hasn't validated.
        """
        weak = []
        for rel in relationships:
            source_name = entities.get(rel["source"], {}).get("name", rel["source"])
            target_name = entities.get(rel["target"], {}).get("name", rel["target"])
            relation = rel.get("relation", "unknown")
            confidence = rel.get("confidence", 0.5)
            num_papers = len(rel.get("papers", []))

            if num_papers <= 1 or confidence < 0.4:
                weak.append({
                    "source": source_name,
                    "target": target_name,
                    "relation": relation,
                    "confidence": confidence,
                    "supporting_papers": num_papers,
                    "gap_score": 0.3 + (1.0 - confidence) * 0.4 + (1.0 / max(1, num_papers)) * 0.3,
                    "reason": f"The relationship '{source_name} --{relation}--> {target_name}' "
                              f"is supported by only {num_papers} paper(s) with confidence {confidence:.2f}. "
                              f"This is either a preliminary finding or a novel connection needing validation.",
                })

        weak.sort(key=lambda x: x["gap_score"], reverse=True)
        return weak[:6]

    def _find_missing_mechanisms(self, entities: dict, relationships: list) -> list:
        """
        Find effects without causes — the core of discovery.
        
        Pattern: "A and B are correlated, but no mechanism links them."
        This is exactly how dark matter was discovered:
          - Observation: galaxies rotate too fast
          - Gap: no mechanism explains the extra mass
          - Proposal: hidden mass (dark matter)
        """
        if not entities:
            return []

        # Build entity relation maps
        entity_rels = defaultdict(list)
        for rel in relationships:
            entity_rels[rel["source"]].append(rel)
            entity_rels[rel["target"]].append(rel)

        # Find entities that are targets of "correlates_with" or "associated_with"
        # but have no deeper causal mechanism
        SHALLOW_RELATIONS = {
            "correlates_with", "associated_with", "related_to",
            "linked_to", "connected_to", "co_occurs_with",
        }
        DEEP_RELATIONS = {
            "causes", "activates", "inhibits", "produces", "enables",
            "prevents", "induces", "triggers", "mediates", "regulates",
            "mechanism", "pathway", "upstream", "downstream",
        }

        missing = []
        for rel in relationships:
            if rel.get("relation", "").lower() in SHALLOW_RELATIONS:
                source_name = entities.get(rel["source"], {}).get("name", rel["source"])
                target_name = entities.get(rel["target"], {}).get("name", rel["target"])

                # Check if there's also a deeper mechanism
                has_deep = False
                for r2 in relationships:
                    if (r2["source"] == rel["source"] and r2["target"] == rel["target"] and
                            r2.get("relation", "").lower() in DEEP_RELATIONS):
                        has_deep = True
                        break

                if not has_deep:
                    missing.append({
                        "observation": f"{source_name} is associated with {target_name}",
                        "source_entity": source_name,
                        "target_entity": target_name,
                        "shallow_relation": rel.get("relation", "associated_with"),
                        "confidence": 0.6,
                        "reason": f"'{source_name}' and '{target_name}' are correlated/associated "
                                  f"but no causal mechanism connects them. This is a classic "
                                  f"discovery opportunity: propose a mechanism that explains WHY.",
                    })

        return missing[:6]

    def _find_explanation_deficits(self, entities: dict, relationships: list,
                                   papers: dict) -> list:
        """
        Use LLM to identify what the papers acknowledge as unexplained.
        
        Papers often say things like:
        - "The mechanism remains unclear"
        - "Further research is needed to explain"
        - "It is not yet understood why"
        - "The cause of X is unknown"
        
        These are goldmines for discovery.
        """
        if not papers or not self.llm_call:
            return []

        # Build paper context
        paper_text = ""
        for pmid, p in list(papers.items())[:10]:
            abstract = p.get("abstract", "")[:400]
            if abstract:
                paper_text += f"\n[{p.get('title', pmid)}] {abstract}\n"

        if not paper_text:
            return []

        prompt = f"""Analyze these scientific paper abstracts and identify what the authors 
acknowledge as UNEXPLAINED, UNKNOWN, or POORLY UNDERSTOOD.

Papers:
{paper_text}

For each gap found, output a JSON object with:
- "observation": what is observed but unexplained
- "acknowledged_by": which paper(s) acknowledge the gap  
- "importance": "high" | "medium" | "low"
- "reason": why this gap exists (missing mechanism? conflicting data? insufficient evidence?)

Output a JSON array of gaps. Be specific. Only include things the papers explicitly
acknowledge as gaps in understanding.

Example:
[{{"observation": "The mechanism by which X causes Y remains unclear", "acknowledged_by": "Paper Title", "importance": "high", "reason": "No causal pathway has been identified"}}]"""

        try:
            raw = self.llm_call(prompt, max_tokens=4096)
            if not raw:
                try:
                    from discovery.llm_client import call_json
                    raw = call_json(prompt, max_tokens=4096, provider="gemini")
                except Exception:
                    pass
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = json.loads(raw)
                else:
                    result = raw

                if isinstance(result, list):
                    for item in result:
                        item.setdefault("confidence", 0.7)
                        item.setdefault("source", "llm_analysis")
                    return result[:6]
        except Exception:
            pass

        return []

    def _score_gap(self, gap: dict, entities: dict, relationships: list) -> float:
        """
        Score a gap by its discovery potential.
        
        Higher score = more likely to lead to a genuine discovery.
        
        Factors:
        1. Type weight (structural holes > orphans > weak bridges)
        2. Confidence
        3. Number of papers involved (more papers = more important gap)
        4. Whether it involves unexplained phenomena
        """
        type_weights = {
            "structural_hole": 0.9,
            "orphan_observation": 0.85,
            "missing_mechanism": 0.95,
            "explanation_deficit": 0.8,
            "weak_bridge": 0.6,
        }

        type_score = type_weights.get(gap.get("type", ""), 0.5)
        confidence = gap.get("confidence", 0.5)
        papers = gap.get("papers", gap.get("supporting_papers", 1))
        paper_factor = min(1.0, math.log2(max(1, papers) + 1) / 4.0)

        # Bonus for "phenomenon" or "observation" entity types
        entity_type = gap.get("entity_type", "")
        phenomenon_bonus = 0.15 if entity_type in (
            "phenomenon", "disease", "disorder", "effect", "observation",
            "anomaly", "symptom", "process"
        ) else 0.0

        score = (type_score * 0.4 + confidence * 0.25 +
                 paper_factor * 0.2 + phenomenon_bonus + 0.05)

        return round(min(1.0, score), 3)

    def _compute_density(self, entities: dict, relationships: list) -> float:
        """Graph density: |E| / (|V| * (|V|-1) / 2)"""
        n = len(entities)
        if n < 2:
            return 0.0
        max_edges = n * (n - 1) / 2
        return round(len(relationships) / max_edges, 4) if max_edges > 0 else 0.0
