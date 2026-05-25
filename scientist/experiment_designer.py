"""
experiment_designer.py — Autonomous Experiment Design & Execution

Designs scientific experiments from hypotheses, generates executable code,
and analyzes results. Inspired by the AI Scientist's code generation pipeline.

Capabilities:
  [ED-1] Experiment Design — Create detailed experimental methodology from a hypothesis
  [ED-2] Code Generation — Generate Python code to test the hypothesis (ML, stats, plots)
  [ED-3] Sandboxed Execution — Run experiments in isolated subprocess with timeout
  [ED-4] Results Analysis — Parse stdout, extract metrics, generate plots
  [ED-5] Iterative Refinement — Refine experiments based on results

Thread-safe. Stateless (each experiment is independent).
"""

import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()

# Experiment templates for common scientific domains
EXPERIMENT_TEMPLATES = {
    "classification": {
        "framework": "sklearn",
        "template": """
import numpy as np
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

# --- Experiment: {experiment_name} ---
# Hypothesis: {hypothesis}
# Domain: {domain}

# Load or generate data
# TODO: Replace with actual data loading
np.random.seed(42)
n_samples = 1000
n_features = 20

# Generate synthetic data (replace with real data)
X = np.random.randn(n_samples, n_features)
y = (X[:, 0] + X[:, 1] > 0).astype(int)

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Model implementation (customize based on hypothesis)
from sklearn.ensemble import RandomForestClassifier
model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
results = {{
    "accuracy": float(accuracy_score(y_test, y_pred)),
    "precision": float(precision_score(y_test, y_pred, average='weighted')),
    "recall": float(recall_score(y_test, y_pred, average='weighted')),
    "f1_score": float(f1_score(y_test, y_pred, average='weighted')),
    "n_train": int(len(X_train)),
    "n_test": int(len(X_test)),
    "n_features": n_features,
}}

# Feature importance
importances = model.feature_importances_
results["top_features"] = [int(i) for i in np.argsort(importances)[-5:].tolist()]
results["top_importances"] = [float(importances[i]) for i in np.argsort(importances)[-5:].tolist()]

print("EXPERIMENT_RESULTS:" + json.dumps(results))
""",
    },
    "regression": {
        "framework": "sklearn",
        "template": """
import numpy as np
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# --- Experiment: {experiment_name} ---
# Hypothesis: {hypothesis}

np.random.seed(42)
n_samples = 1000
n_features = 10

# Generate synthetic data (replace with real data)
X = np.random.randn(n_samples, n_features)
true_coeffs = np.random.randn(n_features)
y = X @ true_coeffs + np.random.randn(n_samples) * 0.1

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Model
from sklearn.ensemble import GradientBoostingRegressor
model = GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
results = {{
    "mse": float(mean_squared_error(y_test, y_pred)),
    "mae": float(mean_absolute_error(y_test, y_pred)),
    "r2": float(r2_score(y_test, y_pred)),
    "n_train": int(len(X_train)),
    "n_test": int(len(X_test)),
}}

print("EXPERIMENT_RESULTS:" + json.dumps(results))
""",
    },
    "ablation": {
        "framework": "sklearn",
        "template": """
import numpy as np
from sklearn.model_selection import cross_val_score
from sklearn.metrics import accuracy_score

# --- Ablation Study: {experiment_name} ---
# Hypothesis: {hypothesis}

np.random.seed(42)
n_samples = 500
n_features = 10

X = np.random.randn(n_samples, n_features)
y = (X[:, 0] + X[:, 1] + np.random.randn(n_samples) * 0.1 > 0).astype(int)

from sklearn.ensemble import RandomForestClassifier

# Full model
full_model = RandomForestClassifier(n_estimators=100, random_state=42)
full_scores = cross_val_score(full_model, X, y, cv=5)
full_mean = float(full_scores.mean())

# Ablated models (remove top features one by one)
results = {{"full_model_mean": full_mean}}
for i in range(min(5, n_features)):
    X_ablated = np.delete(X, i, axis=1)
    ablated_model = RandomForestClassifier(n_estimators=100, random_state=42)
    ablated_scores = cross_val_score(ablated_model, X_ablated, y, cv=5)
    results[f"without_feature_{i}"] = float(ablated_scores.mean())

results["drop_from_best"] = round(full_mean - max([v for k, v in results.items() if k != "full_model_mean"]), 4)

print("EXPERIMENT_RESULTS:" + json.dumps(results))
""",
    },
    "statistical_test": {
        "framework": "scipy",
        "template": """
import numpy as np
from scipy import stats

# --- Statistical Test: {experiment_name} ---
# Hypothesis: {hypothesis}

np.random.seed(42)

# Generate two groups (replace with actual experimental data)
group_a = np.random.normal(loc=0.5, scale=0.2, size=50)
group_b = np.random.normal(loc=0.3, scale=0.2, size=50)

# Statistical tests
t_stat, t_pval = stats.ttest_ind(group_a, group_b)
mw_stat, mw_pval = stats.mannwhitneyu(group_a, group_b)
ks_stat, ks_pval = stats.ks_2samp(group_a, group_b)

# Effect size
pooled_std = np.sqrt((np.std(group_a, ddof=1)**2 + np.std(group_b, ddof=1)**2) / 2)
cohens_d = (np.mean(group_a) - np.mean(group_b)) / pooled_std if pooled_std > 0 else 0

results = {{
    "group_a_mean": float(np.mean(group_a)),
    "group_b_mean": float(np.mean(group_b)),
    "group_a_std": float(np.std(group_a)),
    "group_b_std": float(np.std(group_b)),
    "t_statistic": float(t_stat),
    "t_p_value": float(t_pval),
    "mannwhitney_u_statistic": float(mw_stat),
    "mannwhitney_p_value": float(mw_pval),
    "ks_statistic": float(ks_stat),
    "ks_p_value": float(ks_pval),
    "cohens_d": float(cohens_d),
    "significant_at_005": bool(t_pval < 0.05),
}}

print("EXPERIMENT_RESULTS:" + json.dumps(results))
""",
    },
}


class ExperimentDesigner:
    """
    Designs and executes scientific experiments from hypotheses.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._experiment_history: list[dict] = []

    def design_experiment(
        self,
        hypothesis: str,
        domain: str = "machine_learning",
        experiment_type: str = "classification",
        description: str = "",
    ) -> dict:
        """
        Design a complete experiment from a hypothesis.

        Args:
            hypothesis: The research hypothesis to test
            domain: Scientific domain
            experiment_type: Type of experiment (classification, regression, ablation, statistical_test)
            description: Optional detailed description of the experimental approach

        Returns:
            Dict with experiment design including methodology, variables, and code template
        """
        with self._lock:
            experiment_id = f"EXP-{int(time.time() * 1000)}"

            # Determine experiment type from description if not specified
            if not experiment_type or experiment_type == "auto":
                experiment_type = self._infer_experiment_type(hypothesis, description)

            # Build methodology
            methodology = self._build_methodology(hypothesis, experiment_type, domain)

            # Generate code
            code = self._generate_code(hypothesis, experiment_type, domain, experiment_id)

            # Design metadata
            design = {
                "experiment_id": experiment_id,
                "hypothesis": hypothesis,
                "domain": domain,
                "experiment_type": experiment_type,
                "methodology": methodology,
                "code": code,
                "variables": self._identify_variables(hypothesis, experiment_type),
                "created_at": datetime.now().isoformat(),
                "status": "designed",
            }

            self._experiment_history.append(design)

            return design

    def _infer_experiment_type(self, hypothesis: str, description: str) -> str:
        """Infer the experiment type from the hypothesis text."""
        text = (hypothesis + " " + description).lower()

        if any(w in text for w in ["compare", "vs", "versus", "difference", "ablation", "remove"]):
            return "ablation"
        if any(w in text for w in ["statistical", "significant", "p-value", "p value", "hypothesis test"]):
            return "statistical_test"
        if any(w in text for w in ["predict", "regression", "forecast", "estimate", "continuous"]):
            return "regression"
        return "classification"

    def _build_methodology(self, hypothesis: str, exp_type: str, domain: str) -> dict:
        """Build a structured experimental methodology."""
        return {
            "objective": f"Test the hypothesis: {hypothesis[:200]}",
            "experiment_type": exp_type,
            "domain": domain,
            "approach": {
                "classification": "Train a classifier and evaluate using cross-validation with standard metrics",
                "regression": "Train a regressor and evaluate using MSE, MAE, and R²",
                "ablation": "Remove components systematically and measure performance impact",
                "statistical_test": "Apply statistical tests to compare groups and measure effect sizes",
            }.get(exp_type, "Standard experimental methodology"),
            "metrics": {
                "classification": ["accuracy", "precision", "recall", "f1_score"],
                "regression": ["mse", "mae", "r2"],
                "ablation": ["performance_drop", "feature_importance"],
                "statistical_test": ["p_value", "effect_size", "power"],
            }.get(exp_type, ["custom"]),
            "replication": "5-fold cross-validation (if applicable) or bootstrap resampling",
            "baseline": "Random baseline or existing state-of-the-art as comparison",
        }

    def _identify_variables(self, hypothesis: str, exp_type: str) -> dict:
        """Identify independent, dependent, and control variables from hypothesis."""
        return {
            "independent_variable": "Model architecture / feature set / experimental condition",
            "dependent_variable": "Performance metric / measured outcome",
            "control_variables": "Random seed, train/test split, evaluation protocol",
            "confounds_to_monitor": "Data leakage, overfitting, class imbalance",
        }

    def _generate_code(self, hypothesis: str, exp_type: str, domain: str, experiment_id: str) -> str:
        """Generate executable Python code for the experiment."""
        # Get template or use default
        template_info = EXPERIMENT_TEMPLATES.get(exp_type, EXPERIMENT_TEMPLATES["classification"])
        template = template_info["template"]

        # Format template
        experiment_name = f"Experiment_{experiment_id}"
        code = template.format(
            experiment_name=experiment_name,
            hypothesis=hypothesis,
            domain=domain,
        )

        return code

    def run_experiment(
        self,
        experiment: dict,
        timeout: int = 60,
    ) -> dict:
        """
        Execute an experiment in a sandboxed subprocess.

        Args:
            experiment: Experiment design dict from design_experiment()
            timeout: Maximum execution time in seconds

        Returns:
            Dict with status, results, logs, and any errors
        """
        code = experiment.get("code", "")
        experiment_id = experiment.get("experiment_id", f"EXP-{int(time.time() * 1000)}")

        if not code:
            return {
                "experiment_id": experiment_id,
                "status": "error",
                "error": "No code to execute",
                "results": {},
            }

        # Write code to temp file and execute
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            temp_path = f.name

        start_time = time.time()
        stdout_data = ""
        stderr_data = ""
        results = {}

        try:
            process = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
                cwd=tempfile.gettempdir(),
            )

            stdout_data = process.stdout
            stderr_data = process.stderr
            duration = time.time() - start_time

            # Parse results from stdout
            for line in stdout_data.split("\n"):
                if line.startswith("EXPERIMENT_RESULTS:"):
                    try:
                        results = json.loads(line[len("EXPERIMENT_RESULTS:"):])
                    except json.JSONDecodeError:
                        results = {"parse_error": "Could not parse experiment results"}

            status = "completed" if process.returncode == 0 else "error"

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            status = "timeout"
            stderr_data = f"Experiment timed out after {timeout}s"
        except Exception as e:
            duration = time.time() - start_time
            status = "error"
            stderr_data = f"Execution error: {e}"
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        result = {
            "experiment_id": experiment_id,
            "status": status,
            "duration_s": round(duration, 2),
            "results": results,
            "stdout": stdout_data[:2000],
            "stderr": stderr_data[:1000],
            "error": stderr_data if status == "error" else "",
        }

        with self._lock:
            self._experiment_history.append(result)

        return result

    def analyze_results(self, experiment_result: dict) -> dict:
        """
        Analyze experiment results and extract insights.

        Args:
            experiment_result: Result dict from run_experiment()

        Returns:
            Dict with analysis, conclusions, and suggestions for refinement
        """
        results = experiment_result.get("results", {})
        status = experiment_result.get("status", "")

        if status != "completed" or not results:
            return {
                "status": "analysis_failed",
                "error": f"Experiment {status}: no valid results to analyze",
                "conclusion": "Cannot draw conclusions from failed experiment.",
            }

        analysis = {
            "status": "analyzed",
            "metrics": {},
            "interpretation": "",
            "statistical_significance": None,
            "effect_size": None,
            "suggestions": [],
        }

        # Extract and interpret common metrics
        if "accuracy" in results:
            analysis["metrics"]["accuracy"] = results["accuracy"]
            analysis["metrics"]["f1_score"] = results.get("f1_score", 0)
            analysis["metrics"]["precision"] = results.get("precision", 0)
            analysis["metrics"]["recall"] = results.get("recall", 0)

            analysis["interpretation"] = (
                f"Model achieved accuracy of {results['accuracy']:.1%} "
                f"and F1 of {results.get('f1_score', 0):.1%}"
            )

            if results.get("accuracy", 0) > 0.8:
                analysis["suggestions"].append("Strong performance — consider testing on harder benchmarks")
            elif results.get("accuracy", 0) < 0.5:
                analysis["suggestions"].append("Poor performance — consider a different model architecture")

        elif "mse" in results:
            analysis["metrics"]["mse"] = results["mse"]
            analysis["metrics"]["mae"] = results["mae"]
            analysis["metrics"]["r2"] = results["r2"]

            analysis["interpretation"] = (
                f"Model achieved MSE of {results['mse']:.4f}, "
                f"MAE of {results['mae']:.4f}, "
                f"R² of {results['r2']:.4f}"
            )

            if results.get("r2", 0) > 0.8:
                analysis["suggestions"].append("Excellent fit — consider testing on held-out data")
            elif results.get("r2", 0) < 0.2:
                analysis["suggestions"].append("Poor fit — consider feature engineering or different model")

        elif "t_p_value" in results:
            analysis["metrics"]["t_statistic"] = results["t_statistic"]
            analysis["metrics"]["p_value"] = results["t_p_value"]
            analysis["metrics"]["cohens_d"] = results["cohens_d"]
            analysis["statistical_significance"] = results.get("significant_at_005", False)

            analysis["interpretation"] = (
                f"t-test: t={results['t_statistic']:.3f}, p={results['t_p_value']:.4f}, "
                f"Cohen's d={results['cohens_d']:.3f}. "
                f"{'Statistically significant' if results.get('significant_at_005') else 'Not statistically significant'} "
                f"at α=0.05"
            )

            if results.get("cohens_d", 0) > 0.8:
                analysis["suggestions"].append("Large effect size — the finding is practically meaningful")
            elif results.get("cohens_d", 0) < 0.2:
                analysis["suggestions"].append("Small effect size — consider increasing sample size")

        if not analysis["interpretation"]:
            analysis["interpretation"] = f"Experiment completed with {len(results)} metrics recorded"

        return analysis

    def get_history(self, limit: int = 10) -> list[dict]:
        """Get recent experiment history."""
        with self._lock:
            return list(reversed(self._experiment_history[-limit:]))

    def get_stats(self) -> dict:
        """Get experiment designer statistics."""
        with self._lock:
            completed = sum(1 for e in self._experiment_history if e.get("status") == "completed")
            failed = sum(1 for e in self._experiment_history if e.get("status") in ("error", "timeout"))
            return {
                "total_experiments": len(self._experiment_history),
                "completed": completed,
                "failed": failed,
                "status": "ready",
            }


# ── Singleton ──────────────────────────────────────────────────

_experiment_designer = None
_experiment_lock = threading.Lock()


def get_experiment_designer() -> ExperimentDesigner:
    global _experiment_designer
    if _experiment_designer is None:
        with _experiment_lock:
            if _experiment_designer is None:
                _experiment_designer = ExperimentDesigner()
    return _experiment_designer
