"""
scientist/__init__.py — RUMI Scientist AI Package

A full end-to-end autonomous scientific research system inspired by:
  - Sakana AI's The AI Scientist v2 (Agentic Tree Search)
  - Google's Co-Scientist (Multi-agent collaboration)
  - Bengio's GFlowNets (Diverse hypothesis generation)
  - Feynman's first-principles approach
  - Academic peer review at scale

Modules:
  discovery_engine        — Master orchestrator: idea → experiment → paper → review → iterate
  novelty_checker         — Checks idea novelty against Semantic Scholar / arXiv
  experiment_designer     — Designs experiments, generates/test code, sandboxed execution
  paper_generator         — Generates structured LaTeX manuscripts
  peer_reviewer           — Automated peer review with quality scoring
  feynman_reducer         — First-principles decomposition and simplification
  cross_validator         — Statistical validation, reproducibility checks, baseline comparison
  research_team           — Multi-agent research team with specialized roles and debate
  scientist_search        — Paper search by researcher/topic

  NEW (v2):
  tournament_hypothesis   — GFlowNet-inspired diverse generation + tournament selection
  knowledge_graph         — Structured knowledge graph with multi-hop reasoning
  reproducibility_engine  — Verify and reproduce published results
  active_experiment_selector — Bayesian optimal experiment selection
  cross_domain_connector  — Cross-disciplinary analogy engine
"""

from scientist.discovery_engine import get_discovery_engine, DiscoveryEngine, DiscoveryReport
from scientist.novelty_checker import get_novelty_checker, NoveltyChecker
from scientist.experiment_designer import get_experiment_designer, ExperimentDesigner
from scientist.paper_generator import get_paper_generator, PaperGenerator
from scientist.peer_reviewer import get_peer_reviewer, PeerReviewer
from scientist.feynman_reducer import get_feynman_reducer, FeynmanReducer
from scientist.cross_validator import get_cross_validator, CrossValidator
from scientist.research_team import get_research_team, ResearchTeam
from scientist.scientist_search import get_scientist_search, ScientistSearch

from scientist.tournament_hypothesis import get_tournament_engine, TournamentHypothesisEngine, HypothesisCandidate
from scientist.knowledge_graph import get_knowledge_graph, KnowledgeGraph, KGEntity, KGRelation
from scientist.reproducibility_engine import get_reproducibility_engine, ReproducibilityEngine, ReproducibleClaim, ReproducibilityReport
from scientist.active_experiment_selector import get_experiment_selector, ActiveExperimentSelector, Hypothesis, CandidateExperiment
from scientist.cross_domain_connector import get_cross_domain_connector, CrossDomainConnector, Analogy
from scientist.lab_notebook import get_lab_notebook, LabNotebook, NotebookEntry

__all__ = [
    # Original
    "get_discovery_engine", "DiscoveryEngine", "DiscoveryReport",
    "get_novelty_checker", "NoveltyChecker",
    "get_experiment_designer", "ExperimentDesigner",
    "get_paper_generator", "PaperGenerator",
    "get_peer_reviewer", "PeerReviewer",
    "get_feynman_reducer", "FeynmanReducer",
    "get_cross_validator", "CrossValidator",
    "get_research_team", "ResearchTeam",
    "get_scientist_search", "ScientistSearch",
    # New v2
    "get_tournament_engine", "TournamentHypothesisEngine", "HypothesisCandidate",
    "get_knowledge_graph", "KnowledgeGraph", "KGEntity", "KGRelation",
    "get_reproducibility_engine", "ReproducibilityEngine", "ReproducibleClaim", "ReproducibilityReport",
    "get_experiment_selector", "ActiveExperimentSelector", "Hypothesis", "CandidateExperiment",
    "get_cross_domain_connector", "CrossDomainConnector", "Analogy",
]
