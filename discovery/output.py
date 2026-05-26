import json
import re
from pathlib import Path

HYPOTHESES_DIR = Path(__file__).resolve().parent.parent / "discovery" / "hypotheses"


def post_output(msg):
    """Thread-safe output that strips Rich markup."""
    plain = re.sub(r'\[/?\w+\]', '', msg) if msg else msg
    print(f"  {plain}" if plain else "")


def format_papers(papers: list[dict]) -> str:
    lines = []
    for i, p in enumerate(papers, 1):
        lines.append(f"  {i}. {p['title']}")
        lines.append(f"     PMID: {p['pmid']}  |  {p['url']}")
        abstract = p.get("abstract", "")
        if abstract and abstract != "(No abstract available)":
            lines.append(f"     {abstract[:200]}...")
        lines.append("")
    return "\n".join(lines)


def format_hypotheses(hypotheses: list[dict]) -> str:
    lines = ["", "=" * 70, "  DISCOVERED HYPOTHESES", "=" * 70, ""]
    for i, h in enumerate(hypotheses, 1):
        lines.append(f"  Hypothesis {i}: {h.get('title', 'Untitled')}")
        lines.append(f"  {'─' * 50}")
        lines.append(f"  Pattern: {h.get('pattern_type', 'unknown').replace('_', ' ').title()}")
        lines.append(f"  Confidence: {h.get('confidence', 'N/A')}")
        lines.append(f"  Novelty: {h.get('novelty', 'medium').title()}")

        mg = h.get("mathematical_grounding", {})
        if mg:
            lines.append(f"  Mathematical Grounding:")
            pm = mg.get("primary_metric", "")
            pv = mg.get("metric_value", "")
            pd = mg.get("metric_definition", "")
            lines.append(f"    Primary: {pm} = {pv}  ({pd})")
            for mk, mv in mg.get("supporting_metrics", {}).items():
                lines.append(f"    {mk}: {mv}")

        lines.append("")
        lines.append(f"  {h.get('description', '')}")
        lines.append("")

        nodes = h.get("nodes", [])
        if nodes:
            lines.append("  Nodes (Entities):")
            for n in nodes:
                cond = f" — conditions: {n['conditions']}" if n.get("conditions") else ""
                defn = n.get("definition", "")
                dg = n.get("degree", "")
                bw = n.get("betweenness", "")
                pc = n.get("papers_count", "")
                meta = f" [deg={dg}, bw={bw}, papers={pc}]" if dg != "" else ""
                lines.append(f"    • {n['name']} ({n['type']}){meta}")
                if defn:
                    lines.append(f"      {defn}{cond}")

        edges = h.get("edges", [])
        if edges:
            lines.append("  Edges (Relationships):")
            for e in edges:
                defn = e.get("definition", "")
                papers = e.get("papers", [])
                pstr = f" [{' '.join(papers[:3])}]" if papers else ""
                lines.append(f"    {e['source']} ──{e['relation']}──→ {e['target']}{pstr}")
                if defn:
                    lines.append(f"      {defn}")

        lines.append("")
        lines.append("  Evidence Chain:")
        for j, ev in enumerate(h.get("evidence", []), 1):
            lines.append(f"    {j}. {ev}")
        lines.append(f"  Papers: {', '.join(h.get('papers', []))}")
        lines.append(f"  Testability: {h.get('testability', 'N/A')}")
        lines.append("")
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
