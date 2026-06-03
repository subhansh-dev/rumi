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
from datetime import datetime
from pathlib import Path
from typing import Optional

# Existing modules
from discovery.llm_client import call as llm_call, call_json, get_status
from discovery.citation_grounding import fetch_papers, build_citation_context, ground_claims
from discovery.computational import run_all_calculations, format_calculations_for_prompt
from discovery.domain_computational import run_domain_calculations, format_for_prompt, DOMAIN_COMPUTATIONS
from discovery.claim_labeler import label_report, generate_confidence_summary
from discovery.claim_provenance import ProvenanceTracker
from discovery.graph import KnowledgeGraph
from discovery.contradiction_miner import ContradictionMiner

# NEW discovery modules (v2.1)
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
                        "dyson", "technosignature", "stellar", "dimming", "cme"],
    "neuroscience": ["neuron", "brain", "neurotransmitter", "dopamine", "serotonin",
                     "synaptic", "cortex", "hippocampus", "consciousness", "fmri"],
    "drug_discovery": ["drug", "inhibitor", "kinase", "antibiotic", "cancer", "pharma",
                       "therapeutic", "binding affinity", "clinical trial", "ic50", "ec50"],
    "materials_science": ["perovskite", "battery", "catalyst", "bandgap", "nanomaterial",
                          "graphene", "2d material", "solar cell", "semiconductor", "alloy"],
    "climate_energy": ["climate", "carbon", "emission", "renewable", "solar", "wind",
                       "greenhouse", "warming", "co2", "temperature"],
    "ecology": ["species", "biodiversity", "ecosystem", "conservation", "habitat",
                "extinction", "population", "invasion", "endangered"],
    "physics": ["quantum", "particle", "higgs", "gravity", "wave", "boson",
                "fermion", "relativity", "dark matter", "entanglement"],
    "computer_science": ["neural network", "llm", "transformer", "algorithm", "machine learning",
                         "deep learning", "dataset", "benchmark", "architecture"],
    "public_health": ["vaccine", "pandemic", "epidemic", "disease", "mortality",
                      "prevalence", "intervention", "clinical", "public health"],
    "chemistry": ["reaction", "synthesis", "catalysis", "compound", "organic",
                  "inorganic", "analytical", "spectroscopy", "electrochemistry"],
    "mathematics": ["theorem", "proof", "conjecture", "prime", "topology",
                    "optimization", "sequence", "algebra", "geometry"],
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
        paper_text += f"\n[{i}] {p['title']}\n    {p.get('abstract', '')[:300]}\n"

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
        graph.add_paper(pmid, p["title"], p.get("abstract", ""), p["url"], p.get("year", ""))

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
        print(f"  [Archive] Loaded past discovery context", flush=True)

    # Load hypothesis memory — prior hypotheses from all runs
    hyp_mem = HypothesisMemory()
    prior_hypotheses = hyp_mem.get_all(domain=domain, limit=20)
    # Also fetch by topic similarity
    topic_similar = hyp_mem.find_similar(topic, threshold=0.3)
    prior_hyp_ids = {h.get("id") for h in prior_hypotheses}
    for ts in topic_similar:
        if ts["id"] not in prior_hyp_ids:
            full = hyp_mem.get_hypothesis(ts["id"])
            if full:
                prior_hypotheses.append(full)
                prior_hyp_ids.add(ts["id"])

    # Build prior hypothesis context and merge into archive_context
    if prior_hypotheses:
        prior_lines = []
        prior_lines.append(f"\nPRIOR HYPOTHESIS MEMORY ({len(prior_hypotheses)} hypotheses from past runs):")
        prior_lines.append("These were proposed before. Build on them, refine them, or explore angles they missed.")
        for h in prior_hypotheses[:10]:
            status = h.get("status", "draft")
            title = h.get("title", "?")
            desc = (h.get("description") or "")[:150]
            score = h.get("confidence", 0)
            prior_lines.append(f"  [{status}] {title} (confidence: {score:.2f})")
            if desc:
                prior_lines.append(f"    {desc}")
            weaknesses = h.get("critique_weaknesses", "")
            if weaknesses:
                prior_lines.append(f"    Weaknesses: {weaknesses[:100]}")
        archive_context += "\n" + "\n".join(prior_lines)
        print(f"  [Hypothesis Memory] Loaded {len(prior_hypotheses)} prior hypotheses", flush=True)

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
    print("\n[Phase 1/12] LITERATURE — Fetching papers from 3 sources...", flush=True)
    try:
        # Primary query
        papers = fetch_papers(topic, max_arxiv=20, max_pubmed=20, max_s2=20)
        print(f"  Primary search: {len(papers)} papers")

        # Broader query — extract key terms and search again
        topic_words = [w for w in topic.lower().split() if len(w) > 4]
        if len(topic_words) >= 2:
            broad_query = " ".join(topic_words[:3])
            broad_papers = fetch_papers(broad_query, max_arxiv=10, max_pubmed=10, max_s2=10)
            # Add non-duplicates
            existing_titles = {p["title"].lower()[:60] for p in papers}
            for p in broad_papers:
                if p["title"].lower()[:60] not in existing_titles:
                    papers.append(p)
            print(f"  Broadened search: +{len(papers) - len(broad_papers)} new papers")

        print(f"  Total: {len(papers)} papers from {len(set(p['source'] for p in papers))} sources")
        for p in papers[:5]:
            cites = p.get('citation_count', '')
            cite_str = f" ({cites} citations)" if cites else ""
            print(f"    [{p['source']}] {p['title'][:65]}{cite_str}")
        citation_context = build_citation_context(papers)
        report["phases"]["literature"] = {
            "papers_found": len(papers),
            "sources": list(set(p["source"] for p in papers)),
            "papers": papers,
        }
    except Exception as e:
        print(f"  [ERROR] Literature fetch failed: {e}")
        report["errors"].append(f"Phase 1: {e}")
        papers = []
        citation_context = ""

    # ══════════════════════════════════════════════════════════════
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

    # Phase-specific LLM routing — fast models for extraction, best for reasoning
    # cerebras: fastest (entity extraction, scoring, pattern matching)
    # gemini: best reasoning (mechanisms, theories, adversarial critique)
    # auto: balanced (Cerebras→Groq→Gemini fallback)
    PHASE_PROVIDERS = {
        "literature": "cerebras",       # Phase 1: simple extraction
        "knowledge_graph": "cerebras",  # Phase 2: entity extraction
        "gap_detection": "cerebras",    # Phase 3: pattern matching
        "anomaly_detection": "cerebras",# Phase 4: pattern matching
        "missing_variables": "auto",    # Phase 5: needs some creativity
        "mechanism_generation": "gemini",# Phase 6: deep causal reasoning
        "prediction_engine": "auto",    # Phase 7: balanced
        "theory_competition": "gemini", # Phase 8: tournament needs best reasoning
        "adversarial_test": "cerebras", # Phase 8.5: fast adversarial perspective
        "critical_evaluation": "auto",  # Phase 8.6: balanced
        "skeptic_review": "gemini",     # Phase 11: critical analysis
        "scoring": "cerebras",          # Phase 12: mostly algorithmic
    }
    _current_phase = {"name": "missing_variables"}  # mutable for closure

    # Direct LLM wrapper — no thread, no silent failures
    def _truncated_llm(prompt, max_tokens=4096, **kwargs):
        """LLM call with prompt truncation + phase-aware routing."""
        if len(prompt) > 8000:
            prompt = prompt[:7500] + "\n\n[Context truncated — respond with available information]"
        # Allow phase override via kwargs
        phase = kwargs.get("phase", _current_phase["name"])
        provider = PHASE_PROVIDERS.get(phase, "auto")
        try:
            r = call_json(prompt, max_tokens=max_tokens, provider=provider)
            if r is None and provider != "auto":
                # Phase-specific provider failed — try all providers via auto
                print(f"    [DEBUG] LLM returned None ({provider}), trying auto...", flush=True)
                r = call_json(prompt, max_tokens=max_tokens, provider="auto")
            if r is None:
                print(f"    [DEBUG] LLM returned None (all providers exhausted)", flush=True)
            elif isinstance(r, str) and len(r) < 10:
                print(f"    [DEBUG] LLM returned short string: '{r}'", flush=True)
            return r
        except Exception as e:
            print(f"    [ERROR] LLM exception: {e}", flush=True)
            return None

    try:
        mv_generator = MissingVariableGenerator(graph=graph, llm_call=_truncated_llm)
        mv_results = mv_generator.generate(gaps, anomalies, topic, domain, papers, archive_context)
        hidden_variables = mv_results.get("hidden_variables", [])

        # Algorithmic fallback if LLM returns nothing
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
        mech_generator = MechanismGenerator(graph=graph, llm_call=_truncated_llm)
        mech_results = mech_generator.generate_mechanisms(
            hidden_variables, gaps, anomalies, topic, domain, papers, archive_context
        )
        mechanisms = mech_results.get("mechanisms", [])

        # Algorithmic fallback
        if not mechanisms:
            from discovery.algorithmic_discovery import generate_mechanisms_algorithmic
            mechanisms = generate_mechanisms_algorithmic(graph, hidden_variables, topic, domain)
            if mechanisms:
                print(f"  Algorithmic fallback: {len(mechanisms)} mechanisms")

        # Validate mechanisms — allow single-step direct observations
        validated_mechanisms = []
        for m in mechanisms:
            name = m.get("name", "")
            steps = m.get("steps", [])
            # Reject generic "Hidden mechanism connecting X" without details
            if "Hidden mechanism connecting" in name and len(steps) < 1:
                continue
            # Allow single-step mechanisms (direct observations are valid)
            if len(steps) < 1:
                continue
            # Tag single-step as direct_observation
            if len(steps) == 1:
                m.setdefault("type", "direct_observation")
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
        accepted_preds = validation.get("accepted", predictions)

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
        competition = TheoryCompetition(graph=graph, llm_call=_truncated_llm)
        comp_results = competition.compete(
            mechanisms, hidden_variables, anomalies, gaps, topic, domain, papers,
            archive_context=archive_context
        )
        theories = comp_results.get("theories", [])
        winner = comp_results.get("winner")

        # Algorithmic fallback
        if not theories:
            from discovery.algorithmic_discovery import compare_theories_algorithmic
            theories = compare_theories_algorithmic(hidden_variables, graph, papers)
            winner = theories[0] if theories else None
            if theories:
                print(f"  Algorithmic fallback: {len(theories)} theories compared")

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
        }
    except Exception as e:
        print(f"  [ERROR] Theory competition failed: {e}")
        report["errors"].append(f"Phase 8: {e}")
        theories = []
        winner = None

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

    # ══════════════════════════════════════════════════════════════
    # PHASE 9.7: DATA ANALYSIS — Fetch & analyze real datasets
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 9.7/12] DATA ANALYSIS — Fetching public datasets...", flush=True)
    try:
        from discovery.data_analysis import DataAnalyzer
        analyzer = DataAnalyzer()
        dataset_results = {}

        # Auto-select data source based on domain
        if "space" in domain.lower() or "astro" in domain.lower() or "exoplanet" in topic.lower():
            result = analyzer.fetch_nasa_exoplanets(limit=50)
            if result.get("status") == "ok":
                dataset_results["nasa_exoplanets"] = result
                analysis = analyzer.analyze_dataset("nasa_exoplanets")
                dataset_results["analysis"] = analysis
                print(f"  NASA Exoplanets: {result['records']} records, {len(analysis.get('statistics', {}))} numeric fields")
                if analysis.get("correlations"):
                    top_corr = analysis["correlations"][0]
                    print(f"    Top correlation: {top_corr['field1']} ↔ {top_corr['field2']} (r={top_corr['correlation']})")

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
        contradiction_result = miner.mine()
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

    # ══════════════════════════════════════════════════════════════
    # PHASE 11: SKEPTIC REVIEW
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 11/12] SKEPTIC REVIEW — Adversarial critique...", flush=True)
    _current_phase["name"] = "skeptic_review"
    skeptic_result = {}
    try:
        top_theory = winner or (theories[0] if theories else {})
        if top_theory and _truncated_llm:
            # Build context about competing theories for fair comparison
            alt_names = [t.get('name', '?') for t in theories[:5] if t.get('name') != top_theory.get('name')]
            alt_text = ', '.join(alt_names[:3]) if alt_names else 'none'

            skeptic_prompt = f"""You are a rigorous but fair scientific reviewer. Evaluate this theory objectively.

THEORY: {top_theory.get('name', '?')}
DESCRIPTION: {top_theory.get('description', top_theory.get('mechanism', ''))[:300]}
PREDICTIONS: {json.dumps(top_theory.get('predictions', [])[:3])}
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
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    try:
                        skeptic_result = json.loads(raw)
                    except json.JSONDecodeError:
                        # Try to extract JSON from the response
                        import re
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
        if top_theory:
            score_result = scorer.score(
                top_theory, gaps, anomalies, accepted_preds, papers, graph
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
            report["phases"]["discovery_scoring"] = score_result
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

    # ══════════════════════════════════════════════════════════════
    # PHASE 13: REFINEMENT PIPELINE (13 stages)
    # ══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70, flush=True)
    print("  REFINEMENT PIPELINE — 13 stages of post-processing", flush=True)
    print("=" * 70, flush=True)

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
        improver = get_recursive_improver()
        run_result = {
            "query": topic,
            "domain": domain,
            "hypotheses": theories,
            "contradictions": all_contradictions,
            "metrics": {},
            "errors": report.get("errors", []),
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

    # Save theories to hypothesis memory — cross-run persistence
    try:
        saved_count = 0
        for t in theories:
            if isinstance(t, dict) and t.get("name"):
                hyp_data = {
                    "title": t.get("name", ""),
                    "description": t.get("description", t.get("mechanism", "")),
                    "pattern_type": t.get("type", "proposed"),
                    "confidence": t.get("scores", {}).get("overall", 0),
                    "novelty": t.get("is_novel_vs_known", ""),
                    "status": "accepted" if winner and t.get("name") == winner.get("name") else "survived",
                    "topic": topic,
                    "domain": domain,
                    "testability": json.dumps(t.get("predictions", [])[:3]),
                    "nodes": t.get("hidden_variables", []),
                    "edges": [],
                }
                hyp_mem.save_hypothesis(hyp_data, run_id=run_id)
                saved_count += 1
        if saved_count:
            print(f"  [Hypothesis Memory] Saved {saved_count} theories", flush=True)
        report["hypothesis_memory"] = {"saved": saved_count, "run_id": run_id}
    except Exception as e:
        print(f"  [Hypothesis Memory] Save failed: {e}", flush=True)

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
            mech_params = m.get("key_parameters", [])
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
            explains = t.get("explains", [])
            fails = t.get("fails_to_explain", [])
            assumptions = t.get("key_assumptions", [])
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
