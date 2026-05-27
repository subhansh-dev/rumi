"""
discovery/citation_grounding.py — Real Paper Retrieval & Citation Grounding

Fetches real papers from arXiv + PubMed BEFORE the LLM generates anything.
Injects them as context so the LLM cites real sources instead of hallucinating.
After generation, parses claims and links them to specific papers.

Usage:
    from discovery.citation_grounding import fetch_papers, build_citation_context, ground_claims

    papers = fetch_papers("phosphine Venus atmosphere", max_per_source=5)
    context = build_citation_context(papers)
    # context goes into LLM prompt
    # after LLM output:
    grounded = ground_claims(llm_output, papers)
"""

import re
import time
from discovery.arxiv_api import search_papers as arxiv_search
from discovery.pubmed import search as pubmed_search, fetch as pubmed_fetch


def fetch_papers(query: str, max_arxiv: int = 8, max_pubmed: int = 8) -> list[dict]:
    """
    Fetch real papers from arXiv + PubMed.
    Returns unified list sorted by date (newest first).
    """
    papers = []

    # ── arXiv ──
    try:
        arxiv_results = arxiv_search(query, max_results=max_arxiv)
        for p in arxiv_results:
            papers.append({
                "source": "arxiv",
                "id": p.get("arxiv_id", ""),
                "title": p.get("title", "").strip(),
                "abstract": p.get("abstract", "")[:400],
                "authors": p.get("authors", []),
                "year": p.get("published", "")[:4],
                "url": p.get("url", ""),
                "citation_key": f"arXiv:{p.get('arxiv_id', '')}",
            })
    except Exception as e:
        print(f"  [arXiv] Error: {e}")

    # ── PubMed ──
    try:
        pmids = pubmed_search(query, max_results=max_pubmed)
        if pmids:
            pm_results = pubmed_fetch(pmids)
            for p in pm_results:
                papers.append({
                    "source": "pubmed",
                    "id": p.get("pmid", ""),
                    "title": p.get("title", "").strip(),
                    "abstract": p.get("abstract", "")[:400],
                    "authors": p.get("authors", []),
                    "year": p.get("year", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{p.get('pmid', '')}/",
                    "citation_key": f"PMID:{p.get('pmid', '')}",
                })
    except Exception as e:
        print(f"  [PubMed] Error: {e}")

    # Sort by year descending
    papers.sort(key=lambda p: p.get("year", "0000"), reverse=True)
    return papers


def build_citation_context(papers: list[dict], max_papers: int = 12) -> str:
    """
    Build a structured context block of real papers to inject into the LLM prompt.
    Forces the LLM to cite these specific papers instead of inventing references.
    """
    if not papers:
        return ""

    lines = [
        "=" * 60,
        "REAL PAPER DATABASE — You MUST cite these papers by their citation key.",
        "Do NOT invent papers. Only reference papers listed below.",
        "=" * 60,
        "",
    ]

    for i, p in enumerate(papers[:max_papers], 1):
        authors = ", ".join(p.get("authors", [])[:3])
        if len(p.get("authors", [])) > 3:
            authors += " et al."
        lines.append(
            f"[{i}] {p['citation_key']}  ({p.get('year', 'n/a')})\n"
            f"    Title: {p['title']}\n"
            f"    Authors: {authors}\n"
            f"    Abstract: {p['abstract'][:300]}...\n"
            f"    URL: {p['url']}\n"
        )

    lines.append("=" * 60)
    lines.append(
        "INSTRUCTIONS: When making scientific claims, cite the relevant paper "
        "using [1], [2], etc. If no paper above supports a claim, explicitly "
        "mark it as [UNVERIFIED] or [HYPOTHETICAL]."
    )
    lines.append("=" * 60)

    return "\n".join(lines)


def build_multi_query_context(topic: str) -> str:
    """
    Run multiple targeted queries to get comprehensive coverage.
    Returns the full citation context block.
    """
    # Break topic into sub-queries for better coverage
    queries = _generate_queries(topic)

    all_papers = []
    seen_ids = set()

    for q in queries:
        print(f"  Fetching papers: '{q}'...")
        papers = fetch_papers(q, max_arxiv=5, max_pubmed=5)
        for p in papers:
            pid = p["id"]
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_papers.append(p)

    print(f"  Total unique papers fetched: {len(all_papers)}")
    return build_citation_context(all_papers)


def _generate_queries(topic: str) -> list[str]:
    """Generate targeted search queries from a topic."""
    topic_lower = topic.lower()

    # Extract key entities for targeted queries
    queries = [topic]

    # Add domain-specific sub-queries
    space_keywords = {
        "phosphine": ["phosphine Venus atmosphere detection", "PH3 biosignature exoplanet",
                      "Venus atmospheric chemistry phosphorus"],
        "venus": ["Venus atmosphere composition", "Venus cloud habitability"],
        "exoplanet": ["exoplanet atmosphere characterization", "exoplanet biosignature"],
        "mars": ["Mars atmosphere methane", "Mars biosignature"],
        "jupiter": ["Jupiter atmosphere composition"],
    }

    for keyword, sub_queries in space_keywords.items():
        if keyword in topic_lower:
            queries.extend(sub_queries)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)

    return unique[:5]  # Max 5 queries to stay within rate limits


def ground_claims(text: str, papers: list[dict]) -> dict:
    """
    Parse LLM output and attempt to link claims to real papers.
    Returns a dict with:
      - cited_papers: papers that were referenced
      - uncited_claims: claims without paper support
      - citation_map: mapping of [N] citations to paper data
    """
    # Find all [N] citations in the text
    citation_refs = re.findall(r'\[(\d+)\]', text)
    citation_nums = set(int(n) for n in citation_refs if n.isdigit())

    cited_papers = []
    citation_map = {}
    for num in citation_nums:
        idx = num - 1  # 1-indexed
        if 0 <= idx < len(papers):
            cited_papers.append(papers[idx])
            citation_map[num] = papers[idx]

    # Find sentences with factual claims but no citations
    sentences = re.split(r'(?<=[.!?])\s+', text)
    uncited_claims = []
    claim_indicators = [
        "detected", "found", "reported", "measured", "observed",
        "showed", "demonstrated", "confirmed", "established",
        "ppb", "ppm", "altitude", "concentration", "abundance",
        "upper limit", "non-detection", "significance",
    ]
    for sent in sentences:
        sent_stripped = sent.strip()
        if not sent_stripped or len(sent_stripped) < 30:
            continue
        # Check if sentence has a factual claim indicator
        has_claim = any(ind in sent_stripped.lower() for ind in claim_indicators)
        has_citation = bool(re.search(r'\[\d+\]', sent_stripped))
        has_unverified = '[UNVERIFIED]' in sent_stripped or '[HYPOTHETICAL]' in sent_stripped
        if has_claim and not has_citation and not has_unverified:
            uncited_claims.append(sent_stripped[:200])

    return {
        "cited_papers": cited_papers,
        "uncited_claims": uncited_claims[:20],  # Cap output
        "citation_map": {str(k): {
            "citation_key": v["citation_key"],
            "title": v["title"],
            "url": v["url"],
            "source": v["source"],
        } for k, v in citation_map.items()},
        "total_citations": len(citation_nums),
        "total_papers_available": len(papers),
        "grounding_score": len(citation_nums) / max(1, len(papers)),
    }
