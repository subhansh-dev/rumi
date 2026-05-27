# -*- coding: utf-8 -*-
"""
agency_agent.py — RUMI Agency Agent Tool
Invokes specialized Scientist AI expert agent personas.
Loads agent markdown as system prompt, executes task via Gemini.
"""
import json
import os
import sys
from pathlib import Path


def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _get_base_dir()
AGENTS_DIR = BASE_DIR / "agents"
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

_client_instance = None


def _get_api_key() -> str:
    try:
        data = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        key = data.get("gemini_api_key", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("GOOGLE_API_KEY", "")


AGENT_MAP: dict[str, str] = {
    # Scientist AI — Literature & Knowledge
    "literature_reviewer":            "scientist/literature_reviewer.md",
    "knowledge_curator":              "scientist/knowledge_curator.md",
    "novelty_analyst":                "scientist/novelty_analyst.md",
    # Scientist AI — Hypothesis & Experiment
    "hypothesis_generator":           "scientist/hypothesis_generator.md",
    "experiment_designer":            "scientist/experiment_designer.md",
    "data_analyst":                   "scientist/data_analyst.md",
    # Scientist AI — Validation & Communication
    "peer_reviewer":                  "scientist/peer_reviewer.md",
    "reproducibility_engineer":       "scientist/reproducibility_engineer.md",
    "paper_writer":                   "scientist/paper_writer.md",
    # Scientist AI — Integration & Coordination
    "cross_domain_bridge":            "scientist/cross_domain_bridge.md",
    "research_coordinator":           "scientist/research_coordinator.md",
}


AGENT_ALIASES = {
    # Literature & Knowledge
    "literature review":        "literature_reviewer",
    "review literature":        "literature_reviewer",
    "literature":               "literature_reviewer",
    "knowledge graph":          "knowledge_curator",
    "knowledge":                "knowledge_curator",
    "curator":                  "knowledge_curator",
    "novelty":                  "novelty_analyst",
    "novelty check":            "novelty_analyst",
    "is this novel":           "novelty_analyst",
    # Hypothesis & Experiment
    "hypothesis":               "hypothesis_generator",
    "generate hypothesis":      "hypothesis_generator",
    "hypothesize":              "hypothesis_generator",
    "experiment":               "experiment_designer",
    "design experiment":        "experiment_designer",
    "experimental design":      "experiment_designer",
    "data analysis":            "data_analyst",
    "analyze data":             "data_analyst",
    "data":                     "data_analyst",
    # Validation & Communication
    "peer review":              "peer_reviewer",
    "review paper":             "peer_reviewer",
    "reviewer":                 "peer_reviewer",
    "reproducibility":          "reproducibility_engineer",
    "reproduce":                "reproducibility_engineer",
    "paper":                    "paper_writer",
    "write paper":              "paper_writer",
    "paper writer":             "paper_writer",
    "research paper":           "paper_writer",
    # Integration & Coordination
    "cross domain":             "cross_domain_bridge",
    "bridge":                   "cross_domain_bridge",
    "analogy":                  "cross_domain_bridge",
    "transfer":                 "cross_domain_bridge",
    "coordinator":              "research_coordinator",
    "coordinate":               "research_coordinator",
    "research plan":            "research_coordinator",
    "full research":            "research_coordinator",
}


def _resolve_agent(name: str) -> str:
    normalized = name.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in AGENT_MAP:
        return normalized
    lower_name = name.strip().lower()
    if lower_name in AGENT_ALIASES:
        return AGENT_ALIASES[lower_name]
    for alias, canonical in AGENT_ALIASES.items():
        if alias in lower_name or lower_name in alias:
            return canonical
    return normalized


def _load_agent_prompt(agent_name: str) -> str:
    canonical = _resolve_agent(agent_name)
    if canonical not in AGENT_MAP:
        available = ", ".join(sorted(AGENT_MAP.keys()))
        raise ValueError(
            f"Unknown agent '{agent_name}'. "
            f"Available: {available}"
        )
    file_path = AGENTS_DIR / AGENT_MAP[canonical]
    if not file_path.exists():
        raise FileNotFoundError(
            f"Agent file not found: {file_path}. "
        )
    return file_path.read_text(encoding="utf-8")


def agency_agent(parameters: dict, player=None, **kwargs) -> str:
    """
    Invoke a specialized Scientist AI expert agent persona.

    Parameters:
        agent_name: str — agent name or alias (e.g. "literature_reviewer", "hypothesis")
        task: str — the task or question for the agent
        context: str — optional data or findings to analyze
    """
    agent_name = parameters.get("agent_name", "")
    task = parameters.get("task", "")
    context = parameters.get("context", "")

    if not agent_name:
        return "Error: agent_name is required. Specify which expert agent to invoke."

    try:
        agent_prompt = _load_agent_prompt(agent_name)
    except (ValueError, FileNotFoundError) as e:
        return f"Error: {e}"

    full_prompt = f"{agent_prompt}\n\n## Task\n{task}"
    if context:
        full_prompt += f"\n\n## Context\n{context}"

    try:
        from rumi_llm import generate
        result = generate("gemini-2.5-flash", full_prompt)
        if not result:
            return f"Error: LLM unavailable for {agent_name}"
        return result
    except Exception as e:
        return f"Error invoking {agent_name}: {e}" 
