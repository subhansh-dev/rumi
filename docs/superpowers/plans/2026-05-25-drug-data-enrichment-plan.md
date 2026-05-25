# Drug Data Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add PubChem and OpenFDA lookups to RUMI's Discovery Engine so drug entities in the knowledge graph are enriched with real targets, properties, and side effects.

**Architecture:** Two new standalone modules (`pubchem.py`, `openfda.py`) that call free REST APIs. The existing pipeline is modified to call these after entity extraction. A new `/enrich` command enriches existing graphs.

**Tech Stack:** Python 3.11, urllib (PubChem PUG REST API, OpenFDA API), json

---

## File Structure

| File | Change |
|---|---|
| `discovery/pubchem.py` | Create — PubChem compound search, targets, properties |
| `discovery/openfda.py` | Create — OpenFDA side effects, drug labeling |
| `discovery/output.py` | Modify — show enriched data in stats |
| `main.py` | Modify — add enrichment step to pipeline, add `/enrich` handler |
| `ui.py` | Modify — add `/enrich` to SLASH_COMMANDS |

---

### Task 1: discovery/pubchem.py — PubChem API

**Files:**
- Create: `discovery/pubchem.py`

**Write `discovery/pubchem.py`:**

```python
import json
import urllib.request
import urllib.parse
import time

PUG_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 0.5:
        time.sleep(0.5 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch(url: str) -> dict | None:
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def search_compound(name: str) -> dict | None:
    """Search PubChem by drug name. Returns {cid, name, properties, synonyms} or None."""
    url = f"{PUG_BASE}/compound/name/{urllib.parse.quote(name)}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,InChIKey/JSON"
    data = _fetch(url)
    if not data:
        return None
    props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
    cid = str(props.get("CID", ""))

    synonyms = []
    syn_url = f"{PUG_BASE}/compound/cid/{cid}/synonyms/JSON"
    syn_data = _fetch(syn_url)
    if syn_data:
        synonyms = syn_data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])

    return {
        "cid": cid,
        "name": props.get("Title", name),
        "molecular_formula": props.get("MolecularFormula", ""),
        "molecular_weight": props.get("MolecularWeight", ""),
        "smiles": props.get("CanonicalSMILES", ""),
        "inchikey": props.get("InChIKey", ""),
        "synonyms": synonyms[:20],
    }


def get_targets(name: str) -> list[dict]:
    """Get gene/protein targets for a compound from PubChem bioassays."""
    url = f"{PUG_BASE}/compound/name/{urllib.parse.quote(name)}/targets/JSON"
    data = _fetch(url)
    if not data:
        return []
    results = []
    info_list = data.get("InformationList", {}).get("Information", [])
    for info in info_list:
        for target in info.get("Target", []):
            results.append({
                "name": target.get("Name", ""),
                "type": target.get("TargetType", ""),
                "organism": target.get("Organism", ""),
            })
    return results[:20]


def get_properties(name: str) -> dict:
    """Quick property lookup, returns dict or empty."""
    result = search_compound(name)
    if result:
        return {
            "molecular_formula": result["molecular_formula"],
            "molecular_weight": result["molecular_weight"],
            "smiles": result["smiles"],
            "inchikey": result["inchikey"],
        }
    return {}
```

**Verify:**
```bash
python -c "import sys; sys.path.insert(0,'.'); from discovery.pubchem import search_compound, get_targets; r=search_compound('metformin'); print(r['cid'], r['molecular_formula']); t=get_targets('metformin'); print(len(t), 'targets found')"
```
Expected: CID, formula, and some targets printed.

---

### Task 2: discovery/openfda.py — OpenFDA API

**Files:**
- Create: `discovery/openfda.py`

**Write `discovery/openfda.py`:**

```python
import json
import urllib.request
import urllib.parse
import time

FDA_BASE = "https://api.fda.gov"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 0.3:
        time.sleep(0.3 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch(url: str) -> dict | None:
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def get_side_effects(drug_name: str, limit: int = 20) -> list[dict]:
    """Get top adverse reactions for a drug from FAERS data."""
    query = urllib.parse.quote(f'patient.drug.medicinalproduct:"{drug_name}"')
    url = f"{FDA_BASE}/drug/event.json?search={query}&count=patient.reaction.reactionmeddrapt.exact&limit={limit}"
    data = _fetch(url)
    if not data:
        return []
    return [
        {"reaction": item["term"], "count": item["count"]}
        for item in data.get("results", [])
    ]


def get_labeling(drug_name: str) -> dict | None:
    """Get drug labeling info: mechanism, indications, warnings."""
    query = urllib.parse.quote(f'openfda.brand_name:"{drug_name}"')
    url = f"{FDA_BASE}/drug/label.json?search={query}&limit=1"
    data = _fetch(url)
    if not data:
        return None
    results = data.get("results", [])
    if not results:
        return None
    r = results[0]
    return {
        "mechanism_of_action": _join_field(r.get("mechanism_of_action", [])),
        "indications": _join_field(r.get("indications_and_usage", [])),
        "warnings": _join_field(r.get("boxed_warnings", [])) or _join_field(r.get("warnings_and_cautions", [])),
    }


def _join_field(field: list) -> str:
    if not field:
        return ""
    return " ".join(field)[:500]
```

**Verify:**
```bash
python -c "import sys; sys.path.insert(0,'.'); from discovery.openfda import get_side_effects, get_labeling; se=get_side_effects('metformin'); print(len(se), 'side effects'); lb=get_labeling('metformin'); print('Mechanism:', (lb.get('mechanism_of_action','')[:80] if lb else 'N/A'))"
```
Expected: Side effects list and mechanism of action printed.

---

### Task 3: Modify main.py — Add enrichment to pipeline + /enrich handler

**Files:**
- Modify: `C:\Users\Admin\Desktop\rumi\main.py`

**Step 1: Add enrichment method to RumiLive class.**

Find the Discovery Engine section (near `_run_discovery_pipeline`) and add:

```python
async def _enrich_drug_entities(self, graph):
    """Enrich all drug entities in the graph with PubChem and OpenFDA data."""
    from discovery.pubchem import search_compound, get_targets
    from discovery.openfda import get_side_effects, get_labeling

    drug_entities = {
        eid: ent for eid, ent in graph.entities.items()
        if ent["type"] == "drug"
    }
    if not drug_entities:
        self._post_output("No drug entities found to enrich.")
        return

    enriched = 0
    for eid, ent in drug_entities.items():
        drug_name = ent["name"]

        # PubChem: properties + targets
        pc = search_compound(drug_name)
        if pc:
            if pc["molecular_formula"]:
                prop_eid = f"property_{drug_name.lower().replace(' ', '_')}_mw"
                if prop_eid not in graph.entities:
                    graph.entities[prop_eid] = {
                        "id": prop_eid, "type": "property",
                        "name": f"{drug_name} MW: {pc['molecular_weight']}",
                        "papers": [],
                    }
            targets = get_targets(drug_name)
            for t in targets:
                if t["name"]:
                    tid = f"{'gene' if t['type']=='GENE' else 'protein'}_{t['name'].lower()}"
                    if tid not in graph.entities:
                        graph.entities[tid] = {
                            "id": tid,
                            "type": "gene" if t["type"] == "GENE" else "protein",
                            "name": t["name"],
                            "papers": [],
                        }
                    graph.relationships.append({
                        "source": eid, "relation": "has_target",
                        "target": tid, "confidence": 0.8, "papers": [],
                    })

        # OpenFDA: side effects
        side_effects = get_side_effects(drug_name)
        for se in side_effects[:10]:
            seid = f"side_effect_{se['reaction'].lower().replace(' ', '_')}"
            if seid not in graph.entities:
                graph.entities[seid] = {
                    "id": seid, "type": "side_effect",
                    "name": se["reaction"], "papers": [],
                }
            graph.relationships.append({
                "source": eid, "relation": "has_side_effect",
                "target": seid, "confidence": 0.7,
                "papers": [], "count": se["count"],
            })
        enriched += 1

    graph.save()
    self._post_output(f"Enriched {enriched} drug entities with PubChem + OpenFDA data.")
```

**Step 2: Add enrichment call to `_run_discovery_pipeline`.**

After `graph.save()` and before hypothesis generation, add:

```python
self._post_output("Enriching drug entities with PubChem + OpenFDA data...")
await self._enrich_drug_entities(graph)
```

**Step 3: Add `/enrich` handler to `_on_discovery_command`.**

Find the `_on_discovery_command` method and add:

```python
elif command == "enrich":
    from discovery.graph import KnowledgeGraph
    graph = KnowledgeGraph.load()
    asyncio.run_coroutine_threadsafe(
        self._enrich_drug_entities(graph), self._loop
    )
```

---

### Task 4: Modify ui.py — Add /enrich command

**Files:**
- Modify: `C:\Users\Admin\Desktop\rumi\ui.py`

**Step 1: Add `/enrich` to SLASH_COMMANDS list:**

```python
SLASH_COMMANDS = [
    "/help", "/clear", "/focus", "/think", "/dive",
    "/mute", "/status", "/stats", "/model", "/exit",
    "/science", "/discover", "/search", "/enrich", "/hypothesize", "/experiment",
    "/papers", "/review", "/graph", "/dashboard", "/discoveries", "/notebook", "/domains",
    "/personality",
]
```

**Step 2: Add handler in `_handle_command`:**

```python
elif cmd == "/enrich":
    self.write_log("SYS: Enriching drug entities with PubChem + OpenFDA...")
    if self.on_discovery_command:
        threading.Thread(target=self.on_discovery_command, args=("enrich", ""), daemon=True).start()
```

---

## Self-Review

- [x] **Spec coverage:** pubchem.py (Task 1), openfda.py (Task 2), pipeline enrichment + /enrich (Task 3), ui command (Task 4) — all spec requirements covered
- [x] **No placeholders:** all code written out
- [x] **Type consistency:** data formats match between pubchem.py return types and main.py enrichment code
