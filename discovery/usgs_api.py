"""USGS API — free, no key needed.

For earth science domain. Provides: earthquake data, volcano info.
"""

import json
import time
import urllib.request
import urllib.parse

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
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def search_earthquakes(query: str = "", limit: int = 5) -> list[dict]:
    """Search recent earthquakes by region or magnitude."""
    params = {"format": "geojson", "limit": limit, "orderby": "magnitude"}
    if query:
        params["region"] = query
    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?{urllib.parse.urlencode(params)}"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for f in data.get("features", [])[:limit]:
        props = f.get("properties", {})
        coords = f.get("geometry", {}).get("coordinates", [])
        results.append({
            "place": props.get("place", ""),
            "magnitude": props.get("mag"),
            "depth_km": abs(coords[2]) if len(coords) > 2 else None,
            "time": props.get("time", ""),
            "url": props.get("url", ""),
            "tsunami": props.get("tsunami", 0) == 1,
            "status": props.get("status", ""),
        })
    return results


def enrich_entities(graph, entity_types: set[str] = {"geological_feature", "mineral", "process", "event"}) -> int:
    """Enrich geology entities with USGS data."""
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        eq = search_earthquakes(name, limit=1)
        if eq:
            graph.entities[eid].setdefault("usgs", {})["earthquake"] = eq[0]
            enriched += 1
    return enriched
