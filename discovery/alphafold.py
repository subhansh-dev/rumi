"""AlphaFold - Protein structure predictions (DeepMind)."""
import urllib.request, json, time
BASE = "https://alphafold.ebi.ac.uk/api"

def _fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None

def predict_structure(uniprot_id):
    time.sleep(0.3)
    url = f"{BASE}/prediction/{uniprot_id}"
    data = _fetch(url)
    if not data or not isinstance(data, list) or not data:
        return None
    entry = data[0]
    return {"uniprot_id": uniprot_id, "pdb_url": entry.get("pdbUrl", ""), "confidence": entry.get("confidenceType", "")}

def enrich_entities(graph):
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent.get("type") == "protein":
            uid = ent.get("uniprot_id", "")
            if uid:
                result = predict_structure(uid)
                if result:
                    ent.setdefault("enrichment", {})["alphafold"] = result
                    enriched += 1
    return enriched
