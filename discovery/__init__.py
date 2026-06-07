"""
# Fix Unicode encoding on Windows (cp1252 can't handle scientific symbols like ≥, →, ↔, ‑)
import sys as _sys
if _sys.platform == "win32":
    try:
        _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RUMI Discovery Engine — Autonomous Scientific Discovery Pipeline

Modules:
- pubmed, arxiv_api, semantic_scholar, openalex_api: Literature search
- graph: Knowledge graph
- hypothesis_engine, hypothesis_memory: Hypothesis generation and tracking
- contradiction_miner: Find contradictions in literature
- skeptic_agent: Critical review of hypotheses
- novelty_detector: Check if hypotheses are novel
- experiment_planner: Design experiments
- hypothesis_tournament: Evolutionary hypothesis refinement
- retrieval_filter: Semantic relevance filtering
- pipeline: Main discovery pipeline orchestration
- domains: Domain-specific entity types and configurations

NEW (v2.1):
- domain_ontologies: Real physics/biology/chemistry ontologies for 17 domains
- math_consistency_checker: Verify theories are mathematically sound
- simulation_pipeline: Monte Carlo simulation to test hypotheses
- multi_agent_debate: Multiple AI agents debate a hypothesis
- cross_domain_transfer: Apply discoveries across scientific domains
- continuous_operation: Autonomous continuous research loop
"""
