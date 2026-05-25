# Drug Data Enrichment — Design Document

**Date:** 2026-05-25
**Phase:** 2 of Discovery Engine
**Depends on:** Phase 1 (PubMed + Knowledge Graph)

---

## Overview

Enhance RUMI's Discovery Engine with real drug database lookups. When RUMI extracts a drug entity from PubMed papers, she queries PubChem (compound properties, targets) and OpenFDA (side effects, labeling) to enrich the knowledge graph. This turns simple "drug X treats disease Y" observations into mechanistically-grounded hypotheses backed by known targets, side effect profiles, and molecular properties.

---

## Data Sources

### PubChem (PUG REST API)
- Free, no registration, no API key
- Base URL: `https://pubchem.ncbi.nlm.nih.gov/rest/pug/`
- Endpoints used:
  - `compound/name/{name}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,InChIKey/JSON`
  - `compound/name/{name}/synonyms/JSON`
  - `compound/name/{name}/targets/JSON` — gene/protein targets from bioassays

### OpenFDA
- Free, no registration, no API key (for basic queries)
- Base URL: `https://api.fda.gov/`
- Endpoints used:
  - `drug/event.json?search=patient.drug.medicinalproduct:"{name}"` — adverse events
  - `drug/label.json?search=openfda.brand_name:"{name}"` — drug labeling, mechanism

---

## New Modules

### `discovery/pubchem.py`

```
search_compound(name: str) -> dict | None
  - Search by drug name, return CID + properties + synonyms

get_targets(cid: str) -> list[dict]
  - Return list of {target_name, target_type, organism} from PubChem bioassays

get_properties(cid: str) -> dict
  - Return {molecular_formula, molecular_weight, smiles, inchikey}
```

### `discovery/openfda.py`

```
get_side_effects(drug_name: str, limit: int = 20) -> list[dict]
  - Return list of {reaction, count, serious_count}
  - Aggregated across all reported adverse events

get_labeling(drug_name: str) -> dict | None
  - Return {mechanism_of_action, indications, warnings}
  - Extracted from structured drug labeling data
```

---

## Knowledge Graph Enrichment

### New Entity Types
- `side_effect` — adverse drug reactions (e.g., "Lactic acidosis", "Nausea")

### New Relation Types
- `has_target` — drug → gene/protein (from PubChem targets)
- `has_side_effect` — drug → side_effect (from OpenFDA)
- `has_property` — drug → property (molecular weight, formula)

### Enrichment Flow

```
Drug entity extracted from paper
        ↓
pubchem.search_compound(name)
        ↓
  Found? → Yes → get_targets(cid) → add targets as gene/protein entities
              → get_properties(cid) → add as drug properties
              → No → skip (not in PubChem)
        ↓
openfda.get_side_effects(name)
        ↓
  Found? → Yes → add side_effect entities + has_side_effect relations
              → No → skip
        ↓
openfda.get_labeling(name)
        ↓
  Found? → Yes → extract mechanism_of_action → add as mechanism entity
              → No → skip
        ↓
Hypothesis generation considers enriched graph
```

---

## New Commands

### `/enrich` — Post-hoc enrichment of existing knowledge graph
Scans all existing drug entities in the graph and enriches them with PubChem/OpenFDA data. Progress indicator shows (x/y drugs enriched).

### Modified: `/discover` — Now auto-enriches during pipeline
After entity extraction, before hypothesis generation, RUMI enriches each drug entity.

---

## Repurposing Hypothesis Enhancement

With side effect data, hypothesis generation can now detect:
- Drug X has side effect Y
- Side effect Y involves mechanism M (same mechanism as Disease Z)
- → Drug X might treat Disease Z (repurposing)

Example:
```
Metformin → has_side_effect → Lactic acidosis
Lactic acidosis → involves → Mitochondrial dysfunction
Alzheimer's disease → involves → Mitochondrial dysfunction
→ Metformin might affect Alzheimer's via mitochondrial pathways
```

---

## File Structure Changes

```
discovery/
  pubchem.py        # NEW
  openfda.py        # NEW
  __init__.py       # MODIFIED (exports)
  pubmed.py         # unchanged
  graph.py          # MODIFIED (add side_effect entity type)
  output.py         # MODIFIED (show enriched data in stats)
main.py             # MODIFIED (enrichment step in pipeline, /enrich command)
ui.py               # MODIFIED (add /enrich to SLASH_COMMANDS)
```

---

## Implementation Order

1. `discovery/pubchem.py` — PubChem search, targets, properties
2. `discovery/openfda.py` — OpenFDA side effects, labeling
3. Modify `discovery/graph.py` — add side_effect entity type constants
4. Modify `discovery/output.py` — show enriched data
5. Modify `main.py` — add enrichment step to pipeline + `/enrich` handler
6. Modify `ui.py` — add `/enrich` command
