"""
paper_search.py — Academic Paper Search for RUMI Scientist AI

Searches arXiv and Semantic Scholar APIs for academic papers.
Supports keyword search, author search, paper retrieval, and citation tracking.
"""

import json
import re
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional


ARXIV_BASE = "http://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1/paper"


def search_arxiv(query: str, max_results: int = 10) -> list[dict]:
    """Search arXiv for papers matching the query.
    
    Uses the arXiv API (export.arxiv.org) which returns XML results.
    """
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    url = f"{ARXIV_BASE}?{params}"
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8")
    except Exception as e:
        return [{"error": f"arXiv request failed: {e}"}]

    # Parse XML
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return [{"error": "Failed to parse arXiv response"}]

    papers = []
    for entry in root.findall("atom:entry", ns):
        paper = {
            "title": _clean_html(
                (entry.find("atom:title", ns) or entry.find("title", ns)).text.strip()
                .replace("\n", " ").replace("  ", " ")
                if (entry.find("atom:title", ns) or entry.find("title", ns)) is not None
                else "Untitled"
            ),
            "summary": _clean_html(
                (entry.find("atom:summary", ns) or entry.find("summary", ns)).text.strip()
                .replace("\n", " ").replace("  ", " ")
                if (entry.find("atom:summary", ns) or entry.find("summary", ns)) is not None
                else ""
            ),
            "authors": [
                (author.find("atom:name", ns) or author.find("name")).text
                for author in entry.findall("atom:author", ns)
                if (author.find("atom:name", ns) or author.find("name")) is not None
            ],
            "published": (
                (entry.find("atom:published", ns) or entry.find("published", ns)).text[:10]
                if (entry.find("atom:published", ns) or entry.find("published", ns)) is not None
                else ""
            ),
            "updated": (
                (entry.find("atom:updated", ns) or entry.find("updated", ns)).text[:10]
                if (entry.find("atom:updated", ns) or entry.find("updated", ns)) is not None
                else ""
            ),
            "link": (
                (entry.find("atom:id", ns) or entry.find("id", ns)).text.strip()
                if (entry.find("atom:id", ns) or entry.find("id", ns)) is not None
                else ""
            ),
            "category": (
                (entry.find("arxiv:primary_category", ns) or entry.find("primary_category")).attrib.get("term", "")
                if (entry.find("arxiv:primary_category", ns) or entry.find("primary_category")) is not None
                else ""
            ),
            "source": "arXiv",
        }
        papers.append(paper)

    return papers if papers else [{"error": "No papers found on arXiv"}]


def search_semantic_scholar(query: str, max_results: int = 10) -> list[dict]:
    """Search Semantic Scholar for papers matching the query."""
    base = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = urllib.parse.urlencode({
        "query": query,
        "limit": max_results,
        "fields": "title,authors,year,externalIds,url,abstract,citationCount,publicationDate",
    })
    url = f"{base}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return [{"error": f"Semantic Scholar request failed: {e}"}]

    papers = []
    for paper in data.get("data", []):
        papers.append({
            "title": paper.get("title", "Untitled"),
            "summary": (paper.get("abstract") or "")[:500],
            "authors": [a.get("name", "") for a in paper.get("authors", [])],
            "year": str(paper.get("year") or ""),
            "link": paper.get("url", ""),
            "citation_count": paper.get("citationCount", 0),
            "publication_date": paper.get("publicationDate") or "",
            "source": "Semantic Scholar",
        })

    return papers if papers else [{"error": "No papers found on Semantic Scholar"}]


def get_paper_details(paper_id: str) -> dict:
    """Get detailed information about a specific paper by ID.
    
    Accepts arXiv ID (e.g., '2301.00001') or Semantic Scholar ID.
    """
    # Try Semantic Scholar first
    url = f"{SEMANTIC_SCHOLAR_BASE}/{paper_id}"
    params = urllib.parse.urlencode({
        "fields": "title,abstract,authors,year,venue,externalIds,references,citations,embedding,tldr,publicationDate",
    })
    
    try:
        req = urllib.request.Request(f"{url}?{params}", headers={"User-Agent": "RUMI/2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "title": data.get("title", ""),
            "abstract": data.get("abstract", ""),
            "authors": [a.get("name", "") for a in data.get("authors", [])],
            "year": data.get("year", ""),
            "venue": data.get("venue", ""),
            "citation_count": len(data.get("citations", [])),
            "reference_count": len(data.get("references", [])),
            "publication_date": data.get("publicationDate", ""),
            "tldr": data.get("tldr", {}).get("text", "") if data.get("tldr") else "",
            "link": f"https://www.semanticscholar.org/paper/{paper_id}",
            "source": "Semantic Scholar",
        }
    except Exception:
        return {"error": f"Could not fetch details for paper ID: {paper_id}"}


def format_paper_result(papers: list[dict], source: str = "all") -> str:
    """Format paper search results as a readable string."""
    if not papers:
        return "No papers found."
    
    if len(papers) == 1 and "error" in papers[0]:
        return f"⚠️  {papers[0]['error']}"

    lines = []
    lines.append(f"📚 **Paper Search Results** ({source})")
    lines.append("")
    
    for i, paper in enumerate(papers, 1):
        if "error" in paper:
            continue
        title = paper.get("title", "Untitled")
        authors = ", ".join(paper.get("authors", [])[:3])
        if len(paper.get("authors", [])) > 3:
            authors += " et al."
        year = paper.get("year", "") or paper.get("published", "")[:4]
        link = paper.get("link", "")
        summary = (paper.get("summary", "") or paper.get("abstract", "") or "")[:300]
        citations = paper.get("citation_count")
        source_name = paper.get("source", "")
        
        lines.append(f"**{i}. {title}**")
        if authors:
            lines.append(f"   *Authors:* {authors}")
        lines.append(f"   *Year:* {year}  |  *Source:* {source_name}")
        if citations is not None:
            lines.append(f"   *Citations:* {citations}")
        if summary:
            lines.append(f"   *Abstract:* {summary}...")
        if link:
            lines.append(f"   *Link:* {link}")
        lines.append("")

    return "\n".join(lines)


def _clean_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text)


# ── Tool Interface ──────────────────────────────────────────────
TOOL_DEFINITION = {
    "name": "paper_search",
    "description": "Search academic papers from arXiv and Semantic Scholar. Returns titles, authors, abstracts, and links.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (keywords, author name, or topic)",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (1-25)",
                "default": 10,
            },
            "source": {
                "type": "string",
                "enum": ["arxiv", "semantic_scholar", "all"],
                "description": "Which database to search",
                "default": "all",
            },
        },
        "required": ["query"],
    },
}


def execute_paper_search(query: str, max_results: int = 10, source: str = "all") -> str:
    """Execute paper search across specified sources."""
    all_papers = []
    sources_used = []
    
    if source in ("arxiv", "all"):
        papers = search_arxiv(query, max_results)
        if not (len(papers) == 1 and "error" in papers[0]):
            all_papers.extend(papers)
            sources_used.append("arXiv")
    
    if source in ("semantic_scholar", "all"):
        papers = search_semantic_scholar(query, max_results)
        if not (len(papers) == 1 and "error" in papers[0]):
            all_papers.extend(papers)
            sources_used.append("Semantic Scholar")
    
    if not all_papers:
        return f"⚠️  No papers found for '{query}' across {'+'.join(sources_used) if sources_used else 'available sources'}."
    
    source_label = "+".join(sources_used) if sources_used else source
    return format_paper_result(all_papers[:max_results], source_label)
