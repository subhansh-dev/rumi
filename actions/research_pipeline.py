"""
research_pipeline.py — RUMI Scientist AI Enhanced Pipeline Action Tool

Exposes the ResearchPipeline as a callable action tool for RUMI.
Integrates with the main.py tool registry system.
"""

import json
import time
from datetime import datetime


def research_pipeline(
    action: str = "run",
    topic: str = "",
    hypothesis: str = "",
    mode: str = "full",
    domain: str = "",
    generate_paper: bool = True,
    run_experiments: bool = True,
    use_research_team: bool = True,
    report_id: str = "",
) -> str:
    """
    Enhanced autonomous research pipeline action.

    Action modes:
      run       - Run the enhanced research pipeline (default)
      quick     - Quick mode: literature + novelty + hypothesis only
      explore   - Curiosity-driven topic discovery + quick analysis
      iterate   - Full pipeline + self-improvement analysis
      history   - Show recent pipeline run history
      stats     - Show pipeline statistics
      report    - Get a specific report by ID

    Args:
        action: Operation mode
        topic: Research topic or question
        hypothesis: Optional pre-defined hypothesis
        mode: Pipeline depth (quick | standard | full | explore | iterate)
        domain: Scientific domain hint
        generate_paper: Whether to generate a paper
        run_experiments: Whether to run experiments
        use_research_team: Whether to use multi-agent debate
        report_id: Report ID for report action

    Returns:
        Formatted result string
    """
    try:
        from scientist.pipeline import get_pipeline
        pipeline = get_pipeline()

        if action == "stats":
            stats = pipeline.get_stats()
            return json.dumps(stats, indent=2, default=str)

        if action == "history":
            history = pipeline.get_history(limit=10)
            if not history:
                return "No pipeline runs in history yet."
            summary = []
            for h in history:
                summary.append({
                    "id": h.get("report_id"),
                    "topic": h.get("topic", "")[:60],
                    "mode": h.get("mode"),
                    "duration_s": round(h.get("duration_s", 0), 1),
                    "confidence": round(h.get("confidence", 0), 3),
                    "errors": len(h.get("errors", [])),
                    "phase": h.get("phase"),
                })
            return json.dumps(summary, indent=2, default=str)

        if action == "report":
            if not report_id:
                return "Error: report_id is required for report action."
            report = pipeline.get_report(report_id)
            if not report:
                return f"Report {report_id} not found."
            return json.dumps(report, indent=2, default=str)

        if action == "quick":
            mode = "quick"
        elif action == "explore":
            mode = "explore"
        elif action == "iterate":
            mode = "iterate"

        if not topic and mode != "explore":
            return "Error: topic is required for research pipeline."

        result = pipeline.run(
            topic=topic,
            hypothesis=hypothesis,
            mode=mode,
            domain=domain,
            generate_paper=generate_paper,
            run_experiments=run_experiments,
            use_research_team=use_research_team,
        )

        return _format_pipeline_result(result)

    except Exception as e:
        return f"[TOOL_ERROR] Research pipeline failed: {e}"


def _format_pipeline_result(result: dict) -> str:
    """Format pipeline result into a readable string."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  RESEARCH PIPELINE REPORT")
    lines.append(f"  ID: {result.get('report_id', 'N/A')}")
    lines.append(f"  Topic: {result.get('topic', 'N/A')}")
    lines.append(f"  Mode: {result.get('mode', 'N/A')}")
    lines.append(f"  Duration: {result.get('duration_s', 0):.1f}s")
    lines.append(f"  Confidence: {result.get('confidence', 0):.1%}")
    lines.append("=" * 60)

    # Literature review
    lr = result.get("literature_review", {})
    if lr:
        papers = lr.get("papers", [])
        lines.append(f"\n📚 Literature Review: {len(papers)} papers found")

    # Novelty
    nc = result.get("novelty_check", {})
    if nc:
        ns = nc.get("novelty_score", 0.5)
        verdict = nc.get("verdict", "unknown")
        lines.append(f"\n🔬 Novelty Score: {ns:.0%} — {verdict}")

    # Hypothesis
    hyp = result.get("selected_hypothesis", "")
    if hyp:
        lines.append(f"\n🧪 Hypothesis: {hyp[:200]}")

    # Experiment
    exp = result.get("experiment_result", {})
    if exp:
        status = exp.get("status", "unknown")
        lines.append(f"\n⚗️ Experiment: {status}")
        analysis = result.get("experiment_analysis", {})
        if analysis:
            interp = analysis.get("interpretation", "")
            if interp:
                lines.append(f"   Interpretation: {interp[:200]}")

    # Reproducibility
    rep = result.get("reproducibility_check", {})
    if rep and isinstance(rep, dict):
        rs = rep.get("reproducibility_score", 0.5)
        lines.append(f"\n🔄 Reproducibility Score: {rs:.0%}")

    # Peer Review
    pr = result.get("peer_review", {})
    if pr and isinstance(pr, dict):
        scores = pr.get("scores", {})
        overall = scores.get("overall", 0)
        lines.append(f"\n📝 Peer Review: {overall:.2f}/5.0")

    # Paper
    paper = result.get("paper", {})
    if paper and isinstance(paper, dict):
        title = paper.get("title", "")
        bibtex = paper.get("bibtex_entries", [])
        lines.append(f"\n📄 Paper: {title}")
        lines.append(f"   Citations: {len(bibtex)} references")
        lines.append(f"   Venue: {paper.get('venue', 'arXiv')}")

    # Discoveries
    discoveries = result.get("discoveries", [])
    if discoveries:
        lines.append(f"\n💡 Discoveries:")
        for d in discoveries[:3]:
            lines.append(f"   • {d[:200]}")

    # Next questions
    next_q = result.get("next_questions", [])
    if next_q:
        lines.append(f"\n❓ Next Questions:")
        for q in next_q[:3]:
            lines.append(f"   • {q[:150]}")

    # Self-improvement
    ls = result.get("learning_summary", {})
    if ls and isinstance(ls, dict):
        avg_conf = ls.get("average_confidence")
        if avg_conf is not None:
            lines.append(f"\n📊 Self-Improvement:")
            lines.append(f"   Avg Confidence (last {ls.get('runs_analyzed', 0)} runs): {avg_conf:.1%}")
            suggestions = ls.get("improvement_suggestions", [])
            for s in suggestions:
                lines.append(f"   💡 {s}")

    # Errors
    errors = result.get("errors", [])
    if errors:
        lines.append(f"\n⚠️ Warnings ({len(errors)}):")
        for e in errors[:3]:
            lines.append(f"   • {e[:150]}")

    lines.append("\n" + "=" * 60)
    return "\n".join(lines)
