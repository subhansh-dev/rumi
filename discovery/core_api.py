"""CORE - Open access research papers."""
import urllib.request, urllib.parse, json, time
BASE = "https://api.core.ac.uk/v3"

def _fetch(url, api_key=""):
    try:
        headers = {"User-Agent": "RUMI/1.0"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None

def search_papers(query, limit=10, api_key=""):
    time.sleep(0.5)
    url = f"{BASE}/search/works?q={urllib.parse.quote(query)}&limit={limit}"
    data = _fetch(url, api_key)
    if not data: return []
    return [{"title": r.get("title",""), "abstract": (r.get("abstract") or "")[:600],
             "authors": [a.get("name","") for a in (r.get("authors") or [])[:5]],
             "year": str(r.get("yearPublished","")), "doi": r.get("doi",""), "source": "core"}
            for r in data.get("results", [])]

def enrich_entities(graph): return 0
