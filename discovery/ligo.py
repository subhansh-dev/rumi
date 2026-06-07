"""LIGO - Gravitational wave event catalog."""
import urllib.request, json, time
BASE = "https://gracedb.ligo.org/api"

def _fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None

def search_events(query="", limit=20):
    time.sleep(0.5)
    url = f"{BASE}/events/?format=json&pagesize={limit}"
    data = _fetch(url)
    if not data:
        return []
    return [{"name": e.get("name",""), "event_id": e.get("id",""), "group": e.get("group",""), "pipeline": e.get("pipeline",""), "source": "ligo"} for e in (data if isinstance(data, list) else [])]

def enrich_entities(graph): return 0
