"""OpenCitations - Open citation data."""
import urllib.request, json, time
BASE = "https://opencitations.net/index/api/v1"

def _fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None

def get_citations(doi, limit=10):
    time.sleep(0.5)
    url = f"{BASE}/citations/{doi}"
    data = _fetch(url)
    if not data: return []
    return [{"citing_doi": c.get("citing",""), "cited_doi": c.get("cited",""), "source": "opencitations"} for c in data[:limit]]

def enrich_entities(graph): return 0
