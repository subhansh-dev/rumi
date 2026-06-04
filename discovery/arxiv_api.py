"""arXiv API — free, no key needed.

Provides: paper search for physics, astronomy, math, CS, etc.
Rate limit: ~1 req/3s recommended.
"""

import time
import urllib.request
import urllib.parse

ARXIV_BASE = "https://export.arxiv.org/api/query"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 3.0:
        time.sleep(3.0 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def search_papers(query: str, max_results: int = 10) -> list[dict]:
    """Search arXiv papers. Returns list of paper dicts."""
    # Use shorter, keyword-based queries for better arxiv results
    # Long colon-separated titles confuse the arxiv search
    if ':' in query:
        # Extract the part before the colon (usually the core topic)
        short_q = query.split(':')[0].strip()
    else:
        short_q = query
    # Further shorten if still too long (>80 chars)
    if len(short_q) > 80:
        words = short_q.split()
        short_q = ' '.join(words[:8])

    q = urllib.parse.quote(short_q)
    url = f"{ARXIV_BASE}?search_query=all:{q}&start=0&max_results={max_results}"
    _rate_limit()
    for attempt in range(2):
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                xml_data = resp.read().decode()
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  [arXiv] 429 rate limited (attempt {attempt+1}/2)", flush=True)
                time.sleep(3)
                continue
            return []
        except Exception:
            return []
    else:
        return []

    import xml.etree.ElementTree as ET
    ns = {"a": "http://www.w3.org/2005/Atom",
          "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(xml_data)

    papers = []
    for entry in root.findall("a:entry", ns):
        paper_id = entry.find("a:id", ns).text.strip() if entry.find("a:id", ns) is not None else ""
        paper_id = paper_id.split("/")[-1].split("v")[0] if "abs/" in paper_id else paper_id
        title = entry.find("a:title", ns).text.strip().replace("\n", " ") if entry.find("a:title", ns) is not None else ""
        summary = entry.find("a:summary", ns).text.strip().replace("\n", " ")[:500] if entry.find("a:summary", ns) is not None else ""
        published = entry.find("a:published", ns).text[:10] if entry.find("a:published", ns) is not None else ""
        authors = []
        for author in entry.findall("a:author", ns):
            name = author.find("a:name", ns)
            if name is not None:
                authors.append(name.text)
        categories = []
        for cat in entry.findall("arxiv:primary_category", ns):
            cat_term = cat.get("term", "")
            if cat_term:
                categories.append(cat_term)
        link = ""
        for l in entry.findall("a:link", ns):
            if l.get("title") == "pdf":
                link = l.get("href", "")
                break
        papers.append({
            "arxiv_id": paper_id,
            "title": title,
            "abstract": summary,
            "published": published,
            "authors": authors[:5],
            "categories": categories,
            "url": link or f"https://arxiv.org/abs/{paper_id}",
        })
    return papers


def get_paper_metadata(arxiv_id: str) -> dict | None:
    """Get metadata for a specific arXiv paper by ID."""
    url = f"{ARXIV_BASE}?id_list={arxiv_id}"
    _rate_limit()
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            xml_data = resp.read().decode()
    except Exception:
        return None
    import xml.etree.ElementTree as ET
    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(xml_data)
    entry = root.find("a:entry", ns)
    if entry is None:
        return None
    return {
        "title": entry.find("a:title", ns).text.strip().replace("\n", " ") if entry.find("a:title", ns) is not None else "",
        "abstract": entry.find("a:summary", ns).text.strip().replace("\n", " ")[:500] if entry.find("a:summary", ns) is not None else "",
        "published": entry.find("a:published", ns).text[:10] if entry.find("a:published", ns) is not None else "",
    }


def enrich_entities(graph, query: str = "", max_results: int = 5) -> int:
    """Add arXiv papers as additional paper sources to the graph.

    Returns number of papers added.
    """
    if not query:
        return 0
    papers = search_papers(query, max_results)
    if not papers:
        return 0
    added = 0
    for p in papers:
        pmid = f"arxiv_{p['arxiv_id']}"
        if pmid not in graph.papers:
            graph.add_paper(pmid, p["title"], p["abstract"], p["url"], p.get("published", ""))
            added += 1
    return added
