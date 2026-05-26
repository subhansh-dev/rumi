"""Novelty detection — compare hypotheses against PubMed literature."""

import json
import asyncio
from pathlib import Path
from discovery.hypothesis_memory import HypothesisMemory


class NoveltyDetector:
    def __init__(self, memory=None):
        self.memory = memory or HypothesisMemory()

    async def check(self, hypothesis, graph=None):
        title = hypothesis.get("title", "")
        description = hypothesis.get("description", "")
        keywords = self._extract_keywords(title, description, hypothesis.get("nodes", []))

        # Search PubMed for similar concepts
        similar_papers = await self._search_pubmed(keywords)
        in_pubmed = len(similar_papers) > 0

        # Calculate novelty probability
        if not similar_papers:
            probability = 0.9
        else:
            max_similarity = max(s.get("similarity", 0) for s in similar_papers)
            probability = max(0.0, 1.0 - max_similarity * 0.8)

        result = {
            "in_pubmed": in_pubmed,
            "similar_papers": similar_papers[:5],
            "novelty_probability": round(probability, 3),
            "assessment": "likely novel" if probability > 0.7 else "partially known" if probability > 0.3 else "likely known",
        }

        hid = hypothesis.get("id") if isinstance(hypothesis, dict) else None
        if hid:
            try:
                self.memory.save_novelty_check(hid, in_pubmed, similar_papers[:5], probability)
            except Exception:
                pass

        return result

    def _extract_keywords(self, title, description, nodes):
        words = set()
        for text in [title, description]:
            for w in text.lower().split():
                w = w.strip(",.!?;:()[]{}")
                if len(w) > 3 and w not in self._stopwords():
                    words.add(w)
        for n in nodes:
            name = n.get("name", "")
            for w in name.lower().split():
                w = w.strip(",.!?;:()[]{}")
                if len(w) > 3:
                    words.add(w)
        return list(words)[:15]

    async def _search_pubmed(self, keywords):
        try:
            from discovery.pubmed import search_and_fetch
            query = " ".join(keywords[:5])
            papers = search_and_fetch(query, max_results=5)
            results = []
            for p in papers:
                title = p.get("title", "")
                abstract = p.get("abstract", "")
                overlap = self._text_overlap(" ".join(keywords), title + " " + abstract[:500])
                results.append({
                    "pmid": p.get("pmid"),
                    "title": title,
                    "similarity": round(overlap, 3),
                    "url": p.get("url", ""),
                })
            return [r for r in results if r["similarity"] > 0.05]
        except Exception:
            return []

    def _text_overlap(self, keywords, text):
        kw_set = set(keywords.lower().split())
        txt_set = set(text.lower().split())
        if not kw_set or not txt_set:
            return 0.0
        return len(kw_set & txt_set) / len(kw_set)

    @staticmethod
    def _stopwords():
        return {"this", "that", "with", "from", "have", "been", "were", "would",
                "could", "should", "their", "there", "which", "what", "about",
                "into", "over", "such", "only", "than", "then", "also", "very",
                "just", "more", "these", "those", "through", "during", "before",
                "after", "between", "without", "within", "along", "among"}
