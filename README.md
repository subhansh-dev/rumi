# RUMI — Research & Unified Machine Intelligence

<p align="center">
  <img src="assets/rumi.png" alt="RUMI Logo" width="400" />
</p>

<p align="center">
  <a href="https://github.com/subhansh-dev/Rumi/stargazers">
    <img src="https://img.shields.io/github/stars/subhansh-dev/Rumi?style=flat" alt="Stars" />
  </a>
  <a href="https://github.com/subhansh-dev/Rumi/forks">
    <img src="https://img.shields.io/github/forks/subhansh-dev/Rumi?style=flat" alt="Forks" />
  </a>
  <a href="https://github.com/subhansh-dev/Rumi/issues">
    <img src="https://img.shields.io/github/issues/subhansh-dev/Rumi" alt="Issues" />
  </a>
  <a href="https://github.com/subhansh-dev/Rumi/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/subhansh-dev/Rumi" alt="License" />
  </a>
  <a href="https://python.org/versions/3.11">
    <img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python" />
  </a>
</p>

<p align="center">
  <b>Autonomous Scientific Cognition Framework</b><br>
  Terminal-native. 44 Brain Modules. 48 Discovery Modules. 17 Domains. Recursive Self-Improvement.
</p>

<p align="center">
  <img src="assets/dashboard.png" alt="RUMI Discovery Dashboard" width="900" />
</p>

---

## Table of Contents

- [About](#about)
- [Discovery Pipeline v2](#discovery-pipeline-v2)
- [Cognitive Architecture](#cognitive-architecture)
- [Brain Systems](#brain-systems)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Telegram Integration](#telegram-integration)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## About

**RUMI** is a terminal-native autonomous scientific cognition framework. It doesn't just search and summarize — it generates novel, testable, evidence-grounded hypotheses through a 12-phase discovery pipeline backed by a 44-module cognitive architecture.

| Dimension | RUMI |
|-----------|------|
| **Interface** | Terminal-native (Rich + prompt_toolkit) |
| **Models** | Gemini 2.5 Flash + Groq (Llama 3.3 70B), multi-model routing with token-aware rate limiting |
| **Architecture** | 44 brain modules + 48 discovery modules |
| **Pipeline** | Literature → Knowledge Graph → Gap Detection → Anomaly Detection → Hidden Variables → Mechanisms → Predictions → Theory Competition → Computational Verification → Contradictions → Skeptic Review → Discovery Scoring |
| **Memory** | 9-type system: neural, episodic, vector, procedural, working, associative, predictive, consolidated, global workspace |
| **Learning** | Active inference, curiosity-driven exploration, dreaming (offline replay), meta-learning, recursive self-improvement |
| **Reasoning** | Causal (Pearl's hierarchy), analogical (Gentner's structure mapping), neurosymbolic, first-principles |
| **Cognition** | Dual-process (System 1 fast / System 2 deliberate), integrated information (IIT-phi), metacognition |

### Why RUMI Exists

| Dimension | Conventional Assistants | RUMI |
|-----------|------------------------|-------|
| **Memory** | Stateless per session | 9-type persistent memory with Hebbian learning |
| **Initiative** | Reactive | Proactive — curiosity-driven, autonomous research |
| **Reasoning** | Single-pass generation | Multi-pass: causal, analogical, neurosymbolic, first-principles |
| **Self-awareness** | None | Self-model, introspection, metacognitive monitoring |
| **Learning** | No feedback loop | Error-driven updates, dreaming, recursive self-improvement |
| **Discovery** | Search-and-summarize | 12-phase pipeline: gaps → anomalies → hidden variables → mechanisms → predictions → competition → scoring |

---

## Discovery Pipeline v2

RUMI's discovery engine is not a research assistant. It's a discovery engine. The v2 pipeline runs 12 phases, each with algorithmic fallbacks:

```
Phase 1:  Literature        arXiv + PubMed + Semantic Scholar (multi-query)
Phase 2:  Knowledge Graph   Algorithmic + LLM entity extraction, relationship building
Phase 3:  Gap Detection     Structural holes, orphan observations, missing mechanisms
Phase 4:  Anomaly Detection Conflicting evidence, outliers, prediction violations
Phase 5:  Hidden Variables  Propose unseen entities/processes (dark matter style)
Phase 6:  Mechanisms        Causal pathways, not just correlations
Phase 7:  Predictions       Testable predictions with falsification criteria
Phase 8:  Theory Competition Multiple competing explanations, scored on 7 dimensions
Phase 9:  Computational     Real graph analysis, Monte Carlo, statistics
Phase 10: Contradictions    Algorithmic graph analysis
Phase 11: Skeptic Review    Adversarial critique
Phase 12: Discovery Scoring Novelty, explanatory power, falsifiability (0-100)
```

After the 12-phase pipeline:
- **Refinement Pipeline** (13 stages): knowledge audit, first-principles tracing, mathematical formalization, derivation engine, multi-model competition, adversarial scientists, causal reasoning, uncertainty decomposition, prediction generation, simulation, discovery classification, researcher-grade scoring, self-critique
- **Reflexion** (recursive self-improvement): analyzes weaknesses, generates code patches, tests in sandbox, applies safe fixes — every run makes RUMI better

### 17 Supported Domains

| Domain | Key | Enrichment APIs |
|--------|-----|-----------------|
| Drug Discovery | `drug_discovery` | PubChem + OpenFDA + PDB |
| Materials Science | `materials_science` | PubChem + Materials Project |
| Neuroscience | `neuroscience` | UniProt + PDB |
| Molecular Biology | `molecular_biology` | UniProt + PDB |
| Climate & Energy | `climate_energy` | NASA POWER |
| Space & Astronomy | `space_astronomy` | NASA API + arXiv |
| Computer Science | `computer_science` | GitHub |
| Earth Science | `earth_science` | USGS |
| Oceanography | `oceanography` | NOAA |
| Economics | `economics` | World Bank |
| Public Health | `public_health` | WHO |
| Mathematics | `mathematics` | OEIS + arXiv |
| Social Sciences | `social_science` | OpenAlex |
| Chemistry | `chemistry` | CIR + PubChem |
| Ecology | `ecology` | GBIF |
| Physics | `physics` | arXiv |
| General Science | `general` | Semantic Scholar |

Auto-detect: `/discover black hole dark matter` → physics  
Manual: `/discover drug_discovery: KRAS G12C inhibitor resistance`

### What's New in v2 vs v1

| Dimension | v1 | v2 |
|-----------|----|----|
| Gap Detection | None | Structural holes, orphan observations |
| Anomaly Detection | None | Conflicting evidence, outliers |
| Hidden Variables | None | Proposes unseen entities/processes |
| Mechanisms | Correlations | Causal pathways with steps |
| Predictions | None | Testable with falsification criteria |
| Theory Competition | Single hypothesis | Multiple competing, scored |
| Computational Verification | "Computations run: 0" | Real graph analysis, Monte Carlo |
| Discovery Scoring | Basic confidence | 6-dimension scoring (0-100) |
| Recursive Self-Improvement | None | Reflexion: auto-patches weak modules |

### Key Discovery Modules

| Module | Purpose |
|--------|---------|
| `knowledge_gap_detector` | Find structural holes, orphan observations, missing mechanisms |
| `anomaly_detector` | Find conflicting evidence, outliers, prediction violations |
| `missing_variable_generator` | Propose hidden variables (dark matter style reasoning) |
| `mechanism_generator` | Generate causal pathways, not just correlations |
| `prediction_engine` | Generate testable predictions with falsification criteria |
| `theory_competition` | Compare multiple explanations, score on 7 dimensions |
| `discovery_scorer` | Final quality gate: novelty, explanatory power, falsifiability |
| `computational_verification` | Real computations: graph analysis, Monte Carlo, statistics |
| `domain_ontologies` | Real physics for 17 domains: equations, mechanisms, constraints |
| `math_consistency_checker` | Verify theories: equation parsing, parameter ranges, unit checking |
| `simulation_pipeline` | Monte Carlo testing: 1000 runs, confidence intervals |
| `multi_agent_debate` | 4-role debate: Proposer, Critic, Advocate, Synthesizer |
| `cross_domain_transfer` | 7 built-in analogies + LLM-powered new analogy discovery |
| `continuous_operation` | Autonomous loop: curiosity-driven topic selection |
| `refinement_pipeline` | 13-stage post-processing: audit → formalization → scoring |
| `falsification_engine` | Try to destroy theories: constraints, counterfactuals, adversarial |
| `claim_provenance` | Trace every claim back to its source paper |
| `link_predictor` | Predict missing connections in the knowledge graph |

---

## Cognitive Architecture

RUMI routes inputs through a layered pipeline inspired by dual-process theory and cognitive neuroscience:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PERCEPTION LAYER                              │
│     Voice Input ──► Text ──► Gemini Live API ──► Audio Out           │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────┐
│                         MEMORY LAYER                                 │
│  ┌──────────┐ ┌───────────┐ ┌──────────┐ ┌───────────────────┐      │
│  │  Neural  │ │  Episodic │ │  Vector  │ │    Procedural     │      │
│  │ (Hebbian)│ │  (Events) │ │ (Search) │ │  (Skill Memory)   │      │
│  └──────────┘ └───────────┘ └──────────┘ └───────────────────┘      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │           Memory Coordinator (unified recall)                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────┐
│                       INFERENCE LAYER                                │
│  Active Inference ──► Prediction-Error Minimization (FEP)            │
│  Curiosity Engine ──► Novelty Detection ──► Exploration Drive        │
│  Cognitive Gating ──► System 1 (fast) vs System 2 (deliberate)      │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────┐
│                       REASONING LAYER                                │
│  Causal (Pearl) ──► Analogy (Gentner) ──► Neurosymbolic               │
│  Narrative ──► Creativity ──► Intuition (Recognition-Primed)         │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────┐
│                      REFLECTION LAYER                                │
│  Dreaming ──► Experience Replay ──► Pattern Extraction               │
│  Meta-Reflection ──► Decision Journal ──► Strategy Scoring           │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────┐
│                      IDENTITY LAYER                                  │
│  Self-Model ──► Self-Awareness ──► Consciousness (IIT-Φ)             │
│  Theory of Mind ──► Emotional Regulation ──► Metacognitive Monitor   │
│  Global Workspace (Thalamus) ──► Multi-Module Coordination           │
└───────────────────────────────────┬──────────────────────────────────┘
                                    │
┌───────────────────────────────────▼──────────────────────────────────┐
│                      ACTION LAYER                                    │
│  40+ Tool Actions ──► Execution ──► Verification ──► Learning        │
└──────────────────────────────────────────────────────────────────────┘
```

### Research Foundations

| Research Area | Researcher(s) | Core Idea |
|--------------|---------------|-----------|
| Global Workspace Theory | Bernard Baars (1988) | Consciousness as a broadcast mechanism |
| Integrated Information Theory | Giulio Tononi (2004) | Consciousness as integrated information (Φ) |
| Free Energy Principle | Karl Friston (2010) | All adaptive systems minimize prediction error |
| Dual Process Theory | Daniel Kahneman (2011) | System 1 (fast) vs System 2 (slow) reasoning |
| Recognition-Primed Decisions | Gary Klein (1998) | Experts decide by pattern matching |
| Structure Mapping Theory | Dedre Gentner (1983) | Analogical reasoning as core intelligence |
| Causal Hierarchy | Judea Pearl (2018) | Association → Intervention → Counterfactual |
| Society of Mind | Marvin Minsky (1986) | Intelligence as emergent competition between agents |
| Metacognition | John Flavell (1979) | Thinking about thinking |
| Computational Creativity | Margaret Boden (2004) | Exploration, combination, transformation |
| World Models | Ha & Schmidhuber (2018) | Mental simulation before action |

---

## Brain Systems

### Memory (8 modules)

| Module | Purpose |
|--------|---------|
| Neural Memory | Long-term facts, Hebbian learning, synaptic decay |
| Episodic Memory | Timestamped events with importance scoring |
| Vector Memory | Semantic search via embeddings |
| Procedural Memory | Learns successful tool chains as reusable skills |
| Associative Memory | Spreading activation networks |
| Predictive Memory | Anticipatory recall — pre-loads relevant memories |
| Memory Consolidation | Sleep-like compression of episodic → semantic |
| Memory Coordinator | Unified recall across all memory stores |

### Learning & Adaptation (7 modules)

| Module | Purpose |
|--------|---------|
| Active Inference | Free Energy Principle — minimizes prediction error |
| Learning Engine | Error-driven updates, Q-learning for tool selection |
| Curiosity Engine | Information-seeking, novelty detection, exploration |
| Dreaming System | Offline experience replay, pattern extraction |
| Meta-Learner | Learning to learn — transferable strategies |
| Transfer Learning | Cross-domain pattern transfer |
| Self-Improve Engine | RLHF-inspired: action-outcome pairs, lessons from failures |

### Reasoning (8 modules)

| Module | Purpose |
|--------|---------|
| Causal Reasoner | Pearl's Causal Hierarchy |
| Analogy Engine | Gentner's Structure Mapping Theory |
| Neurosymbolic Reasoner | LLM reasoning + SymPy formal logic verification |
| Narrative Intelligence | Turns experiences into stories |
| Creativity Engine | Conceptual blending, constraint relaxation, bisociation |
| Intuition Engine | Fast pattern matching — Recognition-Primed Decisions |
| Cognitive Integration | Orchestrates all reasoning into unified pipeline |
| Module Competition | Minsky Society of Mind — modules bid for processing |

### Consciousness & Self-Awareness (10 modules)

| Module | Purpose |
|--------|---------|
| Self-Awareness | Consciousness state tracking, emotional state |
| Self-Model | Capability awareness, confidence calibration |
| Theory of Mind | User expertise modeling, intent inference |
| Metacognitive Monitor | Thinking quality tracking, calibration |
| Introspection Engine | Confidence calibration, bias detection (12 types) |
| Integrated Information | Φ (phi) approximation (Tononi's IIT) |
| Self-Narrative | Evolving story of identity and growth |
| Global Workspace | Thalamus-inspired multi-module coordination |
| Workspace Context | Context injection for situational awareness |
| Workspace Events | Inter-module event communication |

### Planning & Autonomy (8 modules)

| Module | Purpose |
|--------|---------|
| Autonomous Planner | MCTS-inspired plan decomposition |
| Goal Engine | Hierarchical goals: life → project → tasks |
| Intrinsic Motivation | Self-Determination Theory: autonomy, competence, relatedness |
| Hierarchical Active Inference | 3-level FEP: Meta → Subgoal → Action |
| Proactive Engine | Anticipates needs, idle check-ins |
| Cognitive Load Manager | Working memory monitoring (7±2 slots) |
| AGI Orchestrator | Master coordinator for all cognitive modules |
| Multi-Agent Orchestrator | Parallel, debate, pipeline, voting, swarm modes |

### Scientific Reasoning & World Models (6 modules)

| Module | Purpose |
|--------|---------|
| Scientific Reasoning | Multi-pass scientific reasoning cycle |
| Discovery Orchestrator | Coordinates discovery across brain modules |
| Theory Formation | Bengio-inspired theory engine |
| World Model | DreamerV3-inspired latent dynamics |
| Enhanced World Model | Non-linear MLP transitions, ensemble prediction |
| Abstraction Engine | First principles, cross-domain transfer |

---

## Installation

### Prerequisites

| Requirement | Details |
|-------------|---------|
| Python | 3.11+ ([download](https://python.org/downloads)) |
| Git | Any recent version |
| OS | Windows (primary), Linux/macOS (partial) |
| RAM | 4GB+ (8GB recommended) |
| API Keys | Gemini (free) at [aistudio.google.com](https://aistudio.google.com/app/apikey) + Groq (free) at [console.groq.com/keys](https://console.groq.com/keys) |

### Quick Start

```bash
git clone https://github.com/subhansh-dev/Rumi
cd rumi
pip install -e .
playwright install chromium
rumi
```

On first launch, RUMI prompts for your Gemini and Groq API keys and saves them to `config/api_keys.json`.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Run `pip install -e .` from project root |
| First launch doesn't appear | Delete `config/api_keys.json` and restart |
| `playwright not found` | Run `playwright install chromium` |
| Groq rate limit errors | Normal for free tier — pipeline auto-retries |
| `sounddevice` fails on Linux | `sudo apt install portaudio19-dev` |
| `pip install -e .` fails on macOS | `pip3 install -e .` + `xcode-select --install` |

---

## Usage

### Discovery

```bash
# Natural language (triggers full 12-phase pipeline)
"run a discovery on fast radio bursts"
"research the multiverse theory"

# Slash command
/discover Oumuamua interstellar object
/discover drug_discovery: KRAS G12C inhibitor resistance

# Python API
from discovery.discovery_pipeline_v2 import run_discovery_pipeline
result = run_discovery_pipeline("anomalous stellar dimming", mode="full")
```

### Slash Commands

| Command | Description |
|---------|-------------|
| `/discover <topic>` | Full 12-phase discovery pipeline |
| `/search <query>` | Quick PubMed search |
| `/dashboard` | Open interactive web dashboard |
| `/contradictions` | Detect contradictions in knowledge graph |
| `/simulate <hypothesis>` | Monte Carlo simulation |
| `/debate <hypothesis>` | 4-agent debate |
| `/continuous [N]` | N autonomous research cycles |
| `/transfer <domain>:<mech> to <domain>` | Cross-domain transfer |
| `/curiosity` | RUMI's research frontier |
| `/evolve` | Theory evolution status |
| `/consistency` | Math consistency check |
| `/status` | System status and uptime |
| `/stats` | Session statistics |
| `/help` | Show all commands |

### Cognitive Tools

```python
# Multi-module cognitive reasoning
cognitive_reason(query="What are the implications of category theory for neural network generalization?", depth="deep")

# Analogy reasoning
analogy_reason(source_domain="biology", target_domain="software_engineering",
               query="How does immune system adaptation inform microservice architecture?")

# Causal analysis
causal_analyze(events="The model performed well on training but failed on test.",
               question="what caused the generalization gap?")

# Creative problem solving
creative_solve(problem="Design a new activation function", constraints="differentiable, efficient", num_ideas=5)
```

### Scientist Agents

```python
agency_agent(agent_name="literature_reviewer", task="Review mechanistic interpretability of transformers")
agency_agent(agent_name="hypothesis_generator", task="Generate hypotheses about scale and emergent abilities")
agency_agent(agent_name="experiment_designer", task="Design experiment to test chain-of-thought emergence")
agency_agent(agent_name="peer_reviewer", task="Review this paper for methodological rigor")
```

### Memory & Learning

```python
save_memory(category="identity", key="name", value="Sir")
brain_memory(action="search", query="preferred programming language")
record_learning(insight="Users prefer direct answers", domain="communication")
reflect_learning(force=True)
```

---

## Configuration

| File | Purpose |
|------|---------|
| `config/api_keys.json` | Gemini + Groq API keys (auto-generated on first launch) |
| `core/prompt.txt` | System personality prompt |
| `RUMI.md` | Identity and behavioral guidelines |
| `SOUL.md` | Core directives and red lines |
| `USER.md` | User profile |
| `memory/` | Persistent memory (long-term + daily logs) |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `RUMI_TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `RUMI_TELEGRAM_ALLOWED_USER` | Allowed Telegram user ID |

---

## Telegram Integration

1. Open Telegram → search **@BotFather** → send `/newbot` → save the token
2. Search **@userinfobot** → send any message → save your numeric User ID
3. Add to `config/api_keys.json`:

```json
{
    "GOOGLE_API_KEY": "your-gemini-key",
    "telegram_bot_token": "7234567890:AAH...",
    "telegram_allowed_user": 123456789
}
```

4. Launch RUMI → send a message to your bot → RUMI responds in terminal and Telegram

Only the configured `telegram_allowed_user` can communicate with RUMI via Telegram.

---

## Project Structure

```
rumi/
├── main.py                      # Entry point (~9000 lines)
├── ui.py                        # Terminal UI (Rich + prompt_toolkit)
├── rumi_launcher.py             # Console entry point
├── rumi_llm.py                  # Unified LLM helper (Groq→Gemini)
├── thinking_loop.py             # Multi-pass reasoning engine
├── telegram_bot.py              # Telegram bridge
├── RUMI.md                      # Identity
├── SOUL.md                      # Core directives
├── USER.md                      # User profile
│
├── discovery/                   # Scientific Discovery Engine (48 modules)
│   ├── discovery_pipeline_v2.py #   12-phase discovery pipeline (ACTIVE)
│   ├── domains.py               #   17 domain configurations
│   ├── graph.py                 #   Knowledge graph + metrics
│   ├── hypothesis_engine.py     #   Hypothesis generation
│   ├── hypothesis_tournament.py #   GFlowNet-style evolution
│   ├── knowledge_gap_detector.py#   Structural holes, orphan observations
│   ├── anomaly_detector.py      #   Conflicting evidence, outliers
│   ├── mechanism_generator.py   #   Causal pathways
│   ├── prediction_engine.py     #   Testable predictions
│   ├── theory_competition.py    #   Multi-theory scoring
│   ├── falsification_engine.py  #   Try to destroy theories
│   ├── computational_verification.py # Real computations
│   ├── discovery_scorer.py      #   6-dimension quality gate
│   ├── refinement_pipeline.py   #   13-stage post-processing
│   ├── multi_agent_debate.py    #   4-role adversarial debate
│   ├── simulation_pipeline.py   #   Monte Carlo (1000 runs)
│   ├── math_consistency_checker.py # Equation validation
│   ├── domain_ontologies.py     #   Real physics for 17 domains
│   ├── cross_domain_transfer.py #   Cross-field analogies
│   ├── continuous_operation.py  #   Autonomous research loop
│   ├── citation_grounding.py    #   Multi-source paper fetch
│   ├── contradiction_miner.py   #   Algorithmic contradiction detection
│   ├── novelty_detector.py      #   PubMed novelty estimation
│   ├── skeptic_agent.py         #   Adversarial critique
│   ├── claim_provenance.py      #   Claim source tracking
│   ├── link_predictor.py        #   Missing connection prediction
│   ├── llm_client.py            #   Unified Groq→Gemini client
│   ├── pubchem.py               #   PubChem enrichment
│   ├── openfda.py               #   OpenFDA enrichment
│   ├── uniprot.py               #   UniProt enrichment
│   ├── pdb.py                   #   Protein Data Bank
│   ├── semantic_scholar.py      #   Paper citations
│   ├── materials_project.py     #   Crystal structures
│   ├── nasa_api.py              #   NASA data
│   ├── arxiv_api.py             #   arXiv papers
│   ├── gbif_api.py              #   Biodiversity data
│   ├── molecule.py              #   Molecule design (RDKit)
│   └── dashboard/
│       └── index.html           #   Interactive web dashboard
│
├── brain/                       # Cognitive Architecture (44 modules)
│   ├── neural_memory.py         #   Hebbian learning
│   ├── episodic_memory.py       #   Event recording
│   ├── vector_memory.py         #   Semantic search
│   ├── active_inference.py      #   Free Energy Principle
│   ├── curiosity.py             #   Novelty detection
│   ├── dreaming.py              #   Experience replay
│   ├── causal_reasoner.py       #   Pearl's causal hierarchy
│   ├── analogy_engine.py        #   Gentner structure mapping
│   ├── creativity_engine.py     #   Conceptual blending
│   ├── self_awareness.py        #   Consciousness tracking
│   ├── self_model.py            #   Capability awareness
│   ├── theory_of_mind.py        #   User modeling
│   ├── metacognitive_monitor.py #   Thinking quality
│   ├── global_workspace.py      #   Thalamus coordination
│   ├── agi_orchestrator.py      #   Master cognitive loop
│   ├── self_improve_engine.py   #   RLHF-inspired improvement
│   ├── reflexion.py             #   Recursive self-improvement
│   ├── scientific_reasoning.py  #   Multi-pass scientific reasoning
│   ├── discovery_orchestrator.py#   Discovery coordination
│   ├── theory_formation.py      #   Theory engine
│   ├── abstraction_engine.py    #   First principles
│   └── ... (30 more modules)
│
├── scientist/                   # Scientist AI (20 files)
│   ├── discovery_engine.py      #   Full discovery pipeline
│   ├── experiment_designer.py   #   Experiment design
│   ├── paper_generator.py       #   Academic paper generation
│   ├── research_team.py         #   5-role multi-agent debate
│   └── pipeline.py              #   12-phase enhanced research pipeline
│
├── actions/                     # Tool actions (14 files)
├── security/                    # Security (7 files)
├── skills/                      # Skill engine (12 files)
├── agent/                       # Task execution (4 files)
├── agents/scientist/            # 11 research agent personas
├── config/                      # Configuration
├── memory/                      # Persistent memory
└── data/                        # Runtime data + discovery reports
```

---

## Run RUMI with AI Assistants

### With Hermes Agent

```
Hey Hermes, I have RUMI at C:\Users\Admin\Desktop\rumi.
Run RUMI's full scientist pipeline to do an edge discovery
in the space astronomy domain. Topic: anomalous stellar
dimming and technosignature detection.
```

### With Claude Code

```
Claude, I have a scientific discovery AI called RUMI at
C:\Users\Admin\Desktop\rumi. Run the full pipeline to
generate novel hypotheses about dark matter detection
methods. Use the physics domain.
```

**Tips:**
- Always specify the domain: `space_astronomy`, `drug_discovery`, `physics`, etc.
- Use `mode="full"` for complete pipeline (all 12 phases)
- Use `mode="quick"` for fast exploration
- Reports save to `data/` as JSON

---

## Contributing

Contributions welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

```bash
git clone https://github.com/subhansh-dev/Rumi.git
cd rumi
pip install -r requirements.txt
python main.py
```

---

## License

[MIT](LICENSE) — Copyright (c) 2026 Subhansh

---

<p align="center">
  <sub>Built by Subhansh · RUMI v2.1</sub>
</p>
