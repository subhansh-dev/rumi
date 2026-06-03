"""Quick test of the refinement pipeline."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from discovery.refinement_pipeline import run_refinement_pipeline
from discovery.graph import KnowledgeGraph

# Minimal mock data
graph = KnowledgeGraph(persist=False)
graph.domain = "space_astronomy"
entities = [
    {"name": "Black Hole", "type": "object", "description": "Gravitational singularity"},
    {"name": "Information Paradox", "type": "process", "description": "Quantum info loss"},
    {"name": "Hawking Radiation", "type": "process", "description": "Thermal emission from BH"},
    {"name": "Holographic Principle", "type": "process", "description": "Info on boundary"},
    {"name": "Firewall Paradox", "type": "process", "description": "AMPS argument"},
]
for e in entities:
    eid = f"{e['type']}_{e['name'].lower().replace(' ', '_')}"
    graph.entities[eid] = {"id": eid, "type": e["type"], "name": e["name"], "aliases": [], "papers": ["p1"]}

papers = [
    {"title": "The Black Hole Information Problem", "source": "pubmed", "year": "2025", "abstract": "Review of the information paradox"},
    {"title": "Hawking radiation and information loss", "source": "arxiv", "year": "2024", "abstract": "Quantum effects near event horizon"},
    {"title": "Holographic principle and black holes", "source": "pubmed", "year": "2023", "abstract": "Information encoded on boundary"},
]

hypotheses = [
    {"id": "h1", "title": "Information preserved via holographic encoding on event horizon",
     "description": "Information about infalling matter is encoded on the event horizon via the holographic principle, preserving unitarity.",
     "confidence": 0.6, "novelty": "high", "key_parameters": [{"name": "entropy", "units": "bits"}]},
]

print("Running refinement pipeline...")
results = run_refinement_pipeline(
    "black hole information paradox", "space_astronomy",
    papers, graph, hypotheses
)

print("\n" + "=" * 50)
print("RESULTS SUMMARY")
print("=" * 50)
for stage, data in results.items():
    if isinstance(data, dict):
        keys = list(data.keys())[:5]
        print(f"  {stage}: {keys}")
    else:
        print(f"  {stage}: {type(data)}")

print(f"\nClassification: {results.get('classification', {}).get('classification', '?')}")
print(f"Grade: {results.get('scoring', {}).get('grade', '?')}")
print(f"Verdict: {results.get('courtroom', {}).get('verdict', '?')}")
