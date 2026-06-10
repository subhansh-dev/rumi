"""
cross_validation.py - Phase 11.6: Test winning theory against held-out papers.

Splits literature into training (75%) and holdout (25%), then tests
whether the winning theory's claims match what holdout papers say.

This prevents overfitting: a theory that only explains the papers
that generated it but fails on independent literature is likely noise.
"""
import re
import random


class CrossValidator:
    """Test theories against held-out literature for robustness."""

    HOLDOUT_FRACTION = 0.25

    def validate(self, theory: dict, papers: list, topic: str, domain: str) -> dict:
        if not papers or len(papers) < 6:
            return {"holdout_papers": 0, "robustness_score": 0.5,
                    "reason": "Not enough papers (need >= 6)"}

        shuffled = list(papers)
        random.seed(42)
        random.shuffle(shuffled)
        holdout_count = max(3, int(len(shuffled) * self.HOLDOUT_FRACTION))
        holdout = shuffled[:holdout_count]
        training = shuffled[holdout_count:]

        theory_claims = self._extract_claims(theory, topic)
        findings = []
        supported = contradicted = neutral = 0

        for paper in holdout:
            finding = self._test_paper(paper, theory_claims, topic)
            findings.append(finding)
            s = finding.get("status", "neutral")
            if s == "supports": supported += 1
            elif s == "contradicts": contradicted += 1
            else: neutral += 1

        total_eval = supported + contradicted
        robustness = supported / total_eval if total_eval > 0 else 0.5

        return {
            "holdout_papers": len(holdout),
            "training_papers": len(training),
            "supported_by_holdout": supported,
            "contradicted_by_holdout": contradicted,
            "neutral_by_holdout": neutral,
            "robustness_score": round(robustness, 3),
            "holdout_findings": findings,
        }

    def _extract_claims(self, theory: dict, topic: str) -> list:
        claims = []
        desc = theory.get("description", theory.get("mechanism", ""))
        if desc:
            for sent in re.split(r'[.!?]\s+', desc):
                sent = sent.strip()
                if len(sent) > 20:
                    has_signal = any(c.isdigit() for c in sent) or any(
                        kw in sent.lower() for kw in [
                            "causes", "leads to", "produces", "increases", "decreases",
                            "correlates", "predicts", "implies", "suggests", "drives",
                            "mediates", "enables", "prevents", "triggers"])
                    if has_signal:
                        claims.append(sent[:200])
        for pred in theory.get("predictions", []):
            stmt = pred.get("statement", pred.get("description", "")) if isinstance(pred, dict) else str(pred)
            if stmt and len(stmt) > 10:
                claims.append(stmt[:200])
        for step in theory.get("steps", [])[:5]:
            if isinstance(step, str) and len(step) > 20:
                claims.append(step[:200])
        return claims[:15]

    def _test_paper(self, paper: dict, claims: list, topic: str) -> dict:
        title = (paper.get("title") or "").lower()
        abstract = (paper.get("abstract") or "").lower()
        combined = title + " " + abstract
        if not combined.strip():
            return {"paper_title": paper.get("title", "?"), "status": "neutral",
                    "reason": "No abstract"}

        stopwords = {"the","and","for","with","that","this","from","are","has","was",
                     "were","been","have","using","which","when","where","what","how"}
        topic_words = set(w for w in topic.lower().split() if len(w) > 3) - stopwords
        if sum(1 for w in topic_words if w in combined) < 1:
            return {"paper_title": paper.get("title", "?")[:80], "status": "neutral",
                    "reason": "Not relevant to topic"}

        support_w = {"consistent","confirms","supports","validates","observed","measured",
                     "detected","found","demonstrated","evidence","significant","correlation"}
        contra_w = {"inconsistent","contradicts","refutes","challenges","no evidence",
                    "not observed","not detected","fails to","incompatible","unexpected",
                    "however","although","despite"}

        sup = con = 0
        for claim in claims[:10]:
            claim_words = set(w for w in claim.lower().split() if len(w) > 4) - stopwords
            overlap = claim_words & set(combined.split())
            if len(overlap) < 2:
                continue
            for w in support_w:
                if w in combined: sup += 1; break
            for w in contra_w:
                if w in combined: con += 1; break

        if sup > con and sup >= 1:
            status, reason = "supports", f"{sup} support vs {con} contradict"
        elif con > sup and con >= 1:
            status, reason = "contradicts", f"{con} contradict vs {sup} support"
        else:
            status, reason = "neutral", f"Insufficient signal ({sup} sup, {con} con)"

        return {"paper_title": paper.get("title", "?")[:80], "status": status,
                "support_signals": sup, "contradict_signals": con, "reason": reason}
