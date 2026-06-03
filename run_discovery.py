"""
run_discovery.py — Full RUMI Discovery Runner

Matches the interactive RUMI terminal flow:
  1. Discovery Pipeline v2 (12 phases)
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
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    import argparse
    parser = argparse.ArgumentParser(description="RUMI Full Discovery Runner")
    parser.add_argument("topic", help="Research topic")
    parser.add_argument("--domain", default="", help="Domain override (e.g. space_astronomy, physics)")
    parser.add_argument("--mode", default="full", choices=["quick", "standard", "full"], help="Pipeline depth")
    parser.add_argument("--skip-refinement", action="store_true", help="Skip refinement pipeline")
    parser.add_argument("--skip-reflexion", action="store_true", help="Skip reflexion cycle")
    args = parser.parse_args()

    topic = args.topic
    domain = args.domain
    mode = args.mode

    print(f"{'='*70}")
    print(f"RUMI DISCOVERY — {topic}")
    print(f"Domain: {domain or 'auto-detect'} | Mode: {mode}")
    print(f"{'='*70}\n")

    report = {}
    total_start = time.time()

    # ── Stage 1: Discovery Pipeline v2 (12 phases) ──
    print("="*70)
    print("STAGE 1: DISCOVERY PIPELINE v2 (12 phases)")
    print("="*70)
    t0 = time.time()
    try:
        from discovery.discovery_pipeline_v2 import run_discovery_pipeline
        report = run_discovery_pipeline(topic, domain=domain, mode=mode)
        phases = report.get("phases", {})
        print(f"\n  Pipeline complete in {time.time()-t0:.0f}s")
        print(f"  Papers: {phases.get('literature', {}).get('papers_found', 0)}")
        print(f"  Entities: {phases.get('knowledge_graph', {}).get('entities', 0)}")
        print(f"  Theories: {len(phases.get('theory_competition', {}).get('theories', []))}")
        score = phases.get('discovery_scoring', {}).get('discovery_score', 0)
        grade = phases.get('discovery_scoring', {}).get('grade', 'F')
        print(f"  Score: {score:.0f}/100 ({grade})")
    except Exception as e:
        print(f"  Pipeline FAILED: {e}")
        import traceback; traceback.print_exc()
        # Save what we have and exit
        _save_report(report, topic)
        return

    # ── Stage 2: Refinement Pipeline (13 stages) ──
    if not args.skip_refinement:
        print(f"\n{'='*70}")
        print("STAGE 2: REFINEMENT PIPELINE (13 stages)")
        print("="*70)
        t0 = time.time()
        try:
            from discovery.refinement_pipeline import run_refinement_pipeline
            from discovery.graph import KnowledgeGraph
            graph = KnowledgeGraph(persist=True)
            hypotheses = report.get("phases", {}).get("theory_competition", {}).get("theories", [])
            contradictions = report.get("phases", {}).get("contradictions", {}).get("contradictions", [])
            refinement = run_refinement_pipeline(
                topic, report.get("domain", ""), [], graph,
                hypotheses, contradictions
            )
            if refinement:
                report["refinement"] = refinement
                print(f"\n  Refinement complete in {time.time()-t0:.0f}s")
            else:
                print(f"\n  Refinement returned empty ({time.time()-t0:.0f}s)")
        except Exception as e:
            print(f"  Refinement FAILED: {e}")
            import traceback; traceback.print_exc()
    else:
        print("\n  [Skipped refinement]")

    # ── Stage 3: Reflexion (self-improvement) ──
    if not args.skip_reflexion:
        print(f"\n{'='*70}")
        print("STAGE 3: REFLEXION (self-improvement)")
        print("="*70)
        t0 = time.time()
        try:
            from brain.reflexion import get_recursive_improver
            from discovery.llm_client import call as llm_call

            improver = get_recursive_improver(llm_fn=llm_call)
            run_result = {
                "query": topic,
                "domain": report.get("domain", ""),
                "hypotheses": report.get("phases", {}).get("theory_competition", {}).get("theories", []),
                "contradictions": report.get("phases", {}).get("contradictions", {}).get("contradictions", []),
                "metrics": {},
                "errors": report.get("errors", []),
            }
            # Use sync version for standalone script
            reflexion_result = improver.reflect_and_improve_sync(
                run_result, llm_fn=llm_call, post_output_fn=lambda msg: print(f"  {msg}")
            )
            if reflexion_result:
                report["reflexion"] = reflexion_result
                patches_applied = reflexion_result.get("patches_applied", 0)
                patches_rejected = reflexion_result.get("patches_rejected", 0)
                improvement = reflexion_result.get("improvement_score", 0)
                print(f"\n  Reflexion complete in {time.time()-t0:.0f}s")
                print(f"  Patches applied: {patches_applied}, rejected: {patches_rejected}")
                print(f"  Improvement score: {improvement:.0%}")
        except Exception as e:
            print(f"  Reflexion FAILED: {e}")
            import traceback; traceback.print_exc()
    else:
        print("\n  [Skipped reflexion]")

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
    print(f"  Gaps: {len(phases.get('gap_detection', {}).get('top_gaps', []))}")
    print(f"  Anomalies: {len(phases.get('anomaly_detection', {}).get('top_anomalies', []))}")
    print(f"  Hidden Variables: {len(phases.get('hidden_variables', {}).get('hidden_variables', []))}")
    print(f"  Mechanisms: {len(phases.get('mechanisms', {}).get('mechanisms', []))}")
    print(f"  Predictions: {len(phases.get('predictions', {}).get('predictions_accepted', []))}")
    print(f"  Theories: {len(phases.get('theory_competition', {}).get('theories', []))}")
    score = phases.get('discovery_scoring', {}).get('discovery_score', 0)
    grade = phases.get('discovery_scoring', {}).get('grade', 'F')
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
