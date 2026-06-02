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

    graph = KnowledgeGraph(persist=False)
    graph.domain = domain

    for p in papers:
        pmid = p.get("id", p.get("citation_key", "unknown"))
        graph.add_paper(pmid, p["title"], p.get("abstract", ""), p["url"], p.get("year", ""))

    for ent in extracted.get("entities", []):
        pmid = papers[0].get("id", "unknown") if papers else "unknown"
        graph.add_paper_entities([ent], pmid)

    for rel in extracted.get("relationships", []):
        pmid = papers[0].get("id", "unknown") if papers else "unknown"
        graph.add_relationships([rel], pmid)

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
    print(f"  Provider:  {status['primary'].upper()}")
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
        }
    except Exception as e:
        print(f"  [ERROR] Literature fetch failed: {e}")
        report["errors"].append(f"Phase 1: {e}")
        papers = []
        citation_context = ""

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
    except Exception as e:
        print(f"  [ERROR] Gap detection failed: {e}")
        report["errors"].append(f"Phase 3: {e}")
        gaps = []

    if mode == "quick":
        return _finalize_report(report, papers, graph, gaps, [], [], [], [], [], [], t_start)

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
    except Exception as e:
        print(f"  [ERROR] Anomaly detection failed: {e}")
        report["errors"].append(f"Phase 4: {e}")
        anomalies = []

    # ══════════════════════════════════════════════════════════════
    # PHASE 5: MISSING VARIABLES
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 5/12] MISSING VARIABLES — Proposing hidden factors...", flush=True)

    # Truncated LLM wrapper — Groq only for discovery engine (Gemini reserved for chats)
    def _truncated_llm(prompt, max_tokens=4096, **kwargs):
        """LLM call with truncated prompt and timeout. Groq only for discovery."""
        if len(prompt) > 2000:
            prompt = prompt[:1800] + "\n\n[Context truncated — respond with available information]"
        import threading
        result = [None]
        error = [None]
        def _call():
            try:
                r = call_json(prompt, max_tokens=min(max_tokens, 2048), provider="groq")
                result[0] = r
            except Exception as e:
                error[0] = e
        t = threading.Thread(target=_call, daemon=True)
        t.start()
        t.join(timeout=60)  # 60 second timeout
        if t.is_alive():
            print("    [WARN] Groq timed out (60s)", flush=True)
            return None
        if error[0]:
            print(f"    [WARN] Groq error: {error[0]}", flush=True)
            return None
        return result[0]

    try:
        mv_generator = MissingVariableGenerator(graph=graph, llm_call=_truncated_llm)
        mv_results = mv_generator.generate(gaps, anomalies, topic, domain, papers)
        hidden_variables = mv_results.get("hidden_variables", [])

        # Algorithmic fallback if LLM returns nothing
        if not hidden_variables:
            from discovery.algorithmic_discovery import generate_hypotheses_algorithmic
            hidden_variables = generate_hypotheses_algorithmic(graph, gaps, anomalies, topic, domain)
            if hidden_variables:
                print(f"  Algorithmic fallback: {len(hidden_variables)} hypotheses")
        print(f"  Proposed {len(hidden_variables)} hidden variables")
        for hv in hidden_variables[:3]:
            print(f"    [{hv.get('type', '?')}] {hv.get('name', '?')}")
            print(f"      {hv.get('description', '')[:100]}")
        report["phases"]["missing_variables"] = {
            "proposed": len(hidden_variables),
            "variables": [hv.get("name", "?") for hv in hidden_variables],
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
    try:
        mech_generator = MechanismGenerator(graph=graph, llm_call=_truncated_llm)
        mech_results = mech_generator.generate_mechanisms(
            hidden_variables, gaps, anomalies, topic, domain, papers
        )
        mechanisms = mech_results.get("mechanisms", [])

        # Algorithmic fallback
        if not mechanisms:
            from discovery.algorithmic_discovery import generate_mechanisms_algorithmic
            mechanisms = generate_mechanisms_algorithmic(graph, hidden_variables, topic, domain)
            if mechanisms:
                print(f"  Algorithmic fallback: {len(mechanisms)} mechanisms")
        print(f"  Generated {len(mechanisms)} mechanisms")
        for m in mechanisms[:3]:
            print(f"    [{m.get('type', '?')}] {m.get('name', '?')}")
            for s in m.get("steps", [])[:2]:
                print(f"      → {s[:80]}")
        report["phases"]["mechanism_generation"] = {
            "mechanisms_generated": len(mechanisms),
            "types": list(set(m.get("type", "?") for m in mechanisms)),
        }
    except Exception as e:
        print(f"  [ERROR] Mechanism generation failed: {e}")
        report["errors"].append(f"Phase 6: {e}")
        mechanisms = []

    # ══════════════════════════════════════════════════════════════
    # PHASE 7: PREDICTION ENGINE
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 7/12] PREDICTION ENGINE — Generating testable predictions...", flush=True)
    try:
        pred_engine = PredictionEngine(graph=graph, llm_call=_truncated_llm)
        pred_results = pred_engine.generate_predictions(
            mechanisms, hidden_variables, topic, domain, anomalies
        )
        predictions = pred_results.get("predictions", [])

        # Algorithmic fallback
        if not predictions:
            from discovery.algorithmic_discovery import generate_predictions_algorithmic
            predictions = generate_predictions_algorithmic(mechanisms, hidden_variables, topic, domain)
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
    try:
        competition = TheoryCompetition(graph=graph, llm_call=_truncated_llm)
        comp_results = competition.compete(
            mechanisms, hidden_variables, anomalies, gaps, topic, domain, papers
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
        print(f"  {len(theories)} competing theories")
        if winner:
            w_score = winner.get("scores", {}).get("overall", 0)
            print(f"  Winner: {winner.get('name', '?')} (score: {w_score:.2f})")
        report["phases"]["theory_competition"] = {
            "theories_compared": len(theories),
            "winner": winner,
            "winner_name": winner.get("name") if winner else None,
            "winner_score": winner.get("scores", {}).get("overall", 0) if winner else 0,
        }
    except Exception as e:
        print(f"  [ERROR] Theory competition failed: {e}")
        report["errors"].append(f"Phase 8: {e}")
        theories = []
        winner = None

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
        report["phases"]["contradictions"] = {"total": len(all_contradictions)}
    except Exception as e:
        print(f"  [ERROR] Contradiction mining failed: {e}")
        all_contradictions = []

    # ══════════════════════════════════════════════════════════════
    # PHASE 11: SKEPTIC REVIEW
    # ══════════════════════════════════════════════════════════════
    print("\n[Phase 11/12] SKEPTIC REVIEW — Adversarial critique...", flush=True)
    skeptic_result = {}
    try:
        top_theory = winner or (theories[0] if theories else {})
        if top_theory and _truncated_llm:
            skeptic_prompt = f"""You are an adversarial skeptical scientific reviewer. FALSIFY this theory.

THEORY: {top_theory.get('name', '?')}
DESCRIPTION: {top_theory.get('description', top_theory.get('mechanism', ''))[:300]}
PREDICTIONS: {json.dumps(top_theory.get('predictions', [])[:3])}

Find:
1. Logical flaws
2. Missing alternatives
3. Top 3 weaknesses
4. Recommendation: accept|revise|reject
5. Revised confidence (0.0-1.0)

Output JSON: {{"critique": "...", "weaknesses": ["w1","w2","w3"], "recommendation": "accept|revise|reject", "revised_confidence": 0.0}}"""

            raw = _truncated_llm(skeptic_prompt, max_tokens=4096)
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    skeptic_result = json.loads(raw)
        print(f"  Recommendation: {skeptic_result.get('recommendation', 'unknown')}")
        report["phases"]["skeptic_review"] = {
            "recommendation": skeptic_result.get("recommendation", "unknown"),
            "revised_confidence": skeptic_result.get("revised_confidence", 0),
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
            print(f"  Discovery Score: {score_result['discovery_score']:.0f}/100")
            print(f"  Grade: {score_result['grade']}")
            print(f"  Summary: {score_result['summary'][:100]}")
            report["phases"]["discovery_scoring"] = score_result
        else:
            report["phases"]["discovery_scoring"] = {"discovery_score": 0, "grade": "F"}
    except Exception as e:
        print(f"  [ERROR] Discovery scoring failed: {e}")
        score_result = {"discovery_score": 0, "grade": "F"}

    return _finalize_report(report, papers, graph, gaps, anomalies,
                            hidden_variables, mechanisms, predictions,
                            theories, accepted_preds, t_start)


def _finalize_report(report, papers, graph, gaps, anomalies,
                     hidden_variables, mechanisms, predictions,
                     theories, accepted_preds, t_start) -> dict:
    """Assemble the final discovery report."""
    total_time = time.time() - t_start
    report["duration_seconds"] = round(total_time, 1)
    report["completed_at"] = datetime.now().isoformat()

    # Build human-readable summary
    summary_lines = []
    summary_lines.append("=" * 70)
    summary_lines.append("  DISCOVERY REPORT")
    summary_lines.append("=" * 70)
    summary_lines.append(f"  Topic: {report['topic']}")
    summary_lines.append(f"  Domain: {report['domain']}")
    summary_lines.append(f"  Duration: {total_time:.1f}s")
    summary_lines.append("")

    # Papers
    summary_lines.append(f"  PAPERS: {len(papers)}")
    for p in papers[:5]:
        summary_lines.append(f"    [{p['source']}] {p['title'][:60]}")

    # Graph
    summary_lines.append(f"\n  KNOWLEDGE GRAPH: {len(graph.entities)} entities, {len(graph.relationships)} relationships")

    # Gaps
    summary_lines.append(f"\n  KNOWLEDGE GAPS: {len(gaps)}")
    for g in gaps[:3]:
        summary_lines.append(f"    [{g.get('type', '?')}] {g.get('reason', '')[:80]}")

    # Anomalies
    summary_lines.append(f"\n  ANOMALIES: {len(anomalies)}")
    for a in anomalies[:3]:
        summary_lines.append(f"    [{a.get('type', '?')}] {a.get('reason', '')[:80]}")

    # Hidden Variables
    summary_lines.append(f"\n  HIDDEN VARIABLES PROPOSED: {len(hidden_variables)}")
    for hv in hidden_variables[:3]:
        summary_lines.append(f"    [{hv.get('type', '?')}] {hv.get('name', '?')}")
        summary_lines.append(f"      {hv.get('description', '')[:100]}")

    # Mechanisms
    summary_lines.append(f"\n  MECHANISMS: {len(mechanisms)}")
    for m in mechanisms[:3]:
        summary_lines.append(f"    [{m.get('type', '?')}] {m.get('name', '?')}")
        for s in m.get("steps", [])[:2]:
            summary_lines.append(f"      → {s[:80]}")

    # Predictions
    summary_lines.append(f"\n  PREDICTIONS: {len(predictions)} generated, {len(accepted_preds)} accepted")
    for p in (accepted_preds or [])[:3]:
        if isinstance(p, dict):
            summary_lines.append(f"    [{p.get('type', '?')}] {p.get('statement', '')[:80]}")

    # Theory Competition
    if theories:
        summary_lines.append(f"\n  THEORY COMPETITION: {len(theories)} theories compared")
        for t in theories[:3]:
            score = t.get("scores", {}).get("overall", 0)
            summary_lines.append(f"    {t.get('name', '?')} (score: {score:.2f})")

    # Computational Verification
    comp_phase = report.get("phases", {}).get("computational_verification", {})
    summary_lines.append(f"\n  COMPUTATIONS RUN: {comp_phase.get('total_computations', 0)}")
    summary_lines.append(f"  SUPPORT LEVEL: {comp_phase.get('support_level', 'unknown')}")

    # Discovery Score
    score_phase = report.get("phases", {}).get("discovery_scoring", {})
    summary_lines.append(f"\n  DISCOVERY SCORE: {score_phase.get('discovery_score', 0):.0f}/100")
    summary_lines.append(f"  GRADE: {score_phase.get('grade', 'F')}")

    # Errors
    if report["errors"]:
        summary_lines.append(f"\n  ERRORS: {len(report['errors'])}")
        for e in report["errors"]:
            summary_lines.append(f"    WARNING: {e}")

    summary_lines.append("=" * 70)

    report_text = "\n".join(summary_lines)
    report["summary_text"] = report_text

    print(report_text)

    # Save report
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)
    report_path = data_dir / f"discovery_v2_{int(time.time())}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str, ensure_ascii=False),
                           encoding="utf-8")
    print(f"\n  Report saved: {report_path}")

    return report


if __name__ == "__main__":
    import sys
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "KRAS G12C inhibitor resistance"
    run_discovery_pipeline(topic, mode="full")
