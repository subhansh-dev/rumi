"""
hypothesis_engine.py — Research Hypothesis Generation for RUMI Scientist AI

Generates, tracks, and evaluates scientific research hypotheses.
Supports hypothesis refinement, experiment suggestion, and confidence tracking.
"""

import threading
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

STATE_FILE = Path(__file__).resolve().parent / "hypothesis_state.json"


class Hypothesis:
    """A single research hypothesis with tracking metadata."""

    def __init__(
        self,
        title: str,
        description: str,
        domain: str = "",
        source: str = "user",
        status: str = "proposed",
    ):
        self.id = f"HYP-{int(time.time() * 1000)}"
        self.title = title
        self.description = description
        self.domain = domain
        self.source = source  # 'user', 'generated', 'from_paper', 'from_discussion'
        self.status = status  # proposed, refining, testing, validated, rejected
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.confidence = 0.0  # 0.0 to 1.0
        self.evidence = []  # list of evidence strings
        self.experiments = []  # list of suggested experiment descriptions
        self.tags = []
        self.notes = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "domain": self.domain,
            "source": self.source,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "experiments": self.experiments,
            "tags": self.tags,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Hypothesis":
        h = cls(
            title=data.get("title", ""),
            description=data.get("description", ""),
            domain=data.get("domain", ""),
            source=data.get("source", "user"),
            status=data.get("status", "proposed"),
        )
        h.id = data.get("id", h.id)
        h.created_at = data.get("created_at", h.created_at)
        h.updated_at = data.get("updated_at", h.updated_at)
        h.confidence = data.get("confidence", 0.0)
        h.evidence = data.get("evidence", [])
        h.experiments = data.get("experiments", [])
        h.tags = data.get("tags", [])
        h.notes = data.get("notes", "")
        return h


class HypothesisEngine:
    """Manages research hypothesis lifecycle — generation, tracking, refinement."""

    def __init__(self):
        self._lock = threading.RLock()
        self._hypotheses: dict[str, Hypothesis] = {}
        self._load()

    # ── Persistence ────────────────────────────────────────────

    def _load(self):
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                for item in data.get("hypotheses", []):
                    h = Hypothesis.from_dict(item)
                    self._hypotheses[h.id] = h
        except Exception:
            self._hypotheses = {}

    def _save(self):
        try:
            STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "hypotheses": [h.to_dict() for h in self._hypotheses.values()],
                "last_updated": datetime.now().isoformat(),
            }
            STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ── CRUD ───────────────────────────────────────────────────

    def add_hypothesis(
        self,
        title: str,
        description: str,
        domain: str = "",
        source: str = "user",
        tags: Optional[list[str]] = None,
    ) -> Hypothesis:
        """Add a new hypothesis."""
        with self._lock:
            h = Hypothesis(
                title=title,
                description=description,
                domain=domain,
                source=source,
            )
            if tags:
                h.tags = tags
            self._hypotheses[h.id] = h
            self._save()
            return h

    def get_hypothesis(self, hyp_id: str) -> Optional[Hypothesis]:
        """Get a hypothesis by ID."""
        with self._lock:
            return self._hypotheses.get(hyp_id)

    def update_hypothesis(
        self,
        hyp_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        confidence: Optional[float] = None,
        evidence: Optional[list[str]] = None,
        experiments: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Update an existing hypothesis."""
        with self._lock:
            h = self._hypotheses.get(hyp_id)
            if not h:
                return False
            if title is not None:
                h.title = title
            if description is not None:
                h.description = description
            if status is not None:
                h.status = status
            if confidence is not None:
                h.confidence = max(0.0, min(1.0, confidence))
            if evidence is not None:
                h.evidence = evidence
            if experiments is not None:
                h.experiments = experiments
            if tags is not None:
                h.tags = tags
            if notes is not None:
                h.notes = notes
            h.updated_at = datetime.now().isoformat()
            self._save()
            return True

    def delete_hypothesis(self, hyp_id: str) -> bool:
        """Delete a hypothesis."""
        with self._lock:
            if hyp_id in self._hypotheses:
                del self._hypotheses[hyp_id]
                self._save()
                return True
            return False

    # ── Queries ─────────────────────────────────────────────────

    def list_hypotheses(
        self,
        status: Optional[str] = None,
        domain: Optional[str] = None,
        sort_by: str = "created",
        limit: int = 20,
    ) -> list[Hypothesis]:
        """List hypotheses with optional filtering."""
        with self._lock:
            results = list(self._hypotheses.values())

            if status:
                results = [h for h in results if h.status == status]
            if domain:
                results = [h for h in results if domain.lower() in h.domain.lower()]

            if sort_by == "confidence":
                results.sort(key=lambda h: h.confidence, reverse=True)
            elif sort_by == "updated":
                results.sort(key=lambda h: h.updated_at, reverse=True)
            else:  # created
                results.sort(key=lambda h: h.created_at, reverse=True)

            return results[:limit]

    def search_hypotheses(self, query: str) -> list[Hypothesis]:
        """Search hypotheses by keyword."""
        with self._lock:
            q = query.lower()
            results = []
            for h in self._hypotheses.values():
                if (
                    q in h.title.lower()
                    or q in h.description.lower()
                    or q in h.domain.lower()
                    or any(q in t.lower() for t in h.tags)
                ):
                    results.append(h)
            return results

    def get_stats(self) -> dict:
        """Get hypothesis engine statistics."""
        with self._lock:
            total = len(self._hypotheses)
            by_status = {}
            by_domain = {}
            avg_confidence = 0.0

            for h in self._hypotheses.values():
                by_status[h.status] = by_status.get(h.status, 0) + 1
                if h.domain:
                    by_domain[h.domain] = by_domain.get(h.domain, 0) + 1
                avg_confidence += h.confidence

            if total > 0:
                avg_confidence /= total

            return {
                "total_hypotheses": total,
                "by_status": by_status,
                "by_domain": by_domain,
                "average_confidence": round(avg_confidence, 3),
            }

    # ── Generation (template-based, LLM-enhanced) ──────────────

    def generate_hypothesis_template(self, domain: str, topic: str) -> str:
        """Generate a hypothesis template for a given domain and topic.
        
        This provides a structured template that an LLM can fill in.
        """
        templates = {
            "machine_learning": (
                f"**Hypothesis:** {topic}\n\n"
                "**Null Hypothesis (H₀):** [No effect / no relationship]\n"
                "**Alternative Hypothesis (H₁):** [Expected effect / relationship]\n\n"
                "**Independent Variable:** [What you change]\n"
                "**Dependent Variable:** [What you measure]\n"
                "**Control Variables:** [What stays constant]\n\n"
                "**Prediction:** If [IV], then [DV] because [mechanism].\n\n"
                "**Experiment Design:**\n"
                "1. [Step 1]\n"
                "2. [Step 2]\n"
                "3. [Step 3]\n\n"
                "**Evaluation Metric:** [How success is measured]\n"
                "**Baseline:** [Current state-of-the-art / random baseline]"
            ),
            "cognitive_science": (
                f"**Hypothesis:** {topic}\n\n"
                "**Background Theory:** [Relevant theory / framework]\n"
                "**Cognitive Mechanism:** [Proposed mechanism]\n\n"
                "**Prediction:** [Observable behavior / measurement]\n\n"
                "**Experimental Paradigm:** [Task design]\n"
                "**Expected Result:** [Predicted outcome]\n"
                "**Alternative Explanation:** [What else could explain the result]\n\n"
                "**Confounds to Control:** [Potential confounding variables]"
            ),
            "software_engineering": (
                f"**Hypothesis:** {topic}\n\n"
                "**Current Approach:** [Existing method / baseline]\n"
                "**Proposed Approach:** [New method]\n\n"
                "**Expected Improvement:** [Quantified prediction]\n"
                "**Metrics:** [Performance / quality / efficiency metrics]\n\n"
                "**Implementation Plan:**\n"
                "1. [Step 1]\n"
                "2. [Step 2]\n"
                "3. [Step 3]\n\n"
                "**Validation:** [How to verify improvement]\n"
                "**Threats to Validity:** [Potential issues]"
            ),
        }

        return templates.get(
            domain.lower().replace(" ", "_"),
            f"**Hypothesis:** {topic}\n\n**Domain:** {domain}\n**Prediction:** [What do you expect to happen?]\n**Evidence Needed:** [What data would confirm or refute this?]"
        )

    def get_status_summary(self) -> str:
        """Get a human-readable summary of all hypotheses."""
        with self._lock:
            if not self._hypotheses:
                return "No hypotheses recorded yet."

            stats = self.get_stats()
            lines = [f"📊 **Hypothesis Engine — {stats['total_hypotheses']} total**", ""]

            if stats["by_status"]:
                lines.append("**By Status:**")
                for status, count in sorted(stats["by_status"].items()):
                    emoji = {
                        "proposed": "💡",
                        "refining": "🔧",
                        "testing": "🧪",
                        "validated": "✅",
                        "rejected": "❌",
                    }.get(status, "📄")
                    lines.append(f"  {emoji} {status.capitalize()}: {count}")
                lines.append("")

            if stats["by_domain"]:
                lines.append("**By Domain:**")
                for domain, count in sorted(stats["by_domain"].items()):
                    lines.append(f"  📂 {domain}: {count}")
                lines.append("")

            if stats["average_confidence"] > 0:
                pct = stats["average_confidence"] * 100
                bars = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                lines.append(f"**Avg Confidence:** {bars} {pct:.0f}%")

            return "\n".join(lines)


# ── Singleton ──────────────────────────────────────────────────
_instance: Optional[HypothesisEngine] = None


def get_hypothesis_engine() -> HypothesisEngine:
    global _instance
    if _instance is None:
        _instance = HypothesisEngine()
    return _instance
