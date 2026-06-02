"""
cross_domain_transfer.py — Apply discoveries from one domain to another.

Real breakthroughs often come from applying ideas across domains:
- Thermodynamics -> Information theory (Maxwell's demon -> Landauer's principle)
- Biology -> Computing (neural networks, genetic algorithms)
- Physics -> Finance (Black-Scholes from heat equation)
- Ecology -> Economics (resource competition models)

This module finds structural analogies between domains and transfers mechanisms.
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class Analogy:
    """A structural analogy between two domains."""
    source_domain: str
    target_domain: str
    source_mechanism: str
    target_mechanism: str
    mapping: Dict[str, str]  # source_concept -> target_concept
    strength: float  # 0-1
    precedent: str  # historical example of this analogy
    prediction: str  # what the analogy predicts in target domain
    limitations: str  # where the analogy breaks down


# Known cross-domain analogies
KNOWN_ANALOGIES = [
    {
        "source": "physics",
        "target": "information_theory",
        "mechanism": "entropy",
        "mapping": {
            "temperature": "information_content",
            "heat": "data",
            "entropy": "Shannon_entropy",
            "free_energy": "KL_divergence",
            "Boltzmann": "Shannon",
        },
        "precedent": "Landauer's principle: erasing 1 bit costs kT*ln(2) energy",
        "prediction": "Information processing has fundamental energy costs",
    },
    {
        "source": "ecology",
        "target": "economics",
        "mechanism": "resource_competition",
        "mapping": {
            "species": "firm",
            "niche": "market",
            "carrying_capacity": "market_size",
            "predation": "hostile_takeover",
            "mutualism": "partnership",
            "extinction": "bankruptcy",
        },
        "precedent": "Lotka-Volterra -> competitive market dynamics",
        "prediction": "Market equilibrium follows same math as ecosystem equilibrium",
    },
    {
        "source": "neuroscience",
        "target": "computer_science",
        "mechanism": "learning",
        "mapping": {
            "synapse": "weight",
            "neuron": "node",
            "plasticity": "gradient_descent",
            "reinforcement": "reward_signal",
            "forgetting": "regularization",
        },
        "precedent": "Hebbian learning -> backpropagation",
        "prediction": "Biological learning rules can improve artificial learning",
    },
    {
        "source": "physics",
        "target": "climate_energy",
        "mechanism": "radiative_transfer",
        "mapping": {
            "photon_absorption": "IR_absorption_by_GHGs",
            "optical_depth": "atmospheric_opacity",
            "blackbody": "Earth_emission",
            "Planck_function": "emission_spectrum",
        },
        "precedent": "Schwarzschild (1906) radiative transfer -> climate models",
        "prediction": "Climate sensitivity derivable from radiative transfer equations",
    },
    {
        "source": "molecular_biology",
        "target": "materials_science",
        "mechanism": "self_assembly",
        "mapping": {
            "protein_folding": "crystal_growth",
            "chaperone": "template",
            "misfolding": "defect",
            "amyloid": "precipitate",
        },
        "precedent": "Protein folding principles -> nanomaterial self-assembly",
        "prediction": "Chaperone-like molecules could guide material self-assembly",
    },
    {
        "source": "physics",
        "target": "economics",
        "mechanism": "statistical_mechanics",
        "mapping": {
            "particles": "agents",
            "energy": "wealth",
            "temperature": "market_volatility",
            "entropy": "market_disorder",
            "Boltzmann_distribution": "wealth_distribution",
        },
        "precedent": "Yakovenko (2009): wealth follows Boltzmann distribution",
        "prediction": "Market crashes as phase transitions",
    },
    {
        "source": "oceanography",
        "target": "neuroscience",
        "mechanism": "fluid_dynamics",
        "mapping": {
            "ocean_current": "neural_signal",
            "thermocline": "synapse",
            "upwelling": "neurotransmitter_release",
            "eddy": "reverberating_circuit",
        },
        "precedent": "Neural field equations from fluid dynamics (Wilson-Cowan)",
        "prediction": "Ocean turbulence models can predict neural oscillations",
    },
]


class CrossDomainTransfer:
    """
    Transfer mechanisms and analogies across scientific domains.
    """

    def __init__(self):
        self.analogies = KNOWN_ANALOGIES
        self.discovered_analogies = []

    def find_analogies(self, source_domain: str, target_domain: str) -> List[Analogy]:
        """Find known analogies between two domains."""
        results = []
        for a in self.analogies:
            if (a["source"] == source_domain and a["target"] == target_domain) or \
               (a["source"] == target_domain and a["target"] == source_domain):
                results.append(Analogy(
                    source_domain=a["source"],
                    target_domain=a["target"],
                    source_mechanism=a["mechanism"],
                    target_mechanism=a["mechanism"],
                    mapping=a["mapping"],
                    strength=0.8,
                    precedent=a["precedent"],
                    prediction=a.get("prediction", ""),
                    limitations="Analogies are structural, not identity",
                ))
        return results

    def find_all_source_analogies(self, domain: str) -> List[Analogy]:
        """Find all analogies involving a domain."""
        results = []
        for a in self.analogies:
            if a["source"] == domain or a["target"] == domain:
                other = a["target"] if a["source"] == domain else a["source"]
                results.append(Analogy(
                    source_domain=a["source"],
                    target_domain=a["target"],
                    source_mechanism=a["mechanism"],
                    target_mechanism=a["mechanism"],
                    mapping=a["mapping"],
                    strength=0.8,
                    precedent=a["precedent"],
                    prediction=a.get("prediction", ""),
                    limitations="Analogies are structural, not identity",
                ))
        return results

    def discover_new_analogy(self, source_domain: str, source_mechanism: str,
                              target_domain: str, llm_fn=None) -> Optional[Analogy]:
        """
        Use LLM to discover a new analogy between domains.
        """
        if not llm_fn:
            return None

        prompt = f"""You are a cross-domain analogy finder.

SOURCE DOMAIN: {source_domain}
SOURCE MECHANISM: {source_mechanism}
TARGET DOMAIN: {target_domain}

Find a structural analogy. The mechanism in the source domain should have
a counterpart in the target domain that works similarly.

Format:
MAPPING: [source_concept1 -> target_concept1, source_concept2 -> target_concept2, ...]
PREDICTION: [what this analogy predicts in the target domain]
PRECEDENT: [has anyone noted this analogy before?]
LIMITATIONS: [where does the analogy break down?]
STRENGTH: [0.0-1.0]"""

        response = llm_fn(prompt)

        # Parse response
        mapping = {}
        mapping_match = re.search(r'MAPPING:\s*(.+)', response)
        if mapping_match:
            pairs = mapping_match.group(1).split(",")
            for pair in pairs:
                if "->" in pair:
                    s, t = pair.split("->", 1)
                    mapping[s.strip()] = t.strip()

        prediction = ""
        pred_match = re.search(r'PREDICTION:\s*(.+)', response)
        if pred_match:
            prediction = pred_match.group(1).strip()

        precedent = ""
        prec_match = re.search(r'PRECEDENT:\s*(.+)', response)
        if prec_match:
            precedent = prec_match.group(1).strip()

        limitations = ""
        lim_match = re.search(r'LIMITATIONS:\s*(.+)', response)
        if lim_match:
            limitations = lim_match.group(1).strip()

        strength = 0.5
        str_match = re.search(r'STRENGTH:\s*([\d.]+)', response)
        if str_match:
            strength = float(str_match.group(1))

        analogy = Analogy(
            source_domain=source_domain,
            target_domain=target_domain,
            source_mechanism=source_mechanism,
            target_mechanism=source_mechanism,  # same structural mechanism
            mapping=mapping,
            strength=strength,
            precedent=precedent,
            prediction=prediction,
            limitations=limitations,
        )

        self.discovered_analogies.append(analogy)
        return analogy

    def get_transfer_suggestions(self, domain: str, discovery: str,
                                  llm_fn=None) -> List[dict]:
        """
        Given a discovery in one domain, suggest where it could transfer.
        """
        # Get known analogies
        analogies = self.find_all_source_analogies(domain)

        suggestions = []
        for a in analogies:
            suggestions.append({
                "from": domain,
                "to": a.target_domain if a.source_domain == domain else a.source_domain,
                "mechanism": a.source_mechanism,
                "mapping": a.mapping,
                "precedent": a.precedent,
                "prediction": a.prediction,
            })

        return suggestions

    def get_summary(self) -> dict:
        """Summary of cross-domain transfer."""
        return {
            "known_analogies": len(self.analogies),
            "discovered_analogies": len(self.discovered_analogies),
            "domains_covered": list(set(
                a["source"] for a in self.analogies
            ) | set(a["target"] for a in self.analogies)),
        }
