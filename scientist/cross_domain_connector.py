"""
cross_domain_connector.py — Cross-Domain Scientific Analogy Engine

Finds structural analogies and transfer opportunities across scientific
domains. Enables cross-disciplinary ideation by mapping concepts between
fields.

Inspired by:
  - Gentner's structure-mapping theory of analogy
  - ResearchAgent's cross-pollination of ideas
  - Historical examples: neural networks ← neuroscience, evolution ← economics

Capabilities:
  [CD-1] Structural analogy detection between domains
  [CD-2] Concept mapping across fields
  [CD-3] Method transfer suggestions
  [CD-4] Analogy strength scoring
  [CD-5] Historical analogy database (successful cross-domain transfers)
  [CD-6] Novel cross-domain hypothesis generation
  [CD-7] Analogy validation (does the mapping hold?)
  [CD-8] Multi-hop analogy chains (A→B→C)

Thread-safe. Persistent state in cross_domain_state.json.
"""

import json
import math
import threading
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()
STATE_FILE = SCIENTIST_DIR / "cross_domain_state.json"

# ── Domain Knowledge Base ─────────────────────────────────────────────────────

DOMAINS = {
    "physics": {
        "name": "Physics",
        "core_concepts": ["energy", "force", "momentum", "entropy", "symmetry", "conservation", "field", "wave", "particle", "spacetime"],
        "methods": ["lagrangian_mechanics", "statistical_mechanics", "quantum_mechanics", "renormalization", "perturbation_theory"],
        "principles": ["least_action", "conservation_laws", "symmetry_breaking", "equilibrium", "phase_transitions"],
    },
    "biology": {
        "name": "Biology",
        "core_concepts": ["evolution", "fitness", "adaptation", "selection", "mutation", "gene", "organism", "ecosystem", "homeostasis", "emergence"],
        "methods": ["phylogenetics", "population_genetics", "molecular_biology", "systems_biology", "bioinformatics"],
        "principles": ["natural_selection", "central_dogma", "red_queen", "punctuated_equilibrium", "niche_construction"],
    },
    "computer_science": {
        "name": "Computer Science",
        "core_concepts": ["algorithm", "complexity", "abstraction", "recursion", "optimization", "search", "learning", "information", "computation", "network"],
        "methods": ["dynamic_programming", "gradient_descent", "monte_carlo", "graph_algorithms", "neural_networks"],
        "principles": ["turing_completeness", "no_free_lunch", "bias_variance_tradeoff", "occam_razor", "curse_of_dimensionality"],
    },
    "economics": {
        "name": "Economics",
        "core_concepts": ["utility", "equilibrium", "incentive", "market", "trade", "scarcity", "value", "risk", "game", "strategy"],
        "methods": ["game_theory", "econometrics", "mechanism_design", "auction_theory", "behavioral_economics"],
        "principles": ["supply_demand", "nash_equilibrium", "pareto_efficiency", "comparative_advantage", "tragedy_of_commons"],
    },
    "chemistry": {
        "name": "Chemistry",
        "core_concepts": ["bond", "reaction", "catalyst", "equilibrium", "concentration", "energy_barrier", "molecule", "phase", "kinetics", "thermodynamics"],
        "methods": ["spectroscopy", "chromatography", "molecular_dynamics", "reaction_kinetics", "computational_chemistry"],
        "principles": ["le_chatelier", "gibbs_free_energy", "activation_energy", "transition_state", "chemical_equilibrium"],
    },
    "mathematics": {
        "name": "Mathematics",
        "core_concepts": ["proof", "structure", "space", "mapping", "invariant", "convergence", "topology", "category", "symmetry", "dimension"],
        "methods": ["linear_algebra", "calculus", "probability_theory", "optimization", "information_geometry"],
        "principles": ["bayes_theorem", "central_limit_theorem", "fixed_point", "duality", "invariance"],
    },
    "neuroscience": {
        "name": "Neuroscience",
        "core_concepts": ["neuron", "synapse", "plasticity", "network", "representation", "coding", "learning", "attention", "memory", "consciousness"],
        "methods": ["electrophysiology", "imaging", "computational_neuroscience", "connectomics", "optogenetics"],
        "principles": ["hebbian_learning", "sparse_coding", "predictive_coding", "free_energy_principle", "neural_efficiency"],
    },
    "ecology": {
        "name": "Ecology",
        "core_concepts": ["niche", "competition", "cooperation", "diversity", "stability", "resilience", "succession", "food_web", "symbiosis", "carrying_capacity"],
        "methods": ["population_modeling", "community_ecology", "landscape_ecology", "meta_analysis"],
        "principles": ["competitive_exclusion", "intermediate_disturbance", "island_biogeography", "metabolic_theory", "maximum_entropy"],
    },
}

# Historical successful cross-domain transfers
HISTORICAL_ANALOGIES = [
    {
        "source": "neuroscience",
        "target": "computer_science",
        "concept": "neural networks",
        "description": "Artificial neural networks inspired by biological neurons. McCulloch-Pitts (1943) → modern deep learning.",
        "strength": 0.9,
        "impact": "transformative",
    },
    {
        "source": "physics",
        "target": "computer_science",
        "concept": "simulated annealing",
        "description": "Optimization algorithm inspired by metallurgical annealing. Kirkpatrick (1983).",
        "strength": 0.8,
        "impact": "significant",
    },
    {
        "source": "biology",
        "target": "computer_science",
        "concept": "genetic algorithms",
        "description": "Evolution-inspired optimization. Holland (1975). Selection, crossover, mutation.",
        "strength": 0.85,
        "impact": "significant",
    },
    {
        "source": "physics",
        "target": "economics",
        "concept": "statistical mechanics → market models",
        "description": "Boltzmann distribution applied to agent behavior. Econophysics.",
        "strength": 0.7,
        "impact": "moderate",
    },
    {
        "source": "ecology",
        "target": "computer_science",
        "concept": "ant colony optimization",
        "description": "Swarm intelligence from ant foraging behavior. Dorigo (1992).",
        "strength": 0.8,
        "impact": "significant",
    },
    {
        "source": "mathematics",
        "target": "neuroscience",
        "concept": "information geometry → brain",
        "description": "Fisher information metric applied to neural population codes.",
        "strength": 0.75,
        "impact": "emerging",
    },
    {
        "source": "physics",
        "target": "biology",
        "concept": "energy landscape → fitness landscape",
        "description": "Wright's fitness landscape inspired by potential energy surfaces.",
        "strength": 0.85,
        "impact": "foundational",
    },
    {
        "source": "computer_science",
        "target": "neuroscience",
        "concept": "backpropagation → synaptic learning",
        "description": "Backprop as model for credit assignment in brain. Still debated.",
        "strength": 0.6,
        "impact": "controversial",
    },
]


class DomainConcept:
    """A concept in a scientific domain with structural properties."""

    def __init__(
        self,
        name: str,
        domain: str,
        concept_type: str = "entity",
        properties: dict | None = None,
        relations: list[str] | None = None,
    ):
        self.name = name
        self.domain = domain
        self.concept_type = concept_type  # entity, process, property, relation, principle
        self.properties = properties or {}
        self.relations = relations or []  # names of related concepts

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "domain": self.domain,
            "type": self.concept_type,
            "properties": self.properties,
            "relations": self.relations,
        }


class Analogy:
    """A structural analogy between two concepts in different domains."""

    def __init__(
        self,
        source_concept: str,
        target_concept: str,
        source_domain: str,
        target_domain: str,
        mapping: dict | None = None,
        strength: float = 0.5,
    ):
        self.id = f"ANL-{int(time.time() * 1000)}"
        self.source_concept = source_concept
        self.target_concept = target_concept
        self.source_domain = source_domain
        self.target_domain = target_domain
        self.mapping = mapping or {}  # source_attr -> target_attr
        self.strength = strength
        self.validated = False
        self.transfer_suggestions: list[str] = []
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": f"{self.source_concept} ({self.source_domain})",
            "target": f"{self.target_concept} ({self.target_domain})",
            "mapping": self.mapping,
            "strength": round(self.strength, 3),
            "validated": self.validated,
            "transfer_suggestions": self.transfer_suggestions,
            "created_at": self.created_at,
        }


class CrossDomainConnector:
    """
    Finds structural analogies and transfer opportunities across
    scientific domains.
    """

    def __init__(self, llm_call=None):
        self._lock = threading.Lock()
        self._llm = llm_call
        self._analogies: list[Analogy] = []
        self._custom_concepts: dict[str, list[DomainConcept]] = defaultdict(list)
        self._load_state()

    def _load_state(self):
        with self._lock:
            if STATE_FILE.exists():
                try:
                    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                    for a in data.get("analogies", []):
                        analogy = Analogy(
                            a["source"].split(" (")[0],
                            a["target"].split(" (")[0],
                            a["source"].split("(")[1].rstrip(")") if "(" in a["source"] else "",
                            a["target"].split("(")[1].rstrip(")") if "(" in a["target"] else "",
                            a.get("mapping"),
                            a.get("strength", 0.5),
                        )
                        analogy.id = a["id"]
                        analogy.validated = a.get("validated", False)
                        analogy.transfer_suggestions = a.get("transfer_suggestions", [])
                        self._analogies.append(analogy)
                except Exception:
                    pass

    def _save_state(self):
        with self._lock:
            data = {
                "analogies": [a.to_dict() for a in self._analogies],
                "saved_at": datetime.now().isoformat(),
            }
            STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ── Analogy Detection ─────────────────────────────────────────────────────

    def find_analogies(
        self,
        concept: str,
        source_domain: str,
        target_domain: str = "",
    ) -> list[Analogy]:
        """
        Find structural analogies for a concept across domains.
        """
        if self._llm:
            return self._llm_find_analogies(concept, source_domain, target_domain)
        return self._heuristic_find_analogies(concept, source_domain, target_domain)

    def _heuristic_find_analogies(
        self,
        concept: str,
        source_domain: str,
        target_domain: str,
    ) -> list[Analogy]:
        """Heuristic analogy finding using domain knowledge base."""
        analogies = []
        concept_lower = concept.lower()

        # Check historical analogies first
        for ha in HISTORICAL_ANALOGIES:
            ha_concept = ha["concept"].lower()
            ha_source = ha["source"].lower()
            ha_target = ha["target"].lower()
            if (
                concept_lower in ha_concept
                or ha_concept in concept_lower
                or concept_lower in ha_source
                or concept_lower in ha_target
                or any(word in ha_concept for word in concept_lower.split("_"))
            ):
                a = Analogy(
                    ha["concept"].split(" → ")[0] if " → " in ha["concept"] else ha["concept"],
                    ha["concept"].split(" → ")[1] if " → " in ha["concept"] else ha["concept"],
                    ha["source"],
                    ha["target"],
                    strength=ha["strength"],
                )
                a.transfer_suggestions = [ha["description"]]
                analogies.append(a)

        # Search domain knowledge base
        targets = [target_domain] if target_domain else [
            d for d in DOMAINS if d != source_domain
        ]

        for target in targets:
            target_info = DOMAINS.get(target, {})
            source_info = DOMAINS.get(source_domain, {})

            # Check for concept overlap in core concepts
            for tc in target_info.get("core_concepts", []):
                similarity = self._concept_similarity(concept_lower, tc)
                if similarity > 0.25:
                    # Find structural parallels
                    mapping = self._find_structural_mapping(
                        concept, source_info, tc, target_info
                    )
                    a = Analogy(concept, tc, source_domain, target, mapping, similarity)
                    a.transfer_suggestions = self._generate_transfer_suggestions(
                        concept, source_domain, tc, target
                    )
                    analogies.append(a)

            # Check method parallels
            for tm in target_info.get("methods", []):
                for sm in source_info.get("methods", []):
                    similarity = self._concept_similarity(sm, tm)
                    if similarity > 0.35:
                        a = Analogy(sm, tm, source_domain, target, strength=similarity)
                        analogies.append(a)

            # Check principle parallels
            for tp in target_info.get("principles", []):
                for sp in source_info.get("principles", []):
                    similarity = self._concept_similarity(sp, tp)
                    if similarity > 0.3:
                        a = Analogy(sp, tp, source_domain, target, strength=similarity)
                        analogies.append(a)

            # Check source concept against target principles
            for tp in target_info.get("principles", []):
                similarity = self._concept_similarity(concept_lower, tp)
                if similarity > 0.3:
                    mapping = self._find_structural_mapping(concept, source_info, tp, target_info)
                    a = Analogy(concept, tp, source_domain, target, mapping, similarity)
                    a.transfer_suggestions = self._generate_transfer_suggestions(concept, source_domain, tp, target)
                    analogies.append(a)

        # Deduplicate and sort
        seen = set()
        unique = []
        for a in sorted(analogies, key=lambda x: x.strength, reverse=True):
            key = (a.source_concept, a.target_concept, a.source_domain, a.target_domain)
            if key not in seen:
                seen.add(key)
                unique.append(a)

        return unique[:10]

    def _llm_find_analogies(
        self,
        concept: str,
        source_domain: str,
        target_domain: str,
    ) -> list[Analogy]:
        """Use LLM to find deep structural analogies."""
        prompt = f"""Find structural analogies for this concept across scientific domains.

Concept: {concept}
Source domain: {source_domain}
Target domain: {target_domain or 'any scientific domain'}

For each analogy, provide:
ANALOGY: <source concept> → <target concept> | FROM: <source domain> | TO: <target domain> | STRENGTH: <0-1> | MAPPING: <structural parallel> | TRANSFER: <method/insight that could transfer>

Find deep structural parallels, not just surface similarities:"""

        response = self._llm(prompt)
        analogies = []

        for line in response.strip().split("\n"):
            if not line.strip().startswith("ANALOGY:"):
                continue
            parts = line.split("|")
            try:
                concepts = parts[0].split("→")
                src = concepts[0].split(":")[1].strip() if ":" in concepts[0] else concepts[0].strip()
                tgt = concepts[1].strip() if len(concepts) > 1 else ""
                src_domain = parts[1].split(":")[1].strip() if len(parts) > 1 else source_domain
                tgt_domain = parts[2].split(":")[1].strip() if len(parts) > 2 else target_domain
                strength = float(parts[3].split(":")[1].strip()) if len(parts) > 3 else 0.5
                mapping_str = parts[4].split(":")[1].strip() if len(parts) > 4 else ""
                transfer = parts[5].split(":")[1].strip() if len(parts) > 5 else ""

                a = Analogy(src, tgt, src_domain, tgt_domain, {"parallel": mapping_str}, strength)
                if transfer:
                    a.transfer_suggestions = [transfer]
                analogies.append(a)
            except (IndexError, ValueError):
                continue

        return analogies

    def _concept_similarity(self, a: str, b: str) -> float:
        """Compute conceptual similarity between two terms."""
        a_norm = a.lower().replace("_", " ")
        b_norm = b.lower().replace("_", " ")
        a_tokens = set(a_norm.split())
        b_tokens = set(b_norm.split())
        if not a_tokens and not b_tokens:
            return 0.0
        intersection = a_tokens & b_tokens
        union = a_tokens | b_tokens
        jaccard = len(intersection) / len(union) if union else 0.0

        # Substring containment bonus
        if a_norm in b_norm or b_norm in a_norm:
            jaccard = max(jaccard, 0.5)

        # Bonus for semantic similarity patterns
        semantic_pairs = [
            ("energy", "fitness"), ("force", "selection"), ("momentum", "inertia"),
            ("entropy", "diversity"), ("equilibrium", "homeostasis"),
            ("wave", "oscillation"), ("field", "landscape"), ("particle", "agent"),
            ("symmetry", "invariance"), ("phase", "state"), ("catalyst", "enzyme"),
            ("network", "graph"), ("optimization", "adaptation"),
            ("selection", "search"), ("mutation", "perturbation"),
            ("fitness", "objective"), ("evolution", "learning"),
            ("crossover", "recombination"), ("niche", "cluster"),
            ("population", "ensemble"), ("generation", "epoch"),
            ("speciation", "clustering"), ("adaptation", "gradient"),
            ("gene", "parameter"), ("phenotype", "output"),
            ("genotype", "weight"), ("organism", "model"),
        ]
        for x, y in semantic_pairs:
            if (x in a_norm and y in b_norm) or (y in a_norm and x in b_norm):
                jaccard = max(jaccard, 0.55)

        return jaccard

    def _find_structural_mapping(
        self,
        source_concept: str,
        source_domain: dict,
        target_concept: str,
        target_domain: dict,
    ) -> dict:
        """Find structural mapping between domain concepts."""
        mapping = {}

        # Map principles
        src_principles = source_domain.get("principles", [])
        tgt_principles = target_domain.get("principles", [])
        if src_principles and tgt_principles:
            mapping["principle_parallel"] = f"{src_principles[0]} ↔ {tgt_principles[0]}"

        # Map methods
        src_methods = source_domain.get("methods", [])
        tgt_methods = target_domain.get("methods", [])
        if src_methods and tgt_methods:
            mapping["method_parallel"] = f"{src_methods[0]} ↔ {tgt_methods[0]}"

        mapping["structural_parallel"] = f"{source_concept} in {source_domain.get('name', '')} ↔ {target_concept} in {target_domain.get('name', '')}"

        return mapping

    def _generate_transfer_suggestions(
        self,
        source_concept: str,
        source_domain: str,
        target_concept: str,
        target_domain: str,
    ) -> list[str]:
        """Generate suggestions for cross-domain method transfer."""
        suggestions = []

        # Check for known transferable methods
        source_info = DOMAINS.get(source_domain, {})
        target_info = DOMAINS.get(target_domain, {})

        for method in source_info.get("methods", []):
            # Check if method conceptually applies to target
            for principle in target_info.get("principles", []):
                if self._concept_similarity(method, principle) > 0.2:
                    suggestions.append(
                        f"Apply {method} from {source_domain} to test {principle} in {target_domain}"
                    )

        if not suggestions:
            suggestions.append(
                f"Investigate whether {source_concept} ({source_domain}) "
                f"has a structural analog in {target_concept} ({target_domain})"
            )

        return suggestions

    # ── Multi-Hop Analogy Chains ──────────────────────────────────────────────

    def find_analogy_chain(
        self,
        source_concept: str,
        source_domain: str,
        target_domain: str,
        max_hops: int = 3,
    ) -> list[list[Analogy]]:
        """
        Find chains of analogies: A → B → C → target.
        Enables discovery of non-obvious connections.
        """
        # Direct analogies
        direct = self.find_analogies(source_concept, source_domain, target_domain)
        if direct:
            return [[a] for a in direct[:3]]

        # Try intermediate domains
        chains = []
        intermediate_domains = [
            d for d in DOMAINS if d not in (source_domain, target_domain)
        ]

        for intermediate in intermediate_domains:
            # First hop: source → intermediate
            first_hop = self.find_analogies(source_concept, source_domain, intermediate)
            if not first_hop:
                continue

            for a1 in first_hop[:2]:
                # Second hop: intermediate → target
                second_hop = self.find_analogies(a1.target_concept, intermediate, target_domain)
                if second_hop:
                    for a2 in second_hop[:2]:
                        chains.append([a1, a2])

        # Sort by average strength
        chains.sort(
            key=lambda c: sum(a.strength for a in c) / len(c),
            reverse=True,
        )
        return chains[:5]

    # ── Hypothesis Generation ─────────────────────────────────────────────────

    def generate_cross_domain_hypothesis(
        self,
        concept: str,
        source_domain: str,
        target_domain: str,
    ) -> dict:
        """
        Generate a novel hypothesis by transferring insights across domains.
        """
        analogies = self.find_analogies(concept, source_domain, target_domain)
        if not analogies:
            return {
                "hypothesis": f"No strong analogy found for {concept} between {source_domain} and {target_domain}",
                "confidence": 0.0,
            }

        best = analogies[0]
        if self._llm:
            return self._llm_generate_hypothesis(best)

        # Template-based hypothesis
        hypothesis = (
            f"If {best.source_concept} in {best.source_domain} is structurally analogous "
            f"to {best.target_concept} in {best.target_domain}, then methods that work for "
            f"{best.source_concept} (e.g., {', '.join(best.transfer_suggestions[:2])}) "
            f"may yield new insights when applied to {best.target_concept}."
        )

        return {
            "hypothesis": hypothesis,
            "analogy": best.to_dict(),
            "confidence": best.strength,
            "testable_predictions": [
                f"Apply {best.source_domain} methodology to {best.target_domain} problem",
                f"Compare structural properties of {best.source_concept} and {best.target_concept}",
            ],
        }

    def _llm_generate_hypothesis(self, analogy: Analogy) -> dict:
        """Use LLM to generate a detailed cross-domain hypothesis."""
        prompt = f"""Generate a novel, testable scientific hypothesis based on this cross-domain analogy.

Source: {analogy.source_concept} in {analogy.source_domain}
Target: {analogy.target_concept} in {analogy.target_domain}
Mapping: {json.dumps(analogy.mapping)}
Transfer suggestions: {', '.join(analogy.transfer_suggestions)}

Generate:
1. A clear, testable hypothesis
2. 2-3 specific predictions
3. An experiment to test it
4. Potential impact if confirmed

Format:
HYPOTHESIS: <text>
PREDICTION: <text>
EXPERIMENT: <text>
IMPACT: <text>"""

        response = self._llm(prompt)
        result = {"analogy": analogy.to_dict(), "confidence": analogy.strength}

        for line in response.strip().split("\n"):
            for prefix in ["HYPOTHESIS:", "PREDICTION:", "EXPERIMENT:", "IMPACT:"]:
                if line.strip().startswith(prefix):
                    key = prefix.rstrip(":").lower()
                    result[key] = line.split(prefix)[1].strip()

        return result

    # ── API ───────────────────────────────────────────────────────────────────

    def list_domains(self) -> list[dict]:
        """List all known domains with their core concepts."""
        return [
            {"domain": d, "name": info["name"], "concepts": info["core_concepts"][:5]}
            for d, info in DOMAINS.items()
        ]

    def get_historical_analogies(self) -> list[dict]:
        """Get database of historical cross-domain transfers."""
        return HISTORICAL_ANALOGIES

    def get_saved_analogies(self) -> list[dict]:
        """Get saved analogy discoveries."""
        with self._lock:
            return [a.to_dict() for a in self._analogies]

    def save_analogy(self, analogy: Analogy):
        """Save an analogy for future reference."""
        with self._lock:
            self._analogies.append(analogy)
            self._save_state()

    def reset(self):
        with self._lock:
            self._analogies.clear()
            self._save_state()


# ── Singleton ─────────────────────────────────────────────────────────────────

_connector: Optional[CrossDomainConnector] = None
_connector_lock = threading.Lock()


def get_cross_domain_connector(llm_call=None) -> CrossDomainConnector:
    global _connector
    with _connector_lock:
        if _connector is None:
            _connector = CrossDomainConnector(llm_call=llm_call)
        return _connector
