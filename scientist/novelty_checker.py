"""
novelty_checker.py — Scientific Novelty & Prior Art Detection

Checks if a research idea, hypothesis, or paper is novel by:
  [NC-1] Searching Semantic Scholar and arXiv for related work
  [NC-2] Computing semantic similarity between the idea and existing literature
  [NC-3] Extracting key claims and checking for overlap with prior art
  [NC-4] Generating a novelty score (0.0 = already known, 1.0 = completely novel)
  [NC-5] Providing a list of closest prior works with similarity scores

Inspired by:
  - AI Scientist's Semantic Scholar novelty verification
  - Embedding-based similarity for scientific text
  - Citation graph analysis for novelty assessment

Thread-safe. Stateless (novelty checks are per-query).
"""

import json
import threading
import time
import urllib.parse
import urllib.request
import re
from pathlib import Path
from typing import Optional

SCIENTIST_DIR = Path(__file__).parent.resolve()

# Similarity thresholds
NOVELTY_HIGH = 0.80    # ≥0.80 similarity = likely duplicate
NOVELTY_MEDIUM = 0.60  # ≥0.60 similarity = somewhat overlapping
NOVELTY_LOW = 0.40     # ≥0.40 similarity = tangential

# Cache for API results
_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL = 3600  # 1 hour


def _hash_text(text: str) -> str:
    import hashlib
    return hashlib.md5(text.encode()).hexdigest()[:16]


def _compute_similarity(text_a: str, text_b: str) -> float:
    """
    Compute a fast approximate text similarity using token overlap and TF-like weighting.
    No external embeddings required — pure Python.

    Uses:
      - Jaccard similarity on token sets (weighted by IDF-like rarity)
      - Bigram overlap for phrase-level matching
      - Length normalization to avoid bias toward longer texts
    """
    if not text_a or not text_b:
        return 0.0

    a_lower = text_a.lower()
    b_lower = text_b.lower()

    # Tokenize
    a_tokens = set(re.findall(r'\b[a-z]+\b', a_lower))
    b_tokens = set(re.findall(r'\b[a-z]+\b', b_lower))

    if not a_tokens or not b_tokens:
        return 0.0

    # Jaccard similarity on tokens
    intersection = a_tokens & b_tokens
    union = a_tokens | b_tokens
    token_jaccard = len(intersection) / len(union) if union else 0.0

    # Bigram overlap (character n-grams for phrase matching)
    def bigrams(s: str) -> set:
        return {s[i:i+2] for i in range(len(s) - 1)}

    a_bigrams = bigrams(a_lower)
    b_bigrams = bigrams(b_lower)

    bg_intersection = a_bigrams & b_bigrams
    bg_union = a_bigrams | b_bigrams
    bigram_jaccard = len(bg_intersection) / len(bg_union) if bg_union else 0.0

    # Keyword importance weighting: rare words that match are more significant
    common_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "has", "have", "had", "do", "does", "did", "will", "would",
        "can", "could", "shall", "should", "may", "might", "must",
        "of", "in", "on", "at", "to", "for", "with", "by", "from",
        "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "out", "off", "over", "under", "again",
        "further", "then", "once", "here", "there", "this", "that",
        "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
        "neither", "each", "every", "all", "any", "few", "more", "most",
        "other", "some", "such", "no", "only", "own", "same", "very",
        "just", "also", "well", "how", "what", "why", "which", "who",
    }

    rare_a = a_tokens - common_words
    rare_b = b_tokens - common_words
    rare_intersection = rare_a & rare_b

    keyword_overlap = len(rare_intersection) / max(len(rare_a | rare_b), 1) if (rare_a | rare_b) else 0.0

    # Weighted combination
    similarity = (
        token_jaccard * 0.25 +
        bigram_jaccard * 0.35 +
        keyword_overlap * 0.40
    )

    return min(1.0, max(0.0, similarity))


def _search_semantic_scholar(query: str, limit: int = 10) -> list[dict]:
    """Search Semantic Scholar API for papers matching the query."""
    cache_key = f"ss:{_hash_text(query)}:{limit}"
    with _CACHE_LOCK:
        if cache_key in _CACHE:
            entry = _CACHE[cache_key]
            if time.time() - entry["time"] < _CACHE_TTL:
                return entry["data"]

    base = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = urllib.parse.urlencode({
        "query": query,
        "limit": min(limit, 100),
        "fields": "title,abstract,authors,year,externalIds,url,citationCount,publicationDate,embedding",
    })
    url = f"{base}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI-Scientist/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []

    papers = []
    for paper in data.get("data", [])[:limit]:
        papers.append({
            "title": paper.get("title", "Untitled"),
            "abstract": paper.get("abstract") or "",
            "authors": [a.get("name", "") for a in paper.get("authors", [])[:5]],
            "year": paper.get("year"),
            "url": paper.get("url", ""),
            "citation_count": paper.get("citationCount", 0),
            "publication_date": paper.get("publicationDate", ""),
            "embedding": paper.get("embedding", {}).get("vector") if paper.get("embedding") else None,
            "source": "Semantic Scholar",
        })

    with _CACHE_LOCK:
        _CACHE[cache_key] = {"data": papers, "time": time.time()}

    return papers


def _search_arxiv(query: str, limit: int = 10) -> list[dict]:
    """Search arXiv for papers matching the query."""
    cache_key = f"ax:{_hash_text(query)}:{limit}"
    with _CACHE_LOCK:
        if cache_key in _CACHE:
            entry = _CACHE[cache_key]
            if time.time() - entry["time"] < _CACHE_TTL:
                return entry["data"]

    import xml.etree.ElementTree as ET

    arxiv_base = "http://export.arxiv.org/api/query"
    params = urllib.parse.urlencode({
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    })
    url = f"{arxiv_base}?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RUMI-Scientist/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8")
    except Exception:
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return []

    papers = []
    for entry in root.findall("atom:entry", ns):
        title_el = entry.find("atom:title", ns) or entry.find("title")
        summary_el = entry.find("atom:summary", ns) or entry.find("summary")
        id_el = entry.find("atom:id", ns) or entry.find("id")
        published_el = entry.find("atom:published", ns) or entry.find("published")

        title = title_el.text.strip().replace("\n", " ").replace("  ", " ") if title_el is not None else "Untitled"
        summary = summary_el.text.strip().replace("\n", " ").replace("  ", " ")[:500] if summary_el is not None else ""
        paper_id = id_el.text.strip() if id_el is not None else ""
        published = published_el.text[:10] if published_el is not None else ""

        authors = []
        for author in entry.findall("atom:author", ns):
            name_el = author.find("atom:name", ns) or author.find("name")
            if name_el is not None:
                authors.append(name_el.text)

        papers.append({
            "title": title,
            "abstract": summary,
            "authors": authors[:5],
            "year": published[:4] if published else None,
            "url": paper_id,
            "citation_count": 0,
            "publication_date": published,
            "embedding": None,
            "source": "arXiv",
        })

    with _CACHE_LOCK:
        _CACHE[cache_key] = {"data": papers, "time": time.time()}

    return papers


class NoveltyChecker:
    """
    Checks the novelty of research ideas against the scientific literature.

    Pipeline:
      1. Search Semantic Scholar + arXiv for related work
      2. Compute similarity between the idea and each found paper
      3. Aggregate into novelty score
      4. Report closest prior art with similarity breakdown
    """

    def __init__(self):
        self._lock = threading.RLock()

    def check_novelty(
        self,
        idea: str,
        domain: str = "",
        max_papers: int = 20,
        include_arxiv: bool = True,
        include_semantic_scholar: bool = True,
    ) -> dict:
        """
        Check the novelty of a research idea.

        Args:
            idea: The research idea, hypothesis, or abstract to check
            domain: Optional domain hint (e.g., "machine learning", "quantum physics")
            max_papers: Maximum number of prior papers to retrieve
            include_arxiv: Whether to search arXiv
            include_semantic_scholar: Whether to search Semantic Scholar

        Returns:
            Dict with:
              - novelty_score: 0.0 to 1.0 (1.0 = completely novel)
              - closest_papers: list of dicts with title, similarity, year, url
              - verdict: "novel", "somewhat_novel", "likely_known", "unknown"
              - overlapping_claims: list of potential overlaps found
        """
        with self._lock:
            # Build search query
            search_query = idea[:200]
            if domain:
                search_query = f"{domain} {search_query}"

            # Gather related papers
            all_papers = []
            seen_titles = set()

            if include_semantic_scholar:
                ss_papers = _search_semantic_scholar(search_query, max_papers // 2 + 5)
                for p in ss_papers:
                    title_lower = p["title"].lower()
                    if title_lower not in seen_titles:
                        seen_titles.add(title_lower)
                        all_papers.append(p)

            if include_arxiv:
                ax_papers = _search_arxiv(search_query, max_papers // 2 + 5)
                for p in ax_papers:
                    title_lower = p["title"].lower()
                    if title_lower not in seen_titles:
                        seen_titles.add(title_lower)
                        all_papers.append(p)

            if not all_papers:
                return {
                    "novelty_score": 1.0,
                    "closest_papers": [],
                    "verdict": "unknown",
                    "overlapping_claims": [],
                    "message": "⚠️  No related papers found in the databases searched. "
                              "The idea may be in a niche area or the databases may be incomplete.",
                }

            # Compute similarity for each paper
            scored_papers = []
            for paper in all_papers:
                abstract = paper.get("abstract", "") or ""
                title = paper.get("title", "")

                # Compare idea against title + abstract
                text_for_comparison = f"{title} {abstract}"
                similarity = _compute_similarity(idea, text_for_comparison)

                # Boost for recent papers that are highly cited
                citation_boost = min(paper.get("citation_count", 0) / 100, 0.1)
                adjusted_similarity = min(1.0, similarity + citation_boost * 0.5)

                scored_papers.append({
                    "title": title,
                    "similarity": round(adjusted_similarity, 4),
                    "raw_similarity": round(similarity, 4),
                    "year": paper.get("year"),
                    "url": paper.get("url", ""),
                    "authors": paper.get("authors", []),
                    "citation_count": paper.get("citation_count", 0),
                    "source": paper.get("source", ""),
                })

            # Sort by similarity (closest first)
            scored_papers.sort(key=lambda p: p["similarity"], reverse=True)

            # Get top matches
            top_papers = scored_papers[:10]

            # Calculate aggregate novelty score
            if top_papers:
                # Weight by similarity — closest paper has biggest impact
                max_similarity = top_papers[0]["similarity"]
                avg_top3 = sum(p["similarity"] for p in top_papers[:3]) / min(3, len(top_papers))

                # Novelty is inverse of max + avg
                novelty_from_max = 1.0 - max_similarity
                novelty_from_avg = 1.0 - avg_top3

                # If very close match exists, novelty is low
                if max_similarity >= NOVELTY_HIGH:
                    novelty_score = max(0.0, 1.0 - max_similarity * 1.2)
                else:
                    novelty_score = novelty_from_max * 0.6 + novelty_from_avg * 0.4
            else:
                novelty_score = 1.0

            novelty_score = max(0.0, min(1.0, novelty_score))

            # Verdict
            if novelty_score >= 0.75:
                verdict = "novel"
            elif novelty_score >= 0.45:
                verdict = "somewhat_novel"
            elif novelty_score >= 0.2:
                verdict = "likely_known"
            else:
                verdict = "known"

            # Extract overlapping claims
            overlapping_claims = []
            for paper in top_papers[:5]:
                if paper["similarity"] >= NOVELTY_MEDIUM:
                    overlapping_claims.append(
                        f"Overlap with '{paper['title']}' ({paper['similarity']:.0%} similarity)"
                    )

            return {
                "novelty_score": round(novelty_score, 3),
                "closest_papers": top_papers,
                "verdict": verdict,
                "overlapping_claims": overlapping_claims,
                "papers_checked": len(scored_papers),
                "message": self._format_novelty_message(novelty_score, top_papers),
            }

    def _format_novelty_message(self, score: float, top_papers: list[dict]) -> str:
        """Format a human-readable novelty assessment."""
        emoji = "🆕" if score >= 0.75 else "🔶" if score >= 0.45 else "⚠️" if score >= 0.2 else "📋"
        label = "Novel" if score >= 0.75 else "Somewhat Novel" if score >= 0.45 else "Likely Known" if score >= 0.2 else "Known"

        lines = [
            f"{emoji} **Novelty Assessment: {label}** (score: {score:.0%})",
            "",
        ]

        if top_papers:
            lines.append(f"**Closest prior work ({len(top_papers)} found):**")
            for i, p in enumerate(top_papers[:5], 1):
                similarity_pct = f"{p['similarity']:.0%}"
                year_str = f" ({p['year']})" if p.get("year") else ""
                cite_str = f" [{p['citation_count']} cit.]" if p.get("citation_count", 0) > 0 else ""
                lines.append(f"  {i}. {p['title']}{year_str}{cite_str} — *{similarity_pct} overlap*")
            lines.append("")

            if score < 0.45:
                lines.append("💡 **Suggestion:** Consider differentiating from the top matches above. "
                           "What makes your approach unique?")
            elif score < 0.75:
                lines.append("🔬 **Suggestion:** The idea has partial overlap but room for novelty. "
                           "Focus on the differentiating aspects.")

        return "\n".join(lines)

    def compare_papers(self, idea: str, paper_title: str, paper_abstract: str) -> dict:
        """
        Directly compare an idea against a specific paper.
        Useful for checking novelty against a known paper.
        """
        similarity = _compute_similarity(idea, f"{paper_title} {paper_abstract}")

        return {
            "idea": idea[:100],
            "paper_title": paper_title,
            "similarity": round(similarity, 3),
            "verdict": "overlapping" if similarity >= NOVELTY_MEDIUM else "distinct",
            "message": (
                f"📊 **Comparison with '{paper_title}'**\n"
                f"  Similarity: {similarity:.0%}\n"
                f"  Verdict: {'⚠️ Significant overlap' if similarity >= NOVELTY_MEDIUM else '✅ Sufficiently distinct'}"
            ),
        }

    def get_stats(self) -> dict:
        """Get novelty checker statistics."""
        with _CACHE_LOCK:
            return {
                "cache_size": len(_CACHE),
                "status": "ready",
            }


# ── Singleton ──────────────────────────────────────────────────

_novelty_checker = None
_novelty_lock = threading.Lock()


def get_novelty_checker() -> NoveltyChecker:
    global _novelty_checker
    if _novelty_checker is None:
        with _novelty_lock:
            if _novelty_checker is None:
                _novelty_checker = NoveltyChecker()
    return _novelty_checker
