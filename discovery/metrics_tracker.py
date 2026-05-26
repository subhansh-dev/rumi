"""Metrics tracking for the discovery pipeline."""

import json
import time
from pathlib import Path
from collections import defaultdict

METRICS_DIR = Path(__file__).resolve().parent / "metrics"


class MetricsTracker:
    def __init__(self):
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        self.run_metrics = defaultdict(list)
        self.run_start = time.time()

    def record(self, stage, status, elapsed_s, metadata=None):
        self.run_metrics[stage].append({
            "status": status,
            "elapsed_s": round(elapsed_s, 2),
            "timestamp": time.time(),
            "metadata": metadata or {},
        })

    def summary(self):
        lines = ["\nDiscovery Metrics:", "─" * 40]
        total_elapsed = time.time() - self.run_start
        for stage, entries in self.run_metrics.items():
            for e in entries:
                icon = "✓" if e["status"] == "ok" else "⏭" if "skip" in str(e["status"]) else "✗"
                lines.append(f"  {icon} {stage}: {e['elapsed_s']:.1f}s")
        lines.append(f"\n  Total: {total_elapsed:.1f}s")

        # Compute aggregate
        completed = sum(1 for v in self.run_metrics.values() for e in v if e["status"] == "ok")
        failed = sum(1 for v in self.run_metrics.values() for e in v if e["status"] != "ok")
        if completed + failed > 0:
            pct = completed / (completed + failed) * 100
            lines.append(f"  Success rate: {pct:.0f}% ({completed}/{completed + failed})")

        return "\n".join(lines)

    def save(self, run_id):
        path = METRICS_DIR / f"{run_id}.json"
        path.write_text(json.dumps({
            "run_id": run_id,
            "elapsed_s": round(time.time() - self.run_start, 1),
            "stages": {k: v for k, v in self.run_metrics.items()},
        }, indent=2, default=str), encoding="utf-8")

    def hypothesis_stats(self, hypotheses):
        if not hypotheses:
            return {"count": 0, "avg_confidence": 0, "novelty_distribution": {}}
        confidences = [h.get("confidence", 0) for h in hypotheses if isinstance(h, dict)]
        novelty_dist = defaultdict(int)
        for h in hypotheses:
            if isinstance(h, dict):
                novelty_dist[h.get("novelty", "unknown")] += 1
        return {
            "count": len(hypotheses),
            "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
            "novelty_distribution": dict(novelty_dist),
        }
