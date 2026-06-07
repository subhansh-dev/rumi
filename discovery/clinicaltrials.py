"""ClinicalTrials.gov - Clinical trial data."""
import urllib.request, urllib.parse, json, time
BASE = "https://clinicaltrials.gov/api/v2"

def _fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None

def search_trials(query, limit=10):
    time.sleep(0.5)
    url = f"{BASE}/studies?query.term={urllib.parse.quote(query)}&pageSize={limit}"
    data = _fetch(url)
    if not data: return []
    trials = []
    for study in data.get("studies", []):
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        status = proto.get("statusModule", {})
        trials.append({"nct_id": ident.get("nctId",""), "title": ident.get("briefTitle",""), "status": status.get("overallStatus",""), "source": "clinicaltrials"})
    return trials

def enrich_entities(graph): return 0
