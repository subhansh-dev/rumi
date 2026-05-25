"""
feynman_reducer.py — First-Principles Scientific Decomposition Engine

Inspired by Richard Feynman's approach to understanding:
  "If you can't explain it simply, you don't understand it well enough."

Capabilities:
  [FR-1] First-Principles Decomposition — Break complex ideas into fundamental truths
  [FR-2] Simplification Analysis — Identify unnecessary complexity and jargon
  [FR-3] Analogy Generation — Create intuitive analogies for complex concepts
  [FR-4] Minimal Explanation — Generate the simplest possible explanation
  [FR-5] "What If" Exploration — Explore counterfactuals and edge cases
  [FR-6] Core Assumption Mining — Identify hidden assumptions in reasoning

Thread-safe. Stateless.
"""

import json
import math
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()

# Fundamental domains (primitive building blocks of scientific reasoning)
FUNDAMENTAL_DOMAINS = {
    "physics": [
        "Conservation laws (energy, momentum, charge)",
        "Forces and interactions (gravitational, electromagnetic, strong, weak)",
        "Quantum mechanics (wave-particle duality, superposition, uncertainty)",
        "Thermodynamics (entropy, temperature, energy transfer)",
        "Relativity (spacetime, speed of light limit)",
    ],
    "mathematics": [
        "Set theory and logic",
        "Number systems and arithmetic",
        "Geometry and topology",
        "Probability and statistics",
        "Calculus and rates of change",
    ],
    "computer_science": [
        "Information theory (bits, entropy, communication)",
        "Computation theory (algorithms, complexity, Turing machines)",
        "Data structures and organization",
        "Feedback and control systems",
    ],
    "biology": [
        "Evolution by natural selection",
        "Cell theory (cells as fundamental unit of life)",
        "DNA as information storage",
        "Homeostasis (feedback systems maintaining stability)",
        "Energy metabolism",
    ],
    "chemistry": [
        "Atomic theory and bonding",
        "Chemical reactions and conservation of mass",
        "Reaction rates and equilibrium",
        "Thermodynamics of chemical systems",
    ],
}


class FeynmanReducer:
    """
    Feynman-style reduction engine: decomposes complex ideas into
    fundamental principles and generates simple explanations.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._reductions_performed = 0

    def reduce(self, concept: str, domain: str = "") -> dict:
        """
        Perform a Feynman reduction on a concept or hypothesis.

        Args:
            concept: The idea, hypothesis, or phenomenon to reduce
            domain: Optional domain hint (physics, mathematics, etc.)

        Returns:
            Dict with decomposition, fundamentals, simple explanation, analogies,
            hidden assumptions, and what-if explorations
        """
        with self._lock:
            self._reductions_performed += 1

            concept_lower = concept.lower()

            # 1. Detect domains mentioned
            detected_domains = self._detect_domains(concept)
            if not detected_domains and domain:
                detected_domains = [domain]

            # 2. Extract core entities and relationships
            core_entities = self._extract_core_entities(concept)
            core_relationships = self._extract_relationships(concept, core_entities)

            # 3. Decompose to fundamentals
            fundamentals = self._decompose_to_fundamentals(concept, detected_domains)

            # 4. Generate simple explanation
            simple_explanation = self._generate_simple_explanation(concept, core_entities, fundamentals)

            # 5. Generate analogies
            analogies = self._generate_analogies(concept, detected_domains)

            # 6. Find hidden assumptions
            assumptions = self._find_assumptions(concept)

            # 7. What-if explorations
            what_ifs = self._generate_what_ifs(concept, core_entities)

            # 8. Minimal explanation (one sentence)
            minimal = self._minimal_explanation(concept, fundamentals)

            return {
                "concept": concept,
                "detected_domains": detected_domains,
                "core_entities": core_entities,
                "core_relationships": core_relationships,
                "fundamental_principles": fundamentals,
                "simple_explanation": simple_explanation,
                "minimal_explanation": minimal,
                "analogies": analogies,
                "hidden_assumptions": assumptions,
                "what_if_explorations": what_ifs,
                "complexity_score": self._compute_complexity(concept),
                "explainability_score": self._compute_explainability(fundamentals, analogies),
                "created_at": datetime.now().isoformat(),
            }

    def _detect_domains(self, text: str) -> list[str]:
        """Detect which scientific domains are relevant to the concept."""
        text_lower = text.lower()
        detected = []

        domain_keywords = {
            "physics": ["quantum", "gravity", "force", "energy", "momentum", "wave",
                       "particle", "field", "electromagnetic", "relativity", "speed of light",
                       "entropy", "thermodynamic", "photon", "electron", "atom"],
            "mathematics": ["equation", "function", "vector", "matrix", "derivative",
                          "integral", "probability", "statistics", "set", "theorem",
                          "algorithm", "proof", "axiom", "geometry", "topology"],
            "computer_science": ["algorithm", "data", "software", "code", "neural",
                                "network", "machine learning", "artificial intelligence",
                                "computation", "programming", "database", "server"],
            "biology": ["evolution", "dna", "gene", "protein", "cell", "organism",
                       "species", "natural selection", "mutation", "genome", "enzyme"],
            "chemistry": ["chemical", "molecule", "compound", "reaction", "bond",
                         "element", "atom", "electron", "valence", "catalyst"],
            "cognitive_science": ["brain", "neuron", "cognition", "memory", "learning",
                                 "perception", "consciousness", "attention",
                                 "neural", "cognitive", "psychology"],
        }

        for domain, keywords in domain_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected.append(domain)
                    break

        return detected[:3] if detected else ["general"]

    def _extract_core_entities(self, text: str) -> list[str]:
        """Extract core nouns and noun phrases from the concept."""
        # Simple extraction: capitalized words and multi-word phrases
        entities = []

        # Capitalized terms (proper nouns, specific concepts)
        cap_terms = re.findall(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\b', text)
        entities.extend([t for t in cap_terms if len(t) > 2])

        # Technical terms (lowercase but domain-specific)
        tech_terms = re.findall(r'\b([a-z]{3,}(?:[-_][a-z]{3,})+)\b', text.lower())
        entities.extend(set(tech_terms))

        return list(set(entities))[:10]

    def _extract_relationships(self, text: str, entities: list[str]) -> list[str]:
        """Extract relationships mentioned in the concept."""
        relationships = []

        relation_patterns = [
            (r'(\w+)\s+(causes?|leads to|results in|produces|creates)\s+(\w+)',
             "{0} → {1}: {2}"),
            (r'(\w+)\s+(depends on|requires|needs|uses)\s+(\w+)',
             "{0} depends on: {2}"),
            (r'(\w+)\s+(increases|decreases|improves|reduces)\s+(\w+)',
             "{0} affects: {2} ({1})"),
            (r'(\w+)\s+(is a|is an|can be|acts as)\s+(\w+)',
             "{0} is a type of: {2}"),
        ]

        for pattern, template in relation_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                relationships.append(template.format(*match))

        return relationships[:10]

    def _decompose_to_fundamentals(self, concept: str, domains: list[str]) -> list[str]:
        """Decompose the concept into fundamental principles."""
        fundamentals = []
        concept_lower = concept.lower()

        for domain in domains:
            principles = FUNDAMENTAL_DOMAINS.get(domain, [])
            matching = []
            for principle in principles:
                # Check if the principle relates to the concept
                principle_keywords = principle.lower().split()
                match_count = sum(1 for kw in principle_keywords if kw in concept_lower or len(kw) > 5)
                if match_count >= 1:
                    matching.append(f"[{domain}] {principle}")

            fundamentals.extend(matching[:3])

        return fundamentals[:6]

    def _generate_simple_explanation(
        self, concept: str, entities: list[str], fundamentals: list[str]
    ) -> str:
        """Generate a simple explanation of the concept."""
        # Use entities and fundamentals to construct explanation
        if not entities:
            return f"{concept[:100]} can be understood by examining its core principles."

        main_entity = entities[0] if entities else concept[:30]

        explanation = (
            f"At its core, {concept[:150]} is about how {main_entity} "
            f"interacts with its environment. "
        )

        if fundamentals:
            explanation += f"The fundamental principles involved include: {'; '.join(fundamentals[:3])}. "
        else:
            explanation += "The key is to understand the basic mechanisms at play. "

        explanation += (
            f"Think of it as a system where changes in one part "
            f"affect the behavior of the whole."
        )

        return explanation

    def _minimal_explanation(self, concept: str, fundamentals: list[str]) -> str:
        """Generate the simplest possible one-sentence explanation."""
        concept_short = concept[:80]
        if fundamentals:
            core = fundamentals[0].split("] ")[-1] if "] " in fundamentals[0] else fundamentals[0]
            return f"{concept_short} is fundamentally about {core.lower()}."
        return f"{concept_short} can be understood by examining its basic components and how they interact."

    def _generate_analogies(self, concept: str, domains: list[str]) -> list[str]:
        """Generate intuitive analogies for the concept."""
        concept_lower = concept.lower()
        analogies = []

        # Domain-specific analogies
        if "physics" in domains or any(w in concept_lower for w in ["energy", "force", "field"]):
            analogies.append(
                "Like water flowing downhill: systems naturally move toward lower energy states. "
                "The gradient determines the direction and speed of change."
            )
        if "mathematics" in domains or any(w in concept_lower for w in ["equation", "function"]):
            analogies.append(
                "Like a recipe: the inputs (ingredients) are transformed through a process "
                "into outputs (the finished dish). The recipe defines the relationship."
            )
        if "computer_science" in domains or any(w in concept_lower for w in ["algorithm", "data", "network"]):
            analogies.append(
                "Like a postal system: data packets travel through a network of sorting stations "
                "(nodes) following rules (protocols) to reach their destination."
            )
        if "biology" in domains or any(w in concept_lower for w in ["evolution", "cell", "gene"]):
            analogies.append(
                "Like a library with millions of books: information (DNA) is stored, "
                "copied, and occasionally edited. Useful books are kept, useless ones fade away."
            )
        if "cognitive_science" in domains or any(w in concept_lower for w in ["brain", "neuron", "memory"]):
            analogies.append(
                "Like a city's traffic system: billions of individual units (neurons/cars) "
                "follow simple rules, creating complex emergent patterns."
            )

        # General analogy
        if not analogies:
            analogies.append(
                "Like building with LEGO blocks: complex structures emerge from "
                "combining simple, fundamental pieces in different ways."
            )

        return analogies[:3]

    def _find_assumptions(self, concept: str) -> list[str]:
        """Identify hidden assumptions in the concept or reasoning."""
        assumptions = []
        concept_lower = concept.lower()

        # Check for common hidden assumptions
        if "linear" not in concept_lower and "linear" not in concept_lower:
            assumptions.append("Assumes relationships between variables are not necessarily linear")
        if "independent" not in concept_lower:
            assumptions.append("Assumes variables may interact with each other")
        if "static" not in concept_lower and "dynamic" not in concept_lower:
            assumptions.append("Assumes the system may be dynamic (changing over time)")
        if "optimal" in concept_lower or "best" in concept_lower:
            assumptions.append("Assumes there exists a single 'best' solution")
        if "simple" in concept_lower or "easy" in concept_lower:
            assumptions.append("Assumes the problem can be solved with simple methods")
        if "general" in concept_lower or "universal" in concept_lower:
            assumptions.append("Assumes findings generalize beyond specific conditions")

        # Scale assumptions
        if any(w in concept_lower for w in ["large", "big", "many", "all"]):
            assumptions.append("Assumes the approach scales to larger systems")
        if any(w in concept_lower for w in ["small", "few", "single"]):
            assumptions.append("Assumes small-scale behavior represents the whole system")

        if not assumptions:
            assumptions.append("No explicit assumptions detected — review may be needed")

        return assumptions[:5]

    def _generate_what_ifs(self, concept: str, entities: list[str]) -> list[str]:
        """Generate counterfactual explorations."""
        explorations = []
        concept_lower = concept.lower()

        if entities:
            main = entities[0]
            explorations.append(f"What if {main} were 10x larger/smaller? How would the system change?")
            explorations.append(f"What if {main} were removed entirely? What would break?")

        explorations.append("What if the constraints were relaxed? Would the same principles apply?")
        explorations.append("What if we approached this from first principles instead?")

        if any(w in concept_lower for w in ["maximum", "minimum", "optimal"]):
            explorations.append("What if we don't optimize at all? Is there a simpler path?")

        return explorations[:4]

    def _compute_complexity(self, concept: str) -> float:
        """Compute a complexity score (0.0 = trivial, 1.0 = extremely complex)."""
        score = 0.0

        # Length-based complexity
        score += min(len(concept) / 500, 0.3)

        # Jargon density
        words = concept.split()
        long_words = sum(1 for w in words if len(w) > 8)
        if words:
            score += min(long_words / len(words) * 2, 0.3)

        # Conjunction/complexity indicators
        indicators = ["however", "therefore", "consequently", "nevertheless",
                      "furthermore", "alternatively", "specifically", "particularly"]
        for ind in indicators:
            if ind in concept.lower():
                score += 0.05

        # Number of distinct entities/concepts
        cap_words = re.findall(r'\b[A-Z][a-z]+\b', concept)
        score += min(len(set(cap_words)) * 0.02, 0.2)

        return min(1.0, score)

    def _compute_explainability(self, fundamentals: list[str], analogies: list[str]) -> float:
        """Compute how explainable the concept is (0.0 = unexplainable, 1.0 = clear)."""
        score = 0.5

        if fundamentals:
            score += min(len(fundamentals) * 0.1, 0.3)

        if analogies:
            score += min(len(analogies) * 0.1, 0.2)

        return min(1.0, score)

    def get_stats(self) -> dict:
        """Get Feynman reducer statistics."""
        with self._lock:
            return {
                "total_reductions": self._reductions_performed,
                "status": "ready",
            }


# ── Singleton ──────────────────────────────────────────────────

_feynman_reducer = None
_feynman_lock = threading.Lock()


def get_feynman_reducer() -> FeynmanReducer:
    global _feynman_reducer
    if _feynman_reducer is None:
        with _feynman_lock:
            if _feynman_reducer is None:
                _feynman_reducer = FeynmanReducer()
    return _feynman_reducer
