"""
pipeline.py — RUMI Scientist AI: Enhanced Research Pipeline Orchestrator

Extends the core discovery_engine with:
  - Active learning loop (curiosity-driven topic prioritization)
  - Multi-agent research team integration
  - Reproducibility ↔ experiment designer link
  - BibTeX citation management
  - Self-improvement cycle (analyze past research to optimize future runs)
  - Real-world experiment hooks (API connections)
  - Full lifecycle: explore → hypothesize → experiment → reproduce → publish → iterate

Thread-safe. Persistent state in pipeline_state.json.
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()
STATE_FILE = SCIENTIST_DIR / "pipeline_state.json"


class PipelineReport:
    """Structured report from a full enhanced pipeline run."""

    def __init__(self, topic: str, mode: str = "full"):
        self.report_id = f"PIPELINE-{int(time.time() * 1000)}"
        self.topic = topic
        self.mode = mode
        self.phase = "initiated"
        self.literature_review: Optional[dict] = None
        self.novelty_check: Optional[dict] = None
        self.feynman_reduction: Optional[dict] = None
        self.research_team_session: Optional[dict] = None
        self.hypotheses: Optional[list] = None
        self.selected_hypothesis: str = ""
        self.experiment_design: Optional[dict] = None
        self.experiment_result: Optional[dict] = None
        self.experiment_analysis: Optional[dict] = None
        self.reproducibility_check: Optional[dict] = None
        self.cross_validation: Optional[dict] = None
        self.peer_review: Optional[dict] = None
        self.paper: Optional[dict] = None
        self.knowledge_graph_updates: Optional[list] = None
        self.discoveries: list = []
        self.learning_summary: Optional[dict] = None
        self.next_questions: list = []
        self.confidence: float = 0.0
        self.duration_s: float = 0.0
        self.errors: list = []
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class ResearchPipeline:
    """
    Enhanced research pipeline orchestrator.

    Builds on discovery_engine with active learning, reproducibility,
    multi-agent teams, BibTeX citations, and self-improvement cycles.

    Modes:
      - quick: literature review + novelty check + hypothesis
      - standard: quick + experiment + analysis
      - full: standard + reproducibility + review + paper + learn
      - explore: curiosity-driven topic discovery + quick
      - iterate: full + self-improvement analysis of past runs
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._history: list[dict] = []
        self._pipeline_count = 0
        self._last_run_stats: list[dict] = []
        self._load()

    def _load(self):
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                self._history = data.get("history", [])
                self._pipeline_count = data.get("pipeline_count", 0)
                self._last_run_stats = data.get("last_run_stats", [])
        except Exception:
            pass

    def _save(self):
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps({
                "history": self._history[-50:],
                "pipeline_count": self._pipeline_count,
                "last_run_stats": self._last_run_stats[-20:],
                "last_updated": datetime.now().isoformat(),
            }, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ────────────────────────────────────────────────────────────────

    def run(
        self,
        topic: str,
        hypothesis: str = "",
        mode: str = "full",
        domain: str = "",
        generate_paper: bool = True,
        run_experiments: bool = True,
        use_research_team: bool = True,
        verbose: bool = True,
    ) -> dict:
        """
        Run the enhanced research pipeline.

        Args:
            topic: Research topic or question
            hypothesis: Optional pre-defined hypothesis
            mode: quick | standard | full | explore | iterate
            domain: Scientific domain hint
            generate_paper: Whether to generate a paper
            run_experiments: Whether to execute experiments
            use_research_team: Whether to use multi-agent debate
            verbose: Include detailed output

        Returns:
            PipelineReport dict
        """
        with self._lock:
            self._pipeline_count += 1

        report = PipelineReport(topic, mode)
        start_time = time.time()

        # ── PHASE 0: Active Learning (curiosity-driven topic enrichment) ──
        if mode in ("explore", "iterate"):
            self._run_active_learning(report)

        # ── PHASE 1: Literature Review ──
        self._phase_literature_review(report, topic, domain)

        # ── PHASE 2: Novelty Check ──
        self._phase_novelty_check(report, topic)

        # ── PHASE 3: Feynman Reduction ──
        self._phase_feynman_reduction(report, topic)

        # ── PHASE 4: Multi-Agent Research Team ──
        if use_research_team:
            self._phase_research_team(report, topic, hypothesis or topic, domain)

        # ── PHASE 5: Hypothesis Generation & Selection ──
        self._phase_hypothesis_generation(report, topic, hypothesis)

        # ── PHASE 6: Experiment Design & Execution ──
        if run_experiments and mode in ("standard", "full", "iterate"):
            self._phase_experiment(report, topic, domain)

            # ── PHASE 7: Reproducibility Check ──
            if report.experiment_result:
                self._phase_reproducibility(report)

            # ── PHASE 8: Cross-Validation ──
            if report.experiment_result:
                self._phase_cross_validation(report)

        # ── PHASE 9: Peer Review ──
        if mode in ("full", "iterate"):
            self._phase_peer_review(report, topic)

        # ── PHASE 10: Paper Generation ──
        if generate_paper and mode in ("full", "iterate"):
            self._phase_paper_generation(report, topic)

        # ── PHASE 11: Knowledge Graph Update ──
        self._phase_knowledge_graph_update(report, topic)

        # ── PHASE 12: Self-Improvement (analyze past runs) ──
        if mode == "iterate":
            self._phase_self_improvement(report)

        # ── FINALIZE ──
        report.duration_s = time.time() - start_time
        report.confidence = self._compute_confidence(report)
        report.discoveries = self._extract_discoveries(report)
        report.next_questions = self._generate_next_questions(report)
        report.phase = "completed"

        with self._lock:
            self._history.append(report.to_dict())
            run_stats = {
                "report_id": report.report_id,
                "topic": topic,
                "mode": mode,
                "duration_s": report.duration_s,
                "confidence": report.confidence,
                "errors": len(report.errors),
                "timestamp": datetime.now().isoformat(),
            }
            self._last_run_stats.append(run_stats)
            self._save()

        return report.to_dict()

    # ────────────────────────────────────────────────────────────────
    # PHASE METHODS
    # ────────────────────────────────────────────────────────────────

    def _phase_active_learning(self, report: PipelineReport):
        """Curiosity-driven topic refinement using active inference."""
        try:
            from brain.curiosity import get_curiosity_module
            from brain.active_inference import get_active_inference
            curiosity = get_curiosity_module()
            aif = get_active_inference()

            # Get curiosity items related to topic
            queue = curiosity.get_curiosity_queue() if hasattr(curiosity, "get_curiosity_queue") else []
            if queue:
                related = [q for q in queue if report.topic.lower() in q.get("topic", "").lower()]
                if related:
                    report.literature_review = {
                        "curiosity_items": related[:3],
                        "exploration_suggestions": [r["topic"] for r in related[:3]],
                    }

            # Use active inference to estimate epistemic value of this topic
            if hasattr(aif, "get_state"):
                state = aif.get_state()
                report.learning_summary = {
                    "epistemic_curiosity": state.get("total_surprise", 0.5) if state else 0.5,
                }

            report.phase = "active_learning_done"
        except Exception as e:
            report.errors.append(f"Active learning phase: {e}")

    def _phase_literature_review(self, report: PipelineReport, topic: str, domain: str):
        """Search and synthesize related literature."""
        try:
            from scientist.scientist_search import get_scientist_search
            from actions.paper_search import paper_search

            literature = {"papers": [], "key_findings": [], "research_gaps": []}

            # Search papers across sources
            try:
                papers_result = paper_search(query=topic, max_results=15, source="all")
                if isinstance(papers_result, dict) and "papers" in papers_result:
                    literature["papers"] = papers_result["papers"][:10]
                elif isinstance(papers_result, str):
                    literature["search_summary"] = papers_result[:500]
            except Exception:
                pass

            # Scientist search for domain-specific researchers
            try:
                search = get_scientist_search()
                researcher_papers = search.search(topic=topic, max_results=10)
                if isinstance(researcher_papers, dict):
                    existing = literature.get("papers", [])
                    if isinstance(researcher_papers.get("papers"), list):
                        literature["papers"] = existing + researcher_papers["papers"][:5]
            except Exception:
                pass

            report.literature_review = literature
            report.phase = "literature_reviewed"
        except Exception as e:
            report.errors.append(f"Literature review phase: {e}")
            report.literature_review = {"papers": [], "error": str(e)}

    def _phase_novelty_check(self, report: PipelineReport, topic: str):
        """Assess novelty of the topic against existing literature."""
        try:
            from scientist.novelty_checker import get_novelty_checker
            checker = get_novelty_checker()
            report.novelty_check = checker.check_novelty(topic, max_papers=15)
            report.phase = "novelty_checked"
        except Exception as e:
            report.errors.append(f"Novelty check phase: {e}")
            report.novelty_check = {"novelty_score": 0.5, "verdict": "unknown"}

    def _phase_feynman_reduction(self, report: PipelineReport, topic: str):
        """First-principles decomposition."""
        try:
            from scientist.feynman_reducer import get_feynman_reducer
            reducer = get_feynman_reducer()
            report.feynman_reduction = reducer.reduce(topic)
            report.phase = "reduced"
        except Exception as e:
            report.errors.append(f"Feynman reduction phase: {e}")

    def _phase_research_team(self, report: PipelineReport, topic: str, hypothesis: str, domain: str):
        """Multi-agent research team collaboration (5-role debate)."""
        try:
            from scientist.research_team import get_research_team
            team = get_research_team()
            context = {}
            if report.literature_review:
                context["literature"] = report.literature_review
            if report.novelty_check:
                context["novelty"] = report.novelty_check
            if report.feynman_reduction:
                context["feynman"] = report.feynman_reduction

            report.research_team_session = team.collaborate(
                topic=topic,
                hypothesis=hypothesis,
                context=context,
            )
            report.phase = "team_collaborated"
        except Exception as e:
            report.errors.append(f"Research team phase: {e}")

    def _phase_hypothesis_generation(self, report: PipelineReport, topic: str, hypothesis: str):
        """Generate diverse hypotheses using tournament selection."""
        try:
            from scientist.tournament_hypothesis import get_tournament_engine
            engine = get_tournament_engine()

            if hypothesis:
                report.selected_hypothesis = hypothesis
                report.hypotheses = [{"title": hypothesis, "score": 1.0}]
            else:
                result = engine.generate_and_select(
                    topic=topic,
                    population_size=8,
                    generations=3,
                )
                if isinstance(result, dict):
                    report.hypotheses = result.get("candidates", [])
                    report.selected_hypothesis = result.get("selected", "")
                elif isinstance(result, str):
                    report.selected_hypothesis = result
                    report.hypotheses = [{"title": result, "score": 1.0}]
                else:
                    report.selected_hypothesis = topic
                    report.hypotheses = [{"title": topic, "score": 0.5}]

            report.phase = "hypothesis_formulated"
        except Exception as e:
            report.errors.append(f"Hypothesis generation phase: {e}")
            report.selected_hypothesis = hypothesis or topic
            report.hypotheses = [{"title": report.selected_hypothesis, "score": 0.5}]

    def _phase_experiment(self, report: PipelineReport, topic: str, domain: str):
        """Design, execute, and analyze experiments."""
        try:
            from scientist.experiment_designer import get_experiment_designer
            from scientist.active_experiment_selector import get_experiment_selector

            designer = get_experiment_designer()

            # Try Bayesian experiment selection first
            exp_type = self._detect_experiment_type(topic, report.selected_hypothesis)
            try:
                selector = get_experiment_selector()
                selection = selector.select_experiment(
                    hypothesis=report.selected_hypothesis,
                    domain=domain or topic,
                )
                if isinstance(selection, dict) and selection.get("selected"):
                    exp_type = selection["selected"].get("type", exp_type)
            except Exception:
                pass

            report.experiment_design = designer.design_experiment(
                hypothesis=report.selected_hypothesis,
                domain=domain or topic,
                experiment_type=exp_type,
            )
            report.phase = "experiment_designed"

            report.experiment_result = designer.run_experiment(
                report.experiment_design, timeout=120
            )

            report.experiment_analysis = designer.analyze_results(
                report.experiment_result
            )
            report.phase = "experiment_executed"
        except Exception as e:
            report.errors.append(f"Experiment phase: {e}")

    def _phase_reproducibility(self, report: PipelineReport):
        """Check reproducibility of experiment results."""
        try:
            from scientist.reproducibility_engine import get_reproducibility_engine
            engine = get_reproducibility_engine()

            report.reproducibility_check = engine.reproduce(
                text=json.dumps({
                    "hypothesis": report.selected_hypothesis,
                    "methodology": report.experiment_design.get("methodology", ""),
                    "results": report.experiment_result.get("results", {}),
                }, default=str),
                title=f"Reproducing: {report.topic[:80]}",
            )
            report.phase = "reproducibility_checked"
        except Exception as e:
            report.errors.append(f"Reproducibility phase: {e}")

    def _phase_cross_validation(self, report: PipelineReport):
        """Cross-validate experiment results."""
        try:
            from scientist.cross_validator import get_cross_validator
            validator = get_cross_validator()

            report.cross_validation = validator.validate_experiment(
                hypothesis=report.selected_hypothesis,
                results=report.experiment_result.get("results", {}),
                methodology=str(report.experiment_design.get("methodology", "")),
            )
            report.phase = "validated"
        except Exception as e:
            report.errors.append(f"Cross-validation phase: {e}")

    def _phase_peer_review(self, report: PipelineReport, topic: str):
        """Automated peer review of the research."""
        try:
            from scientist.peer_reviewer import get_peer_reviewer
            reviewer = get_peer_reviewer()

            report.peer_review = reviewer.review_paper(
                title=f"On the {topic[:80]}",
                abstract=f"Investigation of {topic[:200]}",
                hypothesis=report.selected_hypothesis,
                methodology=str(report.experiment_design.get("methodology", "Systematic investigation")
                               if report.experiment_design else "Systematic investigation"),
                results=report.experiment_result.get("results", {}) if report.experiment_result else {},
                conclusions=self._generate_conclusions(report),
                experiment_logs=report.experiment_result,
            )
            report.phase = "reviewed"
        except Exception as e:
            report.errors.append(f"Peer review phase: {e}")

    def _phase_paper_generation(self, report: PipelineReport, topic: str):
        """Generate paper with BibTeX citations from literature."""
        try:
            from scientist.paper_generator import get_paper_generator
            generator = get_paper_generator()

            related = []
            if report.literature_review:
                papers = report.literature_review.get("papers", [])
                related = [
                    {
                        "title": p.get("title", ""),
                        "authors": p.get("authors", []),
                        "year": p.get("year", ""),
                        "venue": p.get("venue", ""),
                        "url": p.get("url", ""),
                    }
                    for p in papers[:15]
                    if isinstance(p, dict) and p.get("title")
                ]
            if report.novelty_check:
                closest = report.novelty_check.get("closest_papers", [])
                for p in closest:
                    if isinstance(p, dict) and p.get("title") and p not in related:
                        related.append(p)

            report.paper = generator.generate_paper_from_discovery(
                topic=topic,
                hypothesis=report.selected_hypothesis,
                experiment_results=report.experiment_result.get("results", {})
                if report.experiment_result else {},
                experiment_analysis=report.experiment_analysis or {},
                related_papers=related,
            )

            # Add BibTeX citations
            if related:
                bibtex_entries = []
                for i, ref in enumerate(related[:20]):
                    key = f"{ref.get('authors', ['Unknown'])[0].split()[-1] if ref.get('authors') else 'Unknown'}{ref.get('year', 'n.d.')}"
                    key = key.replace(" ", "").replace(".", "")
                    authors = " and ".join(ref.get("authors", ["Unknown"])) if isinstance(ref.get("authors"), list) else "Unknown"
                    bibtex = f"@article{{{key},\n  title={{{ref.get('title', 'Untitled')}}},\n  author={{{authors}}},\n  year={{{ref.get('year', 'n.d.')}}},\n  journal={{{ref.get('venue', 'Unknown')}}}\n}}"
                    bibtex_entries.append({"key": key, "bibtex": bibtex})

                if isinstance(report.paper, dict):
                    report.paper["bibtex_entries"] = bibtex_entries
                    report.paper["citation_count"] = len(bibtex_entries)

            report.phase = "paper_generated"
        except Exception as e:
            report.errors.append(f"Paper generation phase: {e}")

    def _phase_knowledge_graph_update(self, report: PipelineReport, topic: str):
        """Update knowledge graph with findings from this pipeline run."""
        try:
            from scientist.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()

            updates = []
            entities_to_add = [
                {"name": topic[:100], "type": "concept", "description": f"Research topic: {topic[:300]}", "domain": topic[:50]},
            ]
            if report.selected_hypothesis:
                entities_to_add.append({
                    "name": report.selected_hypothesis[:100],
                    "type": "hypothesis",
                    "description": report.selected_hypothesis[:300],
                    "domain": topic[:50],
                })

            for entity in entities_to_add:
                try:
                    result = kg.add_entity(**entity)
                    updates.append(f"Added entity: {entity['name']}")
                except Exception:
                    pass

            # Add relation between topic and hypothesis
            if report.selected_hypothesis:
                try:
                    kg.add_relation(
                        source=topic[:100],
                        target=report.selected_hypothesis[:100],
                        relation_type="produces",
                        confidence=report.confidence,
                    )
                    updates.append("Added relation: topic → hypothesis")
                except Exception:
                    pass

            report.knowledge_graph_updates = updates
            report.phase = "kg_updated"
        except Exception as e:
            report.errors.append(f"Knowledge graph update: {e}")

    def _phase_self_improvement(self, report: PipelineReport):
        """Analyze past pipeline runs to improve future research."""
        try:
            with self._lock:
                recent_runs = self._last_run_stats[-10:]

            if len(recent_runs) >= 2:
                avg_duration = sum(r.get("duration_s", 0) for r in recent_runs) / len(recent_runs)
                avg_confidence = sum(r.get("confidence", 0) for r in recent_runs) / len(recent_runs)
                total_errors = sum(r.get("errors", 0) for r in recent_runs)

                improvement_suggestions = []

                if avg_duration > 300:
                    improvement_suggestions.append(
                        "Pipeline runs are taking >5min on average. "
                        "Consider using 'quick' mode for exploration and 'full' only for polished results."
                    )

                if avg_confidence < 0.4:
                    improvement_suggestions.append(
                        "Average confidence is low. "
                        "Consider deeper literature review and more rigorous experiment design."
                    )

                if total_errors > len(recent_runs):
                    improvement_suggestions.append(
                        "Error rate is high. Check module imports and API connectivity."
                    )

                report.learning_summary = {
                    "average_duration_s": round(avg_duration, 1),
                    "average_confidence": round(avg_confidence, 3),
                    "total_errors_recent": total_errors,
                    "runs_analyzed": len(recent_runs),
                    "improvement_suggestions": improvement_suggestions,
                    "trend": "improving" if avg_confidence > 0.5 else "needs_attention",
                }
            else:
                report.learning_summary = {
                    "note": "Not enough runs to analyze trends (need at least 2).",
                    "runs_analyzed": len(recent_runs),
                }

            report.phase = "self_improved"
        except Exception as e:
            report.errors.append(f"Self-improvement phase: {e}")

    # ────────────────────────────────────────────────────────────────
    # UTILITY METHODS
    # ────────────────────────────────────────────────────────────────

    def _detect_experiment_type(self, topic: str, hypothesis: str) -> str:
        """Auto-detect experiment type from topic/hypothesis text."""
        text = f"{topic} {hypothesis}".lower()
        if any(w in text for w in ["compare", "vs", "versus", "difference", "ablation"]):
            return "ablation"
        if any(w in text for w in ["statistical", "significant", "p-value", "hypothesis test"]):
            return "statistical_test"
        if any(w in text for w in ["predict", "regression", "forecast", "continuous"]):
            return "regression"
        return "classification"

    def _generate_conclusions(self, report: PipelineReport) -> str:
        """Generate conclusions from pipeline data."""
        parts = [f"In this investigation of {report.topic}, we formulated and tested hypotheses."]
        if report.selected_hypothesis:
            parts.append(f"The primary hypothesis was: {report.selected_hypothesis[:200]}")
        if report.experiment_analysis:
            interp = report.experiment_analysis.get("interpretation", "")
            if interp:
                parts.append(interp)
        if report.cross_validation:
            parts.append(
                f"Cross-validation yielded a validity score of "
                f"{report.cross_validation.get('validity_score', 0.5):.0%}."
            )
        if report.reproducibility_check:
            rep_score = report.reproducibility_check.get("reproducibility_score", 0.5) if isinstance(report.reproducibility_check, dict) else 0.5
            parts.append(f"Reproducibility score: {rep_score:.0%}.")
        if report.peer_review:
            scores = report.peer_review.get("scores", {})
            parts.append(f"Peer review: {scores.get('overall', 0):.2f}/5.0.")
        parts.append("Future work should explore extensions and address identified limitations.")
        return " ".join(parts)

    def _compute_confidence(self, report: PipelineReport) -> float:
        """Compute overall confidence from all pipeline stages."""
        scores = []
        novelty = report.novelty_check.get("novelty_score", 0.5) if report.novelty_check else 0.5
        scores.append(1.0 - novelty * 0.3)
        if report.experiment_result:
            scores.append(0.8 if report.experiment_result.get("status") == "completed" else 0.3)
        else:
            scores.append(0.3)
        if report.cross_validation:
            scores.append(report.cross_validation.get("validity_score", 0.5))
        if report.reproducibility_check:
            rep = report.reproducibility_check.get("reproducibility_score", 0.5) if isinstance(report.reproducibility_check, dict) else 0.5
            scores.append(rep)
        if report.peer_review:
            scores.append(report.peer_review.get("scores", {}).get("overall", 3) / 5.0)
        return sum(scores) / len(scores) if scores else 0.5

    def _extract_discoveries(self, report: PipelineReport) -> list:
        """Extract key discoveries from pipeline results."""
        discoveries = []
        if report.experiment_analysis:
            key = report.experiment_analysis.get("key_findings", [])
            if isinstance(key, list):
                discoveries.extend([str(k) for k in key[:3]])
            elif isinstance(key, str):
                discoveries.append(key)
        if report.cross_validation:
            findings = report.cross_validation.get("findings", [])
            if isinstance(findings, list):
                discoveries.extend([str(f) for f in findings[:2]])
        return discoveries[:5]

    def _generate_next_questions(self, report: PipelineReport) -> list:
        """Generate follow-up research questions."""
        questions = []
        topic = report.topic
        if report.novelty_check:
            gaps = report.novelty_check.get("research_gaps", [])
            if isinstance(gaps, list):
                questions.extend([str(g) for g in gaps[:2]])
        questions.append(f"What are the limitations of the current findings on {topic[:80]}?")
        questions.append(f"How do these results generalize across different conditions?")
        questions.append(f"What alternative hypotheses could explain the observations?")
        return questions[:5]

    def _run_active_learning(self, report: PipelineReport):
        """Active learning: use curiosity + active inference to enrich topic."""
        try:
            from brain.curiosity import get_curiosity_module
            from brain.active_inference import get_active_inference
            curiosity = get_curiosity_module()
            aif = get_active_inference()

            queue = curiosity.get_curiosity_queue() if hasattr(curiosity, "get_curiosity_queue") else []
            report.next_questions = [q.get("topic", "") for q in queue[:3] if isinstance(q, dict)]
            state = aif.get_state() if hasattr(aif, "get_state") else {}
            report.learning_summary = {"epistemic_curiosity": state.get("total_surprise", 0.5)} if state else {}
        except Exception:
            pass

    # ────────────────────────────────────────────────────────────────
    # QUERY METHODS
    # ────────────────────────────────────────────────────────────────

    def get_history(self, limit: int = 10) -> list:
        """Get recent pipeline run history."""
        with self._lock:
            return self._history[-limit:]

    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        with self._lock:
            total = self._pipeline_count
            if not self._last_run_stats:
                return {"total_runs": total, "status": "no_data"}
            avg_conf = sum(r.get("confidence", 0) for r in self._last_run_stats) / len(self._last_run_stats)
            avg_dur = sum(r.get("duration_s", 0) for r in self._last_run_stats) / len(self._last_run_stats)
            return {
                "total_runs": total,
                "runs_in_stats": len(self._last_run_stats),
                "average_confidence": round(avg_conf, 3),
                "average_duration_s": round(avg_dur, 1),
                "last_run": self._last_run_stats[-1] if self._last_run_stats else None,
            }

    def get_report(self, report_id: str) -> Optional[dict]:
        """Get a specific pipeline report by ID."""
        with self._lock:
            for r in self._history:
                if r.get("report_id") == report_id:
                    return r
        return None


_instance = None


def get_pipeline():
    """Factory function — returns singleton ResearchPipeline instance."""
    global _instance
    if _instance is None:
        _instance = ResearchPipeline()
    return _instance
