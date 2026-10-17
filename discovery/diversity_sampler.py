"""
discovery/diversity_sampler.py — reward-proportional (GFlowNet-style) selection.

Bengio's GFlowNets define a policy whose sampling probability is proportional to
a reward, P(x) ∝ R(x). Unlike top-k / argmax selection, this keeps mode
diversity: a distinct, slightly lower-reward candidate is not automatically
thrown away.

This module implements that *sampling property* (proportional-to-reward
selection with a temperature knob) combined with sequential niching
(max-marginal-relevance, the mechanism behind DPP/MMR selectors). Together they
give the population-level behaviour GFlowNets are valued for, in closed form.

What this is NOT: a trained flow network. There is no forward policy, no
flow-matching objective and no learned parameters. It is a deterministic
(seeded) sampler over an already-generated candidate set. The docstrings say so
on purpose — the old in-pipeline "GFlowNet" bonus was a capped count of unique
words and earned the name only loosely. This replaces it with the real
proportional-sampling property and honest labelling.
"""
from __future__ import annotations

import math
import random
import re
from typing import Callable, Iterable, Sequence

# Function words carry no topical signal and would inflate apparent similarity.
_STOPWORDS = frozenset(
    """the a an and or of to in for on with by as at from that this these those
    is are was were be been being it its their there here which who whom whose
    what when where why how not no nor but if then than so such can could may
    might must shall should will would do does did done have has had having
    about into over under between across during without within also more most
    other others some any each both few many much very own same too only just
    than then thus hence therefore however although while because due via
    using used use new novel based upon both versus vs""".split()
)


def content_words(text: str) -> set[str]:
    """Lowercased content tokens: no stopwords, no tokens of length <= 2."""
    if not text:
        return set()
    return {
        w for w in re.findall(r"[a-z0-9]+", text.lower())
        if len(w) > 2 and w not in _STOPWORDS
    }


def theory_text(theory: dict) -> str:
    """The text used to judge a theory's distinctiveness."""
    if not isinstance(theory, dict):
        return str(theory or "")
    name = theory.get("name", "") or ""
    body = theory.get("description", "") or theory.get("mechanism", "") or ""
    return f"{name} {body}".strip()


def theory_distance(a: dict, b: dict) -> float:
    """Jaccard distance of content vocabulary. 0.0 = identical, 1.0 = disjoint."""
    wa, wb = content_words(theory_text(a)), content_words(theory_text(b))
    union = wa | wb
    if not union:
        return 1.0
    return 1.0 - len(wa & wb) / len(union)


def marginal_diversity(theory: dict, selected: Sequence[dict]) -> float:
    """Distance to the *nearest* already-selected theory (1.0 when none yet).

    This is the max-marginal-relevance / DPP-style niching term: a candidate is
    only "diverse" if it is far from everything already chosen.
    """
    if not selected:
        return 1.0
    return min(theory_distance(theory, s) for s in selected)


def flow_probabilities(rewards: Iterable[float], temperature: float = 1.0) -> list[float]:
    """Softmax over log-reward / temperature.

    temperature == 1  ->  P ∝ R            (the literal GFlowNet property)
    temperature -> 0   ->  mass on argmax  (degenerates to greedy top-k)
    temperature -> inf ->  uniform

    Zero/negative rewards are floored to a small epsilon so the log is finite.
    """
    rewards = list(rewards)
    if not rewards:
        return []
    t = max(float(temperature), 1e-6)
    logs = [math.log(max(float(r), 1e-9)) / t for r in rewards]
    peak = max(logs)
    exps = [math.exp(v - peak) for v in logs]
    total = sum(exps)
    if total <= 0:
        return [1.0 / len(exps)] * len(exps)
    return [e / total for e in exps]


def _weighted_choice(weights: Sequence[float], rng: random.Random) -> int:
    total = sum(weights)
    if total <= 0:
        return rng.randrange(len(weights))
    target = rng.random() * total
    acc = 0.0
    for i, w in enumerate(weights):
        acc += w
        if target <= acc:
            return i
    return len(weights) - 1


def gflownet_select(
    theories: Sequence[dict],
    reward_fn: Callable[[dict], float] | None = None,
    target_size: int | None = None,
    temperature: float = 0.5,
    diversity_weight: float = 0.5,
    seed: int = 0,
) -> list[int]:
    """Sample a population proportional to reward, with sequential niching.

    Returns the selected indices *in selection order* (best flow first). At each
    step a candidate is drawn with probability proportional to
    ``R(x) ** (1 / temperature) * (1 + diversity_weight * marginal_diversity)``,
    where the diversity term is re-evaluated against everything already picked.

    Seeded, therefore reproducible. With ``temperature -> 0`` it degenerates to
    greedy top-k, which makes the proportional behaviour testable against it.
    """
    n = len(theories)
    if n == 0:
        return []
    size = n if target_size is None else max(1, min(int(target_size), n))
    rng = random.Random(seed)

    if reward_fn is None:
        def reward_fn(t):  # type: ignore[misc]
            return float((t.get("scores", {}) or {}).get("overall", 0.0) or 0.0)

    remaining = list(range(n))
    rewards = {i: max(float(reward_fn(theories[i])), 1e-9) for i in remaining}
    t = max(float(temperature), 1e-6)

    def _log_weight(i: int, chosen: Sequence[dict] | None) -> float:
        base = math.log(rewards[i]) / t
        if chosen is None:
            return base
        return base + math.log(
            1.0 + diversity_weight * marginal_diversity(theories[i], chosen))

    selected: list[int] = []
    while len(selected) < size and remaining:
        # Weights are formed in log space and normalised by their max so that
        # low-temperature runs cannot underflow to an all-zero vector (rewards
        # here are <= 1, so R ** (1/T) would collapse to 0).
        chosen = [theories[j] for j in selected] if selected else None
        logs = [_log_weight(i, chosen) for i in remaining]
        peak = max(logs)
        weights = [math.exp(v - peak) for v in logs]
        pos = _weighted_choice(weights, rng)
        selected.append(remaining.pop(pos))
    return selected


def population_diversity(theories: Sequence[dict]) -> dict:
    """Cheap diversity summary of a candidate set (for logging/diagnostics)."""
    n = len(theories)
    if n < 2:
        return {"n": n, "mean_pairwise_distance": 0.0, "min_distance": 0.0,
                "distinct_vocabulary": len(content_words(theory_text(theories[0]))) if n else 0}
    dists = [
        theory_distance(theories[i], theories[j])
        for i in range(n) for j in range(i + 1, n)
    ]
    vocab: set[str] = set()
    for th in theories:
        vocab |= content_words(theory_text(th))
    return {
        "n": n,
        "mean_pairwise_distance": round(sum(dists) / len(dists), 3),
        "min_distance": round(min(dists), 3),
        "distinct_vocabulary": len(vocab),
    }


__all__ = [
    "content_words",
    "theory_text",
    "theory_distance",
    "marginal_diversity",
    "flow_probabilities",
    "gflownet_select",
    "population_diversity",
]
