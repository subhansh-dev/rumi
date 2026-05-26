"""World Bank API — free, no key needed.

For economics domain. Provides: GDP, inflation, population, trade indicators.
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


def _fetch(url: str) -> list | None:
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


INDICATORS = {
    "gdp": "NY.GDP.MKTP.CD",
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "inflation": "FP.CPI.TOTL.ZG",
    "population": "SP.POP.TOTL",
    "unemployment": "SL.UEM.TOTL.ZS",
    "trade": "NE.EXP.GNFS.CD",
    "research_spending": "GB.XPD.RSDV.GD.ZS",
}


def get_indicator(indicator_name: str = "gdp", country: str = "US", year: int = 2023) -> dict | None:
    """Get economic indicator for a country."""
    code = INDICATORS.get(indicator_name)
    if not code:
        return None
    url = f"http://api.worldbank.org/v2/country/{country}/indicator/{code}?format=json&per_page=5&date={year}"
    data = _fetch(url)
    if not data or len(data) < 2:
        return None
    records = data[1]
    if not records:
        return None
    return {
        "indicator": indicator_name,
        "country": country,
        "year": year,
        "value": records[0].get("value"),
    }


def search_countries(query: str = "", limit: int = 5) -> list[dict]:
    """Search countries by name."""
    url = f"http://api.worldbank.org/v2/country?format=json&per_page={limit}&region=WLD"
    if query:
        url += f"&search={urllib.parse.quote(query)}"
    data = _fetch(url)
    if not data or len(data) < 2:
        return []
    results = []
    for r in data[1][:limit]:
        results.append({
            "name": r.get("name", ""),
            "code": r.get("iso2Code", ""),
            "region": r.get("region", {}).get("value", ""),
            "income_level": r.get("incomeLevel", {}).get("value", ""),
            "capital": r.get("capitalCity", ""),
            "latitude": r.get("latitude"),
            "longitude": r.get("longitude"),
        })
    return results


def enrich_entities(graph, entity_types: set[str] = {"economic_indicator", "market", "country", "institution", "sector"}) -> int:
    """Enrich economics entities with World Bank data."""
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        # Try as country
        countries = search_countries(name, 1)
        if countries:
            graph.entities[eid].setdefault("world_bank", countries[0])
            enriched += 1
            continue
        # Try as indicator
        for key in INDICATORS:
            if key in name.lower():
                val = get_indicator(key)
                if val:
                    graph.entities[eid].setdefault("world_bank", val)
                    enriched += 1
                    break
    return enriched
