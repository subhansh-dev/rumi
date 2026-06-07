import json
import time
from pathlib import Path
from collections import Counter

GRAPH_FILE = Path(__file__).resolve().parent.parent / "discovery" / "graph" / "knowledge_graph.json"

# Maximum entities to load from persistent graph (prevents unbounded growth)
MAX_PERSISTED_ENTITIES = 500
# Maximum age in seconds for persisted entities (default: 7 days)
ENTITY_MAX_AGE = 7 * 24 * 3600


class KnowledgeGraph:
    def __init__(self, persist=True, domain: str = ""):
        self.entities: dict[str, dict] = {}
        self.relationships: list[dict] = []
        self.papers: dict[str, dict] = {}
        self.domain: str = domain or "drug_discovery"
        self._session_count = 0
        self._run_id = f"run_{int(time.time())}"
        if persist:
            self._merge_previous()

    def add_paper_entities(self, entities: list[dict], pmid: str):
        for ent in entities:
            eid = f"{ent['type']}_{ent['name'].lower().replace(' ', '_')}"
            if eid not in self.entities:
                self.entities[eid] = {
                    "id": eid,
                    "type": ent["type"],
                    "name": ent["name"],
                    "aliases": ent.get("aliases", []),
                    "papers": [],
                    "domain": self.domain,
                    "source_run": self._run_id,
                    "created_at": time.time(),
                    "last_used": time.time(),
                }
            if pmid not in self.entities[eid]["papers"]:
                self.entities[eid]["papers"].append(pmid)
            self.entities[eid]["last_used"] = time.time()

    def add_relationships(self, relationships: list[dict], pmid: str):
        for rel in relationships:
            sid = f"{rel['source_type']}_{rel['source'].lower().replace(' ', '_')}"
            tid = f"{rel['target_type']}_{rel['target'].lower().replace(' ', '_')}"
            self.relationships.append({
                "source": sid,
                "relation": rel["relation"],
                "target": tid,
                "confidence": rel.get("confidence", 0.7),
                "papers": [pmid],
            })

    def add_paper(self, pmid: str, title: str, abstract: str, url: str, year: str = ""):
        self.papers[pmid] = {
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "year": year,
            "url": url,
        }

    def add_entity(self, name: str, entity_type: str = "concept", aliases: list = None, papers: list = None):
        """Add a single entity to the graph by name and type."""
        eid = f"{entity_type}_{name.lower().replace(' ', '_')[:80]}"
        if eid not in self.entities:
            self.entities[eid] = {
                "id": eid,
                "type": entity_type,
                "name": name,
                "aliases": aliases or [],
                "papers": papers or [],
                "domain": self.domain,
                "source_run": self._run_id,
                "created_at": time.time(),
                "last_used": time.time(),
            }
        else:
            # Merge papers if entity already exists
            existing_papers = set(self.entities[eid].get("papers", []))
            for p in (papers or []):
                if p not in existing_papers:
                    self.entities[eid]["papers"].append(p)
            self.entities[eid]["last_used"] = time.time()
        return eid

    def stats(self) -> dict:
        entity_types = Counter(e["type"] for e in self.entities.values())
        relation_types = Counter(r["relation"] for r in self.relationships)
        top_entities = sorted(
            self.entities.values(), key=lambda e: len(e["papers"]), reverse=True
        )[:10]
        return {
            "entities": len(self.entities),
            "relationships": len(self.relationships),
            "papers": len(self.papers),
            "entity_types": dict(entity_types),
            "relation_types": dict(relation_types),
            "top_entities": top_entities,
        }

    def _merge_previous(self):
        """Merge entities/papers from the last saved graph with domain filtering and staleness pruning."""
        if GRAPH_FILE.exists():
            try:
                prev = json.loads(GRAPH_FILE.read_text(encoding="utf-8"))
                prev_entities = prev.get("entities", {})
                prev_papers = prev.get("papers", {})
                prev_rels = prev.get("relationships", [])
                prev_domain = prev.get("domain", "")
                now = time.time()

                # One-time migration: reset last_used for entities without domain metadata
                # (entities from before the provenance fix had last_used set to load time)
                migrated = False
                for eid, e in prev_entities.items():
                    if not e.get("domain") and e.get("last_used", 0) > now - 86400:
                        # Entity has no domain and was "used" within 24h — likely from old code
                        # Reset last_used to 0 so staleness scoring works
                        e["last_used"] = 0
                        e["created_at"] = 0
                        migrated = True
                if migrated:
                    print(f"  [Graph Migration] Reset timestamps for old entities (no domain metadata)", flush=True)

                # Domain filtering: only load entities from same domain or cross-domain entities
                domain_match = (prev_domain == self.domain) if prev_domain else True

                # Score and filter entities by staleness + domain relevance
                scored_entities = []
                for eid, e in prev_entities.items():
                    # Staleness scoring
                    created = e.get("created_at", 0)
                    last_used = e.get("last_used", created)
                    age = now - last_used if last_used else now - created
                    staleness = 1.0 / (1.0 + age / 3600)  # decays over hours

                    # Domain relevance
                    ent_domain = e.get("domain", "")
                    if ent_domain == self.domain:
                        domain_relevant = True  # Same domain — keep
                    elif not ent_domain:
                        domain_relevant = False  # No domain metadata — old entity, penalize
                    elif not domain_match:
                        domain_relevant = True  # Cross-domain run — allow all
                    else:
                        domain_relevant = False  # Different domain — penalize

                    # Paper count (well-established entities have more papers)
                    paper_count = len(e.get("papers", []))

                    # Combined score
                    score = staleness * 0.5 + (1.0 if domain_relevant else 0.2) * 0.3 + min(paper_count / 5, 1.0) * 0.2
                    scored_entities.append((eid, e, score))

                # Sort by score, take top N
                scored_entities.sort(key=lambda x: -x[2])
                loaded = 0
                skipped_old = 0
                for eid, e, score in scored_entities[:MAX_PERSISTED_ENTITIES]:
                    # Skip migrated entities (old, no domain metadata, not recently used)
                    if not e.get("domain") and e.get("created_at", 0) == 0 and e.get("last_used", 0) == 0:
                        skipped_old += 1
                        continue
                    if score < 0.1:  # Skip very stale/irrelevant entities
                        continue
                    if eid not in self.entities:
                        # Do NOT update last_used on load — only update when entity is
                        # actually referenced in the current run (add_paper_entities, add_entity)
                        self.entities[eid] = e
                        loaded += 1
                if skipped_old > 0:
                    print(f"  [Graph] Filtered {skipped_old} old entities (no domain, no provenance)", flush=True)

                for pmid, p in prev_papers.items():
                    if pmid not in self.papers:
                        self.papers[pmid] = p
                existing_keys = set(
                    (r["source"], r["relation"], r["target"]) for r in self.relationships
                )
                for r in prev_rels:
                    key = (r["source"], r["relation"], r["target"])
                    if key not in existing_keys:
                        self.relationships.append(r)
                        existing_keys.add(key)
                prev_sessions = prev.get("sessions", 0)
                self._session_count = prev_sessions if isinstance(prev_sessions, (int, float)) else len(prev_sessions)
            except Exception:
                pass

    def to_dict(self) -> dict:
        return {
            "entities": self.entities,
            "relationships": self.relationships,
            "papers": self.papers,
            "domain": self.domain,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGraph":
        g = cls(persist=False)
        g.entities = data.get("entities", {})
        g.relationships = data.get("relationships", [])
        g.papers = data.get("papers", {})
        g.domain = data.get("domain", "drug_discovery")
        return g

    def save(self, session_id=""):
        GRAPH_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = self.to_dict()
        if session_id:
            data["last_session"] = session_id
            data["sessions"] = self._session_count + 1
        data["domain"] = self.domain
        data["last_save"] = time.time()
        GRAPH_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def prune_stale(self, max_age_seconds: int = None):
        """Remove entities that haven't been used recently."""
        max_age = max_age_seconds or ENTITY_MAX_AGE
        now = time.time()
        stale = []
        for eid, ent in self.entities.items():
            last_used = ent.get("last_used", ent.get("created_at", 0))
            if now - last_used > max_age:
                # Only keep entities with many paper references (truly well-established)
                if len(ent.get("papers", [])) >= 5:
                    continue
                stale.append(eid)
        for eid in stale:
            del self.entities[eid]
        # Also prune relationships referencing deleted entities
        entity_ids = set(self.entities.keys())
        self.relationships = [
            r for r in self.relationships
            if r["source"] in entity_ids and r["target"] in entity_ids
        ]
        return len(stale)

    @classmethod
    def load(cls, persist=True) -> "KnowledgeGraph":
        if GRAPH_FILE.exists():
            return cls.from_dict(json.loads(GRAPH_FILE.read_text(encoding="utf-8")))
        return cls(persist=persist)

    def merge(self, other: "KnowledgeGraph"):
        # Merge entities — preserve paper lists instead of overwriting
        for eid, ent in other.entities.items():
            if eid in self.entities:
                # Merge paper lists
                existing_papers = set(self.entities[eid].get("papers", []))
                for p in ent.get("papers", []):
                    if p not in existing_papers:
                        self.entities[eid].setdefault("papers", []).append(p)
                # Merge aliases
                existing_aliases = set(self.entities[eid].get("aliases", []))
                for a in ent.get("aliases", []):
                    if a not in existing_aliases:
                        self.entities[eid].setdefault("aliases", []).append(a)
            else:
                self.entities[eid] = ent
        self.papers.update(other.papers)
        existing = set(
            (r["source"], r["relation"], r["target"]) for r in self.relationships
        )
        for r in other.relationships:
            key = (r["source"], r["relation"], r["target"])
            if key not in existing:
                self.relationships.append(r)
                existing.add(key)

    def filter_by_papers(self, paper_ids: set) -> "KnowledgeGraph":
        """Return a new KnowledgeGraph containing only entities/relationships from given papers."""
        filtered = KnowledgeGraph.__new__(KnowledgeGraph)
        filtered.entities = {}
        filtered.relationships = []
        filtered.papers = {}
        filtered.domain = self.domain
        filtered._session_count = 0

        # Filter entities — keep only those referenced in the given papers
        for eid, ent in self.entities.items():
            ent_papers = set(ent.get("papers", []))
            if ent_papers & paper_ids:
                filtered.entities[eid] = ent

        # Filter papers
        for pmid, p in self.papers.items():
            if pmid in paper_ids:
                filtered.papers[pmid] = p

        # Filter relationships — keep only those between filtered entities
        entity_ids = set(filtered.entities.keys())
        for r in self.relationships:
            if r["source"] in entity_ids and r["target"] in entity_ids:
                filtered.relationships.append(r)

        return filtered

    def detect_contradictions(self) -> list[dict]:
        """Detect contradictions in the knowledge graph:
        - Direct: same source-target with opposite relation types
        - Confidence: same relation with widely varying confidence across papers
        - Side effect: drug treats disease but side effect matches disease symptoms
        - Path-based: entity connected via conflicting chains (A→+B→-C)"""
        from collections import defaultdict
        contradictions = []

        conflicting_pairs = {
            ("activates", "inhibits"), ("activates", "represses"),
            ("treats", "causes"), ("enhances", "inhibits"),
            ("upregulates", "downregulates"), ("promotes", "inhibits"),
            ("induces", "suppresses"),
        }

        # 1. Direct relation conflicts
        pair_relations = defaultdict(list)
        for r in self.relationships:
            s, t = r["source"], r["target"]
            pair_relations[(s, t)].append(r)
        for (s, t), rels in pair_relations.items():
            types_seen = [r["relation"] for r in rels]
            for c1, c2 in conflicting_pairs:
                if c1 in types_seen and c2 in types_seen:
                    src_name = self.entities.get(s, {}).get("name", s)
                    tgt_name = self.entities.get(t, {}).get("name", t)
                    r1 = next(r for r in rels if r["relation"] == c1)
                    r2 = next(r for r in rels if r["relation"] == c2)
                    contradictions.append({
                        "type": "direct",
                        "severity": "high",
                        "summary": f"{src_name} is reported to both {c1} and {c2} {tgt_name}",
                        "source": s, "target": t,
                        "source_name": src_name, "target_name": tgt_name,
                        "relation_a": c1, "relation_b": c2,
                        "papers_a": r1.get("papers", []),
                        "papers_b": r2.get("papers", []),
                    })

        # 2. Confidence anomalies — same relation with >0.4 confidence gap
        rel_groups = defaultdict(list)
        for r in self.relationships:
            key = (r["source"], r["relation"], r["target"])
            rel_groups[key].append(r)
        for key, rels in rel_groups.items():
            confs = [r.get("confidence", 0.5) for r in rels]
            if len(confs) >= 2 and max(confs) - min(confs) > 0.4:
                s, rel, t = key
                src_name = self.entities.get(s, {}).get("name", s)
                tgt_name = self.entities.get(t, {}).get("name", t)
                contradictions.append({
                    "type": "confidence",
                    "severity": "medium",
                    "summary": f"{src_name} {rel} {tgt_name}: confidence ranges {min(confs):.1f}–{max(confs):.1f} across papers",
                    "source": s, "target": t,
                    "source_name": src_name, "target_name": tgt_name,
                    "relation": rel,
                    "min_confidence": round(min(confs), 2),
                    "max_confidence": round(max(confs), 2),
                })

        # 3. Side-effect contradictions — drug treats disease X but has side effects matching X
        drug_entities = {eid: e for eid, e in self.entities.items() if e["type"] == "drug"}
        disease_entities = {eid: e for eid, e in self.entities.items() if e["type"] == "disease"}
        for did, drug in drug_entities.items():
            treatments = [r for r in self.relationships
                          if r["source"] == did and r["relation"] == "treats"]
            side_effects = [r for r in self.relationships
                            if r["source"] == did and r["relation"] == "has_side_effect"]
            if not treatments or not side_effects:
                continue
            drug_name = drug["name"]
            se_names = [self.entities.get(r["target"], {}).get("name", "") for r in side_effects]
            for t in treatments:
                disease_name = self.entities.get(t["target"], {}).get("name", "")
                if not disease_name:
                    continue
                disease_lower = disease_name.lower()
                matching = [s for s in se_names if s.lower() in disease_lower or disease_lower in s.lower()]
                if matching:
                    contradictions.append({
                        "type": "side_effect",
                        "severity": "medium",
                        "summary": f"{drug_name} treats {disease_name} but also causes side effects matching it: {', '.join(matching)}",
                        "source": did, "target": t["target"],
                        "source_name": drug_name, "target_name": disease_name,
                        "side_effects": matching,
                        "relation": "treats",
                    })

        # 4. Path-based contradictions — A→+B→-C implies A→-C indirectly
        adj = defaultdict(list)
        for r in self.relationships:
            adj[r["source"]].append((r["target"], r["relation"], r.get("confidence", 0.5)))
        edge_effects = {"activates": 1, "inhibits": -1, "upregulates": 1, "downregulates": -1,
                        "promotes": 1, "suppresses": -1, "induces": 1, "represses": -1,
                        "enhances": 1, "reduces": -1, "treats": 1, "causes": -1}
        for src in list(adj.keys())[:30]:  # limit scope
            for tgt1, rel1, c1 in adj[src]:
                sign1 = edge_effects.get(rel1, 0)
                if sign1 == 0:
                    continue
                for tgt2, rel2, _ in adj.get(tgt1, []):
                    sign2 = edge_effects.get(rel2, 0)
                    if sign2 == 0:
                        continue
                    if sign1 * sign2 == -1:  # conflicting signs
                        src_name = self.entities.get(src, {}).get("name", src)
                        mid_name = self.entities.get(tgt1, {}).get("name", tgt1)
                        tgt_name = self.entities.get(tgt2, {}).get("name", tgt2)
                        contradictions.append({
                            "type": "path",
                            "severity": "low",
                            "summary": f"{src_name} {rel1} {mid_name} (activates), but {mid_name} {rel2} {tgt_name} (inhibits) — indirect contradiction via chain",
                            "source": src, "intermediate": tgt1, "target": tgt2,
                            "source_name": src_name, "intermediate_name": mid_name, "target_name": tgt_name,
                            "relation_a": rel1, "relation_b": rel2,
                        })

        contradictions.sort(key=lambda c: {"high": 0, "medium": 1, "low": 2}[c["severity"]])
        return contradictions

    def compute_metrics(self) -> dict:
        """Compute mathematical graph metrics: density, degree, betweenness,
        closeness, clustering, relation entropy, co-occurrence (Jaccard),
        edge strength, contradiction candidates, temporal trends."""
        from collections import defaultdict
        import math

        entity_ids = list(self.entities.keys())
        n = len(entity_ids)
        eid_to_idx = {eid: i for i, eid in enumerate(entity_ids)}

        adj_neighbors: dict[str, set[str]] = defaultdict(set)
        adj_with_relation: dict[str, list[tuple[str, str, float]]] = defaultdict(list)
        for r in self.relationships:
            s, t = r["source"], r["target"]
            adj_neighbors[s].add(t)
            adj_neighbors[t].add(s)
            adj_with_relation[s].append((t, r["relation"], r.get("confidence", 0.5)))

        unique_edges = sum(len(v) for v in adj_neighbors.values()) // 2
        density = (2 * unique_edges) / (n * (n - 1)) if n > 1 else 0.0

        entity_metrics = {}
        for eid in entity_ids:
            neighbors = adj_neighbors.get(eid, set())
            deg = len(neighbors)

            relations = [r for r in self.relationships if r["source"] == eid]
            rel_counter = defaultdict(int)
            for r in relations:
                rel_counter[r["relation"]] += 1
            rel_total = sum(rel_counter.values())
            rel_entropy = 0.0
            if rel_total > 1:
                for c in rel_counter.values():
                    p = c / rel_total
                    rel_entropy -= p * math.log2(p)

            entity_metrics[eid] = {
                "degree": deg,
                "relation_entropy": round(rel_entropy, 3),
                "papers_count": len(self.entities[eid].get("papers", [])),
            }

        def _build_undirected_adj(eids: list[str]) -> dict[str, set[str]]:
            adj = defaultdict(set)
            for r in self.relationships:
                s, t = r["source"], r["target"]
                if s in eids and t in eids:
                    adj[s].add(t)
                    adj[t].add(s)
            return adj

        def _brandes_betweenness(eids: list[str], adj: dict[str, set[str]]) -> dict[str, float]:
            cb = defaultdict(float)
            for s in eids:
                s_stack = []
                predecessors = defaultdict(list)
                sigma = {v: 0 for v in eids}
                sigma[s] = 1
                dist = {v: -1 for v in eids}
                dist[s] = 0
                q = [s]
                while q:
                    v = q.pop(0)
                    s_stack.append(v)
                    for w in adj.get(v, set()):
                        if dist[w] < 0:
                            dist[w] = dist[v] + 1
                            q.append(w)
                        if dist[w] == dist[v] + 1:
                            sigma[w] += sigma[v]
                            predecessors[w].append(v)
                delta = defaultdict(float)
                while s_stack:
                    w = s_stack.pop()
                    for v in predecessors[w]:
                        delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
                    if w != s:
                        cb[w] += delta[w]
            n_cb = len(eids)
            if n_cb > 2:
                norm = (n_cb - 1) * (n_cb - 2)
                for v in cb:
                    cb[v] /= norm
            return dict(cb)

        def _closeness_all(eids: list[str], adj: dict[str, set[str]]) -> dict[str, float]:
            cc = {}
            for s in eids:
                dist = {v: -1 for v in eids}
                dist[s] = 0
                q = [s]
                while q:
                    v = q.pop(0)
                    for w in adj.get(v, set()):
                        if dist[w] < 0:
                            dist[w] = dist[v] + 1
                            q.append(w)
                reachable = [d for d in dist.values() if d > 0]
                if not reachable:
                    cc[s] = 0.0
                else:
                    cc[s] = (len(reachable) - 1) / sum(reachable) if sum(reachable) > 0 else 0.0
            return cc

        def _clustering(eids: list[str], adj: dict[str, set[str]]) -> dict[str, float]:
            clust = {}
            for v in eids:
                nb = list(adj.get(v, set()))
                k = len(nb)
                if k < 2:
                    clust[v] = 0.0
                else:
                    edges = 0
                    for i in range(k):
                        for j in range(i + 1, k):
                            if nb[j] in adj.get(nb[i], set()):
                                edges += 1
                    clust[v] = (2 * edges) / (k * (k - 1))
            return clust

        connected_ids = [eid for eid in entity_ids if eid in adj_neighbors]
        undirected_adj = _build_undirected_adj(connected_ids)

        betweenness = _brandes_betweenness(connected_ids, undirected_adj)
        closeness = _closeness_all(connected_ids, undirected_adj)
        clustering = _clustering(connected_ids, undirected_adj)

        for eid in connected_ids:
            entity_metrics[eid]["betweenness"] = round(betweenness.get(eid, 0.0), 4)
            entity_metrics[eid]["closeness"] = round(closeness.get(eid, 0.0), 4)
            entity_metrics[eid]["clustering"] = round(clustering.get(eid, 0.0), 4)

        co_occurrence = {}
        eid_list = entity_ids
        for i in range(len(eid_list)):
            for j in range(i + 1, len(eid_list)):
                a, b = eid_list[i], eid_list[j]
                papers_a = set(self.entities[a].get("papers", []))
                papers_b = set(self.entities[b].get("papers", []))
                intersect = papers_a & papers_b
                union = papers_a | papers_b
                if union:
                    jaccard = len(intersect) / len(union)
                    if jaccard > 0:
                        key = f"{a}|{b}"
                        co_occurrence[key] = {
                            "count": len(intersect),
                            "jaccard": round(jaccard, 4),
                            "pair": [a, b],
                        }

        edge_strength = defaultdict(lambda: {"count": 0, "confidence_sum": 0.0, "papers": set()})
        for r in self.relationships:
            key = (r["source"], r["relation"], r["target"])
            edge_strength[key]["count"] += 1
            edge_strength[key]["confidence_sum"] += r.get("confidence", 0.5)
            for p in r.get("papers", []):
                edge_strength[key]["papers"].add(p)
        edge_strength_out = {}
        for (src, rel, tgt), v in edge_strength.items():
            edge_strength_out[f"{src}|{rel}|{tgt}"] = {
                "count": v["count"],
                "avg_confidence": round(v["confidence_sum"] / v["count"], 3) if v["count"] else 0,
                "papers_count": len(v["papers"]),
            }

        contradiction_candidates = []
        pair_relations = defaultdict(list)
        for r in self.relationships:
            s, t = r["source"], r["target"]
            pair_relations[(s, t)].append(r["relation"])
        conflicting_pairs = {
            ("activates", "inhibits"),
            ("treats", "causes"),
            ("activates", "represses"),
        }
        for (s, t), rels in pair_relations.items():
            for c1, c2 in conflicting_pairs:
                if c1 in rels and c2 in rels:
                    contradiction_candidates.append({
                        "source": s,
                        "target": t,
                        "conflicting_relations": [c1, c2],
                    })
        contradiction_candidates = contradiction_candidates[:20]

        temporal_trends = {}
        for eid in entity_ids:
            years = []
            for pmid in self.entities[eid].get("papers", []):
                p = self.papers.get(pmid, {})
                y = p.get("year", "")
                if y:
                    years.append(y)
            if years:
                year_counts = defaultdict(int)
                for y in years:
                    year_counts[y] += 1
                temporal_trends[eid] = dict(sorted(year_counts.items()))

        return {
            "density": round(density, 4),
            "entity_count": n,
            "edge_count": unique_edges,
            "entity_metrics": entity_metrics,
            "co_occurrence": co_occurrence,
            "edge_strength": edge_strength_out,
            "contradiction_candidates": contradiction_candidates,
            "temporal_trends": temporal_trends,
        }
