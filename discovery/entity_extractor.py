"""
entity_extractor.py — Algorithmic entity extraction from papers.

No LLM calls. Uses NLP patterns to extract entities and relationships
from paper titles and abstracts. Fast, reliable, never hangs.

Approach:
1. Extract noun phrases as entities
2. Use co-occurrence to find relationships
3. Use keyword patterns to classify relationship types
4. Deduplicate and score
"""

import re
from collections import defaultdict, Counter
from typing import List, Dict, Tuple


# Entity type patterns
ENTITY_PATTERNS = {
    "phenomenon": [
        r'\b(?:tension|anomaly|discrepancy|puzzle|problem|crisis)\b',
        r'\b(?:expansion|acceleration|dimming|flaring|eruption)\b',
        r'\b(?:radiation|emission|absorption|scattering|dispersion)\b',
        r'\b(?:oscillation|vibration|resonance|fluctuation)\b',
    ],
    "theory": [
        r'\b(?:theory|model|hypothesis|framework|paradigm|scenario)\b',
        r'\b(?:relativity|quantum|thermodynamics|electrodynamics)\b',
        r'\b(?:inflation|nucleosynthesis|recombination|decoupling)\b',
    ],
    "measurement": [
        r'\b(?:measurement|observation|constraint|limit|bound|detection)\b',
        r'\b(?:survey|catalog|dataset|experiment|telescope)\b',
        r'\b(?:photometry|spectroscopy|polarimetry|interferometry)\b',
    ],
    "entity": [
        r'\b(?:galaxy|galaxies|star|stars|planet|exoplanet|nebula)\b',
        r'\b(?:black hole|neutron star|pulsar|quasar|blazar)\b',
        r'\b(?:supernova|supernovae|nova|gamma-ray burst)\b',
        r'\b(?:dark matter|dark energy|dark sector)\b',
        r'\b(?:photon|neutrino|electron|proton|neutron|boson|fermion)\b',
        r'\b(?:Higgs|WIMP|axion|graviton|sterile neutrino)\b',
    ],
    "parameter": [
        r'\bH[₀0]\b',
        r'\bΩ_[a-z]+\b',
        r'\bσ[₀8]\b',
        r'\b[HN]_{?eff}?\b',
        r'\bf_{?EDE}\b',
        r'\bα\b',
        r'\bβ\b',
        r'\bδ\b',
    ],
    "method": [
        r'\b(?:MCMC|Bayesian|Monte Carlo|bootstrap|jackknife)\b',
        r'\b(?:likelihood|posterior|prior|chi-square|χ²)\b',
        r'\b(?:CMB|BAO|SNe|Type Ia|standard candle|ruler)\b',
        r'\b(?:lensing|timing|pulsar timing|laser ranging)\b',
    ],
    "organization": [
        r'\b(?:Planck|DESI|ACT|SPT|SDSS|JWST|Hubble|Keck)\b',
        r'\b(?:NANOGrav|EPTA|PPTA|LIGO|Virgo|KAGRA)\b',
        r'\b(?:SH0ES|Pantheon\+|Carnegie-Chicago)\b',
    ],
}

# Relationship patterns
RELATION_PATTERNS = {
    "explains": [
        r'(\w[\w\s]+?)\s+(?:explains|accounts for|resolves|addresses)\s+(\w[\w\s]+)',
        r'(\w[\w\s]+?)\s+(?:solution|resolution|explanation)\s+(?:to|for|of)\s+(\w[\w\s]+)',
    ],
    "constrains": [
        r'(\w[\w\s]+?)\s+(?:constrains|limits|rules out|excludes|bounds)\s+(\w[\w\s]+)',
        r'(?:constraints?|limits?|bounds?)\s+(?:on|from)\s+(\w[\w\s]+)',
    ],
    "associated_with": [
        r'(\w[\w\s]+?)\s+(?:and|with|plus|alongside)\s+(\w[\w\s]+)',
        r'(\w[\w\s]+?)\s+(?:correlates?|associated|linked|connected)\s+(?:with|to)\s+(\w[\w\s]+)',
    ],
    "measured_by": [
        r'(\w[\w\s]+?)\s+(?:measured|observed|detected|constrained)\s+(?:by|using|with|from)\s+(\w[\w\s]+)',
        r'(\w[\w\s]+?)\s+(?:measurement|observation|detection|constraint)\s+(?:from|using|with)\s+(\w[\w\s]+)',
    ],
    "proposes": [
        r'(?:we|this|the\s+paper)\s+(?:propose|suggest|introduce|present|develop)\s+(\w[\w\s]+)',
        r'(\w[\w\s]+?)\s+(?:proposes?|suggests?|introduces?|presents?)\s+(\w[\w\s]+)',
    ],
    "affects": [
        r'(\w[\w\s]+?)\s+(?:affects?|impacts?|influences?|modifies?|changes?|alters?)\s+(\w[\w\s]+)',
        r'(\w[\w\s]+?)\s+(?:effect|impact|influence|modification|change|alteration)\s+(?:on|of)\s+(\w[\w\s]+)',
    ],
    "causes": [
        r'(\w[\w\s]+?)\s+(?:causes?|produces?|leads?\s+to|results?\s+in|drives?|generates?)\s+(\w[\w\s]+)',
        r'(\w[\w\s]+?)\s+(?:due to|because of|caused by|driven by|resulting from)\s+(\w[\w\s]+)',
    ],
}


def extract_entities_from_papers(papers: list, domain: str = "") -> dict:
    """
    Extract entities and relationships from papers algorithmically.
    No LLM calls — fast and reliable.

    Returns:
        {"entities": [...], "relationships": [...]}
    """
    all_text = []
    for p in papers:
        title = p.get("title", "")
        abstract = p.get("abstract", "")
        all_text.append(f"{title}. {abstract}")

    combined = " ".join(all_text)

    # 1. Extract entities
    entities = _extract_entities(combined, papers)

    # 2. Extract relationships
    relationships = _extract_relationships(combined, entities, papers)

    return {
        "entities": entities,
        "relationships": relationships,
    }


def _extract_entities(text: str, papers: list) -> list:
    """Extract entities using pattern matching and noun phrases."""
    entities = []
    seen = set()

    # Pattern-based extraction
    for etype, patterns in ENTITY_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                name = match.group(0).strip()
                name_clean = name.lower().strip()
                if len(name_clean) > 2 and name_clean not in seen:
                    seen.add(name_clean)
                    entities.append({
                        "name": name,
                        "type": etype,
                        "aliases": [],
                    })

    # Noun phrase extraction — capitalized multi-word terms
    for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text):
        name = match.group(0).strip()
        name_clean = name.lower()
        if len(name) > 5 and name_clean not in seen:
            # Skip common phrases
            skip_words = {"The", "This", "That", "These", "Those", "However", "Therefore",
                          "Furthermore", "Moreover", "Additionally", "Recent", "Previous"}
            if not any(name.startswith(w) for w in skip_words):
                seen.add(name_clean)
                entities.append({
                    "name": name,
                    "type": "concept",
                    "aliases": [],
                })

    # Extract acronyms and their expansions
    for match in re.finditer(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\(([A-Z]{2,})\)', text):
        full_name = match.group(1).strip()
        acronym = match.group(2).strip()
        full_clean = full_name.lower()
        if full_clean not in seen:
            seen.add(full_clean)
            entities.append({
                "name": full_name,
                "type": "concept",
                "aliases": [acronym],
            })
        if acronym.lower() not in seen:
            seen.add(acronym.lower())
            entities.append({
                "name": acronym,
                "type": "concept",
                "aliases": [full_name],
            })

    # Extract numbers with units (parameters)
    for match in re.finditer(r'(\d+\.?\d*)\s*(km/s/Mpc|Mpc|Gyr|eV|GeV|TeV|Hz|K|%)', text):
        value = match.group(1)
        unit = match.group(2)
        name = f"{value} {unit}"
        if name.lower() not in seen:
            seen.add(name.lower())
            entities.append({
                "name": name,
                "type": "parameter",
                "aliases": [],
            })

    return entities[:50]  # Cap at 50 entities


def _extract_relationships(text: str, entities: list, papers: list) -> list:
    """Extract relationships using co-occurrence and keyword patterns."""
    relationships = []
    seen = set()

    # Get entity names for matching
    entity_names = [e["name"].lower() for e in entities]
    entity_map = {e["name"].lower(): e for e in entities}

    # 1. Co-occurrence relationships
    for p in papers:
        ptext = f"{p.get('title', '')} {p.get('abstract', '')}".lower()
        # Find entities that co-occur in the same paper
        present = [e for e in entities if e["name"].lower() in ptext]
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                e1, e2 = present[i], present[j]
                key = (e1["name"].lower(), e2["name"].lower())
                if key not in seen:
                    seen.add(key)
                    # Determine relationship type from context
                    rel_type = _infer_relationship_type(ptext, e1["name"], e2["name"])
                    relationships.append({
                        "source": e1["name"],
                        "source_type": e1["type"],
                        "relation": rel_type,
                        "target": e2["name"],
                        "target_type": e2["type"],
                        "confidence": 0.6,
                    })

    # 2. Pattern-based relationships
    for rel_type, patterns in RELATION_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                groups = match.groups()
                if len(groups) >= 2:
                    src = groups[0].strip().lower()
                    tgt = groups[-1].strip().lower()
                    # Match to known entities
                    src_entity = _find_closest_entity(src, entity_names, entity_map)
                    tgt_entity = _find_closest_entity(tgt, entity_names, entity_map)
                    if src_entity and tgt_entity and src_entity != tgt_entity:
                        key = (src_entity["name"].lower(), tgt_entity["name"].lower())
                        if key not in seen:
                            seen.add(key)
                            relationships.append({
                                "source": src_entity["name"],
                                "source_type": src_entity["type"],
                                "relation": rel_type,
                                "target": tgt_entity["name"],
                                "target_type": tgt_entity["type"],
                                "confidence": 0.7,
                            })

    return relationships[:30]  # Cap at 30 relationships


def _infer_relationship_type(text: str, e1: str, e2: str) -> str:
    """Infer relationship type from context."""
    text_lower = text.lower()
    e1_lower = e1.lower()
    e2_lower = e2.lower()

    # Check for causal language
    causal_words = ["causes", "leads to", "results in", "drives", "produces"]
    for word in causal_words:
        if word in text_lower and e1_lower in text_lower and e2_lower in text_lower:
            return "causes"

    # Check for constraint language
    constraint_words = ["constrains", "limits", "rules out", "excludes"]
    for word in constraint_words:
        if word in text_lower:
            return "constrains"

    # Check for explanation language
    explain_words = ["explains", "resolves", "accounts for", "solution"]
    for word in explain_words:
        if word in text_lower:
            return "explains"

    # Check for measurement language
    measure_words = ["measured", "observed", "detected", "constraint"]
    for word in measure_words:
        if word in text_lower:
            return "measured_by"

    # Default
    return "associated_with"


def _find_closest_entity(text: str, entity_names: list, entity_map: dict) -> dict:
    """Find the entity that best matches the text."""
    text = text.strip().lower()
    if not text:
        return None

    # Exact match
    if text in entity_map:
        return entity_map[text]

    # Partial match
    for name in entity_names:
        if text in name or name in text:
            return entity_map[name]

    return None
