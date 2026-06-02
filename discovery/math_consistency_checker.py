"""
math_consistency_checker.py — Verify theories are mathematically sound.

Before accepting a theory, check:
1. Can equations be derived?
2. Can parameters be estimated?
3. Are units consistent?
4. Does it violate known constraints?
5. Do the numbers make sense (order of magnitude)?

This is what separates real science from word salad.
"""

import re
import math
from typing import Dict, List, Optional, Tuple


# Physical constants (SI units)
CONSTANTS = {
    "c": {"value": 2.998e8, "units": "m/s", "name": "speed of light"},
    "h": {"value": 6.626e-34, "units": "J*s", "name": "Planck constant"},
    "hbar": {"value": 1.055e-34, "units": "J*s", "name": "reduced Planck constant"},
    "G": {"value": 6.674e-11, "units": "m^3/kg/s^2", "name": "gravitational constant"},
    "k_B": {"value": 1.381e-23, "units": "J/K", "name": "Boltzmann constant"},
    "e": {"value": 1.602e-19, "units": "C", "name": "electron charge"},
    "m_e": {"value": 9.109e-31, "units": "kg", "name": "electron mass"},
    "m_p": {"value": 1.673e-27, "units": "kg", "name": "proton mass"},
    "N_A": {"value": 6.022e23, "units": "1/mol", "name": "Avogadro number"},
    "sigma_SB": {"value": 5.670e-8, "units": "W/m^2/K^4", "name": "Stefan-Boltzmann constant"},
    "R": {"value": 8.314, "units": "J/mol/K", "name": "gas constant"},
    "H0": {"value": 67.4, "units": "km/s/Mpc", "name": "Hubble constant (CMB)"},
    "H0_sne": {"value": 73.0, "units": "km/s/Mpc", "name": "Hubble constant (SNe)"},
    "T_CMB": {"value": 2.725, "units": "K", "name": "CMB temperature"},
    "Omega_b": {"value": 0.049, "units": "dimensionless", "name": "baryon density parameter"},
    "Omega_m": {"value": 0.315, "units": "dimensionless", "name": "matter density parameter"},
    "Omega_Lambda": {"value": 0.685, "units": "dimensionless", "name": "dark energy density"},
    "sigma8": {"value": 0.811, "units": "dimensionless", "name": "matter fluctuation amplitude"},
    "N_eff": {"value": 2.99, "units": "dimensionless", "name": "effective neutrino species"},
    "z_recomb": {"value": 1089.9, "units": "dimensionless", "name": "recombination redshift"},
    "age_universe": {"value": 13.8, "units": "Gyr", "name": "age of universe"},
}

# Unit dimensions
UNIT_DIMENSIONS = {
    "m": {"length": 1},
    "kg": {"mass": 1},
    "s": {"time": 1},
    "K": {"temperature": 1},
    "mol": {"amount": 1},
    "A": {"current": 1},
    "cd": {"luminosity": 1},
    "m/s": {"length": 1, "time": -1},
    "m/s^2": {"length": 1, "time": -2},
    "N": {"mass": 1, "length": 1, "time": -2},
    "J": {"mass": 1, "length": 2, "time": -2},
    "W": {"mass": 1, "length": 2, "time": -3},
    "Pa": {"mass": 1, "length": -1, "time": -2},
    "Hz": {"time": -1},
    "eV": {"mass": 1, "length": 2, "time": -2},
    "km/s/Mpc": {"time": -1},
    "rad": {"angle": 1},
    "sr": {"angle": 2},
}


class MathConsistencyChecker:
    """
    Verify mathematical consistency of scientific theories.
    """

    def check_theory(self, theory: dict, domain: str = "") -> dict:
        """
        Check a theory for mathematical consistency.

        Returns:
            {
                "consistent": bool,
                "checks": [...],
                "violations": [...],
                "warnings": [...],
                "order_of_magnitude": {...},
                "score": 0-100
            }
        """
        checks = []
        violations = []
        warnings = []

        # 1. Extract equations and parameters
        equations = self._extract_equations(theory)
        parameters = self._extract_parameters(theory)

        # 2. Check equations can be parsed
        eq_check = self._check_equations(equations)
        checks.append(eq_check)
        if not eq_check["passed"]:
            violations.append(eq_check["issue"])

        # 3. Check parameter ranges
        param_check = self._check_parameters(parameters, domain)
        checks.append(param_check)
        if not param_check["passed"]:
            warnings.append(param_check["issue"])

        # 4. Check unit consistency
        unit_check = self._check_units(equations, parameters)
        checks.append(unit_check)
        if not unit_check["passed"]:
            violations.append(unit_check["issue"])

        # 5. Check against known constraints
        constraint_check = self._check_constraints(theory, parameters, domain)
        checks.append(constraint_check)
        if not constraint_check["passed"]:
            violations.append(constraint_check["issue"])

        # 6. Order of magnitude check
        magnitude_check = self._check_order_of_magnitude(parameters, domain)
        checks.append(magnitude_check)
        if not magnitude_check["passed"]:
            warnings.append(magnitude_check["issue"])

        # 7. Check predictions have numbers
        pred_check = self._check_predictions_have_numbers(theory)
        checks.append(pred_check)
        if not pred_check["passed"]:
            warnings.append(pred_check["issue"])

        # Compute score
        passed = sum(1 for c in checks if c["passed"])
        total = len(checks)
        score = int(100 * passed / total) if total > 0 else 0

        consistent = len(violations) == 0

        return {
            "consistent": consistent,
            "checks": checks,
            "violations": violations,
            "warnings": warnings,
            "score": score,
            "equations_found": len(equations),
            "parameters_found": len(parameters),
        }

    def _extract_equations(self, theory: dict) -> list:
        """Extract equations from theory."""
        equations = []
        text = theory.get("description", "") + " " + theory.get("mathematical_model", "")
        for step in theory.get("steps", []):
            text += " " + str(step)
        for eq in theory.get("equations", []):
            if isinstance(eq, str):
                equations.append(eq)
        for param in theory.get("key_parameters", []):
            if isinstance(param, dict):
                ev = param.get("expected_value", "")
                if ev and any(c.isdigit() for c in str(ev)):
                    equations.append(f"{param.get('name', '?')} = {ev}")

        # Extract from text
        for match in re.findall(r'([A-Za-z_]\w*)\s*=\s*([^,.;\n]{5,80})', text):
            var, expr = match
            if len(var) > 1 and any(c.isalpha() for c in expr):
                equations.append(f"{var} = {expr.strip()}")

        return equations[:15]

    def _extract_parameters(self, theory: dict) -> dict:
        """Extract parameter values."""
        params = {}
        for p in theory.get("key_parameters", []):
            if isinstance(p, dict):
                name = p.get("name", "")
                value = p.get("expected_value", "")
                if name and value:
                    nums = re.findall(r'[\d.]+(?:e[+-]?\d+)?', str(value))
                    if nums:
                        try:
                            params[name] = float(nums[0])
                        except ValueError:
                            params[name] = nums[0]
        return params

    def _check_equations(self, equations: list) -> dict:
        """Check that equations are parseable."""
        if not equations:
            return {"check": "equations_parseable", "passed": False,
                    "issue": "No equations found — theory lacks mathematical formalism"}

        parseable = 0
        for eq in equations:
            if "=" in eq and len(eq) > 5:
                parseable += 1

        if parseable == 0:
            return {"check": "equations_parseable", "passed": False,
                    "issue": "No valid equations (need X = expression format)"}

        return {"check": "equations_parseable", "passed": True,
                "detail": f"{parseable}/{len(equations)} equations parseable"}

    def _check_parameters(self, parameters: dict, domain: str) -> dict:
        """Check parameter values are reasonable."""
        if not parameters:
            return {"check": "parameters_reasonable", "passed": False,
                    "issue": "No parameters with numeric values found"}

        issues = []
        for name, value in parameters.items():
            if isinstance(value, (int, float)):
                # Check for unreasonable values
                if value == 0:
                    issues.append(f"{name} = 0 (suspicious — usually non-zero)")
                elif abs(value) > 1e100:
                    issues.append(f"{name} = {value} (unreasonably large)")
                elif abs(value) < 1e-100 and value != 0:
                    issues.append(f"{name} = {value} (unreasonally small)")

        if issues:
            return {"check": "parameters_reasonable", "passed": False,
                    "issue": "; ".join(issues)}

        return {"check": "parameters_reasonable", "passed": True,
                "detail": f"{len(parameters)} parameters checked"}

    def _check_units(self, equations: list, parameters: dict) -> dict:
        """Check unit consistency (basic check)."""
        # Basic check: look for common unit mismatches
        issues = []
        for eq in equations:
            eq_lower = eq.lower()
            # Check for mixing dimensionless with dimensional
            if "km/s/mpc" in eq_lower and "seconds" in eq_lower:
                issues.append(f"Unit mismatch in: {eq[:60]}")
            # Check for adding quantities with different units
            if "+" in eq:
                parts = eq.split("+")
                # Very basic check — would need full dimensional analysis for real checking

        if issues:
            return {"check": "unit_consistency", "passed": False,
                    "issue": "; ".join(issues)}

        return {"check": "unit_consistency", "passed": True,
                "detail": "Basic unit check passed (full dimensional analysis not implemented)"}

    def _check_constraints(self, theory: dict, parameters: dict, domain: str) -> dict:
        """Check against known physical constraints."""
        issues = []

        desc = (theory.get("description", "") + " " + theory.get("mathematical_model", "")).lower()

        # Speed of light constraint
        if "velocity" in desc or "speed" in desc:
            for name, value in parameters.items():
                if isinstance(value, (int, float)) and value > 3e8:
                    issues.append(f"{name} = {value} exceeds speed of light (c = 3e8 m/s)")

        # Hubble constant constraint
        if "h0" in desc or "hubble" in desc:
            for name, value in parameters.items():
                if isinstance(value, (int, float)):
                    if "h0" in name.lower() and (value < 60 or value > 80):
                        issues.append(f"{name} = {value} outside observed range (60-80 km/s/Mpc)")

        # Positive definiteness
        for name, value in parameters.items():
            if isinstance(value, (int, float)):
                if any(name.lower().startswith(p) for p in ["mass", "energy", "temperature", "density"]):
                    if value < 0:
                        issues.append(f"{name} = {value} is negative (should be positive)")

        if issues:
            return {"check": "constraint_violations", "passed": False,
                    "issue": "; ".join(issues)}

        return {"check": "constraint_violations", "passed": True,
                "detail": "No known constraints violated"}

    def _check_order_of_magnitude(self, parameters: dict, domain: str) -> dict:
        """Check if parameter values are in the right order of magnitude."""
        # Known reasonable ranges for common parameters
        reasonable_ranges = {
            "alpha": (1e-10, 1),
            "f_ede": (0, 0.2),
            "f_EDE": (0, 0.2),
            "beta": (0, 10),
            "delta": (0, 1),
            "h0": (60, 80),
            "H0": (60, 80),
        }

        issues = []
        for name, value in parameters.items():
            if isinstance(value, (int, float)):
                for param_name, (low, high) in reasonable_ranges.items():
                    if param_name in name.lower():
                        if value < low or value > high:
                            issues.append(f"{name} = {value} outside reasonable range [{low}, {high}]")

        if issues:
            return {"check": "order_of_magnitude", "passed": False,
                    "issue": "; ".join(issues)}

        return {"check": "order_of_magnitude", "passed": True,
                "detail": "Parameter values in reasonable ranges"}

    def _check_predictions_have_numbers(self, theory: dict) -> dict:
        """Check that predictions contain quantitative content."""
        predictions = theory.get("predictions", [])
        if not predictions:
            return {"check": "quantitative_predictions", "passed": False,
                    "issue": "No predictions generated"}

        quant_count = 0
        for pred in predictions:
            if isinstance(pred, str) and any(c.isdigit() for c in pred):
                quant_count += 1
            elif isinstance(pred, dict) and any(c.isdigit() for c in pred.get("statement", "")):
                quant_count += 1

        if quant_count == 0:
            return {"check": "quantitative_predictions", "passed": False,
                    "issue": "Predictions lack quantitative content (no numbers)"}

        return {"check": "quantitative_predictions", "passed": True,
                "detail": f"{quant_count}/{len(predictions)} predictions have numbers"}
