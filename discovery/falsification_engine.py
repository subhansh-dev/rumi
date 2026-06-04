"""
falsification_engine.py — Actively try to KILL theories.

Scientists spend more time trying to destroy theories than create them.
RUMI should do the same.

This module:
1. Checks theories against known observational constraints (DESI, Planck, ACT, etc.)
2. Runs counterfactual reasoning: "If this were true, then X should also be true — is it?"
3. Searches for ruling-out evidence in the literature
4. Identifies the weakest point of each theory
5. Scores killability — how easy would it be to disprove this?

A theory that survives aggressive falsification is much stronger than
one that was never tested.
"""

import json
import re
from typing import Dict, List, Optional
from discovery.json_extract import extract_json


class FalsificationEngine:
    """
    Actively attempt to falsify hypotheses using existing data and reasoning.
    """

    # Known observational constraints by domain
    COSMOLOGY_CONSTRAINTS = {
        "Planck CMB": {
            "description": "Planck 2018 CMB measurements",
            "H0": (67.36, 0.54),  # (value, uncertainty) km/s/Mpc
            "Omega_m": (0.3153, 0.0073),
            "sigma8": (0.8111, 0.0060),
            "constrains": ["varying_G", "early_dark_energy", "modified_gravity", "dark_sector"],
        },
        "DESI BAO": {
            "description": "DESI 2024 Baryon Acoustic Oscillation measurements",
            "H0_range": (67.0, 73.0),
            "constrains": ["varying_G", "early_dark_energy", "coupled_dark_sector"],
        },
        "SH0ES": {
            "description": "Supernovae and H0 for the Equation of State (SH0ES)",
            "H0": (73.04, 1.04),
            "constrains": ["standard_candles", "distance_ladder"],
        },
        "ACT DR6": {
            "description": "Atacama Cosmology Telescope Data Release 6",
            "constrains": ["early_dark_energy", "neutrino_mass", "curvature"],
            "f_EDE_limit": 0.07,  # 95% CL
        },
        "Pulsar Timing Arrays": {
            "description": "NANOGrav/EPTA/PPTA pulsar timing",
            "constrains": ["varying_G", "gravitational_waves"],
            "G_dot_limit": 1e-12,  # |Ġ/G| < 10^-12 /yr
        },
        "Lunar Laser Ranging": {
            "description": "Apollo lunar laser ranging experiment",
            "constrains": ["varying_G", "equivalence_principle"],
            "G_dot_limit": 1e-13,  # |Ġ/G| < 10^-13 /yr
        },
        "BBN": {
            "description": "Big Bang Nucleosynthesis constraints",
            "constrains": ["varying_G", "extra_relativistic_species", "early_dark_energy"],
            "Delta_N_eff_limit": 0.3,
        },
    }

    DRUG_DISCOVERY_CONSTRAINTS = {
        "FDA approved drugs": {
            "description": "Already approved therapeutic agents",
            "constrains": ["novel_targets", "drug_repurposing"],
        },
        "Clinical trial databases": {
            "description": "ClinicalTrials.gov active/completed trials",
            "constrains": ["novel_mechanisms", "combination_therapies"],
        },
        "Known resistance mechanisms": {
            "description": "Documented drug resistance pathways",
            "constrains": ["resistance_bypass", "combination_strategies"],
        },
    }

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def falsify(self, theory: dict, papers: list = None,
                domain: str = "") -> dict:
        """
        Attempt to falsify a theory using multiple methods.

        Returns:
            {
                "constraints_checked": [...],
                "counterfactual_tests": [...],
                "ruling_out_evidence": [...],
                "weakest_point": "...",
                "survival_score": 0.0-1.0,
                "falsification_verdict": "survived|partially_falsified|falsified|unknown",
                "kill_attempts": [...]
            }
        """
        results = {
            "constraints_checked": [],
            "counterfactual_tests": [],
            "ruling_out_evidence": [],
            "weakest_point": "",
            "kill_attempts": [],
        }

        # 1. Check against known observational constraints
        constraint_results = self._check_constraints(theory, domain)
        results["constraints_checked"] = constraint_results

        # 2. Counterfactual reasoning: "If this were true, then..."
        if self.llm_call:
            counterfactuals = self._counterfactual_reasoning(theory, domain)
            results["counterfactual_tests"] = counterfactuals

        # 3. Search papers for ruling-out evidence
        if papers:
            ruling_out = self._search_ruling_out(theory, papers)
            results["ruling_out_evidence"] = ruling_out

        # 4. LLM-based adversarial attack
        if self.llm_call:
            attack = self._adversarial_attack(theory, domain)
            results["kill_attempts"] = attack

        # 5. Find weakest point
        results["weakest_point"] = self._find_weakest_point(results)

        # 6. Compute survival score
        survival = self._compute_survival(results)
        results["survival_score"] = round(survival, 3)

        # 7. Verdict
        if survival > 0.7:
            results["falsification_verdict"] = "survived"
        elif survival > 0.4:
            results["falsification_verdict"] = "partially_falsified"
        elif survival > 0.1:
            results["falsification_verdict"] = "falsified"
        else:
            results["falsification_verdict"] = "unknown"

        return results

    def _check_constraints(self, theory: dict, domain: str) -> list:
        """Check theory against known observational constraints."""
        results = []
        theory_text = json.dumps(theory).lower()

        # Select constraints based on domain
        if domain in ("space_astronomy", "physics", "cosmology", "general"):
            constraints = self.COSMOLOGY_CONSTRAINTS
        elif domain == "drug_discovery":
            constraints = self.DRUG_DISCOVERY_CONSTRAINTS
        else:
            constraints = self.COSMOLOGY_CONSTRAINTS  # default

        for name, constraint in constraints.items():
            # Check if this constraint is relevant to the theory
            relevant = False
            for c_type in constraint.get("constrains", []):
                if c_type.replace("_", " ") in theory_text or c_type in theory_text:
                    relevant = True
                    break

            if not relevant:
                continue

            # Check specific limits
            violations = []
            surviving = []

            # H0 constraints
            if "H0" in constraint and "h0" in theory_text:
                h0_val, h0_err = constraint["H0"]
                # Check if theory claims a different H0
                h0_matches = re.findall(r'H[₀0]\s*[≈=]\s*(\d+\.?\d*)', theory_text)
                for match in h0_matches:
                    try:
                        theory_h0 = float(match)
                        deviation = abs(theory_h0 - h0_val) / h0_err
                        if deviation > 2:
                            violations.append(f"H₀={theory_h0} deviates {deviation:.1f}σ from {name} ({h0_val}±{h0_err})")
                        else:
                            surviving.append(f"H₀={theory_h0} consistent with {name} ({deviation:.1f}σ)")
                    except ValueError:
                        pass

            # Ġ/G constraints
            if "G_dot_limit" in constraint:
                g_patterns = re.findall(r'(?:Ġ|G_dot|G_dot)\s*/\s*G\s*[<≤]?\s*([\d.]+)\s*(?:×\s*10\^?\(?(-?\d+)\)?)?', theory_text)
                for num, exp in g_patterns:
                    try:
                        g_dot = float(num) * (10 ** int(exp)) if exp else float(num)
                        limit = constraint["G_dot_limit"]
                        if g_dot > limit:
                            violations.append(f"|Ġ/G| = {g_dot:.1e} exceeds {name} limit ({limit:.1e})")
                        else:
                            surviving.append(f"|Ġ/G| = {g_dot:.1e} within {name} limit ({limit:.1e})")
                    except (ValueError, TypeError):
                        pass

            # f_EDE constraints
            if "f_EDE_limit" in constraint:
                f_matches = re.findall(r'f_EDE\s*[≈=]?\s*(\d+\.?\d*)\s*%', theory_text)
                for match in f_matches:
                    try:
                        f_ede = float(match) / 100.0
                        limit = constraint["f_EDE_limit"]
                        if f_ede > limit:
                            violations.append(f"f_EDE = {f_ede:.1%} exceeds {name} limit ({limit:.1%})")
                        else:
                            surviving.append(f"f_EDE = {f_ede:.1%} within {name} limit ({limit:.1%})")
                    except ValueError:
                        pass

            results.append({
                "constraint": name,
                "description": constraint.get("description", ""),
                "relevant": True,
                "violations": violations,
                "surviving": surviving,
                "status": "VIOLATED" if violations else ("CONSISTENT" if surviving else "UNCHECKED"),
            })

        return results

    def _counterfactual_reasoning(self, theory: dict, domain: str) -> list:
        """
        If theory T is true, then consequences C1, C2, C3 must follow.
        Check if C1, C2, C3 are actually observed.
        """
        theory_desc = theory.get("description", theory.get("mechanism", ""))[:500]
        predictions = theory.get("predictions", [])
        pred_text = "\n".join(f"- {p}" if isinstance(p, str) else f"- {p.get('statement', '')}"
                              for p in predictions[:5])

        prompt = f"""You are testing a scientific theory through counterfactual reasoning.

THEORY: {theory.get('name', '?')}
DESCRIPTION: {theory_desc}
DOMAIN: {domain}
PREDICTIONS: {pred_text}

For each prediction, ask: "If this theory is true, then what ELSE must also be true?"
Then check: "Is that 'else' actually observed?"

Generate 3-5 counterfactual tests. Each should:
1. State what MUST be true if the theory holds
2. Check if it IS actually true (based on known observations)
3. Rate: SUPPORTED | CONTRADICTED | UNKNOWN

Output JSON:
{{
  "counterfactuals": [
    {{
      "if_true": "If theory T is true, then consequence C must follow",
      "is_observed": true|false|null,
      "status": "SUPPORTED|CONTRADICTED|UNKNOWN",
      "evidence": "what observation supports/contradicts this",
      "damage": "how much this hurts the theory if contradicted"
    }}
  ]
}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=4096)
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = extract_json(raw)
                    return result.get("counterfactuals", [])
        except Exception:
            pass
        return []

    def _search_ruling_out(self, theory: dict, papers: list) -> list:
        """Search papers for evidence that rules out the theory."""
        ruling_out = []
        theory_keywords = set()

        # Extract keywords
        name = theory.get("name", "")
        for word in name.lower().split():
            if len(word) > 4:
                theory_keywords.add(word)

        desc = theory.get("description", "")
        for word in desc.lower().split():
            if len(word) > 6 and word.isalpha():
                theory_keywords.add(word)

        RULING_OUT_SIGNALS = [
            "rules out", "excludes", "incompatible with", "contradicts",
            "cannot explain", "fails to", "inconsistent with", "challenges",
            "refutes", "disproves", "rules-out", "excluded by",
            "tension with", "discrepancy", "at odds with",
        ]

        for paper in papers:
            abstract = (paper.get("abstract", "") + " " + paper.get("title", "")).lower()

            # Check if paper mentions the theory's keywords AND ruling-out signals
            keyword_hits = sum(1 for kw in theory_keywords if kw in abstract)
            ruling_signals = [s for s in RULING_OUT_SIGNALS if s in abstract]

            if keyword_hits > 0 and ruling_signals:
                ruling_out.append({
                    "title": paper.get("title", "?")[:100],
                    "source": paper.get("source", "?"),
                    "ruling_signals": ruling_signals,
                    "keyword_hits": keyword_hits,
                    "severity": "high" if len(ruling_signals) >= 2 else "medium",
                })

        return ruling_out[:5]

    def _adversarial_attack(self, theory: dict, domain: str) -> list:
        """LLM-based adversarial attack: find every reason the theory could be wrong."""
        theory_desc = theory.get("description", theory.get("mechanism", ""))[:500]
        params = json.dumps(theory.get("key_parameters", [])[:3])
        predictions = json.dumps(theory.get("predictions", [])[:3])

        prompt = f"""You are an adversarial scientist trying to DESTROY this theory.
Find every reason it could be wrong.

THEORY: {theory.get('name', '?')}
DOMAIN: {domain}
DESCRIPTION: {theory_desc}
PARAMETERS: {params}
PREDICTIONS: {predictions}

Attack from these angles:
1. Internal inconsistency (does the theory contradict itself?)
2. Known data conflict (does existing data rule it out?)
3. Alternative explanation (is there a simpler explanation?)
4. Parameter fine-tuning (does it require suspiciously precise values?)
5. Missing mechanism (does it invoke something without explaining how?)
6. Occam's razor (is there a simpler theory that works just as well?)

For each attack, rate its severity: FATAL | SERIOUS | MINOR

Output JSON:
{{
  "attacks": [
    {{
      "angle": "which attack angle",
      "argument": "specific argument against the theory",
      "severity": "FATAL|SERIOUS|MINOR",
      "counter": "possible defense against this attack"
    }}
  ]
}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=4096)
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = extract_json(raw)
                    return result.get("attacks", [])
        except Exception:
            pass
        return []

    def _find_weakest_point(self, results: dict) -> str:
        """Identify the single weakest point of the theory."""
        weaknesses = []

        # From constraint violations
        for c in results.get("constraints_checked", []):
            if c.get("status") == "VIOLATED":
                weaknesses.append(("FATAL", f"Violates {c['constraint']}: {c['violations'][0]}"))

        # From counterfactuals
        for cf in results.get("counterfactual_tests", []):
            if isinstance(cf, dict) and cf.get("status") == "CONTRADICTED":
                weaknesses.append(("SERIOUS", f"Counterfactual failed: {cf.get('if_true', '')}"))

        # From ruling-out evidence
        for r in results.get("ruling_out_evidence", []):
            if r.get("severity") == "high":
                weaknesses.append(("SERIOUS", f"Ruled out by: {r.get('title', '')}"))

        # From adversarial attacks
        for a in results.get("kill_attempts", []):
            if isinstance(a, dict) and a.get("severity") == "FATAL":
                weaknesses.append(("FATAL", f"Attack: {a.get('argument', '')}"))

        if not weaknesses:
            return "No critical weaknesses found"

        # Return the most severe
        weaknesses.sort(key=lambda x: 0 if x[0] == "FATAL" else 1)
        return weaknesses[0][1]

    def _compute_survival(self, results: dict) -> float:
        """Compute how well the theory survives falsification attempts."""
        score = 0.8  # start with benefit of the doubt

        # Constraint violations
        for c in results.get("constraints_checked", []):
            if c.get("status") == "VIOLATED":
                score -= 0.3
            elif c.get("status") == "CONSISTENT":
                score += 0.05

        # Counterfactual failures
        for cf in results.get("counterfactual_tests", []):
            if isinstance(cf, dict):
                if cf.get("status") == "CONTRADICTED":
                    score -= 0.2
                elif cf.get("status") == "SUPPORTED":
                    score += 0.05

        # Ruling-out evidence
        for r in results.get("ruling_out_evidence", []):
            if r.get("severity") == "high":
                score -= 0.2
            elif r.get("severity") == "medium":
                score -= 0.1

        # Adversarial attacks
        for a in results.get("kill_attempts", []):
            if isinstance(a, dict):
                severity = a.get("severity", "MINOR")
                if severity == "FATAL":
                    score -= 0.25
                elif severity == "SERIOUS":
                    score -= 0.15
                elif severity == "MINOR":
                    score -= 0.05

        return max(0.0, min(1.0, score))
