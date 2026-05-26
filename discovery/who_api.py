"""WHO API — free, no key needed.

For public health domain. Provides: disease burden, mortality, health indicators.
Uses WHO Global Health Observatory (GHO) API.
"""

import json
import time
import urllib.request
import urllib.parse

WHO_BASE = "https://ghoapi.azureedge.net/api"
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


def search_indicators(query: str = "", limit: int = 5) -> list[dict]:
    """Search WHO health indicators."""
    url = f"{WHO_BASE}/Indicator"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for item in data.get("value", []):
        name = item.get("IndicatorName", "") or ""
        if query and query.lower() not in name.lower():
            continue
        results.append({
            "code": item.get("IndicatorCode", ""),
            "name": name,
        })
        if len(results) >= limit:
            break
    return results


def get_disease_data(disease_name: str = "diabetes") -> dict | None:
    """Get prevalence data for a disease or condition."""
    indicators = search_indicators(disease_name, limit=3)
    if not indicators:
        return None
    code = indicators[0]["code"]
    url = f"{WHO_BASE}/{code}?$filter=ParentLocationCode eq 'Global'&$top=3"
    data = _fetch(url)
    if not data:
        return {"indicator": indicators[0]["name"], "code": code}
    values = []
    for v in data.get("value", [])[:3]:
        values.append({
            "year": v.get("TimeDimensionValue", ""),
            "value": v.get("Value", ""),
            "sex": v.get("Dim2", ""),
        })
    return {
        "indicator": indicators[0]["name"],
        "code": code,
        "values": values,
    }


def enrich_entities(graph, entity_types: set[str] = {"disease", "risk_factor", "intervention", "population"}) -> int:
    """Enrich health entities with WHO data."""
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        data = get_disease_data(name)
        if data:
            graph.entities[eid].setdefault("who", data)
            enriched += 1
    return enriched
