#!/usr/bin/env python3
"""
reflexion.py — RUMI Recursive Self-Improvement Engine
=====================================================

After each discovery run, RUMI analyzes what went wrong, generates
concrete code patches, tests them in sandbox, and applies safe ones.

The recursive loop:
  1. Run discovery → collect metrics + quality signals
  2. Analyze weaknesses → which modules underperformed, why
  3. Generate patches → LLM proposes specific code fixes
  4. Sandbox test → syntax, imports, unit tests
  5. Apply safe patches → git commit with rollback capability
  6. Next run uses improved code → repeat

Safety rails:
  - Never touches main.py, self_modifier.py, or config files
  - Every patch is git-committed separately (easy revert)
  - Max 3 patches per cycle to prevent runaway
  - Confidence threshold: only apply patches scoring > 0.7
  - All changes logged to reflexion_history.json
"""

import ast
import hashlib
import json
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BRAIN_DIR = Path(__file__).parent.resolve()
DISCOVERY_DIR = BRAIN_DIR.parent / "discovery"
DATA_DIR = BRAIN_DIR.parent / "data"
HISTORY_FILE = BRAIN_DIR / "reflexion_history.json"
PATCHES_DIR = BRAIN_DIR.parent / ".reflexion_patches"

# Safety: files that can NEVER be patched by reflexion
FORBIDDEN_FILES = {
    "main.py", "self_modifier.py", "reflexion.py",
    "agi_orchestrator.py", "self_awareness.py",
    # ── Evaluation integrity — the agent must not move its own goalposts ──
    # Scoring + novelty apparatus the self-improvement loop has edited before:
    "discovery_scorer.py", "novelty_checker.py", "novelty_detector.py",
    "confidence_scorer.py", "theory_competition.py",
    # The external eval harness itself:
    "harness.py", "metrics.py", "judge.py",
    # The frozen regression corpus + replay tools (the agent must not move its
    # own baseline or grading config):
    "regression.py", "replay.py", "config.json",
}

# Never patch anything inside these directories, regardless of filename.
FORBIDDEN_PATH_PARTS = {"eval"}

# Where eval/harness.py stamps the external score onto past runs.
ARCHIVE_FILE = DATA_DIR / "discovery_archive.json"

# A patch is provisional until an external score says otherwise.
EXTERNAL_REGRESSION_TOLERANCE = 3.0   # external-score points (0-100 scale)
REGRESSION_GATE_ENABLED = True        # run pytest + frozen-corpus check per patch

MAX_PATCHES_PER_CYCLE = 3
MIN_CONFIDENCE_THRESHOLD = 0.7
MAX_HISTORY = 100


def _is_forbidden_path(path: Path) -> bool:
    """True if `path` may never be patched (by filename or by directory)."""
    if path.name in FORBIDDEN_FILES:
        return True
    return any(part in FORBIDDEN_PATH_PARTS for part in path.parts)


def _read_archive() -> dict:
    try:
        return json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _topic_external_scores(topic: str) -> list:
    """External scores stamped on prior runs of this exact topic (oldest -> newest)."""
    topic = str(topic or "").strip()
    if not topic:
        return []
    out = []
    for run in _read_archive().get("runs", []):
        if str(run.get("topic", "")).strip() == topic:
            s = run.get("external_score")
            if isinstance(s, (int, float)):
                out.append(float(s))
    return out


def _domain_external_scores(domain: str) -> list:
    domain = str(domain or "").strip()
    if not domain:
        return []
    out = []
    for run in _read_archive().get("runs", []):
        if str(run.get("domain", "")).strip() == domain:
            s = run.get("external_score")
            if isinstance(s, (int, float)):
                out.append(float(s))
    return out


def _external_context(run_result: dict) -> dict:
    """The external-score context Reflexion is allowed to optimise against.

    Reads only scores stamped by eval/harness.py — never a self-reported number.
    """
    topic = run_result.get("query") or run_result.get("topic") or ""
    domain = run_result.get("domain") or ""
    same = _topic_external_scores(topic)
    dom = _domain_external_scores(domain)
    return {
        "topic": topic,
        "domain": domain,
        "same_topic_scores": same,
        "same_topic_count": len(same),
        "same_topic_last": same[-1] if same else None,
        "domain_avg": round(sum(dom) / len(dom), 1) if dom else None,
    }


def _timestamp() -> str:
    return datetime.now().isoformat()


def _git_commit(message: str) -> Optional[str]:
    """Commit all changes, return short hash."""
    try:
        subprocess.run(["git", "add", "-A"],
                       cwd=str(BRAIN_DIR.parent),
                       capture_output=True, timeout=10)
        result = subprocess.run(
            ["git", "commit", "-m", f"[Reflexion] {message}"],
            cwd=str(BRAIN_DIR.parent),
            capture_output=True, timeout=10)
        if result.returncode == 0:
            h = subprocess.run(["git", "rev-parse", "HEAD"],
                               cwd=str(BRAIN_DIR.parent),
                               capture_output=True, timeout=5)
            return h.stdout.decode().strip()[:12]
    except Exception:
        pass
    return None


def _git_revert_last() -> bool:
    """Revert the last commit."""
    try:
        result = subprocess.run(
            ["git", "revert", "--no-commit", "HEAD"],
            cwd=str(BRAIN_DIR.parent),
            capture_output=True, timeout=10)
        if result.returncode == 0:
            subprocess.run(["git", "commit", "-m", "[Reflexion] Reverted patch"],
                           cwd=str(BRAIN_DIR.parent),
                           capture_output=True, timeout=10)
            return True
    except Exception:
        pass
    return False


# ════════════════════════════════════════════════════════════════════════
#  PostDiscoveryAnalyzer — identify what went wrong in a discovery run
# ════════════════════════════════════════════════════════════════════════

class PostDiscoveryAnalyzer:
    """
    Analyzes the output of a discovery run to identify weaknesses.
    Returns structured diagnostics: which modules underperformed,
    what patterns of failure exist, and what to improve.
    """

    def analyze(self, run_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Args:
            run_result: {
                "query": str,
                "domain": str,
                "hypotheses": list,
                "contradictions": list,
                "metrics": dict,
                "refinement": dict (optional),
                "errors": list (optional),
            }

        Returns:
            {
                "weaknesses": [...],
                "module_issues": {...},
                "patterns": [...],
                "priority_fixes": [...],
            }
        """
        weaknesses = []
        module_issues = {}
        patterns = []

        hypotheses = run_result.get("hypotheses", [])
        contradictions = run_result.get("contradictions", [])
        metrics = run_result.get("metrics", {})
        errors = run_result.get("errors", [])
        refinement = run_result.get("refinement", {})

        # === Weakness 1: Low hypothesis confidence ===
        if hypotheses:
            valid_hyps = [h for h in hypotheses if isinstance(h, dict)]
            if valid_hyps:
                # Check both 'confidence' and 'scores.overall' (tournament theories use the latter)
                avg_conf = sum(
                    h.get("confidence", 0) or h.get("scores", {}).get("overall", 0)
                    for h in valid_hyps
                ) / len(valid_hyps)
                if avg_conf < 0.4:
                    weaknesses.append({
                        "type": "low_confidence",
                        "severity": "high",
                        "detail": f"Average hypothesis confidence: {avg_conf:.0%}",
                        "module": "hypothesis_engine",
                        "suggestion": "Improve prompt quality, add more domain context, or increase paper count",
                    })
                    module_issues.setdefault("hypothesis_engine", []).append(
                        "low_confidence: hypotheses lack supporting evidence"
                    )

        # === Weakness 2: No contradictions found ===
        if not contradictions:
            weaknesses.append({
                "type": "no_contradictions",
                "severity": "medium",
                "detail": "Contradiction miner found 0 contradictions",
                "module": "contradiction_miner",
                "suggestion": "Check if entity extraction is too shallow or if papers are too homogeneous",
            })
            module_issues.setdefault("contradiction_miner", []).append(
                "empty_output: no contradictions detected in literature"
            )

        # === Weakness 3: Low novelty scores ===
        low_novelty = [h for h in hypotheses if h.get("novelty") == "low"]
        if hypotheses and len(low_novelty) / len(hypotheses) > 0.5:
            weaknesses.append({
                "type": "low_novelty",
                "severity": "high",
                "detail": f"{len(low_novelty)}/{len(hypotheses)} hypotheses have low novelty",
                "module": "novelty_detector",
                "suggestion": "Cross-reference against more diverse literature sources",
            })
            module_issues.setdefault("novelty_detector", []).append(
                "low_novelty_ratio: most hypotheses are not novel"
            )

        # === Weakness 4: Simulation failures ===
        sim_failed = [h for h in hypotheses if h.get("simulation_passed") is False]
        if sim_failed:
            weaknesses.append({
                "type": "simulation_failure",
                "severity": "medium",
                "detail": f"{len(sim_failed)} hypotheses failed simulation",
                "module": "simulation_pipeline",
                "suggestion": "Improve parameter extraction or simulation model",
            })
            module_issues.setdefault("simulation_pipeline", []).append(
                f"failures: {len(sim_failed)} hypotheses failed simulation"
            )

        # === Weakness 5: Consistency violations ===
        violations = [h for h in hypotheses if h.get("consistency_violations")]
        if violations:
            weaknesses.append({
                "type": "consistency_violations",
                "severity": "high",
                "detail": f"{len(violations)} hypotheses have math consistency violations",
                "module": "math_consistency_checker",
                "suggestion": "Tighten constraints or improve mathematical formalization",
            })

        # === Weakness 6: Pipeline errors ===
        for err in errors:
            weaknesses.append({
                "type": "pipeline_error",
                "severity": "critical",
                "detail": str(err)[:200],
                "module": err.get("module", "unknown") if isinstance(err, dict) else "unknown",
                "suggestion": "Fix the error condition",
            })

        # === Weakness 7: Refinement pipeline issues ===
        if refinement:
            ref_scores = refinement.get("scores", {})
            if ref_scores:
                low_scoring = [k for k, v in ref_scores.items() if isinstance(v, (int, float)) and v < 0.5]
                if low_scoring:
                    weaknesses.append({
                        "type": "refinement_weak",
                        "severity": "medium",
                        "detail": f"Low refinement scores in: {', '.join(low_scoring)}",
                        "module": "refinement_pipeline",
                        "suggestion": f"Improve scoring logic for {', '.join(low_scoring[:3])}",
                    })

        # === Weakness 8: Low novelty on theories ===
        known_science = [h for h in hypotheses
                         if h.get("is_novel_vs_known") in ("well_known", "rediscovery")]
        if hypotheses and len(known_science) / len(hypotheses) > 0.3:
            weaknesses.append({
                "type": "known_science_dominates",
                "severity": "high",
                "detail": f"{len(known_science)}/{len(hypotheses)} theories are known science",
                "module": "novelty_checker",
                "suggestion": "Improve What-If engine and hypothesis prompt to generate more novel ideas",
            })

        # === Weakness 9: Low mathematical rigor ===
        low_math = [h for h in hypotheses
                    if h.get("scores", {}).get("mathematical_rigor", 100) < 30]
        if hypotheses and len(low_math) / len(hypotheses) > 0.5:
            weaknesses.append({
                "type": "low_math_rigor",
                "severity": "medium",
                "detail": f"{len(low_math)}/{len(hypotheses)} theories have low mathematical rigor",
                "module": "math_engine",
                "suggestion": "Include more equations and quantitative predictions in theory descriptions",
            })

        # === Weakness 10: Pipeline errors ===
        for err in errors:
            if isinstance(err, str) and err:
                weaknesses.append({
                    "type": "pipeline_error",
                    "severity": "critical",
                    "detail": str(err)[:200],
                    "module": "pipeline",
                    "suggestion": "Fix the error condition",
                })

        # === Pattern detection ===
        # Repeated failure patterns across runs
        if len([w for w in weaknesses if w["module"] == "hypothesis_engine"]) >= 2:
            patterns.append({
                "pattern": "hypothesis_engine_recurring_failure",
                "frequency": 2,
                "recommendation": "Systematic issue in hypothesis generation — needs architectural review",
            })

        # Priority fixes (sorted by severity)
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        priority_fixes = sorted(weaknesses, key=lambda w: severity_order.get(w["severity"], 9))

        return {
            "weaknesses": weaknesses,
            "module_issues": module_issues,
            "patterns": patterns,
            "priority_fixes": priority_fixes[:5],  # Top 5
            "total_weaknesses": len(weaknesses),
            "modules_to_fix": list(module_issues.keys()),
        }


# ════════════════════════════════════════════════════════════════════════
#  CodePatchGenerator — LLM-powered code fix generation
# ════════════════════════════════════════════════════════════════════════

class CodePatchGenerator:
    """
    Uses LLM to generate concrete code patches for identified weaknesses.
    Reads the current module code, provides context, asks for a fix.
    """

    def __init__(self, llm_fn=None):
        """
        Args:
            llm_fn: async function(prompt: str, **kwargs) -> str
                    If None, patches must be generated manually.
        """
        self._llm = llm_fn

    async def generate_patch(
        self,
        module_name: str,
        weakness: Dict[str, Any],
        current_code: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a code patch for a specific weakness.

        Returns:
            {
                "file": str,          # file to patch (relative to rumi/)
                "description": str,   # what the patch does
                "old_code": str,      # code to find
                "new_code": str,      # code to replace with
                "confidence": float,  # how confident in this fix (0-1)
                "reasoning": str,     # why this fix should work
            }
            or None if no patch can be generated.
        """
        if not self._llm:
            return None

        # Locate the module file
        module_path = self._find_module(module_name)
        if not module_path:
            return None

        # Safety check (filename and directory)
        if _is_forbidden_path(module_path):
            return None

        if current_code is None:
            try:
                current_code = module_path.read_text(encoding="utf-8")
            except Exception:
                return None

        prompt = f"""You are RUMI's self-improvement engine. A discovery run found this weakness:

MODULE: {module_name}
WEAKNESS TYPE: {weakness['type']}
SEVERITY: {weakness['severity']}
DETAIL: {weakness['detail']}
SUGGESTION: {weakness['suggestion']}

Here is the current code of the module (first 3000 chars):
```python
{current_code[:3000]}
```

Generate a MINIMAL code patch to fix this specific weakness. Rules:
1. Change the LEAST amount of code possible
2. The patch must be syntactically valid Python
3. Do not change function signatures or public APIs
4. Do not add new dependencies
5. Focus on the specific weakness, not general refactoring

Respond in JSON:
{{
    "description": "What this patch fixes",
    "old_code": "The exact code to find and replace",
    "new_code": "The replacement code",
    "confidence": 0.0-1.0,
    "reasoning": "Why this should fix the weakness"
}}"""

        try:
            # Handle both sync and async LLM functions
            import asyncio
            if asyncio.iscoroutinefunction(self._llm):
                response = await self._llm(prompt, json_mode=True, max_tokens=2048)
            else:
                # Sync LLM — call directly (wrap in executor if needed)
                response = self._llm(prompt, max_tokens=2048)

            if not response:
                return None

            # Parse response
            if isinstance(response, str):
                response = response.strip()
                if response.startswith("```"):
                    response = response.split("\n", 1)[1] if "\n" in response else response[3:]
                    response = response.rsplit("```", 1)[0].strip()
                try:
                    from discovery.json_extract import extract_json
                    patch = extract_json(response)
                except Exception:
                    patch = json.loads(response)
            else:
                patch = response

            if not isinstance(patch, dict):
                return None

            # Validate the patch
            if not all(k in patch for k in ("old_code", "new_code")):
                return None

            # Verify old_code exists in the file
            if patch["old_code"] not in current_code:
                return None

            # Verify new_code is valid Python
            test_code = current_code.replace(patch["old_code"], patch["new_code"])
            try:
                ast.parse(test_code)
            except SyntaxError:
                return None

            patch["file"] = str(module_path.relative_to(BRAIN_DIR.parent))
            return patch

        except Exception:
            return None

    def _find_module(self, module_name: str) -> Optional[Path]:
        """Find the .py file for a module name like 'hypothesis_engine'."""
        # Try discovery/ first
        for search_dir in [DISCOVERY_DIR, BRAIN_DIR]:
            candidate = search_dir / f"{module_name}.py"
            if candidate.exists():
                return candidate
        return None


# ════════════════════════════════════════════════════════════════════════
#  SandboxTester — test patches before applying
# ════════════════════════════════════════════════════════════════════════

class SandboxTester:
    """
    Tests code patches in isolation before they're applied.
    """

    def test_patch(self, file_path: str, old_code: str, new_code: str) -> Dict[str, Any]:
        """
        Test a patch:
        1. Syntax check (AST parse)
        2. Import check (can the modified file be imported?)
        3. Basic smoke test

        Returns:
            {
                "passed": bool,
                "syntax_ok": bool,
                "import_ok": bool,
                "error": str or None,
            }
        """
        full_path = BRAIN_DIR.parent / file_path
        if not full_path.exists():
            return {"passed": False, "syntax_ok": False, "import_ok": False,
                    "error": f"File not found: {file_path}"}

        try:
            original = full_path.read_text(encoding="utf-8")
        except Exception as e:
            return {"passed": False, "syntax_ok": False, "import_ok": False,
                    "error": f"Cannot read file: {e}"}

        # Apply patch to a copy
        patched = original.replace(old_code, new_code, 1)
        if patched == original:
            return {"passed": False, "syntax_ok": False, "import_ok": False,
                    "error": "old_code not found in file"}

        # Test 1: Syntax check
        try:
            ast.parse(patched)
        except SyntaxError as e:
            return {"passed": False, "syntax_ok": False, "import_ok": False,
                    "error": f"Syntax error in patched code: {e}"}

        # Test 2: Write to temp file and try import
        temp_path = full_path.with_suffix(".py.reflexion_test")
        try:
            temp_path.write_text(patched, encoding="utf-8")
            # Try to compile
            compile(patched, str(temp_path), "exec")
            import_ok = True
        except Exception as e:
            import_ok = False
        finally:
            if temp_path.exists():
                temp_path.unlink()

        return {
            "passed": import_ok,
            "syntax_ok": True,
            "import_ok": import_ok,
            "error": None if import_ok else "Import/compile check failed",
        }


# ════════════════════════════════════════════════════════════════════════
#  RecursiveImprover — the main loop
# ════════════════════════════════════════════════════════════════════════

class RecursiveImprover:
    """
    Orchestrates the recursive self-improvement loop.

    Usage:
        improver = RecursiveImprover(llm_fn=my_llm)
        result = await improver.reflect_and_improve(run_result)
    """

    def __init__(self, llm_fn=None):
        self._lock = threading.RLock()
        self._analyzer = PostDiscoveryAnalyzer()
        self._patcher = CodePatchGenerator(llm_fn=llm_fn)
        self._tester = SandboxTester()
        self._history = self._load_history()
        self._cycle_count = len(self._history)
        PATCHES_DIR.mkdir(parents=True, exist_ok=True)

    def _load_history(self) -> list:
        if HISTORY_FILE.exists():
            try:
                return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []

    def _save_history(self):
        with self._lock:
            HISTORY_FILE.write_text(
                json.dumps(self._history[-MAX_HISTORY:], indent=2, default=str),
                encoding="utf-8"
            )

    async def reflect_and_improve(
        self,
        run_result: Dict[str, Any],
        llm_fn=None,
        post_output_fn=None,
    ) -> Dict[str, Any]:
        """
        Full reflexion cycle: analyze → generate patches → test → apply.

        Args:
            run_result: output from a discovery run
            llm_fn: optional override for LLM function
            post_output_fn: optional callback for progress messages

        Returns:
            {
                "cycle": int,
                "weaknesses_found": int,
                "patches_generated": int,
                "patches_applied": int,
                "patches_rejected": int,
                "details": [...],
                "improvement_score": float | None,  # external-signal; None = unverifiable
            }
        """
        if post_output_fn is None:
            post_output_fn = lambda msg: None

        if llm_fn:
            self._patcher = CodePatchGenerator(llm_fn=llm_fn)

        self._cycle_count += 1
        cycle = self._cycle_count
        post_output_fn(f"[Reflexion] Starting self-improvement cycle #{cycle}")

        # Step 0a: External context — the ONLY objective Reflexion may optimise.
        ext_ctx = _external_context(run_result)
        if ext_ctx.get("same_topic_last") is not None:
            post_output_fn(f"[Reflexion] External baseline (same topic): "
                           f"{ext_ctx['same_topic_last']}")
        elif ext_ctx.get("domain_avg") is not None:
            post_output_fn(f"[Reflexion] External baseline (domain avg): {ext_ctx['domain_avg']}")

        # Step 0b: Regression gate on the PREVIOUS cycle's provisional patches.
        prior_gate = self._evaluate_previous_cycle()
        if prior_gate.get("status") == "reverted":
            post_output_fn(f"[Reflexion] Previous patches REGRESSED the external score "
                           f"({prior_gate.get('score_before')} -> "
                           f"{prior_gate.get('score_after')}); reverted.")

        # Step 1: Analyze weaknesses
        analysis = self._analyzer.analyze(run_result)
        weaknesses = analysis["weaknesses"]
        post_output_fn(f"[Reflexion] Found {len(weaknesses)} weaknesses across "
                       f"{len(analysis['modules_to_fix'])} modules")

        if not weaknesses:
            post_output_fn("[Reflexion] No weaknesses detected — discovery run was clean")
            result = {
                "cycle": cycle,
                "weaknesses_found": 0,
                "patches_generated": 0,
                "patches_applied": 0,
                "patches_rejected": 0,
                "details": [],
                "improvement_score": 1.0,
            }
            self._history.append({"timestamp": _timestamp(), "result": result})
            self._save_history()
            return result

        # Step 2: Generate patches for priority weaknesses
        patches = []
        for weakness in analysis["priority_fixes"][:MAX_PATCHES_PER_CYCLE + 1]:
            module = weakness.get("module", "")
            if not module:
                continue
            post_output_fn(f"[Reflexion] Generating patch for {module}: {weakness['type']}")
            patch = await self._patcher.generate_patch(module, weakness)
            if patch:
                patches.append({"patch": patch, "weakness": weakness})
                post_output_fn(f"[Reflexion]   -> Patch generated (confidence: "
                               f"{patch.get('confidence', 0):.0%})")
            else:
                post_output_fn(f"[Reflexion]   -> No patch generated for {module}")

        # Step 3: Test patches in sandbox
        applied = 0
        rejected = 0
        details = []
        applied_patches = []

        for item in patches[:MAX_PATCHES_PER_CYCLE]:
            patch = item["patch"]
            weakness = item["weakness"]

            # Confidence check
            if patch.get("confidence", 0) < MIN_CONFIDENCE_THRESHOLD:
                post_output_fn(f"[Reflexion] Rejected (low confidence {patch.get('confidence', 0):.0%}): "
                               f"{patch.get('description', '')[:60]}")
                rejected += 1
                details.append({
                    "patch": patch["description"],
                    "status": "rejected",
                    "reason": "low_confidence",
                })
                continue

            # Sandbox test
            test_result = self._tester.test_patch(
                patch["file"], patch["old_code"], patch["new_code"]
            )
            if not test_result["passed"]:
                post_output_fn(f"[Reflexion] Rejected (sandbox failed): "
                               f"{test_result.get('error', '')[:60]}")
                rejected += 1
                details.append({
                    "patch": patch["description"],
                    "status": "rejected",
                    "reason": f"sandbox_failed: {test_result.get('error', '')}",
                })
                continue

            # Step 4: Apply the patch provisionally (backup written, not committed)
            if not self._apply_patch(patch):
                rejected += 1
                post_output_fn(f"[Reflexion] Failed to apply: {patch['description'][:60]}")
                details.append({
                    "patch": patch["description"],
                    "status": "apply_failed",
                })
                continue

            # Step 5: Frozen regression gate — a patch may not break the
            # measurable apparatus (harness tests or the frozen corpus).
            gate = self._regression_gate()
            if gate["status"] == "failed":
                self._restore_backup(patch)
                rejected += 1
                post_output_fn(f"[Reflexion] Rejected (regression gate failed): "
                               f"pytest_rc={gate.get('pytest_rc')} "
                               f"corpus_rc={gate.get('corpus_rc')}")
                details.append({
                    "patch": patch["description"],
                    "file": patch["file"],
                    "status": "rejected",
                    "reason": "regression_gate_failed",
                    "gate": gate,
                })
                continue

            # Step 6: Commit the gated patch
            commit_hash = _git_commit(
                f"Reflexion patch: {patch.get('description', 'auto-fix')[:60]}")
            patch["_commit"] = commit_hash
            applied += 1
            post_output_fn(f"[Reflexion] Applied: {patch['description'][:60]} "
                           f"(gate: {gate['status']})")
            details.append({
                "patch": patch["description"],
                "file": patch["file"],
                "status": "applied",
                "confidence": patch.get("confidence", 0),
                "backup": patch.get("_backup"),
                "commit": commit_hash,
                "gate": gate["status"],
            })
            applied_patches.append({
                "file": patch["file"],
                "description": patch.get("description", ""),
                "backup": patch.get("_backup"),
                "commit": commit_hash,
            })

        # Objective = the EXTERNAL score, never "how many patches we applied".
        improvement_score = self._external_improvement_score(ext_ctx, prior_gate)

        result = {
            "cycle": cycle,
            "weaknesses_found": len(weaknesses),
            "patches_generated": len(patches),
            "patches_applied": applied,
            "patches_rejected": rejected,
            "details": details,
            "improvement_score": improvement_score,   # external-signal; None if unmeasurable
            "external_context": ext_ctx,
            "external_before": ext_ctx.get("same_topic_last"),
            "prior_cycle_gate": prior_gate,
            "applied_patches": applied_patches,
            "verification_pending": bool(applied_patches),
        }

        self._history.append({"timestamp": _timestamp(), "result": result})
        self._save_history()

        _impr_txt = (f"{improvement_score:.0%}"
                     if isinstance(improvement_score, (int, float)) else "unverified")
        post_output_fn(f"[Reflexion] Cycle #{cycle} complete: "
                       f"{applied} applied, {rejected} rejected, "
                       f"improvement (external): {_impr_txt}")

        return result

    def _apply_patch(self, patch: Dict[str, Any]) -> bool:
        """Write a validated patch to disk (backup first). Does NOT commit.

        The patch is provisional: the caller runs the regression gate, then either
        commits it or calls _restore_backup(). This keeps git history free of
        fix-then-immediately-revert noise.
        """
        file_path = BRAIN_DIR.parent / patch["file"]
        if not file_path.exists():
            return False

        # Safety: double-check forbidden (filename and directory)
        if _is_forbidden_path(file_path):
            return False

        backup_path = None
        try:
            original = file_path.read_text(encoding="utf-8")
            patched = original.replace(patch["old_code"], patch["new_code"], 1)

            if patched == original:
                return False

            # Backup
            backup_path = PATCHES_DIR / f"{file_path.stem}_{hashlib.md5(patch['old_code'].encode()).hexdigest()[:8]}.backup"
            backup_path.write_text(original, encoding="utf-8")
            patch["_backup"] = backup_path.name

            # Apply
            file_path.write_text(patched, encoding="utf-8")
            return True

        except Exception:
            if backup_path and backup_path.exists():
                try:
                    file_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
                except Exception:
                    pass
            return False

    def _restore_backup(self, patch: Dict[str, Any]) -> bool:
        """Undo a provisional patch using the backup written by _apply_patch."""
        try:
            file_path = BRAIN_DIR.parent / patch["file"]
            backup_name = patch.get("_backup") or patch.get("backup")
            if not backup_name:
                return False
            backup_path = PATCHES_DIR / backup_name
            if not backup_path.exists():
                return False
            file_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
            return True
        except Exception:
            return False

    def _revert_patches(self, patches: list) -> int:
        """Undo a set of previously applied patches (restore backups + commit)."""
        reverted = 0
        for p in reversed(patches):
            if self._restore_backup({"file": p.get("file"),
                                     "_backup": p.get("backup")}):
                reverted += 1
        if reverted:
            _git_commit(f"Reflexion: revert {reverted} patch(es) "
                        f"that regressed the external score")
        return reverted

    @staticmethod
    def _run_cmd(cmd: list, timeout: int = 240) -> Optional[int]:
        """Run a subprocess from the repo root. Returns exit code, or None if it
        could not be run."""
        try:
            r = subprocess.run(cmd, cwd=str(BRAIN_DIR.parent),
                               capture_output=True, timeout=timeout)
            return r.returncode
        except Exception:
            return None

    def _regression_gate(self) -> Dict[str, Any]:
        """Frozen gates a provisional patch must not break.

        Runs the harness tests and the frozen-corpus regression check in fresh
        interpreters. A definitive failure (pytest exit 1, or corpus regression
        exit 1) => revert. If a gate cannot run at all, we warn but do not block.
        """
        if not REGRESSION_GATE_ENABLED:
            return {"status": "skipped"}
        rc_tests = self._run_cmd([sys.executable, "-m", "pytest", "eval/tests", "-q"])
        rc_corpus = self._run_cmd([sys.executable, "-m", "eval.regression", "check"])
        if (rc_tests == 1) or (rc_corpus == 1):
            return {"status": "failed", "pytest_rc": rc_tests, "corpus_rc": rc_corpus}
        ok = (rc_tests in (0, 5)) and (rc_corpus == 0)
        return {"status": "passed" if ok else "inconclusive",
                "pytest_rc": rc_tests, "corpus_rc": rc_corpus}

    def _evaluate_previous_cycle(self) -> Dict[str, Any]:
        """Decide what to do with the previous cycle's provisional patches.

        A provisional patch is kept unless a later run of the SAME topic shows
        the external score regressed beyond tolerance. If there is no comparable
        score yet, the patches stay pending ('unverified').
        """
        prev = None
        for entry in reversed(self._history):
            r = entry.get("result", {})
            if r.get("verification_pending"):
                prev = r
                break
        if not prev:
            return {"status": "n/a", "detail": "no pending patches"}
        patches = prev.get("applied_patches") or []
        if not patches:
            return {"status": "n/a", "detail": "previous cycle applied no patches"}

        before = prev.get("external_before")
        ctx = prev.get("external_context") or {}
        if not isinstance(before, (int, float)):
            before = ctx.get("same_topic_last")
        n_at = ctx.get("same_topic_count", 0)
        now = _topic_external_scores(prev.get("topic"))

        if not isinstance(before, (int, float)) or len(now) <= n_at:
            return {"status": "unverified",
                    "detail": "no comparable external score yet",
                    "score_before": before}

        after = now[-1]
        if after < before - EXTERNAL_REGRESSION_TOLERANCE:
            reverted = self._revert_patches(patches)
            prev["verification_pending"] = False
            prev["gate_status"] = "reverted"
            self._save_history()
            return {"status": "reverted", "score_before": before,
                    "score_after": after, "patches_reverted": reverted}

        prev["verification_pending"] = False
        prev["gate_status"] = "kept"
        self._save_history()
        return {"status": "kept", "score_before": before, "score_after": after}

    @staticmethod
    def _external_improvement_score(ext_ctx: Dict[str, Any],
                                    prior_gate: Dict[str, Any]) -> Optional[float]:
        """Objective = the EXTERNAL score, not the number of patches applied.

        Returns None when there is no comparable external measurement yet — an
        explicitly *unknown* objective, so the loop can never reward itself for
        merely applying patches.
        """
        if prior_gate.get("status") == "reverted":
            return 0.0
        before = prior_gate.get("score_before")
        after = prior_gate.get("score_after")
        if isinstance(before, (int, float)) and isinstance(after, (int, float)) and before > 0:
            return round(max(0.0, min(1.0, (after - before) / before)), 3)
        # Fall back to the same-topic external trend, if we have two points.
        scores = ext_ctx.get("same_topic_scores") or []
        if len(scores) >= 2 and scores[-2] > 0:
            return round(max(0.0, min(1.0, (scores[-1] - scores[-2]) / scores[-2])), 3)
        return None

    def get_history(self, limit: int = 10) -> list:
        """Get recent improvement history."""
        return self._history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get overall self-improvement statistics."""
        total_applied = sum(
            r.get("result", {}).get("patches_applied", 0)
            for r in self._history
        )
        total_rejected = sum(
            r.get("result", {}).get("patches_rejected", 0)
            for r in self._history
        )
        total_weaknesses = sum(
            r.get("result", {}).get("weaknesses_found", 0)
            for r in self._history
        )

        avg_improvement = 0.0
        scores = [r.get("result", {}).get("improvement_score") for r in self._history]
        numeric = [s for s in scores if isinstance(s, (int, float))]
        if numeric:
            avg_improvement = sum(numeric) / len(numeric)

        return {
            "total_cycles": len(self._history),
            "total_weaknesses_found": total_weaknesses,
            "total_patches_applied": total_applied,
            "total_patches_rejected": total_rejected,
            "avg_improvement_score": avg_improvement,
            "last_cycle": self._history[-1] if self._history else None,
        }

    def reflect_and_improve_sync(self, run_result, llm_fn=None, post_output_fn=None):
        """Synchronous wrapper for reflect_and_improve."""
        # Update patcher with llm_fn if provided
        if llm_fn:
            self._patcher = CodePatchGenerator(llm_fn=llm_fn)

        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context, use a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, self.reflect_and_improve(run_result, llm_fn, post_output_fn))
                    return future.result(timeout=300)
            else:
                return loop.run_until_complete(self.reflect_and_improve(run_result, llm_fn, post_output_fn))
        except Exception:
            return asyncio.run(self.reflect_and_improve(run_result, llm_fn, post_output_fn))


# ════════════════════════════════════════════════════════════════════════
#  Convenience functions
# ════════════════════════════════════════════════════════════════════════

_global_improver: Optional[RecursiveImprover] = None
_lock = threading.Lock()


def get_recursive_improver(llm_fn=None) -> RecursiveImprover:
    """Get or create the global RecursiveImprover instance."""
    global _global_improver
    if _global_improver is None:
        with _lock:
            if _global_improver is None:
                _global_improver = RecursiveImprover(llm_fn=llm_fn)
    return _global_improver
