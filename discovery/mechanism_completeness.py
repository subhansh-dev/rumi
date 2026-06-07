"""
mechanism_completeness.py - Is the mechanism derivation complete?

A mechanism that states a result without deriving it is hand-waving.
This module checks if mechanisms provide:
1. Starting assumptions (stated explicitly)
2. Mathematical derivation (from first principles to result)
3. Transport coefficients (derived, not assumed)
4. Numerical validation (simulation or analytic solution)
"""
import re


class MechanismCompletenessChecker:
    """Check if mechanisms are derivationally complete."""

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def check_mechanisms(self, mechanisms: list) -> dict:
        results = []
        for m in (mechanisms or []):
            if not isinstance(m, dict):
                continue
            check = self._check_single(m)
            results.append(check)

        complete = [r for r in results if r["completeness_score"] >= 0.6]
        avg_score = sum(r["completeness_score"] for r in results) / max(1, len(results))
        return {
            "total": len(results),
            "complete": len(complete),
            "incomplete": len(results) - len(complete),
            "avg_completeness": round(avg_score, 3),
            "details": results,
        }

    def _check_single(self, mechanism: dict) -> dict:
        desc = mechanism.get("description", "") + " " + mechanism.get("mechanism", "")
        math_model = mechanism.get("mathematical_model", "")
        steps = mechanism.get("steps", [])
        params = mechanism.get("key_parameters", [])
        full_text = desc + " " + math_model + " " + " ".join(str(s) for s in steps)
        full_lower = full_text.lower()

        # Check 1: Assumptions stated
        assumption_keywords = ["assume", "given", "starting from", "premise", "if we assume",
                              "consider", "suppose", "let us", "we begin"]
        has_assumptions = any(kw in full_lower for kw in assumption_keywords)

        # Check 2: Derivation present (step-by-step reasoning)
        derivation_keywords = ["therefore", "thus", "it follows", "substituting",
                              "solving", "integrating", "deriving", "from this",
                              "we obtain", "we get", "which gives", "yielding"]
        derivation_count = sum(1 for kw in derivation_keywords if kw in full_lower)
        has_derivation = derivation_count >= 2

        # Check 3: Transport coefficients derived (not just stated)
        transport_keywords = ["viscosity", "diffusion", "conductivity", "mean free path",
                            "collision", "cross-section", "boltzmann", "transport",
                            "scattering rate", "relaxation time"]
        has_transport = any(kw in full_lower for kw in transport_keywords)
        # Check if transport coefficient is derived vs assumed
        derived_transport = has_transport and derivation_count >= 1

        # Check 4: Numerical validation
        has_numbers = bool(re.search(r"\d[\d\.eE\+\-]*", full_text))
        has_units = bool(re.search(r"(?:K|eV|GPa|cm|nm|GHz|THz|meV|Mpc|solar|yr|Hz|Pa)", full_text))
        has_simulation = any(kw in full_lower for kw in
            ["simulation", "numerical", "computed", "calculated", "solved",
             "n-body", "monte carlo", "finite element", "analytic solution"])

        # Check 5: Key parameters with expected values
        param_count = len(params) if isinstance(params, list) else 0
        has_params = param_count >= 1

        # Compute completeness score
        score = 0.0
        if has_assumptions: score += 0.2
        if has_derivation: score += 0.3
        if derived_transport: score += 0.2
        elif has_transport: score += 0.1  # mentioned but not derived
        if has_numbers and has_units: score += 0.15
        if has_simulation: score += 0.15
        if has_params: score += 0.1

        # Identify gaps
        gaps = []
        if not has_assumptions:
            gaps.append("No explicit assumptions stated")
        if not has_derivation:
            gaps.append("No step-by-step derivation")
        if not derived_transport:
            if has_transport:
                gaps.append("Transport coefficient mentioned but not derived from first principles")
            else:
                gaps.append("No transport coefficients specified")
        if not has_simulation:
            gaps.append("No numerical validation or simulation")

        return {
            "name": mechanism.get("name", "?"),
            "completeness_score": round(score, 3),
            "has_assumptions": has_assumptions,
            "has_derivation": has_derivation,
            "has_transport": has_transport,
            "derived_transport": derived_transport,
            "has_numerical": has_numbers and has_units,
            "has_simulation": has_simulation,
            "gaps": gaps,
        }

