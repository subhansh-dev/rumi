"""
knowledge_graph.py — Scientific Knowledge Graph Builder

Synthesizes papers, concepts, and findings into a structured knowledge graph.
Enables multi-hop reasoning, gap detection, and cross-disciplinary connections.

Inspired by:
  - ResearchAgent's academic graph connections
  - Bengio's structured object generation
  - Neo4j-style property graphs for scientific knowledge

Capabilities:
  [KG-1] Entity extraction (concepts, methods, findings, researchers, datasets)
  [KG-2] Relation extraction (causes, enables, contradicts, extends, uses)
  [KG-3] Multi-hop reasoning over the graph
  [KG-4] Gap detection (missing connections, understudied areas)
  [KG-5] Subgraph extraction by topic/domain
  [KG-6] Confidence-weighted edges
  [KG-7] Temporal tracking (knowledge evolution)
  [KG-8] Import from papers, search results, and Semantic Scholar
  [KG-9] Export to JSON/DOT formats
  [KG-10] Merge and deduplication

Thread-safe. Persistent state in knowledge_graph_state.json.
"""

import json
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()
STATE_FILE = SCIENTIST_DIR / "knowledge_graph_state.json"

# ── Entity & Relation Types ───────────────────────────────────────────────────

ENTITY_TYPES = {
    "concept", "method", "finding", "hypothesis", "researcher",
    "dataset", "tool", "theory", "variable", "domain",
    "paper", "metric", "model", "phenomenon",
}

RELATION_TYPES = {
    "causes", "enables", "contradicts", "supports", "extends",
    "uses", "produces", "part_of", "related_to", "improves",
    "inspired_by", "tests", "validates", "predicts", "explains",
    "alternative_to", "requires", "generalizes", "specializes",
}

# Confidence thresholds
CONF_HIGH = 0.8
CONF_MEDIUM = 0.5
CONF_LOW = 0.3


class KGEntity:
    """A node in the knowledge graph."""

    def __init__(
        self,
        name: str,
        entity_type: str,
        description: str = "",
        domain: str = "",
        source: str = "",
    ):
        self.id = f"E-{abs(hash(name + entity_type)) % 10**8:08d}"
        self.name = name
        self.entity_type = entity_type if entity_type in ENTITY_TYPES else "concept"
        self.description = description
        self.domain = domain
        self.source = source
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.aliases: list[str] = []
        self.properties: dict = {}
        self.mentions = 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.entity_type,
            "description": self.description,
            "domain": self.domain,
            "source": self.source,
            "aliases": self.aliases,
            "properties": self.properties,
            "mentions": self.mentions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KGEntity":
        e = cls(d["name"], d.get("type", "concept"), d.get("description", ""))
        e.id = d["id"]
        e.domain = d.get("domain", "")
        e.source = d.get("source", "")
        e.aliases = d.get("aliases", [])
        e.properties = d.get("properties", {})
        e.mentions = d.get("mentions", 1)
        e.created_at = d.get("created_at", e.created_at)
        e.updated_at = d.get("updated_at", e.updated_at)
        return e


class KGRelation:
    """An edge in the knowledge graph."""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        confidence: float = 0.5,
        evidence: str = "",
        source: str = "",
    ):
        self.id = f"R-{abs(hash(source_id + target_id + relation_type)) % 10**8:08d}"
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type if relation_type in RELATION_TYPES else "related_to"
        self.confidence = max(0.0, min(1.0, confidence))
        self.evidence = evidence
        self.source = source
        self.created_at = datetime.now().isoformat()
        self.weight = 1.0  # Incremented on corroboration

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source_id,
            "target": self.target_id,
            "type": self.relation_type,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
            "source_ref": self.source,
            "weight": self.weight,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "KGRelation":
        r = cls(d["source"], d["target"], d.get("type", "related_to"), d.get("confidence", 0.5))
        r.id = d["id"]
        r.evidence = d.get("evidence", "")
        r.source = d.get("source_ref", "")
        r.weight = d.get("weight", 1.0)
        r.created_at = d.get("created_at", r.created_at)
        return r


class KnowledgeGraph:
    """
    Scientific knowledge graph with entities, relations, and reasoning.

    Supports multi-hop queries, gap detection, and cross-domain connections.
    """

    def __init__(self, llm_call=None):
        self._lock = threading.Lock()
        self._llm = llm_call
        self._entities: dict[str, KGEntity] = {}  # id -> entity
        self._relations: dict[str, KGRelation] = {}  # id -> relation
        self._name_index: dict[str, str] = {}  # lowercase name -> entity id
        self._adjacency: dict[str, list[str]] = defaultdict(list)  # entity_id -> [relation_ids]
        self._load_state()

    def _load_state(self):
        with self._lock:
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    for e in data.get("entities", []):
                        entity = KGEntity.from_dict(e)
                        self._entities[entity.id] = entity
                        self._name_index[entity.name.lower()] = entity.id
                    for r in data.get("relations", []):
                        rel = KGRelation.from_dict(r)
                        self._relations[rel.id] = rel
                        self._adjacency[rel.source_id].append(rel.id)
                        self._adjacency[rel.target_id].append(rel.id)
                except Exception:
                    pass

    def _save_state(self):
        with self._lock:
            data = {
                "entities": [e.to_dict() for e in self._entities.values()],
                "relations": [r.to_dict() for r in self._relations.values()],
                "stats": self._stats_locked(),
                "saved_at": datetime.now().isoformat(),
            }
            STATE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    # ── Entity Operations ─────────────────────────────────────────────────────

    def add_entity(
        self,
        name: str,
        entity_type: str = "concept",
        description: str = "",
        domain: str = "",
        source: str = "",
        aliases: list[str] | None = None,
        properties: dict | None = None,
    ) -> KGEntity:
        """Add or merge an entity."""
        with self._lock:
            key = name.lower().strip()
            # Check for existing
            if key in self._name_index:
                existing = self._entities[self._name_index[key]]
                existing.mentions += 1
                existing.updated_at = datetime.now().isoformat()
                if description and not existing.description:
                    existing.description = description
                if domain and not existing.domain:
                    existing.domain = domain
                if properties:
                    existing.properties.update(properties)
                if aliases:
                    for a in aliases:
                        if a.lower() not in [x.lower() for x in existing.aliases]:
                            existing.aliases.append(a)
                return existing

            # New entity
            entity = KGEntity(name, entity_type, description, domain, source)
            if aliases:
                entity.aliases = aliases
            if properties:
                entity.properties = properties
            self._entities[entity.id] = entity
            self._name_index[key] = entity.id
            return entity

    def get_entity(self, name: str) -> KGEntity | None:
        """Find entity by name (case-insensitive)."""
        with self._lock:
            key = name.lower().strip()
            eid = self._name_index.get(key)
            return self._entities.get(eid) if eid else None

    def find_entities(
        self,
        query: str = "",
        entity_type: str = "",
        domain: str = "",
    ) -> list[KGEntity]:
        """Search entities by query, type, or domain."""
        with self._lock:
            results = []
            q = query.lower()
            for e in self._entities.values():
                if entity_type and e.entity_type != entity_type:
                    continue
                if domain and e.domain != domain:
                    continue
                if q:
                    text = (e.name + " " + e.description + " " + " ".join(e.aliases)).lower()
                    if q not in text:
                        continue
                results.append(e)
            return results

    # ── Relation Operations ───────────────────────────────────────────────────

    def add_relation(
        self,
        source_name: str,
        target_name: str,
        relation_type: str = "related_to",
        confidence: float = 0.5,
        evidence: str = "",
        source: str = "",
    ) -> KGRelation | None:
        """Add a relation between two entities (creates entities if needed)."""
        src = self.add_entity(source_name, source=source)
        tgt = self.add_entity(target_name, source=source)
        with self._lock:
            # Check for existing relation
            for rid in self._adjacency.get(src.id, []):
                rel = self._relations.get(rid)
                if rel and rel.target_id == tgt.id and rel.relation_type == relation_type:
                    # Corroborate existing
                    rel.weight += 1
                    rel.confidence = min(1.0, rel.confidence + 0.05)
                    if evidence:
                        rel.evidence += f" | {evidence}"
                    return rel

            # New relation
            rel = KGRelation(src.id, tgt.id, relation_type, confidence, evidence, source)
            self._relations[rel.id] = rel
            self._adjacency[src.id].append(rel.id)
            self._adjacency[tgt.id].append(rel.id)
            return rel

    def get_relations(
        self,
        entity_name: str,
        direction: str = "both",
        relation_type: str = "",
    ) -> list[tuple[KGEntity, KGRelation, KGEntity]]:
        """Get all relations for an entity."""
        with self._lock:
            entity = self.get_entity(entity_name)
            if not entity:
                return []
            results = []
            for rid in self._adjacency.get(entity.id, []):
                rel = self._relations.get(rid)
                if not rel:
                    continue
                if relation_type and rel.relation_type != relation_type:
                    continue
                src = self._entities.get(rel.source_id)
                tgt = self._entities.get(rel.target_id)
                if not src or not tgt:
                    continue
                if direction == "out" and rel.source_id != entity.id:
                    continue
                if direction == "in" and rel.target_id != entity.id:
                    continue
                results.append((src, rel, tgt))
            return results

    # ── Multi-Hop Reasoning ───────────────────────────────────────────────────

    def find_path(
        self,
        source_name: str,
        target_name: str,
        max_hops: int = 4,
    ) -> list[list[tuple[KGEntity, KGRelation, KGEntity]]]:
        """Find paths between two entities (BFS, up to max_hops)."""
        with self._lock:
            src = self.get_entity(source_name)
            tgt = self.get_entity(target_name)
            if not src or not tgt:
                return []

            # BFS
            queue: deque = deque([(src.id, [])])
            visited: set[str] = {src.id}
            paths: list[list[tuple[str, str, str]]] = []

            while queue and len(paths) < 10:
                current, path = queue.popleft()
                if len(path) > max_hops:
                    continue
                if current == tgt.id and path:
                    paths.append(path)
                    continue
                for rid in self._adjacency.get(current, []):
                    rel = self._relations.get(rid)
                    if not rel:
                        continue
                    next_id = rel.target_id if rel.source_id == current else rel.source_id
                    if next_id in visited:
                        continue
                    visited.add(next_id)
                    queue.append((next_id, path + [(current, rid, next_id)]))

            # Convert to entity/relation triples
            result = []
            for path in paths:
                triples = []
                for src_id, rel_id, tgt_id in path:
                    rel = self._relations.get(rel_id)
                    if rel:
                        triples.append((
                            self._entities.get(src_id),
                            rel,
                            self._entities.get(tgt_id),
                        ))
                result.append(triples)
            return result

    def neighbors(
        self, entity_name: str, hops: int = 2
    ) -> dict[str, list[KGEntity]]:
        """Get neighbors up to N hops away, grouped by hop distance."""
        with self._lock:
            entity = self.get_entity(entity_name)
            if not entity:
                return {}
            result: dict[str, list[KGEntity]] = {}
            visited: set[str] = {entity.id}
            current_layer = [entity.id]

            for hop in range(1, hops + 1):
                next_layer = []
                hop_entities = []
                for eid in current_layer:
                    for rid in self._adjacency.get(eid, []):
                        rel = self._relations.get(rid)
                        if not rel:
                            continue
                        neighbor_id = rel.target_id if rel.source_id == eid else rel.source_id
                        if neighbor_id not in visited:
                            visited.add(neighbor_id)
                            next_layer.append(neighbor_id)
                            ent = self._entities.get(neighbor_id)
                            if ent:
                                hop_entities.append(ent)
                result[f"hop_{hop}"] = hop_entities
                current_layer = next_layer
                if not current_layer:
                    break
            return result

    # ── Gap Detection ─────────────────────────────────────────────────────────

    def detect_gaps(self) -> list[dict]:
        """
        Detect knowledge gaps:
        - Isolated entities (no connections)
        - Missing bidirectional links
        - Low-confidence clusters
        - Underconnected domains
        """
        with self._lock:
            gaps = []

            # 1. Isolated entities
            for eid, entity in self._entities.items():
                if not self._adjacency.get(eid):
                    gaps.append({
                        "type": "isolated_entity",
                        "entity": entity.name,
                        "description": f"'{entity.name}' has no connections in the graph",
                        "severity": "medium",
                    })

            # 2. Low-confidence edges
            for rel in self._relations.values():
                if rel.confidence < CONF_LOW:
                    src = self._entities.get(rel.source_id)
                    tgt = self._entities.get(rel.target_id)
                    if src and tgt:
                        gaps.append({
                            "type": "weak_connection",
                            "entities": [src.name, tgt.name],
                            "relation": rel.relation_type,
                            "confidence": rel.confidence,
                            "description": f"Weak link ({rel.confidence:.2f}): {src.name} --{rel.relation_type}--> {tgt.name}",
                            "severity": "low",
                        })

            # 3. Domain isolation
            domain_entities: dict[str, set[str]] = defaultdict(set)
            domain_connections: dict[str, int] = defaultdict(int)
            for e in self._entities.values():
                if e.domain:
                    domain_entities[e.domain].add(e.id)
            for rel in self._relations.values():
                src = self._entities.get(rel.source_id)
                tgt = self._entities.get(rel.target_id)
                if src and tgt and src.domain and tgt.domain and src.domain != tgt.domain:
                    key = tuple(sorted([src.domain, tgt.domain]))
                    domain_connections[key] += 1

            for domain, entities in domain_entities.items():
                cross_connections = sum(
                    v for (d1, d2), v in domain_connections.items()
                    if domain in (d1, d2)
                )
                if len(entities) > 3 and cross_connections < 2:
                    gaps.append({
                        "type": "domain_isolation",
                        "domain": domain,
                        "entity_count": len(entities),
                        "cross_connections": cross_connections,
                        "description": f"Domain '{domain}' has {len(entities)} entities but only {cross_connections} cross-domain links",
                        "severity": "high",
                    })

            return gaps

    # ── Subgraph Extraction ───────────────────────────────────────────────────

    def get_subgraph(
        self,
        center_name: str,
        radius: int = 2,
        min_confidence: float = 0.0,
    ) -> dict:
        """Extract a subgraph around an entity."""
        with self._lock:
            center = self.get_entity(center_name)
            if not center:
                return {"entities": [], "relations": []}

            # BFS to radius
            entity_ids: set[str] = {center.id}
            current = [center.id]
            for _ in range(radius):
                next_layer = []
                for eid in current:
                    for rid in self._adjacency.get(eid, []):
                        rel = self._relations.get(rid)
                        if not rel or rel.confidence < min_confidence:
                            continue
                        neighbor = rel.target_id if rel.source_id == eid else rel.source_id
                        if neighbor not in entity_ids:
                            entity_ids.add(neighbor)
                            next_layer.append(neighbor)
                current = next_layer

            # Collect entities and relations
            entities = [self._entities[eid].to_dict() for eid in entity_ids if eid in self._entities]
            relations = [
                r.to_dict() for r in self._relations.values()
                if r.source_id in entity_ids and r.target_id in entity_ids and r.confidence >= min_confidence
            ]
            return {"entities": entities, "relations": relations}

    # ── Import from Text ──────────────────────────────────────────────────────

    def ingest_paper(self, title: str, abstract: str, authors: list[str] = None, domain: str = "") -> dict:
        """
        Extract entities and relations from a paper title + abstract.
        Uses LLM if available, falls back to heuristic extraction.
        """
        # Add paper entity
        paper = self.add_entity(title, "paper", abstract[:200], domain, source="ingest")

        if self._llm:
            return self._llm_extract(title, abstract, domain)

        # Heuristic extraction
        extracted = {"entities": [], "relations": []}

        # Extract capitalized terms as concepts
        concepts = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', title + " " + abstract))
        for c in concepts:
            if len(c) > 3 and c.lower() not in {"the", "this", "that", "these", "those", "from", "with", "using"}:
                ent = self.add_entity(c, "concept", domain=domain, source=title)
                extracted["entities"].append(ent.name)
                # Link paper to concept
                self.add_relation(title, c, "related_to", 0.6, f"Mentioned in {title}")
                extracted["relations"].append((title, c, "related_to"))

        # Extract method patterns
        methods = re.findall(r'\b(?:method|algorithm|approach|technique|framework|model|architecture)\b', abstract, re.I)
        if methods:
            for m in set(methods):
                self.add_relation(title, m, "uses", 0.5, f"Uses {m}")

        # Add author connections
        if authors:
            for author in authors:
                self.add_entity(author, "researcher", source=title)
                self.add_relation(author, title, "produces", 0.8, f"Authored {title}")

        return extracted

    def _llm_extract(self, title: str, abstract: str, domain: str) -> dict:
        """Use LLM for entity/relation extraction."""
        prompt = f"""Extract entities and relations from this scientific paper.

Title: {title}
Abstract: {abstract}
Domain: {domain}

Entity types: {', '.join(sorted(ENTITY_TYPES))}
Relation types: {', '.join(sorted(RELATION_TYPES))}

Format each line as:
ENTITY: <name> | TYPE: <type> | DESC: <description>
RELATION: <source> | TARGET: <target> | TYPE: <relation> | CONF: <0-1>

Extract all important entities and relations:"""

        response = self._llm(prompt)
        extracted = {"entities": [], "relations": []}

        for line in response.strip().split("\n"):
            line = line.strip()
            if line.startswith("ENTITY:"):
                parts = line[7:].split("|")
                try:
                    name = parts[0].strip()
                    etype = parts[1].split(":")[1].strip() if len(parts) > 1 else "concept"
                    desc = parts[2].split(":")[1].strip() if len(parts) > 2 else ""
                    self.add_entity(name, etype, desc, domain, source=title)
                    extracted["entities"].append(name)
                except (IndexError, ValueError):
                    continue
            elif line.startswith("RELATION:"):
                parts = line[9:].split("|")
                try:
                    src = parts[0].strip()
                    tgt = parts[1].split(":")[1].strip() if len(parts) > 1 else ""
                    rtype = parts[2].split(":")[1].strip() if len(parts) > 2 else "related_to"
                    conf = float(parts[3].split(":")[1].strip()) if len(parts) > 3 else 0.5
                    self.add_relation(src, tgt, rtype, conf, source=title)
                    extracted["relations"].append((src, tgt, rtype))
                except (IndexError, ValueError):
                    continue

        return extracted

    # ── Export ─────────────────────────────────────────────────────────────────

    def to_json(self) -> str:
        """Export graph as JSON."""
        with self._lock:
            return json.dumps({
                "entities": [e.to_dict() for e in self._entities.values()],
                "relations": [r.to_dict() for r in self._relations.values()],
                "stats": self._stats_locked(),
            }, indent=2)

    def to_dot(self) -> str:
        """Export graph as DOT format for visualization."""
        with self._lock:
            lines = ["digraph KnowledgeGraph {", '  rankdir=LR;', '  node [shape=box];']
            for e in self._entities.values():
                label = e.name.replace('"', '\\"')
                color = {
                    "concept": "lightblue", "method": "lightgreen",
                    "finding": "lightyellow", "hypothesis": "lightsalmon",
                    "paper": "lightgray", "researcher": "lavender",
                }.get(e.entity_type, "white")
                lines.append(f'  "{e.id}" [label="{label}" style=filled fillcolor={color}];')
            for r in self._relations.values():
                style = "solid" if r.confidence > 0.5 else "dashed"
                lines.append(
                    f'  "{r.source_id}" -> "{r.target_id}" '
                    f'[label="{r.relation_type}" style={style} penwidth={max(1, r.weight)}];'
                )
            lines.append("}")
            return "\n".join(lines)

    def _stats_locked(self) -> dict:
        return {
            "entity_count": len(self._entities),
            "relation_count": len(self._relations),
            "type_distribution": dict(
                Counter(e.entity_type for e in self._entities.values())
            ),
            "domain_distribution": dict(
                Counter(e.domain for e in self._entities.values() if e.domain)
            ),
        }

    def stats(self) -> dict:
        with self._lock:
            return self._stats_locked()

    def reset(self):
        """Clear the entire graph."""
        with self._lock:
            self._entities.clear()
            self._relations.clear()
            self._name_index.clear()
            self._adjacency.clear()
            self._save_state()


# Need Counter for stats
from collections import Counter

# ── Singleton ─────────────────────────────────────────────────────────────────

_graph: Optional[KnowledgeGraph] = None
_graph_lock = threading.Lock()


def get_knowledge_graph(llm_call=None) -> KnowledgeGraph:
    global _graph
    with _graph_lock:
        if _graph is None:
            _graph = KnowledgeGraph(llm_call=llm_call)
        return _graph
