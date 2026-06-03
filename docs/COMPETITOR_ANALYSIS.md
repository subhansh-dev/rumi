# RUMI vs Competitors — Deep Analysis
# Sakana AI Scientist vs FutureHouse Robin vs RUMI

## The Three Systems

### 1. Sakana AI — The AI Scientist (Aug 2024)
- **Focus:** Machine learning research automation
- **Approach:** Idea → Code → Experiment → Paper → Peer Review → Iterate
- **Cost:** ~$15 per paper
- **Key innovation:** Full research lifecycle automation with automated peer review
- **Strengths:** Actually RUNS experiments, writes full papers, iterates on ideas
- **Weaknesses:** ML-only, needs GPU, template-based (not open-ended)

### 2. FutureHouse — Robin (May 2025)
- **Focus:** Biology / drug discovery
- **Approach:** Disease → Queries → Literature → Hypotheses → Assays → Candidates → Ranking
- **Key innovation:** Multi-agent specialization (Crow, Falcon, Owl, Finch)
- **Strengths:** Deep literature integration, pairwise ranking, domain-specific agents
- **Weaknesses:** Biology-only, requires Edison platform, no physics/chemistry/astronomy

### 3. RUMI (2026)
- **Focus:** General scientific discovery (17 domains)
- **Approach:** Literature → Graph → Gaps → Anomalies → Variables → Mechanisms → Predictions → Theories → Test
- **Key innovation:** Cognitive architecture + adversarial testing + tournament competition
- **Strengths:** Multi-domain, no GPU needed, adversarial testing, tournament competition
- **Weaknesses:** No experiment execution, no paper generation, single-pass

---

## Where Each System Outperforms RUMI

### Sakana AI Scientist beats RUMI at:

1. **EXPERIMENT EXECUTION** — Sakana actually writes code, runs experiments, and gets results.
   RUMI only analyzes literature. Sakana can discover something NEW by running experiments.
   RUMI can only discover by synthesizing existing knowledge.

2. **AUTOMATED PEER REVIEW** — Sakana has a dedicated peer review system that evaluates
   papers with near-human accuracy. RUMI has skeptic review but it's not as rigorous.

3. **ITERATIVE IMPROVEMENT** — Sakana runs multiple ideas and iterates. Each idea feeds
   back into the next. RUMI runs once per topic.

4. **PAPER GENERATION** — Sakana outputs complete LaTeX papers. RUMI outputs JSON/text reports.

### FutureHouse Robin beats RUMI at:

1. **LITERATURE DEPTH** — Robin uses Crow (specialized literature search) and Falcon
   (deep literature review) as dedicated agents. RUMI fetches papers once and processes
   them in a single pass. Robin does multiple rounds of literature search with refined queries.

2. **PAIRWISE RANKING** — Robin uses Bradley-Terry model for ranking hypotheses through
   pairwise comparisons. This is more robust than RUMI's weighted scoring. When you have
   10 theories, pairwise comparison (45 pairs) gives much better signal than scoring each
   independently.

3. **DOMAIN SPECIALIZATION** — Robin has agents specifically designed for biology
   (Crow for literature, Falcon for review, Owl for reasoning, Finch for data analysis).
   RUMI uses the same generic LLM for everything.

4. **PRACTICAL OUTPUT** — Robin produces actionable outputs: ranked therapeutic candidates,
   experimental assay designs, CSV files. RUMI produces analysis reports.

5. **CHAIN-OF-THOUGHT REASONING** — Robin's prompts use structured chain-of-thought
   reasoning at every step. RUMI's prompts are more direct.

---

## Features to Steal for RUMI

### HIGH IMPACT — Add These

#### 1. Pairwise Comparison Ranking (from Robin)
Robin uses Bradley-Terry model: compare theories in pairs, not independently.
When you have N theories, generate N*(N-1)/2 pairwise comparisons.
This is MUCH more robust than scoring each theory on a Likert scale.

RUMI already has tournament competition, but it scores theories independently.
The fix: add pairwise comparison as a scoring refinement step.

Implementation: After scoring all theories, do N choose 2 pairwise comparisons.
Ask: "Which theory better explains the observations — A or B?"
Use the results to compute a Bradley-Terry ranking.

#### 2. Multi-Round Literature Search (from Robin)
Robin generates multiple search queries, fetches results, then generates MORE
queries based on what it found. RUMI does one round of literature search.

The fix: After initial literature fetch, analyze what was found, generate
refined queries, fetch again. 2-3 rounds total.

Implementation: Add a "literature refinement" step after Phase 1.
Analyze initial papers → identify gaps in coverage → generate new queries → fetch more.

#### 3. Automated Peer Review (from Sakana)
Sakana has a dedicated peer review system that evaluates papers with near-human accuracy.
RUMI has skeptic review but it's not structured like peer review.

The fix: Add a formal peer review stage that evaluates the discovery like a
journal reviewer would: novelty, methodology, significance, clarity, limitations.

Implementation: Add a peer review prompt that asks:
- Is this novel? (compare to existing literature)
- Is the methodology sound? (check for logical gaps)
- Is it significant? (would it change the field?)
- What are the limitations?
- Overall recommendation: accept/revise/reject

#### 4. Chain-of-Thought Structured Reasoning (from Robin)
Robin's prompts use <analysis_planning> tags to force structured reasoning.
RUMI's prompts are more direct — "generate mechanisms" without the reasoning scaffold.

The fix: Add chain-of-thought scaffolding to key prompts (mechanism generation,
hidden variable generation, theory competition).

Implementation: Update prompts to include:
<analysis_planning>
- What do I know?
- What don't I know?
- What are the possible approaches?
- Which approach is most promising?
</analysis_planning>

#### 5. Iterative Refinement (from Sakana)
Sakana iterates on ideas — each run feeds back into the next.
RUMI runs once per topic.

The fix: After a discovery run, analyze what worked and what didn't,
then re-run with refined queries/hypotheses.

Implementation: Add a "reflection and re-run" mode that:
1. Runs discovery once
2. Analyzes what was weak (low-scoring theories, failed predictions)
3. Generates new queries targeting the weak areas
4. Runs discovery again with the refined context
5. Merges results

### MEDIUM IMPACT — Consider Adding

#### 6. Specialized Sub-Agents (from Robin)
Robin has Crow (literature), Falcon (review), Owl (reasoning), Finch (data).
RUMI uses the same LLM for everything.

The fix: Use different prompts/models for different phases.
- Literature phase: optimized for retrieval and summarization
- Mechanism phase: optimized for creative reasoning
- Skeptic phase: optimized for adversarial critique

#### 7. Structured Output Files (from Robin)
Robin produces CSV files, detailed hypothesis reports, literature reviews.
RUMI produces JSON + text.

The fix: Add CSV export for rankings, structured hypothesis reports.

#### 8. Bradley-Terry Pairwise Ranking (from Robin)
Robin uses choix library for Bradley-Terry ranking from pairwise comparisons.
This is mathematically more robust than simple weighted scoring.

The fix: Install choix, add pairwise comparison step to theory competition.

### LOW IMPACT — Nice to Have

#### 9. Paper Generation (from Sakana)
Sakana writes full LaTeX papers. RUMI could generate a structured paper
from discovery results.

#### 10. Code Execution (from Sakana)
Sakana actually runs code. RUMI could add a "computational experiment" phase
that runs simulations or data analysis.

---

## What RUMI Already Does BETTER

1. **Multi-domain** — RUMI handles 17 domains. Robin is biology-only. Sakana is ML-only.

2. **Adversarial Testing** — RUMI has the Test Stage (Phase 8.5) that attacks every
   discovery with three questions. Neither Sakana nor Robin has this.

3. **Tournament Competition** — RUMI generates 20 theories and eliminates weak ones
   in rounds. Robin generates candidates but doesn't do tournament elimination.

4. **Epistemic Labeling** — RUMI labels parameters as [CITED]/[DERIVED]/[ESTIMATED].
   Neither Sakana nor Robin does this.

5. **Known-vs-New Classification** — RUMI classifies discoveries as replication/
   synthesis/extension/novel_theory. Neither competitor does this explicitly.

6. **No GPU needed** — RUMI runs on CPU with free-tier APIs. Sakana needs GPUs.

7. **No platform dependency** — RUMI is self-contained. Robin needs Edison platform.

8. **Derivation Feature** — RUMI can derive equations from first principles.
   Neither competitor does this.

---

## Priority Implementation Order

1. **Pairwise Comparison Ranking** (from Robin) — highest impact, easiest to implement
2. **Multi-Round Literature Search** (from Robin) — high impact, moderate effort
3. **Automated Peer Review** (from Sakana) — high impact, easy to implement
4. **Chain-of-Thought Scaffolding** (from Robin) — medium impact, easy to implement
5. **Iterative Refinement** (from Sakana) — medium impact, moderate effort
6. **Specialized Sub-Agents** (from Robin) — medium impact, moderate effort
7. **Structured Output Files** (from Robin) — low impact, easy to implement
