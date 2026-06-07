"""
anomaly_detector.py — Find observations that existing theories CANNOT explain.

Discovery almost always starts with anomalies:
  - Dark matter: galaxies rotate too fast (anomaly vs Newtonian prediction)
  - Plate tectonics: continents fit together (anomaly vs static Earth model)
  - CRISPR: strange repeated DNA sequences (anomaly — no known function)
  - Neutrino: missing energy in beta decay (anomaly vs conservation laws)

This module detects:
1. Statistical outliers in the knowledge graph
2. Conflicting evidence across papers
3. Prediction violations (expected vs observed relationships)
4. Entity anomalies (entities that don't fit their category)
5. Temporal anomalies (trends that reverse or contradict)
"""

import json
import math
from collections import defaultdict, Counter
from typing import List, Dict, Optional, Tuple
from discovery.json_extract import extract_json


class AnomalyDetector:
    """
    Detect anomalies in knowledge graphs that may indicate discovery opportunities.
    Combines algorithmic graph analysis with LLM-based semantic anomaly detection.
    """

    def __init__(self, graph=None, llm_call=None):
        self.graph = graph
        self.llm_call = llm_call

    def detect_anomalies(self, topic: str = "", domain: str = "") -> dict:
        """
        Run all anomaly detection methods.

        Returns:
            {
                "conflicting_evidence": [...],
                "outlier_entities": [...],
                "prediction_violations": [...],
                "category_anomalies": [...],
                "semantic_anomalies": [...],
                "summary": {...},
                "top_anomalies": [...]  # ranked by severity
            }
        """
        if not self.graph:
            return {"error": "No graph provided", "top_anomalies": []}

        entities = self.graph.entities if hasattr(self.graph, 'entities') else {}
        relationships = self.graph.relationships if hasattr(self.graph, 'relationships') else []
        papers = self.graph.papers if hasattr(self.graph, 'papers') else {}

        # Algorithmic detection
        conflicting = self._detect_conflicting_evidence(entities, relationships)
        outliers = self._detect_outlier_entities(entities, relationships)
        prediction_violations = self._detect_prediction_violations(entities, relationships)
        category_anomalies = self._detect_category_anomalies(entities, relationships)

        # LLM-based detection
        semantic_anomalies = []
        if self.llm_call and papers:
            semantic_anomalies = self._detect_semantic_anomalies(
                entities, relationships, papers, topic, domain
            )

        # Combine and rank
        all_anomalies = []
        for a in conflicting:
            all_anomalies.append({**a, "type": "conflicting_evidence"})
        for a in outliers:
            all_anomalies.append({**a, "type": "outlier_entity"})
        for a in prediction_violations:
            all_anomalies.append({**a, "type": "prediction_violation"})
        for a in category_anomalies:
            all_anomalies.append({**a, "type": "category_anomaly"})
        for a in semantic_anomalies:
            all_anomalies.append({**a, "type": "semantic_anomaly"})

        # Score anomalies
        for a in all_anomalies:
            a["anomaly_score"] = self._score_anomaly(a)

        # Filter out trivial anomalies — common words, not scientific concepts
        # Only filter truly generic words AND overly common scientific terms
        TRIVIAL_NAMES = {
            "model", "models", "data", "result", "results", "method", "methods",
            "analysis", "approach", "study", "system", "parameter", "value",
            "type", "form", "level", "way", "part", "case", "group", "point",
            "term", "work", "problem", "question", "information", "research",
            "field", "paper", "figure", "table", "section", "review",
            "et al", "abstract", "introduction", "conclusion", "discussion",
            "supplementary", "appendix", "reference", "author", "journal",
            # Generic scientific terms
            "emission", "radiation", "absorption", "scattering", "expansion",
            "observation", "detection", "measurement", "experiment",
            "theory", "model", "hypothesis", "framework", "dynamics",
            "interaction", "process", "mechanism", "effect", "phenomenon",
            "signal", "spectrum", "flux", "intensity", "luminosity",
        }
        filtered = []
        for a in all_anomalies:
            # Get the anomaly identifier — check multiple possible field names
            name = a.get("entity_name", a.get("name", a.get("entity", "")))
            if not name:
                name = a.get("reason", a.get("description", ""))
            name = name.lower().strip()
            if name in TRIVIAL_NAMES:
                continue
            if len(name) < 3:
                continue
            filtered.append(a)
        all_anomalies = filtered

        all_anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)

        summary = {
            "total_anomalies": len(all_anomalies),
            "conflicting_evidence": len(conflicting),
            "outlier_entities": len(outliers),
            "prediction_violations": len(prediction_violations),
            "category_anomalies": len(category_anomalies),
            "semantic_anomalies": len(semantic_anomalies),
            "avg_anomaly_score": (
                sum(a["anomaly_score"] for a in all_anomalies) / max(1, len(all_anomalies))
            ),
        }

        return {
            "conflicting_evidence": conflicting,
            "outlier_entities": outliers,
            "prediction_violations": prediction_violations,
            "category_anomalies": category_anomalies,
            "semantic_anomalies": semantic_anomalies,
            "summary": summary,
            "top_anomalies": all_anomalies[:10],
        }

    def _detect_conflicting_evidence(self, entities: dict,
                                      relationships: list) -> list:
        """
        Find entity pairs with contradictory relationships.
        
        E.g., "X activates Y" AND "X inhibits Y" from different papers.
        This is a strong anomaly signal — one of the papers must be wrong,
        OR there's a hidden variable that explains both.
        """
        OPPOSITES = {
            "activates": "inhibits", "inhibits": "activates",
            "increases": "decreases", "decreases": "increases",
            "promotes": "suppresses", "suppresses": "promotes",
            "upregulates": "downregulates", "downregulates": "upregulates",
            "causes": "prevents", "prevents": "causes",
            "enables": "blocks", "blocks": "enables",
        }

        # Group relationships by (source, target)
        pair_rels = defaultdict(list)
        for rel in relationships:
            src = rel.get("source")
            tgt = rel.get("target")
            if src and tgt:
                pair_rels[(src, tgt)].append(rel)

        conflicts = []
        for (src, tgt), rels in pair_rels.items():
            relations = [r.get("relation", "").lower() for r in rels]

            for i, rel_a in enumerate(relations):
                for j, rel_b in enumerate(relations):
                    if i >= j:
                        continue
                    opposite = OPPOSITES.get(rel_a)
                    if opposite and rel_b == opposite:
                        src_name = entities.get(src, {}).get("name", src)
                        tgt_name = entities.get(tgt, {}).get("name", tgt)
                        papers_a = rels[i].get("papers", [])
                        papers_b = rels[j].get("papers", [])

                        conflicts.append({
                            "entity_a": src_name,
                            "entity_b": tgt_name,
                            "relation_a": rel_a,
                            "relation_b": rel_b,
                            "papers_a": papers_a[:3],
                            "papers_b": papers_b[:3],
                            "confidence": 0.85,
                            "reason": f"CONFLICT: '{src_name} {rel_a} {tgt_name}' "
                                      f"AND '{src_name} {rel_b} {tgt_name}' "
                                      f"from different papers. This contradiction is a discovery "
                                      f"signal: either one is wrong, OR a hidden variable (context, "
                                      f"condition, pathway) explains both.",
                        })

        return conflicts[:5]

    def _detect_outlier_entities(self, entities: dict,
                                 relationships: list) -> list:
        """
        Find entities whose connectivity is statistically unusual.
        
        Very high degree = potential hub/driver (important but may indicate
        hub bias in the literature)
        Very low degree but high paper count = understudied observation
        
        Uses z-score analysis on entity degrees.
        """
        if not entities:
            return []

        # Compute degrees
        degrees = defaultdict(int)
        for rel in relationships:
            src = rel.get("source")
            tgt = rel.get("target")
            if src:
                degrees[src] += 1
            if tgt:
                degrees[tgt] += 1

        # Compute z-scores
        all_degrees = [degrees.get(eid, 0) for eid in entities]
        if len(all_degrees) < 3:
            return []

        mean_d = sum(all_degrees) / len(all_degrees)
        variance = sum((d - mean_d) ** 2 for d in all_degrees) / len(all_degrees)
        std_d = math.sqrt(variance) if variance > 0 else 1.0

        outliers = []
        for eid, entity in entities.items():
            degree = degrees.get(eid, 0)
            papers = len(entity.get("papers", []))
            z_score = (degree - mean_d) / std_d if std_d > 0 else 0

            # High z-score = outlier
            if abs(z_score) > 1.5:
                name = entity.get("name", eid)
                etype = entity.get("type", "unknown")

                if z_score > 1.5:
                    # Hub entity — over-connected
                    outliers.append({
                        "entity": name,
                        "entity_type": etype,
                        "degree": degree,
                        "papers": papers,
                        "z_score": round(z_score, 2),
                        "anomaly_direction": "hub",
                        "confidence": min(0.9, 0.5 + abs(z_score) * 0.1),
                        "reason": f"'{name}' has degree {degree} (z={z_score:.1f}), "
                                  f"much higher than average ({mean_d:.1f}). "
                                  f"It's a hub — either a genuine driver or an over-studied entity.",
                    })
                elif z_score < -1.5 and papers > 1:
                    # Low degree but mentioned in papers = isolated finding
                    outliers.append({
                        "entity": name,
                        "entity_type": etype,
                        "degree": degree,
                        "papers": papers,
                        "z_score": round(z_score, 2),
                        "anomaly_direction": "isolated",
                        "confidence": min(0.85, 0.4 + papers * 0.08),
                        "reason": f"'{name}' appears in {papers} papers but has only {degree} "
                                  f"relationships (z={z_score:.1f}). It's studied but not "
                                  f"integrated — a potential discovery waiting to be connected.",
                    })

        outliers.sort(key=lambda x: abs(x["z_score"]), reverse=True)
        return outliers[:6]

    def _detect_prediction_violations(self, entities: dict,
                                       relationships: list) -> list:
        """
        Find cases where expected relationships are MISSING.
        
        If A→B and B→C exist, we'd expect some relationship A→C.
        If it's missing, that's a prediction violation.
        
        Also: if entity types typically have certain relationships but 
        specific instances don't, that's anomalous.
        """
        violations = []

        # Build type relationship expectations
        type_rel_counts = defaultdict(lambda: defaultdict(int))
        for rel in relationships:
            src = rel.get("source")
            tgt = rel.get("target")
            if not src or not tgt:
                continue
            src_type = entities.get(src, {}).get("type", "unknown")
            tgt_type = entities.get(tgt, {}).get("type", "unknown")
            type_rel_counts[(src_type, tgt_type)][rel.get("relation", "unknown")] += 1

        # For each entity pair connected by a path of length 2,
        # check if there's a direct connection
        adj = defaultdict(set)
        rel_map = {}
        for rel in relationships:
            src = rel.get("source")
            tgt = rel.get("target")
            if src and tgt:
                adj[src].add(tgt)
                rel_map[(src, tgt)] = rel

        # Find transitive gaps (A→B→C but no A→C)
        checked = set()
        for b in entities:
            for a in adj.get(b, set()):
                for c in adj.get(b, set()):
                    if a == c or (a, c) in checked:
                        continue
                    checked.add((a, c))

                    if c not in adj.get(a, set()):
                        # A→B→C exists but A→C doesn't
                        a_name = entities.get(a, {}).get("name", a)
                        b_name = entities.get(b, {}).get("name", b)
                        c_name = entities.get(c, {}).get("name", c)
                        rel_ab = rel_map.get((a, b), {}).get("relation", "?")
                        rel_bc = rel_map.get((b, c), {}).get("relation", "?")

                        violations.append({
                            "entity_a": a_name,
                            "entity_b": b_name,
                            "entity_c": c_name,
                            "path": f"{a_name} --{rel_ab}--> {b_name} --{rel_bc}--> {c_name}",
                            "missing_direct": f"{a_name} → {c_name}",
                            "confidence": 0.5,
                            "reason": f"There's a path {a_name}→{b_name}→{c_name} but no direct "
                                      f"connection. Either the direct link doesn't exist (novel finding) "
                                      f"or it hasn't been studied yet.",
                        })

        # Deduplicate and limit
        seen = set()
        unique = []
        for v in violations:
            key = (v["entity_a"], v["entity_c"])
            if key not in seen:
                seen.add(key)
                unique.append(v)

        unique.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return unique[:5]

    def _detect_category_anomalies(self, entities: dict,
                                    relationships: list) -> list:
        """
        Find entities that behave differently from others in their type.
        
        E.g., a "protein" that has relationships normally seen in "drugs",
        or a "phenomenon" that's described like a "mechanism".
        """
        anomalies = []

        # Build type profiles
        type_profiles = defaultdict(lambda: {"relation_types": Counter(), "neighbor_types": Counter()})
        for rel in relationships:
            rel_src = rel.get("source")
            rel_tgt = rel.get("target")
            if not rel_src or not rel_tgt:
                continue
            src = entities.get(rel_src, {})
            tgt = entities.get(rel_tgt, {})
            src_type = src.get("type", "unknown")
            tgt_type = tgt.get("type", "unknown")
            relation = rel.get("relation", "unknown")

            type_profiles[src_type]["relation_types"][relation] += 1
            type_profiles[src_type]["neighbor_types"][tgt_type] += 1
            type_profiles[tgt_type]["relation_types"][relation] += 1
            type_profiles[tgt_type]["neighbor_types"][src_type] += 1

        # For each entity, check if its profile matches its type
        for eid, entity in entities.items():
            etype = entity.get("type", "unknown")
            if etype == "unknown" or etype not in type_profiles:
                continue

            # Get this entity's actual profile
            entity_relations = Counter()
            entity_neighbors = Counter()
            for rel in relationships:
                rel_src = rel.get("source")
                rel_tgt = rel.get("target")
                if rel_src == eid:
                    entity_relations[rel.get("relation", "?")] += 1
                    entity_neighbors[entities.get(rel_tgt, {}).get("type", "?")] += 1
                elif rel_tgt == eid:
                    entity_relations[rel.get("relation", "?")] += 1
                    entity_neighbors[entities.get(rel_src, {}).get("type", "?")] += 1

            if not entity_relations:
                continue

            # Check for unusual relation types for this entity type
            typical_relations = set(type_profiles[etype]["relation_types"].keys())
            entity_rel_types = set(entity_relations.keys())
            unusual_rels = entity_rel_types - typical_relations

            if unusual_rels and len(entity_relations) >= 2:
                name = entity.get("name", eid)
                anomalies.append({
                    "entity": name,
                    "entity_type": etype,
                    "unusual_relations": list(unusual_rels),
                    "confidence": 0.55,
                    "reason": f"'{name}' (type: {etype}) has relation type(s) "
                              f"{', '.join(unusual_rels)} which are atypical for {etype} entities. "
                              f"This may indicate a novel role or misclassification.",
                })

        anomalies.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return anomalies[:4]

    def _detect_semantic_anomalies(self, entities: dict, relationships: list,
                                    papers: dict, topic: str, domain: str) -> list:
        """
        Use LLM to find semantic anomalies in the literature.
        
        These are cases where the PAPERS themselves acknowledge something weird:
        - "Unexpectedly..."
        - "Surprisingly..."
        - "Contrary to expectations..."
        - "The result was inconsistent with..."
        """
        paper_text = ""
        for pmid, p in list(papers.items())[:8]:
            abstract = p.get("abstract", "")[:400]
            title = p.get("title", "")
            if abstract:
                paper_text += f"\n[{title}] {abstract}\n"

        if not paper_text:
            return []

        prompt = f"""Analyze these scientific papers and find ANOMALIES — observations that
the authors found surprising, unexpected, or inconsistent with existing theory.

Topic: {topic}
Domain: {domain}

Papers:
{paper_text}

For each anomaly found, output a JSON object:
- "observation": the surprising finding
- "paper_source": which paper reported it
- "expected": what existing theory predicted
- "observed": what was actually found  
- "potential_explanation": what might explain the anomaly
- "importance": "high" | "medium" | "low"

Output a JSON array. Only include genuinely surprising findings.

Example:
[{{"observation": "Drug X increased cancer growth instead of inhibiting it", "paper_source": "Smith et al.", "expected": "inhibition", "observed": "promotion", "potential_explanation": "dual pathway activation", "importance": "high"}}]"""

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
                    result = extract_json(raw)
                else:
                    result = raw

                if isinstance(result, list):
                    for item in result:
                        item.setdefault("confidence", 0.7)
                        item.setdefault("source", "llm_analysis")
                    return result[:5]
        except Exception:
            pass

        return []

    def _score_anomaly(self, anomaly: dict) -> float:
        """
        Score anomaly severity.
        
        Higher = more likely to represent a genuine discovery opportunity.
        
        Factors:
        1. Type weight (conflicting evidence > prediction violations > outliers)
        2. Confidence
        3. Whether it involves a contradiction
        """
        type_weights = {
            "conflicting_evidence": 0.95,
            "prediction_violation": 0.7,
            "outlier_entity": 0.65,
            "category_anomaly": 0.5,
            "semantic_anomaly": 0.85,
        }

        type_score = type_weights.get(anomaly.get("type", ""), 0.5)
        confidence = anomaly.get("confidence", 0.5)
        z_bonus = min(0.2, abs(anomaly.get("z_score", 0)) * 0.05) if "z_score" in anomaly else 0

        score = type_score * 0.5 + confidence * 0.3 + z_bonus + 0.1
        return round(min(1.0, score), 3)
