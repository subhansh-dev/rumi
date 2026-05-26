"""OpenAlex API — free, no key required (email recommended for polite pool).

For social sciences domain. Provides paper search, concepts, institutions.
250M+ scholarly works indexed. API: https://api.openalex.org
"""

import json
import time
import urllib.request
import urllib.parse

OPENALEX_BASE = "https://api.openalex.org"
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
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0 (mailto:research@rumi.ai)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def search_works(query: str, limit: int = 5) -> list[dict]:
    """Search scholarly works by keyword."""
    params = {"search": query, "per_page": limit, "sort": "cited_by_count:desc"}
    url = f"{OPENALEX_BASE}/works?{urllib.parse.urlencode(params)}"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for r in data.get("results", [])[:limit]:
        results.append({
            "title": r.get("title", ""),
            "doi": r.get("doi", ""),
            "publication_year": r.get("publication_year"),
            "cited_by_count": r.get("cited_by_count", 0),
            "type": r.get("type", ""),
            "open_access": r.get("open_access", {}).get("is_oa", False),
            "concepts": [c.get("display_name", "") for c in r.get("concepts", [])[:5]],
            "source": (r.get("source") or {}).get("display_name", ""),
        })
    return results


def search_concepts(query: str, limit: int = 5) -> list[dict]:
    """Search OpenAlex research concepts."""
    params = {"search": query, "per_page": limit}
    url = f"{OPENALEX_BASE}/concepts?{urllib.parse.urlencode(params)}"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for r in data.get("results", [])[:limit]:
        results.append({
            "name": r.get("display_name", ""),
            "level": r.get("level", 0),
            "works_count": r.get("works_count", 0),
            "description": (r.get("description") or "")[:300],
        })
    return results


def enrich_entities(graph, entity_types: set[str] = {"theory", "concept", "phenomenon", "institution", "methodology"}) -> int:
    """Enrich social science entities with OpenAlex data."""
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        papers = search_works(name, limit=2)
        if papers:
            graph.entities[eid].setdefault("openalex", {"works": papers})
            enriched += 1
    return enriched
