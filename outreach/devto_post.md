---
title: "I Built an AI That Does Autonomous Scientific Discovery — Here's What It Found"
published: false
tags: ai, research, openscience, python
canonical_url: https://github.com/subhansh-dev/Rumi
---

# I Built an AI That Does Autonomous Scientific Discovery — Here's What It Found

I'm Subhansh, a 19-year-old developer, and for the past few months I've been building something that I think pushes the boundary of what AI assistants can do. It's called **RUMI** — Research & Unified Machine Intelligence — and it's not another chatbot wrapper. It's a full cognitive architecture that autonomously reads scientific literature, builds knowledge graphs, identifies contradictions, and generates novel, testable hypotheses.

Yes, it actually does science. Let me explain.

## The Problem

Every AI assistant today is stateless. You start from zero each session. There's no memory, no learning, no reasoning beyond single-pass generation. For scientific research, this is fundamentally broken — research requires accumulating knowledge over time, connecting disparate findings, and having the creativity to ask questions nobody thought to ask.

## What RUMI Actually Does

RUMI is a terminal-native framework with **88 cognitive brain modules** and a **10-stage discovery pipeline**. When you give it a research topic, it:

1. **Searches PubMed** for relevant papers
2. **Filters** for semantic relevance
3. **Extracts entities** (genes, proteins, diseases, mechanisms — domain-specific)
4. **Builds a knowledge graph** with relationships and metadata
5. **Enriches** with external APIs (PubChem, UniProt, PDB, OpenFDA, Semantic Scholar, NASA, arXiv, etc.)
6. **Computes graph metrics** (Jaccard, betweenness, entropy, clustering)
7. **Mines contradictions** across papers
8. **Generates hypotheses** with confidence scoring
9. **Runs skeptic review** — an AI agent that tries to disprove each hypothesis
10. **Plans experiments** with controls, variables, and failure mode analysis

It supports **17 scientific domains** — from drug discovery to materials science, neuroscience, climate, space astronomy, ecology, physics, mathematics, and more. It auto-detects the domain from your query.

## The KRAS G12C Discovery

Here's a real example. I asked RUMI to analyze resistance mechanisms in KRAS G12C mutant cancers — a major problem in oncology where patients develop resistance to drugs like sotorasib within months.

RUMI analyzed **14 PubMed papers** from 2026, built a knowledge graph of the resistance landscape, and surfaced these key findings:

- **DHX9-RAC1-PAK1 axis**: Sotorasib-bound KRAS accumulates and reactivates MAPK signaling through DHX9 cytoplasmic retention — a mechanism not previously characterized
- **AURKA/PHB2 positive feedback loop**: Long-term sotorasib treatment upregulates AURKA, which stabilizes PHB2, activating PI3K/AKT and bypassing KRAS blockade
- **MET amplification**: Real-world evidence from 9 patients showing MET amplification as a targetable resistance mechanism, with renewed response to combined KRAS+MET inhibition
- **Dual ON/OFF inhibition**: BBO-8520 (binding both GTP and GDP forms) shows more durable suppression and decreased PI3Kα-AKT activation vs sotorasib alone

These aren't just summaries. RUMI connected findings across papers that hadn't been directly compared, identified the PI3Kα-AKT pathway as a convergence point for multiple resistance mechanisms, and suggested combination strategies.

## The Architecture

RUMI's brain includes:

- **9-type memory system**: neural (Hebbian learning), episodic, vector (semantic search), procedural, working, global workspace, associative, predictive, consolidated
- **Reasoning engines**: causal (Pearl's hierarchy), analogical (Gentner's structure mapping), neurosymbolic, first-principles
- **Dual-process cognition**: System 1 for quick facts, System 2 for deliberate multi-step reasoning
- **Active inference**: Free Energy Principle — minimizes prediction error through Bayesian updating
- **Curiosity engine**: Drives exploration of knowledge gaps
- **Dreaming system**: Offline experience replay for memory consolidation
- **Metacognitive monitor**: Tracks thinking quality, detects cognitive biases

It's grounded in real neuroscience research — Global Workspace Theory (Baars), Integrated Information Theory (Tononi), Free Energy Principle (Friston), Dual Process Theory (Kahneman), and more.

## It's Still Early

I want to be honest: RUMI is still in early stages. I'm actively working on her. The hypothesis generation sometimes fails when LLM APIs are rate-limited. The knowledge graph metrics need more validation. The experiment planner generates plausible designs but they need human expert review.

But the core pipeline works. It reads papers, extracts structured knowledge, finds patterns, and generates hypotheses that are genuinely worth investigating. That's not nothing.

## Try It

RUMI is open source and runs on free API keys (Gemini + Groq):

```bash
git clone https://github.com/subhansh-dev/Rumi
cd rumi
pip install -e .
playwright install chromium
rumi
```

Then just type `/discover KRAS G12C resistance mechanisms` and watch it work.

## Links

- **GitHub**: https://github.com/subhansh-dev/Rumi
- **Portfolio**: https://subhanshh.vercel.app

---

I'm not claiming RUMI will replace scientists. But I think tools like this can accelerate the literature review and hypothesis generation phase of research by orders of magnitude. A process that takes a PhD student weeks — reading papers, building mental models, finding connections — RUMI does in minutes.

If you're working in computational biology, drug discovery, or any field where literature synthesis matters, I'd love your feedback. Open an issue, fork it, or just tell me what's missing.

— Subhansh
