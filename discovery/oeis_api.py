"""OEIS API — free, no key needed.

For mathematics domain. Provides integer sequence search and metadata.
"""

import json
import time
import urllib.request
import urllib.parse

OEIS_BASE = "https://oeis.org/search"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 2.0:
        time.sleep(2.0 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch(url: str) -> dict | None:
    _rate_limit()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def search_sequences(query: str, limit: int = 5) -> list[dict]:
    """Search OEIS for integer sequences by keyword or ID."""
    params = {"q": query, "fmt": "json", "start": 0}
    url = f"{OEIS_BASE}?{urllib.parse.urlencode(params)}"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for item in data.get("results", [])[:limit]:
        results.append({
            "id": item.get("number", ""),
            "name": (item.get("name") or "")[:300],
            "data": (item.get("data") or "")[:120],
            "formula": (item.get("formula") or "")[:200],
            "references": item.get("references", []),
            "links": item.get("links", []),
        })
    return results


def enrich_entities(graph, entity_types: set[str] = {"sequence", "constant", "theorem", "function"}) -> int:
    """Enrich math entities with OEIS integer sequence data."""
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        seqs = search_sequences(name, limit=1)
        if seqs:
            graph.entities[eid].setdefault("oeis", seqs[0])
            enriched += 1
    return enriched
