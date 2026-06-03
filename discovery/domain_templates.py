"""
domain_templates.py — Domain-Specific Research Templates for RUMI

Different domains have different research patterns, methodologies,
and key metrics. This module provides domain-specific templates that
customize the pipeline's behavior for each scientific field.

Templates define:
- Research question patterns
- Methodology preferences
- Key metrics and validation criteria
- Scoring weight adjustments
- Data source priorities
"""

from typing import Dict, List, Optional


DOMAIN_TEMPLATES = {
    "space_astronomy": {
        "research_patterns": [
            "Is {observation} consistent with {theory}?",
            "Can {mechanism} explain {anomaly} in {dataset}?",
            "What hidden variables drive {correlation} between {var1} and {var2}?",
            "Does {biosignature} indicate {process} on {body}?",
        ],
        "methodology_preferences": [
            "Spectroscopic analysis", "Transit photometry", "Radial velocity",
            "Monte Carlo simulation", "Bayesian inference", "MCMC sampling",
            "Radiative transfer modeling", "Atmospheric retrieval",
        ],
        "key_metrics": [
            "Signal-to-noise ratio (SNR)", "Transit depth (ppm)",
            "Atmospheric mixing ratio", "Equilibrium temperature",
            "Stellar flux", "Orbital period", "Eccentricity",
        ],
        "data_sources": ["NASA Exoplanet Archive", "MAST", "arXiv astro-ph", "SIMBAD"],
        "scoring_weights": {
            "novelty": 0.20,      # Astronomy values novel discoveries highly
            "evidence": 0.25,     # Strong observational evidence needed
            "predictions": 0.25,  # Testable predictions critical
            "mathematical": 0.15, # Equations important for modeling
            "mechanism": 0.10,    # Mechanisms can be speculative
            "parsimony": 0.05,    # Simpler explanations preferred
        },
        "validation_criteria": [
            "Reproducible with different instruments",
            "Consistent across multiple wavelengths",
            "Matches known physical laws",
            "Predicts new observable signatures",
        ],
    },

    "drug_discovery": {
        "research_patterns": [
            "Does {compound} inhibit {target} via {mechanism}?",
            "Can {pathway} be modulated to treat {disease}?",
            "What biomarkers predict response to {therapy}?",
            "How does {mutation} affect {drug} binding affinity?",
        ],
        "methodology_preferences": [
            "High-throughput screening", "Molecular docking", "MD simulation",
            "Clinical trial design", "PK/PD modeling", "ADMET prediction",
            "Structure-activity relationship", "Dose-response curves",
        ],
        "key_metrics": [
            "IC50", "EC50", "Ki", "Selectivity index",
            "Bioavailability", "Half-life", "Therapeutic index",
            "Binding affinity (kcal/mol)", "Lipinski compliance",
        ],
        "data_sources": ["PubChem", "ChEMBL", "DrugBank", "ClinicalTrials.gov"],
        "scoring_weights": {
            "novelty": 0.15,
            "evidence": 0.30,     # Strong experimental evidence critical
            "predictions": 0.20,
            "mathematical": 0.10,
            "mechanism": 0.20,    # Mechanism of action important
            "parsimony": 0.05,
        },
        "validation_criteria": [
            "Dose-response relationship established",
            "Selectivity over off-targets demonstrated",
            "ADMET properties favorable",
            "In vivo efficacy in animal model",
        ],
    },

    "neuroscience": {
        "research_patterns": [
            "Does {neurotransmitter} mediate {behavior} via {receptor}?",
            "How does {brain_region} connectivity relate to {function}?",
            "Can {stimulation} modulate {circuit} to improve {outcome}?",
        ],
        "methodology_preferences": [
            "fMRI analysis", "Electrophysiology", "Optogenetics",
            "Behavioral assays", "Connectomics", "Computational modeling",
        ],
        "key_metrics": [
            "BOLD signal change", "Firing rate (Hz)", "LFP power",
            "Connectivity strength", "Behavioral score", "Reaction time",
        ],
        "data_sources": ["Allen Brain Atlas", "Human Connectome Project", "NeuroMorpho"],
        "scoring_weights": {
            "novelty": 0.15,
            "evidence": 0.25,
            "predictions": 0.20,
            "mathematical": 0.10,
            "mechanism": 0.25,    # Neural mechanisms critical
            "parsimony": 0.05,
        },
        "validation_criteria": [
            "Replicated across subjects",
            "Consistent with known anatomy",
            "Predicts behavioral outcomes",
            "Dissociable from alternative circuits",
        ],
    },

    "physics": {
        "research_patterns": [
            "Can {framework} unify {phenomenon1} and {phenomenon2}?",
            "What symmetry breaking explains {observation}?",
            "Does {field_theory} predict {effect} at energy {E}?",
        ],
        "methodology_preferences": [
            "Analytical derivation", "Numerical simulation",
            "Lattice QCD", "Monte Carlo", "Renormalization group",
            "Perturbation theory", "Effective field theory",
        ],
        "key_metrics": [
            "Cross-section", "Decay rate", "Coupling constant",
            "Anomalous magnetic moment", "Scattering amplitude",
        ],
        "data_sources": ["arXiv hep-ph", "PDG", "INSPIRE-HEP"],
        "scoring_weights": {
            "novelty": 0.25,      # Physics values theoretical novelty
            "evidence": 0.20,
            "predictions": 0.25,
            "mathematical": 0.20, # Mathematical rigor critical
            "mechanism": 0.05,
            "parsimony": 0.05,
        },
        "validation_criteria": [
            "Mathematically consistent",
            "Reduces to known limits",
            "Makes falsifiable predictions",
            "Respects known symmetries",
        ],
    },

    "ecology": {
        "research_patterns": [
            "How does {stressor} affect {species} population in {ecosystem}?",
            "Can {intervention} reverse {trend} in {habitat}?",
            "What trophic interactions drive {pattern}?",
        ],
        "methodology_preferences": [
            "Population surveys", "Species distribution modeling",
            "Community ecology analysis", "Remote sensing",
            "Stable isotope analysis", "eDNA metabarcoding",
        ],
        "key_metrics": [
            "Species richness", "Shannon diversity", "Population density",
            "Carrying capacity", "Growth rate", "Survival rate",
        ],
        "data_sources": ["GBIF", "IUCN Red List", "eBird", "MODIS"],
        "scoring_weights": {
            "novelty": 0.15,
            "evidence": 0.30,     # Field data critical
            "predictions": 0.15,
            "mathematical": 0.10,
            "mechanism": 0.20,
            "parsimony": 0.10,    # Simple models preferred
        },
        "validation_criteria": [
            "Validated across multiple sites",
            "Consistent with long-term trends",
            "Accounts for confounding variables",
            "Predicts future states accurately",
        ],
    },
}


def get_domain_template(domain: str) -> dict:
    """Get the research template for a domain."""
    return DOMAIN_TEMPLATES.get(domain, DOMAIN_TEMPLATES.get("physics", {}))


def get_scoring_weights(domain: str) -> dict:
    """Get domain-specific scoring weights."""
    template = get_domain_template(domain)
    return template.get("scoring_weights", {
        "novelty": 0.15, "evidence": 0.25, "predictions": 0.20,
        "mathematical": 0.15, "mechanism": 0.15, "parsimony": 0.10,
    })


def get_research_question_prompt(domain: str, topic: str) -> str:
    """Generate domain-specific research question framing."""
    template = get_domain_template(domain)
    patterns = template.get("research_patterns", [])
    metrics = template.get("key_metrics", [])
    methods = template.get("methodology_preferences", [])

    lines = []
    lines.append(f"DOMAIN CONTEXT ({domain}):")
    if patterns:
        lines.append("Research question patterns in this domain:")
        for p in patterns[:3]:
            lines.append(f"  - {p}")
    if metrics:
        lines.append(f"Key metrics: {', '.join(metrics[:5])}")
    if methods:
        lines.append(f"Preferred methods: {', '.join(methods[:4])}")
    return "\n".join(lines)


def get_validation_prompt(domain: str) -> str:
    """Get domain-specific validation criteria for the prompt."""
    template = get_domain_template(domain)
    criteria = template.get("validation_criteria", [])
    if not criteria:
        return ""
    lines = ["Validation criteria for this domain:"]
    for c in criteria:
        lines.append(f"  - {c}")
    return "\n".join(lines)


def adjust_discovery_score(score: dict, domain: str) -> dict:
    """Adjust discovery score using domain-specific weights."""
    weights = get_scoring_weights(domain)
    component_scores = {
        "novelty": score.get("novelty_score", 50),
        "evidence": score.get("evidence_score", 50),
        "predictions": score.get("prediction_score", 50),
        "mathematical": score.get("mathematical_score", 50),
        "mechanism": score.get("mechanism_score", 50),
        "parsimony": score.get("parsimony_score", 50),
    }
    weighted = sum(component_scores[k] * weights.get(k, 0.167) for k in component_scores)
    score["domain_weighted_score"] = round(weighted, 1)
    score["domain_weights"] = weights
    return score
