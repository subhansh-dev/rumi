import json
import urllib.request
import urllib.parse
import time

FDA_BASE = "https://api.fda.gov"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 0.3:
        time.sleep(0.3 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch(url: str) -> dict | None:
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def get_side_effects(drug_name: str, limit: int = 20) -> list[dict]:
    query = urllib.parse.quote(f'patient.drug.medicinalproduct:"{drug_name}"')
    url = f"{FDA_BASE}/drug/event.json?search={query}&count=patient.reaction.reactionmeddrapt.exact&limit={limit}"
    data = _fetch(url)
    if not data:
        return []
    return [
        {"reaction": item["term"], "count": item["count"]}
        for item in data.get("results", [])
    ]


def get_labeling(drug_name: str) -> dict | None:
    query = urllib.parse.quote(f'openfda.brand_name:"{drug_name}"')
    url = f"{FDA_BASE}/drug/label.json?search={query}&limit=1"
    data = _fetch(url)
    if not data:
        return None
    results = data.get("results", [])
    if not results:
        return None
    r = results[0]
    return {
        "mechanism_of_action": _join_field(r.get("mechanism_of_action", [])),
        "indications": _join_field(r.get("indications_and_usage", [])),
        "warnings": _join_field(r.get("boxed_warnings", [])) or _join_field(r.get("warnings_and_cautions", [])),
    }


def _join_field(field: list) -> str:
    if not field:
        return ""
    return " ".join(field)[:500]
