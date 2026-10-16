"""
eval/ — RUMI's External Evaluation Harness.

WHY THIS EXISTS
---------------
RUMI currently grades itself: the headline "discovery score" is built from
numbers RUMI's own LLM produces (confidence, novelty), and the Reflexion
self-improvement loop then edits prompts/thresholds to raise those same
self-reported numbers. That is the reward-hacking failure mode documented for
autonomous research agents.

This package is the countermeasure: a FROZEN, OUT-OF-REACH measuring rig.

  * It reads a finished report as DATA and computes quality numbers.
  * Its core metrics are DETERMINISTIC (no LLM) -> cannot drift, cannot be
    prompt-gamed.
  * It never calls RUMI's own scorers.
  * The agent must never be able to modify anything under eval/.

See README.md for the full contract.

Public API:
    from eval.harness import run_external_eval
"""

__all__ = ["run_external_eval"]


def __getattr__(name: str):
    """Lazy access so `python -m eval.harness` doesn't double-import the module."""
    if name == "run_external_eval":
        from .harness import run_external_eval
        return run_external_eval
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
