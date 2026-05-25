# TOOLS.md — Capabilities Reference

_Complete reference of RUMI's cognitive systems, action tools, skills, agents, and diagnostics._

---

## Cognitive Systems

### Memory Systems

| System | Module | Type | Purpose |
|--------|--------|------|---------|
| Neural Memory | `brain.neural_memory.py` | Persistent (JSON) | Long-term facts with Hebbian learning, 72-hour synaptic decay, pattern completion |
| Episodic Memory | `brain.episodic_memory.py` | Persistent (JSONL) | Timestamped events with importance scoring, searchable history |
| Vector Memory | `brain.vector_memory.py` | Persistent (JSON) | Semantic search via embeddings for fuzzy recall across all stores |
| Procedural Memory | `brain.procedural_memory.py` | Persistent (JSON) | Reusable skill templates — successful tool chains with goal matching |
| Working Memory | `skills/working_memory.py` | In-memory | Active task context (8 slots, Miller's Law), transient |
| Associative Memory | `brain.associative_memory.py` | Persistent (JSON) | Spreading activation networks for context-dependent recall |
| Predictive Memory | `brain.predictive_memory.py` | Persistent (JSON) | Anticipatory recall — pre-loads relevant memories based on context |
| Memory Consolidation | `brain.memory_consolidation.py` | Process | Sleep-like compression: episodic → semantic, redundancy removal |
| Memory Coordinator | `brain.memory_coordinator.py` | Orchestrator | Unified recall across all memory stores with cross-store search |
| Global Workspace | `brain.global_workspace.py` | In-memory | Thalamus-inspired multi-module coordination and broadcast |

### Learning & Adaptation

| System | Module | Purpose |
|--------|--------|---------|
| Active Inference | `brain.active_inference.py` | Free Energy Principle — minimizes prediction error via Bayesian updating |
| Hierarchical AIF | `brain.hierarchical_active_inference.py` | 3-level temporal abstraction (meta → subgoal → action) with precision weighting |
| Curiosity Engine | `brain.curiosity.py` | Novelty detection, information-seeking behavior, exploration queue |
| Dreaming System | `brain.dreaming.py` | Offline experience replay, pattern extraction, memory consolidation |
| Learning Engine | `brain.learning.py` | Error-driven updates, Q-learning for tool selection, user feedback integration |
| Meta-Learner | `brain.meta_learner.py` | Learning to learn — extracts transferable strategies across tasks |
| Transfer Learning | `brain.transfer_learning.py` | Cross-domain pattern transfer with domain-specific abstraction |
| Self-Improve Engine | `brain.self_improve_engine.py` | RLHF-inspired: action-outcome pairs, improvement velocity, failure lessons |
| Code Evolution | `brain.code_evolution.py` | Safe recursive self-improvement: performance analysis, proposals, sandbox testing, rollback |
| Experience Replay | `skills/experience_replay.py` | Past experience review for pattern extraction and learning |
| Decision Journal | `skills/decision_journal.py` | Structured decision logging with reasoning, alternatives, and outcomes |

### Reasoning Systems

| System | Module | Purpose |
|--------|--------|---------|
| Causal Reasoner | `brain.causal_reasoner.py` | Pearl's Causal Hierarchy: association → intervention → counterfactual |
| Analogy Engine | `brain.analogy_engine.py` | Gentner's Structure Mapping Theory — cross-domain structural analogies |
| Neurosymbolic Reasoner | `brain.neurosymbolic_reasoner.py` | Neural LLM + SymPy formal logic: mathematical invariant verification |
| Narrative Intelligence | `brain.narrative_intelligence.py` | Story construction, causal narrative chains, identity evolution |
| Creativity Engine | `brain.creativity_engine.py` | Conceptual blending, constraint relaxation, bisociation for novel ideas |
| Intuition Engine | `brain.intuition_engine.py` | System 1 fast-path: Recognition-Primed Decision Making (Klein) |
| Abstraction Engine | `brain.abstraction_engine.py` | First principles reasoning, hierarchical concept formation, emergent insight |
| Cognitive Integration | `brain.cognitive_integration.py` | Unified pipeline wiring all reasoning modules with complexity-based routing |
| Module Competition | `brain.module_competition.py` | Minsky Society of Mind — modules bid for processing rights based on relevance |

### Consciousness & Self

| System | Module | Purpose |
|--------|--------|---------|
| Self-Awareness | `brain.self_awareness.py` | Consciousness state tracking, emotional state, cognitive event detection |
| Self-Model | `brain.self_model.py` | Capability inventory, confidence calibration, growth tracking across sessions |
| Theory of Mind | `brain.theory_of_mind.py` | User expertise modeling, intent inference, emotional state, adaptive communication |
| Metacognitive Monitor | `brain.metacognitive_monitor.py` | Thinking quality (5 dimensions), calibration tracking, error pattern detection |
| Introspection Engine | `brain.introspection_engine.py` | Confidence calibration, 12 bias types, epistemic humility, narrative self-model |
| Emotional Regulation | `brain/emotional_regulation.py` | Somatic Marker Hypothesis — emotions as decision-pruning signals |
| Integrated Information | `brain.integrated_info.py` | IIT-inspired Φ (phi) — consciousness metric, module connectivity tracking |
| Self-Modifier | `brain.self_modifier.py` | Safe self-code-audit: snapshot, analyze, propose, validate changes |
| Self-Narrative | `brain.narrative_intelligence.py` | Evolving story of identity, growth, and experience |

### Planning & Autonomy

| System | Module | Purpose |
|--------|--------|---------|
| Autonomous Planner | `brain.autonomous_planner.py` | MCTS-inspired plan decomposition with dependency tracking and replanning |
| Goal Engine | `brain.goal_engine.py` | Hierarchical management: life → project → task → subgoal with priority scoring |
| Intrinsic Motivation | `brain.intrinsic_motivation.py` | Self-Determination Theory: autonomy, competence, relatedness drives, flow detection |
| Proactive Engine | `brain.proactive_engine.py` | Anticipates needs, tiered idle check-ins, returning-user greetings |
| Cognitive Load Manager | `brain.cognitive_load.py` | Working memory monitoring (7±2), overload detection, load-shedding |
| AGI Orchestrator | `brain.agi_orchestrator.py` | Master coordinator wiring all modules into unified cognitive loop |
| Multi-Agent Orchestrator | `brain.multi_agent_orchestrator.py` | Parallel/debate/pipeline/voting/specialist/swarm agent execution modes |

### Code Intelligence

| System | Module | Purpose |
|--------|--------|---------|
| Code Intelligence | `brain.code_intelligence.py` | Semantic codebase graph (AST + deps), chunk memory for pattern recognition |
| Code Planner | `brain.code_planner.py` | Hierarchical EFE-based planning with mental simulation |
| Code Simulator | `brain.code_simulator.py` | Predictive execution — simulates code before running, anomaly detection |
| Code Reflector | `brain.code_reflector.py` | Root-cause analysis with hypothesis ranking, failure pattern learning |
| Cognitive Coder | `actions/cognitive_coder.py` | Master orchestrator: build/analyze/plan/simulate/debug/refactor/review/explain |

### World Models

| System | Module | Purpose |
|--------|--------|---------|
| World Model | `brain.world_model.py` | DreamerV3-inspired latent dynamics for outcome prediction |
| Enhanced World Model | `brain.enhanced_world_model.py` | Non-linear MLP transitions, ensemble prediction (linear+nonlinear+causal) |
| World Simulation | `brain.world_simulation.py` | Real-time event tracking, trend detection, counterfactual modeling |
| Findings Bus | `brain.findings_bus.py` | Inter-module communication bus for discoveries and insights |

---

## Scientist AI (15 Modules)

| Module | File | Purpose |
|--------|------|---------|
| Discovery Engine | `scientist/discovery_engine.py` | End-to-end pipeline: idea → novelty check → experiment → paper → review → iterate |
| Tournament Hypotheses | `scientist/tournament_hypothesis.py` | GFlowNet-inspired diverse generation with evolutionary tournament selection |
| Knowledge Graph | `scientist/knowledge_graph.py` | Structured knowledge with multi-hop reasoning, gap detection, paper ingestion |
| Reproducibility Engine | `scientist/reproducibility_engine.py` | Extract testable claims, generate reproduction code, sandbox execution, score reproducibility |
| Active Experiment Selector | `scientist/active_experiment_selector.py` | Bayesian optimal experiment selection maximizing information gain, adaptive stopping |
| Cross-Domain Connector | `scientist/cross_domain_connector.py` | 8-domain analogy engine: physics, biology, CS, economics, chemistry, math, neuroscience, ecology |
| Lab Notebook | `scientist/lab_notebook.py` | Digital experiment tracking: create entries, observations, measurements, status lifecycle |
| Novelty Checker | `scientist/novelty_checker.py` | Semantic Scholar + arXiv-based novelty assessment against existing literature |
| Experiment Designer | `scientist/experiment_designer.py` | Design controlled experiments with hypothesis testing, generate experiment code |
| Paper Generator | `scientist/paper_generator.py` | Structured manuscript generation with methods, results, discussion sections |
| Peer Reviewer | `scientist/peer_reviewer.py` | Automated peer review with methodological critique, quality scoring |
| Feynman Reducer | `scientist/feynman_reducer.py` | First-principles decomposition — explain complex ideas in simple terms |
| Cross-Validator | `scientist/cross_validator.py` | Statistical validation, reproducibility checks, baseline comparison |
| Research Team | `scientist/research_team.py` | 5-role multi-agent debate: Lead, Methodologist, Critic, Analyst, Scribe |
| Scientist Search | `scientist/scientist_search.py` | Paper search by researcher or topic with citation analysis across arXiv + Semantic Scholar |

---

## Action Tools

### Scientist & Research

| Tool | Description |
|------|-------------|
| `scientist_discovery` | Full discovery pipeline: run, quick, full, history, stats |
| `scientist_analyze` | Novelty check, Feynman decomposition, peer review, cross-validation |
| `scientist_experiment` | Design, run, analyze experiments. Hypothesis testing, domain selection |
| `scientist_paper` | Generate academic papers and research reports |
| `scientist_team` | 5-role multi-agent research team collaboration and debate |
| `scientist_tournament` | GFlowNet hypothesis generation with evolutionary tournament selection |
| `scientist_knowledge_graph` | Build and query scientific knowledge graphs, detect gaps, ingest papers |
| `scientist_reproducibility` | Extract claims, reproduce results, sandbox execution, scoring |
| `scientist_experiment_selector` | Bayesian optimal experiment selection and ranking |
| `scientist_cross_domain` | Cross-domain analogies and hypothesis transfer between scientific fields |
| `scientist_lab_notebook` | Digital lab notebook for experiment tracking |
| `scientist_search` | Search papers by researcher with citation analysis |
| `paper_search` | Search academic papers from arXiv and Semantic Scholar |
| `hypothesis_manage` | CRUD for research hypotheses with status lifecycle |

### Web & Search

| Tool | Description |
|------|-------------|
| `web_search` | Quick web search for factual answers, current events, simple lookups |
| `web_research` | Deep multi-source research with full page scraping (30s+) |
| `deep_dive` | In-depth web research with report generation |
| `browser_control` | Full browser automation: navigate, click, type, scroll, fill forms, screenshot |
| `youtube_video` | Search, play, summarize YouTube videos, get info, check trending |

### Code & Development

| Tool | Description |
|------|-------------|
| `cognitive_code` | Full cognitive coding pipeline: build, analyze, plan, simulate, debug, refactor, review, explain |
| `code_helper` | Simple code write, edit, run, build, explain |
| `dev_agent` | Multi-file project generation from natural language descriptions |
| `agency_agent` | 30+ specialized expert agent personas for any domain |
| `multi_agent` | Run multiple agents in parallel, debate, pipeline, voting, specialist, or swarm mode |
| `agent_task` | Advanced async multi-step task management |

### System Control

| Tool | Description |
|------|-------------|
| `open_app` | Launch any application on the computer |
| `computer_control` | Mouse, keyboard, hotkeys, scroll, screenshot, type automation |
| `computer_settings` | Volume, brightness, WiFi, power management, window control |
| `desktop_control` | Wallpaper, organize files, clean desktop, system stats |
| `file_controller` | Full file system: list, create, delete, move, copy, rename, read, write, search |
| `screen_process` | Screen capture and vision analysis (camera or display) |

### Communication

| Tool | Description |
|------|-------------|
| `send_message` | Send messages via WhatsApp, Telegram, or other platforms |
| `reminder` | Set timed reminders using Task Scheduler |
| `telegram_bridge` | Two-way Telegram communication channel |

### AI Processing

| Tool | Description |
|------|-------------|
| `ai_pipeline` | Text processing: summarize, translate, sentiment analysis, entity extraction, document processing |
| `data_analysis` | CSV/JSON data analysis with Polars: analyze, query, chart |
| `weather_report` | Current weather conditions and forecast |

### Memory & Learning

| Tool | Description |
|------|-------------|
| `brain_memory` | Search, recall, store memories across all memory systems |
| `save_memory` | Silently save personal facts about user to long-term memory |
| `memory_stats` | Unified memory system health statistics |
| `procedural_memory` | Learn and retrieve reusable skill templates |
| `record_learning` | Record deliberate insights and lessons learned |
| `reflect_learning` | Run metacognitive reflection session |
| `get_learnings` | Retrieve all recorded learnings |

### Cognitive Diagnostics

| Tool | Description |
|------|-------------|
| `cognitive_status` | View working memory, decision journal, replay stats, strategy scores |
| `consciousness_state` | Full consciousness state: emotions, user model, patterns, narrative |
| `cognitive_reason` | Multi-module reasoning: analogy + causal + creativity + narrative |
| `analogy_reason` | Gentner's Structure Mapping analogical reasoning between domains |
| `causal_analyze` | Pearl's Causal Hierarchy cause-effect analysis |
| `creative_solve` | Computational creativity: conceptual blending for novel solutions |
| `intuition_check` | System 1 fast pattern matching (Recognition-Primed Decisions) |
| `meta_reflect` | Metacognitive reflection on strategies, patterns, and calibration |
| `decision_review` | Query the decision journal for past reasoning |
| `consciousness_check` | IIT-inspired integrated information metrics (phi) |
| `cognitive_load_check` | Check working memory usage and task complexity |

### Autonomy & System

| Tool | Description |
|------|-------------|
| `agi_status` | AGI orchestrator health, system IQ proxy, module stats |
| `self_model_status` | Capabilities, confidence scores, growth tracking |
| `curiosity_queue` | Check curiosity exploration queue |
| `run_dream_cycle` | Trigger immediate dream/replay cycle |
| `force_learning` | Force active inference learning cycle |
| `self_audit` | Self-modification audit: code health, complexity, improvement suggestions |
| `self_narrative` | Read or add to identity story |
| `proactive_suggest` | Get proactive suggestions based on learned patterns |
| `integration_status` | Report available advanced Python modules |
| `api_server` | Start/stop RUMI REST API server |
| `cognitive_code` (status) | Cognitive coding engine system status |

### Utilities

| Tool | Description |
|------|-------------|
| `system_sentinel` | Monitor CPU, RAM, disk health |
| `neural_clipboard` | Monitor clipboard and retrieve history |
| `auto_doc` | Auto-generate project documentation |
| `gesture_music` | Hand gesture-controlled music system |
| `music_control` | Media playback control (play, pause, skip, volume) |
| `security_tools` | Cybersecurity tool suite (requires cyber_enabled) |
| `ac_control` | Air conditioner control (IR/WiFi) |
| `shutdown_rumi` | Graceful shutdown with memory save |

---

## Skills Engine

| Skill | Description |
|-------|-------------|
| `research_agent` | Knowledge-graph-powered autonomous research with entity extraction, claim tracking, contradiction detection |
| `document_intelligence` | Document analysis: contract review, argument mapping, fallacy detection, bias detection, reading level |
| `deep_dive` | Structured in-depth research with multi-source synthesis and report generation |
| `cognitive_gating` | Automatic complexity assessment: routes tasks to System 1 or System 2 |
| `working_memory` | Active task context management (8-slot transient memory) |
| `meta_reflect` | Meta-level reflection on strategies, patterns, and calibration |
| `decision_journal` | Structured decision logging with reasoning and outcomes |
| `experience_replay` | Past experience review for pattern extraction and learning |
| `adaptive_planner` | Dynamic task planning and strategy optimization |
| `auto_doc` | Automatic project documentation generation |
| `neural_clipboard` | Cross-session context transfer via clipboard monitoring |
| `sentinel` | Background system monitoring and alerting |

---

## Expert Agent Personas (30+)

Available via `agency_agent` action tool:

### Engineering
Senior Developer, Software Architect, Frontend Developer, Backend Architect, SRE, DevOps Automator, Security Engineer, Database Optimizer, Code Reviewer, Git Workflow Master, Incident Response Commander, Technical Writer, AI Engineer, Data Engineer, Rapid Prototyper, Codebase Onboarding Engineer, Threat Detection Engineer

### Design
UI Designer, UX Architect

### Testing
API Tester, Accessibility Auditor, Performance Benchmarker, Workflow Optimizer, Test Results Analyzer

### Specialized
Compliance Auditor, Document Generator, Workflow Architect

---

## Security Layer

| Component | Purpose |
|-----------|---------|
| Permission Manager | 3-tier risk system (LOW/MEDIUM/HIGH) for tool access control |
| Audit Logger | Full audit trail for all tool operations with parameter redaction |
| Tools Guard | Rate limiting, SSRF checks, tool call validation |
| Input Sanitizer | Input validation and sanitization |
| Config Validator | API key and configuration validation |
| Lock State | System lock state management |
| Fallback Mode | Permissive mode when security module is unavailable |
| Target Guard | Production safety checks for external operations |
