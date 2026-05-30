"""Semantic relevance filtering for PubMed search results."""

import re
import json
from collections import Counter
from discovery.groq_client import call as groq_call


class RetrievalFilter:
    def __init__(self):
        self.relevance_threshold = 0.3

    def filter(self, papers, topic, domain="general", min_papers=5, max_papers=12):
        if not papers:
            return []

        domain_keywords = self._domain_keywords(domain)
        expanded_terms = self._expand_query(topic, domain_keywords)
        scored = self._score_papers(papers, topic, expanded_terms)
        scored.sort(key=lambda x: x["score"], reverse=True)

        # Batch LLM relevance check for borderline papers
        top = [p for p in scored if p["score"] >= self.relevance_threshold]
        borderline = [p for p in scored if p["score"] < self.relevance_threshold and p["score"] >= 0.15]

        if borderline and len(top) < max_papers:
            llm_scored = self._llm_relevance_check(borderline, topic, domain)
            top.extend(llm_scored)

        top.sort(key=lambda x: x["score"], reverse=True)
        top = top[:max_papers]

        if len(top) < min_papers:
            top = scored[:min_papers]

        result = []
        seen = set()
        for item in top:
            p = item["paper"]
            if p["pmid"] not in seen:
                result.append(p)
                seen.add(p["pmid"])

        return result

    def snowball_expand(self, papers, topic, domain="general", max_extra=5):
        """Snowball sampling: extract key terms from initial results, search for more papers.

        Real scientists expand their search by following citation chains and
        discovering related terminology. This method extracts the most specific
        terms from top papers and does a supplementary search.
        """
        if not papers or len(papers) < 2:
            return []

        # Extract key terms from top paper titles and abstracts
        all_text = " ".join(
            f"{p.get('title', '')} {p.get('abstract', '')[:500]}"
            for p in papers[:5]
        )
        words = re.findall(r'\b[A-Z][A-Za-z]+(?:\s+[A-Za-z]+)*\b', all_text)
        word_freq = Counter(words)
        # Take most common specific terms (skip generic words)
        skip = {'The', 'This', 'These', 'That', 'With', 'From', 'However', 'Although',
                'Using', 'Based', 'Among', 'Despite', 'Recent', 'Previous', 'Various',
                'Different', 'Specific', 'New', 'Novel', 'Study', 'Results', 'Methods'}
        key_terms = [w for w, c in word_freq.most_common(20) if w not in skip and c >= 2]

        if not key_terms:
            return []

        # Do supplementary search with combined key terms
        try:
            from discovery.pubmed import search_and_fetch
            extra_query = " ".join(key_terms[:4])
            extra_papers = search_and_fetch(extra_query, max_results=10)
            if not extra_papers:
                return []

            # Score and filter
            domain_keywords = self._domain_keywords(domain)
            expanded_terms = self._expand_query(topic, domain_keywords)
            scored = self._score_papers(extra_papers, topic, expanded_terms)
            scored.sort(key=lambda x: x["score"], reverse=True)

            # Deduplicate against existing papers
            existing_pmids = {p.get("pmid", "") for p in papers}
            result = []
            for item in scored:
                p = item["paper"]
                if p.get("pmid", "") not in existing_pmids and p.get("pmid", ""):
                    result.append(p)
                    if len(result) >= max_extra:
                        break
            return result
        except Exception:
            return []

    def _domain_keywords(self, domain):
        keywords = {
            "drug_discovery": ["clinical", "therapeutic", "inhibitor", "drug", "treatment",
                               "patient", "mutation", "cancer", "pathway", "mechanism",
                               "kinase", "receptor", "antibody", "molecular", "cellular"],
            "materials_science": ["synthesis", "fabrication", "nanoparticle", "composite",
                                  "catalyst", "bandgap", "conductivity", "polymer", "alloy",
                                  "thin film", "crystal", "dopant", "photovoltaic"],
            "neuroscience": ["neuron", "synapse", "brain", "cortex", "neurotransmitter",
                             "plasticity", "axon", "dendrite", "neural circuit",
                             "hippocampus", "cognition", "memory", "behavioral"],
            "molecular_biology": ["gene", "protein", "transcription", "expression",
                                  "rna", "dna", "chromatin", "epigenetic", "ribosome",
                                  "genome", "proteome", "signaling", "knockout"],
            "climate_energy": ["climate", "emission", "renewable", "solar", "carbon",
                               "temperature", "atmospheric", "energy", "battery",
                               "photovoltaic", "wind", "greenhouse", "warming"],
            "space_astronomy": ["exoplanet", "stellar", "galaxy", "telescope", "spectrum",
                                "atmosphere", "biosignature", "radiation", "orbital",
                                "spectroscopy", "planet", "star", "cosmic", "nebula",
                                "astrobiology", "photochemical", "spectral"],
            "ecology": ["species", "biodiversity", "ecosystem", "habitat", "population",
                        "conservation", "predator", "prey", "migration", "foraging",
                        "evolutionary", "ecological", "biome"],
            "physics": ["quantum", "particle", "field", "gravitational", "electromagnetic",
                        "photon", "electron", "nuclear", "relativity", "thermodynamic",
                        "wave", "entropy", "momentum"],
            "computer_science": ["algorithm", "neural", "learning", "optimization",
                                 "computation", "data", "network", "classification",
                                 "processing", "architecture", "model"],
            "earth_science": ["geology", "tectonic", "sediment", "volcanic", "erosion",
                              "mineral", "fossil", "stratigraphy", "seismic", "crust",
                              "mantle", "geochemical"],
            "oceanography": ["ocean", "current", "salinity", "temperature", "marine",
                             "tide", "wave", "circulation", "phytoplankton", "upwelling",
                             "sea level", "acidification"],
            "economics": ["market", "gdp", "inflation", "trade", "employment",
                          "consumption", "production", "fiscal", "monetary", "growth",
                          "price", "supply", "demand", "investment"],
            "public_health": ["epidemiology", "prevalence", "mortality", "morbidity",
                              "vaccine", "infection", "prevention", "screening",
                              "outbreak", "surveillance", "risk factor", "intervention"],
            "mathematics": ["theorem", "proof", "function", "equation", "topology",
                            "algebra", "geometry", "calculus", "differential",
                            "probability", "statistics", "conjecture"],
            "social_science": ["behavior", "society", "culture", "survey", "demographic",
                               "policy", "attitude", "social", "economic", "political",
                               "psychology", "sociology"],
            "chemistry": ["reaction", "catalyst", "molecule", "bond", "synthesis",
                          "oxidation", "reduction", "ligand", "complex", "isomer",
                          "polymer", "organic", "inorganic", "spectroscopy"],
        }
        return keywords.get(domain, [])

    def _expand_query(self, topic, domain_keywords):
        """Generate expanded search terms using keyword overlap."""
        topic_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', topic.lower()))
        expanded = set(topic_words)
        for kw in domain_keywords:
            if any(w in kw for w in topic_words) or any(w in topic_words for w in kw.split()):
                expanded.add(kw)
        return list(expanded)

    def _score_papers(self, papers, topic, expanded_terms):
        topic_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', topic.lower()))
        scored = []
        for p in papers:
            title = p.get("title", "").lower()
            abstract = (p.get("abstract", "") or "").lower()
            text = title + " " + abstract

            # Topic term overlap
            title_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', title))
            topic_overlap = len(topic_words & title_words) / max(len(topic_words), 1)

            # Domain keyword density
            kw_count = sum(1 for kw in expanded_terms if kw.lower() in text)
            kw_density = min(1.0, kw_count / 20.0)

            # Title relevance (exact phrase match)
            phrase_bonus = 0.2 if any(phrase.lower() in title for phrase in topic.split()) else 0.0

            score = topic_overlap * 0.5 + kw_density * 0.3 + phrase_bonus
            scored.append({"paper": p, "score": round(score, 3)})
        return scored

    def _llm_relevance_check(self, candidates, topic, domain):
        """Use LLM to check relevance of borderline papers."""
        if not candidates:
            return []

        batch = candidates[:8]
        prompt = f"""You are a relevance judge for scientific literature retrieval.

Topic: {topic}
Domain: {domain}

Rate each paper's relevance to the SPECIFIC topic (NOT just the general domain).
Output JSON array of objects with "pmid", "relevant" (true/false), "score" (0.0-1.0):

"""
        for item in batch:
            p = item["paper"]
            prompt += f"--- Paper ---\nPMID: {p['pmid']}\nTitle: {p['title']}\nAbstract: {p.get('abstract','')[:300]}\n\n"

        prompt += 'Output: [{"pmid": "...", "relevant": true, "score": 0.0-1.0}]'

        result = groq_call(prompt, json_mode=True, max_tokens=4096)
        if not result:
            return []

        try:
            if result.startswith("```"):
                result = result.split("\n", 1)[1] if "\n" in result else result[3:]
                result = result.rsplit("```", 1)[0].strip()
            judgments = json.loads(result)
            if not isinstance(judgments, list):
                return []
        except (json.JSONDecodeError, TypeError):
            return []

        pmid_map = {item["paper"]["pmid"]: item for item in candidates}
        filtered = []
        for j in judgments:
            pmid = j.get("pmid")
            if pmid in pmid_map and j.get("relevant", False):
                item = pmid_map[pmid]
                item["score"] = max(item["score"], j.get("score", 0.3))
                filtered.append(item)
        return filtered
