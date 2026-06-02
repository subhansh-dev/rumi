"""
counterfactual_reasoner.py — If theory T is true, then consequences C1, C2, C3 must follow.

This is the core of scientific reasoning that RUMI was missing.

Scientists don't just propose mechanisms. They ask:
  "If G(z) = G0(1 + αz), then BBN deuterium abundance shifts by X%."
  "If f_EDE = 5%, then CMB lensing is enhanced by Y%."
  "If dark sector coupling β exists, then structure growth differs by Z."

This module:
1. Takes a theory with equations and parameters
2. Derives logical consequences using the equations
3. Checks each consequence against known observations
4. Reports which consequences are SUPPORTED, CONTRADICTED, or UNKNOWN

This is Pearl's counterfactual level — the strongest form of causal reasoning.
"""

import json
import re
import math
from typing import Dict, List, Optional


class CounterfactualReasoner:
    """
    Derive and test logical consequences of proposed theories.
    """

    # Known observational data for comparison
    OBSERVATIONAL_DATA = {
        "cosmology": {
            "H0_CMB": {"value": 67.4, "uncertainty": 0.5, "source": "Planck 2018"},
            "H0_SNe": {"value": 73.04, "uncertainty": 1.04, "source": "SH0ES"},
            "H0_tension_sigma": {"value": 5.0, "source": "Hubble tension significance"},
            "Omega_m": {"value": 0.315, "uncertainty": 0.007, "source": "Planck 2018"},
            "sigma8": {"value": 0.811, "uncertainty": 0.006, "source": "Planck 2018"},
            "N_eff": {"value": 2.99, "uncertainty": 0.17, "source": "Planck 2018"},
            "BBN_deuterium": {"value": 2.527e-5, "uncertainty": 0.030e-5, "source": "PDG"},
            "BBN_helium": {"value": 0.245, "uncertainty": 0.003, "source": "PDG"},
            "age_universe_Gyr": {"value": 13.8, "uncertainty": 0.02, "source": "Planck 2018"},
            "z_recombination": {"value": 1089.9, "source": "Planck 2018"},
            "f_EDE_limit": {"value": 0.07, "source": "ACT DR6 95% CL"},
            "G_dot_limit": {"value": 1e-13, "source": "Lunar Laser Ranging"},
        },
        "drug_discovery": {
            "KRAS_G12C_prevalence_NSCLC": {"value": 0.13, "source": "NSCLC mutation frequency"},
            "KRAS_G12C_prevalence_CRC": {"value": 0.03, "source": "CRC mutation frequency"},
            "sotorasib_response_rate": {"value": 0.37, "source": "CodeBreaK 100"},
            "adagrasib_response_rate": {"value": 0.43, "source": "KRYSTAL-1"},
        },
    }

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def reason(self, theory: dict, domain: str = "cosmology") -> dict:
        """
        Derive counterfactual consequences of a theory.

        Returns:
            {
                "counterfactuals": [...],
                "supported": [...],
                "contradicted": [...],
                "unknown": [...],
                "overall_consistency": 0.0-1.0
            }
        """
        # 1. Extract equations and parameters from theory
        equations = self._extract_equations(theory)
        parameters = self._extract_parameters(theory)

        # 2. Derive consequences algorithmically
        algo_consequences = self._derive_consequences(theory, equations, parameters, domain)

        # 3. LLM-based counterfactual reasoning
        llm_consequences = []
        if self.llm_call:
            llm_consequences = self._llm_counterfactuals(theory, domain)

        # 4. Merge and check against observations
        all_consequences = algo_consequences + llm_consequences
        checked = self._check_against_observations(all_consequences, domain)

        # 5. Categorize
        supported = [c for c in checked if c.get("status") == "SUPPORTED"]
        contradicted = [c for c in checked if c.get("status") == "CONTRADICTED"]
        unknown = [c for c in checked if c.get("status") == "UNKNOWN"]

        # 6. Overall consistency
        total = len(checked)
        if total > 0:
            consistency = (len(supported) - len(contradicted) * 2) / total
            consistency = max(0.0, min(1.0, consistency))
        else:
            consistency = 0.5

        return {
            "counterfactuals": checked,
            "supported": supported,
            "contradicted": contradicted,
            "unknown": unknown,
            "overall_consistency": round(consistency, 3),
            "total_derived": len(all_consequences),
            "total_checked": len(checked),
        }

    def _extract_equations(self, theory: dict) -> list:
        """Extract equations from theory."""
        equations = []
        text = theory.get("description", "") + " " + theory.get("mathematical_model", "")
        for step in theory.get("steps", []):
            text += " " + str(step)

        # Match equations like X = Y(1 + αz)
        for match in re.findall(r'([A-Za-z_][\w]*)\s*=\s*([^,.;\n]{5,80})', text):
            var, expr = match
            if len(var) > 1 and any(c.isalpha() for c in expr):
                equations.append({"variable": var, "expression": expr.strip()})

        return equations[:10]

    def _extract_parameters(self, theory: dict) -> dict:
        """Extract parameter values from theory."""
        params = {}

        for p in theory.get("key_parameters", []):
            if isinstance(p, dict):
                name = p.get("name", "")
                value = p.get("expected_value", "")
                if name and value:
                    # Try to extract numeric value
                    nums = re.findall(r'[\d.]+(?:e[+-]?\d+)?', str(value))
                    if nums:
                        try:
                            params[name] = float(nums[0])
                        except ValueError:
                            params[name] = nums[0]

        # Also from description
        desc = theory.get("description", "")
        for match in re.findall(r'(\w+)\s*[≈~=]\s*([\d.]+(?:e[+-]?\d+)?)', desc):
            try:
                params[match[0]] = float(match[1])
            except ValueError:
                pass

        return params

    def _derive_consequences(self, theory: dict, equations: list,
                              parameters: dict, domain: str) -> list:
        """Derive consequences algorithmically from equations."""
        consequences = []
        obs = self.OBSERVATIONAL_DATA.get(domain, self.OBSERVATIONAL_DATA.get("cosmology", {}))

        # Check if theory modifies known constants
        desc = (theory.get("description", "") + " " + theory.get("mathematical_model", "")).lower()

        # Consequence: varying G affects BBN
        if "gravitational" in desc and "constant" in desc:
            # G(z) = G0(1 + αz) → ΔG/G at BBN ≈ α × z_BBN
            alpha = parameters.get("alpha", parameters.get("α", None))
            if alpha is None:
                # Try to extract from text
                alphas = re.findall(r'(\d+\.?\d*)\s*(?:×\s*10\^?\(?(-?\d+)\)?)?', desc)
                for num, exp in alphas:
                    try:
                        alpha = float(num) * (10 ** int(exp)) if exp else float(num)
                        if 1e-10 < alpha < 1:
                            break
                        alpha = None
                    except ValueError:
                        alpha = None

            if alpha and isinstance(alpha, (int, float)):
                z_bbn = 1e9  # BBN redshift
                delta_g_g = alpha * z_bbn
                # Effect on BBN: ΔD/D ≈ 2 × ΔG/G (approximate)
                delta_D_D = 2 * delta_g_g
                D_obs = obs.get("BBN_deuterium", {}).get("value", 2.527e-5)
                D_err = obs.get("BBN_deuterium", {}).get("uncertainty", 0.030e-5)
                delta_D = D_obs * delta_D_D
                sigma_deviation = abs(delta_D) / D_err if D_err > 0 else 0

                consequences.append({
                    "consequence": f"Varying G with α={alpha:.2e} shifts BBN deuterium by ΔD/D = {delta_D_D:.2e}",
                    "observable": "BBN deuterium abundance",
                    "predicted_value": D_obs + delta_D,
                    "observed_value": D_obs,
                    "deviation_sigma": round(sigma_deviation, 1),
                    "status": "CONTRADICTED" if sigma_deviation > 3 else "SUPPORTED" if sigma_deviation < 1 else "UNKNOWN",
                    "source": "algorithmic_derivation",
                })

                # Effect on H0
                z_rec = obs.get("z_recombination", {}).get("value", 1089.9)
                H0_cmb = obs.get("H0_CMB", {}).get("value", 67.4)
                delta_H0 = H0_cmb * alpha * z_rec
                H0_target = obs.get("H0_SNe", {}).get("value", 73.04)
                tension_residual = abs((H0_cmb + delta_H0) - H0_target)

                consequences.append({
                    "consequence": f"Varying G with α={alpha:.2e} shifts H₀ by {delta_H0:.1f} km/s/Mpc",
                    "observable": "Hubble constant",
                    "predicted_value": round(H0_cmb + delta_H0, 1),
                    "observed_value": H0_target,
                    "residual": round(tension_residual, 1),
                    "status": "SUPPORTED" if tension_residual < 2 else "UNKNOWN",
                    "source": "algorithmic_derivation",
                })

                # Ġ/G constraint
                g_dot = alpha * 70  # H0 in km/s/Mpc → /Gyr → /yr
                g_dot_per_yr = g_dot * 3.24e-20  # convert
                limit = obs.get("G_dot_limit", {}).get("value", 1e-13)
                consequences.append({
                    "consequence": f"|Ġ/G| ≈ {g_dot_per_yr:.1e} /yr from varying G with α={alpha:.2e}",
                    "observable": "Lunar laser ranging",
                    "predicted_value": g_dot_per_yr,
                    "observed_limit": limit,
                    "status": "CONTRADICTED" if g_dot_per_yr > limit else "SUPPORTED",
                    "source": "algorithmic_derivation",
                })

        # Consequence: EDE affects CMB lensing
        if "early dark energy" in desc or "ede" in desc:
            f_ede = parameters.get("f_EDE", parameters.get("f_ede", None))
            if f_ede is None:
                f_matches = re.findall(r'(\d+\.?\d*)\s*%', desc)
                if f_matches:
                    try:
                        f_ede = float(f_matches[0]) / 100.0
                    except ValueError:
                        pass

            if f_ede and isinstance(f_ede, (int, float)):
                limit = obs.get("f_EDE_limit", {}).get("value", 0.07)
                consequences.append({
                    "consequence": f"EDE with f_EDE={f_ede:.1%} should be detectable by CMB lensing",
                    "observable": "CMB lensing power",
                    "predicted_f_EDE": f_ede,
                    "observed_limit": limit,
                    "status": "CONTRADICTED" if f_ede > limit else "SUPPORTED",
                    "source": "algorithmic_derivation",
                })

                # Effect on H0
                H0_cmb = obs.get("H0_CMB", {}).get("value", 67.4)
                correction = 0.8
                H0_ede = H0_cmb * (1 + f_ede * correction / (1 - f_ede * correction))
                consequences.append({
                    "consequence": f"EDE with f_EDE={f_ede:.1%} produces H₀ ≈ {H0_ede:.1f} km/s/Mpc",
                    "observable": "Hubble constant",
                    "predicted_value": round(H0_ede, 1),
                    "observed_value": obs.get("H0_SNe", {}).get("value", 73.04),
                    "residual": round(abs(H0_ede - obs.get("H0_SNe", {}).get("value", 73.04)), 1),
                    "source": "algorithmic_derivation",
                })

        return consequences

    def _llm_counterfactuals(self, theory: dict, domain: str) -> list:
        """Use LLM to derive additional counterfactual consequences."""
        theory_desc = theory.get("description", "")[:500]
        params = json.dumps(theory.get("key_parameters", [])[:5])
        predictions = json.dumps(theory.get("predictions", [])[:5])

        prompt = f"""You are deriving counterfactual consequences of a scientific theory.

THEORY: {theory.get('name', '?')}
DOMAIN: {domain}
DESCRIPTION: {theory_desc}
PARAMETERS: {params}
EXISTING PREDICTIONS: {predictions}

For this theory, derive 3-5 ADDITIONAL consequences that MUST follow if the theory is true.
These should be consequences the theory DOESN'T explicitly predict but logically follows.

For each consequence:
1. State the logical chain: "If [theory premise], then [consequence]"
2. Quantify: include expected magnitude, order of magnitude, or percentage
3. Check: does this match known observations?

Output JSON:
{{
  "counterfactuals": [
    {{
      "if_then": "If [premise], then [consequence with numbers]",
      "observable": "what to measure",
      "expected_value": "quantitative prediction",
      "known_observation": "what we actually observe (if known)",
      "status": "SUPPORTED|CONTRADICTED|UNKNOWN"
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
                    result = json.loads(raw)
                    return result.get("counterfactuals", [])
        except Exception:
            pass
        return []

    def _check_against_observations(self, consequences: list, domain: str) -> list:
        """Check consequences against known observational data."""
        obs = self.OBSERVATIONAL_DATA.get(domain, self.OBSERVATIONAL_DATA.get("cosmology", {}))

        checked = []
        for c in consequences:
            if not isinstance(c, dict):
                continue

            # If already has status from algorithmic derivation, keep it
            if c.get("status") in ("SUPPORTED", "CONTRADICTED"):
                checked.append(c)
                continue

            # Try to match against known observations
            observable = c.get("observable", "").lower()
            status = "UNKNOWN"

            for obs_name, obs_data in obs.items():
                if obs_name.lower().replace("_", " ") in observable or observable in obs_name.lower().replace("_", " "):
                    obs_val = obs_data.get("value")
                    obs_err = obs_data.get("uncertainty", 0)
                    pred_val = c.get("expected_value") or c.get("predicted_value")

                    if obs_val and pred_val:
                        try:
                            pred = float(pred_val) if isinstance(pred_val, str) else pred_val
                            deviation = abs(pred - obs_val) / obs_err if obs_err > 0 else abs(pred - obs_val)
                            c["deviation_sigma"] = round(deviation, 1)
                            if deviation < 2:
                                status = "SUPPORTED"
                            elif deviation > 3:
                                status = "CONTRADICTED"
                            else:
                                status = "UNKNOWN"
                        except (ValueError, TypeError):
                            pass
                    break

            c["status"] = c.get("status", status)
            checked.append(c)

        return checked
