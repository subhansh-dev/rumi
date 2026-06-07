"""INSPIRE HEP - High-energy physics literature (CERN)."""
import urllib.request, urllib.parse, json, time
BASE = "https://inspirehep.net/api"
def _fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None
def search_papers(query, limit=10):
    time.sleep(0.5)
    url = f"{BASE}/literature?q={urllib.parse.quote(query)}&size={limit}&sort=mostrecent"
    data = _fetch(url)
    if not data: return []
    papers = []
    for hit in data.get("hits", {}).get("hits", []):
        meta = hit.get("metadata", {})
        titles = meta.get("titles", [{}])
        title = titles[0].get("title", "") if titles else ""
        abstract = meta.get("abstracts", [{}])[0].get("value", "")[:600] if meta.get("abstracts") else ""
        authors = [a.get("full_name", "") for a in meta.get("authors", [])[:5]]
        year = meta.get("earliest_date", "")[:4]
        papers.append({"title": title, "abstract": abstract, "authors": authors, "year": year, "source": "inspire_hep", "id": hit.get("id", "")})
    return papers
def enrich_entities(graph): return 0
