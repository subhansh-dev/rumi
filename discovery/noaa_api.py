"""NOAA API — free, no key needed.

For oceanography domain. Provides: tide predictions, water levels, currents.
Uses NOAA CO-OPS API and NOAA ERDDAP.
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


def search_tide_stations(query: str = "", limit: int = 5) -> list[dict]:
    """Search NOAA tide stations."""
    url = f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations.json?type=tidepredictions"
    data = _fetch(url)
    if not data:
        return []
    stations = data.get("stations", [])
    results = []
    for s in stations[:limit]:
        name = s.get("name", "").lower()
        if query and query.lower() not in name:
            continue
        results.append({
            "id": s.get("id", ""),
            "name": s.get("name", ""),
            "state": s.get("state", ""),
            "latitude": s.get("lat"),
            "longitude": s.get("lng"),
        })
    return results[:limit]


def get_ocean_data(station_id: str = "9414290") -> dict:
    """Get recent water level data for a station. Default: San Francisco."""
    import datetime
    today = str(datetime.date.today())
    url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?station={station_id}&product=water_level&date=today&datum=MLLW&units=metric&time_zone=gmt&format=json"
    data = _fetch(url)
    if not data:
        return {}
    levels = data.get("data", [])
    if not levels:
        return {}
    values = [float(l.get("v", 0)) for l in levels if l.get("v")]
    return {
        "station": station_id,
        "mean_level": round(sum(values) / len(values), 2) if values else 0,
        "max_level": round(max(values), 2) if values else 0,
        "min_level": round(min(values), 2) if values else 0,
        "observations": len(values),
    }


def enrich_entities(graph, entity_types: set[str] = {"ocean_region", "current", "phenomenon", "chemical"}) -> int:
    """Enrich oceanography entities with NOAA data."""
    enriched = 0
    # Get ocean context data
    context = get_ocean_data()
    if context:
        graph.ocean_data = context
        enriched += 1
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        stations = search_tide_stations(name, limit=1)
        if stations:
            graph.entities[eid].setdefault("noaa", stations[0])
            enriched += 1
    return enriched
