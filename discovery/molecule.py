"""Molecule design using Gemini + RDKit + PubChem validation."""

import json
import math
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, QED, Crippen, rdMolDescriptors
from rdkit.Chem.Lipinski import NumHDonors, NumHAcceptors, NumRotatableBonds

API_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"


def _get_gemini_client():
    import google.genai as genai
    cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8-sig"))
    return genai.Client(api_key=cfg.get("gemini_api_key", ""))


DEFAULT_MODEL = "gemini-2.5-flash"


def generate_smiles(target: str, num_candidates: int = 8) -> list[str]:
    """Use Gemini to generate candidate SMILES for a given target."""
    prompt = f"""You are a medicinal chemist designing small molecules that target: {target}

Generate {num_candidates} diverse drug-like small molecules as SMILES strings.

Rules:
- Each must be a valid SMILES string (organic, drug-like)
- MW < 600, LogP between -1 and 5
- Include both known drugs and novel variants
- Cover diverse chemotypes
- Prioritize molecules reported to modulate {target}

Output ONLY a JSON array of objects with keys: smiles, name (if known or 'Novel'), rationale (one sentence)

Example: [{{"smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "name": "Caffeine", "rationale": "Adenosine receptor antagonist"}}]"""

    import google.genai as genai
    from google.genai import types
    client = _get_gemini_client()
    response = client.models.generate_content(
        model=DEFAULT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=4096,
            response_mime_type="application/json",
        ),
    )
    try:
        data = json.loads(response.text)
        return data if isinstance(data, list) else data.get("molecules", [])
    except (json.JSONDecodeError, AttributeError):
        return []


def validate_smiles(entry: dict) -> dict | None:
    """Validate a SMILES with RDKit and compute drug-likeness metrics."""
    smiles = entry.get("smiles", "")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None

    mw = Descriptors.ExactMolWt(mol)
    logp = Crippen.MolLogP(mol)
    hbd = NumHDonors(mol)
    hba = NumHAcceptors(mol)
    rot_bonds = NumRotatableBonds(mol)
    tpsa = Descriptors.TPSA(mol)
    qed = QED.qed(mol)
    heavy_atoms = mol.GetNumHeavyAtoms()

    lipinski_violations = 0
    if mw > 500: lipinski_violations += 1
    if logp > 5: lipinski_violations += 1
    if hbd > 5: lipinski_violations += 1
    if hba > 10: lipinski_violations += 1

    drug_likeness_score = qed
    if heavy_atoms < 6:
        return None  # too small for drug-like
    if lipinski_violations > 1:
        drug_likeness_score *= 0.5

    return {
        "smiles": smiles,
        "name": entry.get("name", "Novel"),
        "rationale": entry.get("rationale", ""),
        "valid": True,
        "molecular_formula": rdMolDescriptors.CalcMolFormula(mol),
        "mw": round(mw, 2),
        "logp": round(logp, 2),
        "hbd": hbd,
        "hba": hba,
        "rotatable_bonds": rot_bonds,
        "tpsa": round(tpsa, 1),
        "heavy_atoms": heavy_atoms,
        "lipinski_violations": lipinski_violations,
        "qed": round(qed, 3),
        "drug_likeness": round(drug_likeness_score, 3),
    }


def lookup_pubchem(smiles: str) -> dict | None:
    """Look up a SMILES in PubChem for known bioactivity data."""
    from discovery.pubchem import search_compound_by_smiles
    result = search_compound_by_smiles(smiles)
    if result and result.get("cid"):
        return {"cid": result["cid"], "synonyms": result.get("synonyms", [])[:5]}
    return None


def cross_reference_graph(graph, molecule: dict) -> float:
    """Score novelty by checking if molecule or known synonyms exist in graph."""
    name = molecule.get("name", "").lower()
    if not name or name == "novel":
        return 1.0  # fully novel
    for eid, ent in graph.entities.items():
        if name in ent.get("name", "").lower():
            return 0.0  # already known in graph
        for alias in ent.get("aliases", []):
            if name in alias.lower():
                return 0.2
    return 0.8


def score_molecule(molecule: dict, graph=None) -> float:
    """Combined score: drug-likeness × novelty × target relevance."""
    dl = molecule.get("drug_likeness", 0)
    novelty = 1.0
    if graph:
        novelty = cross_reference_graph(graph, molecule)
    target_relevance = 0.8  # baseline — Gemini generated it FOR this target
    score = dl * 0.4 + novelty * 0.35 + target_relevance * 0.25
    return round(score, 3)


def generate_candidates(target: str, graph=None, num_candidates: int = 8) -> list[dict]:
    """Full pipeline: Gemini → RDKit validation → PubChem → scoring."""
    raw = generate_smiles(target, num_candidates)
    if not raw:
        return []

    results = []
    for entry in raw:
        validated = validate_smiles(entry)
        if validated is None:
            continue
        pubchem_data = lookup_pubchem(validated["smiles"])
        if pubchem_data:
            validated["pubchem_cid"] = pubchem_data["cid"]
            validated["synonyms"] = pubchem_data["synonyms"]
        else:
            validated["pubchem_cid"] = None
            validated["synonyms"] = []
        novelty = cross_reference_graph(graph, validated) if graph else 1.0
        validated["novelty"] = novelty
        validated["score"] = score_molecule(validated, graph)
        results.append(validated)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def format_candidates(candidates: list[dict]) -> str:
    lines = ["", "=" * 70, "  GENERATED MOLECULES", "=" * 70, ""]
    for i, m in enumerate(candidates, 1):
        lines.append(f"  Candidate {i}: {m['name']} (score: {m['score']})")
        lines.append(f"  {'─' * 50}")
        lines.append(f"  SMILES: {m['smiles']}")
        lines.append(f"  Formula: {m['molecular_formula']}  |  MW: {m['mw']}  |  LogP: {m['logp']}")
        lines.append(f"  HBD: {m['hbd']}  |  HBA: {m['hba']}  |  RotB: {m['rotatable_bonds']}  |  TPSA: {m['tpsa']}")
        lines.append(f"  QED: {m['qed']}  |  Lipinski violations: {m['lipinski_violations']}  |  Novelty: {m['novelty']}")
        if m.get("pubchem_cid"):
            lines.append(f"  PubChem CID: {m['pubchem_cid']} — known compound")
        if m.get("synonyms"):
            lines.append(f"  Known as: {', '.join(m['synonyms'][:4])}")
        if m.get("rationale"):
            lines.append(f"  Rationale: {m['rationale']}")
        lines.append("")
    return "\n".join(lines)
