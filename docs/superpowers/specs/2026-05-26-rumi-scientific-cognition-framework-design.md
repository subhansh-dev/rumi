# RUMI Scientific Cognition Framework

## Objective
Transform RUMI from a literature aggregation system into a modular autonomous scientific cognition framework that generates plausible, testable, novel scientific hypotheses.

## Architecture

### Pipeline Orchestrator (`discovery/pipeline.py`)

```
class Stage:
    name: str
    depends_on: list[str]
    optional: bool
    max_retries: int
    backoff: list[float]

class DiscoveryPipeline:
    stages: dict[str, Stage]
    checkpoints: CheckpointManager
    metrics: MetricsTracker
    context: dict

    async run(topic, domain) -> dict
    async run_from(stage_name) -> dict  # resume from checkpoint
```

Stages:
1. literature_retrieval — PubMed search (existing)
2. entity_extraction — LLM extraction (existing)
3. graph_construction — KnowledgeGraph.build() (existing)
4. contradiction_mining — algorithmic detection (new)
5. latent_discovery — graph link prediction (new)
6. hypothesis_generation — retry chain LLM (new)
7. scientific_reflection — skeptic critique (new)
8. novelty_verification — PubMed comparison (new)
9. experiment_planning — experimental design (new)
10. final_synthesis — report generation (existing)

### Checkpointing
- Per-stage output saved to `discovery/checkpoints/{run_id}/{stage_name}.json`
- Run ID = timestamp + topic slug
- Pipeline resumes from latest checkpoint if re-run within 24h on same topic
- Failed stages: retry 3x, skip if optional, abort if critical

### Retry System
- Unified decorator for LLM calls
- Exponential backoff: 2s, 5s, 15s, 30s
- Provider failover: Groq(3 attempts) → Gemini(2 attempts) → queue
- Queue saves failed calls to `discovery/queue/` for retry later

### Hypothesis Memory (`discovery/hypothesis_memory.py`)
- SQLite: `discovery/hypothesis_memory.db`
- Tables: hypotheses, hypothesis_nodes, hypothesis_edges, novelty_checks
- Cross-session persistence, dedup by title similarity
- Status tracking: draft → verified → rejected → experiment_planned

### Contradiction Miner (`discovery/contradiction_miner.py`)
Algorithmic (not LLM):
1. Direct contradictions — same pair, opposite relations
2. Path contradictions — conflicting downstream effects
3. Paper contradictions — same relation, disagreeing papers
4. Temporal contradictions — entity role changes over time

Output: contradictions list with severity scores.

### Hypothesis Engine (`discovery/hypothesis_engine.py`)
- Builds enhanced prompt from graph + contradictions + latent candidates
- Calls LLM with retry chain (Groq→Gemini→queue)
- Algorithmic confidence scoring (paper count × citation weight × recency × replication)
- Dedup against memory before saving
- Saves to memory + active.json

### Confidence Scorer (`discovery/confidence_scorer.py`)
Evidence-weighted formula:
- `confidence = paper_count_weight × citation_impact × recency_factor × replication_consistency`
- Paper count: logarithmic scaling (log2(n+1)/5, capped at 1.0)
- Citation impact: from Semantic Scholar influence
- Recency: exponential decay over 10yr half-life
- Replication: ratio of supporting papers to contradicting papers

### Novelty Detector (`discovery/novelty_detector.py`)
- Search PubMed for title keywords
- Compare hypothesis entities/relations against existing abstracts
- Similarity via keyword overlap + LLM judgment
- Output: novelty_probability (0-1), similar_papers list

### Skeptic Agent (`discovery/skeptic_agent.py`)
- LLM-based critique of each hypothesis
- Checks: evidence strength, alternative explanations, logical gaps, testability
- Produces: critique text, weaknesses list, revised confidence
- Each hypothesis gets 3 critique rounds

### Experiment Planner (`discovery/experiment_planner.py`)
- For each hypothesis, proposes:
  - Experimental design (controls, variables, endpoints)
  - Predicted outcomes
  - Key biomarkers/measurements
  - Failure mode analysis
- Outputs structured experimental proposal

### Metrics Tracker (`discovery/metrics_tracker.py`)
- Per-stage: latency, token usage, retry count, failure rate
- Per-run: hypotheses count, novelty distribution, avg confidence
- Per-session: cumulative metrics over time
- Output: JSON + console report

## Implementation Phases

### Phase 1 (current)
- pipeline.py (orchestrator + checkpointing + retry)
- hypothesis_memory.py
- contradiction_miner.py
- confidence_scorer.py
- hypothesis_engine.py
- Wire into main.py

### Phase 2
- novelty_detector.py
- skeptic_agent.py
- experiment_planner.py
- metrics_tracker.py

### Phase 3
- mechanistic_reasoner.py
- reflection_loop.py
- Domain-specific cognition modes
- Ablation experiment support
