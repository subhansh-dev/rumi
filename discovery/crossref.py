"""CrossRef API — free, no key needed.

Fourth paper source for RUMI. Covers all academic disciplines.
Rate limit: 50 req/sec with polite pool (mailto header).
"""

import json
import re
import time
import urllib.request
import urllib.parse

CROSSREF_BASE = "https://api.crossref.org/works"
_LAST_CALL = 0.0


def _rate_limit():
    global _LAST_CALL
    now = time.time()
    if now - _LAST_CALL < 0.5:
        time.sleep(0.5 - (now - _LAST_CALL))
    _LAST_CALL = time.time()


def search_papers(query: str, max_results: int = 20) -> list[dict]:
    """Search CrossRef for papers. Returns list of paper dicts."""
    q = urllib.parse.quote(query)
    url = f"{CROSSREF_BASE}?query={q}&rows={max_results}&mailto=subhansh.dev@gmail.com&sort=relevance&order=desc"
    _rate_limit()
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "RUMI/1.0 (mailto:subhansh.dev@gmail.com)"
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"  [CrossRef] 429 rate limited (attempt {attempt+1}/2)", flush=True)
                time.sleep(3)
                continue
            return []
        except Exception:
            return []

        papers = []
        for item in data.get("message", {}).get("items", []):
            title_list = item.get("title", [])
            title = title_list[0] if title_list else ""
            if not title:
                continue
            abstract = item.get("abstract", "")[:500]
            abstract = re.sub(r'<[^>]+>', '', abstract)
            authors = []
            for a in item.get("author", [])[:5]:
                name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                if name:
                    authors.append(name)
            year = ""
            pub_date = item.get("published-print", item.get("published-online", {}))
            if pub_date:
                dp = pub_date.get("date-parts", [[]])
                if dp and dp[0]:
                    year = str(dp[0][0])
            doi = item.get("DOI", "")
            url_link = f"https://doi.org/{doi}" if doi else ""
            papers.append({
                "title": title.strip(),
                "abstract": abstract,
                "authors": authors,
                "year": year,
                "url": url_link,
                "doi": doi,
                "citation_count": item.get("is-referenced-by-count", 0),
            })
        return papers
    return []
