"""
run_discovery.py — Full RUMI Discovery Runner

Matches the interactive RUMI terminal flow:
  1. Discovery Pipeline v2 (16 phases)
  2. Refinement Pipeline (13 stages)  
  3. Reflexion (self-improvement)

Usage:
    python run_discovery.py "your topic here"
    python run_discovery.py "your topic" --domain space_astronomy
    python run_discovery.py "your topic" --mode quick
"""

import sys
import os
import json
import time
import socket
from pathlib import Path

# Global network timeout — prevents DNS hangs from blocking the pipeline indefinitely
# Covers DNS resolution + connection + read (urllib.request.urlopen respects this)
socket.setdefaulttimeout(30)

# Fix Unicode encoding on Windows (cp1252 can't handle scientific symbols)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RUMI Full Discovery Runner")
    parser.add_argument("topic", nargs="?", default="", help="Research topic")
    parser.add_argument("--cause", default="", help="Simple observation/question (e.g. 'Why did the apple fall?')")
    parser.add_argument("--domain", default="", help="Domain override (e.g. space_astronomy, physics)")
    parser.add_argument("--mode", default="full", choices=["quick", "standard", "full"], help="Pipeline depth")
    parser.add_argument("--iterate", action="store_true", help="Run twice: first pass, analyze weaknesses, second pass with refined context")
    args = parser.parse_args()

    cause = args.cause
    topic = args.topic
    domain = args.domain
    mode = args.mode

    # ── CAUSE MODE: Transform observation into research topic ──
    cause_data = None
    if cause:
        print(f"{'='*70}")
        print(f"RUMI CAUSE MODE — The Newton Step")
        print(f"{'='*70}")
        print(f"  Observation: {cause}")
        print()

        # Step 1: Use curious questioning to transform cause into topic
        try:
            from discovery.curious_questioning import CuriousQuestioning
            from discovery.llm_client import call_json as llm_call
            cq = CuriousQuestioning(llm_call=llm_call)
            cause_data = cq.run(cause, domain, papers=[])

            core_question = cause_data.get("reframed", "")
            hypothesis = cause_data.get("question_hypothesis", "")
            questions = cause_data.get("questions", [])

            print(f"  [Curious Engine] Questions generated: {len(questions)}")
            if core_question:
                print(f"  [Curious Engine] Core Question: {core_question[:100]}")
            if hypothesis:
                print(f"  [Curious Engine] Hypothesis: {hypothesis[:100]}")
            print()

            # Step 2: Transform into a research topic
            # Use the core question as the topic, or generate one from the cause
            if core_question and len(core_question) > 20:
                topic = core_question
            elif hypothesis and len(hypothesis) > 20:
                topic = hypothesis[:200]
            else:
                # Fallback: use the cause as the topic
                topic = cause

            # Auto-detect domain if not specified
            if not domain:
                from discovery.discovery_pipeline_v2 import detect_domain
                domain = detect_domain(topic)
                print(f"  [Auto-Detect] Domain: {domain}")

            print(f"  [Topic Generated] {topic[:100]}")
            print()

        except Exception as e:
            print(f"  [WARN] Curious engine failed: {e}")
            topic = cause  # Use cause directly as topic

    # Validate we have a topic
    if not topic:
        parser.error("Please provide a topic or --cause observation")

    print(f"{'='*70}")
    print(f"RUMI DISCOVERY — {topic}")
    print(f"Domain: {domain or 'auto-detect'} | Mode: {mode}")
    print(f"{'='*70}\n")

    report = {}
    total_start = time.time()

    # ── Iterative refinement mode ──
    if args.iterate:
        print("="*70)
        print("ITERATIVE MODE: First pass → Analyze → Second pass → Merge")
        print("="*70)

        # First pass
        print("\n  [Pass 1/2] Running initial discovery...")
        try:
            from discovery.discovery_pipeline_v2 import run_discovery_pipeline
            report_pass1 = run_discovery_pipeline(topic, domain=domain, mode=mode)
        except Exception as e:
            print(f"  Pass 1 failed: {e}")
            report_pass1 = {}

        # Analyze weaknesses
        print("\n  [Analyzing weaknesses from pass 1...]")
        p1_phases = report_pass1.get("phases", {})
        weak_points = []
        # Low-scoring theories
        theories_p1 = p1_phases.get("theory_competition", {}).get("theories", [])
        for t in theories_p1:
            score = t.get("scores", {}).get("overall", 0)
            if score < 0.5:
                weak_points.append(f"Theory '{t.get('name', '?')}' scored only {score:.2f}")
        # Failed predictions
        preds_p1 = p1_phases.get("prediction_engine", {}).get("all_predictions", [])
        failed_preds = [p for p in preds_p1 if isinstance(p, dict) and p.get("validation_status") == "rejected"]
        if failed_preds:
            weak_points.append(f"{len(failed_preds)} predictions were rejected as too vague or unfalsifiable")
        # Unfilled gaps
        gaps_p1 = p1_phases.get("gap_detection", {}).get("top_gaps", [])
        if gaps_p1:
            weak_points.append(f"{len(gaps_p1)} knowledge gaps remain unfilled")

        # Build refined topic for second pass
        refinement_context = ""
        if weak_points:
            refinement_context = " ".join(weak_points[:3])
            refined_topic = f"{topic} (focus on: {refinement_context[:200]})"
            print(f"  Weak points: {len(weak_points)}")
            for wp in weak_points[:3]:
                print(f"    - {wp[:100]}")
        else:
            refined_topic = topic
            print("  No weak points identified — re-running with same topic")

        # Second pass with refined context
        print(f"\n  [Pass 2/2] Running refined discovery...")
        try:
            report_pass2 = run_discovery_pipeline(refined_topic, domain=domain, mode=mode)
        except Exception as e:
            print(f"  Pass 2 failed: {e}")
            report_pass2 = {}

        # Merge results — keep best from each pass
        print("\n  [Merging results from both passes...]")
        report = report_pass2 if report_pass2 else report_pass1

        # Merge theories — keep unique ones from both passes
        p1_theories = p1_phases.get("theory_competition", {}).get("theories", [])
        p2_theories = report_pass2.get("phases", {}).get("theory_competition", {}).get("theories", [])
        if p1_theories and p2_theories:
            seen_names = {t.get("name", "").lower() for t in p2_theories}
            for t in p1_theories:
                if t.get("name", "").lower() not in seen_names:
                    p2_theories.append(t)
            report.setdefault("phases", {}).setdefault("theory_competition", {})["theories"] = p2_theories
            report["phases"]["theory_competition"]["theories_compared"] = len(p2_theories)

        # Merge hidden variables
        p1_hvs = p1_phases.get("missing_variables", {}).get("variable_details", [])
        p2_hvs = report.get("phases", {}).get("missing_variables", {}).get("variable_details", [])
        if p1_hvs and p2_hvs:
            seen_names = {hv.get("name", "").lower() for hv in p2_hvs}
            for hv in p1_hvs:
                if hv.get("name", "").lower() not in seen_names:
                    p2_hvs.append(hv)
            report["phases"]["missing_variables"]["variable_details"] = p2_hvs
            report["phases"]["missing_variables"]["proposed"] = len(p2_hvs)

        print(f"  Merged: {len(p2_theories)} theories, {len(p2_hvs)} hidden variables")
        report["iterative"] = {
            "pass1_score": p1_phases.get("discovery_scoring", {}).get("discovery_score", 0),
            "pass2_score": report.get("phases", {}).get("discovery_scoring", {}).get("discovery_score", 0),
            "weak_points": weak_points,
            "refined_topic": refined_topic,
        }

    else:
        # ── DUAL-TRACK MODE: Track A (conventional) + Track B (curiosity-driven) ──
        from discovery.discovery_pipeline_v2 import run_discovery_pipeline

        # ── Step 1: TRACK A — Conventional Pipeline (NO constraint) ──
        print("="*70)
        print("TRACK A: CONVENTIONAL PIPELINE")
        print("="*70)
        t0 = time.time()
        try:
            report_a = run_discovery_pipeline(topic, domain=domain, mode=mode, original_topic=cause or topic)
            phases_a = report_a.get("phases", {})
            score_a = phases_a.get('discovery_scoring', {}).get('discovery_score', 0)
            grade_a = phases_a.get('discovery_scoring', {}).get('grade', 'F')
            winner_a = report_a.get("canonical_winner", {})
            print(f"\n  Track A complete in {time.time()-t0:.0f}s")
            print(f"  Winner: {winner_a.get('name', '?')[:50]} (score: {winner_a.get('score', 0):.3f})")
            print(f"  Score: {score_a:.0f}/100 ({grade_a})")
        except Exception as e:
            print(f"  Track A FAILED: {e}")
            import traceback; traceback.print_exc()
            report_a = {}

        # ── Step 2: Get constraint from Track A's Phase 0 for Track B ──
        curiosity_constraint = None
        if report_a:
            curiosity_constraint = report_a.get("curious_questioning", {}).get("constraint")
        if cause_data and not curiosity_constraint:
            curiosity_constraint = cause_data.get("constraint")

        # ── Cooldown between tracks — let LLM rate limits reset ──
        if curiosity_constraint and curiosity_constraint.get("forbidden_theories"):
            cooldown = 60
            print(f"\n  [Cooldown] Waiting {cooldown}s for LLM rate limits to reset before Track B...")
            time.sleep(cooldown)
            print(f"  [Cooldown] Done. Starting Track B.\n")

        # ── Step 3: TRACK B — Curiosity-Driven Pipeline (WITH constraint) ──
        report_b = {}
        if curiosity_constraint and curiosity_constraint.get("forbidden_theories"):
            print()
            print("="*70)
            print("TRACK B: CURIOSITY-DRIVEN PIPELINE")
            print(f"  Forbidden: {', '.join(curiosity_constraint['forbidden_theories'])}")
            print("="*70)
            t0 = time.time()
            try:
                report_b = run_discovery_pipeline(topic, domain=domain, mode=mode,
                                                   curiosity_constraint=curiosity_constraint,
                                                   original_topic=cause or topic)
                phases_b = report_b.get("phases", {})
                score_b = phases_b.get('discovery_scoring', {}).get('discovery_score', 0)
                grade_b = phases_b.get('discovery_scoring', {}).get('grade', 'F')
                winner_b = report_b.get("canonical_winner", {})
                print(f"\n  Track B complete in {time.time()-t0:.0f}s")
                print(f"  Winner: {winner_b.get('name', '?')[:50]} (score: {winner_b.get('score', 0):.3f})")
                print(f"  Score: {score_b:.0f}/100 ({grade_b})")
            except Exception as e:
                print(f"  Track B FAILED: {e}")
                import traceback; traceback.print_exc()
        else:
            print("\n  [Track B skipped — no curiosity constraint generated]")

        # ── Step 4: Merge — Track A is primary, Track B added for comparison ──
        report = report_a if report_a else report_b

        if report_b:
            report["track_b"] = {
                "winner": report_b.get("canonical_winner"),
                "score": report_b.get("phases", {}).get("discovery_scoring", {}).get("discovery_score", 0),
                "grade": report_b.get("phases", {}).get("discovery_scoring", {}).get("grade", "F"),
                "theories": report_b.get("phases", {}).get("theory_competition", {}).get("theories", []),
                "constraint": curiosity_constraint,
            }
            report["dual_track"] = {
                "track_a": {
                    "winner": report_a.get("canonical_winner") if report_a else None,
                    "score": report_a.get("phases", {}).get("discovery_scoring", {}).get("discovery_score", 0) if report_a else 0,
                },
                "track_b": {
                    "winner": report_b.get("canonical_winner"),
                    "score": report_b.get("phases", {}).get("discovery_scoring", {}).get("discovery_score", 0),
                },
                "constraint": curiosity_constraint,
            }

        if not report:
            print("  Both tracks failed. Nothing to save.")
            return

    # ── Stage 2: Refinement + Reflexion already run inside pipeline (Phase 13-14) ──
    # Skip duplicate refinement/reflexion — pipeline handles it internally
    print(f"\n  [Refinement + Reflexion already completed inside pipeline (Phase 13-14)]")

    # ── Add cause mode data to report ──
    if cause_data:
        report["cause_mode"] = {
            "original_cause": cause,
            "core_question": cause_data.get("reframed", ""),
            "question_hypothesis": cause_data.get("question_hypothesis", ""),
            "why_it_matters": cause_data.get("why_it_matters", ""),
            "observations": cause_data.get("observations", []),
            "questions": cause_data.get("questions", []),
            "generalizations": cause_data.get("generalizations", []),
            "constraint": cause_data.get("constraint"),
            "generated_topic": topic,
        }

    # ── Save Report ──
    total_time = time.time() - total_start
    print(f"\n{'='*70}")
    print(f"TOTAL TIME: {total_time:.0f}s")
    print(f"{'='*70}")

    report_path = _save_report(report, topic)
    
    # Print summary
    phases = report.get("phases", {})
    print(f"\n{'='*70}")
    print("RESULTS SUMMARY")
    print(f"{'='*70}")
    print(f"  Topic: {topic}")
    print(f"  Domain: {report.get('domain', 'unknown')}")
    print(f"  Papers: {phases.get('literature', {}).get('papers_found', 0)}")
    print(f"  Entities: {phases.get('knowledge_graph', {}).get('entities', 0)}")
    print(f"  Relationships: {phases.get('knowledge_graph', {}).get('relationships', 0)}")
    print(f"  Gaps: {phases.get('gap_detection', {}).get('total_gaps', 0)}")
    print(f"  Anomalies: {phases.get('anomaly_detection', {}).get('total_anomalies', 0)}")
    print(f"  Hidden Variables: {phases.get('missing_variables', {}).get('proposed', 0)}")
    print(f"  Mechanisms: {phases.get('mechanism_generation', {}).get('mechanisms_generated', 0)}")
    print(f"  Predictions: {phases.get('prediction_engine', {}).get('total_predictions', 0)}")
    print(f"  Theories: {phases.get('theory_competition', {}).get('theories_compared', 0)}")
    # New phases
    citation_hop1 = phases.get('citation_network', {}).get('citation_hop1', 0)
    citation_hop2 = phases.get('citation_network', {}).get('citation_hop2', 0)
    if citation_hop1 or citation_hop2:
        print(f"  Citation Walk: +{citation_hop1} hop1, +{citation_hop2} hop2 papers")
    exp_plans = phases.get('experimental_validation', {}).get('plans_generated', 0)
    if exp_plans:
        print(f"  Experiment Plans: {exp_plans}")
    data_results = phases.get('data_analysis', {}).get('datasets_fetched', 0)
    if data_results:
        print(f"  Datasets Analyzed: {data_results}")
    hyp_saved = report.get('hypothesis_memory', {}).get('saved', 0)
    if hyp_saved:
        print(f"  Hypotheses Saved: {hyp_saved} to memory")
    score = phases.get('discovery_scoring', {}).get('discovery_score', 0)
    grade = phases.get('discovery_scoring', {}).get('grade', 'F')
    domain_score = phases.get('discovery_scoring', {}).get('domain_weighted_score', 0)
    if domain_score:
        print(f"  Score: {score:.0f}/100 (domain-weighted: {domain_score:.0f}/100) ({grade})")
    else:
        print(f"  Score: {score:.0f}/100 ({grade})")
    if report.get("refinement"):
        print(f"  Refinement: complete")
    if report.get("reflexion"):
        print(f"  Reflexion: {report['reflexion'].get('patches_applied', 0)} patches applied")
    print(f"  Report: {report_path}")
    print(f"  Time: {total_time:.0f}s")


def _save_report(report, topic):
    """Save report to data/ and update dashboard index."""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize topic for filename
    safe_topic = "".join(c if c.isalnum() or c in " _-" else "" for c in topic)[:50].strip().replace(" ", "_")
    report_path = data_dir / f"discovery_{safe_topic}_{int(time.time())}.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    
    # Update reports index for dashboard
    idx_path = data_dir / "reports_index.json"
    try:
        idx = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else []
    except Exception:
        idx = []
    rel = str(report_path.relative_to(Path(__file__).parent))
    if rel not in idx:
        idx.append(rel)
        idx_path.write_text(json.dumps(idx[-50:], indent=2), encoding="utf-8")
    
    print(f"\n  Report saved: {report_path}")
    return report_path


if __name__ == "__main__":
    main()
