"""Materials Project REST API — free key required (register at materialsproject.org).

For materials science domain. Provides: crystal structure, band gap,
formation energy, density, elastic properties.
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

API_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
MP_BASE = "https://api.materialsproject.org"
_LAST_CALL = 0.0


def _get_key() -> str:
    cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8-sig"))
    return cfg.get("materials_project_api_key", "") or cfg.get("mp_api_key", "")


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 1.0:
        time.sleep(1.0 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch(url: str) -> dict | None:
    key = _get_key()
    if not key:
        return None
    _rate_limit()
    try:
        req = urllib.request.Request(url, headers={"X-API-Key": key})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def search_material(name: str, limit: int = 3) -> list[dict]:
    """Search materials by name or formula."""
    q = urllib.parse.quote(name)
    url = f"{MP_BASE}/materials/summary?formula={q}&_per_page={limit}&_fields=material_id,formula_pretty,crystal_system,space_group,symmetry,band_gap,energy_per_atom,density"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for doc in data.get("data", [])[:limit]:
        results.append({
            "material_id": doc.get("material_id", ""),
            "formula": doc.get("formula_pretty", ""),
            "crystal_system": doc.get("crystal_system", ""),
            "space_group": doc.get("symmetry", {}).get("symbol", ""),
            "band_gap": doc.get("band_gap"),
            "energy_per_atom": doc.get("energy_per_atom"),
            "density": doc.get("density"),
        })
    return results


def get_band_structure(material_id: str) -> dict | None:
    """Get band structure data for a material."""
    url = f"{MP_BASE}/materials/band_structure?material_id={material_id}"
    data = _fetch(url)
    if not data:
        return None
    docs = data.get("data", [])
    if not docs:
        return None
    d = docs[0]
    return {
        "band_gap": d.get("band_gap", {}).get("value"),
        "is_direct": d.get("is_direct"),
        "efermi": d.get("efermi"),
    }


def is_available() -> bool:
    return bool(_get_key())


def enrich_entities(graph, entity_types: set[str] = {"material", "compound", "element"}) -> int:
    """Enrich material/compound entities with Materials Project data.

    Returns count of enriched entities. Only works if API key is set.
    """
    if not _get_key():
        return 0

    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        results = search_material(name, limit=1)
        if not results:
            continue
        r = results[0]
        mp_data = graph.entities[eid].setdefault("materials_project", {})
        mp_data["formula"] = r["formula"]
        mp_data["crystal_system"] = r["crystal_system"]
        mp_data["space_group"] = r["space_group"]
        if r["band_gap"] is not None:
            mp_data["band_gap"] = r["band_gap"]
        if r["density"] is not None:
            mp_data["density"] = r["density"]
        if r["energy_per_atom"] is not None:
            mp_data["energy_per_atom"] = r["energy_per_atom"]
        enriched += 1
    return enriched
