"""
link_predictor.py — Predict missing relationships in the knowledge graph.

Inspired by PyKEEN's knowledge graph embedding approach, but lightweight.
Instead of training a full embedding model, uses graph topology to predict
what relationships SHOULD exist between entities.

Methods:
1. Common Neighbors — if A→C and B→C, maybe A→B
2. Jaccard Similarity — shared neighbors / total neighbors
3. Adamic-Adar — weighted common neighbors (rare neighbors matter more)
4. Path-based — if A→X→B exists, maybe A→B directly
5. Type-based — entities of similar types tend to have similar relationships

This fills the gap between "no relationship exists" and "relationship should exist"
— which is where discoveries hide.
"""

from collections import defaultdict, Counter
from typing import List, Dict, Tuple, Optional
import math


class LinkPredictor:
    """
    Predict missing relationships in knowledge graphs.
    """

    def __init__(self, graph=None):
        self.graph = graph

    def predict_missing_links(self, top_k: int = 10) -> dict:
        """
        Predict missing relationships between entities.

        Returns:
            {
                "predictions": [
                    {
                        "source": "entity_a",
                        "target": "entity_b",
                        "predicted_relation": "relation_type",
                        "confidence": 0.0-1.0,
                        "method": "common_neighbors|jaccard|adamic_adar|path_based|type_based",
                        "reasoning": "why this link should exist"
                    }
                ],
                "summary": {...}
            }
        """
        if not self.graph:
            return {"predictions": [], "summary": {"error": "No graph"}}

        entities = self.graph.entities if hasattr(self.graph, 'entities') else {}
        relationships = self.graph.relationships if hasattr(self.graph, 'relationships') else []

        if not entities or len(entities) < 3:
            return {"predictions": [], "summary": {"too_few_entities": True}}

        # Build adjacency
        adj = defaultdict(set)
        rel_map = {}
        for rel in relationships:
            adj[rel["source"]].add(rel["target"])
            adj[rel["target"]].add(rel["source"])
            rel_map[(rel["source"], rel["target"])] = rel

        # Run all prediction methods
        predictions = []

        # 1. Common Neighbors
        cn_preds = self._common_neighbors(entities, adj, rel_map)
        predictions.extend(cn_preds)

        # 2. Jaccard Similarity
        j_preds = self._jaccard_similarity(entities, adj, rel_map)
        predictions.extend(j_preds)

        # 3. Adamic-Adar
        aa_preds = self._adamic_adar(entities, adj, rel_map)
        predictions.extend(aa_preds)

        # 4. Path-based (2-hop paths without direct link)
        path_preds = self._path_based(entities, adj, rel_map)
        predictions.extend(path_preds)

        # 5. Type-based (entities of same type should be connected)
        type_preds = self._type_based(entities, adj, rel_map)
        predictions.extend(type_preds)

        # Deduplicate and rank
        seen = set()
        unique = []
        for pred in predictions:
            key = (pred["source"], pred["target"])
            if key not in seen:
                seen.add(key)
                unique.append(pred)

        unique.sort(key=lambda x: x["confidence"], reverse=True)
        top = unique[:top_k]

        return {
            "predictions": top,
            "summary": {
                "total_predicted": len(unique),
                "returned": len(top),
                "methods_used": list(set(p["method"] for p in unique)),
                "avg_confidence": sum(p["confidence"] for p in top) / max(1, len(top)),
            },
        }

    def _common_neighbors(self, entities: dict, adj: dict,
                          rel_map: dict) -> list:
        """
        If A and B share many common neighbors, they should be connected.
        Score = |N(A) ∩ N(B)|
        """
        predictions = []
        entity_ids = list(entities.keys())

        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                a, b = entity_ids[i], entity_ids[j]
                if b in adj.get(a, set()):
                    continue  # already connected

                common = adj.get(a, set()) & adj.get(b, set())
                if len(common) >= 2:
                    a_name = entities.get(a, {}).get("name", a)
                    b_name = entities.get(b, {}).get("name", b)
                    confidence = min(0.9, 0.3 + len(common) * 0.15)

                    predictions.append({
                        "source": a_name,
                        "target": b_name,
                        "predicted_relation": "associated_with",
                        "confidence": round(confidence, 3),
                        "method": "common_neighbors",
                        "common_neighbors_count": len(common),
                        "reasoning": f"'{a_name}' and '{b_name}' share {len(common)} common neighbors "
                                    f"but have no direct relationship. They should be connected.",
                    })

        return predictions

    def _jaccard_similarity(self, entities: dict, adj: dict,
                            rel_map: dict) -> list:
        """
        Jaccard = |N(A) ∩ N(B)| / |N(A) ∪ N(B)|
        High Jaccard = entities with similar connectivity patterns.
        """
        predictions = []
        entity_ids = list(entities.keys())

        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                a, b = entity_ids[i], entity_ids[j]
                if b in adj.get(a, set()):
                    continue

                neighbors_a = adj.get(a, set())
                neighbors_b = adj.get(b, set())

                if not neighbors_a or not neighbors_b:
                    continue

                intersection = neighbors_a & neighbors_b
                union = neighbors_a | neighbors_b
                jaccard = len(intersection) / len(union) if union else 0

                if jaccard > 0.3:
                    a_name = entities.get(a, {}).get("name", a)
                    b_name = entities.get(b, {}).get("name", b)

                    predictions.append({
                        "source": a_name,
                        "target": b_name,
                        "predicted_relation": "similar_to",
                        "confidence": round(min(0.85, jaccard), 3),
                        "method": "jaccard_similarity",
                        "jaccard_score": round(jaccard, 3),
                        "reasoning": f"'{a_name}' and '{b_name}' have Jaccard similarity {jaccard:.2f} "
                                    f"— they connect to similar entities and should be linked.",
                    })

        return predictions

    def _adamic_adar(self, entities: dict, adj: dict,
                     rel_map: dict) -> list:
        """
        Adamic-Adar = Σ 1/log|N(z)| for z in N(A) ∩ N(B)
        Rare shared neighbors are more significant than common ones.
        """
        predictions = []
        entity_ids = list(entities.keys())

        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                a, b = entity_ids[i], entity_ids[j]
                if b in adj.get(a, set()):
                    continue

                common = adj.get(a, set()) & adj.get(b, set())
                if not common:
                    continue

                aa_score = sum(1.0 / math.log(max(2, len(adj.get(z, set()))))
                              for z in common)

                if aa_score > 1.0:
                    a_name = entities.get(a, {}).get("name", a)
                    b_name = entities.get(b, {}).get("name", b)
                    confidence = min(0.85, aa_score / 5.0)

                    predictions.append({
                        "source": a_name,
                        "target": b_name,
                        "predicted_relation": "associated_with",
                        "confidence": round(confidence, 3),
                        "method": "adamic_adar",
                        "aa_score": round(aa_score, 3),
                        "reasoning": f"'{a_name}' and '{b_name}' share rare neighbors (AA={aa_score:.2f}), "
                                    f"suggesting a hidden connection.",
                    })

        return predictions

    def _path_based(self, entities: dict, adj: dict,
                    rel_map: dict) -> list:
        """
        If A→X→B exists but A→B doesn't, predict A→B.
        More 2-hop paths = stronger prediction.
        """
        predictions = []
        entity_ids = list(entities.keys())

        for a in entity_ids:
            for b in adj.get(a, set()):
                for c in adj.get(b, set()):
                    if c == a or c in adj.get(a, set()):
                        continue

                    # A→B→C exists but A→C doesn't
                    a_name = entities.get(a, {}).get("name", a)
                    c_name = entities.get(c, {}).get("name", c)
                    b_name = entities.get(b, {}).get("name", b)

                    rel_ab = rel_map.get((a, b), rel_map.get((b, a), {}))
                    rel_bc = rel_map.get((b, c), rel_map.get((c, b), {}))

                    predictions.append({
                        "source": a_name,
                        "target": c_name,
                        "predicted_relation": self._infer_relation(
                            rel_ab.get("relation", "?"),
                            rel_bc.get("relation", "?")
                        ),
                        "confidence": 0.4,
                        "method": "path_based",
                        "path": f"{a_name} → {b_name} → {c_name}",
                        "reasoning": f"Path exists: {a_name}--{rel_ab.get('relation', '?')}-->{b_name}--{rel_bc.get('relation', '?')}-->{c_name}, "
                                    f"but no direct link. Transitive relationship may exist.",
                    })

        # Deduplicate
        seen = set()
        unique = []
        for p in predictions:
            key = (p["source"], p["target"])
            if key not in seen:
                seen.add(key)
                unique.append(p)

        return unique[:8]

    def _type_based(self, entities: dict, adj: dict,
                    rel_map: dict) -> list:
        """
        Entities of the same type that aren't connected should be.
        E.g., two "phenomenon" entities in the same domain.
        """
        predictions = []

        # Group by type
        by_type = defaultdict(list)
        for eid, entity in entities.items():
            etype = entity.get("type", "unknown")
            if etype != "unknown":
                by_type[etype].append(eid)

        for etype, eids in by_type.items():
            if len(eids) < 2:
                continue

            for i in range(len(eids)):
                for j in range(i + 1, len(eids)):
                    a, b = eids[i], eids[j]
                    if b in adj.get(a, set()):
                        continue

                    a_name = entities.get(a, {}).get("name", a)
                    b_name = entities.get(b, {}).get("name", b)

                    predictions.append({
                        "source": a_name,
                        "target": b_name,
                        "predicted_relation": "related_to",
                        "confidence": 0.35,
                        "method": "type_based",
                        "shared_type": etype,
                        "reasoning": f"'{a_name}' and '{b_name}' are both '{etype}' entities "
                                    f"but have no relationship. Same-type entities are often connected.",
                    })

        return predictions[:5]

    def _infer_relation(self, rel_ab: str, rel_bc: str) -> str:
        """Infer what relation A→C should be given A→B and B→C."""
        # Simple transitive inference
        TRANSITIVE = {
            ("causes", "causes"): "causes",
            ("activates", "inhibits"): "modulates",
            ("inhibits", "activates"): "modulates",
            ("produces", "uses"): "enables",
            ("treats", "causes"): "associated_with",
            ("associated_with", "associated_with"): "associated_with",
        }
        return TRANSITIVE.get((rel_ab, rel_bc), "associated_with")
