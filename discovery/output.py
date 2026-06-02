import json
import re
from pathlib import Path

HYPOTHESES_DIR = Path(__file__).resolve().parent.parent / "discovery" / "hypotheses"


def post_output(msg):
    """Thread-safe output that strips Rich markup."""
    # Handle complex Rich markup tags like [bold cyan], [style fg='#4a9eff'], etc.
    plain = re.sub(r'\[[^\]]*\]', '', msg) if msg else msg
    print(f"  {plain}" if plain else "")


def _clean_unicode(text):
    """Clean scientific Unicode formatting issues."""
    if not isinstance(text, str):
        return text
    replacements = {
        "\ufffd": "",
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": " — ",
        "\u2212": "-",
        "\u00b5": "μ",
        "\u00b7": "·",
        "\u03b1": "α",
        "\u03b2": "β",
        "\u03b3": "γ",
        "\u03b4": "δ",
        "\u03b5": "ε",
        "\u03bb": "λ",
        "\u03bc": "μ",
        "\u03c0": "π",
        "\u03c3": "σ",
        "\u03c4": "τ",
        "\u03c6": "φ",
        "\u03a9": "Ω",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'([0-9])\s*um\b', r'\1μm', text)
    text = re.sub(r'\?\?m\b', 'μm', text)
    text = re.sub(r'([0-9]+)\s*[Uu][Mm]\b', r'\1μm', text)
    text = re.sub(r'\?', '', text)
    return text


def format_papers(papers: list[dict]) -> str:
    lines = []
    for i, p in enumerate(papers, 1):
        lines.append(f"  {i}. {p['title']}")
        lines.append(f"     PMID: {p['pmid']}  |  {p['url']}")
        lines.append(f"     Year: {p.get('year', 'N/A')} | Citations: {p.get('citations', 'N/A')}")
        abstract = p.get("abstract", "")
        if abstract and abstract != "(No abstract available)":
            lines.append(f"     {_clean_unicode(abstract[:200])}...")
        lines.append("")
    return "\n".join(lines)


def format_hypotheses(hypotheses: list[dict]) -> str:
    lines = ["", "=" * 70, "  SCIENTIFIC HYPOTHESES", "=" * 70, ""]
    for i, h in enumerate(hypotheses, 1):
        # Hypothesis header
        lines.append(f"  +-- Hypothesis {i} {'-' * 40}")
        lines.append(f"  | Title: {h.get('title', 'Untitled')}")
        lines.append(f"  | Pattern: {h.get('pattern_type', 'unknown').replace('_', ' ').title()}")
        lines.append(f"  | Confidence: {h.get('confidence', 'N/A')}")
        lines.append(f"  | Novelty: {h.get('novelty', 'medium').title()}{' (downranked by skeptic)' if h.get('novelty_override') else ''}")
        lines.append(f"  +{'-' * 60}")

        # 1. Mechanistic Rationale
        mech = h.get("mechanistic_rationale", h.get("description", ""))
        if mech:
            lines.append(_wrap_section("Mechanistic Rationale", _clean_unicode(mech)))

        # 2. Supporting Evidence
        supporting = h.get("supporting_evidence", h.get("evidence", []))
        if supporting:
            lines.append(f"  Supporting Evidence:")
            for j, ev in enumerate(supporting, 1):
                lines.append(f"    {j}. {_clean_unicode(ev)}")

        # 3. Contradictory Evidence
        contra = h.get("contradictory_evidence", [])
        if contra:
            lines.append(f"  WARNING: Contradictory Evidence:")
            for j, ev in enumerate(contra, 1):
                lines.append(f"    {j}. {_clean_unicode(ev)}")
        else:
            lines.append(f"  WARNING: Contradictory Evidence: None specified (consider this a weakness)")

        # 4. Alternative Explanations
        alt = h.get("alternative_explanations", [])
        if alt:
            lines.append(f"  Alternative Explanations:")
            for j, a in enumerate(alt, 1):
                lines.append(f"    {j}. {_clean_unicode(a)}")

        # 5. Environmental Constraints
        env = h.get("environmental_constraints", "")
        if env:
            lines.append(f"  Environmental Constraints: {_clean_unicode(env)}")

        # 6. Failure Conditions
        failures = h.get("failure_conditions", [])
        if failures:
            lines.append(f"  Failure Conditions:")
            for j, f in enumerate(failures, 1):
                lines.append(f"    {j}. {_clean_unicode(f)}")

        # 7. Experimental Validation
        exp = h.get("experimental_validation", h.get("testability", ""))
        if exp:
            lines.append(f"  Experimental Validation: {_clean_unicode(exp)}")

        # 8. Observational Requirements
        obs = h.get("observational_requirements", "")
        if obs:
            lines.append(f"  Observational Requirements: {_clean_unicode(obs)}")

        # 9. Source Traceability
        trace = h.get("source_traceability", [])
        if trace:
            lines.append(f"  Source Traceability:")
            if isinstance(trace, list):
                for j, t in enumerate(trace, 1):
                    if isinstance(t, dict):
                        lines.append(f"    {j}. {_clean_unicode(t.get('claim', ''))} — {t.get('source', '')}")
                    else:
                        lines.append(f"    {j}. {_clean_unicode(t)}")
            else:
                lines.append(f"    {_clean_unicode(str(trace))}")

        # 10. Papers / Nodes
        papers = h.get("papers", [])
        if papers:
            lines.append(f"  Papers: {', '.join(papers)}")

        # 11. Knowledge Graph
        nodes = h.get("nodes", [])
        if nodes:
            lines.append(f"  Nodes (Entities):")
            for n in nodes:
                cond = f" — conditions: {n['conditions']}" if n.get("conditions") else ""
                defn = n.get("definition", "")
                lines.append(f"    • {n['name']} ({n['type']}){cond}")
                if defn:
                    lines.append(f"      {defn}")

        edges = h.get("edges", [])
        if edges:
            lines.append(f"  Edges (Relationships):")
            for e in edges:
                defn = e.get("definition", "")
                papers = e.get("papers", [])
                pstr = f" [{' '.join(papers[:3])}]" if papers else ""
                lines.append(f"    {e['source']} --{e['relation']}--> {e['target']}{pstr}")
                if defn:
                    lines.append(f"      {defn}")

        lines.append("")

    return "\n".join(lines)


def _wrap_section(label, text):
    """Format a section label + wrapped text."""
    raw = f"  {label}: {text}"
    # Basic wrapping — split long lines at 80 chars
    if len(raw) <= 80:
        return raw
    lines = [f"  {label}:"]
    while text:
        if len(text) <= 76:
            lines.append(f"    {text}")
            break
        split_at = text.rfind(" ", 0, 76)
        if split_at < 40:
            split_at = 76
        lines.append(f"    {text[:split_at]}")
        text = text[split_at:].strip()
    return "\n".join(lines)


def format_stats(stats: dict) -> str:
    lines = [
        "  Knowledge Graph Stats:",
        f"    Papers: {stats.get('papers', 0)}",
        f"    Entities: {stats.get('entities', 0)}",
        f"    Relationships: {stats.get('relationships', 0)}",
        "",
        "  Entity Types:",
    ]
    for etype, count in stats.get("entity_types", {}).items():
        lines.append(f"    {etype}: {count}")
    lines.append("")
    lines.append("  Top Entities:")
    for ent in stats.get("top_entities", []):
        lines.append(f"    {ent['name']} ({ent['type']}) - {len(ent['papers'])} papers")
    return "\n".join(lines)


def save_hypotheses(hypotheses: list[dict]):
    HYPOTHESES_DIR.mkdir(parents=True, exist_ok=True)
    (HYPOTHESES_DIR / "active.json").write_text(
        json.dumps(hypotheses, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def save_session(query: str, papers: list[dict], hypotheses: list[dict]):
    from datetime import date
    slug = query.lower().replace(" ", "_")[:30]
    fname = f"{date.today()}_{slug}.json"
    session_dir = Path(__file__).resolve().parent.parent / "discovery" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / fname).write_text(
        json.dumps({"query": query, "papers": papers, "hypotheses": hypotheses}, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
