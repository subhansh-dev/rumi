"""Pipeline orchestrator with stage-based execution, checkpointing, retry."""

import asyncio
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"
QUEUE_DIR = Path(__file__).resolve().parent / "queue"


class Stage:
    def __init__(self, name, description="", depends_on=None, optional=False,
                 max_retries=3, backoff=None, critical=True):
        self.name = name
        self.description = description
        self.depends_on = depends_on or []
        self.optional = optional
        self.max_retries = max_retries
        self.backoff = backoff or [2, 5, 15, 30]
        self.critical = critical

    async def execute(self, context):
        raise NotImplementedError

    def __repr__(self):
        return f"Stage({self.name})"


class LLMStage(Stage):
    def __init__(self, name, description="", depends_on=None, optional=False,
                 max_retries=3, backoff=None, critical=True, providers=None):
        super().__init__(name, description, depends_on, optional, max_retries, backoff, critical)
        self.providers = providers or ["groq", "gemini"]

    async def call_llm(self, prompt, json_mode=False, max_tokens=32768, provider="groq"):
        from discovery.llm_client import call as llm_call
        return llm_call(prompt, json_mode=json_mode, max_tokens=max_tokens,
                        provider=provider)

    async def call_with_retry(self, prompt, json_mode=False, max_tokens=32768):
        last_error = None
        for attempt in range(self.max_retries):
            provider_idx = 0 if attempt < 2 else 1
            if provider_idx >= len(self.providers):
                provider_idx = len(self.providers) - 1
            provider = self.providers[provider_idx]
            try:
                result = await self.call_llm(prompt, json_mode, max_tokens, provider)
                if result and len(result) > 20:
                    return result, provider
                last_error = f"Empty/too short response from {provider}"
            except Exception as e:
                last_error = f"{type(e).__name__} from {provider}: {e}"
            delay = self.backoff[min(attempt, len(self.backoff) - 1)]
            await asyncio.sleep(delay)

        # Queue for later
        queue_path = QUEUE_DIR / f"{int(time.time())}_{self.name}.json"
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        queue_path.write_text(json.dumps({
            "prompt": prompt, "json_mode": json_mode, "max_tokens": max_tokens,
            "stage": self.name, "error": str(last_error), "time": time.time()
        }), encoding="utf-8")

        return None, f"queued (last error: {last_error})"


class CheckpointManager:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir or CHECKPOINT_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _run_dir(self, run_id):
        d = self.base_dir / run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def exists(self, run_id, stage_name):
        return (self.base_dir / run_id / f"{stage_name}.json").exists()

    def save(self, run_id, stage_name, data):
        path = self._run_dir(run_id) / f"{stage_name}.json"
        path.write_text(json.dumps({"data": data, "timestamp": time.time()}, indent=2, default=str), encoding="utf-8")

    def load(self, run_id, stage_name):
        path = self.base_dir / run_id / f"{stage_name}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8")).get("data")

    def latest_run_id(self, topic, max_age_hours=24):
        prefix = self._topic_prefix(topic)
        candidates = sorted(self.base_dir.glob(f"{prefix}_*"), reverse=True)
        for d in candidates:
            if not d.is_dir():
                continue
            cutoff = time.time() - (max_age_hours * 3600)
            if d.stat().st_mtime > cutoff:
                return d.name
        return None

    @staticmethod
    def _topic_prefix(topic):
        return hashlib.md5(topic.encode()).hexdigest()[:8]


class DiscoveryPipeline:
    def __init__(self, stages=None, run_id=None):
        self.stages: dict[str, Stage] = {}
        self.checkpoints = CheckpointManager()
        self.context = {}
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.metrics = {}
        if stages:
            for s in stages:
                self.add_stage(s)

    def add_stage(self, stage):
        self.stages[stage.name] = stage

    async def run(self, topic, domain, resume=False):
        self.context["topic"] = topic
        self.context["domain"] = domain

        if resume:
            existing = self.checkpoints.latest_run_id(topic)
            if existing:
                self.run_id = existing

        results = {}
        for stage_name, stage in self.stages.items():
            start = time.time()

            # Check dependencies
            missing_deps = [d for d in stage.depends_on if d not in results]
            if missing_deps:
                if stage.optional:
                    continue
                raise RuntimeError(f"Stage {stage_name} missing dependencies: {missing_deps}")

            # Check checkpoint
            if self.checkpoints.exists(self.run_id, stage_name):
                data = self.checkpoints.load(self.run_id, stage_name)
                results[stage_name] = data
                self.context[stage_name] = data
                self._log(f"[checkpoint] Loaded {stage_name}")
                self._record_metric(stage_name, "checkpoint_loaded", True, time.time() - start)
                continue

            # Execute with retry
            data = None
            last_error = None
            for attempt in range(stage.max_retries):
                try:
                    data = await stage.execute(self.context)
                    if data is not None:
                        break
                    last_error = "Stage returned None"
                except Exception as e:
                    last_error = f"{type(e).__name__}: {e}"
                delay = stage.backoff[min(attempt, len(stage.backoff) - 1)]
                self._log(f"[retry] {stage_name} attempt {attempt+1} failed ({last_error}), waiting {delay}s")
                await asyncio.sleep(delay)

            if data is None:
                if stage.optional or not stage.critical:
                    self._log(f"[skip] {stage_name} failed — skipping (optional)")
                    self._record_metric(stage_name, "skipped", True, time.time() - start)
                    continue
                raise RuntimeError(f"Critical stage {stage_name} failed: {last_error}")

            # Save checkpoint
            self.checkpoints.save(self.run_id, stage_name, data)
            results[stage_name] = data
            self.context[stage_name] = data
            self._record_metric(stage_name, "completed", False, time.time() - start)

        return results

    async def run_from(self, stage_name, topic, domain):
        self.context["topic"] = topic
        self.context["domain"] = domain

        # Load prior checkpoints
        for s in self.stages:
            if self.checkpoints.exists(self.run_id, s):
                self.context[s] = self.checkpoints.load(self.run_id, s)

        # Find starting index
        names = list(self.stages.keys())
        if stage_name not in names:
            raise ValueError(f"Unknown stage: {stage_name}")
        idx = names.index(stage_name)

        # Run from there
        remaining = {n: self.stages[n] for n in names[idx:]}
        pipeline = DiscoveryPipeline(list(remaining.values()), run_id=self.run_id)
        return await pipeline.run(topic, domain, resume=False)

    def _log(self, msg):
        from discovery.output import post_output
        try:
            post_output(f"[pipeline] {msg}")
        except Exception:
            print(f"  [pipeline] {msg}")

    def _record_metric(self, stage, status, skipped, elapsed):
        self.metrics.setdefault(stage, []).append({
            "status": status, "skipped": skipped, "elapsed_s": round(elapsed, 2),
            "time": time.time()
        })

    def metrics_report(self):
        lines = ["\nPipeline Metrics:", "-" * 40]
        for stage, entries in self.metrics.items():
            for e in entries:
                status = "✓" if e["status"] == "completed" else "⏭" if e["skipped"] else "✗"
                lines.append(f"  {status} {stage}: {e['elapsed_s']:.1f}s")
        return "\n".join(lines)


# --- Retry decorator for standalone usage ---
def retryable(max_retries=3, backoff=None, provider_failover=True):
    backoff = backoff or [2, 5, 15]
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last = e
                    delay = backoff[min(attempt, len(backoff) - 1)]
                    await asyncio.sleep(delay)
            raise last
        return wrapper
    return decorator
