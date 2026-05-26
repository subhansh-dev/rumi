"""NCI CACTUS Chemical Identifier Resolver — free, no key needed.

For chemistry domain. Resolves chemical names to SMILES, InChI, formula, MW.
API: https://cactus.nci.nih.gov/chemical/structure
"""

import json
import time
import urllib.request
import urllib.parse

CIR_BASE = "https://cactus.nci.nih.gov/chemical/structure"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 1.0:
        time.sleep(1.0 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def _fetch_text(url: str) -> str | None:
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode().strip()
    except Exception:
        return None


def resolve(identifier: str, representation: str = "smiles") -> str | None:
    """Resolve a chemical identifier to a different representation.

    Representations: smiles, iupac_name, formula, stdinchi, stdinchikey, mw, cas
    """
    quoted = urllib.parse.quote(identifier, safe="")
    url = f"{CIR_BASE}/{quoted}/{representation}"
    return _fetch_text(url)


def resolve_all(identifier: str) -> dict | None:
    """Resolve multiple representations for a chemical."""
    result = {"name": identifier}
    for rep in ("smiles", "formula", "mw", "iupac_name", "stdinchikey", "cas"):
        val = resolve(identifier, rep)
        if val:
            result[rep] = val
    return result if len(result) > 1 else None


def enrich_entities(graph, entity_types: set[str] = {"chemical", "compound", "element"}) -> int:
    """Enrich chemistry entities with CIR chemical data."""
    enriched = 0
    for eid, ent in list(graph.entities.items()):
        if ent["type"] not in entity_types:
            continue
        name = ent["name"]
        data = resolve_all(name)
        if data:
            graph.entities[eid].setdefault("cir", data)
            enriched += 1
    return enriched
