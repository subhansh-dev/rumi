"""UniProt REST API — free, no API key needed."""

import json
import urllib.request
import urllib.parse
import time

UNIPROT_BASE = "https://rest.uniprot.org/uniprotkb"
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


def search_gene(name: str, limit: int = 3) -> list[dict]:
    """Search UniProt by gene name or protein name."""
    query = urllib.parse.quote(f'({name})')
    url = f"{UNIPROT_BASE}/search?query={query}&format=json&size={limit}"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for entry in data.get("results", []):
        genes = []
        for gene in entry.get("genes", []):
            gene_name = gene.get("geneName", {}).get("value", "")
            if gene_name:
                genes.append(gene_name)
        functions = []
        for comment in entry.get("comments", []):
            if comment.get("commentType") == "FUNCTION":
                for text in comment.get("texts", []):
                    val = text.get("value", "")
                    if val:
                        functions.append(val)
        organism = entry.get("organism", {}).get("scientificName", "")
        results.append({
            "accession": entry.get("primaryAccession", ""),
            "protein_name": entry.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value", ""),
            "gene_names": genes,
            "organism": organism,
            "function": functions[0] if functions else "",
        })
    return results


def enrich_entities(graph, entity_types: set[str] = {"gene", "protein"}) -> int:
    """Enrich gene/protein entities in the graph with UniProt data.

    Returns count of enriched entities.
    """
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        results = search_gene(name, limit=1)
        if not results:
            continue
        r = results[0]
        if r.get("gene_names"):
            if "gene" not in graph.entities[eid]:
                graph.entities[eid].setdefault("uniprot", {})
                graph.entities[eid]["uniprot"]["accession"] = r["accession"]
                graph.entities[eid]["uniprot"]["gene_names"] = r["gene_names"]
                graph.entities[eid]["uniprot"]["organism"] = r["organism"]
                if r.get("function"):
                    graph.entities[eid]["uniprot"]["function"] = r["function"]
            enriched += 1
    return enriched
