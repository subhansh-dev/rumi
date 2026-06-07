"""
discovery_pipeline_v2.py — RUMI's Genuine Scientific Discovery Pipeline.

The difference from run_full_pipeline.py:
  Old: Papers → Entity Extraction → Knowledge Graph → Hypothesis → Skeptic
  New: Papers → Knowledge Graph → GAPS → ANOMALIES → HIDDEN VARIABLES →
       MECHANISMS → PREDICTIONS → THEORY COMPETITION → COMPUTATIONAL
       VERIFICATION → DISCOVERY SCORING → Discovery Report

This is not a research assistant. This is a discovery engine.

Pipeline:
  Phase 1: LITERATURE — Fetch real papers (arXiv + PubMed)
  Phase 2: KNOWLEDGE GRAPH — Entity extraction + relationship building
  Phase 3: GAP DETECTION — What's missing in the knowledge?
  Phase 4: ANOMALY DETECTION — What doesn't fit existing theories?
  Phase 5: MISSING VARIABLES — Propose hidden entities/processes
  Phase 6: MECHANISM GENERATION — Build causal pathways
  Phase 7: PREDICTION ENGINE — Generate testable predictions
  Phase 8: THEORY COMPETITION — Compare multiple explanations
  Phase 9: COMPUTATIONAL VERIFICATION — Run actual computations
  Phase 10: SKEPTIC REVIEW — Adversarial critique
  Phase 11: DISCOVERY SCORING — Final quality gate
  Phase 12: DISCOVERY REPORT — Structured output

Output format:
  Observation: [what we see]
  Problem: [what existing theories can't explain]
  Gap: [what's missing]
  Proposed Mechanism: [our explanation]
  Predictions: [what should be true if we're right]
  Computational Test: [what we computed]
  Result: [supports/contradicts]
  Discovery Score: [0-100]
"""

import json
import time
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Fix Unicode encoding on Windows (cp1252 can't handle scientific symbols)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Existing modules
from discovery.llm_client import call as llm_call, call_json, get_status
from discovery.citation_grounding import fetch_papers, build_citation_context, ground_claims
from discovery.computational import run_all_calculations, format_calculations_for_prompt
from discovery.domain_computational import run_domain_calculations, format_for_prompt, DOMAIN_COMPUTATIONS
from discovery.claim_labeler import label_report, generate_confidence_summary
from discovery.claim_provenance import ProvenanceTracker
from discovery.graph import KnowledgeGraph
from discovery.contradiction_miner import ContradictionMiner

# Discovery modules (v2.1) — all wired into pipeline phases
from discovery.knowledge_gap_detector import KnowledgeGapDetector
from discovery.anomaly_detector import AnomalyDetector
from discovery.missing_variable_generator import MissingVariableGenerator
from discovery.mechanism_generator import MechanismGenerator
from discovery.prediction_engine import PredictionEngine
from discovery.theory_competition import TheoryCompetition
from discovery.discovery_scorer import DiscoveryScorer
from discovery.computational_verification import ComputationalVerifier
from discovery.novelty_checker import NoveltyChecker
from discovery.falsification_engine import FalsificationEngine
from discovery.discovery_tournament import DiscoveryTournament
from discovery.scientific_simulator import ScientificSimulator
from discovery.bayesian_scorer import BayesianScorer
from discovery.literature_contradiction_scorer import LiteratureContradictionScorer
from discovery.resilient_llm import ResilientLLM
from discovery.hypothesis_memory import HypothesisMemory


# Domain detection (reused from run_full_pipeline.py)
DOMAIN_KEYWORDS = {
    "space_astronomy": ["phosphine", "venus", "exoplanet", "mars", "jupiter", "black hole",
                        "neutron star", "pulsar", "galaxy", "telescope", "nasa", "jwst",
                        "spectral", "atmosphere", "biosignature", "cosmolog", "megastructure",
                        "dyson", "technosignature", "stellar", "dimming", "cme", "cosmic",
                        "supernova", "gravitational wave", "dark energy", "hubble",
                        "primordial", "hawking", "microlensing", "lensing"],
    "neuroscience": ["neuron", "brain", "neurotransmitter", "dopamine", "serotonin",
                     "synaptic", "cortex", "hippocampus", "consciousness", "fmri",
                     "neural", "axon", "dendrite", "receptor", "cognition"],
    "drug_discovery": ["drug", "inhibitor", "kinase", "antibiotic", "cancer", "pharma",
                       "therapeutic", "binding affinity", "clinical trial", "ic50", "ec50",
                       "kras", "egfr", "mutation", "resistance", "target", "receptor",
                       "antibody", "molecule", "compound", "assay", "screen"],
    "materials_science": ["perovskite", "battery", "catalyst", "bandgap", "nanomaterial",
                          "graphene", "2d material", "solar cell", "semiconductor", "alloy",
                          "crystal", "thin film", "dopant", "conductivity", "elastic"],
    "climate_energy": ["climate", "carbon", "emission", "renewable", "solar", "wind",
                       "greenhouse", "warming", "co2", "temperature", "methane",
                       "sea level", "ice sheet", "permafrost", "aerosol"],
    "ecology": ["species", "biodiversity", "ecosystem", "conservation", "habitat",
                "extinction", "population", "invasion", "endangered", "predator",
                "prey", "migration", "foraging", "biome", "pollinator"],
    "physics": ["quantum", "particle", "higgs", "gravity", "wave", "boson",
                "fermion", "relativity", "dark matter", "entanglement", "quark",
                "lepton", "gauge", "symmetry", "renormalization", "scattering"],
    "computer_science": ["neural network", "llm", "transformer", "algorithm", "machine learning",
                         "deep learning", "dataset", "benchmark", "architecture",
                         "reinforcement", "generative", "diffusion", "attention"],
    "public_health": ["vaccine", "pandemic", "epidemic", "disease", "mortality",
                      "prevalence", "intervention", "clinical", "public health",
                      "cohort", "randomized", "placebo", "efficacy", "outbreak"],
    "chemistry": ["reaction", "synthesis", "catalysis", "compound", "organic",
                  "inorganic", "analytical", "spectroscopy", "electrochemistry",
                  "oxidation", "reduction", "polymer", "solvent", "yield"],
    "mathematics": ["theorem", "proof", "conjecture", "prime", "topology",
                    "optimization", "sequence", "algebra", "geometry", "manifold",
                    "eigenvalue", "convergence", "bound", "asymptotic"],
}


def detect_domain(topic: str) -> str:
    topic_lower = topic.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in topic_lower)
        if score > 0:
            scores[domain] = score
    return max(scores, key=scores.get) if scores else "general"


def extract_entities_from_papers(papers: list, domain: str) -> dict:
    """LLM entity extraction from paper abstracts."""
    paper_text = ""
    for i, p in enumerate(papers[:8], 1):
        paper_text += f"\n[{i}] {p.get('title', '')}\n    {p.get('abstract', '')[:300]}\n"

    prompt = f"""Extract scientific entities and relationships from these papers.

Domain: {domain}
Papers:
{paper_text}

Output JSON with exactly this structure:
{{
  "entities": [
    {{"name": "entity name", "type": "gene|protein|disease|drug|chemical|organism|phenomenon|technology|method|concept", "aliases": []}}
  ],
  "relationships": [
    {{"source": "entity1", "source_type": "type", "relation": "activates|inhibits|causes|treats|enables|uses|produces|detects|measures|correlates_with|associated_with", "target": "entity2", "target_type": "type", "confidence": 0.7}}
  ]
}}

Extract 10-25 entities and 10-30 relationships. Be specific, not generic."""

    try:
        result = call_json(prompt, max_tokens=4096)
        # Fallback to Gemini if Groq fails
        if not result:
            print("    [DEBUG] Groq returned None, trying Gemini...")
            try:
                result = call_json(prompt, max_tokens=4096, provider="gemini")
            except Exception as e:
                print(f"    [DEBUG] Gemini failed: {e}")
        if result:
            print(f"    [DEBUG] Got result type={type(result)}, len={len(str(result))}")
        else:
            print("    [DEBUG] Both providers returned None")
        if result:
            if isinstance(result, str):
                text = result.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    text = text.rsplit("```", 1)[0].strip()
                # Robust JSON parsing
                try:
                    result = json.loads(text)
                except json.JSONDecodeError:
                    # Try to fix common issues
                    import re
                    # Try extracting just the JSON object
                    json_match = re.search(r'\{[\s\S]*\}', text)
                    if json_match:
                        try:
                            result = json.loads(json_match.group())
                        except json.JSONDecodeError:
                            # Try fixing trailing commas
                            fixed = re.sub(r',\s*}', '}', json_match.group())
                            fixed = re.sub(r',\s*]', ']', fixed)
                            try:
                                result = json.loads(fixed)
                            except json.JSONDecodeError:
                                result = None
                    else:
                        result = None
            if isinstance(result, dict):
                return result
    except Exception as e:
        print(f"    Entity extraction failed: {e}")

    entities = []
    for p in papers:
        title = p.get("title", "")
        if title:
            entities.append({"name": title[:60], "type": "concept", "aliases": []})
    return {"entities": entities, "relationships": []}


def build_knowledge_graph(papers: list, domain: str) -> KnowledgeGraph:
    """Build knowledge graph from papers — algorithmic extraction (fast, reliable) + optional LLM."""
    print("    Extracting entities from papers...")

    # Primary: algorithmic extraction (always works, no LLM needed)
    from discovery.entity_extractor import extract_entities_from_papers as algo_extract
    extracted = algo_extract(papers, domain)
    print(f"    Algorithmic: {len(extracted.get('entities', []))} entities, {len(extracted.get('relationships', []))} relationships")

    # Optional enhancement: LLM extraction for additional entities/relationships
    try:
        llm_extracted = extract_entities_from_papers(papers[:5], domain)  # fewer papers for speed
        llm_entities = llm_extracted.get("entities", [])
        llm_rels = llm_extracted.get("relationships", [])
        if llm_entities or llm_rels:
            # Merge LLM results (add non-duplicates)
            existing_names = {e["name"].lower() for e in extracted.get("entities", [])}
            for e in llm_entities:
                if e["name"].lower() not in existing_names:
                    extracted.setdefault("entities", []).append(e)
                    existing_names.add(e["name"].lower())
            for r in llm_rels:
                key = (r.get("source", "").lower(), r.get("target", "").lower())
                if key not in {(rel.get("source", "").lower(), rel.get("target", "").lower()) for rel in extracted.get("relationships", [])}:
                    extracted.setdefault("relationships", []).append(r)
            print(f"    + LLM enhancement: {len(llm_entities)} entities, {len(llm_rels)} relationships")
    except Exception as e:
        print(f"    LLM enhancement skipped: {e}")

    graph = KnowledgeGraph(persist=True)  # Load previous graph — knowledge accumulates across runs
    graph.domain = domain
    # Track run count for staleness management
    graph._run_count = getattr(graph, '_run_count', 0) + 1
    print(f"  [Graph] Loaded {len(graph.entities)} entities, {len(graph.relationships)} relationships from previous runs")

    for p in papers:
        pmid = p.get("id", p.get("citation_key", "unknown"))
        graph.add_paper(pmid, p["title"], p.get("abstract", ""), p.get("url", ""), p.get("year", ""))

    for ent in extracted.get("entities", []):
        pmid = papers[0].get("id", "unknown") if papers else "unknown"
        graph.add_paper_entities([ent], pmid)

    for rel in extracted.get("relationships", []):
        pmid = papers[0].get("id", "unknown") if papers else "unknown"
        graph.add_relationships([rel], pmid)

    # Prune stale entities — keep only those referenced by papers
    if len(graph.entities) > 500:
        current_paper_ids = set(p.get("id", p.get("citation_key", "")) for p in papers)
        stale = []
        for eid, ent in graph.entities.items():
            ent_papers = set(ent.get("papers", []))
            # Keep if referenced by any current paper
            if ent_papers & current_paper_ids:
                continue
            # Keep if referenced by 3+ papers (well-established entity)
            if len(ent_papers) >= 3:
                continue
            # Prune entities with only old paper references
            if len(ent_papers) <= 1:
                stale.append(eid)
        for eid in stale[:200]:  # max 200 pruned per run
            del graph.entities[eid]
        if stale:
            print(f"    Pruned {len(stale)} stale entities (kept {len(graph.entities)})")

    graph.save(session_id=f"discovery_v2_{int(time.time())}")
    print(f"    Graph: {len(graph.entities)} entities, {len(graph.relationships)} relationships")
    return graph


def run_discovery_pipeline(topic: str, domain: str = "", mode: str = "full") -> dict:
    """
    Run the complete discovery pipeline.

    Args:
        topic: Research topic
        domain: Domain (auto-detected if empty)
        mode: "quick" (phases 1-5), "standard" (1-8), "full" (all 12)

    Returns:
        Complete discovery report dict
    """
    if not domain:
        domain = detect_domain(topic)

    status = get_status()
    t_start = time.time()
    provider_name = status.get("primary", "auto") if isinstance(status, dict) else "auto"

    # Load discovery archive — what RUMI already knows from past runs
    from discovery.discovery_archive import get_archive_context, save_to_archive
    archive_context = get_archive_context(topic, domain)
    if "No previous" not in archive_context:
        # Trim archive context — only keep most recent run summary
        lines = archive_context.split("\n")
        trimmed = []
        for line in lines[:15]:  # max 15 lines from archive
            trimmed.append(line)
        archive_context = "\n".join(trimmed)[:1000]  # cap at 1000 chars
        print(f"  [Archive] Loaded past discovery context (trimmed)", flush=True)

    # Hypothesis memory loading CUT — cross-topic noise outweighs dedup benefit
    # HypothesisEngine and HypothesisTournament still use HypothesisMemory internally for dedup

    # Add domain-specific research template context
    try:
        from discovery.domain_templates import get_research_question_prompt, get_validation_prompt
        domain_q = get_research_question_prompt(domain, topic)
        domain_v = get_validation_prompt(domain)
        if domain_q:
            archive_context += "\n\n" + domain_q
        if domain_v:
            archive_context += "\n" + domain_v
        print(f"  [Domain Template] Loaded {domain} research context", flush=True)
    except Exception:
        pass

    # Add domain ontology context — real scientific knowledge for the domain
    try:
        from discovery.domain_ontologies import DOMAIN_ONTOLOGIES
        ontology = DOMAIN_ONTOLOGIES.get(domain, {})
        if ontology:
            onto_lines = [f"\nDOMAIN ONTOLOGY ({domain}):"]
            # Known mechanisms
            mechanisms = ontology.get("mechanisms", {})
            if mechanisms:
                onto_lines.append("Known mechanisms:")
                for name, desc in list(mechanisms.items())[:5]:
                    onto_lines.append(f"  - {name}: {desc[:120]}")
            # Key equations
            equations = ontology.get("equations", {})
            if equations:
                onto_lines.append("Key equations:")
                for name, eq in list(equations.items())[:5]:
                    onto_lines.append(f"  - {name}: {eq}")
            # Known anomalies (unsolved problems)
            anomalies = ontology.get("anomalies", {})
            if anomalies:
                onto_lines.append("Known unsolved anomalies:")
                for name, desc in list(anomalies.items())[:5]:
                    onto_lines.append(f"  - {name}: {desc[:120]}")
            # Constraints
            constraints = ontology.get("constraints", {})
            if constraints:
                onto_lines.append("Physical constraints:")
                for name, desc in list(constraints.items())[:3]:
                    onto_lines.append(f"  - {name}: {desc[:100]}")
            archive_context += "\n" + "\n".join(onto_lines)
            print(f"  [Domain Ontology] Loaded {len(mechanisms)} mechanisms, {len(equations)} equations, {len(anomalies)} anomalies", flush=True)
    except Exception as e:
        print(f"  [WARN] Domain ontology skipped: {e}", flush=True)

    # Generate run ID for this pipeline execution
    run_id = f"run_{int(time.time())}"

    report = {
        "topic": topic,
        "domain": domain,
        "mode": mode,
        "pipeline_version": "v2_discovery",
        "started_at": datetime.now().isoformat(),
        "phases": {},
        "errors": [],
    }

    print("=" * 70, flush=True)
    print("  RUMI — DISCOVERY PIPELINE v2", flush=True)
    print("=" * 70, flush=True)
    print(f"  Topic:     {topic}")
    print(f"  Domain:    {domain}")
    print(f"  Mode:      {mode}")
    print(f"  Provider:  {provider_name.upper()}")
    print("=" * 70)

    # ══════════════════════════════════════════════════════════════
    # PHASE 1: LITERATURE
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 1/12] LITERATURE — Fetching papers from 4 sources (3 rounds)...", flush=True)
    try:
        # Round 1: Full topic query across all 4 sources
        papers = fetch_papers(topic, max_arxiv=20, max_pubmed=20, max_s2=20, max_crossref=20)
        print(f"  Round 1: {len(papers)} papers")

        # Round 2: Shortened key-phrase query
        topic_words = [w for w in topic.lower().split() if len(w) > 4]
        if len(topic_words) >= 2:
            broad_query = " ".join(topic_words[:4])
            existing_titles = {p["title"].lower()[:60] for p in papers}
            r2 = fetch_papers(broad_query, max_arxiv=15, max_pubmed=15, max_s2=15, max_crossref=15)
            added = 0
            for p in r2:
                if p["title"].lower()[:60] not in existing_titles:
                    existing_titles.add(p["title"].lower()[:60])
                    papers.append(p)
                    added += 1
            print(f"  Round 2: +{added} new papers ({len(papers)} total)")

        # Round 3: Domain-specific sub-queries for deeper coverage
        if len(papers) < 40:
            sub_queries = []
            topic_lower = topic.lower()
            if "black hole" in topic_lower:
                sub_queries = ["primordial black holes dark matter",
                               "Hawking radiation gamma ray",
                               "sub-solar mass gravitational wave merger",
                               "PBH microlensing OGLE EROS"]
            elif "exoplanet" in topic_lower:
                sub_queries = ["exoplanet atmosphere characterization",
                               "biosignature detection JWST"]
            elif "neuroscience" in topic_lower or "brain" in topic_lower:
                sub_queries = ["neural network connectivity",
                               "brain-computer interface"]
            existing_titles = {p["title"].lower()[:60] for p in papers}
            for sq in sub_queries[:3]:
                r3 = fetch_papers(sq, max_arxiv=10, max_pubmed=10, max_s2=10, max_crossref=10)
                for p in r3:
                    if p["title"].lower()[:60] not in existing_titles:
                        existing_titles.add(p["title"].lower()[:60])
                        papers.append(p)
            print(f"  Round 3: {len(papers)} total papers after domain queries")

        sources = set(p.get('source', '?') for p in papers)
        print(f"  Total: {len(papers)} papers from {len(sources)} sources: {', '.join(sorted(sources))}")
        for p in papers[:5]:
            cites = p.get('citation_count', '')
            cite_str = f" ({cites} citations)" if cites else ""
            print(f"    [{p.get('source', '?')}] {p.get('title', '?')[:65]}{cite_str}")
        citation_context = build_citation_context(papers)
        report["phases"]["literature"] = {
            "papers_found": len(papers),
            "sources": list(set(p.get("source", "?") for p in papers)),
            "papers": papers,
        }
    except Exception as e:
        print(f"  [ERROR] Literature fetch failed: {e}")
        report["errors"].append(f"Phase 1: {e}")
        papers = []
        citation_context = ""

    # ══════════════════════════════════════════════════════════════
    # -- Retrieval Filter — ALWAYS run to rank papers by relevance --
    if papers:
        try:
            from discovery.retrieval_filter import RetrievalFilter
            rfilter = RetrievalFilter()
            for p in papers:
                if "pmid" not in p:
                    p["pmid"] = p.get("id", p.get("title", "")[:30])
            filtered = rfilter.filter(papers, topic, domain=domain, min_papers=5, max_papers=30)
            if filtered and len(filtered) < len(papers):
                print(f"  [Retrieval Filter] {len(papers)} -> {len(filtered)} papers", flush=True)
                papers = filtered
            elif filtered:
                print(f"  [Retrieval Filter] {len(papers)} papers ranked by relevance", flush=True)
        except Exception as e:
            print(f"  [WARN] Retrieval filter skipped: {e}")

    # PHASE 1.5: CITATION NETWORK TRAVERSAL — 2-hop walk
    # ══════════════════════════════════════════════════════════════
    if papers:
        print("\n[Phase 1.5/12] CITATION NETWORK — 2-hop citation walk...", flush=True)
        try:
            from discovery.citation_grounding import traverse_citation_network
            papers = traverse_citation_network(papers, hop_depth=2, top_n=5, refs_per_paper=10)
            citation_context = build_citation_context(papers)
            report["phases"]["citation_network"] = {
                "total_papers": len(papers),
                "citation_hop1": len([p for p in papers if p.get("source") == "citation_hop1"]),
                "citation_hop2": len([p for p in papers if p.get("source") == "citation_hop2"]),
            }
        except Exception as e:
            print(f"  [WARN] Citation traversal failed: {e}")

    # ══════════════════════════════════════════════════════════════
    # PHASE 2: KNOWLEDGE GRAPH
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 2/12] KNOWLEDGE GRAPH — Building...", flush=True)
    try:
        graph = build_knowledge_graph(papers, domain)
        report["phases"]["knowledge_graph"] = {
            "entities": len(graph.entities),
            "relationships": len(graph.relationships),
            "papers": len(graph.papers),
        }
    except Exception as e:
        print(f"  [ERROR] Graph build failed: {e}")
        report["errors"].append(f"Phase 2: {e}")
        graph = KnowledgeGraph(persist=False)

    # -- Link Prediction — find missing relationships --
    if graph.entities and len(graph.entities) >= 3:
        try:
            from discovery.link_predictor import LinkPredictor
            lp = LinkPredictor(graph=graph)
            link_results = lp.predict_missing_links(top_k=10)
            predictions = link_results.get("predictions", [])
            if predictions:
                # Add high-confidence predicted links to graph
                added = 0
                for pred in predictions:
                    conf = pred.get("confidence", 0)
                    if conf >= 0.5:
                        src = pred.get("source", "")
                        tgt = pred.get("target", "")
                        rel = pred.get("predicted_relation", "associated_with")
                        if src and tgt:
                            graph.relationships.append({
                                "source": src, "relation": rel, "target": tgt,
                                "confidence": conf, "papers": ["link_prediction"],
                            })
                            added += 1
                print(f"  [Link Prediction] {len(predictions)} predicted, {added} added to graph (conf≥0.5)", flush=True)
                report["phases"]["knowledge_graph"]["predicted_links"] = len(predictions)
                report["phases"]["knowledge_graph"]["predicted_links_added"] = added
        except Exception as e:
            print(f"  [WARN] Link prediction skipped: {e}", flush=True)

    # -- Entity Enrichment — enrich graph with real API data --
    try:
        from discovery.domains import get_domain
        domain_cfg = get_domain(domain)
        if domain_cfg:
            enrich_sources = domain_cfg.get("enrichment", [])
            if enrich_sources:
                total_enriched = 0
                # PubChem enrichment
                if "pubchem" in enrich_sources:
                    try:
                        from discovery.pubchem import search_compound
                        chem_types = {"drug", "compound", "material", "chemical"}
                        for eid, ent in list(graph.entities.items()):
                            if ent.get("type") in chem_types:
                                pc = search_compound(ent["name"])
                                if pc and pc.get("molecular_formula"):
                                    ent.setdefault("enrichment", {})["pubchem"] = {
                                        "formula": pc.get("molecular_formula"),
                                        "mw": pc.get("molecular_weight"),
                                    }
                                    total_enriched += 1
                    except Exception:
                        pass
                # UniProt enrichment
                if "uniprot" in enrich_sources:
                    try:
                        from discovery.uniprot import enrich_entities as enrich_uniprot
                        enriched = enrich_uniprot(graph)
                        total_enriched += enriched
                    except Exception:
                        pass
                # PDB enrichment
                if "pdb" in enrich_sources:
                    try:
                        from discovery.pdb import enrich_entities as enrich_pdb
                        enriched = enrich_pdb(graph)
                        total_enriched += enriched
                    except Exception:
                        pass
                # NASA enrichment
                if "nasa_api" in enrich_sources:
                    try:
                        from discovery.nasa_api import enrich_entities as enrich_nasa
                        enriched = enrich_nasa(graph)
                        total_enriched += enriched
                    except Exception:
                        pass
                # Materials Project enrichment
                if "materials_project" in enrich_sources:
                    try:
                        from discovery.materials_project import enrich_entities as enrich_mp
                        enriched = enrich_mp(graph)
                        total_enriched += enriched
                    except Exception:
                        pass
                # NIST enrichment — thermochemical data, spectral data (free, no API key)
                if "nist" in enrich_sources:
                    try:
                        from discovery.nist_api import search_compound as nist_search, get_thermochemical_data
                        chem_types = {"chemical", "compound", "drug", "material", "element"}
                        nist_enriched = 0
                        for eid, ent in list(graph.entities.items()):
                            if ent.get("type") in chem_types:
                                nist_results = nist_search(ent["name"], limit=1)
                                if nist_results:
                                    nist_data = nist_results[0]
                                    ent.setdefault("enrichment", {})["nist"] = {
                                        "formula": nist_data.get("formula", ""),
                                        "cas": nist_data.get("cas", ""),
                                        "molecular_weight": nist_data.get("molecular_weight"),
                                        "source": "NIST Chemistry WebBook",
                                    }
                                    # Fetch thermochemical data if we have a CAS number
                                    if nist_data.get("cas"):
                                        try:
                                            thermo = get_thermochemical_data(nist_data["cas"])
                                            if thermo.get("status") == "ok":
                                                ent["enrichment"]["nist"]["thermochemical"] = {
                                                    "boiling_point_K": thermo.get("boiling_point_K"),
                                                    "melting_point_K": thermo.get("melting_point_K"),
                                                    "enthalpy_of_formation": thermo.get("enthalpy_of_formation_kj_mol"),
                                                    "entropy": thermo.get("entropy_J_mol_K"),
                                                    "heat_capacity": thermo.get("heat_capacity_J_mol_K"),
                                                }
                                        except Exception:
                                            pass
                                    nist_enriched += 1
                        total_enriched += nist_enriched
                        if nist_enriched:
                            print(f"  [NIST] {nist_enriched} compounds enriched with thermochemical data", flush=True)
                    except Exception:
                        pass
                # ClinicalTrials enrichment — drug discovery
                if "clinicaltrials" in enrich_sources or domain == "drug_discovery":
                    try:
                        from discovery.clinicaltrials import search_trials
                        drug_entities = {eid: ent for eid, ent in graph.entities.items() if ent.get("type") in ("drug", "compound")}
                        for eid, ent in list(drug_entities.items())[:5]:
                            trials = search_trials(ent.get("name", ""), limit=3)
                            if trials:
                                ent.setdefault("enrichment", {})["clinicaltrials"] = trials
                                total_enriched += 1
                    except Exception:
                        pass

                # INSPIRE HEP enrichment — physics
                if "inspire_hep" in enrich_sources or domain == "physics":
                    try:
                        from discovery.inspire_hep import search_papers as inspire_search
                        for eid, ent in list(graph.entities.items())[:5]:
                            if ent.get("type") in ("phenomenon", "theory", "entity"):
                                papers = inspire_search(ent.get("name", ""), limit=3)
                                if papers:
                                    ent.setdefault("enrichment", {})["inspire_hep"] = len(papers)
                                    total_enriched += 1
                    except Exception:
                        pass

                # LIGO enrichment — gravitational wave events
                if domain == "physics" or "gravitational" in topic.lower():
                    try:
                        from discovery.ligo import search_events
                        events = search_events(limit=5)
                        if events:
                            for event in events[:3]:
                                graph.add_entity(event.get("name", "GW Event"), entity_type="phenomenon")
                            total_enriched += len(events)
                    except Exception:
                        pass

                # OpenFDA enrichment — drug safety data
                if "openfda" in enrich_sources:
                    try:
                        from discovery.openfda import search_drug
                        drug_types = {"drug", "compound", "medication"}
                        for eid, ent in list(graph.entities.items()):
                            if ent.get("type") in drug_types:
                                fda = search_drug(ent["name"])
                                if fda:
                                    ent.setdefault("enrichment", {})["openfda"] = fda
                                    total_enriched += 1
                    except Exception:
                        pass

                # KEGG enrichment — biochemical pathways
                if "kegg" in enrich_sources:
                    try:
                        from discovery.kegg import search_pathway
                        bio_types = {"protein", "gene", "pathway", "enzyme", "compound"}
                        for eid, ent in list(graph.entities.items()):
                            if ent.get("type") in bio_types:
                                kegg = search_pathway(ent["name"])
                                if kegg:
                                    ent.setdefault("enrichment", {})["kegg"] = kegg
                                    total_enriched += 1
                    except Exception:
                        pass

                # NOAA enrichment — climate/ocean data
                if "noaa" in enrich_sources:
                    try:
                        from discovery.noaa_api import search_datasets
                        climate_types = {"phenomenon", "observation", "measurement"}
                        for eid, ent in list(graph.entities.items()):
                            if ent.get("type") in climate_types:
                                noaa = search_datasets(ent["name"], limit=2)
                                if noaa:
                                    ent.setdefault("enrichment", {})["noaa"] = noaa
                                    total_enriched += 1
                    except Exception:
                        pass

                # USGS enrichment — earth science data
                if "usgs" in enrich_sources:
                    try:
                        from discovery.usgs_api import search_earthquakes
                        earth_types = {"phenomenon", "observation", "measurement"}
                        for eid, ent in list(graph.entities.items()):
                            if ent.get("type") in earth_types:
                                usgs = search_earthquakes(ent["name"])
                                if usgs:
                                    ent.setdefault("enrichment", {})["usgs"] = usgs
                                    total_enriched += 1
                    except Exception:
                        pass

                # World Bank enrichment — economics data
                if "world_bank" in enrich_sources:
                    try:
                        from discovery.world_bank_api import search_indicators
                        econ_types = {"indicator", "metric", "phenomenon"}
                        for eid, ent in list(graph.entities.items()):
                            if ent.get("type") in econ_types:
                                wb = search_indicators(ent["name"])
                                if wb:
                                    ent.setdefault("enrichment", {})["world_bank"] = wb
                                    total_enriched += 1
                    except Exception:
                        pass

                # GitHub enrichment — code/data repositories
                if "github" in enrich_sources:
                    try:
                        from discovery.github_api import search_repos
                        for eid, ent in list(graph.entities.items()):
                            if ent.get("type") in ("method", "tool", "algorithm", "framework"):
                                repos = search_repos(ent["name"], limit=2)
                                if repos:
                                    ent.setdefault("enrichment", {})["github"] = repos
                                    total_enriched += 1
                    except Exception:
                        pass

                # DrugBank enrichment — drug data
                if "drugbank" in enrich_sources:
                    try:
                        from discovery.drugbank_mini import search_drug
                        drug_types = {"drug", "compound", "medication"}
                        for eid, ent in list(graph.entities.items()):
                            if ent.get("type") in drug_types:
                                db = search_drug(ent["name"])
                                if db:
                                    ent.setdefault("enrichment", {})["drugbank"] = db
                                    total_enriched += 1
                    except Exception:
                        pass

                # CIR enrichment — chemical identifier resolver
                if "cir" in enrich_sources:
                    try:
                        from discovery.cir_api import resolve
                        chem_types = {"chemical", "compound", "drug", "material"}
                        for eid, ent in list(graph.entities.items()):
                            if ent.get("type") in chem_types:
                                cir = resolve(ent["name"])
                                if cir:
                                    ent.setdefault("enrichment", {})["cir"] = cir
                                    total_enriched += 1
                    except Exception:
                        pass

                if total_enriched:
                    print(f"  [Entity Enrichment] {total_enriched} entities enriched", flush=True)
                    report["phases"]["knowledge_graph"]["enriched"] = total_enriched
    except Exception as e:
        print(f"  [WARN] Entity enrichment skipped: {e}", flush=True)

    # ══════════════════════════════════════════════════════════════
    # PHASE 3: GAP DETECTION
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 3/12] GAP DETECTION — Finding what's missing...", flush=True)
    try:
        # Use algorithmic gap detection (fast, reliable, no LLM needed)
        gap_detector = KnowledgeGapDetector(graph=graph, llm_call=None)
        gap_results = gap_detector.detect_gaps(topic, domain)
        gaps = gap_results.get("top_gaps", [])
        print(f"  Found {len(gaps)} knowledge gaps")
        for g in gaps[:3]:
            print(f"    [{g.get('type', '?')}] {g.get('reason', '')[:80]}")
        report["phases"]["gap_detection"] = gap_results.get("summary", {})
        report["phases"]["gap_detection"]["top_gaps"] = gaps
    except Exception as e:
        print(f"  [ERROR] Gap detection failed: {e}")
        report["errors"].append(f"Phase 3: {e}")
        gaps = []

    # -- Cross-Domain Transfer --
    if gaps:
        try:
            from discovery.cross_domain_transfer import CrossDomainTransfer
            cdt = CrossDomainTransfer()
            analogies = cdt.find_all_source_analogies(domain)
            if analogies:
                print(f"  [Cross-Domain] {len(analogies)} analogies from other fields", flush=True)
                for a in analogies[:3]:
                    print(f"    {a.source_domain} -> {a.target_domain}: {a.source_mechanism[:60]}")
        except Exception as e:
            print(f"  [WARN] Cross-domain transfer skipped: {e}")

    if mode == "quick":
        return _finalize_report(report, papers, graph, gaps, [], [], [], [], [], [], t_start)

    # ══════════════════════════════════════════════════════════════
    # PHASE 3.5: LITERATURE REFINEMENT — Multi-round search
    # ══════════════════════════════════════════════════════════════
    # Adaptive literature search: analyze what was found, generate
    # targeted queries for gaps, fetch again. Multi-round approach.
    if gaps and len(papers) < 50:
        print("\n[Phase 3.5/12] LITERATURE REFINEMENT — Targeted search based on gaps...", flush=True)
        try:
            # Generate targeted queries from gaps
            gap_queries = set()
            for g in gaps[:6]:
                if isinstance(g, dict):
                    reason = g.get("reason", g.get("description", ""))
                    gtype = g.get("type", "")
                    # Extract key terms from gap descriptions
                    words = [w for w in reason.split() if len(w) > 4 and w.lower() not in
                             ("these", "their", "there", "which", "about", "would", "could",
                              "should", "between", "through", "having", "being", "other")]
                    if len(words) >= 2:
                        gap_queries.add(" ".join(words[:4]))

            # Also generate queries from graph entities that have few connections
            if hasattr(graph, 'entities') and graph.entities:
                entity_degrees = {}
                for r in graph.relationships:
                    if isinstance(r, dict):
                        src = r.get("source", "")
                        tgt = r.get("target", "")
                    else:
                        src, tgt = r[0], r[1]
                    entity_degrees[src] = entity_degrees.get(src, 0) + 1
                    entity_degrees[tgt] = entity_degrees.get(tgt, 0) + 1
                # Find under-connected entities
                low_degree = sorted(entity_degrees.items(), key=lambda x: x[1])[:5]
                for eid, deg in low_degree:
                    ename = graph.entities.get(eid, {}).get("name", eid)
                    if ename and len(ename) > 3:
                        gap_queries.add(f"{topic} {ename}")

            if gap_queries:
                existing_titles = {p["title"].lower()[:60] for p in papers}
                new_papers = []
                for query in list(gap_queries)[:3]:
                    try:
                        round_papers = fetch_papers(query, max_arxiv=8, max_pubmed=8, max_s2=8)
                        for p in round_papers:
                            if p["title"].lower()[:60] not in existing_titles:
                                existing_titles.add(p["title"].lower()[:60])
                                new_papers.append(p)
                    except Exception:
                        continue

                if new_papers:
                    papers.extend(new_papers)
                    # Rebuild graph with new papers
                    try:
                        for p in new_papers:
                            graph.add_entity(p.get("title", "")[:80], entity_type="paper")
                    except Exception:
                        pass
                    print(f"  Gap-targeted search: +{len(new_papers)} new papers (total: {len(papers)})")
                else:
                    print("  Gap-targeted search: no new papers found")
            else:
                print("  No gap queries generated — skipping refinement")

        except Exception as e:
            print(f"  [WARN] Literature refinement failed: {e}")

    # ══════════════════════════════════════════════════════════════
    # PHASE 4: ANOMALY DETECTION
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 4/12] ANOMALY DETECTION — Finding what doesn't fit...", flush=True)
    try:
        # Use algorithmic anomaly detection (fast, reliable)
        anomaly_detector = AnomalyDetector(graph=graph, llm_call=None)
        anomaly_results = anomaly_detector.detect_anomalies(topic, domain)
        anomalies = anomaly_results.get("top_anomalies", [])
        print(f"  Found {len(anomalies)} anomalies")
        for a in anomalies[:3]:
            print(f"    [{a.get('type', '?')}] {a.get('reason', '')[:80]}")
        report["phases"]["anomaly_detection"] = anomaly_results.get("summary", {})
        report["phases"]["anomaly_detection"]["top_anomalies"] = anomalies
    except Exception as e:
        print(f"  [ERROR] Anomaly detection failed: {e}")
        report["errors"].append(f"Phase 4: {e}")
        anomalies = []

    # ══════════════════════════════════════════════════════════════
    # PHASE 5: MISSING VARIABLES
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 5/12] MISSING VARIABLES — Proposing hidden factors...", flush=True)

    # Phase-specific LLM routing — spread work across ALL providers
    # Each provider has internal fallback: Cerebras → Groq → Gemini
    PHASE_PROVIDERS = {
        # Groq (3 keys) — fast extraction, volume
        "literature": "groq",
        "knowledge_graph": "groq",
        "gap_detection": "groq",
        "anomaly_detection": "groq",
        "prediction_engine": "groq",
        "adversarial_test": "groq",
        "scoring": "groq",
        # Auto-routing (Cerebras→Groq→Gemini) — creative/reasoning phases
        # Lets the system pick the best available model for complex tasks
        "missing_variables": "auto",
        "mechanism_generation": "auto",
        "theory_competition": "auto",
        "critical_evaluation": "auto",
        "skeptic_review": "auto",
        # Gemini — available as fallback in auto routing
    }
    _current_phase = {"name": "missing_variables"}  # mutable for closure

    # Direct LLM wrapper — multi-layer fallback using ALL providers
    # Layer 1: Phase-specific provider (with its own internal fallback chain)
    # Layer 2: Auto (Cerebras→Groq→Gemini with cooldown-aware retry)
    # Layer 3: Wait for cooldown, retry auto one more time
    def _truncated_llm(prompt, max_tokens=4096, **kwargs):
        """LLM call with prompt truncation + phase-aware routing + multi-layer fallback."""
        if len(prompt) > 10000:
            prompt = prompt[:9500] + "\n\n[Context truncated — respond with available information]"
        phase = kwargs.get("phase", _current_phase["name"])
        provider = PHASE_PROVIDERS.get(phase, "auto")

        def _is_empty_json(r):
            """Check if response is empty or an empty JSON object/array."""
            if not r:
                return True
            stripped = r.strip()
            if stripped in ('{}', '[]', '{"theories": []}', '{"hidden_variables": []}',
                            '{"mechanisms": []}', '{"predictions": []}'):
                return True
            return False

        try:
            # Layer 1: Try phase-specific provider with json_mode=True
            r = llm_call(prompt, json_mode=True, max_tokens=max_tokens, provider=provider)
            if r and not _is_empty_json(r):
                return r
            # If json_mode returned empty, retry without json_mode (some providers return empty JSON)
            if _is_empty_json(r):
                r = llm_call(prompt, json_mode=False, max_tokens=max_tokens, provider=provider)
                if r:
                    return r

            # Layer 2: Phase provider exhausted — try auto
            if provider != "auto":
                print(f"    [DEBUG] {provider} exhausted, trying auto...", flush=True)
                r = llm_call(prompt, json_mode=True, max_tokens=max_tokens, provider="auto")
                if r and not _is_empty_json(r):
                    return r
                if _is_empty_json(r):
                    r = llm_call(prompt, json_mode=False, max_tokens=max_tokens, provider="auto")
                    if r:
                        return r

            # Layer 3: All providers in cooldown — wait for soonest, retry
            import discovery.llm_client as _lc
            soonest = min(
                getattr(_lc, '_cerebras_cooldown_until', 0),
                getattr(_lc, '_groq_cooldown_until', 0),
                getattr(_lc, '_gemini_cooldown_until', 0),
            )
            wait = max(0, min(20, soonest - time.time()))
            if wait > 0:
                print(f"    [DEBUG] All providers cooling down, waiting {wait:.0f}s...", flush=True)
                time.sleep(wait + 1)
            r = llm_call(prompt, json_mode=True, max_tokens=max_tokens, provider="auto")
            if r and not _is_empty_json(r):
                return r
            if _is_empty_json(r):
                r = llm_call(prompt, json_mode=False, max_tokens=max_tokens, provider="auto")
                if r:
                    return r

            print(f"    [DEBUG] LLM exhausted (all providers)", flush=True)
            return None
        except Exception as e:
            print(f"    [ERROR] LLM exception: {e}", flush=True)
            return None

    try:
        # ── "What If" Counterfactual Engine ──
        # Generate genuinely novel hypotheses by asking "what if established theory is wrong?"
        # Run whenever we have ANY context (anomalies, gaps, or papers)
        counterfactual_hypotheses = []
        if _truncated_llm and (anomalies or gaps or papers):
            try:
                # Build context from whatever is available
                context_lines = []
                if anomalies:
                    context_lines.append("OBSERVED ANOMALIES:")
                    for a in anomalies[:5]:
                        context_lines.append(f"- [{a.get('type','?')}] {a.get('reason',a.get('description',''))[:120]}")
                if gaps:
                    context_lines.append("\nKNOWLEDGE GAPS:")
                    for g in gaps[:5]:
                        context_lines.append(f"- [{g.get('type','?')}] {g.get('reason',g.get('description',''))[:120]}")
                context_text = "\n".join(context_lines) if context_lines else f"Topic: {topic} (no specific anomalies or gaps detected yet)"

                # Get cross-domain analogies for inspiration
                analogy_text = ""
                try:
                    from discovery.cross_domain_transfer import CrossDomainTransfer
                    cdt = CrossDomainTransfer()
                    analogies = cdt.find_all_source_analogies(domain)
                    if analogies:
                        analogy_lines = []
                        for a in analogies[:3]:
                            analogy_lines.append(f"- {a.source_domain} -> {a.target_domain}: {a.source_mechanism[:100]}")
                            if a.prediction:
                                analogy_lines.append(f"  Prediction: {a.prediction[:80]}")
                        analogy_text = "\nCROSS-DOMAIN INSPIRATION:\n" + "\n".join(analogy_lines)
                        analogy_text += "\nUse these analogies to inspire hypotheses that transfer insights from other fields."
                except Exception:
                    pass

                cf_prompt = f"""You are a contrarian scientist. Your job is to CONSTRUCT new explanatory variables, not retrieve existing theories.

TOPIC: {topic}
DOMAIN: {domain}

{context_text}
{analogy_text}

CRITICAL RULES:
- DO NOT propose well-known speculative frameworks (dark photons, sterile neutrinos, dark energy coupling, etc.)
- DO NOT combine popular ideas into a soup (dark matter + dark energy + dark photon = NOT novel)
- DO CONSTRUCT new measurable parameters that don't exist in any paper
- DO CONNECT two separate observations with a hidden variable that resolves both

APPROACH:
1. What MEASURABLE PARAMETER would distinguish between competing explanations?
2. What QUANTITY is currently unconstrained that, if measured, would resolve the anomaly?
3. What HIDDEN VARIABLE connects two SEPARATE observations that nobody has linked before?

BAD (exotic physics soup):
"Dark photon mediated sterile neutrino decay with dark energy coupling" — just combining popular ideas

GOOD (constructed variable):
"Gravitational-wave memory coupling field (GWMCF)" — a new parameter quantifying GW memory interaction
"Conformational expansion factor (CEF)" — a new measurable quantity for protein changes

Generate 2-3 hypotheses that CONSTRUCT new explanatory variables.
Each must include: name, description, testable prediction, and WHY it hasn't been proposed before.

Output JSON:
{{"hypotheses": [{{"name": "novel hypothesis name", "description": "detailed explanation", "type": "counterfactual", "novelty": "high", "confidence": 0.3, "testable_prediction": "specific prediction", "why_novel": "why this hasn't been proposed before"}}]}}"""

                cf_raw = _truncated_llm(cf_prompt, max_tokens=4096)
                if cf_raw:
                    from discovery.json_extract import extract_json
                    cf_result = extract_json(cf_raw)
                    if cf_result:
                        cf_hyps = cf_result.get("hypotheses", [])
                        for h in cf_hyps:
                            h.setdefault("name", "")
                            h.setdefault("description", "")
                            h.setdefault("type", "counterfactual")
                            h.setdefault("novelty", "high")
                            if h.get("name") and h.get("description"):
                                counterfactual_hypotheses.append(h)
                        print(f"  [What-If Engine] {len(counterfactual_hypotheses)} counterfactual hypotheses generated", flush=True)
            except Exception as e:
                print(f"  [WARN] What-If engine skipped: {e}", flush=True)

        # CONTRADICTION-DRIVEN HYPOTHESIS GENERATION
        # Find contradictions in the graph and generate hypotheses that EXPLAIN them
        if _truncated_llm and graph.relationships:
            try:
                from discovery.contradiction_miner import ContradictionMiner
                miner = ContradictionMiner(graph)
                early_contradictions = miner.mine(papers=papers, llm_call=_truncated_llm)
                contra_list = early_contradictions.get("contradictions", [])
                if contra_list:
                    print(f"  [Contradiction Engine] {len(contra_list)} contradictions found early", flush=True)
                    # Generate hypotheses that EXPLAIN these contradictions
                    contra_text = "\n".join(
                        f"- [{c.get('type','?')}] {c.get('summary', c.get('description', ''))[:120]}"
                        for c in contra_list[:5]
                    )
                    contra_prompt = f"""You are a scientist resolving contradictions. For each contradiction, propose a hidden variable or mechanism that would EXPLAIN why both sides are partially correct.

TOPIC: {topic}
DOMAIN: {domain}

CONTRADICTIONS:
{contra_text}

For each contradiction, propose a hypothesis that:
1. Explains WHY both sides can be true under different conditions
2. Identifies the HIDDEN VARIABLE that determines which side applies
3. Makes a TESTABLE prediction about when each side applies

BAD: "One paper is wrong" (not a resolution)
GOOD: "Both papers are correct — the effect depends on condition X that differs between studies"

Output JSON:
{{"hypotheses": [{{"name": "...", "description": "...", "type": "contradiction_explanation", "resolves": "which contradiction", "hidden_variable": "what determines the outcome", "testable_prediction": "..."}}]}}"""

                    contra_raw = _truncated_llm(contra_prompt, max_tokens=4096)
                    if contra_raw:
                        from discovery.json_extract import extract_json
                        contra_result = extract_json(contra_raw)
                        if contra_result:
                            contra_hyps = contra_result.get("hypotheses", [])
                            added = 0
                            for h in contra_hyps:
                                h.setdefault("name", "")
                                h.setdefault("description", "")
                                h.setdefault("type", "contradiction_explanation")
                                h.setdefault("source", "contradiction_driven")
                                if h.get("name") and h.get("description"):
                                    counterfactual_hypotheses.append(h)
                                    added += 1
                            if added:
                                print(f"  [Contradiction Engine] {added} hypotheses from contradictions", flush=True)
            except Exception as e:
                print(f"  [WARN] Contradiction-driven hypotheses skipped: {e}", flush=True)

        # PRIMARY: MissingVariableGenerator — detailed hypotheses with derivations
        hidden_variables = []
        try:
            mv_generator = MissingVariableGenerator(graph=graph, llm_call=_truncated_llm)
            mv_results = mv_generator.generate(gaps, anomalies, topic, domain, papers, archive_context)
            hidden_variables = mv_results.get("hidden_variables", [])
        except Exception as e:
            print(f"  [MissingVariableGenerator] Failed: {e}", flush=True)

        # Merge counterfactual hypotheses with generated ones
        if counterfactual_hypotheses:
            for cfh in counterfactual_hypotheses:
                cfh.setdefault("source", "counterfactual_engine")
                hidden_variables.append(cfh)
            print(f"  [Merged] {len(hidden_variables)} total hidden variables ({len(counterfactual_hypotheses)} from What-If)", flush=True)

        # FALLBACK: HypothesisEngine — generate -> reflect -> refine
        if not hidden_variables:
            try:
                import asyncio
                from discovery.hypothesis_engine import HypothesisEngine
                he = HypothesisEngine(llm_call=_truncated_llm)
                primary_hyps = asyncio.run(he.generate(graph, topic, domain, run_id))
                if primary_hyps:
                    hidden_variables = primary_hyps if isinstance(primary_hyps, list) else []
                    print(f"  [HypothesisEngine] {len(hidden_variables)} hypotheses (generate->reflect->refine)", flush=True)
            except Exception as e:
                print(f"  [HypothesisEngine] Failed: {e}", flush=True)

        # LAST RESORT: Algorithmic
        if not hidden_variables:
            from discovery.algorithmic_discovery import generate_hypotheses_algorithmic
            hidden_variables = generate_hypotheses_algorithmic(graph, gaps, anomalies, topic, domain)
            if hidden_variables:
                print(f"  Algorithmic fallback: {len(hidden_variables)} hypotheses")

        # Validate hidden variables — reject those with unjustified parameters
        validated_hvs = []
        for hv in hidden_variables:
            name = hv.get("name", "")
            desc = hv.get("description", "")
            # Skip generic "Hidden mechanism connecting X" without explanation
            if "Hidden mechanism connecting" in name and len(desc) < 100:
                continue
            # Require key_parameters to have origin/measurement
            params = hv.get("key_parameters", [])
            for p in params:
                if isinstance(p, dict) and not p.get("origin") and not p.get("units"):
                    p["status"] = "unjustified"
                    p["penalty"] = -0.1
            validated_hvs.append(hv)
        hidden_variables = validated_hvs

        # Novelty check — reject hidden variables that are known science
        if hidden_variables and papers:
            try:
                from discovery.novelty_checker import NoveltyChecker
                nc = NoveltyChecker(llm_call=_truncated_llm)
                novel_hvs = []
                for hv in hidden_variables:
                    hv_name = hv.get("name", hv.get("title", ""))
                    if not hv_name:
                        continue
                    novelty_result = nc.check_novelty(hv, papers or [], topic, domain)
                    novelty_score = novelty_result.get("novelty_score", 0.5)
                    novelty_verdict = novelty_result.get("novelty_verdict", "unknown")
                    is_known = novelty_verdict in ("well_known", "rediscovery")
                    if is_known and novelty_score < 0.3:
                        print(f"    [Novelty Filter] Rejected known science: {hv_name[:50]} (verdict={novelty_verdict})", flush=True)
                        continue
                    hv["novelty_score"] = novelty_score
                    hv["novelty_verdict"] = novelty_verdict
                    hv["is_novel_vs_known"] = novelty_verdict
                    hv["novelty_checked"] = True
                    novel_hvs.append(hv)
                if len(novel_hvs) < len(hidden_variables):
                    print(f"  [Novelty Filter] {len(hidden_variables)} -> {len(novel_hvs)} (removed {len(hidden_variables) - len(novel_hvs)} known science)", flush=True)
                hidden_variables = novel_hvs
            except Exception as e:
                print(f"  [WARN] Novelty filter skipped: {e}", flush=True)

        print(f"  Proposed {len(hidden_variables)} hidden variables")
        for hv in hidden_variables[:3]:
            print(f"    [{hv.get('type', '?')}] {hv.get('name', '?')}")
            print(f"      {hv.get('description', '')[:100]}")
        report["phases"]["missing_variables"] = {
            "proposed": len(hidden_variables),
            "variables": [hv.get("name", "?") for hv in hidden_variables],
            "variable_details": hidden_variables,
        }
    except Exception as e:
        print(f"  [ERROR] Missing variable generation failed: {e}")
        report["errors"].append(f"Phase 5: {e}")
        hidden_variables = []

    if mode in ("quick", "standard"):
        return _finalize_report(report, papers, graph, gaps, anomalies,
                                hidden_variables, [], [], [], [], t_start)

    # ══════════════════════════════════════════════════════════════
    # PHASE 6: MECHANISM GENERATION
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 6/12] MECHANISM GENERATION — Building causal pathways...", flush=True)
    _current_phase["name"] = "mechanism_generation"
    try:
        # PRIMARY: MechanismGenerator — detailed causal chains with derivations
        mechanisms = []
        try:
            mech_generator = MechanismGenerator(graph=graph, llm_call=_truncated_llm)
            mech_results = mech_generator.generate_mechanisms(
                hidden_variables, gaps, anomalies, topic, domain, papers, archive_context
            )
            mechanisms = mech_results.get("mechanisms", [])
        except Exception as e:
            print(f"  [MechanismGenerator] Failed: {e}", flush=True)

        # FALLBACK: MechanismDiscoveryEngine — graph-mined correlations
        if not mechanisms:
            try:
                from discovery.mechanism_discovery import MechanismDiscoveryEngine
                mde = MechanismDiscoveryEngine(graph=graph, llm_call=_truncated_llm)
                mde_results = mde.discover_from_graph(topic, domain)
                if mde_results and mde_results.get("mechanisms"):
                    raw_mechanisms = mde_results["mechanisms"]
                    # Normalize MechanismDiscovery format: flatten candidates and remap fields
                    mechanisms = []
                    for group in raw_mechanisms:
                        # Skip schema-like objects
                        if group.get("type") == "object" and not group.get("description") and not group.get("candidates"):
                            continue
                        candidates = group.get("candidates", [])
                        if not candidates:
                            # Single mechanism (no candidates wrapper) — only add if it has substance
                            if group.get("name") or group.get("description") or group.get("steps"):
                                mechanisms.append(group)
                        else:
                            for c in candidates:
                                # Remap fields to standard format
                                if "causal_chain" in c and "steps" not in c:
                                    c["steps"] = c["causal_chain"]
                                if "correlation" not in c and group.get("correlation"):
                                    c["correlation"] = group["correlation"]
                                # Extract name from multiple possible fields
                                if "name" not in c or not c.get("name") or c.get("name") in ("object", ""):
                                    c["name"] = (
                                        c.get("mechanism_name") or
                                        c.get("correlation") or
                                        c.get("description", "")[:60] or
                                        c.get("type", "causal_pathway")
                                    )
                                # Skip if name is still generic
                                if c.get("name") in ("object", "causal_pathway", ""):
                                    continue
                                c.setdefault("type", "causal_pathway")
                                mechanisms.append(c)
                    print(f"  [MechanismDiscovery] {len(mechanisms)} mechanisms (normalized from {len(raw_mechanisms)} groups)", flush=True)
            except Exception as e:
                print(f"  [MechanismDiscovery] Failed: {e}", flush=True)

        # LAST RESORT: Algorithmic
        if not mechanisms:
            from discovery.algorithmic_discovery import generate_mechanisms_algorithmic
            mechanisms = generate_mechanisms_algorithmic(graph, hidden_variables, topic, domain)
            if mechanisms:
                print(f"  Algorithmic fallback: {len(mechanisms)} mechanisms")

        # -- Math Consistency Checker --
        if mechanisms:
            try:
                from discovery.math_consistency_checker import MathConsistencyChecker
                mcc = MathConsistencyChecker()
                for mech in mechanisms[:3]:
                    math_result = mcc.check_theory(mech, domain=domain)
                    if math_result and not math_result.get("consistent", True):
                        mech["math_warnings"] = math_result.get("issues", [])[:3]
                        print(f"  [Math Check] {mech.get('name', '?')[:30]}: issues found", flush=True)
            except Exception as e:
                print(f"  [WARN] Math consistency check skipped: {e}")

        # Validate mechanisms — allow descriptions without explicit steps
        validated_mechanisms = []
        for m in mechanisms:
            name = m.get("name", "")
            steps = m.get("steps", m.get("causal_chain", []))  # handle both formats
            description = m.get("description", m.get("mechanism", m.get("correlation", "")))
            # Ensure steps field exists for downstream consumers
            if "steps" not in m and "causal_chain" in m:
                m["steps"] = m["causal_chain"]
            # Fix unnamed mechanisms — extract name from description
            if not name or name in ("Unnamed mechanism", "Unnamed Mechanism", ""):
                if description:
                    m["name"] = description[:60]
                    name = m["name"]
                elif steps:
                    m["name"] = f"Mechanism: {steps[0][:40]}"
                    name = m["name"]
            # Reject truly empty mechanisms — no name, no description, no steps
            if not name and not description and len(steps) < 1:
                continue
            # Reject generic "Hidden mechanism connecting X" with no description
            if "Hidden mechanism connecting" in name and not description and len(steps) < 1:
                continue
            # Reject non-scientific mechanisms
            desc_lower = (description + " " + name).lower()
            non_scientific = [
                "funding", "organizational", "market", "economic", "political",
                "social", "management", "administrative", "bureaucratic",
                "funding-driven", "market-driven", "resource allocation",
            ]
            if any(term in desc_lower for term in non_scientific):
                continue
            # Tag single-step as direct_observation
            if len(steps) == 1:
                m.setdefault("type", "direct_observation")
            # Tag mechanisms with description but no steps as proposed
            if len(steps) < 1 and description:
                m.setdefault("type", "proposed")
            # Mark as speculative if missing key fields — no confidence cap
            if not m.get("inputs") and not m.get("outputs"):
                m["status"] = "speculative"
                # Don't cap confidence — let scorer decide
            validated_mechanisms.append(m)
        mechanisms = validated_mechanisms

        print(f"  Generated {len(mechanisms)} mechanisms")
        for m in mechanisms[:3]:
            print(f"    [{m.get('type', '?')}] {m.get('name', '?')}")
            for s in m.get("steps", [])[:2]:
                s_str = str(s)[:80] if s else ""
                print(f"      → {s_str}")
        report["phases"]["mechanism_generation"] = {
            "mechanisms_generated": len(mechanisms),
            "types": list(set(m.get("type", "?") for m in mechanisms)),
            "mechanism_details": mechanisms,
        }
    except Exception as e:
        print(f"  [ERROR] Mechanism generation failed: {e}")
        report["errors"].append(f"Phase 6: {e}")
        mechanisms = []

    # ══════════════════════════════════════════════════════════════
    # PHASE 7: PREDICTION ENGINE
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 7/12] PREDICTION ENGINE — Generating testable predictions...", flush=True)
    _current_phase["name"] = "prediction_engine"
    try:
        # Defensive: convert all mechanism/HV values to strings to prevent float+str errors
        safe_mechanisms = []
        for m in (mechanisms or []):
            if isinstance(m, dict):
                sm = {k: str(v) if not isinstance(v, (list, dict)) else v for k, v in m.items()}
                safe_mechanisms.append(sm)
            else:
                safe_mechanisms.append(m)
        safe_hvs = []
        for h in (hidden_variables or []):
            if isinstance(h, dict):
                sh = {k: str(v) if not isinstance(v, (list, dict)) else v for k, v in h.items()}
                safe_hvs.append(sh)
            else:
                safe_hvs.append(h)

        pred_engine = PredictionEngine(graph=graph, llm_call=_truncated_llm)
        pred_results = pred_engine.generate_predictions(
            safe_mechanisms, safe_hvs, topic, domain, anomalies
        )
        predictions = pred_results.get("predictions", [])

        # Algorithmic fallback
        if not predictions:
            from discovery.algorithmic_discovery import generate_predictions_algorithmic
            predictions = generate_predictions_algorithmic(mechanisms, hidden_variables, topic, domain, graph)
            if predictions:
                print(f"  Algorithmic fallback: {len(predictions)} predictions")

        # Validate predictions
        validation = pred_engine.validate_predictions(predictions)

        # -- Counterfactual Reasoning — store results in report --
        if mechanisms:
            try:
                from discovery.counterfactual_reasoner import CounterfactualReasoner
                cfr = CounterfactualReasoner(llm_call=_truncated_llm)
                # Build a proper theory dict for the reasoner
                top_theory = winner or (theories[0] if theories else {})
                cf_theory = {
                    "name": top_theory.get("title", top_theory.get("name", "")),
                    "description": top_theory.get("description", top_theory.get("mechanism", "")),
                    "mathematical_model": top_theory.get("mathematical_model", ""),
                    "key_parameters": top_theory.get("key_parameters", []),
                    "predictions": predictions,
                    "mechanisms": mechanisms,
                    "steps": top_theory.get("steps", []),
                }
                cf_result = cfr.reason(cf_theory, domain=domain)
                if cf_result and cf_result.get("counterfactuals"):
                    print(f"  [Counterfactual] {len(cf_result['counterfactuals'])} consequences derived", flush=True)
                    report["phases"]["counterfactual_reasoning"] = {
                        "total_derived": cf_result.get("total_derived", 0),
                        "supported": len(cf_result.get("supported", [])),
                        "contradicted": len(cf_result.get("contradicted", [])),
                        "consistency": cf_result.get("overall_consistency", 0),
                        "details": cf_result,
                    }
            except Exception as e:
                print(f"  [WARN] Counterfactual reasoning skipped: {e}")
        accepted_preds = validation.get("accepted", predictions)

        # -- Prediction Literature Validator — check predictions against real papers --
        if accepted_preds:
            try:
                from discovery.prediction_literature_validator import PredictionLiteratureValidator
                plv = PredictionLiteratureValidator(llm_call=_truncated_llm)
                lit_validation = plv.validate_predictions(
                    accepted_preds, mechanisms, topic, domain, existing_papers=papers
                )
                if lit_validation:
                    validated = lit_validation.get("validations", [])
                    supported = sum(1 for v in validated if v.get("validation_status") == "supported")
                    contradicted = sum(1 for v in validated if v.get("validation_status") == "contradicted")
                    print(f"  [Lit Validation] {supported} supported, {contradicted} contradicted by literature", flush=True)
                    if "prediction_engine" not in report["phases"]:
                        report["phases"]["prediction_engine"] = {}
                    report["phases"]["prediction_engine"]["literature_validation"] = {
                        "total_validated": len(validated),
                        "supported": supported,
                        "contradicted": contradicted,
                    }
            except Exception as e:
                print(f"  [WARN] Prediction literature validation skipped: {e}", flush=True)

        print(f"  Generated {len(predictions)} predictions ({len(accepted_preds)} accepted)")
        for p in accepted_preds[:3]:
            print(f"    [{p.get('type', '?')}] {p.get('statement', '')[:80]}")
        report["phases"]["prediction_engine"] = {
            "total_predictions": len(predictions),
            "accepted": len(accepted_preds),
            "acceptance_rate": validation.get("acceptance_rate", 0),
            "accepted_details": accepted_preds,
            "predictions": predictions,
            "all_predictions": predictions,
        }
    except Exception as e:
        print(f"  [ERROR] Prediction generation failed: {e}")
        report["errors"].append(f"Phase 7: {e}")
        predictions = []
        accepted_preds = []

    # ══════════════════════════════════════════════════════════════
    # PHASE 8: THEORY COMPETITION
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 8/12] THEORY COMPETITION — Comparing explanations...", flush=True)
    _current_phase["name"] = "theory_competition"
    try:
        # PRIMARY: TheoryCompetition — full tournament with scoring/elimination
        theories = []
        winner = None
        comp_results = {}  # Initialize — only assigned if TheoryCompetition runs
        try:
            competition = TheoryCompetition(graph=graph, llm_call=_truncated_llm)
            comp_results = competition.compete(
                mechanisms, hidden_variables, anomalies, gaps, topic, domain, papers,
                archive_context=archive_context
            )
            theories = comp_results.get("theories", [])
            winner = comp_results.get("winner")
        except Exception as e:
            print(f"  [TheoryCompetition] Failed: {e}", flush=True)

        # FALLBACK: HypothesisTournament — evolutionary tournament
        if not theories:
            try:
                import asyncio
                from discovery.hypothesis_tournament import HypothesisTournament
                ht = HypothesisTournament(llm_call=_truncated_llm)
                tournament_hyps = asyncio.run(ht.run(hidden_variables[:6], graph, topic, domain))
                if tournament_hyps:
                    theories = tournament_hyps if isinstance(tournament_hyps, list) else []
                    winner = theories[0] if theories else None
                    print(f"  [HypothesisTournament] {len(theories)} theories (evolutionary)", flush=True)
            except Exception as e:
                print(f"  [HypothesisTournament] Failed: {e}", flush=True)

        # LAST RESORT: Algorithmic (NOT a real tournament — flag it)
        if not theories:
            from discovery.algorithmic_discovery import compare_theories_algorithmic
            theories = compare_theories_algorithmic(hidden_variables, graph, papers)
            winner = theories[0] if theories else None
            if theories:
                print(f"  [WARN] TOURNAMENT FAILED — using algorithmic graph analysis instead", flush=True)
                print(f"  [WARN] These theories did NOT go through generation/scoring/elimination", flush=True)
                for t in theories:
                    t["tournament_status"] = "algorithmic_fallback"
                    t["tournament_reliable"] = False

        # -- Multi-Agent Debate — store results in report --
        top_theory = winner or (theories[0] if theories else {})
        if top_theory:
            try:
                from discovery.multi_agent_debate import MultiAgentDebate
                mad = MultiAgentDebate()
                theory_desc = top_theory.get("description", top_theory.get("mechanism", top_theory.get("name", "")))
                if theory_desc:
                    debate_result = mad.run_debate(theory_desc, topic=topic)
                    if debate_result:
                        verdict = getattr(debate_result, "final_verdict", "unknown")
                        confidence = getattr(debate_result, "confidence", 0)
                        print(f"  [Multi-Agent Debate] Verdict: {verdict} (confidence: {confidence:.0%})", flush=True)
                        report["phases"]["multi_agent_debate"] = {
                            "verdict": verdict,
                            "confidence": confidence,
                            "details": str(debate_result)[:500],
                        }
            except Exception as e:
                print(f"  [WARN] Multi-agent debate skipped: {e}")

        # Normalize theory format — HypothesisTournament outputs different fields than scorer expects
        for t in theories:
            if "name" not in t and "title" in t:
                t["name"] = t["title"]
            if "description" not in t and "mechanistic_rationale" in t:
                t["description"] = t["mechanistic_rationale"]
            if "type" not in t and "pattern_type" in t:
                t["type"] = t["pattern_type"]
            if "predictions" not in t:
                t["predictions"] = []
            if "steps" not in t and "edges" in t:
                t["steps"] = [f"{e.get('source','')} --{e.get('relation','')}--> {e.get('target','')}" for e in t.get("edges", [])]
            if "hidden_variables" not in t and "nodes" in t:
                t["hidden_variables"] = t["nodes"]
            if "explains" not in t and "supporting_evidence" in t:
                t["explains"] = t["supporting_evidence"]
            if "fails_to_explain" not in t and "contradictory_evidence" in t:
                t["fails_to_explain"] = t["contradictory_evidence"]
            if "key_assumptions" not in t:
                t["key_assumptions"] = []

        # Validate theories — require causal chains, not just correlations
        validated_theories = []
        for t in theories:
            name = t.get("name", "")
            desc = t.get("description", t.get("mechanism", ""))
            # Track causal status for reporting — don't penalize
            # Correlations are valid starting points (Darwin didn't know DNA)
            if "correlat" in desc.lower() and "caus" not in desc.lower():
                t["causal_status"] = "correlation_only"
                t["causal_penalty"] = 0  # no penalty — correlations are valid
            has_causal = any(kw in desc.lower() for kw in ["causes", "leads to", "produces", "generates", "triggers", "mediates", "drives"])
            if not has_causal:
                t["causal_status"] = "no_causal_claim"
                t["causal_penalty"] = 0  # no penalty — track for reporting only
            validated_theories.append(t)
        theories = validated_theories

        print(f"  {len(theories)} competing theories (tournament)")
        if winner:
            w_score = winner.get("scores", {}).get("overall", 0)
            print(f"  Winner: {winner.get('name', '?')} (score: {w_score:.2f})")
        eliminated = comp_results.get("eliminated", [])
        if eliminated:
            print(f"  Eliminated: {len(eliminated)} theories killed in tournament")

        # Determine tournament source
        tournament_source = "hypothesis_tournament" if not comp_results else "theory_competition"

        # Novelty check on surviving theories
        if theories and papers:
            try:
                from discovery.novelty_checker import NoveltyChecker
                nc_theory = NoveltyChecker(llm_call=_truncated_llm)
                for t in theories[:5]:
                    t_name = t.get("name", "")
                    if not t_name:
                        continue
                    t_novelty = nc_theory.check_novelty(t, papers or [], topic, domain)
                    t_score = t_novelty.get("novelty_score", 0.5)
                    t_verdict = t_novelty.get("novelty_verdict", "unknown")
                    t["is_novel_vs_known"] = t_verdict
                    t["novelty_score"] = t_score
                    if t_verdict in ("well_known", "rediscovery"):
                        print(f"  [Novelty] {t_name[:40]}: {t_verdict} (score={t_score:.2f}) — KNOWN SCIENCE", flush=True)
                    else:
                        print(f"  [Novelty] {t_name[:40]}: {t_verdict} (score={t_score:.2f})", flush=True)
            except Exception as e:
                print(f"  [WARN] Theory novelty check skipped: {e}", flush=True)

        # -- Winner Override: if winner is well_known/rediscovery, pick best novel theory --
        if winner and winner.get("is_novel_vs_known") in ("well_known", "rediscovery"):
            novel_theories = [t for t in theories
                              if t.get("is_novel_vs_known") not in ("well_known", "rediscovery", "")]
            if novel_theories:
                best_novel = max(novel_theories, key=lambda t: t.get("scores", {}).get("overall", 0))
                print(f"  [Winner Override] '{winner.get('name', '?')[:40]}' is {winner.get('is_novel_vs_known')}", flush=True)
                print(f"  [Winner Override] Picking novel: '{best_novel.get('name', '?')[:40]}' (score={best_novel.get('scores', {}).get('overall', 0):.2f})", flush=True)
                winner = best_novel

        # -- GFlowNet-Inspired Diversity Selection --
        # Re-rank theories by composite score: quality + novelty + diversity
        # This rewards theories that are DIFFERENT from each other, not just high-scoring
        if len(theories) >= 3:
            try:
                import re
                # Compute diversity bonus for each theory
                for i, t in enumerate(theories):
                    t_desc = t.get("description", t.get("mechanism", ""))
                    t_name = t.get("name", "")
                    quality_score = t.get("scores", {}).get("overall", 0)

                    # Novelty bonus
                    novelty_verdict = t.get("is_novel_vs_known", "")
                    novelty_bonus = {"novel": 0.2, "refinement": 0.1, "": 0.05}.get(novelty_verdict, 0)

                    # Diversity bonus — reward theories with unique terms
                    # Compare against other theories' descriptions
                    unique_terms = 0
                    t_words = set(w.lower() for w in t_desc.split() if len(w) > 4)
                    for j, other in enumerate(theories):
                        if i == j:
                            continue
                        other_desc = other.get("description", "")
                        other_words = set(w.lower() for w in other_desc.split() if len(w) > 4)
                        overlap = len(t_words & other_words)
                        total = len(t_words | other_words)
                        if total > 0:
                            similarity = overlap / total
                            if similarity < 0.3:  # less similar = more diverse
                                unique_terms += 1

                    diversity_bonus = min(0.15, unique_terms * 0.03)

                    # Composite score (GFlowNet-style: quality × novelty × diversity)
                    composite = quality_score * (1 + novelty_bonus + diversity_bonus)
                    t["_gflownet_score"] = round(composite, 3)
                    t["_diversity_bonus"] = round(diversity_bonus, 3)
                    t["_novelty_bonus"] = round(novelty_bonus, 3)

                # Re-sort by composite score
                theories.sort(key=lambda t: t.get("_gflownet_score", 0), reverse=True)

                # Update winner if composite score suggests a different one
                if theories and winner:
                    best_composite = theories[0]
                    if best_composite.get("_gflownet_score", 0) > (winner.get("_gflownet_score", 0) or 0):
                        print(f"  [GFlowNet] Re-ranked: '{best_composite.get('name', '?')[:40]}' (composite={best_composite.get('_gflownet_score', 0):.3f})", flush=True)
                        print(f"  [GFlowNet] Diversity bonus: +{best_composite.get('_diversity_bonus', 0):.2f}, Novelty bonus: +{best_composite.get('_novelty_bonus', 0):.2f}", flush=True)
            except Exception as e:
                print(f"  [WARN] GFlowNet re-ranking skipped: {e}", flush=True)

        report["phases"]["theory_competition"] = {
            "theories_compared": comp_results.get("theories_compared", len(theories)),
            "theories": theories,
            "eliminated": eliminated,
            "winner": winner,
            "winner_name": winner.get("name") if winner else None,
            "winner_score": winner.get("scores", {}).get("overall", 0) if winner else 0,
            "tournament_log": comp_results.get("tournament_log", []),
            "competition_analysis": comp_results.get("competition_analysis", ""),
            "discriminating_experiments": comp_results.get("discriminating_experiments", []),
            "tournament_source": tournament_source,
        }
    except Exception as e:
        print(f"  [ERROR] Theory competition failed: {e}")
        report["errors"].append(f"Phase 8: {e}")
        theories = []
        winner = None

    # ══════════════════════════════════════════════════════════════
    # PHASE 8.25: MOLECULE GENERATION — Drug candidates (drug_discovery only)
    # ══════════════════════════════════════════════════════════════
    if domain in ("drug_discovery",) and (winner or theories):
        print("\n[Phase 8.25] MOLECULE GENERATION — Designing drug candidates...", flush=True)
        try:
            from discovery.molecule import generate_candidates, format_candidates
            top_theory = winner or (theories[0] if theories else {})
            # Extract target from theory — look for protein/gene/drug entities
            target = ""
            theory_desc = top_theory.get("description", top_theory.get("mechanism", ""))
            theory_name = top_theory.get("name", "")
            # Try to find a drug target from hidden variables or graph entities
            for hv in (hidden_variables or []):
                if isinstance(hv, dict) and hv.get("type") in ("protein", "gene", "drug"):
                    target = hv.get("name", "")
                    break
            if not target:
                # Use theory name as target
                target = theory_name or topic
            if target:
                print(f"  Target: {target}", flush=True)
                candidates = generate_candidates(target, graph=graph, num_candidates=6)
                if candidates:
                    print(f"  Generated {len(candidates)} drug candidates", flush=True)
                    for c in candidates[:3]:
                        print(f"    {c.get('name', '?')}: {c.get('molecular_formula', '?')} "
                              f"(QED={c.get('qed', 0):.2f}, score={c.get('score', 0):.2f})", flush=True)
                    report["phases"]["molecule_generation"] = {
                        "target": target,
                        "candidates_generated": len(candidates),
                        "top_candidates": [{
                            "name": c.get("name"),
                            "smiles": c.get("smiles"),
                            "formula": c.get("molecular_formula"),
                            "mw": c.get("mw"),
                            "qed": c.get("qed"),
                            "score": c.get("score"),
                            "lipinski_violations": c.get("lipinski_violations"),
                        } for c in candidates[:5]],
                    }
                else:
                    print("  No valid candidates generated (RDKit may not be installed)", flush=True)
        except (ImportError, AttributeError, Exception) as e:
            print(f"  [WARN] Molecule generation skipped: {e}", flush=True)

    # ══════════════════════════════════════════════════════════════
    # PHASE 8.3: ABSTRACTION COMPRESSION — Find simplest explanation
    # ══════════════════════════════════════════════════════════════
    # A theory is compression: 100 observations → 1 principle
    # Ask: what is the SIMPLEST explanation that accounts for everything?
    if theories and _truncated_llm and len(theories) >= 2:
        print("\n[Phase 8.3] ABSTRACTION COMPRESSION — Finding simplest unifying principle...", flush=True)
        try:
            theory_summaries = []
            for t in theories[:6]:
                name = t.get("name", "?")
                desc = t.get("description", "")[:100]
                theory_summaries.append(f"- {name}: {desc}")

            # Build observations text
            obs_lines = []
            for g in (gaps or [])[:5]:
                reason = g.get("reason", g.get("description", ""))[:100]
                if reason:
                    obs_lines.append(f"- {reason}")
            obs_text = chr(10).join(obs_lines) if obs_lines else "No specific observations available"

            compress_prompt = f"""You are a theoretical physicist seeking the SIMPLEST explanation.

TOPIC: {topic}
DOMAIN: {domain}

CURRENT THEORIES:
{chr(10).join(theory_summaries)}

OBSERVATIONS TO EXPLAIN:
{obs_text}

Your task: Find ONE unifying principle that explains ALL observations with MINIMUM assumptions.

A good unifying principle:
- Explains more with less (Occam's razor)
- Connects seemingly unrelated observations
- Makes NEW predictions that individual theories don't
- Has mathematical elegance (fewer free parameters)

BAD: "Multiple mechanisms coexist" — that's not compression, that's giving up
GOOD: "All observations follow from principle X because Y" — that's compression

Output JSON:
{{"unifying_principle": "one sentence description", "explanation": "how it explains all observations", "new_predictions": ["prediction 1", "prediction 2"], "simplicity_score": 0.0-1.0, "why_better": "why this is simpler than individual theories"}}"""

            compress_raw = _truncated_llm(compress_prompt, max_tokens=2048)
            if compress_raw:
                from discovery.json_extract import extract_json
                compress_result = extract_json(compress_raw)
                if compress_result and compress_result.get("unifying_principle"):
                    principle = compress_result["unifying_principle"]
                    explanation = compress_result.get("explanation", "")
                    new_preds = compress_result.get("new_predictions", [])
                    simplicity = compress_result.get("simplicity_score", 0)
                    print(f"  [Abstraction] Unifying principle: {principle[:80]}", flush=True)
                    print(f"  [Abstraction] Simplicity score: {simplicity}", flush=True)
                    if new_preds:
                        print(f"  [Abstraction] New predictions: {len(new_preds)}", flush=True)
                    report["phases"]["abstraction_compression"] = {
                        "unifying_principle": principle,
                        "explanation": explanation[:500],
                        "new_predictions": new_preds,
                        "simplicity_score": simplicity,
                    }
        except Exception as e:
            print(f"  [WARN] Abstraction compression skipped: {e}", flush=True)

    # ══════════════════════════════════════════════════════════════
    # PHASE 8.5: ADVERSARIAL TEST — Attack every discovery
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 8.5/12] ADVERSARIAL TEST — Attacking every discovery...", flush=True)
    _current_phase["name"] = "adversarial_test"
    try:
        from discovery.test_stage import AdversarialTest
        tester = AdversarialTest(llm_call=_truncated_llm)
        test_results = tester.test_discoveries(
            hidden_variables, mechanisms, theories, papers, topic, domain, gaps, anomalies
        )
        report["phases"]["adversarial_test"] = test_results

        # Print results
        summary = test_results.get("survival_summary", {})
        for category in ["hidden_variables", "mechanisms", "theories"]:
            s = summary.get(category, {})
            survived = s.get("survived", 0)
            weakened = s.get("weakened", 0)
            killed = s.get("killed", 0)
            total = s.get("started", 0)
            print(f"  {category}: {total} tested → {survived} survived, {weakened} weakened, {killed} killed")

        # Print individual verdicts
        for test_list_name in ["hidden_variable_tests", "mechanism_tests", "theory_tests"]:
            for t in test_results.get(test_list_name, [])[:3]:
                name = t.get("name", "?")
                verdict = t.get("verdict", "?")
                score = t.get("attack_score", 0)
                existing = t.get("existing_theory", "")
                falsification = t.get("falsification", "")
                icon = {"survived": "✓", "weakened": "⚠", "killed": "✗"}.get(verdict, "?")
                print(f"    {icon} {name[:40]} ({verdict}, score: {score:.2f})")
                if existing and existing != "None known":
                    print(f"      Existing theory: {str(existing)[:80]}")
                if falsification:
                    print(f"      Falsification: {str(falsification)[:80]}")

    except Exception as e:
        print(f"  [ERROR] Adversarial test failed: {e}")
        report["errors"].append(f"Phase 8.5: {e}")

    # ══════════════════════════════════════════════════════════════
    # PHASE 8.6: CRITICAL EVALUATION — Formal assessment
    # ══════════════════════════════════════════════════════════════
    # Evaluates the top discovery across 6 dimensions:
    # novelty, methodology, significance, clarity, limitations, reproducibility.
    print("\n[Phase 8.6/12] CRITICAL EVALUATION — Formal assessment...", flush=True)
    _current_phase["name"] = "critical_evaluation"
    try:
        from discovery.peer_review import CriticalEvaluator
        reviewer = CriticalEvaluator(llm_call=_truncated_llm)
        top_theory = winner or (theories[0] if theories else {})
        if top_theory:
            peer_review = reviewer.review(
                top_theory, mechanisms, accepted_preds, papers, topic, domain,
                adversarial_results=test_results if 'test_results' in dir() else None
            )
            report["phases"]["peer_review"] = peer_review
            print(f"  Overall score: {peer_review.get('overall_score', 0)}/10")
            print(f"  Recommendation: {peer_review.get('recommendation', 'unknown')}")
            major = peer_review.get("major_issues", [])
            if major:
                print(f"  Major issues: {len(major)}")
                for issue in major[:2]:
                    print(f"    ! {str(issue)[:80]}")
    except Exception as e:
        print(f"  [WARN] Critical evaluation failed: {e}")
        report["errors"].append(f"Phase 8.6: {e}")

    # ══════════════════════════════════════════════════════════════
    # PHASE 9: COMPUTATIONAL VERIFICATION
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 9/12] COMPUTATIONAL VERIFICATION — Running computations...", flush=True)
    try:
        verifier = ComputationalVerifier(graph=graph)
        top_theory = winner or (theories[0] if theories else {})
        verify_results = verifier.verify(top_theory, accepted_preds, mechanisms)
        comp_summary = verify_results.get("verification_summary", {})
        print(f"  Computations run: {verify_results.get('computations_run', 0)}")
        print(f"  Support level: {comp_summary.get('support_level', 'unknown')}")
        for finding in comp_summary.get("key_findings", [])[:3]:
            print(f"    → {finding[:80]}")
        report["phases"]["computational_verification"] = comp_summary
    except Exception as e:
        print(f"  [ERROR] Computational verification failed: {e}")
        report["errors"].append(f"Phase 9: {e}")
        verify_results = {"computations_run": 0}

    # -- Computation Engine — SymPy/NumPy verification of numerical claims --
    top_theory = winner or (theories[0] if theories else {})
    if mechanisms:
        try:
            from discovery.computation_engine import verify_mechanism_numbers
            ce_results = []
            for mech in mechanisms[:3]:
                ce_result = verify_mechanism_numbers(mech)
                if ce_result:
                    ce_results.append(ce_result)
            if ce_results:
                total_verified = sum(r.get("verified_count", 0) for r in ce_results)
                total_failed = sum(r.get("failed_count", 0) for r in ce_results)
                total_untraceable = sum(r.get("untraceable_count", 0) for r in ce_results)
                print(f"  [Computation Engine] {total_verified} verified, {total_failed} failed, {total_untraceable} untraceable", flush=True)
                report["phases"]["computational_verification"]["computation_engine"] = {
                    "verified": total_verified, "failed": total_failed, "untraceable": total_untraceable,
                    "mechanisms_checked": len(ce_results),
                }
        except Exception as e:
            print(f"  [WARN] Computation engine skipped: {e}", flush=True)

    # -- Domain Computations — run domain-specific calculations --
    all_calculations = {}
    try:
        from discovery.domain_computational import run_domain_calculations, format_for_prompt, DOMAIN_COMPUTATIONS
        domain_calcs = run_domain_calculations(domain, topic)
        if domain_calcs:
            all_calculations.update(domain_calcs)
            calc_context = format_for_prompt(domain_calcs)
            if calc_context:
                print(f"  [Domain Computations] {len(domain_calcs)} calculations for {domain}", flush=True)
                report["phases"]["computational_verification"]["domain_calculations"] = {
                    "count": len(domain_calcs),
                    "names": list(domain_calcs.keys())[:5],
                }
    except Exception as e:
        print(f"  [WARN] Domain computations skipped: {e}", flush=True)

    # -- Topic-specific calculations (e.g. phosphine/Venus) --
    try:
        from discovery.computational import run_all_calculations, format_calculations_for_prompt
        topic_calcs = run_all_calculations(topic)
        if topic_calcs:
            all_calculations.update(topic_calcs)
            print(f"  [Topic Computations] {len(topic_calcs)} calculations run", flush=True)
            report["phases"]["computational_verification"]["topic_calculations"] = {
                "count": len(topic_calcs),
                "names": list(topic_calcs.keys())[:5],
            }
    except Exception as e:
        print(f"  [WARN] Topic computations skipped: {e}", flush=True)

    # -- Math Engine — 6-category mathematical verification --
    top_theory = winner or (theories[0] if theories else {})
    if top_theory:
        try:
            from discovery.math_engine import run_math_verification
            math_result = run_math_verification(top_theory, mechanisms=mechanisms, predictions=accepted_preds, llm_call=_truncated_llm)
            if math_result:
                math_score = math_result.get("overall_score", 0)
                math_summary = math_result.get("summary", "")
                print(f"  [Math Engine] Score: {math_score}/100 — {math_summary}", flush=True)
                report["phases"]["math_verification"] = {
                    "overall_score": math_score,
                    "summary": math_summary,
                    "equation_solving": math_result.get("equation_solving", {}),
                    "dimensional_analysis": math_result.get("dimensional_analysis", {}),
                    "derivation_verification": math_result.get("derivation_verification", {}),
                    "kinetic_validation": math_result.get("kinetic_validation", {}),
                    "kinetic_reviewer_objections": math_result.get("kinetic_reviewer_objections", {}),
                }
                # Print kinetic issues if found
                kv = math_result.get("kinetic_validation", {})
                kv_issues = kv.get("issues", [])
                if kv_issues:
                    for issue in kv_issues:
                        sev = issue.get("severity", "warning").upper()
                        print(f"  [Math Engine] KINETIC {sev}: {issue.get('detail', '')[:120]}", flush=True)
                    reviewer = math_result.get("kinetic_reviewer_objections", {})
                    if reviewer.get("fatal_flaws"):
                        print(f"  [Math Engine] FATAL FLAWS: {len(reviewer['fatal_flaws'])} found", flush=True)
                # Store math score on theory for scorer to use
                top_theory["math_engine_score"] = math_score
        except Exception as e:
            print(f"  [WARN] Math engine skipped: {e}", flush=True)

    # -- Initialize ProvenanceTracker for claim tracking --
    provenance = None
    try:
        from discovery.claim_provenance import ProvenanceTracker
        provenance = ProvenanceTracker(papers=papers, calculations=all_calculations)
    except Exception:
        pass

    # ══════════════════════════════════════════════════════════════
    # PHASE 9.5: EXPERIMENTAL VALIDATION PLANNING
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 9.5/12] EXPERIMENTAL VALIDATION — Designing experiments...", flush=True)
    _current_phase["name"] = "critical_evaluation"  # use gemini for experiment design
    try:
        from discovery.experiment_planner import ExperimentPlanner
        planner = ExperimentPlanner(llm_call=_truncated_llm)
        top_theory = winner or (theories[0] if theories else {})
        if top_theory:
            exp_plans = planner.plan_for_top_theories(
                theories[:3], mechanisms, accepted_preds, papers, topic, domain, max_plans=2
            )
            if exp_plans:
                print(f"  Generated {len(exp_plans)} experimental validation plans")
                for ep in exp_plans:
                    etype = ep.get("experiment_type", "?")
                    tname = ep.get("theory_name", "?")
                    cost = ep.get("estimated_cost", "?")
                    timeline = ep.get("timeline_estimate", "?")
                    print(f"    [{etype}] {tname[:40]} — {timeline}, {cost} cost")
                report["phases"]["experimental_validation"] = {
                    "plans_generated": len(exp_plans),
                    "plans": exp_plans,
                }
            else:
                print("  No experimental plans generated")
    except Exception as e:
        print(f"  [WARN] Experimental validation planning failed: {e}")

    # -- Simulation Pipeline --
    top_theory = winner or (theories[0] if theories else {})
    if top_theory and accepted_preds:
        try:
            from discovery.simulation_pipeline import SimulationPipeline
            sp = SimulationPipeline()
            theory_desc = top_theory.get("description", top_theory.get("mechanism", ""))
            if theory_desc:
                sim_result = sp.run(theory_desc, domain=domain)
                if sim_result:
                    summary = sp.get_summary()
                    print(f"  [Monte Carlo] {summary.get('total_simulations', 0)} sims, support: {summary.get('overall_support', 'unknown')}", flush=True)
        except Exception as e:
            print(f"  [WARN] Simulation pipeline skipped: {e}")

    # ══════════════════════════════════════════════════════════════
    # PHASE 9.7: DATA ANALYSIS — Fetch & analyze real datasets
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 9.7/12] DATA ANALYSIS — Fetching public datasets...", flush=True)
    try:
        from discovery.data_analysis import DataAnalyzer
        analyzer = DataAnalyzer()
        dataset_results = {}

        # Auto-select data source based on domain
        domain_lower = domain.lower()
        topic_lower = topic.lower()

        # Space/Astronomy: NASA Exoplanets + NEO
        if "space" in domain_lower or "astro" in domain_lower or "exoplanet" in topic_lower:
            result = analyzer.fetch_nasa_exoplanets(limit=50)
            if result.get("status") == "ok":
                dataset_results["nasa_exoplanets"] = result
                analysis = analyzer.analyze_dataset("nasa_exoplanets")
                dataset_results["analysis"] = analysis
                print(f"  NASA Exoplanets: {result['records']} records, {len(analysis.get('statistics', {}))} numeric fields")
                if analysis.get("correlations"):
                    top_corr = analysis["correlations"][0]
                    print(f"    Top correlation: {top_corr['field1']} ↔ {top_corr['field2']} (r={top_corr['correlation']})")
            # Also fetch NEO data for asteroid/comet topics
            if any(kw in topic_lower for kw in ["asteroid", "neo", "comet", "impact", "meteor"]):
                neo_result = analyzer.fetch_nasa_neo(days=7)
                if neo_result.get("status") == "ok":
                    dataset_results["nasa_neo"] = neo_result
                    print(f"  NASA NEO: {neo_result['records']} near-earth objects")

        # Climate/Energy: NASA POWER data
        elif "climate" in domain_lower or "energy" in domain_lower:
            try:
                from discovery.nasa_power import get_climate_data
                climate = get_climate_data(lat=40.0, lon=-100.0, year=2023)
                if climate:
                    dataset_results["nasa_power"] = {"status": "ok", "records": 1, "data": climate}
                    print(f"  NASA POWER: climate data fetched")
            except Exception:
                pass

        # Drug Discovery: PubChem compound data for entities in graph
        elif "drug" in domain_lower or "pharma" in domain_lower:
            try:
                from discovery.pubchem import search_compound
                compounds_found = 0
                for eid, ent in list(graph.entities.items())[:10]:
                    if ent.get("type") in ("drug", "compound", "chemical"):
                        pc = search_compound(ent["name"])
                        if pc:
                            compounds_found += 1
                if compounds_found:
                    dataset_results["pubchem"] = {"status": "ok", "records": compounds_found}
                    print(f"  PubChem: {compounds_found} compounds enriched")
            except Exception:
                pass

        # Ecology: GBIF species data
        elif "ecology" in domain_lower or "species" in topic_lower or "biodiversity" in topic_lower:
            try:
                from discovery.gbif_api import search_species
                species = search_species(topic.split()[0] if topic else "", limit=20)
                if species:
                    dataset_results["gbif"] = {"status": "ok", "records": len(species), "data": species}
                    print(f"  GBIF: {len(species)} species records")
            except Exception:
                pass

        # Public Health: WHO data
        elif "health" in domain_lower or "epidem" in topic_lower or "disease" in topic_lower:
            try:
                from discovery.who_api import get_disease_data, search_indicators
                disease_data = get_disease_data(topic.split()[0] if topic else "diabetes")
                if disease_data:
                    dataset_results["who_disease"] = {"status": "ok", "records": 1, "data": disease_data}
                    print(f"  WHO: disease data fetched")
                indicators = search_indicators(topic.split()[0] if topic else "", limit=10)
                if indicators:
                    dataset_results["who_indicators"] = {"status": "ok", "records": len(indicators), "data": indicators}
                    print(f"  WHO: {len(indicators)} health indicators")
            except Exception:
                pass

        # Materials Science: Materials Project data for entities
        elif "material" in domain_lower:
            try:
                from discovery.materials_project import enrich_entities as enrich_mp
                enriched = enrich_mp(graph)
                if enriched:
                    dataset_results["materials_project"] = {"status": "ok", "records": enriched}
                    print(f"  Materials Project: {enriched} materials enriched")
            except Exception:
                pass

        # Mathematics: OEIS sequences
        elif "math" in domain_lower or "sequence" in topic_lower or "prime" in topic_lower:
            try:
                from discovery.oeis_api import enrich_entities as enrich_oeis
                enriched = enrich_oeis(graph)
                if enriched:
                    dataset_results["oeis"] = {"status": "ok", "records": enriched}
                    print(f"  OEIS: {enriched} sequences enriched")
            except Exception:
                pass

        # Chemistry / Drug Discovery / Materials: NIST thermochemical data
        if not dataset_results or "chemistry" in domain_lower or "drug" in domain_lower or "material" in domain_lower:
            try:
                from discovery.nist_api import search_compound as nist_search, get_thermochemical_data, get_fundamental_constants
                nist_data = {}
                # Search NIST for chemical entities in graph
                chem_types = {"chemical", "compound", "drug", "material", "element"}
                searched = 0
                for eid, ent in list(graph.entities.items())[:15]:
                    if ent.get("type") in chem_types:
                        results = nist_search(ent["name"], limit=1)
                        if results:
                            nist_data[ent["name"]] = results[0]
                            searched += 1
                if nist_data:
                    dataset_results["nist_compounds"] = {"status": "ok", "records": len(nist_data), "data": nist_data}
                    print(f"  NIST: {len(nist_data)} compounds found in WebBook")
                # Also fetch fundamental constants for physics/chemistry domains
                if "physics" in domain_lower or "chemistry" in domain_lower:
                    constants = get_fundamental_constants()
                    if constants:
                        dataset_results["nist_constants"] = {"status": "ok", "records": len(constants.get("constants", {})), "data": constants}
                        print(f"  NIST CODATA: {len(constants.get('constants', {}))} fundamental constants")
            except Exception:
                pass

        if dataset_results:
            report["phases"]["data_analysis"] = {
                "datasets_fetched": len(dataset_results),
                "results": {k: {"status": v.get("status"), "records": v.get("records", 0)} for k, v in dataset_results.items() if isinstance(v, dict)},
                "statistics": dataset_results.get("analysis", {}).get("statistics", {}),
                "correlations": dataset_results.get("analysis", {}).get("correlations", []),
            }
        else:
            print("  No domain-specific datasets available")
    except Exception as e:
        print(f"  [WARN] Data analysis failed: {e}")

    # ══════════════════════════════════════════════════════════════
    # PHASE 10: CONTRADICTION MINING
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 10/12] CONTRADICTION MINING...", flush=True)
    try:
        miner = ContradictionMiner(graph)
        contradiction_result = miner.mine(papers=papers, llm_call=_truncated_llm)
        contradictions = contradiction_result.get("contradictions", [])
        graph_contradictions = graph.detect_contradictions()
        all_contradictions = contradictions + [
            {"type": c["type"], "description": c["summary"], "severity": c.get("severity", "medium")}
            for c in graph_contradictions
        ]
        print(f"  Found {len(all_contradictions)} contradictions")
        report["phases"]["contradictions"] = {
            "total": len(all_contradictions),
            "contradictions": all_contradictions,
        }
    except Exception as e:
        print(f"  [ERROR] Contradiction mining failed: {e}")
        all_contradictions = []

    # -- Contradiction-Driven Hypothesis Generation --
    # Contradictions between papers are where discoveries hide
    if all_contradictions and _truncated_llm and len(theories) < 10:
        try:
            contra_text = "\n".join(
                f"- [{c.get('type','?')}] {c.get('description', c.get('summary', ''))[:120]}"
                for c in all_contradictions[:5]
            )
            contra_prompt = f"""You are a scientist resolving contradictions in the literature.

TOPIC: {topic}
DOMAIN: {domain}

CONTRADICTIONS FOUND:
{contra_text}

For each contradiction, propose a hypothesis that would RESOLVE it.
A resolving hypothesis explains WHY both sides are partially right, under different conditions.

BAD: "One paper is wrong" (not a resolution)
GOOD: "Both papers are correct — the effect depends on condition X that differs between studies"

Generate 2-3 hypotheses that resolve these contradictions. Each must:
1. Explain why BOTH sides of the contradiction can be true
2. Identify the hidden variable that determines which side applies
3. Make a testable prediction about when each side applies

Output JSON:
{{"hypotheses": [{{"name": "...", "description": "...", "type": "contradiction_resolution", "resolves": "which contradiction", "hidden_variable": "what determines the outcome", "testable_prediction": "..."}}]}}"""

            contra_raw = _truncated_llm(contra_prompt, max_tokens=4096)
            if contra_raw:
                from discovery.json_extract import extract_json
                contra_result = extract_json(contra_raw)
                if contra_result:
                    contra_hyps = contra_result.get("hypotheses", [])
                    added = 0
                    for h in contra_hyps:
                        h.setdefault("name", "")
                        h.setdefault("description", "")
                        h.setdefault("type", "contradiction_resolution")
                        h.setdefault("source", "contradiction_resolution")
                        if h.get("name") and h.get("description"):
                            # Add to theories, not hidden variables
                            h.setdefault("predictions", [])
                            h.setdefault("key_assumptions", [])
                            h.setdefault("explains", [])
                            h.setdefault("fails_to_explain", [])
                            theories.append(h)
                            added += 1
                    if added:
                        print(f"  [Contradiction Resolution] {added} hypotheses generated from contradictions", flush=True)
        except Exception as e:
            print(f"  [WARN] Contradiction-driven hypotheses skipped: {e}", flush=True)

    # ══════════════════════════════════════════════════════════════
    # PHASE 11: SKEPTIC REVIEW
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 11/12] SKEPTIC REVIEW — Adversarial critique...", flush=True)
    _current_phase["name"] = "skeptic_review"
    skeptic_result = {}
    try:
        top_theory = winner or (theories[0] if theories else {})
        if top_theory and _truncated_llm:
            # -- SkepticAgent legacy (async, wrapped) --
            try:
                import asyncio
                from discovery.skeptic_agent import SkepticAgent
                sa = SkepticAgent(llm_call=_truncated_llm)
                legacy_review = asyncio.run(sa.review(top_theory))
                if legacy_review:
                    print(f"  [SkepticAgent] Legacy review complete", flush=True)
            except Exception:
                pass

            # Build context about competing theories for fair comparison
            alt_names = [t.get('name', '?') for t in theories[:5] if t.get('name') != top_theory.get('name')]
            alt_text = ', '.join(alt_names[:3]) if alt_names else 'none'

            skeptic_prompt = f"""You are a rigorous but fair scientific reviewer. Evaluate this theory objectively.

THEORY: {top_theory.get('name', '?')}
DESCRIPTION: {top_theory.get('description', top_theory.get('mechanism', ''))[:300]}
PREDICTIONS: {json.dumps((top_theory.get('predictions') if isinstance(top_theory.get('predictions'), list) else [])[:3])}
COMPETING THEORIES: {alt_text}
PAPERS SUPPORTING: {len(papers)}

Evaluate FAIRLY:
1. What does this theory explain well? (strengths)
2. What are the genuine weaknesses? (be specific)
3. How does it compare to alternatives?
4. What evidence would strengthen or weaken it?
5. Recommendation: accept (strong) | revise (promising but needs work) | reject (fundamentally flawed)
6. Revised confidence (0.0-1.0) — be realistic, not automatically low
7. FAILURE CONDITIONS: What specific observation would definitively disprove this theory?
8. DESTROYING EVIDENCE: What existing evidence contradicts or weakens this theory?
9. COMPETING EXPLANATION: What alternative theory explains the same data better?

IMPORTANT: Only recommend "reject" if the theory has FUNDAMENTAL logical flaws or contradicts established evidence. Most theories should get "revise" or "accept with conditions".

Output JSON: {{"critique": "...", "strengths": ["s1", "s2"], "weaknesses": ["w1", "w2"], "recommendation": "accept|revise|reject", "revised_confidence": 0.0, "improvement_suggestions": ["suggestion1"], "failure_conditions": ["condition1"], "destroying_evidence": ["evidence1"], "competing_explanation": "alternative theory"}}"""

            raw = _truncated_llm(skeptic_prompt, max_tokens=4096)
            if raw:
                from discovery.json_extract import extract_json
                skeptic_result = extract_json(raw)
                if skeptic_result is None:
                    # Fallback: try regex extraction
                    import re
                    if isinstance(raw, str):
                        match = re.search(r'\{.*\}', raw, re.DOTALL)
                        if match:
                            try:
                                skeptic_result = json.loads(match.group())
                            except json.JSONDecodeError:
                                pass

        rec = skeptic_result.get('recommendation', 'unknown')
        conf = skeptic_result.get('revised_confidence', 0)
        strengths = skeptic_result.get('strengths', [])
        weaknesses = skeptic_result.get('weaknesses', [])
        print(f"  Recommendation: {rec} (confidence: {conf:.0%})")
        if strengths:
            print(f"  Strengths: {', '.join(strengths[:2])}")
        if weaknesses:
            print(f"  Weaknesses: {', '.join(weaknesses[:2])}")
        report["phases"]["skeptic_review"] = {
            "recommendation": rec,
            "revised_confidence": conf,
            "strengths": strengths,
            "weaknesses": weaknesses,
        }
    except Exception as e:
        print(f"  [ERROR] Skeptic review failed: {e}")
        skeptic_result = {"recommendation": "unknown", "weaknesses": ["Review failed"]}

    # ══════════════════════════════════════════════════════════════
    # PHASE 12: DISCOVERY SCORING
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 12/12] DISCOVERY SCORING — Final quality gate...", flush=True)
    try:
        scorer = DiscoveryScorer()
        top_theory = winner or (theories[0] if theories else {})

        # If no theory from tournament, construct synthetic theory from pipeline output
        if not top_theory or not top_theory.get("name"):
            if hidden_variables or mechanisms or accepted_preds:
                print(f"  [WARN] No tournament theories — constructing synthetic theory from pipeline output", flush=True)
                top_theory = {
                    "name": f"Discovery synthesis: {topic[:60]}",
                    "description": f"Synthesized from {len(hidden_variables)} hidden variables, "
                                   f"{len(mechanisms)} mechanisms, and {len(accepted_preds)} predictions.",
                    "type": "synthesis",
                    "predictions": accepted_preds or [],
                    "hidden_variables": [hv.get("name", "") for hv in hidden_variables],
                    "steps": [s for m in mechanisms[:3] for s in (m.get("steps") if isinstance(m.get("steps"), list) else m.get("causal_chain") if isinstance(m.get("causal_chain"), list) else [])[:2]],
                    "explains": [g.get("reason", "") for g in (gaps or [])[:3]],
                    "fails_to_explain": [],
                    "key_assumptions": [],
                    "tournament_status": "synthetic",
                }

        if top_theory:
            score_result = scorer.score(
                top_theory, gaps, anomalies, accepted_preds, papers, graph,
                adversarial_results=report.get("phases", {}).get("adversarial_test"),
                skeptic_result=report.get("phases", {}).get("skeptic_review"),
                critical_eval=report.get("phases", {}).get("peer_review"),
            )
            # Apply domain-specific scoring weights
            try:
                from discovery.domain_templates import adjust_discovery_score
                score_result = adjust_discovery_score(score_result, domain)
                domain_score = score_result.get("domain_weighted_score", score_result["discovery_score"])
                print(f"  Discovery Score: {score_result['discovery_score']:.0f}/100 (domain-weighted: {domain_score:.0f}/100)")
            except Exception:
                print(f"  Discovery Score: {score_result['discovery_score']:.0f}/100")
            print(f"  Grade: {score_result['grade']}")
            print(f"  Summary: {score_result['summary'][:100]}")
            adv_penalty = score_result.get("adversarial_penalty", 0)
            if adv_penalty > 0:
                print(f"  Adversarial Penalty: -{adv_penalty:.0f} points", flush=True)
                for detail in score_result.get("adversarial_details", []):
                    print(f"    - {detail}", flush=True)
            report["phases"]["discovery_scoring"] = score_result

            # -- Confidence Scorer — store in report and adjust score --
            try:
                from discovery.confidence_scorer import ConfidenceScorer
                cs = ConfidenceScorer()
                cs_result = cs.score(top_theory, graph=graph)
                if cs_result:
                    conf = cs_result.get("confidence", 0)
                    print(f"  [Confidence] Evidence-weighted: {conf:.2f}")
                    report["phases"]["confidence_scoring"] = cs_result
                    # If confidence is very low, cap the discovery score
                    if conf < 0.1:
                        current_score = score_result.get("discovery_score", 0)
                        capped = min(current_score, 55)
                        if capped < current_score:
                            score_result["discovery_score"] = capped
                            score_result.setdefault("adversarial_details", []).append(
                                f"Very low confidence ({conf:.2f}) -> capped at 55"
                            )
                            print(f"  [Confidence] Very low confidence -> score capped at 55", flush=True)
            except Exception as e:
                print(f"  [WARN] Confidence scorer skipped: {e}")

        else:
            report["phases"]["discovery_scoring"] = {"discovery_score": 0, "grade": "F"}
    except Exception as e:
        print(f"  [ERROR] Discovery scoring failed: {e}")
        score_result = {"discovery_score": 0, "grade": "F"}

    # Classify discovery type — prevent inflation
    try:
        top_theory = winner or (theories[0] if theories else {})
        theory_desc = top_theory.get("description", top_theory.get("mechanism", "")) if top_theory else ""
        theory_name = top_theory.get("name", "") if top_theory else ""

        # Check for novelty requirements
        has_new_mechanism = any(kw in theory_desc.lower() for kw in ["novel", "new mechanism", "proposed", "unknown"])
        has_new_prediction = len(accepted_preds) > 0
        has_new_math = any(kw in theory_desc.lower() for kw in ["equation", "formula", "derivation", "mathematical"])
        not_in_literature = top_theory.get("is_novel_vs_known", "") == "novel" if top_theory else False

        if has_new_mechanism and has_new_prediction and has_new_math and not_in_literature:
            discovery_class = "novel_theory"
        elif has_new_mechanism or has_new_prediction:
            discovery_class = "extension"
        elif len(theories) > 1:
            discovery_class = "synthesis"
        else:
            discovery_class = "replication"

        report["phases"]["discovery_classification"] = {
            "classification": discovery_class,
            "has_new_mechanism": has_new_mechanism,
            "has_new_prediction": has_new_prediction,
            "has_new_math": has_new_math,
            "not_in_literature": not_in_literature,
        }
        print(f"  Classification: {discovery_class}")
    except Exception as e:
        print(f"  [WARN] Classification failed: {e}")

    # -- Discovery Enhancer --
    try:
        from discovery.discovery_enhancer import enhance_discovery
        enhanced = enhance_discovery(report, topic, domain, papers=papers, graph=graph)
        if enhanced:
            print(f"  [Enhancer] Post-pipeline enhancement complete", flush=True)
    except Exception as e:
        print(f"  [WARN] Discovery enhancer skipped: {e}")

    # ══════════════════════════════════════════════════════════════
    # PHASE 13: REFINEMENT PIPELINE (13 stages)
    # ══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70, flush=True)
    print("  REFINEMENT PIPELINE — 13 stages of post-processing", flush=True)
    print("=" * 70, flush=True)

    # -- Metrics Tracker --
    try:
        from discovery.metrics_tracker import MetricsTracker
        metrics = MetricsTracker()
        for phase_name, phase_data in report.get("phases", {}).items():
            if isinstance(phase_data, dict):
                metrics.record(phase_name, "ok", time.time() - t_start, metadata={"items": len(phase_data)})
    except Exception:
        pass

    try:
        from discovery.refinement_pipeline import run_refinement_pipeline
        refinement = run_refinement_pipeline(
            topic, domain, papers, graph,
            theories, all_contradictions
        )
        report["refinement"] = refinement

        # Print refinement summary
        if refinement:
            print(f"\n  Stage 1 (Knowledge Audit): {len(refinement.get('audit', {}).get('key_entities', []))} key entities")
            print(f"  Stage 5 (Multi-Model): {len(refinement.get('multi_model', {}).get('hypotheses', []))} hypotheses")
            classification = refinement.get('classification', {})
            print(f"  Stage 11 (Classification): {classification.get('classification', 'unknown')}")
            scoring = refinement.get('scoring', {})
            print(f"  Stage 12 (Scoring): {scoring.get('grade', '?')} ({scoring.get('total_score', 0):.0f}/100)")
            courtroom = refinement.get('courtroom', {})
            print(f"  Stage 13 (Courtroom): {courtroom.get('verdict', 'unknown')}")
            report["phases"]["refinement"] = {
                "classification": classification.get('classification', 'unknown'),
                "grade": scoring.get('grade', '?'),
                "score": scoring.get('total_score', 0),
                "verdict": courtroom.get('verdict', 'unknown'),
            }

            # Propagate refinement adversarial results to discovery score
            refinement_adv = refinement.get('adversarial', {})
            if refinement_adv:
                survived = refinement_adv.get('survived', True)
                fatal = refinement_adv.get('fatal', 0)
                if not survived or fatal > 0:
                    # Apply refinement penalty to discovery score
                    if "discovery_scoring" in report.get("phases", {}):
                        current_score = report["phases"]["discovery_scoring"].get("discovery_score", 0)
                        penalty = min(15, fatal * 5)  # up to 15 points
                        new_score = max(0, current_score - penalty)
                        report["phases"]["discovery_scoring"]["discovery_score"] = new_score
                        report["phases"]["discovery_scoring"].setdefault("adversarial_details", []).append(
                            f"Refinement adversarial: {fatal} fatal (-{penalty})"
                        )
                        print(f"  [Refinement Impact] {fatal} fatal findings -> score -{penalty} ({current_score:.0f} -> {new_score:.0f})", flush=True)
    except Exception as e:
        print(f"  [ERROR] Refinement pipeline failed: {e}")
        report["errors"].append(f"Refinement: {e}")

    # ══════════════════════════════════════════════════════════════
    # PHASE 14: REFLEXION (Recursive Self-Improvement)
    # ══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70, flush=True)
    print("  REFLEXION — Recursive Self-Improvement", flush=True)
    print("=" * 70, flush=True)

    try:
        from brain.reflexion import get_recursive_improver
        improver = get_recursive_improver(llm_fn=_truncated_llm)
        run_result = {
            "query": topic,
            "domain": domain,
            "hypotheses": theories,
            "contradictions": all_contradictions,
            "metrics": {},
            "errors": report.get("errors", []),
            "refinement": report.get("refinement", {}),
        }
        reflexion_result = improver.reflect_and_improve_sync(run_result)
        report["reflexion"] = reflexion_result
        print(f"  Weaknesses found: {reflexion_result.get('weaknesses_found', 0)}")
        print(f"  Patches applied: {reflexion_result.get('patches_applied', 0)}")
        print(f"  Patches rejected: {reflexion_result.get('patches_rejected', 0)}")
        print(f"  Improvement score: {reflexion_result.get('improvement_score', 0):.0%}")
    except Exception as e:
        print(f"  [WARN] Reflexion skipped: {e}")

    # ══════════════════════════════════════════════════════════════
    # FINALIZE
    # ══════════════════════════════════════════════════════════════
    # Save to discovery archive — remember what we found
    try:
        run_summary = save_to_archive(report, topic, domain)
        print(f"  [Archive] Saved: {run_summary.get('theories_count', 0)} theories, "
              f"{run_summary.get('variables_count', 0)} variables, "
              f"{run_summary.get('mechanisms_count', 0)} mechanisms", flush=True)
    except Exception as e:
        print(f"  [Archive] Save failed: {e}", flush=True)

    # Hypothesis memory saving CUT — cross-topic noise outweighs benefit
    # HypothesisEngine and HypothesisTournament still save internally

    # -- Claim Grounding — link claims to real papers --
    try:
        from discovery.citation_grounding import ground_claims
        top_theory = winner or (theories[0] if theories else {})
        if top_theory and papers:
            theory_text = top_theory.get("description", top_theory.get("mechanism", ""))
            if theory_text:
                grounding = ground_claims(theory_text, papers)
                cited = grounding.get("cited_papers", [])
                uncited = grounding.get("uncited_claims", [])
                if cited or uncited:
                    print(f"  [Claim Grounding] {len(cited)} claims cited, {len(uncited)} uncited", flush=True)
                    report["phases"]["claim_grounding"] = {
                        "cited_papers": len(cited),
                        "uncited_claims": len(uncited),
                        "citation_map": grounding.get("citation_map", {}),
                    }
    except Exception as e:
        print(f"  [WARN] Claim grounding skipped: {e}", flush=True)

    # -- Claim Labeling — add confidence labels to report --
    try:
        from discovery.claim_labeler import label_report, generate_confidence_summary
        # Build a text summary of the top theory for labeling
        top_theory = winner or (theories[0] if theories else {})
        if top_theory:
            report_text = f"Theory: {top_theory.get('name', '')}\n"
            report_text += f"Description: {top_theory.get('description', top_theory.get('mechanism', ''))}\n"
            for p in (accepted_preds or [])[:5]:
                if isinstance(p, dict):
                    report_text += f"Prediction: {p.get('statement', p.get('description', ''))}\n"
            labeled = label_report(report_text, papers=papers, calculations=all_calculations)
            confidence_summary = generate_confidence_summary(labeled)
            if confidence_summary:
                print(f"  [Claim Labels] {confidence_summary}", flush=True)
                report["phases"]["claim_labeling"] = confidence_summary
    except Exception as e:
        print(f"  [WARN] Claim labeling skipped: {e}", flush=True)

    # -- Provenance Tracking — trace claims back to evidence --
    if provenance:
        try:
            top_theory = winner or (theories[0] if theories else {})
            if top_theory:
                theory_text = f"Theory: {top_theory.get('name', '')}\n"
                theory_text += f"Description: {top_theory.get('description', top_theory.get('mechanism', ''))}\n"
                for p in (accepted_preds or [])[:5]:
                    if isinstance(p, dict):
                        theory_text += f"Prediction: {p.get('statement', p.get('description', ''))}\n"
                provenance.process_report(theory_text)
                if provenance.claim_chains:
                    chains = [c.to_dict() for c in provenance.claim_chains]
                    validated = sum(1 for c in chains if c.get("label") == "VALIDATED")
                    inferred = sum(1 for c in chains if c.get("label") == "INFERRED")
                    speculative = sum(1 for c in chains if c.get("label") == "SPECULATIVE")
                    print(f"  [Provenance] {len(chains)} claims tracked: {validated} validated, {inferred} inferred, {speculative} speculative", flush=True)
                    report["phases"]["provenance"] = {
                        "total_claims": len(chains),
                        "validated": validated,
                        "inferred": inferred,
                        "speculative": speculative,
                        "chains": chains[:5],
                    }
        except Exception as e:
            print(f"  [WARN] Provenance tracking skipped: {e}", flush=True)

    # FINALIZE
    return _finalize_report(report, papers, graph, gaps, anomalies,
                            hidden_variables, mechanisms, predictions,
                            theories, accepted_preds, t_start)


def _finalize_report(report, papers, graph, gaps, anomalies,
                     hidden_variables, mechanisms, predictions,
                     theories, accepted_preds, t_start) -> dict:
    """Assemble the final discovery report with full scientific detail."""
    total_time = time.time() - t_start
    report["duration_seconds"] = round(total_time, 1)
    report["completed_at"] = datetime.now().isoformat()
    phases = report.get("phases", {})

    L = []  # summary lines

    L.append("=" * 70)
    L.append("  DISCOVERY REPORT")
    L.append("=" * 70)
    L.append(f"  Topic: {report.get('topic', 'N/A')}")
    L.append(f"  Domain: {report.get('domain', 'N/A')}")
    L.append(f"  Mode: {report.get('mode', 'N/A')}")
    L.append(f"  Duration: {total_time:.1f}s")
    L.append("")

    # ── Papers ──
    L.append("─" * 70)
    L.append(f"  PAPERS ({len(papers)})")
    L.append("─" * 70)
    for p in papers[:10]:
        if isinstance(p, dict):
            src = p.get("source", "?")
            title = p.get("title", "N/A")[:80]
            authors = p.get("authors", "")
            if isinstance(authors, list):
                authors = ", ".join(authors[:3])
            year = p.get("year", "")
            L.append(f"  [{src}] {title}")
            if authors:
                L.append(f"    Authors: {str(authors)[:80]}")
            if year:
                L.append(f"    Year: {year}")
    if len(papers) > 10:
        L.append(f"  ... and {len(papers) - 10} more papers")
    L.append("")

    # ── Knowledge Graph ──
    L.append("─" * 70)
    L.append("  KNOWLEDGE GRAPH")
    L.append("─" * 70)
    L.append(f"  Entities: {len(graph.entities)}")
    L.append(f"  Relationships: {len(graph.relationships)}")
    # Top entities by degree
    if hasattr(graph, 'entities') and graph.entities:
        try:
            degrees = {}
            for src, tgt, _ in graph.relationships:
                degrees[src] = degrees.get(src, 0) + 1
                degrees[tgt] = degrees.get(tgt, 0) + 1
            top_entities = sorted(degrees.items(), key=lambda x: -x[1])[:8]
            if top_entities:
                L.append(f"  Top entities by connections:")
                for name, deg in top_entities:
                    L.append(f"    {name} (degree: {deg})")
        except Exception:
            pass
    L.append("")

    # ── Knowledge Gaps ──
    if gaps:
        L.append("─" * 70)
        L.append(f"  KNOWLEDGE GAPS ({len(gaps)})")
        L.append("─" * 70)
        # Categorize gaps
        gap_types = {}
        for g in gaps:
            gtype = g.get("type", "unknown")
            gap_types.setdefault(gtype, []).append(g)
        for gtype, glist in gap_types.items():
            L.append(f"  [{gtype}] ({len(glist)} gaps)")
            for g in glist[:3]:
                reason = g.get("reason", g.get("description", ""))
                if reason:
                    L.append(f"    - {str(reason)[:120]}")
        L.append("")

    # ── Anomalies ──
    if anomalies:
        L.append("─" * 70)
        L.append(f"  ANOMALIES ({len(anomalies)})")
        L.append("─" * 70)
        for a in anomalies[:8]:
            atype = a.get("type", "?")
            areason = a.get("reason", a.get("description", ""))
            L.append(f"  [{atype}] {str(areason)[:120]}")
        L.append("")

    # ── Hidden Variables ──
    if hidden_variables:
        L.append("─" * 70)
        L.append(f"  HIDDEN VARIABLES ({len(hidden_variables)})")
        L.append("─" * 70)
        for i, hv in enumerate(hidden_variables):
            name = hv.get("name", "?")
            vtype = hv.get("type", "entity")
            desc = hv.get("description", "")
            evidence = hv.get("evidence", "")
            testability = hv.get("testability", "")
            key_params = hv.get("key_parameters", [])
            L.append(f"  {i+1}. [{vtype}] {name}")
            if desc:
                L.append(f"     Description: {desc[:200]}")
            if evidence:
                L.append(f"     Evidence: {str(evidence)[:150]}")
            if testability:
                L.append(f"     Testability: {str(testability)[:120]}")
            # Show derivation if available
            derivation = hv.get("derivation", "")
            if derivation and derivation.lower() not in ("not derivable", "n/a", ""):
                L.append(f"     Derivation:")
                for dline in str(derivation).split("\n")[:4]:
                    L.append(f"       {dline.strip()[:120]}")
            if key_params:
                for kp in key_params[:3]:
                    if isinstance(kp, dict):
                        pname = kp.get("name", "")
                        pval = kp.get("value", kp.get("expected_value", kp.get("range", "")))
                        punits = kp.get("units", "")
                        psource = kp.get("source", kp.get("origin", ""))
                        pdetail = kp.get("source_detail", "")
                        # Epistemic status label
                        label_map = {"cited": "📚 CITED", "derived": "🔧 DERIVED", "estimated": "⚠ ESTIMATED"}
                        label = label_map.get(psource, f"? {psource}" if psource else "")
                        L.append(f"     Parameter: {pname} = {pval} {punits}  {label}")
                        if pdetail:
                            L.append(f"       Source: {str(pdetail)[:120]}")
            L.append("")
        L.append("")

    # ── Mechanisms ──
    if mechanisms:
        L.append("─" * 70)
        L.append(f"  MECHANISMS ({len(mechanisms)})")
        L.append("─" * 70)
        for i, m in enumerate(mechanisms):
            mtype = m.get("type", "mechanism")
            mname = m.get("name", "?")
            mdesc = m.get("description", "")
            inputs = m.get("inputs", [])
            outputs = m.get("outputs", [])
            observables = m.get("observables", [])
            steps = m.get("steps", [])
            L.append(f"  {i+1}. [{mtype}] {mname}")
            if mdesc:
                L.append(f"     {mdesc[:200]}")
            if inputs:
                L.append(f"     Inputs: {', '.join(str(x) for x in (list(inputs) if isinstance(inputs, dict) else inputs)[:5])}")
            if outputs:
                L.append(f"     Outputs: {', '.join(str(x) for x in (list(outputs) if isinstance(outputs, dict) else outputs)[:5])}")
            if observables:
                L.append(f"     Observables: {', '.join(str(x) for x in (list(observables) if isinstance(observables, dict) else observables)[:5])}")
            for j, step in enumerate(steps):
                s_str = str(step)[:150] if step else ""
                if s_str:
                    L.append(f"     Step {j+1}: {s_str}")
            # Show derivation if available
            derivation = m.get("derivation", "")
            if derivation and derivation.lower() not in ("not derivable", "n/a", ""):
                L.append(f"     Derivation:")
                for dline in str(derivation).split("\n")[:5]:
                    L.append(f"       {dline.strip()[:120]}")
            # Show classification (known synthesis vs new physics)
            classification = m.get("classification", "")
            if classification:
                class_labels = {
                    "new_synthesis": "NEW SYNTHESIS of existing data",
                    "new_physics": "NEW PHYSICS — novel mechanism",
                    "new_context_for_known": "KNOWN mechanism in NEW context",
                    "replication": "REPLICATION of known results",
                }
                L.append(f"     Classification: {class_labels.get(classification, classification)}")
            # Show key parameters with epistemic labels
            mech_params = m.get("key_parameters") or []
            if isinstance(mech_params, dict):
                mech_params = [{"name": k, "value": v} for k, v in mech_params.items()]
            if mech_params:
                L.append(f"     Key parameters:")
                for kp in mech_params[:4]:
                    if isinstance(kp, dict):
                        kpname = kp.get("name", "")
                        kpval = kp.get("expected_value", kp.get("value", kp.get("range", "")))
                        kpunits = kp.get("units", "")
                        kpsource = kp.get("source", "")
                        kpdetail = kp.get("source_detail", "")
                        label_map = {"cited": "CITED", "derived": "DERIVED", "estimated": "ESTIMATED"}
                        label = label_map.get(kpsource, kpsource if kpsource else "")
                        kpline = f"       {kpname} = {kpval} {kpunits}"
                        if label:
                            kpline += f"  [{label}]"
                        L.append(kpline)
                        if kpdetail:
                            L.append(f"         {str(kpdetail)[:100]}")
            L.append("")
        L.append("")

    # ── Predictions ──
    if predictions or accepted_preds:
        preds_to_show = accepted_preds if accepted_preds else predictions
        L.append("─" * 70)
        L.append(f"  PREDICTIONS ({len(predictions)} generated, {len(accepted_preds)} accepted)")
        L.append("─" * 70)
        for i, p in enumerate(preds_to_show):
            if isinstance(p, dict):
                ptype = p.get("type", "prediction")
                stmt = p.get("statement", p.get("description", ""))
                conf = p.get("confidence", "")
                test = p.get("test", p.get("test_method", ""))
                fals = p.get("falsification", p.get("falsification_criterion", ""))
                L.append(f"  {i+1}. [{ptype}] {stmt[:180]}")
                if conf:
                    L.append(f"     Confidence: {conf}")
                if test:
                    L.append(f"     Test: {str(test)[:120]}")
                if fals:
                    L.append(f"     Falsification: {str(fals)[:120]}")
                L.append("")
        L.append("")

    # ── Rejected Predictions ──
    rejected_preds = [p for p in (predictions or []) if isinstance(p, dict) and p.get("validation_status") == "rejected"]
    if rejected_preds:
        L.append("─" * 70)
        L.append(f"  REJECTED PREDICTIONS ({len(rejected_preds)})")
        L.append("─" * 70)
        for p in rejected_preds[:5]:
            stmt = p.get("statement", p.get("description", ""))[:120]
            reason = p.get("rejection_reason", "unknown")
            L.append(f"  [REJECTED] {stmt}")
            L.append(f"     Reason: {reason}")
        L.append("")

    # ── Adversarial Verdicts (killed/superseded) ──
    adv_test = phases.get("adversarial_test", {})
    if adv_test:
        killed_items = []
        for test_list_name in ["hidden_variable_tests", "mechanism_tests", "theory_tests"]:
            for t in adv_test.get(test_list_name, []):
                if isinstance(t, dict) and t.get("verdict") in ("superseded", "killed"):
                    killed_items.append(t)
        if killed_items:
            L.append("─" * 70)
            L.append(f"  KILLED / SUPERSEDED BY ADVERSARIAL TEST ({len(killed_items)})")
            L.append("─" * 70)
            for t in killed_items[:8]:
                name = t.get("name", "?")[:50]
                verdict = t.get("verdict", "?")
                reason = t.get("reasoning", t.get("existing_theory", ""))[:100]
                score = t.get("attack_score", 0)
                L.append(f"  [SUPERSEDED] {name} (attack score: {score:.2f})")
                if reason:
                    L.append(f"     Reason: {reason}")
            L.append("")

    # ── Theory Competition ──
    if theories:
        L.append("─" * 70)
        tc = phases.get("theory_competition", {})
        total_compared = tc.get("theories_compared", len(theories))
        eliminated_count = len(tc.get("eliminated", []))
        L.append(f"  THEORY TOURNAMENT ({total_compared} entered, {len(theories)} survived, {eliminated_count} eliminated)")
        L.append("─" * 70)

        # Tournament log
        tournament_log = tc.get("tournament_log", [])
        if tournament_log:
            L.append(f"  Tournament rounds:")
            for entry in tournament_log:
                round_num = entry.get("round", "?")
                action = entry.get("action", "?")
                survived = entry.get("survived", entry.get("candidates", "?"))
                elim = entry.get("eliminated", "")
                if elim:
                    L.append(f"    Round {round_num}: {action} — {survived} survived, {elim} eliminated")
                else:
                    L.append(f"    Round {round_num}: {action} — {survived} candidates")

        # Competition analysis
        analysis = tc.get("competition_analysis", "")
        if analysis:
            L.append(f"\n  Analysis: {str(analysis)[:300]}")

        # Sort by overall score
        scored = []
        for t in theories:
            if isinstance(t, dict):
                score = t.get("scores", {}).get("overall", 0)
                scored.append((score, t))
        scored.sort(key=lambda x: -x[0])

        L.append(f"\n  Survivors (ranked):")
        for rank, (score, t) in enumerate(scored[:7], 1):
            tname = t.get("name", "?")
            tdesc = t.get("description", "")
            ttype = t.get("type", "hypothesis")
            scores = t.get("scores", {})
            mechanism = t.get("mechanism", "")
            explains = t.get("explains") or t.get("supporting_evidence") or []
            fails = t.get("fails_to_explain") or t.get("contradictory_evidence") or []
            assumptions = t.get("key_assumptions") or []
            causal = t.get("causal_status", "")

            L.append(f"  {rank}. {tname} (score: {score:.2f}) [{ttype}]")
            if tdesc:
                L.append(f"     {tdesc[:200]}")
            if mechanism:
                L.append(f"     Mechanism: {str(mechanism)[:150]}")
            if explains:
                L.append(f"     Explains: {'; '.join(str(e)[:60] for e in explains[:3])}")
            if fails:
                L.append(f"     Fails to explain: {'; '.join(str(f)[:60] for f in fails[:3])}")
            if assumptions:
                L.append(f"     Key assumptions: {'; '.join(str(a)[:60] for a in assumptions[:3])}")
            if causal:
                L.append(f"     Causal status: {causal}")
            # Per-dimension scores
            if scores and isinstance(scores, dict):
                dims = []
                for dim in ["explanatory_power", "predictive_power", "falsifiability",
                            "evidence_strength", "novelty", "simplicity", "mathematical_rigor"]:
                    if dim in scores:
                        dims.append(f"{dim}={scores[dim]:.0%}" if isinstance(scores[dim], float) and scores[dim] <= 1 else f"{dim}={scores[dim]}")
                if dims:
                    L.append(f"     Scores: {', '.join(dims)}")
            L.append("")

        # Discriminating experiments
        experiments = tc.get("discriminating_experiments", [])
        if experiments:
            L.append(f"  Discriminating experiments (would separate top 2):")
            for i, exp in enumerate(experiments[:3], 1):
                L.append(f"    {i}. {str(exp)[:150]}")
            L.append("")

        # Show eliminated theories briefly
        eliminated = tc.get("eliminated", [])
        if eliminated:
            L.append(f"  Eliminated ({len(eliminated)}):")
            for t in eliminated[:5]:
                tname = t.get("name", "?")
                score = t.get("scores", {}).get("overall", 0)
                reason = t.get("elimination_reason", "")
                L.append(f"    ✗ {tname} (score: {score:.2f}) — {str(reason)[:80]}")
            if len(eliminated) > 5:
                L.append(f"    ... and {len(eliminated) - 5} more")
        L.append("")

    # ── Adversarial Test Results ──
    adv_test = phases.get("adversarial_test", {})
    if adv_test:
        L.append("─" * 70)
        L.append("  ADVERSARIAL TEST — What Survived the Attack")
        L.append("─" * 70)
        summary = adv_test.get("survival_summary", {})
        for category in ["hidden_variables", "mechanisms", "theories"]:
            s = summary.get(category, {})
            started = s.get("started", 0)
            survived = s.get("survived", 0)
            weakened = s.get("weakened", 0)
            killed = s.get("killed", 0)
            if started > 0:
                L.append(f"  {category}: {started} tested → {survived} survived, {weakened} weakened, {killed} killed")

        # Show individual test results
        for test_list_name, label in [
            ("hidden_variable_tests", "Hidden Variables"),
            ("mechanism_tests", "Mechanisms"),
            ("theory_tests", "Theories"),
        ]:
            test_list = adv_test.get(test_list_name, [])
            if test_list:
                L.append(f"  {label}:")
                for t in test_list:
                    name = t.get("name", "?")
                    verdict = t.get("verdict", "?")
                    score = t.get("attack_score", 0)
                    existing = t.get("existing_theory", "")
                    can_remove = t.get("can_remove_variables", False)
                    falsification = t.get("falsification", "")
                    reasoning = t.get("reasoning", "")
                    icon = {"survived": "✓", "weakened": "⚠", "killed": "✗"}.get(verdict, "?")

                    L.append(f"    {icon} {name[:50]} [{verdict}, attack score: {score:.2f}]")
                    if existing and existing.lower() not in ("none known", "no known theory explains this", ""):
                        L.append(f"      Existing theory: {str(existing)[:100]}")
                    if can_remove:
                        removable = t.get("removable_variables", [])
                        L.append(f"      Can remove: {', '.join(str(v) for v in removable[:3])}")
                    if falsification and falsification.lower() not in ("none", "test failed", ""):
                        L.append(f"      Falsification: {str(falsification)[:100]}")
                    if reasoning:
                        L.append(f"      Verdict: {str(reasoning)[:120]}")
        L.append("")

    # ── Critical Evaluation ──
    pr = phases.get("peer_review", {})
    if pr:
        L.append("─" * 70)
        L.append("  CRITICAL EVALUATION — 6-Dimension Assessment")
        L.append("─" * 70)
        L.append(f"  Overall Score: {pr.get('overall_score', 0)}/10")
        L.append(f"  Recommendation: {pr.get('recommendation', 'unknown')}")
        summary = pr.get("summary", "")
        if summary:
            L.append(f"  Summary: {str(summary)[:300]}")
        # Dimension scores
        for dim in ["novelty", "methodology", "significance", "clarity", "limitations", "reproducibility"]:
            dim_data = pr.get(dim, {})
            if isinstance(dim_data, dict):
                score = dim_data.get("score", "?")
                comment = dim_data.get("comment", "")
                L.append(f"  {dim.capitalize()}: {score}/10 — {str(comment)[:80]}")
        # Issues
        major = pr.get("major_issues", [])
        minor = pr.get("minor_issues", [])
        questions = pr.get("questions_for_authors", [])
        if major:
            L.append(f"  Major issues ({len(major)}):")
            for issue in major:
                L.append(f"    ! {str(issue)[:120]}")
        if minor:
            L.append(f"  Minor issues ({len(minor)}):")
            for issue in minor:
                L.append(f"    - {str(issue)[:120]}")
        if questions:
            L.append(f"  Questions for authors:")
            for q in questions:
                L.append(f"    ? {str(q)[:120]}")
        L.append("")

    # ── Contradictions ──
    contradictions = phases.get("contradictions", {})
    contradiction_list = contradictions.get("contradictions", [])
    if contradiction_list:
        L.append("─" * 70)
        L.append(f"  CONTRADICTIONS ({len(contradiction_list)})")
        L.append("─" * 70)
        for i, c in enumerate(contradiction_list[:5]):
            if isinstance(c, dict):
                cdesc = c.get("description", c.get("detail", ""))
                csev = c.get("severity", "")
                L.append(f"  {i+1}. {str(cdesc)[:150]}")
                if csev:
                    L.append(f"     Severity: {csev}")
            elif isinstance(c, str):
                L.append(f"  {i+1}. {c[:150]}")
        L.append("")

    # ── Computational Verification ──
    comp = phases.get("computational_verification", {})
    if comp:
        L.append("─" * 70)
        L.append("  COMPUTATIONAL VERIFICATION")
        L.append("─" * 70)
        L.append(f"  Computations run: {comp.get('total_computations', 0)}")
        L.append(f"  Support level: {comp.get('support_level', 'unknown')}")
        for finding in comp.get("key_findings", [])[:5]:
            L.append(f"    → {str(finding)[:120]}")
        L.append("")

    # ── Skeptic Review ──
    sr = phases.get("skeptic_review", {})
    if sr:
        L.append("─" * 70)
        L.append("  SKEPTIC REVIEW")
        L.append("─" * 70)
        L.append(f"  Recommendation: {sr.get('recommendation', 'N/A')}")
        L.append(f"  Revised confidence: {sr.get('revised_confidence', 0):.0%}")
        strengths = sr.get("strengths", [])
        weaknesses = sr.get("weaknesses", [])
        if strengths:
            L.append(f"  Strengths ({len(strengths)}):")
            for s in strengths:
                L.append(f"    + {str(s)[:150]}")
        if weaknesses:
            L.append(f"  Weaknesses ({len(weaknesses)}):")
            for w in weaknesses:
                L.append(f"    - {str(w)[:150]}")
        failure_conditions = sr.get("failure_conditions", [])
        if failure_conditions:
            L.append(f"  Failure conditions:")
            for fc in failure_conditions:
                L.append(f"    ! {str(fc)[:120]}")
        L.append("")

    # ── Discovery Scoring ──
    ds = phases.get("discovery_scoring", {})
    if ds:
        L.append("─" * 70)
        L.append("  DISCOVERY SCORING")
        L.append("─" * 70)
        L.append(f"  Overall Score: {ds.get('discovery_score', 0):.0f}/100")
        L.append(f"  Grade: {ds.get('grade', 'F')}")
        scores = ds.get("scores", {})
        if scores:
            L.append(f"  Dimension scores:")
            for dim, val in scores.items():
                L.append(f"    {dim}: {val}")
        strengths = ds.get("strengths", [])
        weaknesses = ds.get("weaknesses", [])
        if strengths:
            L.append(f"  Strengths: {'; '.join(str(s)[:80] for s in strengths[:3])}")
        if weaknesses:
            L.append(f"  Weaknesses: {'; '.join(str(w)[:80] for w in weaknesses[:3])}")
        summary = ds.get("summary", "")
        if summary:
            L.append(f"  Summary: {str(summary)[:200]}")
        L.append("")

    # ── Discovery Classification — What's Known vs What's New ──
    dc = phases.get("discovery_classification", {})
    if dc:
        L.append("─" * 70)
        L.append("  DISCOVERY CLASSIFICATION — What's Known vs What's New")
        L.append("─" * 70)
        classification = dc.get('classification', 'N/A')
        class_desc = {
            "replication": "Confirms existing knowledge — validates what was already known",
            "synthesis": "Combines existing ideas in a new way — new connections between known concepts",
            "extension": "New application of known mechanisms — applies existing physics to new domain",
            "novel_theory": "Requires new mechanism, new prediction, new mathematics — genuinely new",
        }
        L.append(f"  Classification: {classification}")
        L.append(f"  Meaning: {class_desc.get(classification, 'Unknown classification')}")
        L.append(f"  Details:")
        L.append(f"    New mechanism proposed: {dc.get('has_new_mechanism', False)}")
        L.append(f"    New prediction generated: {dc.get('has_new_prediction', False)}")
        L.append(f"    New mathematics introduced: {dc.get('has_new_math', False)}")
        L.append(f"    Not found in literature: {dc.get('not_in_literature', False)}")

        # Summarize what's known vs what's new from mechanisms
        mech_classifications = {}
        for m in mechanisms:
            mc = m.get("classification", "")
            if mc:
                mech_classifications[mc] = mech_classifications.get(mc, 0) + 1
        if mech_classifications:
            L.append(f"  Mechanism breakdown:")
            for mc, count in mech_classifications.items():
                mc_label = {
                    "new_synthesis": "New synthesis of existing data",
                    "new_physics": "New physics — novel mechanism",
                    "new_context_for_known": "Known mechanism in new context",
                    "replication": "Replication of known results",
                }.get(mc, mc)
                L.append(f"    {mc_label}: {count}")
        L.append("")

    # ── Errors ──
    if report.get("errors"):
        L.append("─" * 70)
        L.append(f"  ERRORS ({len(report['errors'])})")
        L.append("─" * 70)
        for e in report["errors"]:
            L.append(f"  ! {e}")
        L.append("")

    L.append("=" * 70)

    report_text = "\n".join(L)
    report["summary_text"] = report_text

    print(report_text)

    # Save report + text + update dashboard index
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    report_path = data_dir / f"discovery_v2_{int(time.time())}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str, ensure_ascii=False),
                           encoding="utf-8")
    print(f"\n  Report saved: {report_path}")

    # Save human-readable text report alongside JSON
    txt_path = report_path.with_suffix(".txt")
    txt_path.write_text(report_text, encoding="utf-8")
    print(f"  Text report: {txt_path}")

    # Update reports index for dashboard
    idx_path = data_dir / "reports_index.json"
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []
    except Exception:
        idx = []
    rel = str(report_path.relative_to(Path(__file__).parent.parent))
    if rel not in idx:
        idx.append(rel)
        idx_path.write_text(json.dumps(idx[-50:], indent=2), encoding="utf-8")

    return report


if __name__ == "__main__":
    import sys
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "KRAS G12C inhibitor resistance"
    run_discovery_pipeline(topic, mode="full")
