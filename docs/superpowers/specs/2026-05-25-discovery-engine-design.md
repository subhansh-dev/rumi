# RUMI Discovery Engine — Design Document

**Date:** 2026-05-25
**Status:** Approved design, pre-implementation

---

## Overview

RUMI becomes a genuine autonomous scientific discovery AI — starting with drug discovery literature mining, scaling to drug repurposing and de novo molecule generation. Unlike the previous "12-phase pipeline" which generated a paper *plan*, the Discovery Engine produces **real, testable hypotheses** from real research papers.

**Vision:** Type /discover find repurposing targets for Metformin → RUMI searches PubMed, extracts entities, builds a knowledge graph, mines overlooked connections, and returns 3-5 novel hypotheses with evidence chains — all autonomously.

---

## Architecture

### Approach: Agentic Workflow (RUMI-driven, minimal infrastructure)

No separate server. RUMI drives everything from her session using:
- web_search / webfetch → query PubMed Entrez API
- Gemini (her own model) → entity extraction, reasoning, hypothesis generation
- Local JSON files → persistent knowledge graph across sessions
- Single HTML file → web dashboard for visual exploration

### Pipeline Flow

`
User: "/discover <topic>"
          |
          v
  Discovery Intake Protocol
  - Clarifying questions (domain, depth, specific angle)
          |
          v
  1. PubMed Search
     webfetch(entrez API) -> PMIDs + abstracts
          |
          v
  2. Entity Extraction
     Gemini: paper -> {drug, disease, gene, mechanism, relation} triples
          |
          v
  3. Knowledge Graph Build
     Merge entities + relationships -> discovery/graph/knowledge_graph.json
          |
          v
  4. Pattern Mining
     Graph algorithms + Gemini:
     - Indirect connections (drug repurposing)
     - Bridge nodes (connecting disconnected clusters)
     - Contradictions (conflicting findings)
     - Low co-occurrence / high potential
          |
          v
  5. Hypothesis Generation
     Gemini: 3-5 falsifiable hypotheses with evidence chains
          |
          v
  6. Output
     Terminal: formatted results
     Files: saved to discovery/
     Dashboard: updated HTML
`

---

## Discovery Intake Protocol

Before running any pipeline, RUMI asks targeted clarifying questions (one at a time, multiple choice preferred):

| Question | Purpose | Example options |
|---|---|---|
| **Domain** | What field? | Drug discovery / Biomedicine / Materials / General |
| **Specific focus** | Exact target? | "Repurpose Metformin" / "Novel antibiotics" / "Alzheimer's treatments" |
| **Depth** | How thorough? | "Quick scan (20 papers)" / "Deep dive (100+ papers)" |
| **Existing data?** | Build on previous? | "Fresh start" / "Build on existing graph" |

---

## Commands

| Command | Description |
|---|---|
| /discover <topic> | Full pipeline: intake -> search -> extract -> graph -> mine -> hypothesize |
| /search <query> | Quick PubMed search, show results, no deep analysis |
| /hypothesize <topic> | Mine existing graph for new hypotheses |
| /graph | Show knowledge graph stats (nodes, edges, top entities, gaps) |
| /dashboard | Open discovery dashboard in browser |
| /discoveries | List all saved discoveries with hypotheses |

---

## Knowledge Graph Data Model

### Entity Types

drug, disease, gene, protein, mechanism, pathway, 	issue, symptom, side_effect

### Relation Types

	reats, causes, ctivates, inhibits, inds, expressed_in, egulates, ssociated_with, contraindicates, metabolized_by

### Confidence Levels

| Level | Description |
|---|---|
| 0.9-1.0 | Explicitly stated in paper abstract |
| 0.7-0.9 | Strongly implied |
| 0.5-0.7 | Weakly implied or inferred |
| 0.3-0.5 | Speculative (LLM extrapolation) |

### Storage Format

Entities stored by ID in a JSON object. Each entity has type, name, aliases, associated paper PMIDs, and optional properties. Relationships stored as an array of objects with source, relation, target, confidence, supporting papers, and contradictions.

---

## Pattern Mining Strategies

### 1. Indirect Connection (Drug Repurposing)
Drug A -> treats -> Disease X (via Mechanism M)
Mechanism M -> dysregulated_in -> Disease Y
**Hypothesis:** Drug A might treat Disease Y

### 2. Bridge Node Discovery
Entity E connects two otherwise disconnected disease clusters
**Hypothesis:** E is a previously overlooked mechanistic link

### 3. Contradiction Detection
Paper 1: Drug A -> activates -> Gene G
Paper 2: Drug A -> inhibits -> Gene G
**Hypothesis:** Context-dependent modulation (dosage, tissue, subtype)

### 4. Low Co-occurrence / High Potential
Two entities with strong mechanistic plausibility but rarely co-mentioned
**Hypothesis:** Overlooked connection worth investigating.

---

## Dashboard

Single HTML file (discovery/dashboard/index.html) using:
- **vis-network CDN** for interactive knowledge graph
- **Pure CSS** for styling (no frameworks)
- Reads from discovery/graph/knowledge_graph.json and discovery/hypotheses/

Tabs:
1. **Graph** — Interactive knowledge graph. Drugs=green, diseases=red, genes=blue, mechanisms=orange. Click node -> shows connected papers + evidence.
2. **Hypotheses** — Ranked list with expandable evidence chains.
3. **Papers** — Searchable paper list with extracted entities.
4. **Stats** — Graph metrics, top entities, gap clusters.

---

## File Structure

`
rumi/
  discovery/
    sessions/                    # One JSON per /discover command
      2026-05-25_metformin.json
    graph/
      knowledge_graph.json       # Merged graph across all sessions
    hypotheses/
      active.json                # Current ranked hypotheses
      archived.json              # Older, for tracking
    dashboard/
      index.html                 # Single-file dashboard (vis-network)
  config/
    api_keys.json                # Add ncbi_email for PubMed access
  ui.py                          # Add /discover, /search, /hypothesize, /graph, /dashboard, /discoveries
  main.py                        # Discovery orchestration methods
  SOUL.md                        # Updated with Discovery Intake Protocol
  RUMI.md                        # Updated capabilities
`

---

## Implementation Phases

### Phase 1 (This sprint)
- PubMed search via webfetch (Entrez API)
- Entity extraction via Gemini
- Knowledge graph in JSON (via Python script or direct file writes)
- Pattern mining via Gemini reasoning over graph
- Hypothesis generation with evidence chains
- Basic terminal output
- /discover and /graph commands

### Phase 2 (Next)
- Web dashboard (single HTML file)
- Drug repurposing focused searches
- /dashboard, /discoveries, /hypothesize commands
- Discovery Intake Protocol (clarifying questions)

### Phase 3 (Future)
- De novo molecule generation via RDKit
- DrugBank/PubChem integration
- Automated contradiction resolution
- Autonomous idle-time discovery scanning

---

## Files to Modify

| File | Change |
|---|---|
| ui.py | Add 6 new slash command handlers |
| main.py | Add discovery orchestration methods |
| SOUL.md | Add Discovery Intake Protocol to Scientist AI Protocols section |
| RUMI.md | Add Discovery Engine to capabilities table |
| config/api_keys.json | Add 
cbi_email for PubMed API access |

## Files to Create

| File | Purpose |
|---|---|
| discovery/__init__.py | Package init |
| discovery/pubmed.py | PubMed search and fetch functions |
| discovery/extractor.py | Entity extraction from paper text |
| discovery/graph.py | Knowledge graph build, merge, query |
| discovery/miner.py | Pattern mining strategies |
| discovery/hypothesize.py | Hypothesis generation and ranking |
| discovery/output.py | Terminal formatting, file output |
| discovery/dashboard/index.html | Web dashboard |
