"""
B3 — the neutral critics must not run on the generator's model family.

Self-preference bias: a model asked to attack/review its own output tends to
be softer on it. This test parses PHASE_PROVIDERS out of the pipeline (via AST,
so it survives refactors) and asserts the critic phases use a provider that the
generation phases never use.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PIPELINE = ROOT / "discovery" / "discovery_pipeline_v2.py"

GENERATOR_PHASES = {
    "missing_variables", "gap_discovery", "mechanism_generation",
    "prediction_engine", "theory_competition",
}
CRITIC_PHASES = {"adversarial_test", "critical_evaluation", "skeptic_review"}


def _resolve_phase_providers() -> dict:
    tree = ast.parse(PIPELINE.read_text(encoding="utf-8"))

    consts: dict = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            consts[node.targets[0].id] = node.value.value

    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "PHASE_PROVIDERS"
                and isinstance(node.value, ast.Dict)):
            out = {}
            for k, v in zip(node.value.keys, node.value.values):
                if not (isinstance(k, ast.Constant) and isinstance(k.value, str)):
                    continue
                if isinstance(v, ast.Constant):
                    out[k.value] = v.value
                elif isinstance(v, ast.Name):
                    out[k.value] = consts.get(v.id, f"<{v.id}>")
            return out
    return {}


def test_critic_phases_are_declared():
    providers = _resolve_phase_providers()
    assert providers, "PHASE_PROVIDERS not found"
    for p in CRITIC_PHASES:
        assert p in providers, f"critic phase {p} missing from PHASE_PROVIDERS"


def test_critics_use_a_family_the_generator_never_uses():
    providers = _resolve_phase_providers()
    gen = {providers[p] for p in GENERATOR_PHASES if p in providers}
    critics = {providers[p] for p in CRITIC_PHASES if p in providers}
    assert critics, "no critic providers resolved"
    assert not (critics & gen), (
        f"critics share a model family with the generator: {sorted(critics & gen)}"
    )


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
