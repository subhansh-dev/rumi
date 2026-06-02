"""
multi_agent_debate.py — Multiple AI agents debate a hypothesis.

Instead of one LLM generating a theory and rubber-stamping it,
multiple agents with different roles argue:

1. PROPOSER: generates the hypothesis
2. CRITIC: attacks it, finds flaws
3. ADVOCATE: defends it, finds supporting evidence
4. SYNTHESIZER: finds the truth between them

This prevents groupthink and forces the theory to survive scrutiny.
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class DebateRound:
    """A single round of debate."""
    agent: str
    role: str
    argument: str
    strength: str  # "strong", "moderate", "weak"
    specific_points: List[str]
    score: float  # 0-100


@dataclass
class DebateResult:
    """Result of a full debate."""
    hypothesis: str
    rounds: List[DebateRound]
    proposer_score: float
    critic_score: float
    advocate_score: float
    synthesizer_score: float
    final_verdict: str  # "accept", "revise", "reject"
    confidence: float  # 0-1
    key_insights: List[str]
    revisions_needed: List[str]


# --- Debate Prompts ---

PROPOSER_PROMPT = """You are the PROPOSER. You generate hypotheses.

Given a topic and literature, propose a specific, testable hypothesis.

Requirements:
1. Make a BOLD claim (not a vague platitude)
2. State it as: "X causes Y because Z"
3. Include at least ONE quantitative prediction
4. Explain the mechanism (how it works)
5. Explain what observation would FALSIFY it

Topic: {topic}
Literature: {literature}

Generate exactly ONE hypothesis. Be specific. Include numbers.
Format:
CLAIM: [one sentence claim]
MECHANISM: [how it works]
PREDICTION: [quantitative prediction with numbers]
FALSIFICATION: [what would disprove it]
NOVELTY: [why this is new, not just restating known physics]"""

CRITIC_PROMPT = """You are the CRITIC. Your job is to DESTROY this hypothesis.

Find every flaw:
1. Does it violate known physics? (check constants, conservation laws)
2. Are the numbers reasonable? (order of magnitude)
3. Is the mechanism actually explained or just hand-waving?
4. Has someone already proposed this? (check for prior art)
5. Is there a simpler explanation? (Occam's razor)
6. Are there internal contradictions?

Hypothesis: {hypothesis}
Known data: {known_data}
Domain ontology: {ontology}

Attack it hard. Be specific. Cite physics.
Format:
FLAW 1: [specific flaw]
FLAW 2: [specific flaw]
...
VERDICT: [fatal_faws / serious_concerns / minor_issues / no_issues]
SEVERITY: [0-10, where 10 = completely destroys the hypothesis]"""

ADVOCATE_PROMPT = """You are the ADVOCATE. Your job is to DEFEND this hypothesis.

The critic attacked it. Find the defense:
1. Address each flaw specifically
2. Show supporting evidence
3. Show the mechanism CAN work
4. Show the predictions are testable
5. Compare with alternative explanations

Hypothesis: {hypothesis}
Critic's attack: {critique}
Supporting evidence: {evidence}

Defend it. Be specific. Cite evidence.
Format:
DEFENSE 1: [address flaw 1]
DEFENSE 2: [address flaw 2]
...
SUPPORTING EVIDENCE: [what supports this]
VERDICT: [strong_defense / partial_defense / weak_defense / indefensible]
REMAINING_VULNERABILITIES: [what can't be defended]"""

SYNTHESIZER_PROMPT = """You are the SYNTHESIZER. You find the truth.

Given the proposer's hypothesis, the critic's attack, and the advocate's defense,
determine what is actually true.

Consider:
1. Which critic flaws are FATAL vs addressable?
2. Which advocate defenses are valid vs hand-waving?
3. What is the NET assessment?
4. What REVISIONS would make the hypothesis stronger?
5. What EXPERIMENTS would settle the debate?

Hypothesis: {hypothesis}
Proposer: {proposal}
Critic: {critique}
Advocate: {defense}
Simulation results: {simulation}

Be specific and quantitative.
Format:
NET ASSESSMENT: [2-3 sentences]
STRENGTHS: [numbered list]
WEAKNESSES: [numbered list]
REVISIONS NEEDED: [specific changes]
EXPERIMENTS TO SETTLE: [specific tests]
FINAL SCORE: [0-100]
VERDICT: [accept / revise / reject]
CONFIDENCE: [0-1]"""


class MultiAgentDebate:
    """
    Orchestrates a multi-agent debate on a hypothesis.
    """

    def __init__(self):
        self.prompts = {
            "proposer": PROPOSER_PROMPT,
            "critic": CRITIC_PROMPT,
            "advocate": ADVOCATE_PROMPT,
            "synthesizer": SYNTHESIZER_PROMPT,
        }

    def run_debate(self, hypothesis: str, topic: str = "",
                   literature: str = "", known_data: str = "",
                   ontology: str = "", evidence: str = "",
                   simulation: str = "",
                   llm_fn=None) -> DebateResult:
        """
        Run the full debate.

        Args:
            hypothesis: The hypothesis to debate (or topic to generate from)
            topic: Research topic
            literature: Literature context
            known_data: Known observational data
            ontology: Domain ontology terms
            evidence: Supporting evidence
            simulation: Simulation results
            llm_fn: LLM call function (async or sync)

        Returns:
            DebateResult with full debate transcript and verdict
        """
        rounds = []

        # If no hypothesis provided, proposer generates one
        if not hypothesis and llm_fn:
            proposal_prompt = self.prompts["proposer"].format(
                topic=topic, literature=literature
            )
            proposal_text = llm_fn(proposal_prompt)
            # Extract CLAIM
            if "CLAIM:" in proposal_text:
                hypothesis = proposal_text.split("CLAIM:")[1].split("\n")[0].strip()
            else:
                hypothesis = proposal_text[:200]
        elif not hypothesis:
            hypothesis = f"Hypothesis about {topic}"

        rounds.append(DebateRound(
            agent="proposer", role="Generates hypothesis",
            argument=hypothesis,
            strength="moderate",
            specific_points=[hypothesis],
            score=60.0
        ))

        # If no LLM function, return structured result with what we have
        if not llm_fn:
            return DebateResult(
                hypothesis=hypothesis,
                rounds=rounds,
                proposer_score=60.0,
                critic_score=0.0,
                advocate_score=0.0,
                synthesizer_score=0.0,
                final_verdict="revise",
                confidence=0.3,
                key_insights=["No LLM available for debate"],
                revisions_needed=["Run with LLM for full debate"],
            )

        # CRITIC attacks
        critic_prompt = self.prompts["critic"].format(
            hypothesis=hypothesis, known_data=known_data, ontology=ontology
        )
        critique = llm_fn(critic_prompt)
        critic_score = self._extract_score(critique)
        critic_strength = "strong" if critic_score > 70 else "moderate" if critic_score > 40 else "weak"

        rounds.append(DebateRound(
            agent="critic", role="Attacks hypothesis",
            argument=critique,
            strength=critic_strength,
            specific_points=self._extract_points(critique),
            score=critic_score
        ))

        # ADVOCATE defends
        advocate_prompt = self.prompts["advocate"].format(
            hypothesis=hypothesis, critique=critique, evidence=evidence
        )
        defense = llm_fn(advocate_prompt)
        advocate_score = self._extract_score(defense)

        rounds.append(DebateRound(
            agent="advocate", role="Defends hypothesis",
            argument=defense,
            strength="strong" if advocate_score > 70 else "moderate" if advocate_score > 40 else "weak",
            specific_points=self._extract_points(defense),
            score=advocate_score
        ))

        # SYNTHESIZER determines truth
        synthesizer_prompt = self.prompts["synthesizer"].format(
            hypothesis=hypothesis,
            proposal=hypothesis,
            critique=critique,
            defense=defense,
            simulation=simulation
        )
        synthesis = llm_fn(synthesizer_prompt)
        synthesizer_score = self._extract_score(synthesis)
        verdict = self._extract_verdict(synthesis)
        confidence = self._extract_confidence(synthesis)

        rounds.append(DebateRound(
            agent="synthesizer", role="Finds truth",
            argument=synthesis,
            strength="strong" if synthesizer_score > 70 else "moderate" if synthesizer_score > 40 else "weak",
            specific_points=self._extract_points(synthesis),
            score=synthesizer_score
        ))

        return DebateResult(
            hypothesis=hypothesis,
            rounds=rounds,
            proposer_score=60.0,
            critic_score=critic_score,
            advocate_score=advocate_score,
            synthesizer_score=synthesizer_score,
            final_verdict=verdict,
            confidence=confidence,
            key_insights=self._extract_insights(synthesis),
            revisions_needed=self._extract_revisions(synthesis),
        )

    def _extract_score(self, text: str) -> float:
        """Extract numeric score from text."""
        import re
        for pattern in [r'SCORE[:\s]*(\d+)', r'SEVERITY[:\s]*(\d+)',
                        r'(\d+)/100', r'(\d+)\s*out\s*of\s*100']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return 50.0

    def _extract_verdict(self, text: str) -> str:
        """Extract verdict from text."""
        text_lower = text.lower()
        if "accept" in text_lower:
            return "accept"
        elif "reject" in text_lower:
            return "reject"
        else:
            return "revise"

    def _extract_confidence(self, text: str) -> float:
        """Extract confidence from text."""
        import re
        match = re.search(r'CONFIDENCE[:\s]*([\d.]+)', text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 0.5

    def _extract_points(self, text: str) -> list:
        """Extract numbered points from text."""
        import re
        points = []
        for match in re.finditer(r'(?:FLAW|DEFENSE|STRENGTH|WEAKNESS|POINT)\s*\d+[:\s]*(.+)', text):
            points.append(match.group(1).strip()[:200])
        return points[:5]

    def _extract_insights(self, text: str) -> list:
        """Extract key insights."""
        import re
        insights = []
        in_section = False
        for line in text.split("\n"):
            if "STRENGTH" in line.upper():
                in_section = True
                continue
            if in_section and line.strip().startswith(("-", "*", "1.", "2.", "3.")):
                insights.append(line.strip().lstrip("-*0123456789. "))
        return insights[:5] or ["No specific insights extracted"]

    def _extract_revisions(self, text: str) -> list:
        """Extract needed revisions."""
        import re
        revisions = []
        in_section = False
        for line in text.split("\n"):
            if "REVISION" in line.upper():
                in_section = True
                continue
            if in_section and line.strip().startswith(("-", "*", "1.", "2.", "3.")):
                revisions.append(line.strip().lstrip("-*0123456789. "))
            if in_section and line.strip() == "":
                in_section = False
        return revisions[:5] or ["No specific revisions needed"]
