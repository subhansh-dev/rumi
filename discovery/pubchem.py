import json
import urllib.request
import urllib.parse
import time

PUG_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 0.5:
        time.sleep(0.5 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch(url: str) -> dict | None:
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def search_compound_by_smiles(smiles: str) -> dict | None:
    url = f"{PUG_BASE}/compound/smiles/{urllib.parse.quote(smiles)}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,InChIKey/JSON"
    data = _fetch(url)
    if not data:
        return None
    props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
    cid = str(props.get("CID", ""))
    if not cid or cid == "0":
        return None
    synonyms = []
    syn_url = f"{PUG_BASE}/compound/cid/{cid}/synonyms/JSON"
    syn_data = _fetch(syn_url)
    if syn_data:
        synonyms = syn_data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])
    return {
        "cid": cid,
        "synonyms": synonyms[:20],
        "name": props.get("Title", ""),
    }


def search_compound(name: str) -> dict | None:
    url = f"{PUG_BASE}/compound/name/{urllib.parse.quote(name)}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,InChIKey/JSON"
    data = _fetch(url)
    if not data:
        return None
    props = data.get("PropertyTable", {}).get("Properties", [{}])[0]
    cid = str(props.get("CID", ""))

    synonyms = []
    syn_url = f"{PUG_BASE}/compound/cid/{cid}/synonyms/JSON"
    syn_data = _fetch(syn_url)
    if syn_data:
        synonyms = syn_data.get("InformationList", {}).get("Information", [{}])[0].get("Synonym", [])

    smiles = (props.get("CanonicalSMILES") or props.get("SMILES") or props.get("ConnectivitySMILES") or "")

    return {
        "cid": cid,
        "name": props.get("Title", name),
        "molecular_formula": props.get("MolecularFormula", ""),
        "molecular_weight": props.get("MolecularWeight", ""),
        "smiles": smiles,
        "inchikey": props.get("InChIKey", ""),
        "synonyms": synonyms[:20],
    }


def get_targets(name: str) -> list[dict]:
    url = f"{PUG_BASE}/compound/name/{urllib.parse.quote(name)}/targets/JSON"
    data = _fetch(url)
    if not data:
        return []
    results = []
    for info in data.get("InformationList", {}).get("Information", []):
        for target in info.get("Target", []):
            results.append({
                "name": target.get("Name", ""),
                "type": target.get("TargetType", ""),
                "organism": target.get("Organism", ""),
            })
    return results[:20]


def get_properties(name: str) -> dict:
    result = search_compound(name)
    if result:
        return {
            "molecular_formula": result["molecular_formula"],
            "molecular_weight": result["molecular_weight"],
            "smiles": result["smiles"],
            "inchikey": result["inchikey"],
        }
    return {}
