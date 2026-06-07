"""
discovery_enhancer.py — Post-pipeline enhancement layer.

Runs AFTER the existing discovery_pipeline_v2 to add:
1. Novelty checking (is this actually new?)
2. Falsification (can we kill this theory?)
3. Scientific simulation (run the actual math)
4. Bayesian scoring (proper probability, not arbitrary confidence)
5. Literature contradiction scoring (support vs reject)
6. Discovery tournament (evolutionary selection)

This APPENDS to RUMI's existing pipeline without modifying it.
"""

import json
import time
from typing import Dict, List, Optional


def enhance_discovery(pipeline_result: dict, topic: str, domain: str,
                      papers: list = None, graph=None) -> dict:
    """
    Enhance a discovery pipeline result with additional analysis layers.

    Args:
        pipeline_result: Output from run_discovery_pipeline()
        topic: Research topic
        domain: Research domain
        papers: Papers from the pipeline
        graph: Knowledge graph from the pipeline

    Returns:
        Enhanced result with new analysis layers added
    """
    t_start = time.time()
    phases = pipeline_result.get("phases", {})
    errors = pipeline_result.get("errors", [])

    # Extract what we need from the pipeline
    hidden_variables = phases.get("missing_variables", {}).get("variables", [])
    mechanisms = phases.get("mechanism_generation", {}).get("mechanisms_generated", [])
    predictions = phases.get("prediction_engine", {}).get("total_predictions", 0)

    # Get the actual theory data from the saved report
    theories = _extract_theories_from_report(pipeline_result)
    gaps = _extract_gaps_from_report(pipeline_result)
    anomalies = _extract_anomalies_from_report(pipeline_result)

    # If no theories exist, generate a basic one from gaps/anomalies
    if not theories and (gaps or anomalies):
        print("  No theories from pipeline — generating from gaps/anomalies...", flush=True)
        try:
            from discovery.resilient_llm import ResilientLLM
            resilient = ResilientLLM()
            gap_text = "\n".join(f"- {g.get('reason', g.get('description', ''))[:150]}" for g in gaps[:5])
            anomaly_text = "\n".join(f"- {a.get('reason', a.get('observation', ''))[:150]}" for a in anomalies[:5])
            prompt = f"""Based on these knowledge gaps and anomalies, propose one scientific theory.

TOPIC: {topic}
DOMAIN: {domain}

GAPS:
{gap_text}

ANOMALIES:
{anomaly_text}

Output JSON:
{{"name": "theory name", "type": "proposed", "description": "description with equations",
  "key_parameters": [{{"name": "p", "expected_value": "v", "units": "u"}}],
  "predictions": ["prediction with numbers"],
  "literature_basis": ["related concept"],
  "is_novel_vs_known": "extension_of_known"}}"""

            result = resilient.call_json(prompt, max_tokens=4096)
            if result and isinstance(result, dict):
                theories = [result]
                print(f"  Generated theory: {result.get('name', '?')}", flush=True)
        except Exception as e:
            print(f"  Theory generation failed: {e}", flush=True)

    enhancement = {
        "novelty_check": {},
        "falsification": {},
        "scientific_simulation": {},
        "bayesian_scoring": {},
        "literature_contradiction": {},
        "discovery_tournament": {},
    }

    # ══════════════════════════════════════════════════════════════
    # ENHANCEMENT 1: NOVELTY CHECK
    # ══════════════════════════════════════════════════════════════
    print("\n[Enhancement 1/6] NOVELTY CHECK — Is this actually new?", flush=True)
    try:
        from discovery.novelty_checker import NoveltyChecker
        from discovery.resilient_llm import ResilientLLM

        resilient = ResilientLLM()
        novelty_checker = NoveltyChecker(llm_call=resilient.call_json)

        if theories:
            top_theory = theories[0]
            # Ensure top_theory is a dict
            if isinstance(top_theory, str):
                top_theory = {"name": top_theory, "type": "proposed", "description": top_theory}
            novelty_result = novelty_checker.check_novelty(top_theory, papers or [], topic, domain)
            enhancement["novelty_check"] = novelty_result
            print(f"  Verdict: {novelty_result.get('novelty_verdict', '?')} "
                  f"(score: {novelty_result.get('novelty_score', 0):.2f})")
            print(f"  Novel: {novelty_result.get('what_is_novel', '?')[:80]}")
            print(f"  Known: {novelty_result.get('what_is_known', '?')[:80]}")
    except Exception as e:
        import traceback
        print(f"  [ERROR] Novelty check failed: {e}")
        print(f"  [DEBUG] {traceback.format_exc()[-300:]}", flush=True)
        errors.append(f"Enhancement novelty: {e}")

    # ══════════════════════════════════════════════════════════════
    # ENHANCEMENT 2: FALSIFICATION ENGINE
    # ══════════════════════════════════════════════════════════════
    print("\n[Enhancement 2/6] FALSIFICATION — Can we kill this theory?", flush=True)
    try:
        from discovery.falsification_engine import FalsificationEngine
        from discovery.resilient_llm import ResilientLLM

        resilient = ResilientLLM()
        falsifier = FalsificationEngine(llm_call=resilient.call_json)

        if theories:
            t = theories[0] if isinstance(theories[0], dict) else {"name": str(theories[0]), "type": "proposed", "description": str(theories[0])}
            falsification_result = falsifier.falsify(t, papers or [], domain)
            enhancement["falsification"] = falsification_result
            print(f"  Constraints checked: {len(falsification_result.get('constraints_checked', []))}")
            print(f"  Counterfactuals: {len(falsification_result.get('counterfactual_tests', []))}")
            print(f"  Kill attempts: {len(falsification_result.get('kill_attempts', []))}")
            print(f"  Survival score: {falsification_result.get('survival_score', 0):.2f}")
            print(f"  Verdict: {falsification_result.get('falsification_verdict', '?')}")
            print(f"  Weakest point: {falsification_result.get('weakest_point', '?')[:80]}")
    except Exception as e:
        import traceback
        print(f"  [ERROR] Falsification failed: {e}")
        print(f"  [DEBUG] {traceback.format_exc()[-300:]}", flush=True)
        errors.append(f"Enhancement falsification: {e}")

    # ══════════════════════════════════════════════════════════════
    # ENHANCEMENT 3: SCIENTIFIC SIMULATION + COUNTERFACTUAL REASONING
    # ══════════════════════════════════════════════════════════════
    print("\n[Enhancement 3/6] SIMULATION + COUNTERFACTUAL — Running the math", flush=True)
    try:
        from discovery.scientific_simulator import ScientificSimulator
        from discovery.counterfactual_reasoner import CounterfactualReasoner
        from discovery.resilient_llm import ResilientLLM

        # Scientific simulation
        simulator = ScientificSimulator()
        safe_theories = [t if isinstance(t, dict) else {"name": str(t), "type": "proposed"} for t in theories]
        sim_result = simulator.simulate(safe_theories, [], [], topic, domain)
        enhancement["scientific_simulation"] = sim_result
        summary = sim_result.get("summary", {})
        print(f"  Tools used: {summary.get('tools_used', [])}")
        print(f"  Equations solved: {summary.get('equations_solved', 0)}")
        print(f"  Parameters swept: {summary.get('parameters_swept', 0)}")
        print(f"  Observables computed: {summary.get('observables_computed', 0)}")
        for obs in sim_result.get("observables", []):
            print(f"    → {obs.get('finding', '')[:80]}")

        # Counterfactual reasoning
        resilient = ResilientLLM()
        counterfactual = CounterfactualReasoner(llm_call=resilient.call_json)
        if theories:
            t = theories[0] if isinstance(theories[0], dict) else {"name": str(theories[0]), "type": "proposed"}
            cf_result = counterfactual.reason(t, domain)
            enhancement["counterfactual_reasoning"] = cf_result
            print(f"  Counterfactuals derived: {cf_result.get('total_derived', 0)}")
            print(f"  Supported: {len(cf_result.get('supported', []))}")
            print(f"  Contradicted: {len(cf_result.get('contradicted', []))}")
            print(f"  Unknown: {len(cf_result.get('unknown', []))}")
            print(f"  Overall consistency: {cf_result.get('overall_consistency', 0):.2f}")
            for c in cf_result.get("contradicted", []):
                print(f"    ⚠ CONTRADICTED: {c.get('consequence', '')[:80]}")
    except Exception as e:
        print(f"  [ERROR] Simulation/counterfactual failed: {e}")
        errors.append(f"Enhancement simulation: {e}")

    # ══════════════════════════════════════════════════════════════
    # ENHANCEMENT 4: BAYESIAN SCORING
    # ══════════════════════════════════════════════════════════════
    print("\n[Enhancement 4/6] BAYESIAN SCORING — Proper probability", flush=True)
    try:
        from discovery.bayesian_scorer import BayesianScorer

        bayesian = BayesianScorer()
        if theories:
            t = theories[0] if isinstance(theories[0], dict) else {"name": str(theories[0]), "type": "proposed"}
            bayesian_result = bayesian.score(t, papers, [], graph)
            enhancement["bayesian_scoring"] = bayesian_result
            print(f"  Prior: {bayesian_result.get('prior', 0):.4f}")
            print(f"  Likelihood: {bayesian_result.get('likelihood', 0):.4f}")
            print(f"  Posterior: {bayesian_result.get('posterior', 0):.4f}")
            print(f"  Bayes factor: {bayesian_result.get('bayes_factor', 0):.1f}")
            print(f"  Interpretation: {bayesian_result.get('interpretation', '?')}")
    except Exception as e:
        print(f"  [ERROR] Bayesian scoring failed: {e}")
        errors.append(f"Enhancement bayesian: {e}")

    # ══════════════════════════════════════════════════════════════
    # ENHANCEMENT 5: LITERATURE CONTRADICTION SCORING
    # ══════════════════════════════════════════════════════════════
    print("\n[Enhancement 5/6] LITERATURE CONTRADICTION — Support vs reject", flush=True)
    try:
        from discovery.literature_contradiction_scorer import LiteratureContradictionScorer
        from discovery.resilient_llm import ResilientLLM

        resilient = ResilientLLM()
        lit_scorer = LiteratureContradictionScorer(graph=graph, llm_call=resilient.call_json)

        if theories:
            lit_result = lit_scorer.score(theories[0], papers)
            enhancement["literature_contradiction"] = lit_result
            print(f"  Supporting papers: {len(lit_result.get('supporting_papers', []))}")
            print(f"  Contradicting papers: {len(lit_result.get('contradicting_papers', []))}")
            print(f"  Net alignment: {lit_result.get('net_alignment', 0):.3f}")
            print(f"  Verdict: {lit_result.get('literature_verdict', '?')}")
    except Exception as e:
        print(f"  [ERROR] Literature contradiction failed: {e}")
        errors.append(f"Enhancement lit_contradiction: {e}")

    # ══════════════════════════════════════════════════════════════
    # ENHANCEMENT 6: DISCOVERY TOURNAMENT
    # ══════════════════════════════════════════════════════════════
    print("\n[Enhancement 6/6] DISCOVERY TOURNAMENT — Evolutionary selection", flush=True)
    try:
        from discovery.discovery_tournament import DiscoveryTournament
        from discovery.resilient_llm import ResilientLLM

        resilient = ResilientLLM()
        tournament = DiscoveryTournament(llm_call=resilient.call_json)

        # Normalize theory format for tournament
        seed_hypotheses = []
        for t in (theories or []):
            if not isinstance(t, dict):
                t = {"name": str(t), "type": "proposed", "description": str(t)}
            # Ensure required fields exist
            t.setdefault("name", t.get("title", "Unnamed"))
            t.setdefault("description", t.get("mechanistic_rationale", t.get("mechanism", "")))
            t.setdefault("type", t.get("pattern_type", "proposed"))
            t.setdefault("predictions", [])
            t.setdefault("steps", t.get("causal_chain", []))
            t.setdefault("explains", t.get("supporting_evidence", []))
            t.setdefault("fails_to_explain", t.get("contradictory_evidence", []))
            t.setdefault("key_assumptions", [])
            if t.get("name") and t.get("description"):
                seed_hypotheses.append(t)
        if seed_hypotheses:
            tournament_result = tournament.run(
                seed_hypotheses, topic, domain,
                generations=2, population_size=5,
                papers=papers, graph=graph
            )
            enhancement["discovery_tournament"] = tournament_result
            stats = tournament_result.get("tournament_stats", {})
            print(f"  Generations run: {stats.get('generations_run', 0)}")
            print(f"  Final population: {stats.get('final_population', 0)}")
            print(f"  Winner: {stats.get('winner_name', '?')}")
            print(f"  Winner score: {stats.get('winner_score', 0):.2f}")
    except Exception as e:
        print(f"  [ERROR] Tournament failed: {e}")
        errors.append(f"Enhancement tournament: {e}")

    # Merge enhancements into pipeline result
    elapsed = time.time() - t_start
    enhancement["enhancement_duration"] = round(elapsed, 1)
    pipeline_result["enhancements"] = enhancement
    pipeline_result["errors"] = errors

    print(f"\n  Enhancements complete in {elapsed:.1f}s", flush=True)

    return pipeline_result


def _extract_theories_from_report(result: dict) -> list:
    """Extract theory data from pipeline result."""
    # Try to get all theories from theory competition phase
    comp = result.get("phases", {}).get("theory_competition", {})
    theories = comp.get("theories", [])
    if theories:
        # Normalize each theory
        normalized = []
        for t in theories:
            if not isinstance(t, dict):
                continue
            t.setdefault("name", t.get("title", "Unnamed"))
            t.setdefault("description", t.get("mechanistic_rationale", t.get("mechanism", "")))
            t.setdefault("type", t.get("pattern_type", "proposed"))
            t.setdefault("predictions", [])
            t.setdefault("key_parameters", [])
            t.setdefault("steps", t.get("causal_chain", []))
            t.setdefault("explains", t.get("supporting_evidence", []))
            t.setdefault("fails_to_explain", t.get("contradictory_evidence", []))
            t.setdefault("key_assumptions", [])
            normalized.append(t)
        return normalized

    # Try winner only
    winner = comp.get("winner")
    if winner and isinstance(winner, dict):
        return [winner]

    # Try to get from mechanism generation
    mech = result.get("phases", {}).get("mechanism_generation", {})
    mechanisms = mech.get("mechanisms_generated", 0)
    if mechanisms > 0:
        return [{
            "name": "Primary theory",
            "type": "proposed",
            "description": "Theory from mechanism generation phase",
            "predictions": [],
            "key_parameters": [],
        }]

    return []


def _extract_gaps_from_report(result: dict) -> list:
    """Extract gap data from pipeline result."""
    gaps = result.get("phases", {}).get("gap_detection", {})
    return gaps.get("top_gaps", [])


def _extract_anomalies_from_report(result: dict) -> list:
    """Extract anomaly data from pipeline result."""
    anomalies = result.get("phases", {}).get("anomaly_detection", {})
    return anomalies.get("top_anomalies", [])
