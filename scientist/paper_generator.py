"""
paper_generator.py — Scientific Paper Generation (LaTeX)

Generates structured academic papers from research data.
Inspired by AI Scientist's LaTeX paper pipeline.

Capabilities:
  [PG-1] Structure Generation — Create full LaTeX document skeleton (abstract, intro, methods, results, conclusion)
  [PG-2] Citation Management — Format citations from paper metadata
  [PG-3] Results Integration — Embed experiment results, tables, and figures
  [PG-4] Multiple Templates — Support for conference formats (NeurIPS, ICML, ACL) and journal styles
  [PG-5] Bibliography Generation — Create .bib files from research sources

Thread-safe. Stateless.
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()

# LaTeX templates for different publication venues
LATEX_TEMPLATES = {
    "neurips": {
        "class": "\\documentclass{article}\n"
                "\\usepackage[final]{neurips_2024}\n"
                "\\usepackage[utf8]{inputenc}\n"
                "\\usepackage{amsmath,amssymb,amsfonts}\n"
                "\\usepackage{booktabs}\n"
                "\\usepackage{graphicx}\n"
                "\\usepackage{hyperref}\n"
                "\\usepackage{cite}\n"
                "\\usepackage{array}\n",
        "style": "NeurIPS 2024",
    },
    "icml": {
        "class": "\\documentclass{article}\n"
                "\\usepackage[accepted]{icml2024}\n"
                "\\usepackage{amsmath,amssymb}\n"
                "\\usepackage{booktabs}\n"
                "\\usepackage{graphicx}\n"
                "\\usepackage{hyperref}\n"
                "\\usepackage{cite}\n",
        "style": "ICML 2024",
    },
    "arxiv": {
        "class": "\\documentclass{article}\n"
                "\\usepackage{amsmath,amssymb,amsfonts}\n"
                "\\usepackage{booktabs}\n"
                "\\usepackage{graphicx}\n"
                "\\usepackage{hyperref}\n"
                "\\usepackage{cite}\n"
                "\\usepackage[margin=1in]{geometry}\n",
        "style": "arXiv",
    },
    "report": {
        "class": "\\documentclass[11pt]{article}\n"
                "\\usepackage{amsmath,amssymb}\n"
                "\\usepackage{booktabs}\n"
                "\\usepackage{graphicx}\n"
                "\\usepackage{hyperref}\n"
                "\\usepackage[margin=1in]{geometry}\n"
                "\\usepackage{times}\n",
        "style": "Research Report",
    },
}


class PaperGenerator:
    """
    Generates scientific papers from research data, hypotheses, and experimental results.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._papers_generated = 0

    def generate_paper(
        self,
        title: str,
        authors: list[str],
        abstract: str,
        introduction: str,
        hypothesis: str,
        methodology: str,
        results: dict,
        conclusions: str,
        references: Optional[list[dict]] = None,
        venue: str = "arxiv",
        include_appendix: bool = True,
    ) -> dict:
        """
        Generate a complete LaTeX paper from research components.

        Args:
            title: Paper title
            authors: List of author names
            abstract: Paper abstract
            introduction: Introduction section text
            hypothesis: Research hypothesis
            methodology: Methodology description
            results: Dict of experimental results
            conclusions: Conclusions text
            references: Optional list of reference dicts with title, authors, year, url
            venue: Publication venue template (neurips, icml, arxiv, report)
            include_appendix: Whether to include an appendix

        Returns:
            Dict with full LaTeX source, bib file content, and metadata
        """
        with self._lock:
            self._papers_generated += 1

            template = LATEX_TEMPLATES.get(venue.lower(), LATEX_TEMPLATES["arxiv"])

            # Build document
            latex_parts = [template["class"]]

            # Title and authors
            latex_parts.append(f"\\title{{{self._escape_latex(title)}}}")
            latex_parts.append("\\author{")
            for i, author in enumerate(authors):
                if i > 0:
                    latex_parts.append("  \\and ")
                latex_parts.append(f"  {self._escape_latex(author)}")
            latex_parts.append("}")

            # Document body
            latex_parts.append("\\begin{document}")
            latex_parts.append("\\maketitle")

            # Abstract
            latex_parts.append("\\begin{abstract}")
            latex_parts.append(self._escape_latex(abstract))
            latex_parts.append("\\end{abstract}")

            # Introduction
            latex_parts.append("\\section{Introduction}")
            latex_parts.append(self._escape_latex(introduction))

            # Related Work (auto-generated from references)
            if references:
                latex_parts.append("\\section{Related Work}")
                latex_parts.append(
                    "Recent advances in this area have explored various approaches. "
                    "\\citet{" + ", ".join([f"ref{i+1}" for i in range(min(len(references), 5))]) + "} "
                    "provide foundational context for this work."
                )

            # Hypothesis
            latex_parts.append("\\section{Hypothesis}")
            latex_parts.append(self._escape_latex(hypothesis))

            # Methodology
            latex_parts.append("\\section{Methodology}")
            latex_parts.append(self._escape_latex(methodology))

            # Results
            latex_parts.append("\\section{Experiments and Results}")
            latex_parts.append(self._format_results_section(results))

            # Discussion
            latex_parts.append("\\section{Discussion}")
            latex_parts.append(
                "The experimental results presented in Section~\\ref{sec:results} "
                "provide evidence regarding our hypothesis. "
                "We find that " + self._escape_latex(self._summarize_results(results)) + " "
                "These findings have implications for future research in this direction."
            )

            # Conclusions
            latex_parts.append("\\section{Conclusion}")
            latex_parts.append(self._escape_latex(conclusions))

            # Appendix
            if include_appendix:
                latex_parts.append("\\appendix")
                latex_parts.append("\\section{Appendix}")
                latex_parts.append("\\subsection{Detailed Results}")
                latex_parts.append(self._format_appendix(results))

            # Bibliography
            latex_parts.append("\\bibliographystyle{plainnat}")
            latex_parts.append("\\bibliography{references}")

            latex_parts.append("\\end{document}")

            latex_source = "\n\n".join(latex_parts)

            # Generate .bib file
            bib_source = self._generate_bibtex(references or [])

            # Write to file
            paper_id = f"PAPER-{int(time.time() * 1000)}"
            output_dir = SCIENTIST_DIR / "papers"
            output_dir.mkdir(parents=True, exist_ok=True)

            tex_path = output_dir / f"{paper_id}.tex"
            bib_path = output_dir / f"{paper_id}.bib"

            try:
                tex_path.write_text(latex_source, encoding="utf-8")
                bib_path.write_text(bib_source, encoding="utf-8")
            except Exception:
                pass

            return {
                "paper_id": paper_id,
                "title": title,
                "venue": template["style"],
                "latex_source": latex_source,
                "bib_source": bib_source,
                "tex_path": str(tex_path),
                "bib_path": str(bib_path),
                "word_count": len(latex_source.split()),
                "generated_at": datetime.now().isoformat(),
            }

    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters."""
        replacements = [
            ("\\", "\\textbackslash{}"),
            ("{", "\\{"),
            ("}", "\\}"),
            ("$", "\\$"),
            ("&", "\\&"),
            ("#", "\\#"),
            ("^", "\\textasciicircum{}"),
            ("_", "\\_"),
            ("~", "\\textasciitilde{}"),
            ("%", "\\%"),
        ]
        for old, new in replacements:
            text = text.replace(old, new)
        return text

    def _format_results_section(self, results: dict) -> str:
        """Format experimental results as LaTeX section content with tables."""
        parts = []
        parts.append("\\label{sec:results}")
        parts.append("")

        if not results:
            parts.append("Results from our experiments are summarized below.")
            return "\n".join(parts)

        # Create table from key metrics
        parts.append("\\begin{table}[htbp]")
        parts.append("\\centering")
        parts.append("\\caption{Experimental Results}")
        parts.append("\\label{tab:results}")
        parts.append("\\begin{tabular}{lr}")
        parts.append("\\toprule")
        parts.append("Metric & Value \\\\")
        parts.append("\\midrule")

        for key, value in results.items():
            if isinstance(value, (int, float)):
                if isinstance(value, float):
                    formatted = f"{value:.4f}"
                else:
                    formatted = str(value)
                key_pretty = key.replace("_", " ").title()
                parts.append(f"{self._escape_latex(key_pretty)} & {formatted} \\\\")

        parts.append("\\bottomrule")
        parts.append("\\end{tabular}")
        parts.append("\\end{table}")

        # Key findings
        parts.append("")
        parts.append("Our experiments demonstrate the following key findings:")
        for key, value in results.items():
            if isinstance(value, (int, float)):
                if key in ("accuracy", "f1_score", "precision", "recall", "r2"):
                    parts.append(f"\\item {key.replace('_', ' ').title()}: {value:.1%}")
                elif key in ("mse", "mae"):
                    parts.append(f"\\item {key.upper()}: {value:.4f}")

        return "\n".join(parts)

    def _format_appendix(self, results: dict) -> str:
        """Format detailed results for the appendix."""
        parts = []
        parts.append("\\begin{table}[htbp]")
        parts.append("\\centering")
        parts.append("\\caption{Complete Experimental Results}")
        parts.append("\\begin{tabular}{lc}")
        parts.append("\\toprule")
        parts.append("Metric & Value \\\\")
        parts.append("\\midrule")

        for key, value in sorted(results.items()):
            if isinstance(value, (int, float)):
                if isinstance(value, float):
                    formatted = f"{value:.6f}"
                else:
                    formatted = str(value)
                parts.append(f"{key} & {formatted} \\\\")

        parts.append("\\bottomrule")
        parts.append("\\end{tabular}")
        parts.append("\\end{table}")

        return "\n".join(parts)

    def _summarize_results(self, results: dict) -> str:
        """Generate a human-readable summary of results."""
        insights = []
        if "accuracy" in results:
            insights.append(f"the model achieved {results['accuracy']:.1%} accuracy")
        if "f1_score" in results:
            insights.append(f"with an F1 score of {results['f1_score']:.1%}")
        if "r2" in results:
            insights.append(f"the model explains {results['r2']:.1%} of the variance (R²={results['r2']:.3f})")
        if "mse" in results:
            insights.append(f"the mean squared error was {results['mse']:.4f}")
        if "t_p_value" in results:
            if results.get("significant_at_005"):
                insights.append(f"the results are statistically significant (p={results['t_p_value']:.4f})")
            else:
                insights.append(f"the results did not reach statistical significance (p={results['t_p_value']:.4f})")
        if "cohens_d" in results:
            insights.append(f"with an effect size of d={results['cohens_d']:.2f}")

        return ", and ".join(insights) if insights else "the results provide mixed evidence"

    def _generate_bibtex(self, references: list[dict]) -> str:
        """Generate BibTeX entries from reference data."""
        entries = []
        for i, ref in enumerate(references):
            ref_id = f"ref{i+1}"
            title = self._escape_latex(ref.get("title", "Unknown Title"))
            authors = ref.get("authors", ["Unknown"])
            author_str = " and ".join(authors[:5])
            if len(authors) > 5:
                author_str += " and others"
            year = ref.get("year", "n.d.")
            url = ref.get("url", "")

            entry = (
                f"@misc{{{ref_id},\n"
                f"  author = {{{author_str}}},\n"
                f"  title = {{{title}}},\n"
                f"  year = {{{year}}},\n"
            )
            if url:
                entry += f"  url = {{{url}}},\n"
            entry += "}"

            entries.append(entry)

        return "\n\n".join(entries)

    def generate_paper_from_discovery(
        self,
        topic: str,
        hypothesis: str,
        experiment_results: dict,
        experiment_analysis: dict,
        related_papers: Optional[list[dict]] = None,
        venue: str = "arxiv",
    ) -> dict:
        """
        Generate a complete paper from a discovery pipeline run.
        Convenience method that auto-fills sections from discovery data.
        """
        # Build abstract from components
        abstract = (
            f"This paper investigates the hypothesis: {hypothesis[:300]}. "
            f"Through systematic experimentation, we evaluate this hypothesis "
            f"and present our findings. "
            f"Our analysis reveals key insights into {topic[:200]}."
        )

        # Build introduction
        introduction = (
            f"The study of {topic} represents an important area of research "
            f"with significant implications. In this work, we propose to investigate "
            f"a novel hypothesis derived from current understanding of the field. "
            f"Our approach builds upon existing work while exploring new directions."
        )

        # Build methodology
        methodology = (
            f"To test our hypothesis, we designed a series of experiments "
            f"using standard evaluation protocols. "
            f"Experimental results were analyzed using appropriate statistical methods."
        )

        # Build conclusions
        conclusions = (
            f"In this paper, we investigated {topic[:200]}. "
            f"Our experimental results provide evidence that "
            f"{self._summarize_results(experiment_results)}. "
            f"Future work should explore extensions of this approach "
            f"and address limitations identified in our analysis."
        )

        # Extract metrics from experiment results
        metrics = {}
        if isinstance(experiment_results, dict):
            for key, value in experiment_results.items():
                if isinstance(key, str) and isinstance(value, (int, float)):
                    metrics[key] = value

        # Also include analysis metrics
        if isinstance(experiment_analysis, dict):
            analysis_metrics = experiment_analysis.get("metrics", {})
            metrics.update(analysis_metrics)

        return self.generate_paper(
            title=f"On the {topic[:80]}",
            authors=["RUMI AI Scientist"],
            abstract=abstract,
            introduction=introduction,
            hypothesis=hypothesis,
            methodology=methodology,
            results=metrics,
            conclusions=conclusions,
            references=related_papers,
            venue=venue,
        )

    def generate_short_report(self, topic: str, findings: list[str], confidence: float = 0.5) -> str:
        """Generate a concise research report (plain text, not LaTeX)."""
        lines = [
            f"📋 **Research Report: {topic}**",
            f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"  Confidence: {confidence:.0%}",
            "",
            "**Findings:**",
        ]

        for i, finding in enumerate(findings, 1):
            lines.append(f"  {i}. {finding}")

        lines.extend([
            "",
            "**Methodology:**",
            "  - Literature search via Semantic Scholar and arXiv",
            "  - Hypothesis formulation and novelty checking",
            "  - Experimental validation where applicable",
            "  - Automated analysis and synthesis",
        ])

        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Get paper generator statistics."""
        with self._lock:
            papers_dir = SCIENTIST_DIR / "papers"
            paper_count = 0
            try:
                if papers_dir.exists():
                    paper_count = len(list(papers_dir.glob("*.tex")))
            except Exception:
                pass

            return {
                "papers_generated": self._papers_generated,
                "papers_on_disk": paper_count,
                "status": "ready",
            }


# ── Singleton ──────────────────────────────────────────────────

_paper_generator = None
_paper_lock = threading.Lock()


def get_paper_generator() -> PaperGenerator:
    global _paper_generator
    if _paper_generator is None:
        with _paper_lock:
            if _paper_generator is None:
                _paper_generator = PaperGenerator()
    return _paper_generator
