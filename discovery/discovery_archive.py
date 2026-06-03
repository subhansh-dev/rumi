"""
discovery_archive.py — Persistent Discovery Memory Across Runs

RUMI should remember what it discovered before. This module:
1. Saves key results from each run to a persistent archive
2. Loads past discoveries at the start of new runs
3. Provides context: "you already found X, don't re-discover it"
4. Tracks how theories evolve across runs
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional

ARCHIVE_PATH = Path(__file__).parent.parent / "data" / "discovery_archive.json"


def load_archive() -> dict:
    """Load the persistent discovery archive."""
    if ARCHIVE_PATH.exists():
        try:
            return json.loads(ARCHIVE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"runs": [], "known_theories": [], "known_variables": [], "known_mechanisms": []}


def save_to_archive(report: dict, topic: str, domain: str):
    """Save key results from a discovery run to the archive."""
    archive = load_archive()
    phases = report.get("phases", {})

    # Extract key results
    theories = phases.get("theory_competition", {}).get("theories", [])
    variables = phases.get("missing_variables", {}).get("variable_details", [])
    mechanisms = phases.get("mechanism_generation", {}).get("mechanism_details", [])
    score = phases.get("discovery_scoring", {}).get("discovery_score", 0)
    grade = phases.get("discovery_scoring", {}).get("grade", "F")

    # Build run summary
    run_summary = {
        "topic": topic,
        "domain": domain,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "score": score,
        "grade": grade,
        "papers": phases.get("literature", {}).get("papers_found", 0),
        "entities": phases.get("knowledge_graph", {}).get("entities", 0),
        "theories_count": len(theories),
        "variables_count": len(variables),
        "mechanisms_count": len(mechanisms),
    }

    # Save theories (deduplicated by name)
    for t in theories:
        if isinstance(t, dict):
            name = t.get("name", "").strip()
            if name:
                existing = {et.get("name", "").lower() for et in archive.get("known_theories", [])}
                if name.lower() not in existing:
                    archive.setdefault("known_theories", []).append({
                        "name": name,
                        "description": t.get("description", "")[:200],
                        "type": t.get("type", ""),
                        "score": t.get("scores", {}).get("overall", 0),
                        "run_topic": topic,
                        "run_timestamp": run_summary["timestamp"],
                    })

    # Save variables (deduplicated by name)
    for v in variables:
        if isinstance(v, dict):
            name = v.get("name", "").strip()
            if name:
                existing = {ev.get("name", "").lower() for ev in archive.get("known_variables", [])}
                if name.lower() not in existing:
                    archive.setdefault("known_variables", []).append({
                        "name": name,
                        "type": v.get("type", ""),
                        "description": v.get("description", "")[:200],
                        "run_topic": topic,
                        "run_timestamp": run_summary["timestamp"],
                    })

    # Save mechanisms (deduplicated by name)
    for m in mechanisms:
        if isinstance(m, dict):
            name = m.get("name", "").strip()
            if name:
                existing = {em.get("name", "").lower() for em in archive.get("known_mechanisms", [])}
                if name.lower() not in existing:
                    archive.setdefault("known_mechanisms", []).append({
                        "name": name,
                        "type": m.get("type", ""),
                        "description": m.get("description", "")[:200],
                        "run_topic": topic,
                        "run_timestamp": run_summary["timestamp"],
                    })

    # Add run summary
    archive.setdefault("runs", []).append(run_summary)

    # Keep archive manageable (last 50 runs, last 200 theories/variables/mechanisms)
    archive["runs"] = archive["runs"][-50:]
    archive["known_theories"] = archive["known_theories"][-200:]
    archive["known_variables"] = archive["known_variables"][-200:]
    archive["known_mechanisms"] = archive["known_mechanisms"][-200:]

    # Save
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_PATH.write_text(json.dumps(archive, indent=2, default=str), encoding="utf-8")
    return run_summary


def get_archive_context(topic: str, domain: str) -> str:
    """Generate context from past discoveries for a new run.

    This tells RUMI: "you already found these things, don't re-discover them.
    Build on them or explore new angles."
    """
    archive = load_archive()
    if not archive.get("runs"):
        return "No previous discoveries in archive."

    lines = []
    lines.append("PREVIOUS DISCOVERY CONTEXT:")
    lines.append("You have run discoveries before. Here's what you already found.")
    lines.append("Don't re-discover these — build on them or explore new angles.")
    lines.append("")

    # Recent runs
    recent_runs = archive.get("runs", [])[-5:]
    if recent_runs:
        lines.append("Recent runs:")
        for r in recent_runs:
            lines.append(f"  - {r.get('topic', '?')} (domain: {r.get('domain', '?')}, "
                        f"score: {r.get('score', 0):.0f}/100, {r.get('timestamp', '?')})")
        lines.append("")

    # Known theories (relevant to current domain)
    relevant_theories = [t for t in archive.get("known_theories", [])
                        if t.get("run_topic", "").lower().startswith(topic[:20].lower())
                        or t.get("run_topic", "").lower() in topic.lower()
                        or topic.lower() in t.get("run_topic", "").lower()]
    if relevant_theories:
        lines.append(f"Previously discovered theories ({len(relevant_theories)}):")
        for t in relevant_theories[-5:]:
            lines.append(f"  - {t.get('name', '?')} (score: {t.get('score', 0):.2f})")
            lines.append(f"    {t.get('description', '')[:100]}")
        lines.append("")

    # Known variables
    relevant_vars = [v for v in archive.get("known_variables", [])
                    if v.get("run_topic", "").lower().startswith(topic[:20].lower())
                    or v.get("run_topic", "").lower() in topic.lower()
                    or topic.lower() in v.get("run_topic", "").lower()]
    if relevant_vars:
        lines.append(f"Previously proposed hidden variables ({len(relevant_vars)}):")
        for v in relevant_vars[-5:]:
            lines.append(f"  - [{v.get('type', '?')}] {v.get('name', '?')}")
        lines.append("")

    # Known mechanisms
    relevant_mechs = [m for m in archive.get("known_mechanisms", [])
                     if m.get("run_topic", "").lower().startswith(topic[:20].lower())
                     or m.get("run_topic", "").lower() in topic.lower()
                     or topic.lower() in m.get("run_topic", "").lower()]
    if relevant_mechs:
        lines.append(f"Previously discovered mechanisms ({len(relevant_mechs)}):")
        for m in relevant_mechs[-5:]:
            lines.append(f"  - [{m.get('type', '?')}] {m.get('name', '?')}")
        lines.append("")

    if not relevant_theories and not relevant_vars and not relevant_mechs:
        lines.append(f"No previous discoveries on '{topic}' — this is a fresh exploration.")
    else:
        lines.append("INSTRUCTION: Build on these previous findings or explore angles not yet covered.")

    return "\n".join(lines)


def get_archive_stats() -> dict:
    """Get summary statistics of the archive."""
    archive = load_archive()
    return {
        "total_runs": len(archive.get("runs", [])),
        "total_theories": len(archive.get("known_theories", [])),
        "total_variables": len(archive.get("known_variables", [])),
        "total_mechanisms": len(archive.get("known_mechanisms", [])),
        "topics_covered": list(set(r.get("topic", "") for r in archive.get("runs", []))),
    }
