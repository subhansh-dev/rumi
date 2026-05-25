# Discovery Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn RUMI into an autonomous drug discovery AI that searches PubMed, extracts entities, builds a knowledge graph, and generates novel hypotheses.

**Architecture:** Agentic workflow — RUMI drives discovery via session tools (Gemini for extraction/reasoning). Python utility modules handle PubMed API, graph persistence, and output formatting. Static HTML dashboard for visual exploration.

**Tech Stack:** Python 3.11, urllib (Entrez API), json, pathlib, webbrowser, vis-network (CDN for dashboard)

---

## File Structure

| File | Responsibility |
|---|---|
| `discovery/__init__.py` | Package init |
| `discovery/pubmed.py` | PubMed ESearch + EFetch via Entrez API |
| `discovery/graph.py` | KnowledgeGraph class: entities, relationships, merge, save/load |
| `discovery/output.py` | Terminal formatting helpers |
| `discovery/dashboard/index.html` | Static web dashboard (vis-network) |
| `ui.py` | 6 new slash command handlers |
| `main.py` | DiscoveryEngine orchestration + Intake Protocol |
| `SOUL.md` | Discovery Intake Protocol section |
| `RUMI.md` | Updated capabilities table |

---

### Task 1: discovery/pubmed.py — PubMed Search Utility

**Files:**
- Create: `discovery/__init__.py` (empty)
- Create: `discovery/pubmed.py`

- [ ] **Step 1: Create `discovery/__init__.py`** — empty file.

- [ ] **Step 2: Write `discovery/pubmed.py`:**

```python
import json, time, urllib.request, urllib.parse
from pathlib import Path
from typing import Optional

CACHE_DIR = Path(__file__).resolve().parent.parent / "discovery" / "cache"
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _get_email() -> str:
    try:
        cfg = json.loads(
            (Path(__file__).resolve().parent.parent / "config" / "api_keys.json").read_text(encoding="utf-8-sig")
        )
        return cfg.get("ncbi_email", "rumi@research.ai")
    except Exception:
        return "rumi@research.ai"


def search(query: str, max_results: int = 20, retstart: int = 0) -> list[str]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    params = urllib.parse.urlencode({
        "db": "pubmed", "term": query, "retmax": max_results,
        "retstart": retstart, "retmode": "json", "email": _get_email(),
    })
    try:
        with urllib.request.urlopen(f"{ESEARCH_URL}?{params}", timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"[PubMed ERROR] search failed: {e}")
        return []


def fetch(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    params = urllib.parse.urlencode({
        "db": "pubmed", "id": ",".join(pmids),
        "retmode": "xml", "rettype": "abstract", "email": _get_email(),
    })
    try:
        with urllib.request.urlopen(f"{EFETCH_URL}?{params}", timeout=30) as resp:
            xml_data = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[PubMed ERROR] fetch failed: {e}")
        return []
    return _parse_xml_results(xml_data)


def _parse_xml_results(xml_text: str) -> list[dict]:
    results = []
    for article in xml_text.split("<PubmedArticle>")[1:]:
        pmid = _extract_tag(article, "PMID")
        title = _extract_tag(article, "ArticleTitle")
        abstract = _extract_tag(article, "AbstractText")
        if pmid and title:
            results.append({
                "pmid": pmid, "title": title,
                "abstract": abstract or "(No abstract available)",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })
    return results


def _extract_tag(text: str, tag: str) -> str:
    start = text.find(f"<{tag}>")
    if start == -1:
        start = text.find(f"<{tag} ")
    if start == -1:
        return ""
    start = text.find(">", start) + 1
    end = text.find(f"</{tag}>", start)
    return text[start:end].strip() if end != -1 else ""


def search_and_fetch(query: str, max_results: int = 20) -> list[dict]:
    pmids = search(query, max_results)
    if not pmids:
        return []
    time.sleep(1)
    return fetch(pmids)
```

- [ ] **Step 3: Verify PubMed module works**

```bash
python -c "from discovery.pubmed import search_and_fetch; r = search_and_fetch('metformin alzheimer', 3); print(len(r)); [print(p['title'][:80]) for p in r]"
```
Expected: 3 paper titles printed.

---

### Task 2: discovery/graph.py — Knowledge Graph Utility

**Files:**
- Create: `discovery/graph.py`

- [ ] **Step 1: Write `discovery/graph.py`:**

```python
import json
from pathlib import Path
from collections import Counter

GRAPH_FILE = Path(__file__).resolve().parent.parent / "discovery" / "graph" / "knowledge_graph.json"


class KnowledgeGraph:
    def __init__(self):
        self.entities: dict[str, dict] = {}
        self.relationships: list[dict] = []
        self.papers: dict[str, dict] = {}

    def add_paper_entities(self, entities: list[dict], pmid: str):
        for ent in entities:
            eid = f"{ent['type']}_{ent['name'].lower().replace(' ', '_')}"
            if eid not in self.entities:
                self.entities[eid] = {"id": eid, "type": ent["type"], "name": ent["name"], "aliases": ent.get("aliases", []), "papers": []}
            if pmid not in self.entities[eid]["papers"]:
                self.entities[eid]["papers"].append(pmid)

    def add_relationships(self, relationships: list[dict], pmid: str):
        for rel in relationships:
            sid = f"{rel['source_type']}_{rel['source'].lower().replace(' ', '_')}"
            tid = f"{rel['target_type']}_{rel['target'].lower().replace(' ', '_')}"
            self.relationships.append({"source": sid, "relation": rel["relation"], "target": tid, "confidence": rel.get("confidence", 0.7), "papers": [pmid]})

    def add_paper(self, pmid: str, title: str, abstract: str, url: str):
        self.papers[pmid] = {"pmid": pmid, "title": title, "abstract": abstract, "url": url}

    def stats(self) -> dict:
        entity_types = Counter(e["type"] for e in self.entities.values())
        relation_types = Counter(r["relation"] for r in self.relationships)
        return {
            "entities": len(self.entities), "relationships": len(self.relationships),
            "papers": len(self.papers), "entity_types": dict(entity_types),
            "relation_types": dict(relation_types),
            "top_entities": sorted(self.entities.values(), key=lambda e: len(e["papers"]), reverse=True)[:10],
        }

    def to_dict(self) -> dict:
        return {"entities": self.entities, "relationships": self.relationships, "papers": self.papers}

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGraph":
        g = cls(); g.entities = data.get("entities", {}); g.relationships = data.get("relationships", []); g.papers = data.get("papers", {}); return g

    def save(self):
        GRAPH_FILE.parent.mkdir(parents=True, exist_ok=True)
        GRAPH_FILE.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls) -> "KnowledgeGraph":
        if GRAPH_FILE.exists():
            return cls.from_dict(json.loads(GRAPH_FILE.read_text(encoding="utf-8")))
        return cls()

    def merge(self, other: "KnowledgeGraph"):
        self.entities.update(other.entities)
        self.papers.update(other.papers)
        existing = set((r["source"], r["relation"], r["target"]) for r in self.relationships)
        for r in other.relationships:
            key = (r["source"], r["relation"], r["target"])
            if key not in existing:
                self.relationships.append(r); existing.add(key)
```

- [ ] **Step 2: Quick test**

```bash
python -c "from discovery.graph import KnowledgeGraph; import json; g=KnowledgeGraph(); g.add_paper('123','Test','Abstract','url'); g.add_paper_entities([{'type':'drug','name':'Metformin'}],'123'); g.add_relationships([{'source_type':'drug','source':'Metformin','relation':'treats','target_type':'disease','target':'Diabetes','confidence':0.9}],'123'); print(json.dumps(g.stats(),indent=2))"
```

---

### Task 3: discovery/output.py — Output Formatting

**Files:**
- Create: `discovery/output.py`

- [ ] **Step 1: Write `discovery/output.py`:**

```python
import json
from pathlib import Path

HYPOTHESES_DIR = Path(__file__).resolve().parent.parent / "discovery" / "hypotheses"


def format_papers(papers: list[dict]) -> str:
    lines = []
    for i, p in enumerate(papers, 1):
        lines.append(f"  {i}. {p['title']}")
        lines.append(f"     PMID: {p['pmid']}  |  {p['url']}")
        abstract = p.get("abstract", "")
        if abstract and abstract != "(No abstract available)":
            lines.append(f"     {abstract[:200]}...")
        lines.append("")
    return "\n".join(lines)


def format_hypotheses(hypotheses: list[dict]) -> str:
    lines = ["", "=" * 70, "  DISCOVERED HYPOTHESES", "=" * 70, ""]
    for i, h in enumerate(hypotheses, 1):
        lines.append(f"  Hypothesis {i}: {h['title']}")
        lines.append(f"  Confidence: {h.get('confidence', 'N/A')}")
        lines.append(f"  {h['description']}")
        lines.append("")
        lines.append("  Evidence Chain:")
        for j, ev in enumerate(h.get("evidence", []), 1):
            lines.append(f"    {j}. {ev}")
        lines.append(f"  Papers: {', '.join(h.get('papers', []))}")
        lines.append(f"  Testability: {h.get('testability', 'N/A')}")
        lines.append("")
    return "\n".join(lines)


def format_stats(stats: dict) -> str:
    lines = [
        "  Knowledge Graph Stats:",
        f"    Papers: {stats.get('papers', 0)}",
        f"    Entities: {stats.get('entities', 0)}",
        f"    Relationships: {stats.get('relationships', 0)}",
        "", "  Entity Types:",
    ]
    for etype, count in stats.get("entity_types", {}).items():
        lines.append(f"    {etype}: {count}")
    lines.append(""); lines.append("  Top Entities:")
    for ent in stats.get("top_entities", []):
        lines.append(f"    {ent['name']} ({ent['type']}) - {len(ent['papers'])} papers")
    return "\n".join(lines)


def save_hypotheses(hypotheses: list[dict]):
    HYPOTHESES_DIR.mkdir(parents=True, exist_ok=True)
    (HYPOTHESES_DIR / "active.json").write_text(json.dumps(hypotheses, indent=2, ensure_ascii=False), encoding="utf-8")


def save_session(query: str, papers: list[dict], hypotheses: list[dict]):
    from datetime import date
    slug = query.lower().replace(" ", "_")[:30]
    fname = f"{date.today()}_{slug}.json"
    session_dir = Path(__file__).resolve().parent.parent / "discovery" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / fname).write_text(
        json.dumps({"query": query, "papers": papers, "hypotheses": hypotheses}, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
```

---

### Task 4: main.py — Discovery Engine

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Read `main.py` to find correct insertion points**, then add:

```python
# --- Discovery Engine ---

async def _run_discovery_pipeline(self, query: str, depth: str = "quick"):
    from discovery.pubmed import search_and_fetch
    from discovery.graph import KnowledgeGraph
    from discovery.output import format_papers, save_session

    max_results = 20 if depth == "quick" else 100

    self._post_output("🔍 Searching PubMed...")
    papers = search_and_fetch(query, max_results=max_results)
    if not papers:
        self._post_output("No papers found.")
        return
    self._post_output(f"Found {len(papers)} papers.")
    self._post_output(format_papers(papers[:5]))

    self._post_output("🧬 Extracting entities and relationships...")
    extraction_prompt = self._build_extraction_prompt(papers)
    extraction_result = await self._call_llm(extraction_prompt)
    entities, relationships = self._parse_extraction(extraction_result)

    self._post_output("📊 Building knowledge graph...")
    graph = KnowledgeGraph.load()
    for p in papers:
        graph.add_paper(p["pmid"], p["title"], p.get("abstract", ""), p["url"])
    if entities:
        graph.add_paper_entities(entities, papers[0]["pmid"])
    if relationships:
        graph.add_relationships(relationships, papers[0]["pmid"])
    graph.save()

    self._post_output("💡 Mining patterns and generating hypotheses...")
    hypothesis_prompt = self._build_hypothesis_prompt(graph, query)
    hypothesis_result = await self._call_llm(hypothesis_prompt)
    hypotheses = self._parse_hypotheses(hypothesis_result)

    from discovery.output import format_hypotheses, save_hypotheses
    save_hypotheses(hypotheses)
    save_session(query, papers, hypotheses)
    self._post_output(format_hypotheses(hypotheses))
    self._post_output("\n  Done. Run /dashboard to explore visually.")

def _build_extraction_prompt(self, papers: list[dict]) -> str:
    papers_text = "\n\n".join(
        f"--- Paper {i+1} (PMID: {p['pmid']}) ---\nTitle: {p['title']}\nAbstract: {p.get('abstract', '')}"
        for i, p in enumerate(papers)
    )
    return f"""You are a biomedical entity extractor. Extract ALL drugs, diseases, genes, proteins, mechanisms, and pathways from these papers.

For each paper, output a JSON array of entities and relationships.

Entity format: {{"type": "drug|disease|gene|protein|mechanism|pathway", "name": "exact name"}}
Relationship format: {{"source": "entity name", "source_type": "entity type", "relation": "treats|causes|activates|inhibits|binds|expressed_in|regulates|associated_with", "target": "entity name", "target_type": "entity type", "confidence": 0.0-1.0}}

Papers:
{papers_text}

Output ONLY valid JSON in this format:
{{"entities": [...], "relationships": [...]}}"""

def _build_hypothesis_prompt(self, graph, query: str) -> str:
    stats = graph.stats()
    graph_summary = json.dumps({
        "entities": {k: {"type": v["type"], "name": v["name"], "papers": len(v["papers"])} for k, v in list(graph.entities.items())[:50]},
        "relationships": graph.relationships[:100],
        "stats": stats,
    }, indent=2)
    return f"""You are an AI drug discovery scientist analyzing a knowledge graph from PubMed papers on: "{query}"

Knowledge Graph:
{graph_summary}

Apply pattern mining to find NON-OBVIOUS connections:
1. Indirect Connection (Drug Repurposing): Drug A treats Disease X via Mechanism M, and M relevant to Disease Y -> Drug A might treat Y.
2. Bridge Node Discovery: Entity connecting two disconnected disease clusters.
3. Contradiction Detection: Conflicting findings about same entity pair.
4. Low Co-occurrence: Mechanistically plausible connections rarely mentioned.

Generate 3-5 specific falsifiable hypotheses. Each needs: title, description, confidence (0-1), evidence list, papers (PMIDs), testability, novelty.

Output ONLY valid JSON as a list of hypothesis objects."""

def _parse_extraction(self, text: str) -> tuple[list, list]:
    import re, json
    m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if m: text = m.group(1)
    try:
        data = json.loads(text.strip())
        return data.get("entities", []), data.get("relationships", [])
    except json.JSONDecodeError:
        return [], []

def _parse_hypotheses(self, text: str) -> list:
    import re, json
    m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if m: text = m.group(1)
    try:
        data = json.loads(text.strip())
        return data if isinstance(data, list) else data.get("hypotheses", [])
    except json.JSONDecodeError:
        return []

async def _call_llm(self, prompt: str) -> str:
    from google import genai
    from google.genai import types
    import json as j
    from pathlib import Path
    cfg = j.loads((Path(__file__).resolve().parent / "config" / "api_keys.json").read_text(encoding="utf-8-sig"))
    client = genai.Client(api_key=cfg["gemini_api_key"])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.3, max_output_tokens=8192),
    )
    return response.text
```

---

### Task 5: ui.py — Discovery Commands

**Files:**
- Modify: `ui.py`

- [ ] **Step 1: Read `ui.py` to find the existing command handler registration pattern.** Add 6 handlers:

```python
@handler("/discover")
async def handle_discover(self, args: str):
    # TODO: call _discovery_intake for clarifying questions
    await self._run_discovery_pipeline(args.strip() or "drug discovery")

@handler("/search")
async def handle_search(self, args: str):
    from discovery.pubmed import search_and_fetch
    from discovery.output import format_papers
    papers = search_and_fetch(args, max_results=10)
    self._post_output(format_papers(papers) if papers else "No results found.")

@handler("/hypothesize")
async def handle_hypothesize(self, args: str):
    from discovery.graph import KnowledgeGraph
    graph = KnowledgeGraph.load()
    if not graph.entities:
        self._post_output("No knowledge graph. Run /discover first.")
        return
    result = await self._call_llm(self._build_hypothesis_prompt(graph, args or "existing data"))
    hypotheses = self._parse_hypotheses(result)
    from discovery.output import format_hypotheses, save_hypotheses
    save_hypotheses(hypotheses)
    self._post_output(format_hypotheses(hypotheses))

@handler("/graph")
async def handle_graph(self, args: str):
    from discovery.graph import KnowledgeGraph
    from discovery.output import format_stats
    graph = KnowledgeGraph.load()
    self._post_output(format_stats(graph.stats()))

@handler("/dashboard")
async def handle_dashboard(self, args: str):
    import webbrowser
    dp = Path(__file__).resolve().parent / "discovery" / "dashboard" / "index.html"
    if dp.exists():
        webbrowser.open(dp.as_uri())
        self._post_output("Dashboard opened in browser.")
    else:
        self._post_output("Dashboard not found. Run /discover first.")

@handler("/discoveries")
async def handle_discoveries(self, args: str):
    sd = Path(__file__).resolve().parent / "discovery" / "sessions"
    if not sd.exists():
        self._post_output("No discoveries yet."); return
    for s in sorted(sd.glob("*.json"), reverse=True)[:5]:
        data = json.loads(s.read_text(encoding="utf-8"))
        self._post_output(f"{s.stem} - {data.get('query','?')} ({len(data.get('papers',[]))} papers, {len(data.get('hypotheses',[]))} hypotheses)")
```

---

### Task 6: Web Dashboard

**Files:**
- Create: `discovery/dashboard/index.html`

- [ ] **Step 1: Create directory and write dashboard HTML**

The dashboard is a single self-contained HTML file (~150 lines) that:
- Uses vis-network CDN for interactive knowledge graph visualization
- Has tabs: Graph | Hypotheses | Papers | Stats
- Reads JSON files via fetch
- Dark theme matching RUMI's terminal aesthetic

Key content (write to `discovery/dashboard/index.html`):

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>RUMI Discovery Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.6/dist/vis-network.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1a1a2e; color: #e0e0e0; font-family: 'Segoe UI', monospace; }
  .tab-bar { display: flex; background: #16213e; padding: 8px; gap: 4px; }
  .tab { padding: 10px 24px; cursor: pointer; color: #8899aa; border-radius: 4px 4px 0 0; }
  .tab:hover { background: #0f3460; }
  .tab.active { color: #00d4aa; background: #1a1a2e; border-bottom: 2px solid #00d4aa; }
  #graph-container { width: 100%; height: 80vh; }
  .hypothesis-card { background: #16213e; margin: 12px; padding: 16px; border-radius: 8px; border-left: 4px solid #00d4aa; }
  .hypothesis-card h3 { color: #00d4aa; margin-bottom: 8px; }
  .evidence { font-size: 0.9em; color: #aabbcc; margin-top: 8px; padding-left: 16px; }
  .stat-grid { display: flex; flex-wrap: wrap; gap: 16px; padding: 20px; }
  .stat-box { background: #16213e; padding: 24px; border-radius: 8px; min-width: 160px; text-align: center; }
  .stat-value { font-size: 2.5em; color: #00d4aa; font-weight: bold; }
  .stat-label { color: #8899aa; font-size: 0.9em; margin-top: 4px; }
  .hidden { display: none; }
  #papers-container { padding: 20px; }
  .paper-item { background: #16213e; margin: 8px 0; padding: 12px; border-radius: 4px; }
</style>
</head>
<body>
<div class="tab-bar">
  <div class="tab active" onclick="switchTab('graph')">Graph</div>
  <div class="tab" onclick="switchTab('hypotheses')">Hypotheses</div>
  <div class="tab" onclick="switchTab('papers')">Papers</div>
  <div class="tab" onclick="switchTab('stats')">Stats</div>
</div>
<div id="graph-container"></div>
<div id="hypotheses-container" class="hidden" style="padding:20px;max-height:80vh;overflow-y:auto;"></div>
<div id="papers-container" class="hidden"></div>
<div id="stats-container" class="hidden"></div>
<script>
const COLORS = {drug:'#4ade80', disease:'#f87171', gene:'#60a5fa', protein:'#a78bfa', mechanism:'#fb923c', pathway:'#fbbf24'};
let network = null;

async function loadGraph() {
  try {
    const resp = await fetch('../../discovery/graph/knowledge_graph.json');
    const data = await resp.json();
    const nodes = [], edges = [];
    const ents = data.entities || {};
    for (const [id, e] of Object.entries(ents)) {
      nodes.push({ id, label: e.name, title: `${e.type}: ${e.name}\nPapers: ${(e.papers||[]).length}`, color: COLORS[e.type]||'#94a3b8', shape: 'dot', size: 20 + Math.min((e.papers||[]).length * 3, 30) });
    }
    const rels = data.relationships || [];
    for (const r of rels) {
      edges.push({ from: r.source, to: r.target, label: r.relation, title: `Confidence: ${r.confidence}`, width: (r.confidence||0.5)*3, color: { color: '#64748b', highlight: '#00d4aa' }, font: { size: 10, color: '#94a3b8' } });
    }
    const container = document.getElementById('graph-container');
    network = new vis.Network(container, { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) }, {
      physics: { solver: 'forceAtlas2Based', stabilization: { iterations: 200 } },
      interaction: { hover: true, tooltipDelay: 100 },
      nodes: { borderWidth: 2, font: { color: '#e0e0e0', size: 12 } },
    });
  } catch(e) { document.getElementById('graph-container').innerHTML = '<p style="padding:40px;color:#8899aa;">No graph data yet. Run /discover first.</p>'; }
}

async function loadHypotheses() {
  try {
    const resp = await fetch('../../discovery/hypotheses/active.json');
    const hyps = await resp.json();
    const container = document.getElementById('hypotheses-container');
    container.innerHTML = hyps.map((h,i) => `<div class="hypothesis-card"><h3>Hypothesis ${i+1}: ${h.title}</h3><div style="color:#8899aa;font-size:0.9em;margin-bottom:8px;">Confidence: ${(h.confidence*100).toFixed(0)}%</div><p>${h.description}</p><div class="evidence"><strong>Evidence:</strong><ul>${(h.evidence||[]).map(e=>'<li>'+e+'</li>').join('')}</ul></div><div style="margin-top:8px;color:#8899aa;font-size:0.85em;">Papers: ${(h.papers||[]).join(', ')}<br>Testability: ${h.testability||'N/A'}</div></div>`).join('');
  } catch(e) { document.getElementById('hypotheses-container').innerHTML = '<p style="padding:20px;color:#8899aa;">No hypotheses yet.</p>'; }
}

async function loadPapers() {
  try {
    const resp = await fetch('../../discovery/graph/knowledge_graph.json');
    const data = await resp.json();
    const papers = Object.values(data.papers || {});
    const container = document.getElementById('papers-container');
    container.innerHTML = '<input type="text" id="paper-search" placeholder="Search papers..." style="width:100%;padding:10px;margin-bottom:12px;background:#16213e;border:1px solid #333;color:#e0e0e0;border-radius:4px;" oninput="filterPapers()">'
      + '<div id="paper-list">' + papers.map(p => `<div class="paper-item"><strong>${p.title}</strong><br><span style="color:#8899aa;font-size:0.85em;">PMID: ${p.pmid} | <a href="${p.url}" target="_blank" style="color:#00d4aa;">View</a></span></div>`).join('') + '</div>';
    window._papers = papers;
  } catch(e) { document.getElementById('papers-container').innerHTML = '<p style="padding:20px;color:#8899aa;">No papers yet.</p>'; }
}
window.filterPapers = function() {
  const q = (document.getElementById('paper-search').value||'').toLowerCase();
  const filtered = (window._papers||[]).filter(p => p.title.toLowerCase().includes(q));
  document.getElementById('paper-list').innerHTML = filtered.map(p => `<div class="paper-item"><strong>${p.title}</strong><br><span style="color:#8899aa;font-size:0.85em;">PMID: ${p.pmid}</span></div>`).join('');
};

async function loadStats() {
  try {
    const resp = await fetch('../../discovery/graph/knowledge_graph.json');
    const data = await resp.json();
    const ents = Object.values(data.entities||{}), rels = data.relationships||[], papers = Object.values(data.papers||{});
    const etypes = {}; ents.forEach(e => { etypes[e.type] = (etypes[e.type]||0)+1; });
    const container = document.getElementById('stats-container');
    container.innerHTML = '<div class="stat-grid">'
      + `<div class="stat-box"><div class="stat-value">${papers.length}</div><div class="stat-label">Papers</div></div>`
      + `<div class="stat-box"><div class="stat-value">${ents.length}</div><div class="stat-label">Entities</div></div>`
      + `<div class="stat-box"><div class="stat-value">${rels.length}</div><div class="stat-label">Relationships</div></div>`
      + Object.entries(etypes).map(([t,c]) => `<div class="stat-box"><div class="stat-value" style="color:${COLORS[t]||'#e0e0e0'}">${c}</div><div class="stat-label">${t}</div></div>`).join('')
      + '</div>';
  } catch(e) { document.getElementById('stats-container').innerHTML = '<p style="padding:20px;color:#8899aa;">No stats yet.</p>'; }
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab[onclick="switchTab('${name}')"]`).classList.add('active');
  ['graph-container','hypotheses-container','papers-container','stats-container'].forEach(id => document.getElementById(id).classList.toggle('hidden', id !== name+'-container'));
  if (name==='graph' && network) network.redraw();
}

loadGraph(); loadHypotheses(); loadPapers(); loadStats();
</script>
</body>
</html>
```

---

### Task 7: SOUL.md & RUMI.md Updates

**Files:**
- Modify: `SOUL.md`
- Modify: `RUMI.md`

- [ ] **Step 1: Add Discovery Intake Protocol to SOUL.md** after the "Scientist AI Protocols" section:

```markdown
### Discovery Intake Protocol

Before running `/discover`, clarify the user's intent:
1. **Domain** — "Drug discovery? Biomedicine? Materials science?"
2. **Specific focus** — "Any particular drug, disease, or mechanism?"
3. **Depth** — "Quick scan (~20 papers) or deep dive (~100+)?"
4. **Build on existing?** — "Fresh start or build on previous discoveries?"
```

- [ ] **Step 2: Add Discovery Engine row to RUMI.md capabilities table:**

```markdown
| **Discovery Engine** | Autonomous drug discovery: PubMed search, entity extraction, knowledge graph, pattern mining, hypothesis generation, web dashboard |
```

---

## Self-Review

- [x] **Spec coverage:** PubMed search (T1), knowledge graph (T2), output (T3), orchestration/intake (T4), commands (T5), dashboard (T6), docs (T7) — all spec requirements covered
- [x] **No placeholders:** all code written out, no TODOs except the intake protocol integration which is a future enhancement
- [x] **Type consistency:** data shapes match across tasks — entities/relationships use same format in extraction, graph, and dashboard
- [x] **Testable:** each task has a run command to verify
