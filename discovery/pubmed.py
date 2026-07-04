import json
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

_last_call = 0.0


def _rate_limit():
    global _last_call
    now = time.time()
    if now - _last_call < 0.35:
        time.sleep(0.35 - (now - _last_call))
    _last_call = time.time()


def _get_email() -> str:
    try:
        cfg = json.loads(
            (Path(__file__).resolve().parent.parent / "config" / "api_keys.json").read_text(encoding="utf-8-sig")
        )
        return cfg.get("ncbi_email", "rumi@research.ai")
    except Exception:
        return "rumi@research.ai"


def _fetch_with_retry(url: str, timeout: int = 30) -> bytes | None:
    """Fetch URL with exponential backoff retry."""
    for attempt in range(3):
        try:
            _rate_limit()
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                if attempt == 0:
                    print(f"  [PubMed] 429 rate limited, retrying in {wait}s...", flush=True)
                time.sleep(wait)
                continue
            return None
        except Exception:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            return None
    return None


def search(query: str, max_results: int = 20, retstart: int = 0) -> list[str]:
    params = urllib.parse.urlencode({
        "db": "pubmed", "term": query, "retmax": max_results,
        "retstart": retstart, "retmode": "json", "email": _get_email(),
    })
    data = _fetch_with_retry(f"{ESEARCH_URL}?{params}")
    if data is None:
        return []
    try:
        result = json.loads(data.decode())
        return result.get("esearchresult", {}).get("idlist", [])
    except Exception:
        return []


def fetch(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    params = urllib.parse.urlencode({
        "db": "pubmed", "id": ",".join(pmids),
        "retmode": "xml", "rettype": "abstract", "email": _get_email(),
    })
    data = _fetch_with_retry(f"{EFETCH_URL}?{params}")
    if data is None:
        return []
    xml_text = data.decode("utf-8", errors="replace")
    return _parse_xml_results(xml_text)


def _parse_xml_results(xml_text: str) -> list[dict]:
    results = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    for article in root.iter("PubmedArticle"):
        pmid_el = article.find(".//PMID")
        title_el = article.find(".//ArticleTitle")
        if pmid_el is None or title_el is None:
            continue

        pmid = pmid_el.text or ""
        title = "".join(title_el.itertext())

        abstract_parts = []
        for at in article.findall(".//AbstractText"):
            abstract_parts.append("".join(at.itertext()))
        abstract = " ".join(abstract_parts) if abstract_parts else "(No abstract available)"

        year = ""
        pub_date = article.find(".//PubDate")
        if pub_date is not None:
            y = pub_date.find("Year")
            if y is not None and y.text:
                year = y.text

        results.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "year": year,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })
    return results


def search_and_fetch(query: str, max_results: int = 20) -> list[dict]:
    pmids = search(query, max_results)
    if not pmids:
        return []
    time.sleep(0.5)
    return fetch(pmids)
