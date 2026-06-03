"""Semantic Scholar API — free REST API, no key needed.

For all domains. Provides: paper citations, influence scores, embeddings.
Rate limit: 100 req/min without key, 1000 req/min with free key.
"""

import json
import time
import urllib.request
import urllib.parse

S2_BASE = "https://api.semanticscholar.org/graph/v1"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 0.6:
        time.sleep(0.6 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch(url: str) -> dict | None:
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def search_papers(query: str, limit: int = 20) -> list[dict]:
    """Search papers with citation influence metrics and abstracts."""
    q = urllib.parse.quote(query)
    url = f"{S2_BASE}/paper/search?query={q}&limit={limit}&fields=title,year,citationCount,influentialCitationCount,authors,abstract,externalIds"
    data = _fetch(url)
    if not data:
        return []
    return [
        {
            "title": p.get("title", "") if isinstance(p, dict) else str(p),
            "year": p.get("year") if isinstance(p, dict) else None,
            "abstract": p.get("abstract", "") if isinstance(p, dict) else "",
            "citation_count": p.get("citationCount", 0) if isinstance(p, dict) else 0,
            "influential_citations": p.get("influentialCitationCount", 0) if isinstance(p, dict) else 0,
            "authors": [a.get("name", "") if isinstance(a, dict) else str(a) for a in (p.get("authors", []) if isinstance(p, dict) else [])[:5]],
            "paperId": p.get("paperId", "") if isinstance(p, dict) else "",
            "arxivId": ((p.get("externalIds") or {}).get("ArXiv", "")) if isinstance(p, dict) else "",
            "pmid": ((p.get("externalIds") or {}).get("PubMed", "")) if isinstance(p, dict) else "",
        }
        for p in (data.get("data", []) if isinstance(data, dict) else [])
    ]


def get_paper_influence(title: str) -> dict | None:
    """Get citation influence for a specific paper by title."""
    q = urllib.parse.quote(title)
    url = f"{S2_BASE}/paper/search?query={q}&limit=1&fields=title,citationCount,influentialCitationCount,embedding"
    data = _fetch(url)
    if not data or not data.get("data"):
        return None
    p = data["data"][0]
    result = {
        "title": p.get("title", ""),
        "citation_count": p.get("citationCount", 0),
        "influential_citations": p.get("influentialCitationCount", 0),
    }
    embed = p.get("embedding")
    if embed and embed.get("vector"):
        result["has_embedding"] = True
    return result


def enrich_entities(graph) -> int:
    """Enrich paper entities in graph with Semantic Scholar citation data.

    Returns count of enriched papers.
    """
    enriched = 0
    for pmid, paper in list(graph.papers.items()):
        title = paper.get("title", "")
        if not title:
            continue
        info = get_paper_influence(title)
        if info:
            paper["citation_count"] = info.get("citation_count", 0)
            paper["influential_citations"] = info.get("influential_citations", 0)
            enriched += 1
    return enriched


def get_references(paper_id: str, limit: int = 20) -> list[dict]:
    """Get papers that this paper cites (outgoing references)."""
    url = f"{S2_BASE}/paper/{paper_id}/references?limit={limit}&fields=title,year,citationCount,influentialCitationCount,authors,abstract,externalIds"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for ref in (data.get("data", []) if isinstance(data, dict) else []):
        p = ref.get("citedPaper", {}) if isinstance(ref, dict) else {}
        if not p or not p.get("title"):
            continue
        results.append({
            "title": p.get("title", ""),
            "year": p.get("year"),
            "abstract": p.get("abstract", "") or "",
            "citation_count": p.get("citationCount", 0) or 0,
            "influential_citations": p.get("influentialCitationCount", 0) or 0,
            "authors": [a.get("name", "") for a in (p.get("authors") or [])[:5]],
            "paperId": p.get("paperId", ""),
            "arxivId": ((p.get("externalIds") or {}).get("ArXiv", "")),
        })
    return results


def get_citations(paper_id: str, limit: int = 20) -> list[dict]:
    """Get papers that cite this paper (incoming citations)."""
    url = f"{S2_BASE}/paper/{paper_id}/citations?limit={limit}&fields=title,year,citationCount,influentialCitationCount,authors,abstract,externalIds"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for cit in (data.get("data", []) if isinstance(data, dict) else []):
        p = cit.get("citingPaper", {}) if isinstance(cit, dict) else {}
        if not p or not p.get("title"):
            continue
        results.append({
            "title": p.get("title", ""),
            "year": p.get("year"),
            "abstract": p.get("abstract", "") or "",
            "citation_count": p.get("citationCount", 0) or 0,
            "influential_citations": p.get("influentialCitationCount", 0) or 0,
            "authors": [a.get("name", "") for a in (p.get("authors") or [])[:5]],
            "paperId": p.get("paperId", ""),
            "arxivId": ((p.get("externalIds") or {}).get("ArXiv", "")),
        })
    return results
