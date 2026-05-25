"""GBIF (Global Biodiversity Information Facility) API — free, no key needed.

Provides: species occurrence data, species name lookup, taxonomy.
"""

import json
import time
import urllib.request
import urllib.parse

GBIF_BASE = "https://api.gbif.org/v1"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 1.0:
        time.sleep(1.0 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch(url: str) -> dict | None:
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def search_species(name: str, limit: int = 5) -> list[dict]:
    """Search species by scientific or common name."""
    q = urllib.parse.quote(name)
    url = f"{GBIF_BASE}/species/search?q={q}&limit={limit}&offset=0"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for s in data.get("results", [])[:limit]:
        results.append({
            "key": s.get("key", ""),
            "scientific_name": s.get("scientificName", "") or s.get("canonicalName", "") or s.get("species", ""),
            "kingdom": s.get("kingdom", ""),
            "phylum": s.get("phylum", ""),
            "class_": s.get("class", ""),
            "order": s.get("order", ""),
            "family": s.get("family", ""),
            "genus": s.get("genus", ""),
            "conservation_status": s.get("threatStatus", ""),
            "rank": s.get("taxonRank", ""),
        })
    return results


def get_species_details(species_key: int) -> dict | None:
    """Get detailed species information by GBIF key."""
    url = f"{GBIF_BASE}/species/{species_key}"
    data = _fetch(url)
    if not data:
        return None
    return {
        "scientific_name": data.get("scientificName", ""),
        "kingdom": data.get("kingdom", ""),
        "phylum": data.get("phylum", ""),
        "class_": data.get("class", ""),
        "order": data.get("order", ""),
        "family": data.get("family", ""),
        "genus": data.get("genus", ""),
        "conservation_status": data.get("threatStatus", ""),
        "habitat": data.get("habitat", ""),
    }


def get_occurrences(species_key: int, limit: int = 5) -> list[dict]:
    """Get occurrence records for a species."""
    url = f"{GBIF_BASE}/occurrence/search?speciesKey={species_key}&limit={limit}"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for o in data.get("results", [])[:limit]:
        results.append({
            "country": o.get("country", ""),
            "year": o.get("year", ""),
            "latitude": o.get("decimalLatitude"),
            "longitude": o.get("decimalLongitude"),
            "basis_of_record": o.get("basisOfRecord", ""),
        })
    return results


def enrich_entities(graph, entity_types: set[str] = {"species", "organism"}) -> int:
    """Enrich species/organism entities with GBIF taxonomy data.

    Returns count of enriched entities.
    """
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        results = search_species(name, limit=1)
        if not results:
            continue
        r = results[0]
        gbif_data = graph.entities[eid].setdefault("gbif", {})
        gbif_data["scientific_name"] = r["scientific_name"]
        gbif_data["kingdom"] = r["kingdom"]
        gbif_data["phylum"] = r["phylum"]
        gbif_data["class"] = r["class_"]
        gbif_data["order"] = r["order"]
        gbif_data["family"] = r["family"]
        gbif_data["genus"] = r["genus"]
        if r["conservation_status"]:
            gbif_data["conservation_status"] = r["conservation_status"]
        enriched += 1
    return enriched
