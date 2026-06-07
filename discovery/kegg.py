"""KEGG - Kyoto Encyclopedia of Genes and Genomes."""
import urllib.request, urllib.parse, json, time
BASE = "https://rest.kegg.jp"

def _fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode()
    except Exception:
        return None

def search_pathways(query, limit=5):
    time.sleep(0.5)
    url = f"{BASE}/find/pathway/{urllib.parse.quote(query)}"
    data = _fetch(url)
    if not data: return []
    return [{"id": l.split("\t")[0], "name": l.split("\t")[1] if "\t" in l else l, "source": "kegg"} for l in data.strip().split("\n")[:limit]]

def enrich_entities(graph): return 0
