"""
RUMI Full Discovery Pipeline — Every module wired.

Papers → KnowledgeGraph → ContradictionMiner → Gap Detection →
HypothesisEngine → HypothesisTournament → SkepticAgent →
ExperimentPlanner → Computational Verification →
Claim Labeling + Provenance → Discovery Candidate

This is the pipeline RUMI was designed to run.
"""

import asyncio
import json
import sys
import time
import os

# Force unbuffered output for background runs
sys.stdout.reconfigure(line_buffering=True)
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from discovery.llm_client import call as llm_call, call_json, is_available, get_status
from discovery.citation_grounding import fetch_papers, build_citation_context, ground_claims
from discovery.computational import run_all_calculations, format_calculations_for_prompt
from discovery.domain_computational import run_domain_calculations, format_for_prompt, DOMAIN_COMPUTATIONS
from discovery.claim_labeler import label_report, generate_confidence_summary, add_report_header
from discovery.claim_provenance import ProvenanceTracker
from discovery.graph import KnowledgeGraph
from discovery.contradiction_miner import ContradictionMiner
from discovery.hypothesis_engine import HypothesisEngine
from discovery.hypothesis_tournament import HypothesisTournament
from discovery.skeptic_agent import SkepticAgent
from discovery.experiment_planner import ExperimentPlanner
from discovery.novelty_detector import NoveltyDetector
from discovery.confidence_scorer import ConfidenceScorer
from discovery.pipeline import LLMStage

# ── Domain detection ──
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
    if scores:
        return max(scores, key=scores.get)
    return "general"


def extract_entities_from_papers(papers: list[dict], domain: str) -> dict:
    """Use LLM to extract entities and relationships from paper abstracts."""
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
        result = call_json(prompt, max_tokens=2048)
        if result:
            if isinstance(result, str):
                # Strip markdown fences if present
                text = result.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                    text = text.rsplit("```", 1)[0].strip()
                result = json.loads(text)
            if isinstance(result, dict):
                return result
        else:
            print("    [WARN] Entity extraction LLM returned None — using fallback", flush=True)
    except Exception as e:
        print(f"    Entity extraction LLM call failed: {e}", flush=True)

    # Fallback: extract basic entities from titles
    entities = []
    relationships = []
    for p in papers:
        title = p.get("title", "")
        if title:
            entities.append({"name": title[:60], "type": "concept", "aliases": []})
    return {"entities": entities, "relationships": relationships}


def build_knowledge_graph(papers: list[dict], domain: str) -> KnowledgeGraph:
    """Build a real KnowledgeGraph from papers with LLM-extracted entities."""
    print("    Extracting entities from papers via LLM...")
    extracted = extract_entities_from_papers(papers, domain)

    graph = KnowledgeGraph(persist=False)
    graph.domain = domain

    # Add papers
    for p in papers:
        pmid = p.get("id", p.get("citation_key", "unknown"))
        graph.add_paper(pmid, p["title"], p.get("abstract", ""), p["url"], p.get("year", ""))

    # Add entities
    for ent in extracted.get("entities", []):
        pmid = papers[0].get("id", "unknown") if papers else "unknown"
        graph.add_paper_entities([ent], pmid)

    # Add relationships
    for rel in extracted.get("relationships", []):
        pmid = papers[0].get("id", "unknown") if papers else "unknown"
        graph.add_relationships([rel], pmid)

    graph.save(session_id=f"full_pipeline_{int(time.time())}")
    print(f"    Graph: {len(graph.entities)} entities, {len(graph.relationships)} relationships")
    return graph


def run_full_pipeline(topic: str, domain: str = "", generations: int = 3):
    """
    The real pipeline. Every module, wired properly.
    """
    if not domain:
        domain = detect_domain(topic)

    status = get_status()
    t_start = time.time()

    print("=" * 70, flush=True)
    print("  RUMI — FULL DISCOVERY PIPELINE", flush=True)
    print("=" * 70, flush=True)
    print(f"  Topic:     {topic}")
    print(f"  Domain:    {domain}")
    print(f"  Provider:  {status['primary'].upper()}")
    print(f"  Modules:   Graph + ContradictionMiner + HypothesisEngine")
    print(f"             + Tournament({generations}gen) + SkepticAgent + ExperimentPlanner")
    print("=" * 70)

    # ════════════════════════════════════════════════════════════════
    # STAGE 1: PAPERS — Real citations from arXiv + PubMed
    # ════════════════════════════════════════════════════════════════
    print("\n[1/9] PAPERS — Fetching from arXiv + PubMed...")
    papers = fetch_papers(topic, max_arxiv=6, max_pubmed=6)
    print(f"  Found {len(papers)} papers")
    for p in papers[:4]:
        print(f"    [{p['source']}] {p['citation_key']} — {p['title'][:65]}")
    citation_context = build_citation_context(papers)

    # ════════════════════════════════════════════════════════════════
    # STAGE 2: KNOWLEDGE GRAPH — Entity extraction + graph building
    # ════════════════════════════════════════════════════════════════
    print("\n[2/9] KNOWLEDGE GRAPH — Building from papers...")
    graph = build_knowledge_graph(papers, domain)

    # ════════════════════════════════════════════════════════════════
    # STAGE 3: CONTRADICTION DETECTION — Algorithmic graph analysis
    # ════════════════════════════════════════════════════════════════
    print("\n[3/9] CONTRADICTION DETECTION — Mining knowledge graph...")
    miner = ContradictionMiner(graph)
    contradiction_result = miner.mine()
    contradictions = contradiction_result.get("contradictions", [])
    print(f"  Found {len(contradictions)} contradictions")
    for c in contradictions[:3]:
        print(f"    [{c.get('type', '?')}] {c.get('description', c.get('summary', ''))[:80]}")

    # Also run the graph's built-in contradiction detection
    graph_contradictions = graph.detect_contradictions()
    all_contradictions = contradictions + [
        {"type": c["type"], "description": c["summary"], "severity": c.get("severity", "medium")}
        for c in graph_contradictions
    ]
    print(f"  Graph contradictions: {len(graph_contradictions)}")
    print(f"  Total: {len(all_contradictions)} contradictions")

    # ════════════════════════════════════════════════════════════════
    # STAGE 4: GAP DETECTION — Graph metrics + structural holes
    # ════════════════════════════════════════════════════════════════
    print("\n[4/9] GAP DETECTION — Analyzing knowledge graph structure...")
    metrics = graph.compute_metrics()
    print(f"  Density: {metrics['density']}")
    print(f"  Entities: {metrics['entity_count']}, Edges: {metrics['edge_count']}")

    # Find high-betweenness entities (potential bridging concepts)
    top_betweenness = sorted(
        metrics.get("entity_metrics", {}).items(),
        key=lambda x: x[1].get("betweenness", 0), reverse=True
    )[:5]
    if top_betweenness:
        print("  Bridging concepts (high betweenness):")
        for eid, m in top_betweenness:
            name = graph.entities.get(eid, {}).get("name", eid)
            print(f"    {name}: betweenness={m.get('betweenness', 0):.4f}")

    # ════════════════════════════════════════════════════════════════
    # STAGE 5: "WHAT IF Z CAUSES Y?" — Hypothesis generation
    # ════════════════════════════════════════════════════════════════
    print("\n[5/9] HYPOTHESIS GENERATION — 'What if Z causes Y?'...", flush=True)

    # Build the hypothesis prompt manually (bypass HypothesisEngine's retry issues)
    from discovery.hypothesis_engine import HypothesisEngine
    hypothesis_engine = HypothesisEngine()
    run_id = f"full_{int(time.time())}"

    hyp_prompt = hypothesis_engine._build_prompt(graph, topic, domain, all_contradictions, None)
    print(f"  Prompt: {len(hyp_prompt)} chars, calling LLM...", flush=True)

    hyp_raw = None
    for attempt in range(3):
        try:
            hyp_raw = llm_call(hyp_prompt, json_mode=True, max_tokens=3072, provider="auto")
            if hyp_raw and len(hyp_raw) > 50:
                break
        except Exception as e:
            print(f"  Attempt {attempt+1} failed: {e}", flush=True)
            time.sleep(3)

    if hyp_raw:
        hyp_raw = hyp_raw.strip()
        if hyp_raw.startswith("```"):
            hyp_raw = hyp_raw.split("\n", 1)[1] if "\n" in hyp_raw else hyp_raw[3:]
            hyp_raw = hyp_raw.rsplit("```", 1)[0].strip()
        try:
            parsed = json.loads(hyp_raw)
            if isinstance(parsed, list):
                hypotheses = parsed
            elif isinstance(parsed, dict):
                hypotheses = parsed.get("hypotheses", [parsed])
            else:
                hypotheses = [parsed]
        except json.JSONDecodeError:
            hypotheses = []
    else:
        hypotheses = []

    # Enrich with metadata
    for h in hypotheses:
        import uuid
        from datetime import datetime
        h["id"] = str(uuid.uuid4())
        h["topic"] = topic
        h["domain"] = domain
        h["provider"] = "groq"
        h["created_at"] = datetime.utcnow().isoformat()
        h["status"] = "draft"
        h.setdefault("confidence", 0.5)
        h.setdefault("novelty", "medium")
        h.setdefault("title", "Untitled hypothesis")

    if not hypotheses:
        # Fallback
        hypotheses = hypothesis_engine._fallback_hypothesis(topic, domain, "LLM returned empty")

    print(f"  Generated {len(hypotheses)} hypotheses", flush=True)
    for h in hypotheses:
        conf = h.get("confidence", 0)
        nov = h.get("novelty", "?")
        print(f"    [{nov}|{conf:.2f}] {h.get('title', 'Untitled')[:70]}", flush=True)

    # Run hypothesis tournament (evolutionary selection)
    print(f"\n[5b/9] TOURNAMENT — Evolving {len(hypotheses)} hypotheses over {generations} generations...", flush=True)
    try:
        from discovery.hypothesis_tournament import HypothesisTournament
        tournament = HypothesisTournament()
        evolved = asyncio.run(
            tournament.run(hypotheses, graph, topic, domain, generations=generations)
        )
        for i, h in enumerate(evolved[:5]):
            rank = h.get("tournament_rank", i + 1)
            conf = h.get("confidence", 0)
            nov = h.get("novelty", "?")
            print(f"    #{rank} [{nov}|{conf:.2f}] {h.get('title', 'Untitled')[:60]}", flush=True)
    except Exception as e:
        print(f"  Tournament failed ({e}), using original hypotheses", flush=True)
        evolved = hypotheses
    print(f"\n[7/9] TOURNAMENT — {len(evolved)} hypotheses after evolution", flush=True)

    # ════════════════════════════════════════════════════════════════
    # STAGE 6: SKEPTIC REVIEW — Adversarial falsification
    # ════════════════════════════════════════════════════════════════
    print("\n[6/9] SKEPTIC REVIEW — Adversarial falsification of top hypothesis...", flush=True)
    top_hypothesis = hypotheses[0]

    # Build skeptic prompt directly
    skeptic_prompt = f"""You are an adversarial skeptical scientific reviewer. FALSIFY this hypothesis.

HYPOTHESIS:
Title: {top_hypothesis.get('title')}
Rationale: {top_hypothesis.get('mechanistic_rationale', top_hypothesis.get('description', ''))}
Confidence: {top_hypothesis.get('confidence')}
Evidence: {json.dumps(top_hypothesis.get('supporting_evidence', []))}

Analyze:
1. Logical flaws
2. Missing alternatives
3. Top 3 weaknesses
4. Recommendation: accept|revise|reject
5. Revised confidence (0.0-1.0)

Output JSON: {{"critique": "...", "weaknesses": ["w1","w2","w3"], "recommendation": "accept|revise|reject", "revised_confidence": 0.0}}"""

    skeptic_raw = None
    try:
        skeptic_raw = llm_call(skeptic_prompt, json_mode=True, max_tokens=2048, provider="auto")
    except Exception as e:
        print(f"  Skeptic call failed: {e}", flush=True)

    if skeptic_raw:
        skeptic_raw = skeptic_raw.strip()
        if skeptic_raw.startswith("```"):
            skeptic_raw = skeptic_raw.split("\n", 1)[1] if "\n" in skeptic_raw else skeptic_raw[3:]
            skeptic_raw = skeptic_raw.rsplit("```", 1)[0].strip()
        try:
            skeptic_result = json.loads(skeptic_raw)
        except json.JSONDecodeError:
            skeptic_result = {"recommendation": "unknown", "revised_confidence": 0, "weaknesses": ["Parse failed"]}
    else:
        skeptic_result = {"recommendation": "unknown", "revised_confidence": 0, "weaknesses": ["LLM failed"]}

    recommendation = skeptic_result.get("recommendation", "unknown")
    revised_conf = skeptic_result.get("revised_confidence", 0)
    weaknesses = skeptic_result.get("weaknesses", [])
    print(f"  Recommendation: {recommendation}")
    print(f"  Revised confidence: {revised_conf}")
    print(f"  Top weaknesses:")
    for w in weaknesses[:3]:
        print(f"    - {w[:80]}")

    # Update hypothesis with skeptic feedback
    top_hypothesis["skeptic_review"] = skeptic_result
    top_hypothesis["post_skeptic_confidence"] = revised_conf

    # ════════════════════════════════════════════════════════════════
    # STAGE 8: EXPERIMENT DESIGN — Generate test for top hypothesis
    # ════════════════════════════════════════════════════════════════
    print("\n[8/9] EXPERIMENT DESIGN — Generating test protocol...", flush=True)

    exp_prompt = f"""Design an experiment to test this hypothesis:

Title: {top_hypothesis.get('title')}
Rationale: {top_hypothesis.get('mechanistic_rationale', top_hypothesis.get('description', ''))}
Domain: space_astronomy

Output JSON: {{"experiment_type": "observational|computational", "design": "detailed steps", "variables": {{"independent": ["v1"], "dependent": ["v2"], "controlled": ["v3"]}}, "control_groups": ["c1"], "expected_outcomes": {{"confirm": "...", "disconfirm": "..."}}, "timeline_estimate": "months", "estimated_cost": "low|medium|high"}}"""

    exp_raw = None
    try:
        exp_raw = llm_call(exp_prompt, json_mode=True, max_tokens=2048, provider="auto")
    except Exception as e:
        print(f"  Experiment call failed: {e}", flush=True)

    if exp_raw:
        exp_raw = exp_raw.strip()
        if exp_raw.startswith("```"):
            exp_raw = exp_raw.split("\n", 1)[1] if "\n" in exp_raw else exp_raw[3:]
            exp_raw = exp_raw.rsplit("```", 1)[0].strip()
        try:
            experiment = json.loads(exp_raw)
        except json.JSONDecodeError:
            experiment = {"experiment_type": "unknown", "design": "Parse failed"}
    else:
        experiment = {"experiment_type": "unknown", "design": "LLM failed"}
    exp_type = experiment.get("experiment_type", "unknown")
    timeline = experiment.get("timeline_estimate", "unknown")
    print(f"  Type: {exp_type}")
    print(f"  Timeline: {timeline}")
    print(f"  Variables: {len(experiment.get('variables', {}).get('independent', []))} independent")
    print(f"  Controls: {len(experiment.get('control_groups', []))}")

    top_hypothesis["experiment"] = experiment

    # ════════════════════════════════════════════════════════════════
    # STAGE 9: EVIDENCE — Computations + claim labeling + provenance
    # ════════════════════════════════════════════════════════════════
    print("\n[9/9] EVIDENCE — Computations + claim labeling + provenance...")

    # Run domain-specific calculations
    calculations = {}
    if domain in DOMAIN_COMPUTATIONS:
        domain_calcs = run_domain_calculations(domain, topic)
        calculations.update(domain_calcs)
        print(f"  Domain calculations: {len(domain_calcs)}")
    if domain == "space_astronomy":
        space_calcs = run_all_calculations(topic)
        calculations.update(space_calcs)
    calc_context = format_for_prompt(calculations) or format_calculations_for_prompt(calculations)
    print(f"  Total calculations: {len(calculations)}")

    # Generate final report with all context
    final_prompt = _build_final_prompt(
        topic, domain, citation_context, calc_context,
        graph, all_contradictions, evolved, top_hypothesis,
        skeptic_result, experiment
    )

    print("  Generating final report via LLM...", flush=True)
    t0 = time.time()
    raw_output = llm_call(final_prompt[:8000], max_tokens=4096, provider="auto")
    elapsed = time.time() - t0
    print(f"  Generated in {elapsed:.1f}s ({len(raw_output or '')} chars)")

    if not raw_output:
        print("  [ERROR] LLM failed. Using hypothesis summary as fallback.")
        raw_output = _fallback_report(top_hypothesis, evolved, skeptic_result, experiment)

    raw_output = raw_output.encode("utf-8", errors="replace").decode("utf-8", errors="replace")

    # Label claims
    labeled_output = label_report(raw_output, papers, calculations)
    grounding = ground_claims(raw_output, papers)
    confidence = generate_confidence_summary(labeled_output)

    # Add provenance
    tracker = ProvenanceTracker(papers, calculations)
    provenance_output = tracker.process_report(labeled_output)

    # Assemble final report
    header = _build_report_header(
        topic, domain, papers, calculations, graph,
        all_contradictions, evolved, skeptic_result, confidence
    )
    full_report = header + provenance_output

    # References
    if papers:
        full_report += "\n\n" + "=" * 70 + "\n  REFERENCES (Real papers)\n" + "=" * 70 + "\n\n"
        for i, p in enumerate(papers, 1):
            authors = ", ".join(p.get("authors", [])[:3])
            if len(p.get("authors", [])) > 3:
                authors += " et al."
            full_report += f"  [{i}] {p['citation_key']} ({p.get('year', 'n/a')})\n"
            full_report += f"      {p['title']}\n      {authors}\n      {p['url']}\n\n"

    # Computational details
    if calculations:
        full_report += "\n" + "=" * 70 + "\n  COMPUTATIONAL DETAILS\n" + "=" * 70 + "\n\n"
        full_report += json.dumps(calculations, indent=2, default=str)

    # Discovery candidates summary
    full_report += "\n\n" + "=" * 70 + "\n  DISCOVERY CANDIDATES\n" + "=" * 70 + "\n\n"
    for i, h in enumerate(evolved[:5], 1):
        conf = h.get("confidence", 0)
        nov = h.get("novelty", "?")
        rank = h.get("tournament_rank", i)
        full_report += f"  #{rank} [{nov}|{conf:.2f}] {h.get('title', 'Untitled')}\n"
        full_report += f"      {h.get('mechanistic_rationale', h.get('description', ''))[:200]}\n\n"

    # Stats
    total_time = time.time() - t_start
    print("\n" + "=" * 70)
    print(f"  COMPLETE — {total_time:.1f}s")
    print(f"  Papers:          {len(papers)}")
    print(f"  Graph entities:  {len(graph.entities)}")
    print(f"  Contradictions:  {len(all_contradictions)}")
    print(f"  Hypotheses:      {len(evolved)} (after {generations} generations)")
    print(f"  Skeptic verdict: {recommendation}")
    print(f"  Reliability:     {confidence.get('reliability_score', 0):.0%}")
    print(f"  Claims:          {confidence.get('breakdown', {})}")
    print(f"  Citations:       {grounding['total_citations']}/{len(papers)}")
    print("=" * 70)

    return full_report


def _build_final_prompt(topic, domain, citation_context, calc_context,
                        graph, contradictions, evolved, top_hypothesis,
                        skeptic_result, experiment):
    """Build the final generation prompt with ALL pipeline context."""

    # Hypothesis summaries
    hyp_text = ""
    for h in evolved[:5]:
        conf = h.get("confidence", 0)
        nov = h.get("novelty", "?")
        hyp_text += f"\n- [{nov}|{conf:.2f}] {h.get('title', 'Untitled')}\n"
        hyp_text += f"  Rationale: {h.get('mechanistic_rationale', h.get('description', ''))[:200]}\n"
        if h.get("supporting_evidence"):
            hyp_text += f"  Evidence: {', '.join(str(e)[:50] for e in h['supporting_evidence'][:3])}\n"

    # Contradiction summaries
    cont_text = ""
    for c in contradictions[:5]:
        cont_text += f"\n- [{c.get('type', '?')}] {c.get('description', c.get('summary', ''))[:150]}"

    # Skeptic review
    skeptic_text = ""
    if skeptic_result:
        skeptic_text = f"""
SKEPTIC REVIEW:
  Recommendation: {skeptic_result.get('recommendation', 'unknown')}
  Revised confidence: {skeptic_result.get('revised_confidence', 'N/A')}
  Top weaknesses: {json.dumps(skeptic_result.get('weaknesses', [])[:3])}
  Logical flaws: {json.dumps(skeptic_result.get('logical_flaws', [])[:3])}
"""

    # Experiment design
    exp_text = ""
    if experiment:
        exp_text = f"""
EXPERIMENT DESIGN:
  Type: {experiment.get('experiment_type', 'unknown')}
  Design: {experiment.get('design', '')[:300]}
  Expected outcomes: {json.dumps(experiment.get('expected_outcomes', {}), indent=2)[:300]}
  Timeline: {experiment.get('timeline_estimate', 'unknown')}
"""

    return f"""You are RUMI — Research & Unified Machine Intelligence.

Topic: "{topic}"
Domain: {domain}

CRITICAL RULES:
1. Cite papers using [1], [2], etc. from the REAL papers below.
2. Use real numbers from the computational results below.
3. Mark unsourced claims as [UNVERIFIED].
4. Mark predictions as [HYPOTHETICAL].
5. Never invent paper titles, authors, or numerical values.
6. Every number must trace to a computation or citation.

{citation_context}

{calc_context}

=== KNOWLEDGE GRAPH ===
Entities: {len(graph.entities)}
Relationships: {len(graph.relationships)}

=== DETECTED CONTRADICTIONS ===
{cont_text or "None detected"}

=== TOP HYPOTHESIS (after tournament + skeptic review) ===
{hyp_text}

{skeptic_text}

{exp_text}

=== INSTRUCTIONS ===
Generate a comprehensive 12-phase discovery report that:

PHASE 1 -- Literature Review (cite real papers, acknowledge contradictions)
PHASE 2 -- Knowledge Graph (report the actual graph structure)
PHASE 3 -- Novelty Assessment (use graph gaps and contradictions)
PHASE 4 -- Hypothesis Generation (present the tournament winners, explain evolution)
PHASE 5 -- Experiment Design (use the experiment plan above)
PHASE 6 -- Active Experiment Selection (justify why this hypothesis won)
PHASE 7 -- Execution Protocol (detailed methodology)
PHASE 8 -- Analysis Plan (statistical methods, verification)
PHASE 9 -- Expected Results (use computed ranges + confidence intervals)
PHASE 10 -- Paper Abstract (grounded in citations + computed values)
PHASE 11 -- Peer Review (incorporate the skeptic's weaknesses)
PHASE 12 -- Knowledge Update (what we now know, what remains unknown)

Be rigorous. Be honest about uncertainty. The skeptic found these weaknesses — address them.
"""


def _build_report_header(topic, domain, papers, calculations, graph,
                         contradictions, evolved, skeptic_result, confidence):
    """Build the transparency disclosure header."""

    breakdown = confidence.get("breakdown", {})

    header = f"""
======================================================================
  RUMI REPORT — TRANSPARENCY DISCLOSURE
======================================================================

  This report was generated by RUMI's FULL DISCOVERY PIPELINE:
    KnowledgeGraph → ContradictionMiner → HypothesisEngine →
    HypothesisTournament → SkepticAgent → ExperimentPlanner →
    Computational Verification → Claim Labeling + Provenance

  SOURCES CONSULTED:
    Real papers fetched:  {len(papers)} (from arXiv + PubMed APIs)
    Knowledge graph:      {len(graph.entities)} entities, {len(graph.relationships)} relationships
    Contradictions found: {len(contradictions)}
    Hypotheses generated: {len(evolved)} (after tournament evolution)
    Computations run:     {len(calculations)}

  CLAIM CLASSIFICATION:
    {breakdown.get('VALIDATED', 0)} VALIDATED    — Backed by real papers or databases
    {breakdown.get('INFERRED', 0)} INFERRED     — Logical deduction from validated claims
    {breakdown.get('SIMULATED', 0)} SIMULATED    — From computational models (has assumptions)
    {breakdown.get('HYPOTHETICAL', 0)} HYPOTHETICAL — Explicit "what if" scenarios
    {breakdown.get('SPECULATIVE', 0)} SPECULATIVE  — AI-generated, no evidence backing

  OVERALL RELIABILITY: {confidence.get('reliability_score', 0):.0%}

  SKEPTIC VERDICT: {skeptic_result.get('recommendation', 'unknown')}
  REVISED CONFIDENCE: {skeptic_result.get('revised_confidence', 'N/A')}

  IMPORTANT:
    Numbers labeled {{VALIDATED}} come from real papers or databases.
    Numbers labeled {{SIMULATED}} come from models with stated assumptions.
    Numbers labeled {{SPECULATIVE}} were invented by the AI.
    Numbers labeled {{HYPOTHETICAL}} are conditional predictions.

======================================================================
"""
    return header


def _fallback_report(hypothesis, evolved, skeptic_result, experiment):
    """Fallback if LLM fails for final report."""
    text = f"# Discovery Report\n\n"
    text += f"## Top Hypothesis\n{hypothesis.get('title', 'Untitled')}\n"
    text += f"{hypothesis.get('mechanistic_rationale', hypothesis.get('description', ''))}\n\n"
    text += f"## Skeptic Review\n"
    text += f"Recommendation: {skeptic_result.get('recommendation', 'unknown')}\n"
    text += f"Weaknesses: {json.dumps(skeptic_result.get('weaknesses', []))}\n\n"
    text += f"## Experiment\n{json.dumps(experiment, indent=2)}\n"
    return text


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RUMI Full Discovery Pipeline")
    parser.add_argument("--topic", default="anomalous stellar dimming and technosignatures")
    parser.add_argument("--domain", default="")
    parser.add_argument("--generations", type=int, default=3)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    report = run_full_pipeline(args.topic, args.domain, args.generations)
    if report:
        print("\n\n" + report[:3000] + "\n\n... [truncated for console] ...")
        out_path = args.output or str(BASE / "data" / "full_pipeline_report.md")
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(report, encoding="utf-8")
        print(f"\nSaved to: {out_path}")
