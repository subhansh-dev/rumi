"""
curious_questioning.py - Phase 0: The Newton Step

Before literature review, before gap detection:
  1. OBSERVE: What is surprising about this topic?
  2. QUESTION: Why does this happen? What if X were different?
  3. REFRAME: Turn the observation into a testable question
  4. SEARCH: Find papers about the WHY

This produces a question-driven hypothesis that gets merged
with the broad pipeline results. User gets BOTH.
"""
import re


class CuriousQuestioning:
    """Phase 0: Generate the question that drives discovery."""

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def run(self, topic, domain, papers=None):
        """Run curious questioning on a topic."""
        result = {"observations": [], "questions": [],
                  "reframed": "", "question_hypothesis": "",
                  "why_it_matters": ""}

        observations = self._extract_observations(topic, papers or [])
        result["observations"] = observations

        questions = self._generate_questions(topic, domain, observations)
        result["questions"] = questions

        if self.llm_call:
            llm = self._llm_questioning(topic, domain, observations)
            if llm:
                result["questions"].extend(llm.get("questions", []))
                result["question_hypothesis"] = llm.get("hypothesis", "")
                result["reframed"] = llm.get("core_question", "")
                result["why_it_matters"] = llm.get("why_this_matters", "")

        # Set reframed from first question if not set by LLM
        if not result["reframed"] and questions:
            first_q = questions[0]
            if isinstance(first_q, dict):
                result["reframed"] = first_q.get("question", "")
            else:
                result["reframed"] = str(first_q)

        # Add category summary
        categories = {}
        for q in questions:
            if isinstance(q, dict):
                cat = q.get("category", "unknown")
                categories[cat] = categories.get(cat, 0) + 1
        result["category_summary"] = categories

        return result

    def _extract_observations(self, topic, papers):
        """Extract surprising observations from papers."""
        observations = []
        stopwords = {"the","and","for","with","that","this","from","are",
                     "has","was","were","been","have","using","which","when","where","what"}
        topic_words = set(w for w in topic.lower().split() if len(w) > 3)
        topic_kw = topic_words - stopwords

        for p in papers:
            combined = ((p.get("title") or "") + " " + (p.get("abstract") or "")).lower()
            relevance = sum(1 for w in topic_kw if w in combined)
            if relevance < 2:
                continue

            surprise_patterns = [
                r"surprising[ly]?\s+.{10,80}",
                r"unexpected\s+.{10,80}",
                r"contradicts?\s+.{10,80}",
                r"however[,]?\s+.{10,80}",
                r"unlike\s+.{10,80}",
                r"despite\s+.{10,80}",
                r"paradox\s+.{10,80}",
                r"myster\w+\s+.{10,80}",
                r"unclear\s+.{10,80}",
                r"remains\s+.{10,80}",
                r"not well understood\s+.{10,60}",
                r"why\s+.{10,80}",
                r"how does\s+.{10,80}",
                r"what causes?\s+.{10,80}",
            ]
            for pat in surprise_patterns:
                for m in re.finditer(pat, combined):
                    observations.append({
                        "observation": m.group(0)[:150],
                        "source": p.get("title", "?")[:60],
                        "type": "surprising",
                    })

        seen = set()
        unique = []
        for obs in observations:
            key = obs["observation"][:40].lower()
            if key not in seen:
                seen.add(key)
                unique.append(obs)
        return unique[:10]

    # The 5 categories of discovery questions (from the other AI's insight)
    QUESTION_CATEGORIES = {
        "assumption_attack": {
            "name": "Assumption Attack",
            "template": "What assumption does everyone accept about {topic}? What if it's wrong?",
            "description": "Challenges the foundational assumptions everyone takes for granted",
        },
        "missing_variable": {
            "name": "Missing Variable",
            "template": "What unmeasured quantity could explain {topic} that nobody is looking at?",
            "description": "Finds hidden factors that could explain the observations",
        },
        "scale_transfer": {
            "name": "Scale Transfer",
            "template": "Does a mechanism at one scale (quantum/molecular/atomic) also exist at another scale (macroscopic/cosmic)?",
            "description": "Crosses scale boundaries to find analogous mechanisms",
        },
        "cross_domain": {
            "name": "Cross-Domain",
            "template": "What field solved an analogous problem to {topic}? What can we borrow?",
            "description": "Imports solutions from other fields",
        },
        "anomaly": {
            "name": "Anomaly",
            "template": "What observation about {topic} remains unexplained by the dominant theory?",
            "description": "Targets contradictions and unexplained observations",
        },
    }

    def _generate_questions(self, topic, domain, observations):
        """Generate questions in 5 specific categories (not generic 'Why?' questions)."""
        questions = []

        # Category 1: Assumption attacks
        questions.append({
            "category": "assumption_attack",
            "question": f"What assumption does everyone accept about {topic[:50]}? What if it's wrong?",
            "from_observation": False,
        })

        # Category 2: Missing variables — from observations
        for obs in observations[:2]:
            text = obs["observation"].lower()
            if any(w in text for w in ["unclear", "unknown", "not understood", "mystery", "paradox"]):
                questions.append({
                    "category": "missing_variable",
                    "question": f"What unmeasured quantity could explain: {obs['observation'][:80]}?",
                    "from_observation": True,
                })

        # Category 3: Scale transfer
        questions.append({
            "category": "scale_transfer",
            "question": f"Does a mechanism at one scale (quantum/molecular) also drive {topic[:50]} at another scale (macroscopic/cosmic)?",
            "from_observation": False,
        })

        # Category 4: Cross-domain — from observations
        for obs in observations[:2]:
            text = obs["observation"].lower()
            if any(w in text for w in ["however", "despite", "unlike", "contradicts"]):
                questions.append({
                    "category": "cross_domain",
                    "question": f"What field solved an analogous problem to: {obs['observation'][:80]}?",
                    "from_observation": True,
                })

        # Category 5: Anomaly — from observations
        for obs in observations[:2]:
            text = obs["observation"].lower()
            if any(w in text for w in ["surprising", "unexpected", "paradox", "anomal"]):
                questions.append({
                    "category": "anomaly",
                    "question": f"Why does this observation remain unexplained: {obs['observation'][:80]}?",
                    "from_observation": True,
                })

        # Add generic questions if not enough category-specific ones
        topic_words = topic.lower().split()
        core = " ".join(w for w in topic_words if len(w) > 4)[:40]
        if core and len(questions) < 5:
            questions.append({
                "category": "assumption_attack",
                "question": f"What if the standard model of {core} is fundamentally incomplete?",
                "from_observation": False,
            })

        return questions[:8]

    def _llm_questioning(self, topic, domain, observations):
        """Use LLM to generate deep questions in 5 specific categories."""
        obs_lines = []
        for o in observations[:5]:
            obs_lines.append("- " + o.get("observation","")[:100])
        obs_text = chr(10).join(obs_lines) if obs_lines else "No specific observations found yet."

        prompt = (
            "You are a curious scientist like Newton, Einstein, or Darwin.\n"
            "Your job is to ask the DEEP QUESTIONS that lead to discoveries.\n\n"
            "TOPIC: " + topic + "\n"
            "DOMAIN: " + domain + "\n\n"
            "OBSERVATIONS FROM LITERATURE:\n" + obs_text + "\n\n"
            "Generate questions in these 5 categories:\n\n"
            "1. ASSUMPTION ATTACK: What assumption does everyone accept? What if it's wrong?\n"
            "2. MISSING VARIABLE: What unmeasured quantity could explain the observations?\n"
            "3. SCALE TRANSFER: Does a mechanism at one scale also exist at another?\n"
            "4. CROSS-DOMAIN: What field solved an analogous problem?\n"
            "5. ANOMALY: What observation remains unexplained by the dominant theory?\n\n"
            "For each category, generate 1-2 specific, testable questions.\n\n"
            "Then pick the ONE most important question as the core_question.\n\n"
            'Output JSON:\n'
            '{"core_question": "The one deep question that drives discovery",\n'
            ' "why_this_matters": "Why answering this would be a breakthrough",\n'
            ' "hypothesis": "Your best guess at the answer",\n'
            ' "questions": [\n'
            '   {"category": "assumption_attack", "question": "..."},\n'
            '   {"category": "missing_variable", "question": "..."},\n'
            '   {"category": "scale_transfer", "question": "..."},\n'
            '   {"category": "cross_domain", "question": "..."},\n'
            '   {"category": "anomaly", "question": "..."}\n'
            ' ]}'
        )

        try:
            raw = self.llm_call(prompt, max_tokens=2048)
            if raw:
                from discovery.json_extract import extract_json
                result = extract_json(raw if isinstance(raw, str) else str(raw))
                if isinstance(result, dict):
                    return result
        except Exception:
            pass
        return None
