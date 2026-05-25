import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _get_email() -> str:
    try:
        cfg = json.loads(
            (Path(__file__).resolve().parent.parent / "config" / "api_keys.json").read_text(encoding="utf-8-sig")
        )
        return cfg.get("ncbi_email", "rumi@research.ai")
    except Exception:
        return "rumi@research.ai"


def search(query: str, max_results: int = 20, retstart: int = 0) -> list[str]:
    params = urllib.parse.urlencode({
        "db": "pubmed", "term": query, "retmax": max_results,
        "retstart": retstart, "retmode": "json", "email": _get_email(),
    })
    try:
        with urllib.request.urlopen(f"{ESEARCH_URL}?{params}", timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data.get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        print(f"[PubMed ERROR] search failed: {e}")
        return []


def fetch(pmids: list[str]) -> list[dict]:
    if not pmids:
        return []
    params = urllib.parse.urlencode({
        "db": "pubmed", "id": ",".join(pmids),
        "retmode": "xml", "rettype": "abstract", "email": _get_email(),
    })
    try:
        with urllib.request.urlopen(f"{EFETCH_URL}?{params}", timeout=30) as resp:
            xml_data = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[PubMed ERROR] fetch failed: {e}")
        return []
    return _parse_xml_results(xml_data)


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
    time.sleep(1)
    return fetch(pmids)
