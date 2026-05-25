"""
research_team.py — Multi-Agent Research Team

Simulates a collaborative research team with specialized roles.
Inspired by:
  - Google's Co-Scientist (multi-agent collaboration)
  - AI Scientist (specialized agents for ideation, execution, review)
  - Scientific peer review and debate dynamics

Team Roles:
  [RT-1] Lead Researcher — Sets research direction and synthesizes findings
  [RT-2] Methodologist — Designs rigorous experimental methodology
  [RT-3] Critic — Finds flaws, gaps, and potential improvements
  [RT-4] Analyst — Interprets results and extracts insights
  [RT-5] Scribe — Documents findings and generates reports

Capabilities:
  - Collaborative research planning
  - Structured debate between roles
  - Consensus building and synthesis
  - Multi-perspective evaluation of hypotheses
  - Automated research protocol generation

Thread-safe.
"""

import json
import random
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()

# Role definitions
ROLES = {
    "lead": {
        "name": "Lead Researcher",
        "expertise": "Research direction, hypothesis formulation, synthesis",
        "perspective": "Big picture — how does this fit into the broader field?",
        "style": "Visionary and integrative",
    },
    "methodologist": {
        "name": "Methodologist",
        "expertise": "Experimental design, statistics, reproducibility",
        "perspective": "Rigor — is the methodology sound and well-controlled?",
        "style": "Careful and precise",
    },
    "critic": {
        "name": "Critic",
        "expertise": "Falsification, boundary conditions, alternative explanations",
        "perspective": "Skepticism — what could be wrong? What are the alternatives?",
        "style": "Constructively skeptical",
    },
    "analyst": {
        "name": "Analyst",
        "expertise": "Data interpretation, pattern recognition, quantitative reasoning",
        "perspective": "Evidence — what do the data actually say?",
        "style": "Data-driven and objective",
    },
    "scribe": {
        "name": "Scribe",
        "expertise": "Documentation, communication, knowledge distillation",
        "perspective": "Clarity — how do we communicate this effectively?",
        "style": "Clear and structured",
    },
}

# Debate templates for structured discussion
DEBATE_PROMPTS = {
    "hypothesis_review": {
        "instruction": "Review the following research hypothesis.",
        "questions": {
            "lead": "Is this hypothesis worth pursuing? Why?",
            "methodologist": "Can this hypothesis be empirically tested?",
            "critic": "What are the strongest arguments against this hypothesis?",
            "analyst": "What evidence would convincingly support or refute this?",
        },
    },
    "experiment_review": {
        "instruction": "Review the proposed experimental design.",
        "questions": {
            "lead": "Does this experiment adequately address the hypothesis?",
            "methodologist": "Are the controls and measurements appropriate?",
            "critic": "What confounds or biases are not addressed?",
            "analyst": "Are the planned analyses appropriate for the data?",
        },
    },
    "result_interpretation": {
        "instruction": "Interpret the experimental results.",
        "questions": {
            "lead": "What do these results mean for our research direction?",
            "methodologist": "Are the results statistically robust?",
            "critic": "What alternative interpretations exist?",
            "analyst": "What patterns and anomalies do you see in the data?",
        },
    },
    "paper_review": {
        "instruction": "Review the research paper or report.",
        "questions": {
            "lead": "Does the paper tell a compelling story?",
            "methodologist": "Is the methodology sufficiently described?",
            "critic": "What weaknesses need addressing before publication?",
            "analyst": "Are claims supported by the presented evidence?",
        },
    },
}


class ResearchTeam:
    """
    Multi-agent research team that collaborates on scientific tasks.
    Each role provides a unique perspective through structured responses.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._sessions: list[dict] = []

    def collaborate(
        self,
        topic: str,
        hypothesis: str = "",
        context: Optional[dict] = None,
        debate_type: str = "hypothesis_review",
    ) -> dict:
        """
        Run a collaborative research session with all team members.

        Args:
            topic: Research topic
            hypothesis: Optional specific hypothesis to evaluate
            context: Optional context (experimental results, methodology, etc.)
            debate_type: Type of debate (hypothesis_review, experiment_review, etc.)

        Returns:
            Dict with individual contributions, synthesis, and consensus
        """
        with self._lock:
            session_id = f"SESSION-{int(time.time() * 1000)}"
            context = context or {}

            # Get debate template
            template = DEBATE_PROMPTS.get(debate_type, DEBATE_PROMPTS["hypothesis_review"])

            # Each member contributes
            contributions = {}
            for role_key, role_info in ROLES.items():
                question = template.get("questions", {}).get(role_key, "What is your assessment?")
                contribution = self._simulate_contribution(
                    role_key, role_info, topic, hypothesis, context, question
                )
                contributions[role_key] = contribution

            # Synthesize into consensus
            synthesis = self._synthesize(contributions, topic, hypothesis)

            # Generate summary report
            report = self._generate_report(
                session_id, topic, hypothesis, contributions, synthesis
            )

            self._sessions.append(report)

            return report

    def _simulate_contribution(
        self,
        role_key: str,
        role_info: dict,
        topic: str,
        hypothesis: str,
        context: dict,
        question: str,
    ) -> dict:
        """
        Simulate a research team member's contribution.
        Each role provides a structured response based on its expertise.
        """
        role_name = role_info["name"]

        response = {
            "role": role_name,
            "role_key": role_key,
            "expertise": role_info["expertise"],
            "perspective": role_info["perspective"],
            "response": self._generate_role_response(role_key, topic, hypothesis, context, question),
            "confidence": random.uniform(0.5, 0.9),
        }

        # Role-specific analysis
        if role_key == "lead":
            response["key_points"] = self._lead_analysis(topic, hypothesis)
            response["verdict"] = "promising" if len(hypothesis) > 20 else "needs_refinement"

        elif role_key == "methodologist":
            response["methodology_assessment"] = self._methodologist_assessment(hypothesis, context)
            response["rigor_score"] = round(random.uniform(0.4, 0.9), 2)

        elif role_key == "critic":
            response["concerns"] = self._critic_concerns(topic, hypothesis)
            response["risk_score"] = round(random.uniform(0.2, 0.8), 2)

        elif role_key == "analyst":
            response["data_requirements"] = self._analyst_requirements(hypothesis, context)
            response["evidence_quality"] = "strong" if context.get("results") else "insufficient"

        elif role_key == "scribe":
            response["summary"] = self._scribe_summary(topic, hypothesis, context)
            response["clarity_score"] = round(random.uniform(0.5, 0.95), 2)

        return response

    def _generate_role_response(
        self, role: str, topic: str, hypothesis: str,
        context: dict, question: str,
    ) -> str:
        """Generate a role-specific response text."""
        if role == "lead":
            assess = "this hypothesis is well-formulated and addresses a gap in the field. " if len(hypothesis) > 50 else "the research direction needs more precise formulation. "
            return (
                f"As Lead Researcher examining '{topic[:100]}', I assess that "
                f"{assess}"
                f"Our approach should consider how this relates to existing paradigms "
                f"and what novel contribution we can make."
            )

        if role == "methodologist":
            assess = "using controlled experiments with proper randomization and blinding. " if not context.get("methodology") else "the proposed methodology is largely sound. "
            return (
                f"From a methodological standpoint, I recommend "
                f"{assess}"
                f"We need to ensure adequate sample sizes, appropriate statistical tests, "
                f"and clear documentation of all procedures for reproducibility."
            )

        if role == "critic":
            assess = "the hypothesis is too vague to be falsifiable. " if len(hypothesis) < 30 else "the hypothesis is testable but has boundary conditions. "
            return (
                f"As Critic, I identify several concerns: "
                f"{assess}"
                f"We must consider alternative explanations, potential confounds, "
                f"and whether the predicted effects are practically significant, "
                f"not just statistically significant."
            )

        if role == "analyst":
            assess = "we need more data before drawing conclusions. " if not context.get("results") else "the data show interesting patterns worth exploring. "
            return (
                f"My analysis suggests that "
                f"{assess}"
                f"Key quantitative aspects to consider: effect sizes, confidence intervals, "
                f"and the practical significance of any findings."
            )

        if role == "scribe":
            assess = "The team has identified a promising research direction. " if len(hypothesis) > 20 else "The team recommends refining the hypothesis. "
            return (
                f"To summarize the discussion: we are investigating {topic[:100]}. "
                f"{assess}"
                f"Key next steps include experimental design, data collection, and analysis planning."
            )

        return f"Assessing {topic[:100]} from the perspective of {role}."

    def _lead_analysis(self, topic: str, hypothesis: str) -> list[str]:
        """Lead Researcher: identify key points."""
        points = [
            f"Research on {topic[:80]} addresses a relevant question",
            "The proposed direction aligns with current trends in the field",
        ]
        if hypothesis:
            points.append(f"Hypothesis is {'well-formulated' if len(hypothesis) > 50 else 'needs refinement'}")
        return points

    def _methodologist_assessment(self, hypothesis: str, context: dict) -> str:
        """Methodologist: assess experimental rigor."""
        if context.get("methodology"):
            return "Methodology is present but should be reviewed for best practices"
        return "No methodology specified — controlled experiments with randomization needed"

    def _critic_concerns(self, topic: str, hypothesis: str) -> list[str]:
        """Critic: identify potential issues."""
        concerns = [
            "Consider whether the hypothesis is falsifiable",
            "Check for potential confounds and alternative explanations",
        ]
        if len(hypothesis) < 30:
            concerns.append("Hypothesis is too vague — needs operationalization")
        if not topic:
            concerns.append("Research topic needs clearer boundaries")
        return concerns

    def _analyst_requirements(self, hypothesis: str, context: dict) -> list[str]:
        """Analyst: specify data requirements."""
        return [
            "Quantitative measurements with known precision",
            "Adequate sample size for desired statistical power",
            "Control group or baseline for comparison",
        ]

    def _scribe_summary(self, topic: str, hypothesis: str, context: dict) -> str:
        """Scribe: generate meeting summary."""
        return (
            f"Research team discussion on: {topic[:100]}. "
            f"Hypothesis: {hypothesis[:150] if hypothesis else 'To be formulated'}. "
            f"Status: {'Context provided, ready for experimentation' if context else 'Initial exploration phase'}."
        )

    def _synthesize(self, contributions: dict, topic: str, hypothesis: str) -> dict:
        """Synthesize individual contributions into a consensus."""
        # Extract verdicts
        lead_verdict = contributions.get("lead", {}).get("verdict", "needs_refinement")
        rigor_score = contributions.get("methodologist", {}).get("rigor_score", 0.5)
        risk_score = contributions.get("critic", {}).get("risk_score", 0.5)
        evidence_quality = contributions.get("analyst", {}).get("evidence_quality", "insufficient")

        # Compute consensus
        consensus_score = 0.5 + (rigor_score - 0.5) * 0.3 - (risk_score - 0.5) * 0.3
        if evidence_quality == "strong":
            consensus_score += 0.1

        consensus_score = max(0.0, min(1.0, consensus_score))

        # Collective recommendation
        if consensus_score >= 0.7:
            recommendation = "proceed"
        elif consensus_score >= 0.4:
            recommendation = "proceed_with_caution"
        else:
            recommendation = "reconsider"

        # Key takeaways from all members
        all_takeaways = []
        for role_key, contrib in contributions.items():
            role_name = ROLES.get(role_key, {}).get("name", role_key)
            response_text = contrib.get("response", "")
            all_takeaways.append(f"**{role_name}**: {response_text[:150]}")

        return {
            "consensus_score": round(consensus_score, 3),
            "recommendation": recommendation,
            "key_takeaways": all_takeaways,
            "lead_verdict": lead_verdict,
            "overall_rigor": rigor_score,
            "overall_risk": risk_score,
            "evidence_quality": evidence_quality,
        }

    def _generate_report(
        self,
        session_id: str,
        topic: str,
        hypothesis: str,
        contributions: dict,
        synthesis: dict,
    ) -> dict:
        """Generate a structured research team report."""
        return {
            "session_id": session_id,
            "topic": topic,
            "hypothesis": hypothesis,
            "timestamp": datetime.now().isoformat(),
            "team_size": len(contributions),
            "contributions": contributions,
            "synthesis": synthesis,
        }

    def format_report(self, report: dict) -> str:
        """Format a research team report for display."""
        topic = report.get("topic", "Unknown Topic")
        hypothesis = report.get("hypothesis", "")
        synthesis = report.get("synthesis", {})

        lines = [
            f"👥 **Research Team Discussion**",
            f"  Topic: {topic[:100]}",
        ]

        if hypothesis:
            lines.append(f"  Hypothesis: {hypothesis[:150]}")

        lines.extend([
            "",
            "**Team Contributions:**",
        ])

        for role_key, contrib in report.get("contributions", {}).items():
            role_name = contrib.get("role", role_key)
            response = contrib.get("response", "")[:200]
            confidence = contrib.get("confidence", 0.5)

            emoji = {
                "lead": "🎯", "methodologist": "🔬",
                "critic": "⚡", "analyst": "📊", "scribe": "✏️",
            }.get(role_key, "👤")

            lines.append(f"  {emoji} **{role_name}** (conf: {confidence:.0%})")
            lines.append(f"    {response}")

            # Role-specific details
            if role_key == "critic":
                concerns = contrib.get("concerns", [])
                for c in concerns:
                    lines.append(f"    ⚠️  {c}")
            elif role_key == "lead":
                points = contrib.get("key_points", [])
                for p in points:
                    lines.append(f"    💡 {p}")

        lines.extend([
            "",
            "**Synthesis & Consensus:**",
            f"  Consensus Score: {synthesis.get('consensus_score', 0):.0%}",
            f"  Recommendation: **{synthesis.get('recommendation', 'unknown')}**",
            f"  Evidence Quality: {synthesis.get('evidence_quality', 'unknown')}",
        ])

        return "\n".join(lines)

    def debate(
        self,
        topic: str,
        hypothesis: str,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Run a structured debate between Critic and Lead Researcher.
        Useful for stress-testing a hypothesis.
        """
        context = context or {}

        # Round 1: Critic attacks, Lead defends
        critic_points = [
            "What is the null hypothesis and how would we falsify this claim?",
            "What alternative mechanisms could explain the same phenomenon?",
            "What are the boundary conditions beyond which this hypothesis breaks down?",
        ]

        lead_defense = [
            "The hypothesis is grounded in established theory",
            "It generates specific, testable predictions",
            "It has explanatory power beyond existing models",
        ]

        # Round 2: Methodologist evaluates the debate
        methodologist_evaluation = (
            "The debate reveals that the hypothesis has both strengths "
            "and testable weaknesses. Priority should be given to experiments "
            "that can distinguish between the proposed mechanism and alternatives."
        )

        return {
            "session_id": f"DEBATE-{int(time.time() * 1000)}",
            "topic": topic,
            "hypothesis": hypothesis,
            "rounds": [
                {
                    "round": 1,
                    "critic_points": critic_points,
                    "lead_defense": lead_defense,
                }
            ],
            "evaluation": methodologist_evaluation,
            "verdict": "testable_with_caveats",
        }

    def get_session_history(self, limit: int = 10) -> list[dict]:
        """Get recent research team sessions."""
        with self._lock:
            return list(reversed(self._sessions[-limit:]))

    def get_stats(self) -> dict:
        """Get research team statistics."""
        with self._lock:
            return {
                "total_sessions": len(self._sessions),
                "team_size": len(ROLES),
                "roles_available": list(ROLES.keys()),
                "status": "ready",
            }


# ── Singleton ──────────────────────────────────────────────────

_research_team = None
_team_lock = threading.Lock()


def get_research_team() -> ResearchTeam:
    global _research_team
    if _research_team is None:
        with _team_lock:
            if _research_team is None:
                _research_team = ResearchTeam()
    return _research_team
