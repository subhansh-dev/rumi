# RUMI Scientist AI — Research Synthesis

> **Date:** 2026-05-24
> **Purpose:** Synthesize cutting-edge research on Scientist AI, AGI architectures, cognitive systems, and autonomous learning to guide RUMI's development roadmap.

---

## Table of Contents

1. [Scientist AI Systems](#1-scientist-ai-systems)
2. [AGI Cognitive Architectures](#2-agi-cognitive-architectures)
3. [Autonomous Code & Software Engineering AI](#3-autonomous-code--software-engineering-ai)
4. [Curiosity & Open-Ended Learning](#4-curiosity--open-ended-learning)
5. [Integration Roadmap for RUMI](#5-integration-roadmap-for-rumi)

---

## 1. Scientist AI Systems

### 1.1 Sakana AI — The AI Scientist

**Paper:** *The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery* (2024)
**Authors:** Lu et al. (Sakana AI)
**Links:** [arXiv:2408.06292](https://arxiv.org/abs/2408.06292)

**Key Contributions:**
- **End-to-end automation** of the scientific research lifecycle: idea generation → experiment → paper writing → peer review
- Uses LLMs (GPT-4) to generate novel research ideas, then executes experiments via code execution
- Template-based paper generation with LaTeX output
- **Automated peer review**: LLM-as-judge evaluates generated papers on novelty, correctness, clarity
- Open-ended loop: findings feed back into idea generation

**Limitations for RUMI:**
- Very expensive (estimated $15/paper in API costs)
- Paper quality limited by LLM hallucination
- No real-world experiment execution — purely computational experiments

**RUMI Integration Potential:** ★★★★★ (core inspiration)

### 1.2 Google DeepMind — Scientific Discovery Systems

**Key Systems:**
- **AlphaFold** (2021-2024): Protein structure prediction — solved 50-year grand challenge
- **GNoME** (2023): Graph Networks for Materials Exploration — discovered 380,000 stable materials
- **FunSearch** (2023): LLM-guided evolutionary search for mathematical discoveries

**Key Techniques:**
- Combination of domain-specific neural networks + LLM reasoning
- Structured experimental pipelines with clear validation metrics
- Active learning: system proposes experiments that maximize information gain

**RUMI Integration Potential:** ★★★★☆ (experimental design patterns)

### 1.3 Agent-Based Research Systems

| System | Focus | Key Technique |
|--------|-------|---------------|
| **PaperQA** | Literature retrieval & synthesis | RAG over full paper corpus with citation-grounding |
| **Elicit** | Research workflow automation | Structured data extraction from papers |
| **Consensus** | Evidence synthesis | LLM + retrieval-based claim verification |
| **ResearchAgent** (Microsoft, 2024) | Iterative research | Multi-agent: idea → experiment → critique loop |

**RUMI Integration Potential:** ★★★★☆ (literature search already implemented in paper_search.py)

---

## 2. AGI Cognitive Architectures

### 2.1 Active Inference & Free Energy Principle

**Foundational Papers:**
- Friston, K. *The free-energy principle: a unified brain theory?* (2010) — Nature Reviews Neuroscience
- Parr, T. & Friston, K. *Active Inference* (2019) — MIT Press

**Key Concepts:**
- **Free Energy Principle**: All self-organizing systems minimize variational free energy
- **Active Inference**: Perception and action are unified through belief updating
- **Expected Free Energy (EFE)**: Guides action selection — agents choose actions that maximize epistemic value (information gain) and pragmatic value (goal achievement)

**RUMI Status:** ✅ Already implemented (`brain/active_inference.py`, `brain/hierarchical_active_inference.py`)

**Enhancements Recommended:**
- Deep Active Inference (deep temporal models)
- Multi-modal active inference (integrating vision, text, audio)
- Precision-weighted belief updating

### 2.2 Global Workspace Theory (GWT)

**Foundational Papers:**
- Baars, B. *A cognitive theory of consciousness* (1988)
- Dehaene, S. et al. *A neuronal model of a global workspace* (1998)

**Key Concepts:**
- **Global Workspace**: A unified information exchange hub where modules compete for attention
- **Conscious access**: Information that enters the global workspace becomes globally available
- **Ignition**: When a coalition of modules reaches critical activation, it dominates the workspace

**RUMI Status:** ✅ Already implemented (`brain/global_workspace.py`, `brain/workspace_events.py`, `brain/workspace_context.py`)

**Enhancements Recommended:**
- **Attention-based gating**: Use transformer attention mechanisms for workspace access
- **Workspace broadcasting**: Implement genuine global broadcasting with module subscription system
- **Metacognitive workspace monitor**: A meta-level module observing workspace dynamics
- **Competition dynamics**: Strengthen `brain/module_competition.py` with clear winner-take-all mechanisms

### 2.3 Integrated Information Theory (IIT)

**Foundational Papers:**
- Tononi, G. *An information integration theory of consciousness* (2004)
- Tononi, G. et al. *Integrated information theory: from consciousness to its physical substrate* (2016)

**Key Concept:**
- **Φ (Phi)**: A measure of integrated information — the amount of information generated by a system above and beyond its parts
- Systems with high Φ have strong cause-effect repertoires

**RUMI Status:** ✅ Already implemented (`brain/integrated_info.py`)

**Enhancements Recommended:**
- Compute partition-based Φ approximations (PyPhi integration)
- Use Φ as a health metric for cognitive system coherence
- Track Φ over time to detect cognitive degradation or growth

### 2.4 Mixture of Experts & Modular Architectures

**Key Papers:**
- Shazeer et al. *Outrageously Large Neural Networks* (2017) — Sparsely-gated MoE
- Fedus et al. *Switch Transformers* (2021) — Simplified MoE
- **Mixtral 8x7B** (2023) — Successful MoE language model

**Key Concepts:**
- **Sparse activation**: Only a subset of "expert" modules activated per input
- **Routing**: Learned gating network selects which experts to use
- **Load balancing**: Ensures all experts are utilized

**RUMI Status:** ⚠️ Partial — `brain/module_competition.py` implements basic competition

**Enhancements Recommended:**
- **Task-specific routing**: Train a router that maps task embeddings to optimal module subsets
- **Load-balanced module usage**: Prevent over/under-utilization of cognitive modules
- **Dynamic module creation**: Spawn new modules when novel tasks don't fit existing ones

### 2.5 Recursive Self-Improvement

**Key Papers:**
- Schmidhuber, J. *Goal Generation & Self-Improvement* (2009)
- **Self-Taught Optimizer** (2023): An LLM recursively improves its own code
- **Voyager** (2023): LLM-powered agent that discovers and improves skills

**Key Concepts:**
- **Self-play**: System generates increasingly challenging tasks
- **Skill discovery**: Autonomous identification and acquisition of new capabilities
- **Meta-learning**: "Learning to learn" — improving the learning algorithm itself

**RUMI Status:** ⚠️ Partial — `brain/self_improve_engine.py` exists

**Enhancements Recommended:**
- **Self-play curriculum**: Generate tasks at appropriate difficulty level
- **Skill chaining**: Compose discovered skills for complex tasks
- **Code-level self-modification**: Use `brain/self_modifier.py` to suggest and validate code changes

---

## 3. Autonomous Code & Software Engineering AI

### 3.1 SWE-bench & Coding Agents

**Key Systems:**
- **Devin** (Cognition AI, 2024): First AI software engineer — plans, codes, tests, deploys
- **SWE-agent** (Princeton, 2024): State-of-the-art on SWE-bench
- **CodeAct** (2024): Code-as-action paradigm for LLM agents
- **OpenCodeInterpreter** (2024): Open-source coding agent

**Key Techniques:**
- **Agentic loops**: Plan → Code → Test → Fix → Reflect
- **Repository-level understanding**: Build codebase graphs before editing
- **Test-driven development**: Generate tests first, then code to pass them

**RUMI Status:** ✅ `cognitive_coder` action implements build→plan→simulate→debug→reflect loop
**RUMI Status:** ✅ `brain/code_intelligence.py` implements semantic code understanding

### 3.2 Self-Debugging & Reflection

**Key Papers:**
- Chen et al. *Teaching LLMs to Self-Debug* (2023)
- Shinn et al. *Reflexion: An Autonomous Agent with Dynamic Memory and Self-Reflection* (2023)
- Madaan et al. *Self-Refine: Iterative Refinement with Self-Feedback* (2023)

**Key Techniques:**
- **Execution feedback**: Run code, capture errors, feed back to model
- **Self-explanation**: Model explains its own reasoning, catches errors
- **Reflection tokens**: Special tokens that trigger self-review

**RUMI Status:** ✅ `brain/code_reflector.py` and `brain/code_simulator.py` implement these

---

## 4. Curiosity & Open-Ended Learning

### 4.1 Curiosity-Driven Exploration

**Key Papers:**
- Pathak et al. *Curiosity-driven Exploration by Self-Supervised Prediction* (2017)
- Burda et al. *Large-Scale Study of Curiosity-Driven Learning* (2018)
- **RND (Random Network Distillation)** (2018): State-of-the-art exploration bonus

**Key Concepts:**
- **Prediction error as curiosity**: Novelty = inability to predict consequences of an action
- **Exploration bonus**: Reward agent for visiting novel states
- **Epistemic value**: Actions that reduce uncertainty about the world

**RUMI Status:** ✅ `brain/curiosity.py`, `brain/intrinsic_motivation.py` implement basic curiosity

**Enhancements Recommended:**
- **Ensemble disagreement**: Use multiple models where disagreement = novelty
- **Information gain maximization**: Choose actions that maximize expected information gain
- **Curiosity curriculum**: Progressive: simple exploration → complex hypothesis testing

### 4.2 Empowerment & Skill Discovery

**Key Papers:**
- Klyubin et al. *Empowerment: A Universal Agent-Centric Measure of Control* (2005)
- Gregor et al. *Variational Intrinsic Control* (2016)
- Eysenbach et al. *Diversity is All You Need* (2018): Unsupervised skill discovery

**Key Concepts:**
- **Empowerment**: Agent's capacity to influence its own future sensor states
- **Mutual information maximization**: Skills that are distinguishable from each other
- **Skill chaining**: Compose learned skills to solve complex tasks

---

## 5. Integration Roadmap for RUMI

### Already Implemented ✅

| Feature | Location | Notes |
|---------|----------|-------|
| Active Inference | `brain/active_inference.py` | Perception-action loop with EFE |
| Global Workspace | `brain/global_workspace.py` | 12+ module adapters connected |
| Integrated Information (Φ) | `brain/integrated_info.py` | Basic Phi computation |
| Curiosity Module | `brain/curiosity.py` | Topic tracking, exploration suggestions |
| Self-Improvement | `brain/self_improve_engine.py` | Code evolution tracking |
| Code Intelligence | `brain/code_intelligence.py` | Semantic chunking & understanding |
| Reflexion | `brain/code_reflector.py` | Pattern learning & anomaly detection |
| Hierarchical Active Inference | `brain/hierarchical_active_inference.py` | Multi-level temporal abstraction |
| Theory of Mind | `brain/theory_of_mind.py` | User mental model |
| Multi-Agent Orchestration | `brain/multi_agent_orchestrator.py` | 30+ expert agent personas |
| Paper Search (NEW) | `actions/paper_search.py` | arXiv + Semantic Scholar search |
| Hypothesis Engine (NEW) | `brain/hypothesis_engine.py` | Hypothesis CRUD + templates |

### HIGH Priority Enhancements 🚀

#### H1. Scientist AI — Full Research Lifecycle Automation
- **Current**: `paper_search.py` (literature search) + `hypothesis_engine.py` (hypothesis tracking)
- **Goal**: End-to-end research workflow: idea → literature review → hypothesis → experiment → paper
- **Implementation**:
  1. Add `actions/experiment_tracker.py` — track computational experiments with results
  2. Add `actions/research_writer.py` — generate structured research summaries in markdown/LaTeX
  3. Connect to `hypothesis_engine.py`: auto-transition hypotheses through status lifecycle
  4. Add citation management: BibTeX export, citation formatting

#### H2. Enhanced Curiosity — Ensemble Novelty Detection
- **Current**: Basic prediction-error curiosity in `brain/curiosity.py`
- **Goal**: Multi-model disagreement-based novelty detection
- **Implementation**:
  1. Maintain ensemble of 3-5 lightweight predictors per domain
  2. Novelty = inter-model disagreement on prediction
  3. Novel findings auto-create hypotheses in `hypothesis_engine.py`

#### H3. Active Learning for Research
- **Goal**: RUMI proactively identifies knowledge gaps and proposes experiments
- **Implementation**:
  1. Use EFE from `brain/active_inference.py` to score research directions
  2. "Epistemic foraging": prioritize searches/hypotheses that maximize information gain
  3. Auto-generate experiment proposals from uncertainty maps

### MEDIUM Priority Enhancements 🔬

#### M1. Self-Play Curriculum Learning
- Use `brain/goal_engine.py` + `brain/intrinsic_motivation.py` to generate progressive skill challenges
- Track skill mastery and auto-advance difficulty
- Log breakthroughs in `memory/MEMORY.md`

#### M2. Workspace Attention Mechanism
- Replace basic module competition with transformer-based attention gating
- Modules compete for "broadcast time" in global workspace based on relevance
- Implement workspace consciousness metrics (track which modules dominate)

#### M3. Paper Writing Pipeline
- Template-based research paper generation (following Sakana AI pattern)
- Citations automatically formatted from `paper_search.py` results
- Export to LaTeX/PDF

### LOW Priority Enhancements 📋

#### L1. PyPhi Integration
- Connect `brain/integrated_info.py` to PyPhi library for accurate Φ computation
- Use Φ as a real-time cognitive health dashboard metric

#### L2. Recursive Self-Improvement Loop
- `brain/self_modifier.py` + `brain/code_evolution.py` → propose → validate → apply improvements
- Safety-critical: each self-modification requires test suite passing

#### L3. Meta-Cognitive Dashboard
- Visual terminal dashboard showing: module activation, Φ over time, hypothesis pipeline status
- Built into `ui.py` as `/brain_health` slash command

---

## Key Research Sources

1. Lu et al. *The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery*. arXiv:2408.06292 (2024)
2. Friston, K. *The free-energy principle: a unified brain theory?* Nature Reviews Neuroscience 11, 127–138 (2010)
3. Baars, B. *In the Theater of Consciousness: The Workspace of the Mind*. Oxford University Press (1997)
4. Tononi, G. *An information integration theory of consciousness*. BMC Neuroscience 5, 42 (2004)
5. Pathak et al. *Curiosity-driven Exploration by Self-Supervised Prediction*. ICML (2017)
6. Shinn et al. *Reflexion: Language Agents with Verbal Reinforcement Learning*. NeurIPS (2023)
7. Chen et al. *Teaching Large Language Models to Self-Debug*. arXiv:2304.05128 (2023)
8. Shazeer et al. *Outrageously Large Neural Networks*. AAAI (2017)
9. Schmidhuber, J. *Goal Generation & Self-Improvement*. (2009)
10. Sakana AI. *The AI Scientist: Open-Ended Scientific Discovery*. Blog & arXiv (2024)
