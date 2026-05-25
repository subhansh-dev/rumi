"""Protein Data Bank (RCSB) enrichment — free REST API, no key needed.

For molecular biology, neuroscience, and drug discovery domains.
Provides: protein structures, ligands, sequence data, function.
"""

import json
import time
import urllib.request
import urllib.parse

PDB_BASE = "https://data.rcsb.org/rest/v1"
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


def _fetch_text(url: str) -> str | None:
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode()
    except Exception:
        return None


def search_protein(name: str, limit: int = 3) -> list[dict]:
    """Search PDB by protein or gene name. Returns structure info."""
    query = {
        "query": {
            "type": "terminal",
            "service": "full_text",
            "parameters": {"value": name, "operator": "contains"}
        },
        "return_type": "entry",
        "request_options": {"paginate": {"start": 0, "rows": limit}}
    }
    url = "https://search.rcsb.org/rcsbsearch/v2/query"
    _rate_limit()
    try:
        req = urllib.request.Request(
            url, data=json.dumps(query).encode(),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return []

    results = []
    for entry in data.get("result_set", [])[:limit]:
        pdb_id = entry.get("identifier", "")
        if not pdb_id:
            continue
        detail = _fetch(f"{PDB_BASE}/core/entry/{pdb_id}")
        if not detail:
            continue
        results.append({
            "pdb_id": pdb_id,
            "title": detail.get("struct", {}).get("title", ""),
            "method": detail.get("exptl", [{}])[0].get("method", ""),
            "resolution": detail.get("rcsb_entry_info", {}).get("resolution_combined", [{}])[0].get("value", ""),
            "deposited": detail.get("rcsb_accession_info", {}).get("deposit_date", ""),
        })
    return results


def get_ligands(pdb_id: str) -> list[dict]:
    """Get non-polymer ligands for a PDB structure."""
    url = f"{PDB_BASE}/core/entry/{pdb_id}"
    data = _fetch(url)
    if not data:
        return []
    ligands = []
    for group in data.get("rcsb_entry_container_identifiers", {}).get("non_polymer_entity_ids", []):
        lig_url = f"{PDB_BASE}/core/nonpolymer_entity/{pdb_id}/{group}"
        lig_data = _fetch(lig_url)
        if lig_data:
            ligands.append({
                "id": group,
                "name": lig_data.get("pdbx_entity_nonpoly", {}).get("name", ""),
                "formula": lig_data.get("chem_comp", {}).get("formula", ""),
            })
    return ligands


def enrich_entities(graph, entity_types: set[str] = {"protein", "gene"}) -> int:
    """Enrich protein/gene entities in graph with PDB data.

    Returns count of enriched entities.
    """
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        results = search_protein(name, limit=1)
        if not results:
            continue
        r = results[0]
        pdb_data = graph.entities[eid].setdefault("pdb", {})
        pdb_data["pdb_id"] = r["pdb_id"]
        pdb_data["title"] = r["title"]
        pdb_data["method"] = r["method"]
        if r.get("resolution"):
            pdb_data["resolution"] = r["resolution"]
        ligands = get_ligands(r["pdb_id"])
        if ligands:
            pdb_data["ligands"] = [l["name"] for l in ligands[:5] if l["name"]]
        enriched += 1
    return enriched
