"""
theory_competition.py — Tournament-style theory competition.

Real science is hypothesis SELECTION, not hypothesis generation.
Generate many, force them to compete, eliminate weak ones, keep survivors.

Tournament structure:
  Round 1: Generate 20 candidates (10 LLM + 10 algorithmic variants)
  Round 2: Score all 20, eliminate bottom 10
  Round 3: Cross-compare top 10, eliminate bottom 5
  Final:   Top 5 survivors with detailed head-to-head analysis

Inspired by:
  - Thagard's Explanatory Coherence theory
  - Bayesian model comparison (Bayes factors)
  - Minimum Description Length (MDL)
  - Lipton's Inference to the Best Explanation (IBE)
  - GFlowNet-style hypothesis diversification
"""

import json
import math
import random
from typing import List, Dict, Optional


class TheoryCompetition:
    """
    Tournament-style theory competition. Generate many, kill weak, keep survivors.
    """

    def __init__(self, graph=None, llm_call=None):
        self.graph = graph
        self.llm_call = llm_call

    def compete(self, mechanisms: list, hidden_variables: list,
                anomalies: list, gaps: list, topic: str, domain: str,
                papers: list = None, archive_context: str = "") -> dict:
        """
        Run multi-round tournament competition.

        Returns:
            {
                "theories": [...all survivors with scores...],
                "eliminated": [...theories that were killed...],
                "winner": {...},
                "tournament_log": [...round-by-round results...],
                "competition_analysis": "...",
                "discriminating_experiments": [...]
            }
        """
        if not self.llm_call:
            return {"theories": [], "winner": None, "error": "No LLM client"}

        # Format inputs
        mech_list = mechanisms[:5] if isinstance(mechanisms, list) else mechanisms.get("mechanisms", [])[:5]
        hv_list = hidden_variables[:5] if isinstance(hidden_variables, list) else hidden_variables.get("hidden_variables", [])[:5]

        mech_text = self._format_list(mech_list, "mechanism")
        hv_text = self._format_list(hv_list, "hidden variable")
        anomaly_text = self._format_list(anomalies[:6] if anomalies else [], "anomaly")
        gap_text = self._format_list(gaps[:6] if gaps else [], "gap")
        paper_text = self._format_papers(papers[:8] if papers else [])

        tournament_log = []
        eliminated = []

        # ═══════════════════════════════════════════════════════
        # ROUND 1: Generate 20 candidates
        # ═══════════════════════════════════════════════════════
        print("  [Round 1] Generating 20 theory candidates...", flush=True)
        all_theories = []

        # LLM batch 1: 10 theories
        batch1 = self._generate_theories(
            mech_text, hv_text, anomaly_text, gap_text, paper_text,
            topic, domain, count=10, batch_label="LLM batch",
            archive_context=archive_context
        )
        all_theories.extend(batch1)

        # LLM batch 2: 10 more with different framing
        batch2 = self._generate_theories(
            mech_text, hv_text, anomaly_text, gap_text, paper_text,
            topic, domain, count=10, batch_label="creative batch",
            creative=True, archive_context=archive_context
        )
        all_theories.extend(batch2)

        # Deduplicate by name
        seen_names = set()
        unique_theories = []
        for t in all_theories:
            name = t.get("name", "").lower().strip()
            if name and name not in seen_names:
                seen_names.add(name)
                unique_theories.append(t)
        all_theories = unique_theories

        print(f"  [Round 1] {len(all_theories)} unique candidates generated", flush=True)
        tournament_log.append({
            "round": 1,
            "action": "generation",
            "candidates": len(all_theories),
        })

        if len(all_theories) < 3:
            # Not enough theories — return what we have
            return self._finalize(all_theories, [], tournament_log)

        # ═══════════════════════════════════════════════════════
        # ROUND 2: Score all, eliminate bottom half
        # ═══════════════════════════════════════════════════════
        print(f"  [Round 2] Scoring {len(all_theories)} candidates...", flush=True)
        self._score_all(all_theories, anomalies, gaps, papers)

        # Sort by overall score
        all_theories.sort(key=lambda t: t.get("scores", {}).get("overall", 0), reverse=True)

        # Eliminate bottom half
        cutoff = max(5, len(all_theories) // 2)
        survivors_r2 = all_theories[:cutoff]
        killed_r2 = all_theories[cutoff:]

        for t in killed_r2:
            t["eliminated_in_round"] = 2
            t["elimination_reason"] = f"Score {t.get('scores', {}).get('overall', 0):.2f} — bottom half"
            eliminated.append(t)

        tournament_log.append({
            "round": 2,
            "action": "elimination",
            "survived": len(survivors_r2),
            "eliminated": len(killed_r2),
            "cutoff_score": survivors_r2[-1].get("scores", {}).get("overall", 0) if survivors_r2 else 0,
        })
        print(f"  [Round 2] {len(survivors_r2)} survived, {len(killed_r2)} eliminated", flush=True)

        # ═══════════════════════════════════════════════════════
        # ROUND 3: Cross-compare survivors, eliminate more
        # ═══════════════════════════════════════════════════════
        if len(survivors_r2) > 5:
            print(f"  [Round 3] Cross-comparing {len(survivors_r2)} survivors...", flush=True)
            cross_results = self._cross_compare(survivors_r2, topic, domain)

            # Apply cross-comparison adjustments
            for t in survivors_r2:
                name = t.get("name", "")
                cross = cross_results.get(name, {})
                if cross:
                    # Adjust scores based on head-to-head
                    win_rate = cross.get("win_rate", 0.5)
                    current = t.get("scores", {}).get("overall", 0.5)
                    adjusted = current * 0.7 + win_rate * 0.3
                    t["scores"]["overall"] = round(adjusted, 3)
                    t["cross_comparison"] = cross

            # Re-sort and eliminate bottom
            survivors_r2.sort(key=lambda t: t.get("scores", {}).get("overall", 0), reverse=True)
            survivors_r3 = survivors_r2[:max(5, len(survivors_r2) * 2 // 3)]
            killed_r3 = survivors_r2[len(survivors_r3):]

            for t in killed_r3:
                t["eliminated_in_round"] = 3
                t["elimination_reason"] = f"Lost head-to-head — win rate {t.get('cross_comparison', {}).get('win_rate', 0):.0%}"
                eliminated.append(t)

            tournament_log.append({
                "round": 3,
                "action": "cross_comparison_elimination",
                "survived": len(survivors_r3),
                "eliminated": len(killed_r3),
            })
            print(f"  [Round 3] {len(survivors_r3)} survived, {len(killed_r3)} eliminated", flush=True)
        else:
            survivors_r3 = survivors_r2

        # ═══════════════════════════════════════════════════════
        # FINAL: Top survivors
        # ═══════════════════════════════════════════════════════
        survivors_r3.sort(key=lambda t: t.get("scores", {}).get("overall", 0), reverse=True)
        final = survivors_r3[:7]  # Keep top 7

        # Generate discriminating experiments
        experiments = []
        if len(final) >= 2:
            experiments = self._generate_discriminating_experiments(
                final[0], final[1], topic, domain
            )

        # Competition analysis
        analysis = self._generate_analysis(final, eliminated, topic, domain)

        tournament_log.append({
            "round": "final",
            "action": "survivors",
            "count": len(final),
            "winner": final[0].get("name", "?") if final else None,
            "winner_score": final[0].get("scores", {}).get("overall", 0) if final else 0,
        })

        return self._finalize(final, eliminated, tournament_log, experiments, analysis)

    def _generate_theories(self, mech_text, hv_text, anomaly_text, gap_text,
                           paper_text, topic, domain, count=10,
                           batch_label="batch", creative=False,
                           archive_context="") -> list:
        """Generate a batch of theories via LLM."""
        creative_instruction = ""
        if creative:
            creative_instruction = """
Be CREATIVE. Generate theories from DIFFERENT domains:
- An explanation from biology applied to physics
- An explanation from economics applied to astronomy
- An explanation from information theory applied to chemistry
- A completely unexpected angle nobody would think of
- A theory that combines two unrelated fields
The most important discoveries come from unexpected connections."""

        prompt = f"""You are generating competing scientific theories for a tournament.
The TOP {count // 2} will survive. The rest will be eliminated. Make every theory count.

TOPIC: {topic}
DOMAIN: {domain}

OBSERVATIONS TO EXPLAIN:
{anomaly_text}

KNOWLEDGE GAPS:
{gap_text}

PROPOSED MECHANISMS (from prior pipeline stages):
{mech_text}

PROPOSED HIDDEN VARIABLES:
{hv_text}

RELEVANT PAPERS:
{paper_text}

{archive_context}

Generate EXACTLY {count} COMPETING THEORIES. Each must explain the same observations
but through DIFFERENT mechanisms. Include:
- Conventional explanations (no new physics needed)
- Extensions of known mechanisms
- Novel mechanisms from the proposed hidden variables
- Cross-domain explanations
- Null hypothesis (everything is noise/artifacts)
{creative_instruction}

For each theory provide:
1. name: Short descriptive name
2. description: One paragraph explanation
3. type: proposed|alternative|conventional|null|creative
4. mechanism: HOW it explains the observations (specific pathway)
5. hidden_variables: Any new entities/processes it requires
6. explains: Which observations it explains
7. fails_to_explain: Which observations it CANNOT explain (be honest)
8. predictions: Specific testable predictions with numbers
9. key_assumptions: What it assumes (fewer = better)
10. key_parameters: Parameters with values and source (cited|derived|estimated)

Output JSON: {{"theories": [{{...}}, ...]}}

Generate ALL {count} theories. Quality AND quantity. This is a tournament — only the strong survive."""

        try:
            raw = self.llm_call(prompt, max_tokens=8192)
            if not raw:
                from discovery.llm_client import call_json
                raw = call_json(prompt, max_tokens=8192, provider="auto")

            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = json.loads(raw)
                else:
                    result = raw

                if isinstance(result, dict):
                    theories = result.get("theories", [])
                    # Ensure defaults
                    for t in theories:
                        t.setdefault("name", "Unnamed Theory")
                        t.setdefault("type", "alternative")
                        t.setdefault("scores", {})
                        t.setdefault("explains", [])
                        t.setdefault("fails_to_explain", [])
                        t.setdefault("predictions", [])
                        t.setdefault("key_assumptions", [])
                    return theories[:count]

        except Exception as e:
            print(f"    [WARN] {batch_label} failed: {e}", flush=True)

        return []

    def _score_all(self, theories: list, anomalies: list, gaps: list, papers: list):
        """Score all theories on 7 dimensions."""
        WEIGHTS = {
            "explanatory_power": 0.20,
            "predictive_power": 0.20,
            "falsifiability": 0.15,
            "evidence_support": 0.15,
            "novelty": 0.10,
            "simplicity": 0.10,
            "coherence": 0.10,
        }

        observations = []
        if anomalies:
            for a in anomalies:
                if isinstance(a, dict):
                    observations.append(a.get("reason", a.get("description", "")))
        if gaps:
            for g in gaps:
                if isinstance(g, dict):
                    observations.append(g.get("reason", g.get("description", "")))

        for theory in theories:
            # Use LLM scores if available, otherwise compute
            scores = theory.get("scores", {})

            # Recompute overall with our weights
            weighted = sum(
                scores.get(dim, 0.5) * weight
                for dim, weight in WEIGHTS.items()
            )

            # Apply causal status bonus/penalty (no more penalty for correlations)
            causal_status = theory.get("causal_status", "")
            if causal_status in ("causal_pathway", "counterfactual"):
                weighted += 0.05  # bonus for causal claims

            scores["overall"] = round(min(1.0, max(0.0, weighted)), 3)
            theory["scores"] = scores

    def _cross_compare(self, theories: list, topic: str, domain: str) -> dict:
        """Head-to-head elimination ranking.

        Instead of scoring theories independently (which is unreliable), we compare
        them in direct matchups: A vs B, one pair at a time. The theory that wins
        more matchups is stronger — regardless of what independent scores say.

        For N theories, we generate N*(N-1)/2 matchups and compute win rates.
        """
        if len(theories) < 2:
            return {}

        n = len(theories[:10])  # cap at 10
        pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append((i, j))

        # Batch pairs into groups of 5 to save tokens
        batch_size = 5
        wins = [0] * n
        total_games = [0] * n

        for batch_start in range(0, len(pairs), batch_size):
            batch = pairs[batch_start:batch_start + batch_size]

            pair_text = ""
            for idx, (i, j) in enumerate(batch):
                ti = theories[i]
                tj = theories[j]
                pair_text += f"""
Pair {idx+1}: "{ti.get('name', '?')}" vs "{tj.get('name', '?')}"
  A: {ti.get('description', '')[:120]}
  A explains: {', '.join(str(e)[:40] for e in ti.get('explains', [])[:2])}
  B: {tj.get('description', '')[:120]}
  B explains: {', '.join(str(e)[:40] for e in tj.get('explains', [])[:2])}
"""

            prompt = f"""You are a scientific judge. For each pair below, decide which
theory BETTER explains the observations for: {topic} ({domain})

{pair_text}

For each pair, choose A or B. Consider:
- Which explains more observations?
- Which has stronger evidence?
- Which makes more testable predictions?
- Which has fewer unsupported assumptions?

Output JSON: {{"results": [{{"pair": 1, "winner": "A|B", "reason": "brief reason"}}, ...]}}"""

            try:
                raw = self.llm_call(prompt, max_tokens=1024)
                if not raw:
                    continue

                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = json.loads(raw)
                else:
                    result = raw

                if isinstance(result, dict):
                    for r in result.get("results", []):
                        pair_idx = r.get("pair", 1) - 1
                        winner = r.get("winner", "A")
                        if pair_idx < len(batch):
                            i, j = batch[pair_idx]
                            total_games[i] += 1
                            total_games[j] += 1
                            if winner == "A":
                                wins[i] += 1
                            else:
                                wins[j] += 1
            except Exception:
                continue

        # Compute elimination scores (win rate from head-to-head matchups)
        results = {}
        for i in range(n):
            name = theories[i].get("name", f"Theory {i}")
            total = total_games[i]
            if total > 0:
                win_rate = wins[i] / total
            else:
                win_rate = 0.5  # no data → neutral

            results[name] = {
                "name": name,
                "win_count": wins[i],
                "total_comparisons": total_games[i],
                "win_rate": round(win_rate, 3),
                "elimination_score": round(win_rate, 3),
            }

        return results

    def _generate_discriminating_experiments(self, theory1, theory2, topic, domain):
        """Generate experiments that would distinguish between top 2 theories."""
        prompt = f"""Two theories compete to explain: {topic} ({domain})

THEORY 1: {theory1.get('name', '?')}
  {theory1.get('description', '')[:200]}
  Predictions: {theory1.get('predictions', [])[:2]}

THEORY 2: {theory2.get('name', '?')}
  {theory2.get('description', '')[:200]}
  Predictions: {theory2.get('predictions', [])[:2]}

Design 2-3 experiments that would DEFINITIVELY distinguish between these theories.
Each experiment must:
1. Have a different predicted outcome for each theory
2. Be practically feasible
3. Have a clear success/failure criterion

Output JSON: {{"experiments": ["experiment 1 description", "experiment 2 description"]}}"""

        try:
            raw = self.llm_call(prompt, max_tokens=2048)
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = json.loads(raw)
                else:
                    result = raw
                if isinstance(result, dict):
                    return result.get("experiments", [])
        except Exception:
            pass
        return []

    def _generate_analysis(self, survivors, eliminated, topic, domain):
        """Generate competition analysis summary."""
        if not survivors:
            return "No theories survived."

        winner = survivors[0]
        winner_score = winner.get("scores", {}).get("overall", 0)

        analysis = f"Winner: {winner.get('name', '?')} (score: {winner_score:.2f}). "
        analysis += f"{len(survivors)} theories survived the tournament. "
        analysis += f"{len(eliminated)} were eliminated. "

        if len(survivors) > 1:
            runner_up = survivors[1]
            runner_score = runner_up.get("scores", {}).get("overall", 0)
            gap = winner_score - runner_score
            if gap < 0.05:
                analysis += f"Close competition — runner-up {runner_up.get('name', '?')} is within {gap:.2f}. "
            else:
                analysis += f"Clear winner — gap to runner-up is {gap:.2f}. "

        return analysis

    def _finalize(self, survivors, eliminated, tournament_log,
                  experiments=None, analysis=None):
        """Build final result dict."""
        survivors.sort(key=lambda t: t.get("scores", {}).get("overall", 0), reverse=True)
        winner = survivors[0] if survivors else None

        return {
            "theories": survivors,
            "theories_compared": len(survivors) + len(eliminated),
            "eliminated": eliminated,
            "winner": winner,
            "winner_name": winner.get("name") if winner else None,
            "winner_score": winner.get("scores", {}).get("overall", 0) if winner else 0,
            "tournament_log": tournament_log,
            "competition_analysis": analysis or "",
            "discriminating_experiments": experiments or [],
        }

    def _format_list(self, items: list, item_type: str) -> str:
        if not items:
            return f"No {item_type}s available."
        text = ""
        for i, item in enumerate(items, 1):
            if isinstance(item, dict):
                name = item.get("name", item.get("observation", item.get("reason", "?")))
                desc = item.get("description", item.get("mechanism", ""))[:200]
                text += f"\n{i}. {name}\n   {desc}\n"
            else:
                text += f"\n{i}. {str(item)[:200]}\n"
        return text

    def _format_papers(self, papers: list) -> str:
        if not papers:
            return "No papers available."
        text = ""
        for p in papers[:6]:
            if isinstance(p, dict):
                title = p.get("title", "?")
                abstract = p.get("abstract", "")[:150]
                text += f"\n- [{title}] {abstract}\n"
        return text

    # Keep backward compatibility
    def score_theory(self, theory: dict, observations: list,
                     alternatives: list = None) -> dict:
        """Score a single theory (legacy method)."""
        explains = theory.get("explains", [])
        fails = theory.get("fails_to_explain", [])
        predictions = theory.get("predictions", [])
        assumptions = theory.get("key_assumptions", [])

        total_obs = len(observations) if observations else max(1, len(explains) + len(fails))
        explanatory = len(explains) / total_obs if total_obs > 0 else 0.5
        predictive = min(1.0, len(predictions) * 0.2)
        simplicity = max(0.1, 1.0 - len(assumptions) * 0.15)
        contradiction_penalty = len(fails) * 0.05

        return {
            "explanatory_power": round(explanatory, 3),
            "predictive_power": round(predictive, 3),
            "simplicity": round(simplicity, 3),
            "contradiction_penalty": round(contradiction_penalty, 3),
        }
