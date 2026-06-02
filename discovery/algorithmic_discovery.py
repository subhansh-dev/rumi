"""
algorithmic_discovery.py — Generate hypotheses, mechanisms, and predictions
WITHOUT LLM calls. Uses graph analysis, pattern matching, and domain knowledge.

This is the fallback that ensures RUMI ALWAYS produces results, even when
LLM APIs are down or rate-limited.

Approach:
1. Analyze knowledge graph structure for patterns
2. Match gaps/anomalies against known discovery templates
3. Generate mechanisms from causal chain analysis
4. Extract predictions from mathematical relationships
5. Compare theories using structural analysis
"""

import json
import re
import math
from collections import defaultdict, Counter
from typing import List, Dict, Optional


# Discovery templates — patterns that historically led to discoveries
DISCOVERY_TEMPLATES = {
    "hidden_variable": {
        "pattern": "Observation A and Observation B are both true, but no known mechanism connects them.",
        "template": "Propose hidden entity/process C that connects A and B.",
        "examples": ["dark matter", "neutrino", "H. pylori", "oxygen"],
    },
    "anomalous_measurement": {
        "pattern": "Measurement M differs significantly from theoretical prediction P.",
        "template": "Either the measurement is wrong, the theory is wrong, or a hidden factor F affects M.",
        "examples": ["Hubble tension", "muon g-2", "Pioneer anomaly"],
    },
    "missing_mechanism": {
        "pattern": "Entity A correlates with Entity B, but no causal pathway exists.",
        "template": "Propose mechanism M that mediates the A→B relationship.",
        "examples": ["plate tectonics", "germ theory", "quantum entanglement"],
    },
    "scale_discrepancy": {
        "pattern": "Effect E is observed at scale S1 but predicted only at scale S2.",
        "template": "Propose bridging mechanism that operates across scales.",
        "examples": ["renormalization", "emergence", "fractal structures"],
    },
}


def generate_hypotheses_algorithmic(graph, gaps, anomalies, topic, domain):
    """
    Generate hypotheses without LLM calls.
    Uses graph structure, gap analysis, and discovery templates.
    """
    hypotheses = []
    
    entities = graph.entities if hasattr(graph, 'entities') else {}
    relationships = graph.relationships if hasattr(graph, 'relationships') else {}
    
    # 1. From gaps: propose hidden variables for orphan observations
    for gap in gaps[:5]:
        if gap.get("type") == "orphan_observation":
            entity = gap.get("entity", gap.get("reason", ""))
            hypotheses.append({
                "name": f"Hidden mechanism for {entity}",
                "type": "proposed",
                "description": f"Observation '{entity}' exists in the literature but has no causal explanation. "
                              f"Propose a hidden mechanism that connects this observation to known entities in the graph.",
                "key_parameters": [{"name": "entity", "expected_value": entity, "units": ""}],
                "predictions": [f"If a hidden mechanism connects '{entity}' to other entities, "
                              f"then there should be observable correlations with graph neighbors."],
                "literature_basis": [f"Gap detected: {gap.get('reason', '')[:100]}"],
                "is_novel_vs_known": "novel",
                "confidence": 0.4,
                "source": "algorithmic_gap_analysis",
            })
    
    # 2. From anomalies: propose explanations for outlier entities
    for anomaly in anomalies[:5]:
        if anomaly.get("type") == "outlier_entity":
            entity = anomaly.get("entity", "")
            z_score = anomaly.get("z_score", 0)
            hypotheses.append({
                "name": f"Explanation for {entity} hub status",
                "type": "proposed",
                "description": f"Entity '{entity}' is a hub (z={z_score:.1f}) with unusually high connectivity. "
                              f"This suggests it plays a central role that may not be fully understood. "
                              f"Propose that {entity} has a hidden function or mechanism that explains its centrality.",
                "key_parameters": [{"name": "z_score", "expected_value": str(z_score), "units": ""}],
                "predictions": [f"If {entity} has a hidden function, then removing it from the graph "
                              f"should fragment the knowledge structure more than expected."],
                "literature_basis": [f"Anomaly detected: {anomaly.get('reason', '')[:100]}"],
                "is_novel_vs_known": "novel",
                "confidence": 0.5,
                "source": "algorithmic_anomaly_analysis",
            })
    
    # 3. From graph structure: propose missing connections
    missing_links = _find_missing_links(graph)
    for link in missing_links[:3]:
        hypotheses.append({
            "name": f"Connection: {link['source']} ↔ {link['target']}",
            "type": "proposed",
            "description": f"Entities '{link['source']}' and '{link['target']}' share {link['common_count']} "
                          f"common neighbors but have no direct relationship. This suggests a hidden connection.",
            "key_parameters": [{"name": "common_neighbors", "expected_value": str(link['common_count']), "units": ""}],
            "predictions": [f"If '{link['source']}' and '{link['target']}' are connected, "
                          f"then experimental studies should find correlations between them."],
            "literature_basis": [f"Graph analysis: {link['common_count']} common neighbors"],
            "is_novel_vs_known": "novel",
            "confidence": 0.35,
            "source": "algorithmic_graph_analysis",
        })
    
    # 4. From domain-specific templates
    if domain in ("space_astronomy", "physics", "cosmology"):
        hypotheses.append({
            "name": "Modified gravitational constant G(z)",
            "type": "alternative",
            "description": "The gravitational constant G may vary with redshift: G(z) = G₀(1 + αz). "
                          "This would affect the expansion history and could explain discrepancies between "
                          "early-universe and late-universe measurements.",
            "key_parameters": [{"name": "α", "expected_value": "10⁻⁵ to 10⁻⁴", "units": "dimensionless"}],
            "predictions": ["If G varies, then BBN deuterium abundance should shift by ~0.5% for α = 10⁻⁴.",
                          "Lunar laser ranging should detect |Ġ/G| ~ 10⁻¹²/yr."],
            "literature_basis": ["Dirac (1937)", "Brans-Dicke (1961)", "Uzan (2003)"],
            "is_novel_vs_known": "extension_of_known",
            "confidence": 0.6,
            "source": "domain_template",
        })
        hypotheses.append({
            "name": "Early dark energy phase",
            "type": "alternative",
            "description": "A scalar field φ acts as dark energy at early times (z~3000) but decays before today. "
                          "This modifies the sound horizon at recombination, reducing the CMB-inferred H₀.",
            "key_parameters": [{"name": "f_EDE", "expected_value": "3-7%", "units": "fraction of total energy"}],
            "predictions": ["If f_EDE = 5%, then CMB lensing should show ~2% enhancement at ℓ > 2000.",
                          "Matter power spectrum suppression ~3% at k ~ 1 h/Mpc."],
            "literature_basis": ["Poulin et al. (2019)", "Smith et al. (2020)", "Ivanov et al. (2020)"],
            "is_novel_vs_known": "well_known",
            "confidence": 0.7,
            "source": "domain_template",
        })
    
    return hypotheses


def generate_mechanisms_algorithmic(graph, hypotheses, topic, domain):
    """
    Generate causal mechanisms without LLM calls.
    Uses graph paths and domain templates.
    """
    mechanisms = []
    
    for hyp in hypotheses[:5]:
        name = hyp.get("name", "")
        desc = hyp.get("description", "")
        
        # Extract causal steps from description
        steps = _extract_causal_steps(desc)
        
        mechanisms.append({
            "name": f"Mechanism: {name}",
            "type": "causal_pathway",
            "description": desc,
            "steps": steps,
            "mathematical_model": _extract_equations_from_text(desc),
            "key_parameters": hyp.get("key_parameters", []),
            "literature_basis": hyp.get("literature_basis", []),
            "is_novel_vs_known": hyp.get("is_novel_vs_known", "unknown"),
            "confidence": hyp.get("confidence", 0.5),
            "predictions": hyp.get("predictions", []),
            "source": "algorithmic",
        })
    
    return mechanisms


def generate_predictions_algorithmic(mechanisms, hypotheses, topic, domain):
    """
    Generate testable predictions without LLM calls.
    Extracts predictions from hypotheses and mechanisms.
    """
    predictions = []
    
    for hyp in hypotheses[:5]:
        for pred in hyp.get("predictions", []):
            if isinstance(pred, str) and len(pred) > 20:
                # Check if prediction has quantitative content
                has_numbers = any(c.isdigit() for c in pred)
                predictions.append({
                    "statement": pred,
                    "type": "novel" if has_numbers else "correlational",
                    "mechanism_source": hyp.get("name", ""),
                    "testability": "moderate" if has_numbers else "hard",
                    "falsification": f"Observe the opposite of: {pred[:100]}",
                    "confidence": hyp.get("confidence", 0.5),
                    "source": "algorithmic",
                })
    
    # Add domain-specific predictions
    if domain in ("space_astronomy", "physics", "cosmology"):
        predictions.append({
            "statement": "If the Hubble tension is real, then independent distance measurements "
                        "(gravitational lensing time delays, TRGB) should give H₀ values between "
                        "the CMB (67.4) and SNe (73.0) measurements.",
            "type": "novel",
            "mechanism_source": "Hubble tension",
            "testability": "easy",
            "falsification": "If all independent methods give H₀ = 67.4 ± 0.5 or H₀ = 73.0 ± 1.0",
            "confidence": 0.8,
            "source": "domain_template",
        })
    
    return predictions


def compare_theories_algorithmic(theories, graph, papers):
    """
    Compare theories without LLM calls.
    Uses structural analysis and evidence counting.
    """
    scored = []
    
    for theory in theories:
        score = 0.0
        
        # Factor 1: Explanatory power
        explains = theory.get("explains", [])
        predictions = theory.get("predictions", [])
        score += min(30, len(explains) * 5 + len(predictions) * 3)
        
        # Factor 2: Literature support
        lit = theory.get("literature_basis", [])
        score += min(20, len(lit) * 5)
        
        # Factor 3: Quantitative predictions
        quant_preds = sum(1 for p in predictions if isinstance(p, str) and any(c.isdigit() for c in p))
        score += min(25, quant_preds * 8)
        
        # Factor 4: Type bonus
        type_bonus = {"null": 10, "conventional": 8, "alternative": 15, "proposed": 12}
        score += type_bonus.get(theory.get("type", ""), 5)
        
        # Factor 5: Simplicity (fewer parameters = better)
        params = theory.get("key_parameters", [])
        score += max(0, 15 - len(params) * 3)
        
        theory["scores"] = {
            "explanatory_power": min(1.0, len(explains) * 0.2),
            "predictive_power": min(1.0, len(predictions) * 0.15),
            "simplicity": max(0.1, 1.0 - len(params) * 0.15),
            "novelty": 0.7 if theory.get("is_novel_vs_known") == "novel" else 0.4,
            "falsifiability": min(1.0, quant_preds * 0.3),
            "evidence_support": min(1.0, len(lit) * 0.2),
            "coherence": 0.6,
            "overall": round(score / 100, 3),
        }
        theory["_tournament_score"] = score
        scored.append(theory)
    
    scored.sort(key=lambda t: t.get("_tournament_score", 0), reverse=True)
    return scored


def _find_missing_links(graph):
    """Find entity pairs with common neighbors but no direct link."""
    entities = graph.entities if hasattr(graph, 'entities') else {}
    relationships = graph.relationships if hasattr(graph, 'relationships') else {}
    
    adj = defaultdict(set)
    for rel in relationships:
        adj[rel["source"]].add(rel["target"])
        adj[rel["target"]].add(rel["source"])
    
    missing = []
    entity_ids = list(entities.keys())
    
    for i in range(min(len(entity_ids), 20)):
        for j in range(i + 1, min(len(entity_ids), 20)):
            a, b = entity_ids[i], entity_ids[j]
            if b in adj.get(a, set()):
                continue
            
            common = adj.get(a, set()) & adj.get(b, set())
            if len(common) >= 2:
                a_name = entities.get(a, {}).get("name", a)
                b_name = entities.get(b, {}).get("name", b)
                missing.append({
                    "source": a_name,
                    "target": b_name,
                    "common_count": len(common),
                })
    
    missing.sort(key=lambda x: x["common_count"], reverse=True)
    return missing[:5]


def _extract_causal_steps(description):
    """Extract causal steps from a description."""
    steps = []
    
    # Split on common causal connectors
    parts = re.split(r'\.|\band\b|\bthen\b|\bleading to\b|\bresulting in\b', description)
    for part in parts:
        part = part.strip()
        if len(part) > 20:
            steps.append(part)
    
    return steps[:5] if steps else [description[:200]]


def _extract_equations_from_text(text):
    """Extract equations from text."""
    equations = []
    
    # Match common equation patterns
    patterns = [
        r'([A-Za-z_]\w*)\s*=\s*([^,.;]{5,60})',
        r'([A-Za-z_]\w*)\s*≈\s*([^,.;]{5,40})',
        r'([A-Za-z_]\w*)\s*~\s*([^,.;]{5,40})',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            var, expr = match.groups()
            if len(var) > 1 and any(c.isalpha() for c in expr):
                equations.append(f"{var} = {expr.strip()}")
    
    return "; ".join(equations[:3]) if equations else "No equations extracted"
