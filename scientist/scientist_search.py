"""
scientist_search.py — Researcher-Focused Paper Search Engine (Enhanced)

Searches for academic papers from famous/seminal researchers.
Bridges the existing actions/paper_search.py with the Scientist AI pipeline.

Capabilities:
  [SS-1] Search by famous researcher name (Feynman, Einstein, Turing, etc.)
  [SS-2] Combined topic + author search
  [SS-3] Find seminal/highly-cited papers
  [SS-4] Citation graph and impact analysis
  [SS-5] Researcher biography and context
  [SS-6] Paper ingestion for downstream analysis
  [SS-7] Research timeline (chronological ordering)
  [SS-8] BibTeX export for papers
  [SS-9] Impact scoring by field
  [SS-10] Cross-field researcher discovery
  [SS-11] Trend extraction from search results

Thread-safe.
"""

import json
import re
import threading
from collections import Counter
from datetime import datetime
from typing import Optional

# ── Famous Researcher Database ──────────────────────────────────

FAMOUS_RESEARCHERS = {
    # ── Physics ────────────────────────────────────────────────
    "richard feynman": {
        "name": "Richard Feynman",
        "field": "Physics",
        "era": "20th century",
        "known_for": "Quantum electrodynamics, Feynman diagrams, path integral formulation",
        "seminal_papers": [
            ("Space-Time Approach to Quantum Electrodynamics", 1949),
            ("The Theory of Positrons", 1949),
            ("Mathematical Formulation of the Quantum Theory of Electromagnetic Interaction", 1950),
        ],
        "aliases": ["feynman", "r p feynman", "richard p feynman", "richard feynman"],
        "impact_score": 95,
    },
    "albert einstein": {
        "name": "Albert Einstein",
        "field": "Physics",
        "era": "20th century",
        "known_for": "Theory of relativity, photoelectric effect, E=mc\u00b2",
        "seminal_papers": [
            ("Zur Elektrodynamik bewegter K\u00f6rper (On the Electrodynamics of Moving Bodies)", 1905),
            ("Ist die Tr\u00e4gheit eines K\u00f6rpers von seinem Energieinhalt abh\u00e4ngig?", 1905),
            ("Die Grundlage der allgemeinen Relativit\u00e4tstheorie", 1916),
        ],
        "aliases": ["einstein", "a einstein", "albert einstein"],
        "impact_score": 99,
    },
    "isaac newton": {
        "name": "Isaac Newton",
        "field": "Physics / Mathematics",
        "era": "17th century",
        "known_for": "Newtonian mechanics, calculus, law of gravitation",
        "seminal_papers": [
            ("Philosophi\u00e6 Naturalis Principia Mathematica", 1687),
            ("Opticks", 1704),
            ("De analysi per aequationes numero terminorum infinitas", 1669),
        ],
        "aliases": ["newton", "isaac newton", "i newton", "sir isaac newton"],
        "impact_score": 99,
    },
    "stephen hawking": {
        "name": "Stephen Hawking",
        "field": "Physics",
        "era": "20th-21st century",
        "known_for": "Black hole radiation (Hawking radiation), cosmology",
        "seminal_papers": [
            ("Black hole explosions", 1974),
            ("Particle creation by black holes", 1975),
            ("The large-scale structure of space-time", 1973),
        ],
        "aliases": ["hawking", "stephen hawking", "s hawking"],
        "impact_score": 90,
    },
    "max planck": {
        "name": "Max Planck",
        "field": "Physics",
        "era": "19th-20th century",
        "known_for": "Quantum theory, Planck's constant",
        "seminal_papers": [
            ("Zur Theorie des Gesetzes der Energieverteilung im Normalspectrum", 1900),
            ("\u00dcber das Gesetz der Energieverteilung im Normalspectrum", 1900),
        ],
        "aliases": ["planck", "max planck", "m planck"],
        "impact_score": 93,
    },
    "nikola tesla": {
        "name": "Nikola Tesla",
        "field": "Physics / Engineering",
        "era": "19th-20th century",
        "known_for": "AC power system, Tesla coil, wireless transmission",
        "seminal_papers": [
            ("A New System of Alternating Current Motors and Transformers", 1888),
            ("The Problem of Increasing Human Energy", 1900),
            ("Experiments with Alternating Currents of Very High Frequency", 1891),
        ],
        "aliases": ["tesla", "nikola tesla", "n tesla"],
        "impact_score": 88,
    },
    "niels bohr": {
        "name": "Niels Bohr",
        "field": "Physics",
        "era": "20th century",
        "known_for": "Bohr model of the atom, complementarity principle, Copenhagen interpretation",
        "seminal_papers": [
            ("On the Constitution of Atoms and Molecules", 1913),
            ("The Quantum Postulate and the Recent Development of Atomic Theory", 1928),
            ("Can Quantum-Mechanical Description of Physical Reality Be Considered Complete?", 1935),
        ],
        "aliases": ["bohr", "niels bohr", "n bohr"],
        "impact_score": 94,
    },
    "werner heisenberg": {
        "name": "Werner Heisenberg",
        "field": "Physics",
        "era": "20th century",
        "known_for": "Uncertainty principle, matrix mechanics, quantum theory",
        "seminal_papers": [
            ("\u00dcber quantentheoretische Umdeutung kinematischer und mechanischer Beziehungen", 1925),
            ("\u00dcber den anschaulichen Inhalt der quantentheoretischen Kinematik und Mechanik", 1927),
        ],
        "aliases": ["heisenberg", "werner heisenberg", "w heisenberg"],
        "impact_score": 93,
    },
    "erwin schrodinger": {
        "name": "Erwin Schr\u00f6dinger",
        "field": "Physics",
        "era": "20th century",
        "known_for": "Schr\u00f6dinger equation, wave mechanics, Schr\u00f6dinger's cat",
        "seminal_papers": [
            ("Quantisierung als Eigenwertproblem (Schr\u00f6dinger equation)", 1926),
            ("Die gegenw\u00e4rtige Situation in der Quantenmechanik (Schr\u00f6dinger's cat)", 1935),
        ],
        "aliases": ["schrodinger", "erwin schrodinger", "e schrodinger"],
        "impact_score": 94,
    },
    "paul dirac": {
        "name": "Paul Dirac",
        "field": "Physics",
        "era": "20th century",
        "known_for": "Dirac equation, quantum electrodynamics, antimatter prediction",
        "seminal_papers": [
            ("The Quantum Theory of the Electron (Dirac equation)", 1928),
            ("Quantised Singularities in the Electromagnetic Field (magnetic monopoles)", 1931),
            ("The Principles of Quantum Mechanics", 1930),
        ],
        "aliases": ["dirac", "paul dirac", "p a m dirac", "p dirac"],
        "impact_score": 92,
    },
    "michael faraday": {
        "name": "Michael Faraday",
        "field": "Physics / Chemistry",
        "era": "19th century",
        "known_for": "Electromagnetic induction, electrolysis, field theory",
        "seminal_papers": [
            ("Experimental Researches in Electricity (electromagnetic induction)", 1831),
            ("On the Chemical History of a Candle", 1861),
            ("On the Physical Character of the Lines of Magnetic Force", 1852),
        ],
        "aliases": ["faraday", "michael faraday", "m faraday"],
        "impact_score": 95,
    },
    "james clerk maxwell": {
        "name": "James Clerk Maxwell",
        "field": "Physics",
        "era": "19th century",
        "known_for": "Maxwell's equations, electromagnetic theory, statistical mechanics",
        "seminal_papers": [
            ("A Dynamical Theory of the Electromagnetic Field (Maxwell's equations)", 1865),
            ("On Physical Lines of Force", 1861),
            ("On the Stability of the Motion of Saturn's Rings", 1859),
        ],
        "aliases": ["maxwell", "james clerk maxwell", "j c maxwell", "james maxwell"],
        "impact_score": 97,
    },
    # ── Chemistry / Biology ────────────────────────────────────
    "marie curie": {
        "name": "Marie Curie",
        "field": "Physics / Chemistry",
        "era": "19th-20th century",
        "known_for": "Radioactivity, polonium, radium",
        "seminal_papers": [
            ("Sur une substance nouvelle radio-active, contenue dans la pechblende", 1898),
            ("Sur le poids atomique du radium", 1902),
            ("Sur la radioactivit\u00e9 provoqu\u00e9e par les rayons de Becquerel", 1899),
        ],
        "aliases": ["curie", "marie curie", "m curie"],
        "impact_score": 93,
    },
    "linus pauling": {
        "name": "Linus Pauling",
        "field": "Chemistry",
        "era": "20th century",
        "known_for": "Chemical bonding, quantum chemistry, vitamin C",
        "seminal_papers": [
            ("The Nature of the Chemical Bond", 1939),
            ("A Theory of the Structure of Proteins", 1951),
            ("Molecular structure of nucleic acids", 1953),
        ],
        "aliases": ["pauling", "linus pauling", "l pauling"],
        "impact_score": 90,
    },
    "frances arnold": {
        "name": "Frances Arnold",
        "field": "Chemistry / Bioengineering",
        "era": "21st century",
        "known_for": "Directed evolution of enzymes",
        "seminal_papers": [
            ("Directed evolution of enzymes", 1993),
            ("Optimization of enzymes by directed evolution", 1996),
            ("Engineered enzymes for sustainable chemistry", 2018),
        ],
        "aliases": ["arnold", "frances arnold", "f arnold"],
        "impact_score": 87,
    },
    "rosalind franklin": {
        "name": "Rosalind Franklin",
        "field": "Chemistry / Biology",
        "era": "20th century",
        "known_for": "DNA structure (X-ray crystallography), Photo 51",
        "seminal_papers": [
            ("Molecular configuration in sodium thymonucleate", 1953),
            ("Structure of the DNA molecule", 1953),
        ],
        "aliases": ["franklin", "rosalind franklin", "r franklin"],
        "impact_score": 88,
    },
    "charles darwin": {
        "name": "Charles Darwin",
        "field": "Biology",
        "era": "19th century",
        "known_for": "Theory of evolution by natural selection, On the Origin of Species",
        "seminal_papers": [
            ("On the Origin of Species by Means of Natural Selection", 1859),
            ("The Descent of Man", 1871),
            ("On the Tendency of Species to form Varieties", 1858),
        ],
        "aliases": ["darwin", "charles darwin", "c darwin"],
        "impact_score": 98,
    },
    "gregor mendel": {
        "name": "Gregor Mendel",
        "field": "Biology / Genetics",
        "era": "19th century",
        "known_for": "Mendelian inheritance, laws of genetics",
        "seminal_papers": [
            ("Versuche \u00fcber Pflanzenhybriden (Experiments on Plant Hybridization)", 1866),
        ],
        "aliases": ["mendel", "gregor mendel", "g mendel"],
        "impact_score": 94,
    },
    "louis pasteur": {
        "name": "Louis Pasteur",
        "field": "Biology / Chemistry",
        "era": "19th century",
        "known_for": "Germ theory, pasteurization, vaccination (rabies, anthrax)",
        "seminal_papers": [
            ("M\u00e9moire sur les corpuscules organis\u00e9s qui existent dans l'atmosph\u00e8re", 1861),
            ("Sur les maladies virulentes et la vaccination (anthrax vaccine)", 1881),
            ("M\u00e9thode pour pr\u00e9venir la rage apr\u00e8s morsure", 1885),
        ],
        "aliases": ["pasteur", "louis pasteur", "l pasteur"],
        "impact_score": 95,
    },
    "barbara mcclintock": {
        "name": "Barbara McClintock",
        "field": "Biology / Genetics",
        "era": "20th century",
        "known_for": "Transposons (jumping genes), maize cytogenetics",
        "seminal_papers": [
            ("The Stability of Broken Ends of Chromosomes in Zea Mays", 1941),
            ("Induction of Instability at Selected Loci in Maize", 1950),
            ("Controlling Elements and the Gene", 1956),
        ],
        "aliases": ["mcclintock", "barbara mcclintock", "b mcclintock"],
        "impact_score": 89,
    },
    # ── Computer Science / Mathematics ─────────────────────────
    "alan turing": {
        "name": "Alan Turing",
        "field": "Computer Science",
        "era": "20th century",
        "known_for": "Turing machine, Enigma codebreaking, Turing test",
        "seminal_papers": [
            ("On Computable Numbers, with an Application to the Entscheidungsproblem", 1936),
            ("Computing Machinery and Intelligence", 1950),
            ("The Chemical Basis of Morphogenesis", 1952),
        ],
        "aliases": ["turing", "a m turing", "alan m turing", "alan turing"],
        "impact_score": 97,
    },
    "john von neumann": {
        "name": "John von Neumann",
        "field": "Mathematics / Computer Science",
        "era": "20th century",
        "known_for": "Von Neumann architecture, game theory, quantum mechanics",
        "seminal_papers": [
            ("First Draft of a Report on the EDVAC", 1945),
            ("Zur Theorie der Gesellschaftsspiele (Theory of Games)", 1928),
            ("Mathematical Foundations of Quantum Mechanics", 1932),
        ],
        "aliases": ["von neumann", "j von neumann", "john von neumann"],
        "impact_score": 95,
    },
    "geoffrey hinton": {
        "name": "Geoffrey Hinton",
        "field": "Computer Science / AI",
        "era": "21st century",
        "known_for": "Backpropagation, deep learning, neural networks",
        "seminal_papers": [
            ("Learning representations by back-propagating errors", 1986),
            ("A fast learning algorithm for deep belief nets", 2006),
            ("Reducing the dimensionality of data with neural networks", 2006),
        ],
        "aliases": ["hinton", "geoffrey hinton", "g hinton"],
        "impact_score": 96,
    },
    "yann lecun": {
        "name": "Yann LeCun",
        "field": "Computer Science / AI",
        "era": "21st century",
        "known_for": "Convolutional neural networks, deep learning",
        "seminal_papers": [
            ("Gradient-based learning applied to document recognition", 1998),
            ("Convolutional networks for images, speech, and time series", 2010),
            ("Deep learning (Nature 2015)", 2015),
        ],
        "aliases": ["lecun", "yann lecun", "y lecun"],
        "impact_score": 93,
    },
    "ada lovelace": {
        "name": "Ada Lovelace",
        "field": "Computer Science",
        "era": "19th century",
        "known_for": "First computer programmer, analytical engine",
        "seminal_papers": [
            ("Sketch of the Analytical Engine (notes)", 1843),
            ("Translation and notes on Menabrea's memoir", 1843),
        ],
        "aliases": ["lovelace", "ada lovelace", "ada king"],
        "impact_score": 90,
    },
    "grace hopper": {
        "name": "Grace Hopper",
        "field": "Computer Science",
        "era": "20th century",
        "known_for": "COBOL, compiler development, computer programming pioneer",
        "seminal_papers": [
            ("Compiling Routines", 1952),
            ("The Education of a Computer", 1952),
        ],
        "aliases": ["hopper", "grace hopper", "g hopper"],
        "impact_score": 87,
    },
    "norbert wiener": {
        "name": "Norbert Wiener",
        "field": "Mathematics / Cybernetics",
        "era": "20th century",
        "known_for": "Cybernetics, Wiener process, mathematical modeling",
        "seminal_papers": [
            ("Cybernetics: Or Control and Communication in the Animal and the Machine", 1948),
            ("The Human Use of Human Beings", 1950),
            ("Generalized harmonic analysis", 1930),
        ],
        "aliases": ["wiener", "norbert wiener", "n wiener"],
        "impact_score": 88,
    },
    "claude shannon": {
        "name": "Claude Shannon",
        "field": "Mathematics / Computer Science",
        "era": "20th century",
        "known_for": "Information theory, digital circuit design, entropy",
        "seminal_papers": [
            ("A Mathematical Theory of Communication", 1948),
            ("The Bandwagon (editorial on information theory)", 1956),
            ("Programming a Computer for Playing Chess", 1950),
        ],
        "aliases": ["shannon", "claude shannon", "c shannon"],
        "impact_score": 96,
    },
    "john nash": {
        "name": "John Nash",
        "field": "Mathematics / Economics",
        "era": "20th century",
        "known_for": "Nash equilibrium, game theory",
        "seminal_papers": [
            ("Equilibrium points in n-person games", 1950),
            ("The Bargaining Problem", 1950),
            ("Non-Cooperative Games", 1951),
        ],
        "aliases": ["nash", "john nash", "j nash", "john forbes nash"],
        "impact_score": 91,
    },
    "katherine johnson": {
        "name": "Katherine Johnson",
        "field": "Mathematics",
        "era": "20th century",
        "known_for": "NASA trajectory calculations, orbital mechanics",
        "seminal_papers": [
            ("Determination of Azimuth Angle at Burnout for Placing a Satellite Over a Selected Earth Position", 1960),
        ],
        "aliases": ["katherine johnson", "k johnson"],
        "impact_score": 84,
    },
    "carl friedrich gauss": {
        "name": "Carl Friedrich Gauss",
        "field": "Mathematics",
        "era": "18th-19th century",
        "known_for": "Number theory, Gaussian distribution, differential geometry, algebra",
        "seminal_papers": [
            ("Disquisitiones Arithmeticae", 1801),
            ("Theoria motus corporum coelestium (method of least squares)", 1809),
            ("Disquisitiones generales circa superficies curvas (differential geometry)", 1828),
        ],
        "aliases": ["gauss", "carl friedrich gauss", "c f gauss", "carl gauss"],
        "impact_score": 98,
    },
    "leonhard euler": {
        "name": "Leonhard Euler",
        "field": "Mathematics",
        "era": "18th century",
        "known_for": "Euler's identity, graph theory, calculus of variations, mechanics",
        "seminal_papers": [
            ("Solutio problematis ad geometriam situs pertinentis (Seven Bridges of K\u00f6nigsberg)", 1736),
            ("Introductio in analysin infinitorum", 1748),
            ("Mechanica sive motus scientia analytico exposita", 1736),
        ],
        "aliases": ["euler", "leonhard euler", "l euler"],
        "impact_score": 99,
    },
    "pierre de fermat": {
        "name": "Pierre de Fermat",
        "field": "Mathematics",
        "era": "17th century",
        "known_for": "Fermat's Last Theorem, Fermat's little theorem, analytic geometry",
        "seminal_papers": [
            ("Methodus ad disquirendam maximam et minimam (calculus)", 1638),
            ("Varia opera mathematica (incl. Fermat's Last Theorem note)", 1679),
        ],
        "aliases": ["fermat", "pierre de fermat", "p fermat"],
        "impact_score": 91,
    },
    "edwin hubble": {
        "name": "Edwin Hubble",
        "field": "Physics / Astronomy",
        "era": "20th century",
        "known_for": "Hubble's law, expanding universe, galaxy classification",
        "seminal_papers": [
            ("A Relation between Distance and Radial Velocity among Extra-Galactic Nebulae (Hubble's Law)", 1929),
            ("The Realm of the Nebulae", 1936),
        ],
        "aliases": ["hubble", "edwin hubble", "e hubble"],
        "impact_score": 91,
    },
}


# ── Fields mapping for cross-field discovery ────────────────────

FIELD_MAP = {
    "physics": {"related": ["mathematics", "astronomy", "engineering", "chemistry"]},
    "mathematics": {"related": ["physics", "computer science", "economics", "statistics"]},
    "computer science": {"related": ["mathematics", "engineering", "physics", "psychology"]},
    "chemistry": {"related": ["physics", "biology", "engineering", "materials science"]},
    "biology": {"related": ["chemistry", "genetics", "medicine", "psychology"]},
    "genetics": {"related": ["biology", "chemistry", "medicine"]},
    "engineering": {"related": ["physics", "computer science", "mathematics"]},
    "astronomy": {"related": ["physics", "mathematics"]},
    "cybernetics": {"related": ["mathematics", "computer science", "biology", "psychology"]},
    "economics": {"related": ["mathematics", "computer science", "psychology"]},
    "ai": {"related": ["computer science", "mathematics", "psychology", "biology"]},
    "bioengineering": {"related": ["biology", "chemistry", "engineering"]},
}


class ScientistSearch:
    """
    Researcher-focused paper search engine.
    Finds papers from famous scientists and provides context about their work.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._search_count = 0

    # ── Researcher Identification ──────────────────────────────

    def identify_researcher(self, name: str) -> Optional[dict]:
        """
        Identify a famous researcher by name (fuzzy match).

        Args:
            name: Name or partial name of a researcher

        Returns:
            Dict with researcher info, or None if not found
        """
        name_lower = name.strip().lower()

        # Direct match
        if name_lower in FAMOUS_RESEARCHERS:
            return FAMOUS_RESEARCHERS[name_lower]

        # Alias match
        for key, info in FAMOUS_RESEARCHERS.items():
            for alias in info.get("aliases", []):
                if name_lower == alias or name_lower in alias or alias in name_lower:
                    return info

        # Fuzzy match
        closest = None
        best_score = 0
        for key, info in FAMOUS_RESEARCHERS.items():
            score = 0
            if name_lower in key:
                score += 10
            for alias in info.get("aliases", []):
                if name_lower in alias:
                    score += 5
                name_words = set(name_lower.split())
                alias_words = set(alias.split())
                overlap = len(name_words & alias_words)
                if overlap >= 2:
                    score += overlap * 3
            if score > best_score:
                best_score = score
                closest = info

        return closest if best_score >= 3 else None

    # ── Listing ────────────────────────────────────────────────

    def list_researchers(self, field: str = "") -> list[dict]:
        """
        List all known researchers, optionally filtered by field.

        Args:
            field: Optional field filter

        Returns:
            List of researcher info dicts
        """
        results = []
        field_lower = field.lower().strip()

        for key, info in FAMOUS_RESEARCHERS.items():
            if field_lower and field_lower not in info.get("field", "").lower():
                continue
            results.append({
                "name": info["name"],
                "field": info["field"],
                "known_for": info["known_for"],
                "era": info.get("era", ""),
                "impact_score": info.get("impact_score", 0),
            })

        return sorted(results, key=lambda x: x["name"])

    # ── Paper Search ───────────────────────────────────────────

    def search_papers(
        self,
        researcher_name: str,
        topic: str = "",
        max_results: int = 10,
        source: str = "all",
    ) -> dict:
        """
        Search for papers by a famous researcher, optionally filtered by topic.

        Args:
            researcher_name: Name of the researcher
            topic: Optional topic filter
            max_results: Max papers to return
            source: Source to search (arxiv, semantic_scholar, all)

        Returns:
            Dict with researcher info, search query, and papers
        """
        with self._lock:
            self._search_count += 1

        researcher = self.identify_researcher(researcher_name)

        if researcher:
            search_name = researcher["name"]
            primary_alias = researcher["aliases"][0] if researcher["aliases"] else search_name
        else:
            search_name = researcher_name
            primary_alias = researcher_name.lower().replace(" ", "+")

        if topic:
            query = f"{primary_alias} {topic}"
        else:
            query = primary_alias

        papers = self._execute_search(query, max_results, source)

        return {
            "researcher": researcher or {"name": researcher_name, "field": "Unknown"},
            "known_researcher": researcher is not None,
            "query": query,
            "topic": topic,
            "papers": papers,
            "total_found": len(papers),
            "timestamp": datetime.now().isoformat(),
        }

    def _execute_search(self, query: str, max_results: int, source: str) -> list[dict]:
        """Execute paper search using existing actions."""
        try:
            from actions.paper_search import search_arxiv, search_semantic_scholar
        except ImportError:
            return [{"error": "paper_search module not available"}]

        all_papers = []

        if source in ("arxiv", "all"):
            try:
                results = search_arxiv(query, max_results)
                if not (len(results) == 1 and "error" in results[0]):
                    for p in results:
                        p["source_api"] = "arXiv"
                    all_papers.extend(results)
            except Exception:
                pass

        if source in ("semantic_scholar", "all"):
            try:
                results = search_semantic_scholar(query, max_results)
                if not (len(results) == 1 and "error" in results[0]):
                    for p in results:
                        p["source_api"] = "Semantic Scholar"
                    all_papers.extend(results)
            except Exception:
                pass

        # Deduplicate by title
        seen_titles = set()
        unique_papers = []
        for p in all_papers:
            title = p.get("title", "").lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_papers.append(p)

        return unique_papers[:max_results]

    # ── Researcher Profile ─────────────────────────────────────

    def get_researcher_profile(self, name: str) -> dict:
        """
        Get a comprehensive profile of a famous researcher.

        Args:
            name: Name of the researcher

        Returns:
            Dict with biography, seminal papers, field, and recent papers
        """
        researcher = self.identify_researcher(name)

        if not researcher:
            return {
                "found": False,
                "name": name,
                "message": f"Researcher '{name}' not found in database.",
            }

        papers_result = self.search_papers(
            researcher_name=researcher["name"],
            max_results=5,
        )

        return {
            "found": True,
            "name": researcher["name"],
            "field": researcher["field"],
            "era": researcher.get("era", ""),
            "known_for": researcher["known_for"],
            "seminal_papers": [p[0] for p in researcher.get("seminal_papers", [])],
            "impact_score": researcher.get("impact_score", 0),
            "recent_papers": papers_result["papers"],
            "search_query": papers_result["query"],
            "total_papers_found": papers_result["total_found"],
        }

    # ── Research Timeline ──────────────────────────────────────

    def get_research_timeline(self, name: str) -> dict:
        """
        Get a chronological timeline of a researcher's key works.

        Args:
            name: Name of the researcher

        Returns:
            Dict with timeline data (chronological list of works)
        """
        researcher = self.identify_researcher(name)

        if not researcher:
            return {
                "found": False,
                "name": name,
                "message": f"Researcher '{name}' not found.",
            }

        # Build timeline from seminal papers
        timeline = []
        for paper_title, year in researcher.get("seminal_papers", []):
            timeline.append({
                "year": year,
                "title": paper_title,
                "type": "seminal_work",
            })

        # Sort chronologically
        timeline.sort(key=lambda x: x["year"])

        # Fill gaps with decade context
        decades = set()
        for item in timeline:
            decade = (item["year"] // 10) * 10
            decades.add(decade)

        return {
            "found": True,
            "name": researcher["name"],
            "field": researcher["field"],
            "era": researcher.get("era", ""),
            "timeline": timeline,
            "decades_active": sorted(decades),
            "num_landmarks": len(timeline),
            "known_for": researcher["known_for"],
        }

    def format_timeline(self, timeline_data: dict) -> str:
        """Format a research timeline for display."""
        if not timeline_data.get("found"):
            return f"Researcher '{timeline_data.get('name', '')}' not found."

        lines = [
            f"📅 **Research Timeline: {timeline_data['name']}**",
            f"   {timeline_data['field']} — {timeline_data['era']}",
            f"   *{timeline_data['known_for']}*",
            "",
            "**Key Milestones (Chronological Order):**",
            "",
        ]

        timeline = timeline_data.get("timeline", [])
        for i, item in enumerate(timeline, 1):
            year = item["year"]
            title = item["title"]
            lines.append(f"   **{year}** — {title}")

        lines.append("")
        lines.append(f"   Total landmarks: {timeline_data['num_landmarks']}")
        lines.append(f"   Active decades: {', '.join(str(d) for d in timeline_data['decades_active'])}")

        return "\n".join(lines)

    # ── Research Impact ────────────────────────────────────────

    def get_research_impact(self, name: str) -> dict:
        """
        Compute research impact metrics for a researcher.

        Args:
            name: Name of the researcher

        Returns:
            Dict with impact metrics
        """
        researcher = self.identify_researcher(name)

        if not researcher:
            return {
                "found": False,
                "name": name,
                "message": f"Researcher '{name}' not found.",
            }

        impact = researcher.get("impact_score", 50)
        num_seminal = len(researcher.get("seminal_papers", []))

        # Compute field rank
        field = researcher["field"].split("/")[0].strip()
        field_scores = []
        for key, info in FAMOUS_RESEARCHERS.items():
            if field.lower() in info["field"].lower():
                field_scores.append((info["impact_score"], info["name"]))
        field_scores.sort(reverse=True)

        field_rank = 1
        for score, name in field_scores:
            if name == researcher["name"]:
                break
            field_rank += 1

        # Impact level classification
        if impact >= 95:
            level = "Legendary"
            badge = "🏆"
        elif impact >= 90:
            level = "Highly Influential"
            badge = "🌟"
        elif impact >= 85:
            level = "Very Influential"
            badge = "⭐"
        elif impact >= 80:
            level = "Influential"
            badge = "✨"
        else:
            level = "Notable"
            badge = "📌"

        return {
            "found": True,
            "name": researcher["name"],
            "field": researcher["field"],
            "impact_score": impact,
            "impact_level": level,
            "impact_badge": badge,
            "num_seminal_papers": num_seminal,
            "field_rank": field_rank,
            "field_total": len(field_scores),
            "known_for": researcher["known_for"],
        }

    def format_impact(self, impact_data: dict) -> str:
        """Format research impact for display."""
        if not impact_data.get("found"):
            return f"Researcher '{impact_data.get('name', '')}' not found."

        badge = impact_data["impact_badge"]
        lines = [
            f"{badge} **Research Impact: {impact_data['name']}**",
            f"   Field: {impact_data['field']}",
            "",
            f"   **Impact Score:** {impact_data['impact_score']}/100 — {impact_data['impact_level']}",
            f"   **Field Rank:** #{impact_data['field_rank']} of {impact_data['field_total']} in database",
            f"   **Seminal Papers:** {impact_data['num_seminal_papers']}",
            "",
            f"   *Known for:* {impact_data['known_for']}",
            "",
        ]

        # Visual impact bar
        bar_len = 30
        filled = int(impact_data['impact_score'] / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"   [{bar}] {impact_data['impact_score']}/100")

        return "\n".join(lines)

    # ── BibTeX Export ──────────────────────────────────────────

    def export_to_bibtex(self, name: str, papers_result: Optional[dict] = None) -> str:
        """
        Export papers from a researcher in BibTeX format.

        Args:
            name: Name of the researcher
            papers_result: Optional pre-fetched search result; if None, fetches automatically

        Returns:
            BibTeX-formatted string of papers
        """
        researcher = self.identify_researcher(name)

        if not researcher:
            return f"% Researcher '{name}' not found in database."

        if papers_result is None:
            papers_result = self.search_papers(
                researcher_name=name,
                max_results=10,
            )

        papers = papers_result.get("papers", [])

        entries = []
        entries.append(f"% BibTeX export for {researcher['name']} — generated {datetime.now().strftime('%Y-%m-%d')}")
        entries.append(f"% Field: {researcher['field']}")
        entries.append(f"% Known for: {researcher['known_for']}")
        entries.append("")

        # Seminal papers
        entries.append(f"% --- Seminal Works ---")
        for i, (title, year) in enumerate(researcher.get("seminal_papers", []), 1):
            author_key = researcher["name"].split()[-1].lower()
            key = f"{author_key}_{year}_{i}"
            entries.append(f"@article{{{key},")
            entries.append(f"  author={{{researcher['name']}}},")
            entries.append(f"  title={{{title}}},")
            entries.append(f"  year={{{year}}},")
            entries.append(f"  note={{Seminal work by {researcher['name']}}},")
            entries.append("}")
            entries.append("")

        # Recent papers from search
        valid_papers = [p for p in papers if "error" not in p]
        if valid_papers:
            entries.append(f"% --- Recent Publications ---")
            for i, paper in enumerate(valid_papers, 1):
                authors = paper.get("authors", [])
                author_str = " and ".join(authors[:3]) if authors else researcher["name"]
                if len(authors) > 3:
                    author_str += " and others"
                title = paper.get("title", "Untitled")
                year = paper.get("year", "") or paper.get("published", "")[:4] or "unknown"
                key = f"{researcher['name'].split()[-1].lower()}_{year}_{len(researcher['seminal_papers']) + i}"

                entries.append(f"@article{{{key},")
                entries.append(f"  author={{{author_str}}},")
                entries.append(f"  title={{{title}}},")
                entries.append(f"  year={{{year}}},")
                if paper.get("link"):
                    entries.append(f"  url={{{paper['link']}}},")
                source = paper.get("source_api", paper.get("source", ""))
                if source:
                    entries.append(f"  journal={{arXiv preprint ({source})}},")
                cits = paper.get("citation_count")
                if cits is not None:
                    entries.append(f"  note={{Cited by {cits}}},")
                entries.append("}")
                entries.append("")

        return "\n".join(entries)

    def format_bibtex_summary(self, name: str, bibtex: str) -> str:
        """Format BibTeX export summary for display."""
        researcher = self.identify_researcher(name)
        if not researcher:
            return f"Researcher '{name}' not found."

        entry_count = bibtex.count("@article{")
        lines = [
            f"📖 **BibTeX Export: {researcher['name']}**",
            f"   {entry_count} entries generated",
            "",
            "```bibtex",
            bibtex[:2000],
            "```" if len(bibtex) > 2000 else "",
        ]
        if len(bibtex) > 2000:
            lines.append(f"   *(showing first 2000 of {len(bibtex)} characters)*")

        return "\n".join(lines)

    # ── Cross-Field Discovery ──────────────────────────────────

    def find_similar_researchers(self, name: str, max_results: int = 5) -> dict:
        """
        Find researchers in similar or related fields.

        Args:
            name: Name of the researcher to find similar for
            max_results: Maximum number of similar researchers to return

        Returns:
            Dict with similar researchers grouped by relatedness
        """
        researcher = self.identify_researcher(name)

        if not researcher:
            return {"found": False, "name": name, "message": f"Researcher '{name}' not found."}

        field = researcher["field"].lower()
        field_parts = [f.strip() for f in field.split("/")]

        # Collect related fields
        related_fields = set()
        for fp in field_parts:
            if fp in FIELD_MAP:
                related_fields.update(FIELD_MAP[fp]["related"])
            # Also add parts of the field name
            for rf_key, rf_data in FIELD_MAP.items():
                if fp in rf_key or rf_key in fp:
                    related_fields.update(rf_data["related"])

        # Find similar researchers
        same_field = []
        related_field = []
        for key, info in FAMOUS_RESEARCHERS.items():
            if info["name"] == researcher["name"]:
                continue
            info_field_lower = info["field"].lower()

            # Same field match
            if any(fp in info_field_lower for fp in field_parts):
                same_field.append({
                    "name": info["name"],
                    "field": info["field"],
                    "known_for": info["known_for"],
                    "relationship": "same field",
                })
            # Related field match
            elif any(rf in info_field_lower for rf in related_fields):
                related_field.append({
                    "name": info["name"],
                    "field": info["field"],
                    "known_for": info["known_for"],
                    "relationship": "related field",
                })

        return {
            "found": True,
            "name": researcher["name"],
            "field": researcher["field"],
            "same_field": same_field[:max_results],
            "related_field": related_field[:max_results],
            "total_same_field": len(same_field),
            "total_related_field": len(related_field),
        }

    def format_similar_researchers(self, similar_data: dict) -> str:
        """Format similar researchers for display."""
        if not similar_data.get("found"):
            return f"Researcher '{similar_data.get('name', '')}' not found."

        lines = [
            f"🔗 **Researchers Related to {similar_data['name']}**",
            f"   Field: {similar_data['field']}",
            "",
        ]

        same = similar_data.get("same_field", [])
        related = similar_data.get("related_field", [])

        if same:
            lines.append(f"**Same Field ({similar_data['total_same_field']} found):**")
            for r in same:
                lines.append(f"   👤 **{r['name']}** — {r['known_for'][:80]}")
            lines.append("")

        if related:
            lines.append(f"**Related Fields ({similar_data['total_related_field']} found):**")
            for r in related:
                lines.append(f"   🔗 **{r['name']}** ({r['field']}) — {r['known_for'][:60]}")
            lines.append("")

        if not same and not related:
            lines.append("   No similar researchers found.")

        return "\n".join(lines)

    # ── Trend Extraction ───────────────────────────────────────

    def extract_trends(self, papers_result: dict) -> dict:
        """
        Extract trending topics and keywords from paper search results.

        Args:
            papers_result: Result dict from search_papers()

        Returns:
            Dict with trend analysis (top keywords, topic clusters, etc.)
        """
        papers = papers_result.get("papers", [])
        valid_papers = [p for p in papers if "error" not in p]

        if not valid_papers:
            return {
                "found": False,
                "message": "No papers to analyze for trends.",
            }

        # Extract keywords from titles and abstracts
        stop_words = {
            "the", "a", "an", "of", "in", "to", "and", "for", "is", "on", "that",
            "this", "with", "by", "at", "from", "as", "are", "was", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "can", "could", "may", "might", "shall", "should", "about",
            "into", "through", "during", "before", "after", "above", "below",
            "between", "such", "their", "our", "its", "these", "those", "using",
            "based", "via", "new", "method", "approach", "study", "results",
            "data", "model", "system", "also", "two", "one", "first", "well",
            "methods", "proposed", "show", "paper", "non", "novel", "however",
        }

        keywords = Counter()
        for paper in valid_papers:
            title = paper.get("title", "")
            summary = paper.get("summary", "") or paper.get("abstract", "")
            text = f"{title} {summary}"
            words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
            for w in words:
                if w not in stop_words:
                    keywords[w] += 1

        top_keywords = keywords.most_common(15)

        # Group by year if available
        by_year = {}
        years_with_papers = 0
        for paper in valid_papers:
            year = (paper.get("year", "") or paper.get("published", "")[:4])
            if year and year.isdigit() and len(year) == 4:
                by_year.setdefault(int(year), 0)
                by_year[int(year)] += 1
                years_with_papers += 1

        return {
            "found": True,
            "total_papers_analyzed": len(valid_papers),
            "top_keywords": top_keywords,
            "papers_by_year": dict(sorted(by_year.items())),
            "years_span": f"{min(by_year.keys())}-{max(by_year.keys())}" if by_year else "unknown",
            "year_range_start": min(by_year.keys()) if by_year else None,
            "year_range_end": max(by_year.keys()) if by_year else None,
        }

    def format_trends(self, trends: dict) -> str:
        """Format trend analysis for display."""
        if not trends.get("found"):
            return "No papers to analyze for trends."

        lines = [
            "📊 **Research Trends Analysis**",
            f"   Analyzing {trends['total_papers_analyzed']} papers",
            "",
        ]

        # Top keywords
        lines.append("**Hot Keywords:**")
        for word, count in trends.get("top_keywords", []):
            bar = "█" * min(count, 20)
            lines.append(f"   {bar} {word} ({count}x)")
        lines.append("")

        # Papers by year
        by_year = trends.get("papers_by_year", {})
        if by_year:
            lines.append(f"**Publication Timeline ({trends.get('years_span', '')}):**")
            max_count = max(by_year.values()) if by_year else 1
            for year, count in sorted(by_year.items()):
                bar_len = int(count / max_count * 20)
                bar = "▇" * bar_len
                year_str = f"   **{year}** {bar} ({count} paper{'s' if count != 1 else ''})"
                lines.append(year_str)

        return "\n".join(lines)

    # ── Comparison ─────────────────────────────────────────────

    def compare_researchers(
        self,
        names: list[str],
        topic: str = "",
    ) -> dict:
        """
        Compare multiple researchers' work on a given topic.

        Args:
            names: List of researcher names
            topic: Topic to filter by

        Returns:
            Dict with comparison data for each researcher
        """
        results = {}
        for name in names:
            search_result = self.search_papers(
                researcher_name=name,
                topic=topic,
                max_results=3,
            )
            researcher = search_result.get("researcher", {})
            papers = search_result.get("papers", [])
            results[name] = {
                "name": researcher.get("name", name),
                "field": researcher.get("field", "Unknown"),
                "known_for": researcher.get("known_for", ""),
                "impact_score": researcher.get("impact_score", 0),
                "known_researcher": search_result.get("known_researcher", False),
                "papers_found": len([p for p in papers if "error" not in p]),
                "top_papers": [p.get("title", "") for p in papers if "error" not in p][:3],
            }

        return {
            "topic": topic,
            "researchers": results,
            "timestamp": datetime.now().isoformat(),
        }

    # ── Stats ──────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get search engine statistics."""
        with self._lock:
            # Compute field breakdown
            field_counts = Counter()
            for key, info in FAMOUS_RESEARCHERS.items():
                field_counts[info["field"]] += 1

            # Era breakdown
            era_counts = Counter()
            for key, info in FAMOUS_RESEARCHERS.items():
                era_counts[info.get("era", "unknown")] += 1

            return {
                "total_searches": self._search_count,
                "researchers_in_db": len(FAMOUS_RESEARCHERS),
                "fields_covered": len(field_counts),
                "field_breakdown": dict(field_counts.most_common()),
                "era_breakdown": dict(era_counts.most_common()),
                "total_seminal_papers": sum(
                    len(info.get("seminal_papers", []))
                    for info in FAMOUS_RESEARCHERS.values()
                ),
                "status": "ready",
            }

    # ── Formatting ─────────────────────────────────────────────

    def format_search_results(self, result: dict) -> str:
        """Format search results for display."""
        researcher = result.get("researcher", {})
        papers = result.get("papers", [])
        known = result.get("known_researcher", False)

        lines = []
        name = researcher.get("name", "Unknown")
        field = researcher.get("field", "")
        known_for = researcher.get("known_for", "")
        era = researcher.get("era", "")

        # Header
        icon = "🔬" if known else "🔎"
        lines.append(f"{icon} **Paper Search: {name}**")
        if known_for:
            lines.append(f"   {field} — {known_for}")
            if era:
                lines.append(f"   Era: {era}")
        lines.append("")

        if not papers or (len(papers) == 1 and "error" in papers[0]):
            error_msg = papers[0].get("error", "No papers found") if papers else "No papers found"
            lines.append(f"⚠️  {error_msg}")
            return "\n".join(lines)

        # Results count
        lines.append(f"**Results ({result.get('total_found', len(papers))} papers found):**")
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
            summary = (paper.get("summary", "") or paper.get("abstract", "") or "")[:250]
            citations = paper.get("citation_count")
            source_name = paper.get("source_api", paper.get("source", ""))

            lines.append(f"**{i}. {title}**")
            if authors:
                lines.append(f"   *Authors:* {authors}")
            info_parts = []
            if year:
                info_parts.append(f"*Year:* {year}")
            if source_name:
                info_parts.append(f"*Source:* {source_name}")
            if citations is not None:
                info_parts.append(f"*Citations:* {citations}")
            if info_parts:
                lines.append("   " + " | ".join(info_parts))
            if summary:
                lines.append(f"   *Abstract:* {summary}...")
            if link:
                lines.append(f"   *Link:* <{link}>")
            lines.append("")

        if result.get("topic"):
            lines.append(f"   *Topic filter:* {result['topic']}")

        return "\n".join(lines)

    def format_researcher_list(self, researchers: list[dict]) -> str:
        """Format a list of researchers for display."""
        if not researchers:
            return "No researchers found."

        # Group by field
        by_field = {}
        for r in researchers:
            field = r.get("field", "Unknown")
            by_field.setdefault(field, [])
            by_field[field].append(r)

        lines = [
            "🔬 **Available Researchers**",
            f"   Total: {len(researchers)} researchers in database",
            "",
        ]

        for field in sorted(by_field.keys()):
            group = by_field[field]
            lines.append(f"**{field} ({len(group)}):**")
            for r in sorted(group, key=lambda x: x["name"]):
                impact = r.get("impact_score", 0)
                impact_str = f" [{impact}/100]" if impact else ""
                known = r.get("known_for", "")[:80]
                lines.append(f"   👤 **{r['name']}**{impact_str}")
                if known:
                    lines.append(f"      {known}")
            lines.append("")

        return "\n".join(lines)

    def format_profile(self, profile: dict) -> str:
        """Format a researcher profile for display."""
        if not profile.get("found"):
            return f"Researcher '{profile.get('name', '')}' not found."

        impact = profile.get("impact_score", 0)
        if impact >= 95:
            badge = "🏆"
        elif impact >= 90:
            badge = "🌟"
        elif impact >= 80:
            badge = "⭐"
        else:
            badge = "📌"

        era = profile.get("era", "")

        lines = [
            f"{badge} **{profile['name']}**",
            f"   *Field:* {profile['field']}",
        ]
        if era:
            lines.append(f"   *Era:* {era}")
        lines.append(f"   *Known for:* {profile['known_for']}")
        if impact:
            lines.append(f"   *Impact Score:* {impact}/100")
        lines.append("")
        lines.append("**Seminal Papers:**")

        for paper in profile.get("seminal_papers", []):
            lines.append(f"   📄 {paper}")

        recent = profile.get("recent_papers", [])
        if recent and not (len(recent) == 1 and "error" in recent[0]):
            lines.extend(["", "**Recent Publications:**"])
            for i, paper in enumerate(recent[:5], 1):
                title = paper.get("title", "Untitled")
                year = paper.get("year", "") or paper.get("published", "")[:4]
                year_str = f" ({year})" if year else ""
                lines.append(f"   {i}. {title}{year_str}")

        lines.append("")
        lines.append(f"🔍 *Search query:* `{profile.get('search_query', '')}`")

        return "\n".join(lines)

    def format_comparison(self, comparison: dict) -> str:
        """Format researcher comparison for display."""
        researchers = comparison.get("researchers", {})
        topic = comparison.get("topic", "")

        lines = [
            "⚖️ **Researcher Comparison**",
        ]
        if topic:
            lines.append(f"   Topic: {topic}")
        lines.append("")

        # Comparison table header
        headers = ["Name", "Field", "Papers Found", "Impact"]
        lines.append(f"| {' | '.join(headers)} |")
        lines.append(f"|{'|'.join(['---' for _ in headers])}|")
        lines.append("")

        for name, data in researchers.items():
            impact = data.get("impact_score", "N/A")
            impact_str = f"{impact}/100" if impact else "N/A"
            known = " (known)" if data["known_researcher"] else ""
            lines.append(f"**{data['name']}**{known}")
            lines.append(f"   Field: {data['field']}")
            lines.append(f"   Papers: {data['papers_found']} | Impact: {impact_str}")
            if data["known_for"]:
                lines.append(f"   Known for: {data['known_for']}")
            if data["top_papers"]:
                lines.append(f"   Top papers:")
                for p in data["top_papers"]:
                    lines.append(f"     • {p[:90]}")
            lines.append("")

        return "\n".join(lines)

    def format_stats_table(self, stats: dict) -> str:
        """Format stats as a structured table."""
        lines = [
            "📊 **Scientist Search Statistics**",
            "",
            "**Overview:**",
            f"   Total searches run: {stats['total_searches']}",
            f"   Researchers in database: {stats['researchers_in_db']}",
            f"   Fields covered: {stats['fields_covered']}",
            f"   Total seminal papers indexed: {stats['total_seminal_papers']}",
            f"   Status: {stats['status']}",
            "",
        ]

        fields = stats.get("field_breakdown", {})
        if fields:
            lines.append("**Researchers by Field:**")
            for field, count in sorted(fields.items(), key=lambda x: -x[1]):
                bar = "█" * count
                lines.append(f"   {bar} {field} ({count})")

        lines.append("")

        eras = stats.get("era_breakdown", {})
        if eras:
            lines.append("**Researchers by Era:**")
            for era, count in sorted(eras.items(), key=lambda x: -x[1]):
                lines.append(f"   • {era}: {count} researchers")

        return "\n".join(lines)


# ── Singleton ──────────────────────────────────────────────────

_scientist_search = None
_search_lock = threading.Lock()


def get_scientist_search() -> ScientistSearch:
    global _scientist_search
    if _scientist_search is None:
        with _search_lock:
            if _scientist_search is None:
                _scientist_search = ScientistSearch()
    return _scientist_search
