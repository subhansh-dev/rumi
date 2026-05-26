"""Novelty detection — compare hypotheses against PubMed literature with calibrated scoring."""

import json
import asyncio
import re
from pathlib import Path
from collections import Counter
from discovery.hypothesis_memory import HypothesisMemory


class NoveltyDetector:
    def __init__(self, memory=None):
        self.memory = memory or HypothesisMemory()

    async def check(self, hypothesis, graph=None):
        title = hypothesis.get("title", "")
        mechanistic_rationale = hypothesis.get("mechanistic_rationale", hypothesis.get("description", ""))
        supporting_evidence = hypothesis.get("supporting_evidence", hypothesis.get("evidence", []))
        contradictory_evidence = hypothesis.get("contradictory_evidence", [])
        alternative_explanations = hypothesis.get("alternative_explanations", [])
        nodes = hypothesis.get("nodes", [])

        # Extract keywords from title and rationale
        title_keywords = self._extract_keywords(title)
        rationale_keywords = self._extract_keywords(mechanistic_rationale)
        node_names = set()
        for n in nodes:
            name = n.get("name", "")
            for w in name.lower().split():
                w = w.strip(",.!?;:()[]{}")
                if len(w) > 3:
                    node_names.add(w)

        # Use entity names as primary keywords (more specific)
        primary_kw = list(node_names) if node_names else title_keywords
        secondary_kw = [w for w in rationale_keywords if w not in primary_kw]

        # Search PubMed with primary keywords
        similar_papers = await self._search_pubmed(primary_kw[:8], max_results=10)

        # Calculate literature overlap score
        in_pubmed = len(similar_papers) > 0
        literature_overlap = 0.0
        citation_weight = 0.0
        if similar_papers:
            similarities = [s.get("similarity", 0) for s in similar_papers]
            literature_overlap = max(similarities) if similarities else 0.0
            citation_weight = sum(s.get("citations", 0) for s in similar_papers if s.get("citations"))
            citation_weight = min(1.0, citation_weight / 100.0)

        # Calculate mechanistic redundancy — how many similar papers cover same mechanism
        if supporting_evidence:
            mech_overlap = self._mechanism_overlap(supporting_evidence, similar_papers)
        else:
            mech_overlap = 0.0

        # Final novelty probability: blend of multiple factors
        base_novelty = max(0.0, 1.0 - literature_overlap * 0.5 - citation_weight * 0.2 - mech_overlap * 0.3)
        capped = min(base_novelty, 0.85)  # Never exceed 0.85 — be conservative

        assessment = self._assess(capped, similar_papers)

        result = {
            "in_pubmed": in_pubmed,
            "similar_papers": similar_papers[:6],
            "literature_overlap": round(literature_overlap, 3),
            "citation_weight": round(citation_weight, 3),
            "mech_overlap": round(mech_overlap, 3),
            "novelty_probability": round(capped, 3),
            "assessment": assessment,
        }

        hid = hypothesis.get("id") if isinstance(hypothesis, dict) else None
        if hid:
            try:
                self.memory.save_novelty_check(hid, in_pubmed, similar_papers[:5], capped)
            except Exception:
                pass

        return result

    def _assess(self, probability, similar_papers):
        if probability > 0.7:
            return "possibly novel — check similar papers"
        elif probability > 0.4:
            return "partial overlap with existing literature"
        elif probability > 0.2:
            return "significant overlap — likely known"
        else:
            return "substantially known in literature"

    def _extract_keywords(self, text):
        tokens = re.findall(r'[A-Za-z][A-Za-z0-9_-]{2,}', text.lower())
        meaningful = [t for t in tokens if t not in self._stopwords()]
        return meaningful

    def _mechanism_overlap(self, evidence, similar_papers):
        if not evidence or not similar_papers:
            return 0.0
        all_evidence = " ".join(evidence).lower()
        all_paper_texts = []
        for p in similar_papers:
            title = p.get("title", "").lower()
            abstract = p.get("abstract", "").lower()
            all_paper_texts.append(title + " " + abstract[:500])
        if not all_paper_texts:
            return 0.0
        scores = []
        for text in all_paper_texts:
            kw_set = set(self._extract_keywords(all_evidence))
            txt_set = set(self._extract_keywords(text))
            if not kw_set or not txt_set:
                continue
            jaccard = len(kw_set & txt_set) / len(kw_set | txt_set)
            scores.append(jaccard)
        return max(scores) if scores else 0.0

    async def _search_pubmed(self, keywords, max_results=10):
        try:
            from discovery.pubmed import search_and_fetch
            query = " ".join(keywords[:5])
            papers = search_and_fetch(query, max_results=max_results)
            results = []
            for p in papers:
                title = p.get("title", "")
                abstract = p.get("abstract", "")
                overlap = self._text_overlap(" ".join(keywords), title + " " + abstract[:500])
                results.append({
                    "pmid": p.get("pmid"),
                    "title": title,
                    "abstract": abstract[:300],
                    "similarity": round(overlap, 3),
                    "citations": p.get("citations", 0),
                    "year": p.get("year", ""),
                    "url": p.get("url", ""),
                })
            return [r for r in results if r["similarity"] > 0.05]
        except Exception as e:
            return []

    def _text_overlap(self, keywords, text):
        kw_set = set(keywords.lower().split())
        txt_set = set(text.lower().split())
        if not kw_set or not txt_set:
            return 0.0
        jaccard = len(kw_set & txt_set) / len(kw_set | txt_set)
        return jaccard

    @staticmethod
    def _stopwords():
        return {"this", "that", "with", "from", "have", "been", "were", "would",
                "could", "should", "their", "there", "which", "what", "about",
                "into", "over", "such", "only", "than", "then", "also", "very",
                "just", "more", "these", "those", "through", "during", "before",
                "after", "between", "without", "within", "along", "among",
                "might", "may", "can", "will", "has", "had", "did", "does",
                "does", "been", "being", "some", "any", "each", "every",
                "both", "most", "few", "much", "many", "still", "even",
                "well", "back", "here", "there", "where", "when", "how",
                "because", "while", "since", "until", "upon", "yet"}
