"""
algorithmic_discovery.py — Generate hypotheses, mechanisms, and predictions
WITHOUT LLM calls. Uses graph analysis, pattern matching, and domain knowledge.

This is the fallback that ensures RUMI ALWAYS produces results, even when
LLM APIs are down or rate-limited.

v2.1: Domain-grounded generation — hypotheses are built from actual entities
in the knowledge graph, not from hardcoded cosmology templates.
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


def _extract_topic_entities(graph, papers, topic):
    """Extract key entities from the current graph and papers — domain grounding."""
    entities = graph.entities if hasattr(graph, 'entities') else {}
    relationships = graph.relationships if hasattr(graph, 'relationships') else {}

    # Get entity names and their connectivity
    entity_names = []
    for eid, edata in entities.items():
        name = edata.get("name", eid)
        etype = edata.get("type", "unknown")
        papers_count = len(edata.get("papers", []))
        entity_names.append({"name": name, "type": etype, "papers": papers_count, "id": eid})

    # Sort by paper count (most studied first)
    entity_names.sort(key=lambda e: e["papers"], reverse=True)

    # Extract key terms from topic
    topic_words = set(w.lower() for w in re.split(r'\W+', topic) if len(w) > 3)

    # Get relationship types
    rel_types = Counter(r.get("relation", r.get("type", "unknown")) for r in relationships)

    return {
        "entities": entity_names,
        "topic_words": topic_words,
        "rel_types": rel_types,
        "relationships": relationships,
    }


def generate_hypotheses_algorithmic(graph, gaps, anomalies, topic, domain):
    """
    Generate hypotheses without LLM calls.
    v2.1: Now grounded in actual graph entities — no more hardcoded cosmology templates.
    """
    hypotheses = []

    entities = graph.entities if hasattr(graph, 'entities') else {}
    relationships = graph.relationships if hasattr(graph, 'relationships') else {}

    # Extract domain-grounded context
    context = _extract_topic_entities(graph, [], topic)
    entity_list = context.get("entities", [])
    top_entities = [e.get("name", "") for e in entity_list[:10]]

    # 1. From gaps: propose hidden variables for orphan observations
    for gap in gaps[:5]:
        if gap.get("type") == "orphan_observation":
            entity = gap.get("entity", gap.get("reason", ""))
            # Find related entities from the graph
            related = _find_related_entities(entity, entity_list, relationships)
            related_str = ", ".join(related[:3]) if related else "other observed entities"
            hypotheses.append({
                "name": f"Hidden mechanism connecting {entity} to {related_str}",
                "type": "proposed",
                "description": f"The observation '{entity}' appears in the literature but lacks a causal explanation. "
                              f"Based on the knowledge graph, it may be connected to {related_str}. "
                              f"Propose a domain-specific mechanism that explains this orphan observation "
                              f"in the context of {topic}.",
                "key_parameters": [{"name": "entity", "expected_value": entity, "units": ""}],
                "predictions": [f"If a hidden mechanism connects '{entity}' to {related_str}, "
                              f"then targeted experiments should reveal correlations between them."],
                "literature_basis": [f"Gap detected: {gap.get('reason', '')[:100]}"],
                "is_novel_vs_known": "novel",
                "confidence": 0.4,
                "source": "algorithmic_gap_analysis",
                "domain": domain,
                "grounded_entities": [entity] + related[:3],
            })

    # 2. From anomalies: propose explanations for outlier entities
    for anomaly in anomalies[:5]:
        if anomaly.get("type") == "outlier_entity":
            entity = anomaly.get("entity", "")
            z_score = anomaly.get("z_score", 0)
            # Find what this hub connects to
            connected = _get_connected_entities(entity, relationships, entity_list)
            connected_str = ", ".join(connected[:5]) if connected else "multiple domains"
            hypotheses.append({
                "name": f"Central role of {entity} in {topic}",
                "type": "proposed",
                "description": f"'{entity}' is a hub entity (z={z_score:.1f}) connecting: {connected_str}. "
                              f"This unusually high connectivity suggests {entity} plays a mechanistic role "
                              f"that current models may underestimate. Propose that {entity} has a "
                              f"regulatory or mediating function in the system described by {topic}.",
                "key_parameters": [{"name": "z_score", "expected_value": str(z_score), "units": ""}],
                "predictions": [f"If {entity}'s hub role is mechanistic, then experimentally perturbing it "
                              f"should disrupt multiple downstream pathways simultaneously."],
                "literature_basis": [f"Anomaly: {entity} degree z={z_score:.1f}"],
                "is_novel_vs_known": "novel",
                "confidence": 0.5,
                "source": "algorithmic_anomaly_analysis",
                "domain": domain,
                "grounded_entities": [entity] + connected[:5],
            })

    # 3. From prediction violations: propose missing direct connections
    for anomaly in anomalies[:5]:
        if anomaly.get("type") == "prediction_violation":
            reason = anomaly.get("reason", "")
            # Extract entity names from the violation reason
            entities_in_path = re.findall(r'([A-Za-z_][\w\s]*?)(?:→|→|->)', reason)
            if len(entities_in_path) >= 2:
                src, dst = entities_in_path[0].strip(), entities_in_path[-1].strip()
                hypotheses.append({
                    "name": f"Direct mechanism: {src} → {dst}",
                    "type": "proposed",
                    "description": f"The knowledge graph shows an indirect path between '{src}' and '{dst}' "
                                  f"but no direct connection. This suggests a missing causal link. "
                                  f"Propose that {src} directly influences {dst} through a mechanism "
                                  f"not yet captured in the literature for {topic}.",
                    "key_parameters": [],
                    "predictions": [f"If {src} directly affects {dst}, then experiments isolating "
                                  f"this pathway should show measurable correlation."],
                    "literature_basis": [f"Graph analysis: indirect path {src}→{dst}"],
                    "is_novel_vs_known": "novel",
                    "confidence": 0.35,
                    "source": "algorithmic_graph_analysis",
                    "domain": domain,
                    "grounded_entities": [src, dst],
                })

    # 4. From graph structure: propose missing connections
    missing_links = _find_missing_links(graph)
    for link in missing_links[:3]:
        # Only include if entities are domain-relevant (appear in papers)
        if link['source'] in top_entities or link['target'] in top_entities:
            hypotheses.append({
                "name": f"Connection: {link['source']} ↔ {link['target']}",
                "type": "proposed",
                "description": f"Entities '{link['source']}' and '{link['target']}' share {link['common_count']} "
                              f"common neighbors but have no direct relationship. In the context of {topic}, "
                              f"this structural hole suggests a missing mechanistic link.",
                "key_parameters": [{"name": "common_neighbors", "expected_value": str(link['common_count']), "units": ""}],
                "predictions": [f"If '{link['source']}' and '{link['target']}' are connected, "
                              f"then experimental studies should find correlations between them."],
                "literature_basis": [f"Graph analysis: {link['common_count']} common neighbors"],
                "is_novel_vs_known": "novel",
                "confidence": 0.35,
                "source": "algorithmic_graph_analysis",
                "domain": domain,
                "grounded_entities": [link['source'], link['target']],
            })

    # 5. Domain-specific hypotheses built from ACTUAL entities in the graph
    #    (Replaces the old hardcoded G(z) / Early Dark Energy templates)
    domain_hypotheses = _generate_entity_grounded_hypotheses(
        graph, entity_list, relationships, topic, domain
    )
    hypotheses.extend(domain_hypotheses)

    return hypotheses


def _find_related_entities(entity_name, entity_list, relationships):
    """Find entities related to a given entity through the graph."""
    related = []
    entity_lower = entity_name.lower()
    for rel in relationships:
        src = rel.get("source", "")
        tgt = rel.get("target", "")
        src_name = rel.get("source_name", "")
        tgt_name = rel.get("target_name", "")
        if entity_lower in src.lower() or entity_lower in src_name.lower():
            related.append(tgt_name or tgt)
        elif entity_lower in tgt.lower() or entity_lower in tgt_name.lower():
            related.append(src_name or src)
    # Deduplicate and clean
    seen = set()
    clean = []
    for r in related:
        r_clean = r.split("_", 1)[-1] if "_" in r else r
        if r_clean and r_clean.lower() != entity_lower and r_clean not in seen:
            seen.add(r_clean)
            clean.append(r_clean)
    return clean[:5]


def _get_connected_entities(entity_name, relationships, entity_list):
    """Get all entities directly connected to a given entity."""
    connected = []
    for rel in relationships:
        src = rel.get("source", "")
        tgt = rel.get("target", "")
        if entity_name.lower() in src.lower():
            connected.append(tgt)
        elif entity_name.lower() in tgt.lower():
            connected.append(src)
    # Resolve IDs to names
    name_map = {e.get("id", ""): e.get("name", "") for e in entity_list}
    resolved = []
    seen = set()
    for c in connected:
        name = name_map.get(c, c)
        if name not in seen and name.lower() != entity_name.lower():
            seen.add(name)
            resolved.append(name)
    return resolved[:10]


def _generate_entity_grounded_hypotheses(graph, entity_list, relationships, topic, domain):
    """
    Generate domain-specific hypotheses from actual entities in the graph.
    This replaces the old hardcoded templates that always returned G(z) and Early Dark Energy.
    """
    hypotheses = []

    # Get process-type and object-type entities
    processes = [e for e in entity_list if e.get("type") in ("process", "measurement", "phenomenon")]
    objects = [e for e in entity_list if e.get("type") in ("object", "instrument", "material")]
    properties = [e for e in entity_list if e.get("type") in ("property", "measurement")]

    # Strategy 1: Propose that a process affects an object
    if processes and objects:
        proc = processes[0].get("name", "")
        obj = objects[0].get("name", "")
        hypotheses.append({
            "name": f"{proc} modulates {obj}",
            "type": "alternative",
            "description": (
                f"Propose that the process '{proc}' directly modulates the properties of '{obj}' "
                f"in ways not captured by current models of {topic}. This would explain observed "
                f"correlations in the knowledge graph and predict specific measurable effects."
            ),
            "key_parameters": [{"name": "modulation_strength", "expected_value": "unknown", "units": ""}],
            "predictions": [
                f"If {proc} modulates {obj}, then varying {proc} should produce measurable changes in {obj}'s observable properties.",
                f"The effect should scale with the intensity of {proc}.",
            ],
            "literature_basis": [f"Entity '{proc}' and '{obj}' both appear in {topic} literature"],
            "is_novel_vs_known": "novel",
            "confidence": 0.5,
            "source": "entity_grounded",
            "domain": domain,
            "grounded_entities": [proc, obj],
        })

    # Strategy 2: Propose that two unconnected processes share a common cause
    if len(processes) >= 2:
        p1, p2 = processes[0].get("name", ""), processes[1].get("name", "")
        hypotheses.append({
            "name": f"Common cause: {p1} ↔ {p2}",
            "type": "alternative",
            "description": (
                f"The processes '{p1}' and '{p2}' both appear in the {topic} literature but "
                f"are not directly connected. Propose a shared upstream cause or common driver "
                f"that produces both phenomena, which would explain their co-occurrence."
            ),
            "key_parameters": [],
            "predictions": [
                f"If a common cause drives both {p1} and {p2}, then they should co-vary in experimental settings.",
                f"Suppressing the common cause should reduce both phenomena simultaneously.",
            ],
            "literature_basis": [f"Both '{p1}' and '{p2}' appear in graph for {topic}"],
            "is_novel_vs_known": "novel",
            "confidence": 0.45,
            "source": "entity_grounded",
            "domain": domain,
            "grounded_entities": [p1, p2],
        })

    # Strategy 3: Propose that a measurement anomaly reveals new physics
    if properties:
        prop = properties[0].get("name", "")
        hypotheses.append({
            "name": f"Novel interpretation of {prop}",
            "type": "alternative",
            "description": (
                f"The measured property '{prop}' in the context of {topic} may not conform "
                f"to standard models. Propose that {prop} reflects an underlying mechanism "
                f"not yet accounted for, potentially involving entities at the boundary of "
                f"current knowledge."
            ),
            "key_parameters": [{"name": prop, "expected_value": "to be determined", "units": ""}],
            "predictions": [
                f"If {prop} reflects new physics, then precision measurements should deviate from standard model predictions.",
                f"The deviation should correlate with other anomalies in the {topic} dataset.",
            ],
            "literature_basis": [f"Property '{prop}' measured in {topic} studies"],
            "is_novel_vs_known": "novel",
            "confidence": 0.4,
            "source": "entity_grounded",
            "domain": domain,
            "grounded_entities": [prop],
        })

    return hypotheses


def generate_mechanisms_algorithmic(graph, hypotheses, topic, domain):
    """
    Generate causal mechanisms without LLM calls.
    v2.1: Uses graph paths and entity-grounded descriptions.
    """
    mechanisms = []

    for hyp in hypotheses[:5]:
        name = hyp.get("name", "")
        desc = hyp.get("description", "")
        grounded = hyp.get("grounded_entities", [])

        # Extract causal steps from description
        steps = _extract_causal_steps(desc)

        # Build a domain-grounded mechanism description
        if grounded and len(grounded) >= 2:
            mech_desc = f"In the context of {topic}: "
            for i in range(len(grounded) - 1):
                mech_desc += f"{grounded[i]} influences {grounded[i+1]} through a causal pathway. "
            mech_desc += f"This mechanism is grounded in entities extracted from the literature."
        else:
            mech_desc = desc

        mechanisms.append({
            "name": f"Mechanism: {name}",
            "type": "causal_pathway",
            "description": mech_desc,
            "steps": steps,
            "mathematical_model": _extract_equations_from_text(desc),
            "key_parameters": hyp.get("key_parameters", []),
            "literature_basis": hyp.get("literature_basis", []),
            "is_novel_vs_known": hyp.get("is_novel_vs_known", "unknown"),
            "confidence": hyp.get("confidence", 0.5),
            "predictions": hyp.get("predictions", []),
            "source": "algorithmic",
            "domain": domain,
            "grounded_entities": grounded,
        })

    return mechanisms


def generate_predictions_algorithmic(mechanisms, hypotheses, topic, domain, graph=None):
    """
    Generate testable predictions without LLM calls.
    v2.1: Extracts predictions from hypotheses and mechanisms, grounded in domain.
    """
    predictions = []

    for hyp in hypotheses[:5]:
        for pred in hyp.get("predictions", []):
            if isinstance(pred, str) and len(pred) > 20:
                # Check if prediction has quantitative content
                has_numbers = any(c.isdigit() for c in pred)
                grounded = hyp.get("grounded_entities", [])
                predictions.append({
                    "statement": pred,
                    "type": "novel" if has_numbers else "correlational",
                    "mechanism_source": hyp.get("name", ""),
                    "testability": "moderate" if has_numbers else "hard",
                    "falsification": f"Observe the opposite of: {pred[:100]}",
                    "confidence": hyp.get("confidence", 0.5),
                    "source": "algorithmic",
                    "domain": domain,
                    "grounded_entities": grounded,
                })

    # Add domain-specific predictions from graph entities
    entities = graph.entities if graph and hasattr(graph, 'entities') else {}
    for eid, edata in list(entities.items())[:5]:
        name = edata.get("name", "")
        etype = edata.get("type", "")
        if etype in ("process", "measurement") and name:
            predictions.append({
                "statement": f"If '{name}' is systematically varied in experiments related to {topic}, "
                           f"then downstream observables should show measurable correlated changes.",
                "type": "interventional",
                "mechanism_source": f"Graph entity: {name}",
                "testability": "moderate",
                "falsification": f"Varying {name} produces no measurable change in observables.",
                "confidence": 0.4,
                "source": "algorithmic_entity_grounded",
                "domain": domain,
                "grounded_entities": [name],
            })

    return predictions


def compare_theories_algorithmic(theories, graph, papers):
    """
    Compare theories without LLM calls.
    v2.1: Includes domain relevance scoring.
    """
    scored = []

    # Build entity set from graph for relevance checking
    entities = graph.entities if hasattr(graph, 'entities') else {}
    graph_entity_names = set()
    for eid, edata in entities.items():
        graph_entity_names.add(edata.get("name", "").lower())

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

        # Factor 6: DOMAIN RELEVANCE (NEW — penalizes theories not grounded in current graph)
        grounded = theory.get("grounded_entities", [])
        if grounded:
            grounded_in_graph = sum(1 for g in grounded if g.lower() in graph_entity_names)
            domain_relevance = grounded_in_graph / max(1, len(grounded))
        else:
            domain_relevance = 0.0
        score += domain_relevance * 20  # Up to 20 bonus points for domain grounding

        # Factor 7: Cross-domain bonus (connections between fields are valuable)
        theory_domain = theory.get("domain", "")
        if theory_domain and theory_domain != graph.domain:
            score *= 1.15  # 15% bonus for cross-domain connections

        theory["scores"] = {
            "explanatory_power": min(1.0, len(explains) * 0.2),
            "predictive_power": min(1.0, len(predictions) * 0.15),
            "simplicity": max(0.1, 1.0 - len(params) * 0.15),
            "novelty": 0.7 if theory.get("is_novel_vs_known") == "novel" else 0.4,
            "falsifiability": min(1.0, quant_preds * 0.3),
            "evidence_support": min(1.0, len(lit) * 0.2),
            "domain_relevance": domain_relevance,
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
        src = rel.get("source")
        tgt = rel.get("target")
        if src and tgt:
            adj[src].add(tgt)
            adj[tgt].add(src)

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
