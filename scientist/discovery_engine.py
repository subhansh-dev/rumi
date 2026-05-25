"""
discovery_engine.py — Autonomous Scientific Discovery Pipeline

The master orchestrator for RUMI's Scientist AI. Runs the complete
discovery loop:
  [DE-1] Idea → Novelty Check → Hypothesis Formulation
  [DE-2] Hypothesis → Experiment Design → Execution → Analysis
  [DE-3] Results → Peer Review → Paper Generation
  [DE-4] Paper → Iterate (refine hypothesis based on review)
  [DE-5] Discover → Learn → Update Knowledge Graph → Discover Again

Inspired by:
  - Sakana AI's The AI Scientist v2 (Agentic Tree Search)
  - Feynman's approach to understanding
  - The full scientific method as a closed loop

Thread-safe. Persistent state in discovery_state.json.
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()
STATE_FILE = SCIENTIST_DIR / "discovery_state.json"


class DiscoveryReport:
    """A structured report from a complete discovery run."""

    def __init__(self, topic: str):
        self.report_id = f"DISCOVERY-{int(time.time() * 1000)}"
        self.topic = topic
        self.phase = "initiated"
        self.novelty_check: Optional[dict] = None
        self.hypothesis: str = ""
        self.experiment_design: Optional[dict] = None
        self.experiment_result: Optional[dict] = None
        self.experiment_analysis: Optional[dict] = None
        self.feynman_reduction: Optional[dict] = None
        self.peer_review: Optional[dict] = None
        self.cross_validation: Optional[dict] = None
        self.research_team_session: Optional[dict] = None
        self.paper: Optional[dict] = None
        self.discoveries: list[dict] = []
        self.confidence: float = 0.0
        self.duration_s: float = 0.0
        self.errors: list[str] = []
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "topic": self.topic,
            "phase": self.phase,
            "novelty_check": self.novelty_check,
            "hypothesis": self.hypothesis,
            "experiment_design": self.experiment_design,
            "experiment_result": self.experiment_result,
            "experiment_analysis": self.experiment_analysis,
            "feynman_reduction": self.feynman_reduction,
            "peer_review": self.peer_review,
            "cross_validation": self.cross_validation,
            "research_team_session": self.research_team_session,
            "paper": self.paper,
            "discoveries": self.discoveries,
            "confidence": round(self.confidence, 3),
            "duration_s": round(self.duration_s, 2),
            "errors": self.errors,
            "created_at": self.created_at,
        }


class DiscoveryEngine:
    """
    Master orchestrator for the full scientific discovery pipeline.

    Runs: Idea → Novelty Check → Feynman Reduction → Research Team →
          Experiment Design → Execute → Analyze → Cross-Validate →
          Peer Review → Paper Generation
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._history: list[dict] = []
        self._discovery_count = 0
        self._load()

    def _load(self):
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self._history = data.get("history", [])
                self._discovery_count = data.get("discovery_count", 0)
        except Exception:
            self._history = []
            self._discovery_count = 0

    def _save(self):
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps({
                "history": self._history[-20:],
                "discovery_count": self._discovery_count,
                "last_updated": datetime.now().isoformat(),
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    def run_discovery(
        self,
        topic: str,
        hypothesis: str = "",
        run_experiments: bool = True,
        generate_paper: bool = True,
        verbose: bool = True,
    ) -> dict:
        """
        Run a full autonomous discovery pipeline.

        Args:
            topic: Research topic or question
            hypothesis: Optional pre-defined hypothesis (if empty, one will be generated)
            run_experiments: Whether to execute experiments
            generate_paper: Whether to generate a paper/report
            verbose: Whether to include detailed output

        Returns:
            Dict with full discovery report
        """
        with self._lock:
            self._discovery_count += 1

        report = DiscoveryReport(topic)
        start_time = time.time()

        # ════════════════════════════════════════════════════════════
        # PHASE 1: Novelty Check
        # ════════════════════════════════════════════════════════════
        try:
            from scientist.novelty_checker import get_novelty_checker
            checker = get_novelty_checker()
            report.novelty_check = checker.check_novelty(topic, max_papers=15)
            report.phase = "novelty_checked"
        except Exception as e:
            report.errors.append(f"Novelty check failed: {e}")
            report.novelty_check = {"novelty_score": 0.5, "verdict": "unknown", "error": str(e)}

        # ════════════════════════════════════════════════════════════
        # PHASE 2: Feynman Reduction (first-principles understanding)
        # ════════════════════════════════════════════════════════════
        try:
            from scientist.feynman_reducer import get_feynman_reducer
            reducer = get_feynman_reducer()
            report.feynman_reduction = reducer.reduce(topic)
            report.phase = "reduced"
        except Exception as e:
            report.errors.append(f"Feynman reduction failed: {e}")

        # ════════════════════════════════════════════════════════════
        # PHASE 3: Research Team Collaboration
        # ════════════════════════════════════════════════════════════
        try:
            from scientist.research_team import get_research_team
            team = get_research_team()
            report.research_team_session = team.collaborate(
                topic=topic,
                hypothesis=hypothesis or topic,
                context={"novelty": report.novelty_check},
            )
            report.phase = "team_collaborated"
        except Exception as e:
            report.errors.append(f"Research team session failed: {e}")

        # ════════════════════════════════════════════════════════════
        # PHASE 4: Hypothesis Formulation
        # ════════════════════════════════════════════════════════════
        if hypothesis:
            report.hypothesis = hypothesis
        else:
            # Generate hypothesis from novelty check / feynman reduction
            report.hypothesis = self._generate_hypothesis(topic, report)
        report.phase = "hypothesis_formulated"

        # ════════════════════════════════════════════════════════════
        # PHASE 5: Experiment Design & Execution
        # ════════════════════════════════════════════════════════════
        if run_experiments:
            try:
                from scientist.experiment_designer import get_experiment_designer
                designer = get_experiment_designer()

                # Auto-detect experiment type
                exp_type = self._detect_experiment_type(topic, report.hypothesis)

                report.experiment_design = designer.design_experiment(
                    hypothesis=report.hypothesis,
                    domain=topic,
                    experiment_type=exp_type,
                )
                report.phase = "experiment_designed"

                # Run experiment
                report.experiment_result = designer.run_experiment(
                    report.experiment_design,
                    timeout=120,
                )

                # Analyze results
                report.experiment_analysis = designer.analyze_results(
                    report.experiment_result
                )
                report.phase = "experiment_executed"

            except Exception as e:
                report.errors.append(f"Experiment failed: {e}")

        # ════════════════════════════════════════════════════════════
        # PHASE 6: Cross-Validation
        # ════════════════════════════════════════════════════════════
        if run_experiments and report.experiment_result:
            try:
                from scientist.cross_validator import get_cross_validator
                validator = get_cross_validator()

                report.cross_validation = validator.validate_experiment(
                    hypothesis=report.hypothesis,
                    results=report.experiment_result.get("results", {}),
                    methodology=str(report.experiment_design.get("methodology", "")),
                )
                report.phase = "validated"
            except Exception as e:
                report.errors.append(f"Cross-validation failed: {e}")

        # ════════════════════════════════════════════════════════════
        # PHASE 7: Peer Review
        # ════════════════════════════════════════════════════════════
        try:
            from scientist.peer_reviewer import get_peer_reviewer
            reviewer = get_peer_reviewer()

            report.peer_review = reviewer.review_paper(
                title=f"On the {topic[:80]}",
                abstract=f"Investigation of {topic[:200]}",
                hypothesis=report.hypothesis,
                methodology=str(report.experiment_design.get("methodology", "Systematic investigation")
                               if report.experiment_design else "Systematic investigation"),
                results=report.experiment_result.get("results", {}) if report.experiment_result else {},
                conclusions=self._generate_conclusions(report),
                experiment_logs=report.experiment_result,
            )
            report.phase = "reviewed"
        except Exception as e:
            report.errors.append(f"Peer review failed: {e}")

        # ════════════════════════════════════════════════════════════
        # PHASE 8: Paper Generation
        # ════════════════════════════════════════════════════════════
        if generate_paper:
            try:
                from scientist.paper_generator import get_paper_generator
                generator = get_paper_generator()

                # Get related papers from novelty check
                related = []
                if report.novelty_check:
                    related = report.novelty_check.get("closest_papers", [])[:10]

                report.paper = generator.generate_paper_from_discovery(
                    topic=topic,
                    hypothesis=report.hypothesis,
                    experiment_results=report.experiment_result.get("results", {})
                    if report.experiment_result else {},
                    experiment_analysis=report.experiment_analysis or {},
                    related_papers=related,
                )
                report.phase = "paper_generated"
            except Exception as e:
                report.errors.append(f"Paper generation failed: {e}")

        # ════════════════════════════════════════════════════════════
        # FINAL: Synthesize Confidence & Discoveries
        # ════════════════════════════════════════════════════════════
        report.duration_s = time.time() - start_time
        report.confidence = self._compute_confidence(report)
        report.discoveries = self._extract_discoveries(report)

        # Record in hypothesis engine
        try:
            from brain.hypothesis_engine import get_hypothesis_engine
            engine = get_hypothesis_engine()
            engine.add_hypothesis(
                title=f"Discovery: {topic[:80]}",
                description=(
                    f"Automated discovery on {topic}. "
                    f"Novelty score: {report.novelty_check.get('novelty_score', 0.5):.0%}. "
                    f"Confidence: {report.confidence:.0%}. "
                    f"Duration: {report.duration_s:.0f}s."
                ),
                domain=topic[:50],
                source="scientist_ai",
                tags=["discovery", "automated"],
            )
        except Exception:
            pass

        report.report_id = f"DISCOVERY-{self._discovery_count}"

        with self._lock:
            self._history.append(report.to_dict())
            self._save()

        return report.to_dict()

    def _generate_hypothesis(self, topic: str, report: DiscoveryReport) -> str:
        """Generate a hypothesis from topic and context."""
        # Build hypothesis from available data
        novelty_score = report.novelty_check.get("novelty_score", 0.5) if report.novelty_check else 0.5
        feynman_fundamentals = (
            report.feynman_reduction.get("fundamental_principles", [])
            if report.feynman_reduction else []
        )

        hypothesis_parts = [f"Investigation into {topic}"]

        if feynman_fundamentals:
            hypothesis_parts.append(
                f"based on fundamental principles of {feynman_fundamentals[0].split('] ')[-1] if '] ' in feynman_fundamentals[0] else feynman_fundamentals[0]}"
            )

        hypothesis_parts.append(
            f"yields novel insights with estimated novelty of {novelty_score:.0%}"
        )

        return ". ".join(hypothesis_parts)

    def _detect_experiment_type(self, topic: str, hypothesis: str) -> str:
        """Auto-detect the best experiment type."""
        text = f"{topic} {hypothesis}".lower()

        if any(w in text for w in ["compare", "vs", "versus", "difference", "ablation"]):
            return "ablation"
        if any(w in text for w in ["statistical", "significant", "p-value"]):
            return "statistical_test"
        if any(w in text for w in ["predict", "regression", "forecast", "continuous"]):
            return "regression"
        return "classification"

    def _generate_conclusions(self, report: DiscoveryReport) -> str:
        """Generate conclusions from available data."""
        parts = [
            f"In this investigation of {report.topic}, we formulated and tested "
            f"a hypothesis regarding {report.hypothesis[:100]}."
        ]

        if report.experiment_analysis:
            analysis = report.experiment_analysis
            interp = analysis.get("interpretation", "")
            if interp:
                parts.append(interp)

        if report.cross_validation:
            val = report.cross_validation
            parts.append(
                f"Cross-validation yielded a validity score of "
                f"{val.get('validity_score', 0.5):.0%}."
            )

        if report.peer_review:
            scores = report.peer_review.get("scores", {})
            overall = scores.get("overall", 0)
            parts.append(
                f"Automated peer review scored the work at {overall:.2f}/5.0 "
                f"({scores.get('novelty', 0):.1f} novelty, "
                f"{scores.get('soundness', 0):.1f} soundness)."
            )

        parts.append("Future work should explore extensions and address identified limitations.")

        return " ".join(parts)

    def _compute_confidence(self, report: DiscoveryReport) -> float:
        """Compute overall confidence from all pipeline stages."""
        scores = []

        # Novelty confidence (inverse: more novel = less established = lower confidence)
        novelty = report.novelty_check.get("novelty_score", 0.5) if report.novelty_check else 0.5
        scores.append(1.0 - novelty * 0.3)  # novel ideas have less prior evidence

        # Experiment success
        if report.experiment_result:
            if report.experiment_result.get("status") == "completed":
                scores.append(0.8)
            elif report.experiment_result.get("status") == "timeout":
                scores.append(0.3)
            else:
                scores.append(0.2)

        # Cross-validation
        if report.cross_validation:
            scores.append(report.cross_validation.get("validity_score", 0.5))

        # Peer review
        if report.peer_review:
            overall = report.peer_review.get("scores", {}).get("overall", 3.0)
            scores.append(overall / 5.0)

        # Research team consensus
        if report.research_team_session:
            synthesis = report.research_team_session.get("synthesis", {})
            scores.append(synthesis.get("consensus_score", 0.5))

        return sum(scores) / len(scores) if scores else 0.5

    def _extract_discoveries(self, report: DiscoveryReport) -> list[dict]:
        """Extract key discoveries from the pipeline output."""
        discoveries = []

        # Discovery from novelty check
        if report.novelty_check:
            discoveries.append({
                "type": "literature_insight",
                "description": f"Novelty assessment: {report.novelty_check.get('verdict', 'unknown')} "
                              f"(score: {report.novelty_check.get('novelty_score', 0):.0%})",
                "confidence": report.novelty_check.get("novelty_score", 0.5),
            })

        # Discovery from Feynman reduction
        if report.feynman_reduction:
            discoveries.append({
                "type": "first_principles",
                "description": f"Core fundamentals identified: "
                              f"{', '.join(report.feynman_reduction.get('fundamental_principles', [])[:3])}",
                "confidence": 0.7,
            })

        # Discovery from experiment
        if report.experiment_analysis:
            analysis = report.experiment_analysis
            interp = analysis.get("interpretation", "")
            if interp:
                discoveries.append({
                    "type": "experimental_finding",
                    "description": interp[:200],
                    "confidence": 0.6,
                })

        # Discovery from peer review
        if report.peer_review:
            strengths = report.peer_review.get("strengths", [])
            for s in strengths:
                discoveries.append({
                    "type": "strength",
                    "description": s,
                    "confidence": 0.8,
                })

        return discoveries

    def run_quick_discovery(self, topic: str) -> str:
        """
        Run a lightweight discovery (no experiments or paper generation).
        Returns a formatted text summary.
        """
        result = self.run_discovery(
            topic=topic,
            run_experiments=False,
            generate_paper=False,
            verbose=False,
        )

        novelty = result.get("novelty_check", {})
        feynman = result.get("feynman_reduction", {})
        review = result.get("peer_review", {})

        lines = [
            f"🔬 **Discovery Scan: {topic}**",
            f"  Confidence: {result.get('confidence', 0):.0%}",
            f"  Duration: {result.get('duration_s', 0):.1f}s",
            "",
        ]

        if novelty:
            lines.append(f"**Novelty:** {novelty.get('verdict', 'unknown')} ({novelty.get('novelty_score', 0):.0%})")

        if feynman:
            principles = feynman.get("fundamental_principles", [])
            if principles:
                lines.append(f"**First Principles:**")
                for p in principles[:3]:
                    lines.append(f"  • {p}")
            analogies = feynman.get("analogies", [])
            if analogies:
                lines.append(f"**Analogy:** {analogies[0][:100]}...")

        if review:
            scores = review.get("scores", {})
            lines.append(f"**Quality Review:** "
                        f"Nov={scores.get('novelty', 0):.1f} "
                        f"Snd={scores.get('soundness', 0):.1f} "
                        f"Clr={scores.get('clarity', 0):.1f} "
                        f"Rep={scores.get('reproducibility', 0):.1f} "
                        f"Sig={scores.get('significance', 0):.1f}")

        discoveries = result.get("discoveries", [])
        if discoveries:
            lines.append(f"\n**Discoveries ({len(discoveries)}):**")
            for d in discoveries:
                lines.append(f"  💡 {d.get('description', '')[:150]}")

        if result.get("errors"):
            lines.append(f"\n⚠️  **Errors ({len(result['errors'])}):**")
            for e in result["errors"]:
                lines.append(f"  • {e[:200]}")

        return "\n".join(lines)

    def run_full_discovery(
        self,
        topic: str,
        hypothesis: str = "",
    ) -> str:
        """
        Run a full discovery pipeline with experiments and paper generation.
        Returns a formatted text summary.
        """
        result = self.run_discovery(
            topic=topic,
            hypothesis=hypothesis,
            run_experiments=True,
            generate_paper=True,
        )

        lines = [
            f"🧬 **Full Scientific Discovery: {topic}**",
            f"  Status: Phase {result.get('phase', 'unknown')}",
            f"  Confidence: {result.get('confidence', 0):.0%}",
            f"  Duration: {result.get('duration_s', 0):.1f}s",
            "",
        ]

        # Hypothesis
        if result.get("hypothesis"):
            lines.append(f"**Hypothesis:** {result['hypothesis'][:200]}")

        # Novelty
        nc = result.get("novelty_check", {})
        if nc:
            lines.append(f"**Novelty:** {nc.get('verdict', 'unknown')} — {nc.get('message', '')[:200]}")

        # Experiment
        exp = result.get("experiment_result", {})
        if exp:
            status = exp.get("status", "unknown")
            duration = exp.get("duration_s", 0)
            lines.append(f"**Experiment:** {status} ({duration:.1f}s)")

        # Results
        analysis = result.get("experiment_analysis", {})
        if analysis:
            interp = analysis.get("interpretation", "")
            if interp:
                lines.append(f"**Analysis:** {interp}")

        # Validation
        cv = result.get("cross_validation", {})
        if cv:
            lines.append(f"**Validation:** Score {cv.get('validity_score', 0):.0%} — {cv.get('recommendation', 'N/A')}")

        # Peer Review
        pr = result.get("peer_review", {})
        if pr:
            scores = pr.get("scores", {})
            lines.append(
                f"**Peer Review:** {pr.get('recommendation', 'N/A')} "
                f"(overall {scores.get('overall', 0):.2f}/5.0)"
            )

        # Paper
        paper = result.get("paper", {})
        if paper:
            paper_path = paper.get("tex_path", "")
            lines.append(f"**Paper:** Generated ({paper.get('venue', 'Report')}) — {paper_path}")

        # Discoveries
        discoveries = result.get("discoveries", [])
        if discoveries:
            lines.append(f"\n**Discoveries:**")
            for d in discoveries:
                lines.append(f"  💡 {d.get('description', '')[:150]}")

        # Errors
        errors = result.get("errors", [])
        if errors:
            lines.append(f"\n⚠️  **{len(errors)} Warnings:**")
            for e in errors:
                lines.append(f"  • {e[:200]}")

        return "\n".join(lines)

    def get_history(self, limit: int = 10) -> list[dict]:
        """Get discovery history."""
        with self._lock:
            return list(reversed(self._history[-limit:]))

    def format_history(self, limit: int = 5) -> str:
        """Format discovery history for display."""
        history = self.get_history(limit)
        if not history:
            return "No discoveries have been run yet."

        lines = [f"📚 **Discovery History ({len(self._history)} total)**", ""]
        for h in history:
            lines.append(
                f"  • {h.get('report_id', '?')}: "
                f"\"{h.get('topic', '?')[:60]}\" — "
                f"Phase: {h.get('phase', '?')} — "
                f"Conf: {h.get('confidence', 0):.0%}"
            )
        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Get discovery engine statistics."""
        with self._lock:
            total = len(self._history)
            with_papers = sum(1 for h in self._history if h.get("paper"))
            with_experiments = sum(1 for h in self._history if h.get("experiment_result"))
            avg_confidence = (
                sum(h.get("confidence", 0) for h in self._history) / total
                if total > 0 else 0
            )

            return {
                "total_discoveries": self._discovery_count,
                "sessions_completed": total,
                "with_papers": with_papers,
                "with_experiments": with_experiments,
                "average_confidence": round(avg_confidence, 3),
                "status": "ready",
            }


# ── Singleton ──────────────────────────────────────────────────

_discovery_engine = None
_discovery_lock = threading.Lock()


def get_discovery_engine() -> DiscoveryEngine:
    global _discovery_engine
    if _discovery_engine is None:
        with _discovery_lock:
            if _discovery_engine is None:
                _discovery_engine = DiscoveryEngine()
    return _discovery_engine
