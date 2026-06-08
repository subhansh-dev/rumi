"""
curious_questioning.py - Phase 0: The Newton Step

Before literature review, before gap detection:
  1. OBSERVE: What is surprising about this topic?
  2. QUESTION: Why does this happen? What if X were different?
  3. GENERALIZE: Does this same pattern appear somewhere ELSE? (Newton's move)
  4. CONSTRAINT: Build forbidden_theories + required_properties for Track B
  5. REFRAME: Turn the observation into a testable question
  6. SEARCH: Find papers about the WHY

This produces a question-driven hypothesis that gets merged
with the broad pipeline results. User gets BOTH.

NEW: Also produces a CONSTRAINT object for Track B pipeline:
  - forbidden_theories: theories that Track B must NOT reproduce
  - required_properties: what a novel theory must satisfy
  - cross_domain_connections: Newton-style generalizations
"""
import re


class CuriousQuestioning:
    """Phase 0: Generate the question that drives discovery."""

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def run(self, topic, domain, papers=None, cross_domain_papers=None):
        """Run curious questioning on a topic.

        Args:
            topic: Research topic or observation
            domain: Domain key (e.g. physics, space_astronomy)
            papers: Domain-specific papers for observations
            cross_domain_papers: Papers from OTHER domains for generalization

        Returns:
            dict with observations, questions, core_question, hypothesis,
            AND a constraint object for Track B pipeline.
        """
        result = {"observations": [], "questions": [],
                  "reframed": "", "question_hypothesis": "",
                  "why_it_matters": "", "generalizations": [],
                  "constraint": None}

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

        # ── NEW: GENERALIZE — Newton's move ──
        # Connect the anomaly to something ELSE in a different domain
        if self.llm_call:
            generalizations = self._generalize(topic, domain, observations,
                                                result["reframed"],
                                                papers or [], cross_domain_papers)
            result["generalizations"] = generalizations

        # ── NEW: GENERATE CONSTRAINT — for Track B pipeline ──
        constraint = self._generate_constraint(topic, domain, result["reframed"],
                                                result["question_hypothesis"],
                                                observations, result["generalizations"],
                                                papers or [])
        result["constraint"] = constraint

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

    # ═══════════════════════════════════════════════════════════════
    # NEW: GENERALIZE — Newton's Move
    # ═══════════════════════════════════════════════════════════════

    def _generalize(self, topic, domain, observations, core_question,
                    domain_papers, cross_domain_papers):
        """
        Newton's move: Does this same phenomenon appear somewhere ELSE?

        Newton saw the apple fall and asked: does the same force hold the Moon?
        He connected TWO things nobody had connected: apple-falling (near) with
        moon-orbiting (far). The data already existed. The CONNECTION was new.

        This method finds cross-domain connections — similar patterns in
        different fields that might share a common underlying cause.

        Args:
            topic: Research topic
            domain: Domain key
            observations: Surprising observations from Phase 0
            core_question: The deep question from Phase 0
            domain_papers: Papers from the main domain
            cross_domain_papers: Papers from OTHER domains

        Returns:
            List of generalization dicts:
            [{"domain_a": "...", "observation_a": "...",
              "domain_b": "...", "observation_b": "...",
              "connection": "...", "hypothesis": "..."}]
        """
        obs_lines = []
        for o in observations[:5]:
            if isinstance(o, dict):
                obs_lines.append(f"- {o.get('observation', '')[:100]}")
        obs_text = "\n".join(obs_lines) if obs_lines else "No specific observations yet."

        cross_lines = []
        if cross_domain_papers:
            for p in cross_domain_papers[:8]:
                if isinstance(p, dict):
                    title = p.get("title", "?")[:80]
                    abstract = (p.get("abstract") or "")[:150]
                    src_domain = p.get("source_domain", p.get("source", "unknown"))
                    cross_lines.append(f"- [{src_domain}] {title}: {abstract}")
        cross_text = "\n".join(cross_lines) if cross_lines else "No cross-domain papers available."

        prompt = f"""You are Newton. You just observed something surprising about: {topic}

OBSERVATIONS FROM LITERATURE:
{obs_text}

CORE QUESTION: {core_question or "Not yet determined"}

CROSS-DOMAIN PAPERS (from OTHER fields):
{cross_text}

Now do what Newton did with the apple and the moon:

Newton saw an apple fall. Everyone saw apples fall. But Newton asked:
"Does the SAME force that pulls the apple also hold the Moon in orbit?"

He connected TWO observations that nobody had connected:
  - Observation A (near Earth): Apple falls to ground
  - Observation B (far from Earth): Moon orbits Earth
  - Connection: SAME FORCE at different scales
  - Hypothesis: Inverse square law of gravitational attraction

Your task: Find 2-3 CROSS-DOMAIN CONNECTIONS for this topic.

For each connection:
1. OBSERVATION A: The surprising finding in the main domain ({domain})
2. OBSERVATION B: A SIMILAR pattern in a DIFFERENT domain (from cross-domain papers or your knowledge)
3. CONNECTION: Why might these be the SAME underlying phenomenon?
4. HYPOTHESIS: If they share a cause, what would that cause be?
5. NOVELTY: Has anyone proposed this connection before? (yes/no/unknown)

IMPORTANT:
- The connection must be SPECIFIC, not vague ("both involve energy" is too vague)
- The hypothesis must be TESTABLE — it must make a prediction that differs from existing theories
- The connection should be SURPRISING — something a domain expert wouldn't immediately see

Output JSON:
{{"generalizations": [
  {{
    "observation_a": "What we see in the main domain",
    "domain_a": "{domain}",
    "observation_b": "What we see in a different domain",
    "domain_b": "the other domain",
    "connection": "Why these might be the same phenomenon",
    "hypothesis": "If they share a cause, what is it?",
    "novelty": "yes|no|unknown",
    "testable_prediction": "What prediction does this connection make that existing theories don't?"
  }}
]}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=2048)
            if raw:
                from discovery.json_extract import extract_json
                result = extract_json(raw if isinstance(raw, str) else str(raw))
                if isinstance(result, dict):
                    generalizations = result.get("generalizations", [])
                    # Validate: each must have observation_a, observation_b, connection
                    valid = []
                    for g in generalizations:
                        if isinstance(g, dict):
                            if g.get("observation_a") and g.get("observation_b") and g.get("connection"):
                                valid.append(g)
                    if valid:
                        return valid
        except Exception:
            pass
        return []

    # ═══════════════════════════════════════════════════════════════
    # NEW: GENERATE CONSTRAINT — For Track B Pipeline
    # ═══════════════════════════════════════════════════════════════

    def _generate_constraint(self, topic, domain, core_question, hypothesis,
                             observations, generalizations, papers):
        """
        Build a constraint object for Track B pipeline.

        The constraint tells the mechanism generator and theory tournament:
        - What theories they MUST NOT reproduce (forbidden_theories)
        - What a novel theory MUST satisfy (required_properties)
        - What cross-domain connections to explore (generalizations)

        This is what makes Track B produce genuinely novel mechanisms
        instead of reproducing known theories from the literature.

        Returns:
            {
                "core_question": "What if dark matter isn't particles?",
                "forbidden_theories": ["MOND", "TeVeS", "Emergent Gravity", ...],
                "required_properties": ["explains galaxy rotation curves without DM particles", ...],
                "cross_domain_connections": [{"observation_a": ..., "observation_b": ..., ...}],
                "novelty_direction": "gravity modification from information-theoretic principles",
                "constraint_prompt": "Ready-to-use prompt fragment for mechanism generator"
            }
        """
        # Build observation summary
        obs_lines = []
        for o in observations[:5]:
            if isinstance(o, dict):
                obs_lines.append(f"- {o.get('observation', '')[:100]}")
        obs_text = "\n".join(obs_lines) if obs_lines else "No specific observations yet."

        # Build generalization summary
        gen_lines = []
        for g in generalizations[:3]:
            if isinstance(g, dict):
                gen_lines.append(
                    f"- Connection: {g.get('connection', '')[:100]}\n"
                    f"  Hypothesis: {g.get('hypothesis', '')[:100]}"
                )
        gen_text = "\n".join(gen_lines) if gen_lines else "No cross-domain connections found yet."

        prompt = f"""You are building a CONSTRAINT for a scientific discovery pipeline.

TOPIC: {topic}
DOMAIN: {domain}
CORE QUESTION: {core_question or "Not yet determined"}
HYPOTHESIS: {hypothesis or "Not yet determined"}

OBSERVATIONS:
{obs_text}

CROSS-DOMAIN CONNECTIONS:
{gen_text}

Your task: Build a constraint that forces the pipeline to generate NOVEL theories,
not reproduce existing ones from the literature.

Step 1: IDENTIFY FORBIDDEN THEORIES
List 3-5 existing theories that the pipeline should NOT reproduce.
These are well-known explanations already in the literature.
Example: For dark matter topic → ["MOND", "TeVeS", "Emergent Gravity", "f(R) gravity"]

Step 2: DEFINE REQUIRED PROPERTIES
What must a novel theory satisfy? 2-4 specific requirements.
Example: ["explains galaxy rotation curves without dark matter particles",
          "makes a prediction that differs from MOND"]

Step 3: DEFINE NOVELTY DIRECTION
What direction should novel theories explore?
Example: "gravity modification from information-theoretic principles"

Step 4: BUILD CONSTRAINT PROMPT
Write a ready-to-use prompt fragment that can be appended to the mechanism
generator and theory tournament prompts. This fragment should:
- List the forbidden theories
- List the required properties
- Explain WHY these are forbidden (they're already in the literature)
- Encourage first-principles derivation, not literature reproduction

Output JSON:
{{
  "forbidden_theories": ["Theory 1", "Theory 2", ...],
  "required_properties": ["Property 1", "Property 2", ...],
  "novelty_direction": "What direction to explore",
  "constraint_prompt": "Ready-to-use prompt fragment (2-3 paragraphs)"
}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=2048)
            if raw:
                from discovery.json_extract import extract_json
                result = extract_json(raw if isinstance(raw, str) else str(raw))
                if isinstance(result, dict):
                    constraint = {
                        "core_question": core_question or topic,
                        "forbidden_theories": result.get("forbidden_theories", []),
                        "required_properties": result.get("required_properties", []),
                        "novelty_direction": result.get("novelty_direction", ""),
                        "constraint_prompt": result.get("constraint_prompt", ""),
                        "cross_domain_connections": generalizations,
                    }
                    return constraint
        except Exception:
            pass

        # Fallback: build a basic constraint without LLM
        return {
            "core_question": core_question or topic,
            "forbidden_theories": [],
            "required_properties": [],
            "novelty_direction": "",
            "constraint_prompt": "",
            "cross_domain_connections": generalizations,
        }
