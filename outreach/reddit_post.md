# Reddit Post

## Target subreddits: r/MachineLearning, r/artificial, r/LocalLLaMA, r/bioinformatics, r/opensource

### Title:
I built an open-source AI that autonomously reads scientific papers, builds knowledge graphs, and generates novel hypotheses — here's what it found when analyzing cancer drug resistance

### Body:

Hey everyone,

I'm Subhansh (19), and I've been building something I'm pretty excited about. It's called RUMI (Research & Unified Machine Intelligence) — an autonomous scientific cognition framework that goes beyond "chat with papers" into actual hypothesis generation.

**What makes it different from ChatGPT/Perplexity/etc:**

- It has a 10-stage discovery pipeline: PubMed search → entity extraction → knowledge graph → enrichment (PubChem, UniProt, PDB, NASA, arXiv, 15+ APIs) → contradiction mining → hypothesis generation → skeptic review → novelty verification → experiment planning
- 88 cognitive brain modules — causal reasoning (Pearl), analogical reasoning (Gentner), active inference (Friston's Free Energy Principle), dual-process cognition (Kahneman), metacognition, curiosity-driven exploration
- 9-type memory system that persists across sessions (neural, episodic, vector, procedural, etc.)
- Supports 17 scientific domains with auto-detection
- Terminal-native, no GUI bloat, runs on free API keys (Gemini + Groq)

**Real example — KRAS G12C cancer resistance:**

I ran RUMI on KRAS G12C resistance mechanisms (a hot topic in oncology — patients develop resistance to sotorasib within months). It analyzed 14 recent PubMed papers and:

- Identified the DHX9-RAC1-PAK1 axis as a novel resistance mechanism (sotorasib-bound KRAS accumulation reactivating MAPK)
- Found the AURKA/PHB2 positive feedback loop bypassing KRAS blockade via PI3K/AKT
- Connected MET amplification across multiple papers as a targetable resistance mechanism
- Surfaced that dual ON/OFF KRAS inhibition (BBO-8520) shows more durable suppression

These connections across papers weren't explicitly made in any single review. RUMI found them by building a knowledge graph and mining cross-paper patterns.

**What it looks like:**

```
> /discover KRAS G12C resistance mechanisms

Domain detected: drug_discovery
Searching PubMed... 14 papers found
Extracting entities... 47 entities, 89 relationships
Building knowledge graph... 
Enriching with PubChem, UniProt, PDB...
Computing graph metrics...
Mining contradictions...
Generating hypotheses... 3 hypotheses generated
Skeptic review... 2 survived
Planning experiments...
```

**Honest caveats:**

- Still early stage, I'm actively developing it
- Hypothesis generation fails sometimes when APIs rate-limit
- Experiment plans need human expert review
- It won't replace scientists — but it can accelerate literature synthesis from weeks to minutes

**Links:**

- GitHub: https://github.com/subhansh-dev/Rumi
- Portfolio: https://subhanshh.vercel.app

Would love feedback from anyone in comp bio, drug discovery, or AI4Science. What's missing? What would make this actually useful for your workflow?
