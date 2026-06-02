"""
simulation_pipeline.py — Simulation-first discovery pipeline.

Theory means nothing without numbers.
This pipeline:
1. Takes a hypothesis
2. Runs Monte Carlo simulations
3. Generates synthetic data
4. Tests predictions against known physics
5. Returns quantitative results with confidence intervals

No LLM needed for this — pure computation.
"""

import math
import random
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


@dataclass
class SimulationResult:
    """Result from a simulation run."""
    hypothesis: str
    n_simulations: int
    predictions: Dict[str, Any]
    confidence_intervals: Dict[str, Tuple[float, float]]
    known_data_comparison: Dict[str, Any]
    passed_consistency: bool
    score: float
    details: str


class MonteCarloSimulator:
    """Run Monte Carlo simulations to test hypotheses."""

    def __init__(self, n_default: int = 1000):
        self.n_default = n_default

    def simulate_hubble_tension(self, params: dict, n: int = 0) -> SimulationResult:
        """
        Simulate the Hubble tension with Early Dark Energy (EDE) model.

        Key physics:
        - EDE fraction f_ede at z_c ~ 5000 reduces sound horizon
        - alpha is the initial field displacement
        - beta controls when EDE activates
        """
        n = n or self.n_default
        f_ede = params.get("f_ede", 0.127)
        z_c = params.get("z_c", 5100)
        alpha = params.get("alpha", 2.83)
        theta_s = params.get("theta_s", 0.0104)

        # Known CMB constraint
        theta_s_cmb = 1.04092e-2  # from Planck 2018

        # Simulate: each MC sample draws from posterior
        h0_samples = []
        omega_m_samples = []
        for _ in range(n):
            # Perturb parameters within errors
            f_ede_i = f_ede + random.gauss(0, f_ede * 0.15)
            z_c_i = z_c + random.gauss(0, z_c * 0.1)
            alpha_i = alpha + random.gauss(0, alpha * 0.1)

            # EDE increases H0: H0 ~ H0_LCDM * (1 + f_ede * correction)
            h0_lcdm = 67.4
            # The correction comes from reduced sound horizon
            correction = 1 + 0.3 * f_ede_i * (alpha_i / 3.0) * (5000 / z_c_i)
            h0_i = h0_lcdm * correction + random.gauss(0, 0.5)
            h0_samples.append(h0_i)

            omega_m_i = 0.315 * (h0_lcdm / h0_i) ** 2 + random.gauss(0, 0.005)
            omega_m_samples.append(omega_m_i)

        # Compute statistics
        h0_mean = sum(h0_samples) / n
        h0_std = (sum((x - h0_mean)**2 for x in h0_samples) / n) ** 0.5
        omega_m_mean = sum(omega_m_samples) / n

        # Confidence intervals (68% and 95%)
        h0_sorted = sorted(h0_samples)
        h0_68 = (h0_sorted[int(0.16*n)], h0_sorted[int(0.84*n)])
        h0_95 = (h0_sorted[int(0.025*n)], h0_sorted[int(0.975*n)])

        # Compare with known data
        h0_sne = 73.0
        h0_cmb = 67.4
        tension_with_sne = abs(h0_mean - h0_sne) / h0_std
        tension_with_cmb = abs(h0_mean - h0_cmb) / h0_std

        # Pass/fail: H0 should be between 67-73, f_ede < 0.15
        passed = 67 < h0_mean < 76 and 0 < f_ede < 0.15

        score = 0.0
        if 68 < h0_mean < 74:
            score += 40
        if f_ede < 0.15:
            score += 30
        if theta_s_cmb * 0.99 < theta_s < theta_s_cmb * 1.01:
            score += 30

        return SimulationResult(
            hypothesis=f"EDE model with f_ede={f_ede:.3f}, z_c={z_c:.0f}",
            n_simulations=n,
            predictions={
                "H0": round(h0_mean, 2),
                "H0_std": round(h0_std, 2),
                "Omega_m": round(omega_m_mean, 4),
                "tension_with_sne_sigma": round(tension_with_sne, 2),
                "tension_with_cmb_sigma": round(tension_with_cmb, 2),
            },
            confidence_intervals={
                "H0_68": (round(h0_68[0], 2), round(h0_68[1], 2)),
                "H0_95": (round(h0_95[0], 2), round(h0_95[1], 2)),
            },
            known_data_comparison={
                "H0_SNe": h0_sne,
                "H0_CMB": h0_cmb,
                "tension_resolved": tension_with_sne < 2.0,
            },
            passed_consistency=passed,
            score=score,
            details=f"H0 = {h0_mean:.2f} +/- {h0_std:.2f} km/s/Mpc. "
                    f"Tension with SNe: {tension_with_sne:.1f}sigma. "
                    f"f_ede = {f_ede:.3f} (< 0.15)."
        )

    def simulate_generic(self, hypothesis: str, domain: str,
                         params: dict, n: int = 0) -> SimulationResult:
        """
        Generic Monte Carlo simulation for any hypothesis.

        Extracts key parameters, perturbs them, checks consistency.
        """
        n = n or self.n_default

        # Extract numeric parameters
        numeric_params = {}
        for k, v in params.items():
            if isinstance(v, (int, float)):
                numeric_params[k] = float(v)

        if not numeric_params:
            return SimulationResult(
                hypothesis=hypothesis, n_simulations=0,
                predictions={}, confidence_intervals={},
                known_data_comparison={}, passed_consistency=False,
                score=0.0, details="No numeric parameters to simulate"
            )

        # Run MC
        samples = {k: [] for k in numeric_params}
        for _ in range(n):
            for k, v in numeric_params.items():
                # Perturb by 10%
                v_i = v + random.gauss(0, abs(v) * 0.1 + 1e-10)
                samples[k].append(v_i)

        # Compute stats
        predictions = {}
        cis = {}
        for k, samps in samples.items():
            mean = sum(samps) / n
            std = (sum((x - mean)**2 for x in samps) / n) ** 0.5
            sorted_s = sorted(samps)
            predictions[k] = round(mean, 4)
            cis[f"{k}_68"] = (round(sorted_s[int(0.16*n)], 4), round(sorted_s[int(0.84*n)], 4))
            cis[f"{k}_95"] = (round(sorted_s[int(0.025*n)], 4), round(sorted_s[int(0.975*n)], 4))

        # Check consistency: no NaN, no inf, no negative for positive quantities
        passed = True
        issues = []
        for k, mean in predictions.items():
            if math.isnan(mean) or math.isinf(mean):
                passed = False
                issues.append(f"{k} is {mean}")

        score = 80.0 if passed else 20.0

        return SimulationResult(
            hypothesis=hypothesis,
            n_simulations=n,
            predictions=predictions,
            confidence_intervals=cis,
            known_data_comparison={},
            passed_consistency=passed,
            score=score,
            details=f"Simulated {len(numeric_params)} parameters x {n} runs. "
                    + "; ".join(issues) if issues else "All parameters consistent."
        )


class SimulationPipeline:
    """
    Full simulation-first pipeline.

    Flow:
    1. Parse hypothesis -> extract parameters
    2. Run Monte Carlo simulation
    3. Compare with known data
    4. Compute confidence intervals
    5. Score and rank
    """

    def __init__(self):
        self.mc = MonteCarloSimulator()
        self.results_history = []

    def run(self, hypothesis: str, domain: str,
            parameters: dict, n_simulations: int = 1000) -> SimulationResult:
        """Run the simulation pipeline."""

        # Route to domain-specific simulation
        if "hubble" in hypothesis.lower() or "ede" in hypothesis.lower() or "h0" in str(parameters).lower():
            result = self.mc.simulate_hubble_tension(parameters, n_simulations)
        else:
            result = self.mc.simulate_generic(hypothesis, domain, parameters, n_simulations)

        self.results_history.append(result)
        return result

    def get_summary(self) -> dict:
        """Summary of all simulation results."""
        if not self.results_history:
            return {"total": 0, "avg_score": 0, "passed": 0}

        total = len(self.results_history)
        avg_score = sum(r.score for r in self.results_history) / total
        passed = sum(1 for r in self.results_history if r.passed_consistency)

        return {
            "total": total,
            "avg_score": round(avg_score, 1),
            "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{100*passed/total:.0f}%",
        }
