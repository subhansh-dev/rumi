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
from discovery.semantic_scholar import search_papers as s2_search


def fetch_papers(query: str, max_arxiv: int = 20, max_pubmed: int = 20,
                 max_s2: int = 20) -> list[dict]:
    """
    Fetch real papers from arXiv + PubMed + Semantic Scholar.
    Returns unified list sorted by date (newest first).
    Targets 50+ papers for comprehensive coverage.
    """
    papers = []
    seen_titles = set()

    def _add_paper(paper_dict):
        """Add paper if not duplicate."""
        title_key = paper_dict.get("title", "").lower().strip()[:60]
        if title_key and title_key not in seen_titles:
            seen_titles.add(title_key)
            papers.append(paper_dict)

    # ── arXiv ──
    try:
        arxiv_results = arxiv_search(query, max_results=max_arxiv)
        for p in arxiv_results:
            _add_paper({
                "source": "arxiv",
                "id": p.get("arxiv_id", ""),
                "title": p.get("title", "").strip(),
                "abstract": p.get("abstract", "")[:600],
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
                _add_paper({
                    "source": "pubmed",
                    "id": p.get("pmid", ""),
                    "title": p.get("title", "").strip(),
                    "abstract": p.get("abstract", "")[:600],
                    "authors": p.get("authors", []),
                    "year": p.get("year", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{p.get('pmid', '')}/",
                    "citation_key": f"PMID:{p.get('pmid', '')}",
                })
    except Exception as e:
        print(f"  [PubMed] Error: {e}")

    # ── Semantic Scholar (third source — fills gaps) ──
    try:
        s2_results = s2_search(query, limit=max_s2)
        for p in s2_results:
            _add_paper({
                "source": "semantic_scholar",
                "id": p.get("paperId", ""),
                "title": p.get("title", "").strip(),
                "abstract": p.get("abstract", "")[:600] if p.get("abstract") else "",
                "authors": [a.get("name", "") for a in p.get("authors", [])[:5]],
                "year": str(p.get("year", "")),
                "url": f"https://www.semanticscholar.org/paper/{p.get('paperId', '')}",
                "citation_key": f"S2:{p.get('paperId', '')[:8]}",
                "citation_count": p.get("citationCount", 0),
                "influential_citations": p.get("influentialCitationCount", 0),
            })
    except Exception as e:
        print(f"  [SemanticScholar] Error: {e}")

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


def _generate_queries(topic: str, domain: str = "") -> list[str]:
    """Generate targeted search queries from a topic + domain."""
    topic_lower = topic.lower()
    queries = [topic]

    # ── Domain-specific sub-queries ──
    domain_queries = {
        "space_astronomy": {
            "phosphine": ["phosphine Venus atmosphere detection", "PH3 biosignature exoplanet"],
            "venus": ["Venus atmosphere composition", "Venus cloud habitability"],
            "exoplanet": ["exoplanet atmosphere characterization", "exoplanet biosignature"],
            "mars": ["Mars atmosphere methane", "Mars biosignature"],
            "black hole": ["black hole event horizon", "gravitational wave detection"],
            "neutron star": ["neutron star equation of state", "pulsar timing"],
        },
        "drug_discovery": {
            "kinase": ["kinase inhibitor selectivity", "drug resistance mechanism"],
            "antibiotic": ["antimicrobial resistance", "novel antibiotic target"],
            "cancer": ["oncogene targeted therapy", "tumor microenvironment"],
            "protein": ["protein structure drug design", "alphafold drug discovery"],
        },
        "materials_science": {
            "perovskite": ["perovskite solar cell stability", "halide perovskite bandgap"],
            "battery": ["solid state electrolyte", "lithium dendrite formation"],
            "catalyst": ["electrocatalyst oxygen evolution", "photocatalyst water splitting"],
            "2d material": ["graphene electronic properties", "transition metal dichalcogenide"],
        },
        "neuroscience": {
            "neurotransmitter": ["dopamine receptor signaling", "serotonin neural circuit"],
            "brain": ["neural network connectivity", "brain-computer interface"],
            "memory": ["hippocampal place cells", "synaptic plasticity LTP"],
            "consciousness": ["neural correlates consciousness", "integrated information theory"],
        },
        "climate_energy": {
            "climate": ["climate model projection", "carbon capture technology"],
            "solar": ["perovskite solar efficiency", "photovoltaic degradation"],
            "carbon": ["CO2 atmospheric concentration", "carbon sequestration"],
            "renewable": ["grid scale energy storage", "wind turbine efficiency"],
        },
        "ecology": {
            "biodiversity": ["species extinction rate", "biodiversity ecosystem function"],
            "conservation": ["habitat fragmentation effect", "conservation genetics"],
            "invasion": ["invasive species impact", "biological invasion mechanism"],
        },
        "physics": {
            "quantum": ["quantum entanglement verification", "quantum computing error correction"],
            "particle": ["higgs boson decay channel", "dark matter direct detection"],
            "gravity": ["gravitational wave source", "general relativity test"],
        },
        "computer_science": {
            "llm": ["large language model scaling", "transformer attention mechanism"],
            "neural network": ["neural architecture search", "deep learning optimization"],
            "security": ["adversarial machine learning", "federated learning privacy"],
        },
        "public_health": {
            "vaccine": ["vaccine efficacy clinical trial", "mRNA vaccine platform"],
            "pandemic": ["epidemic modeling prediction", "disease surveillance system"],
            "mental health": ["depression treatment outcome", "anxiety disorder prevalence"],
        },
        "chemistry": {
            "organic": ["cross-coupling reaction mechanism", "asymmetric catalysis enantioselective"],
            "biochemistry": ["enzyme catalysis mechanism", "protein folding kinetics"],
            "analytical": ["mass spectrometry sensitivity", "NMR structure determination"],
        },
        "mathematics": {
            "prime": ["prime number distribution", "Riemann hypothesis progress"],
            "topology": ["topological invariant computation", "knot theory application"],
            "optimization": ["convex optimization convergence", "combinatorial optimization heuristic"],
        },
    }

    # Get domain-specific queries
    domain_key = domain if domain in domain_queries else ""
    if not domain_key:
        # Auto-detect domain from topic
        for dkey, keywords in domain_queries.items():
            if any(kw in topic_lower for kw in keywords):
                domain_key = dkey
                break

    if domain_key and domain_key in domain_queries:
        for keyword, sub_queries in domain_queries[domain_key].items():
            if keyword in topic_lower:
                queries.extend(sub_queries)

    # Remove duplicates
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)

    return unique[:5]


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
