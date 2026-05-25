"""NASA API wrapper — free key at api.nasa.gov.

Provides: image library, exoplanet data, near-Earth objects.
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

API_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
NASA_BASE = "https://api.nasa.gov"
_LAST_CALL = 0.0


def _get_key() -> str:
    cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8-sig"))
    return cfg.get("nasa_api_key", "") or cfg.get("nasa_api_key", "DEMO_KEY")


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


def search_images(query: str, limit: int = 5) -> list[dict]:
    """Search NASA image library."""
    q = urllib.parse.quote(query)
    url = f"https://images-api.nasa.gov/search?q={q}&media_type=image&page_size={limit}"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for item in data.get("collection", {}).get("items", [])[:limit]:
        data_node = item.get("data", [{}])[0]
        links = item.get("links", [{}])
        results.append({
            "title": data_node.get("title", ""),
            "description": data_node.get("description", "")[:300],
            "photographer": data_node.get("photographer", ""),
            "date": data_node.get("date_created", ""),
            "nasa_id": data_node.get("nasa_id", ""),
            "thumbnail": links[0].get("href", "") if links else "",
        })
    return results


def search_exoplanets(name: str = "", limit: int = 5) -> list[dict]:
    """Search exoplanet data via NASA Exoplanet Archive."""
    where = f"%20where%20pl_name%20like%20'%25{urllib.parse.quote(name)}%25'" if name else "%20where%20pl_name%20is%20not%20null"
    url = f"https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+pl_name,pl_rade,pl_masse,pl_orbper,pl_eqt,st_dist,sy_dist+from+pscomppars{where}&format=json&limit={limit}"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for row in data:
        results.append({
            "name": row.get("pl_name", ""),
            "radius_earth": row.get("pl_rade"),
            "mass_earth": row.get("pl_masse"),
            "orbital_period_days": row.get("pl_orbper"),
            "equilibrium_temp": row.get("pl_eqt"),
            "distance_pc": row.get("sy_dist") or row.get("st_dist"),
        })
    return results


def get_neo(start_date: str = "", end_date: str = "", limit: int = 10) -> list[dict]:
    """Get near-Earth objects. Date format: YYYY-MM-DD."""
    key = _get_key()
    if not key:
        return []
    import datetime
    if not start_date:
        start_date = str(datetime.date.today())
    params = urllib.parse.urlencode({"start_date": start_date, "api_key": key})
    url = f"{NASA_BASE}/neo/rest/v1/feed?{params}"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for date_key in sorted(data.get("near_earth_objects", {}).keys()):
        for neo in data["near_earth_objects"][date_key][:limit]:
            diameter = neo.get("estimated_diameter", {}).get("meters", {})
            results.append({
                "name": neo.get("name", ""),
                "diameter_m": diameter.get("estimated_diameter_max"),
                "hazardous": neo.get("is_potentially_hazardous_asteroid", False),
                "magnitude": neo.get("absolute_magnitude_h"),
                "close_approach": neo.get("close_approach_data", [{}])[0].get("close_approach_date", "") if neo.get("close_approach_data") else "",
                "velocity_km_s": neo.get("close_approach_data", [{}])[0].get("relative_velocity", {}).get("kilometers_per_second", "") if neo.get("close_approach_data") else "",
            })
    return results


def is_available() -> bool:
    key = _get_key()
    return bool(key) and key != "DEMO_KEY"


def enrich_entities(graph, entity_types: set[str] = {"celestial_body", "exoplanet", "star", "galaxy"}) -> int:
    """Enrich space-related entities with NASA data."""
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        # Try exoplanet lookup
        exo = search_exoplanets(name, limit=1)
        if exo:
            graph.entities[eid].setdefault("nasa", {})["exoplanet"] = exo[0]
            enriched += 1
            continue
        # Try image search for context
        images = search_images(name, limit=1)
        if images:
            graph.entities[eid].setdefault("nasa", {})["image"] = images[0]
            enriched += 1
    return enriched
