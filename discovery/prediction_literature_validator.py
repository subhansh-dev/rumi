"""
prediction_literature_validator.py — Validate RUMI's predictions against real literature.

The core validation gap: RUMI predicts "P_i,off ≈ 0.12 at CAG=0.6" but never checks
if any published paper actually measured this. This module:

1. Extracts specific numerical claims from predictions
2. Searches literature for papers that TESTED those exact claims  
3. Uses LLM to compare RUMI's numbers against published data
4. Returns grounded validation: supported / contradicted / unverifiable

Usage:
    from discovery.prediction_literature_validator import PredictionLiteratureValidator
    validator = PredictionLiteratureValidator(llm_call=_truncated_llm)
    results = validator.validate_predictions(predictions, mechanisms, topic, domain)
"""

import json
import re
import time
from typing import Optional


class PredictionLiteratureValidator:
    """Validate RUMI's numerical predictions against real published data."""

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def validate_predictions(self, predictions: list, mechanisms: list = None,
                             topic: str = "", domain: str = "",
                             existing_papers: list = None) -> dict:
        """
        Validate all predictions against literature.

        Returns:
            {
                "validations": [
                    {
                        "prediction": "...",
                        "numerical_claims": ["P_i,off ≈ 0.12", ...],
                        "search_queries": ["CRISPR off-target CpG methylation cleavage rate", ...],
                        "papers_found": 5,
                        "supporting_papers": 2,
                        "contradicting_papers": 0,
                        "unverifiable_claims": ["Δg_meth = -0.4 kcal/mol"],
                        "grounded_claims": ["P_i,off ≈ 0.12 supported by 2 papers"],
                        "validation_status": "supported|partially_supported|contradicted|unverifiable",
                        "confidence_adjustment": 0.0,  # +/- adjustment to original confidence
                        "details": "..."
                    }
                ],
                "summary": {
                    "total_predictions": N,
                    "supported": N,
                    "partially_supported": N,
                    "contradicted": N,
                    "unverifiable": N,
                    "overall_grounding": "strong|moderate|weak|none"
                }
            }
        """
        if not predictions:
            return self._empty_result()

        # Import paper search
        try:
            from discovery.citation_grounding import fetch_papers
        except ImportError:
            return self._empty_result("citation_grounding not available")

        validations = []

        for pred in predictions[:7]:  # Cap at 7 predictions to avoid API abuse
            if not isinstance(pred, dict):
                continue

            statement = pred.get("statement", pred.get("description", ""))
            if not statement or len(statement) < 20:
                continue

            try:
                validation = self._validate_single_prediction(
                    pred, mechanisms, topic, domain, existing_papers, fetch_papers
                )
                validations.append(validation)
                time.sleep(1)  # Rate limit between predictions
            except Exception as e:
                validations.append({
                    "prediction": statement[:200],
                    "validation_status": "error",
                    "details": str(e),
                    "confidence_adjustment": 0.0,
                })

        return self._build_result(validations)

    def _validate_single_prediction(self, pred: dict, mechanisms: list,
                                     topic: str, domain: str,
                                     existing_papers: list,
                                     fetch_papers_fn) -> dict:
        """Validate one prediction against literature."""
        statement = pred.get("statement", pred.get("description", ""))
        original_confidence = pred.get("confidence", 0.5)

        # Step 1: Extract numerical claims from the prediction
        numerical_claims = self._extract_numerical_claims(statement)
        # Also extract from mechanism math if available
        mechanism_params = self._extract_mechanism_params(mechanisms)

        # Step 2: Build targeted search queries
        search_queries = self._build_search_queries(
            statement, numerical_claims, mechanism_params, topic, domain
        )

        # Step 3: Search for papers
        all_papers = []
        for query in search_queries[:3]:  # Max 3 searches per prediction
            try:
                papers = fetch_papers_fn(query, max_arxiv=8, max_pubmed=8,
                                         max_s2=8, max_crossref=5)
                all_papers.extend(papers)
                time.sleep(0.5)
            except Exception:
                continue

        # Deduplicate
        seen = set()
        unique_papers = []
        for p in all_papers:
            key = (p.get("title", "") or "")[:60].lower()
            if key and key not in seen:
                seen.add(key)
                unique_papers.append(p)

        # Step 4: Use LLM to compare claims against papers
        if self.llm_call and unique_papers:
            comparison = self._llm_compare_claims(
                statement, numerical_claims, mechanism_params,
                unique_papers, topic, domain
            )
        else:
            comparison = {
                "supporting_papers": 0,
                "contradicting_papers": 0,
                "unverifiable_claims": numerical_claims,
                "grounded_claims": [],
                "validation_status": "unverifiable" if not unique_papers else "no_llm",
                "details": "No papers found" if not unique_papers else "LLM not available",
            }

        # Step 5: Compute confidence adjustment
        adj = self._compute_confidence_adjustment(
            comparison, original_confidence, len(unique_papers)
        )

        return {
            "prediction": statement[:300],
            "original_confidence": original_confidence,
            "numerical_claims": numerical_claims,
            "mechanism_params_used": mechanism_params[:5],
            "search_queries": search_queries[:3],
            "papers_found": len(unique_papers),
            "supporting_papers": comparison.get("supporting_papers", 0),
            "contradicting_papers": comparison.get("contradicting_papers", 0),
            "unverifiable_claims": comparison.get("unverifiable_claims", []),
            "grounded_claims": comparison.get("grounded_claims", []),
            "validation_status": comparison.get("validation_status", "unverifiable"),
            "confidence_adjustment": adj,
            "adjusted_confidence": round(max(0.1, min(0.99,
                original_confidence + adj)), 3),
            "details": comparison.get("details", ""),
        }

    def _extract_numerical_claims(self, text: str) -> list:
        """Pull specific numerical claims from prediction text."""
        claims = []
        # Match patterns like: P_i,off ≈ 0.12, D_eff ≈ 0.12 µm²/s, etc.
        patterns = [
            # "X ≈ Y" or "X = Y" or "X ~ Y"
            r'[\w_]+[\s]*(?:≈|~=|~|=|is approximately)\s*[\d][\d\.e\-+]*\s*[\w°%µ·/\-*²³]*',
            # "12%" or "23 %"
            r'\d+\.?\d*\s*%',
            # "factor of X" or "X-fold"
            r'(?:factor|fold)[\s]*(?:of\s*)?[\d\.]+',
            # "from X to Y"
            r'from\s+[\d\.]+\s+to\s+[\d\.]+',
        ]
        for pat in patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            claims.extend(matches[:3])

        # Also grab any equation-like fragments
        eq_matches = re.findall(r'[\w_]+\s*[=≈~]\s*[\d\.]+[eE]?[\-+]?\d*', text)
        claims.extend(eq_matches[:3])

        # Deduplicate and clean
        seen = set()
        clean = []
        for c in claims:
            c = c.strip()
            if c and c not in seen and len(c) > 3:
                seen.add(c)
                clean.append(c)
        return clean[:8]

    def _extract_mechanism_params(self, mechanisms: list) -> list:
        """Extract key parameters from mechanisms for search context."""
        params = []
        for m in (mechanisms or [])[:3]:
            math_text = m.get("math", m.get("equation", ""))
            if math_text:
                # Extract variable = value patterns
                matches = re.findall(r'(\w+)\s*[≈=]\s*([\d\.]+[eE]?[\-+]?\d*)\s*([\w°µ·/\-*²³]*)', math_text)
                for var, val, unit in matches:
                    params.append(f"{var} = {val} {unit}".strip())
            # Also grab from steps
            for step in (m.get("steps", m.get("derivation_steps", [])) or [])[:5]:
                if isinstance(step, str):
                    matches = re.findall(r'(\w+)\s*[≈=]\s*([\d\.]+[eE]?[\-+]?\d*)\s*([\w°µ·/\-*²³]*)', step)
                    for var, val, unit in matches:
                        params.append(f"{var} = {val} {unit}".strip())
        return list(dict.fromkeys(params))[:10]  # Deduplicate preserving order

    def _build_search_queries(self, prediction: str, claims: list,
                               params: list, topic: str, domain: str) -> list:
        """Build targeted literature search queries."""
        queries = []

        # Query 1: Topic + key measurement terms from the prediction
        # Extract the main subject nouns
        key_terms = self._extract_key_terms(prediction, topic)
        if key_terms:
            queries.append(f"{topic} {key_terms} measured experimental data")

        # Query 2: Specific numerical claim
        if claims:
            # Take the most specific claim and search for it
            best_claim = max(claims, key=len) if claims else ""
            claim_clean = re.sub(r'[≈~=]', '', best_claim).strip()
            if claim_clean:
                queries.append(f"{topic} {claim_clean}")

        # Query 3: Mechanism parameters
        if params:
            queries.append(f"{topic} {' '.join(params[:3])} measurement")

        # Fallback
        if not queries:
            queries.append(f"{topic} quantitative measurements {domain}")

        return queries[:4]

    def _extract_key_terms(self, prediction: str, topic: str) -> str:
        """Extract the most relevant measurement terms from a prediction."""
        # Remove the topic itself to get the specific claim
        clean = prediction
        for word in topic.lower().split():
            clean = re.sub(re.escape(word), '', clean, flags=re.IGNORECASE)

        # Remove common filler words
        stopwords = {'if', 'then', 'the', 'a', 'an', 'is', 'are', 'will', 'be',
                     'that', 'this', 'with', 'for', 'from', 'under', 'than',
                     'approximately', 'about', 'around', 'predicted', 'probability'}
        words = [w for w in clean.split() if w.lower() not in stopwords and len(w) > 2]
        return ' '.join(words[:6])

    def _llm_compare_claims(self, prediction: str, claims: list,
                             params: list, papers: list,
                             topic: str, domain: str) -> dict:
        """Use LLM to compare RUMI's claims against found papers."""
        # Build paper summaries (limit to avoid token explosion)
        paper_text = ""
        for i, p in enumerate(papers[:10]):
            title = p.get("title", "Unknown")
            abstract = (p.get("abstract", "") or "")[:300]
            source = p.get("source", "?")
            paper_text += f"\n[{i+1}] ({source}) {title}\n    {abstract}\n"

        claims_text = "\n".join(f"  - {c}" for c in claims[:6])
        params_text = "\n".join(f"  - {p}" for p in params[:6])

        prompt = f"""You are a scientific validation expert. Compare RUMI's predictions against published literature.

RUMI'S PREDICTION:
"{prediction}"

NUMERICAL CLAIMS MADE:
{claims_text or '  (none extracted)'}

MECHANISM PARAMETERS:
{params_text or '  (none extracted)'}

PAPERS FOUND IN LITERATURE:
{paper_text or '  (none found)'}

TASK: For each numerical claim, determine if the literature SUPPORTS, CONTRADICTS, or CANNOT VERIFY it.

Rate each paper as supporting/contradicting/irrelevant.
Identify which specific claims are grounded in real data vs. pure speculation.

Output JSON:
{{"supporting_papers": N, "contradicting_papers": N, "irrelevant_papers": N, "grounded_claims": ["claim1: supported by paper [X]", ...], "unverifiable_claims": ["claim1: no literature found", ...], "contradicted_claims": ["claim1: paper [X] shows different value", ...], "validation_status": "supported|partially_supported|contradicted|unverifiable", "details": "2-3 sentence summary of validation findings"}}"""

        raw = self.llm_call(prompt, max_tokens=2048, phase="validation")
        if not raw:
            return {"validation_status": "unverifiable", "details": "LLM call failed"}

        try:
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0].strip()
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract status from free text
            lower = raw.lower()
            if "support" in lower and "contradict" not in lower:
                status = "supported"
            elif "contradict" in lower:
                status = "contradicted"
            elif "partially" in lower:
                status = "partially_supported"
            else:
                status = "unverifiable"
            return {
                "validation_status": status,
                "details": raw[:300],
                "supporting_papers": 0,
                "contradicting_papers": 0,
                "unverifiable_claims": claims,
                "grounded_claims": [],
            }

    def _compute_confidence_adjustment(self, comparison: dict,
                                        original_confidence: float,
                                        papers_found: int) -> float:
        """Compute confidence adjustment based on literature validation."""
        status = comparison.get("validation_status", "unverifiable")
        supporting = comparison.get("supporting_papers", 0)
        contradicting = comparison.get("contradicting_papers", 0)

        if status == "supported" and supporting >= 2:
            return +0.10  # Strong literature support
        elif status == "supported":
            return +0.05
        elif status == "partially_supported":
            return +0.02
        elif status == "contradicted" and contradicting >= 2:
            return -0.20  # Strongly contradicted
        elif status == "contradicted":
            return -0.10
        elif status == "unverifiable" and papers_found == 0:
            return -0.05  # No papers found = slight penalty
        return 0.0

    def _build_result(self, validations: list) -> dict:
        """Build summary from individual validations."""
        supported = sum(1 for v in validations if v.get("validation_status") == "supported")
        partial = sum(1 for v in validations if v.get("validation_status") == "partially_supported")
        contradicted = sum(1 for v in validations if v.get("validation_status") == "contradicted")
        unverifiable = sum(1 for v in validations if v.get("validation_status") == "unverifiable")
        total = len(validations)

        if total == 0:
            grounding = "none"
        elif supported / total > 0.6:
            grounding = "strong"
        elif (supported + partial) / total > 0.5:
            grounding = "moderate"
        elif contradicted / total > 0.3:
            grounding = "weak_contradicted"
        else:
            grounding = "weak"

        return {
            "validations": validations,
            "summary": {
                "total_predictions": total,
                "supported": supported,
                "partially_supported": partial,
                "contradicted": contradicted,
                "unverifiable": unverifiable,
                "overall_grounding": grounding,
                "avg_confidence_adjustment": round(
                    sum(v.get("confidence_adjustment", 0) for v in validations) / max(1, total), 3
                ),
            }
        }

    def _empty_result(self, reason: str = "No predictions") -> dict:
        return {
            "validations": [],
            "summary": {
                "total_predictions": 0,
                "supported": 0,
                "partially_supported": 0,
                "contradicted": 0,
                "unverifiable": 0,
                "overall_grounding": "none",
                "avg_confidence_adjustment": 0.0,
                "note": reason,
            }
        }
