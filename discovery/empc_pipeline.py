"""
empc_pipeline.py - Evidence Mechanism Equation Prediction Pipeline
Enforces strict scientific reasoning chain at each stage.
"""
import re

class EMPCPipeline:
    """Evidence -> Mechanism -> Equation -> Prediction pipeline."""

    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def run(self, topic, domain, papers, mechanisms, theories):
        """Run the full EMPC pipeline."""
        result = {"evidence": {}, "mechanisms": {}, "equations": {},
                  "predictions": {}, "grounding_scores": {}, "chain_integrity": 0.0}
        evidence = self._extract_evidence(papers, topic)
        result["evidence"] = evidence
        mech = self._ground_mechanisms(mechanisms, evidence)
        result["mechanisms"] = mech
        eqs = self._ground_equations(mechanisms, theories, mech)
        result["equations"] = eqs
        preds = self._ground_predictions(theories, eqs)
        result["predictions"] = preds
        result["grounding_scores"] = {
            "evidence_quality": evidence.get("quality_score", 0),
            "mechanism_grounding": mech.get("grounding_score", 0),
            "equation_grounding": eqs.get("grounding_score", 0),
            "prediction_grounding": preds.get("grounding_score", 0),
        }
        scores = list(result["grounding_scores"].values())
        result["chain_integrity"] = round(sum(scores) / len(scores), 3) if scores else 0
        return result

    def _extract_evidence(self, papers, topic):
        """Stage 1: Extract findings using 5 strategies."""
        findings = []
        stopwords = {"the","and","for","with","that","this","from","are","has","was",
                     "were","been","have","will","would","could","should","into","over",
                     "such","than","them","then","they","using","which","when","where"}
        topic_words = set(w for w in topic.lower().split() if len(w) > 3)
        topic_kw = topic_words - stopwords

        for p in (papers or []):
            title = (p.get("title") or "")
            abstract = (p.get("abstract") or "")
            combined = (title + " " + abstract).lower()
            cits = p.get("citation_count", 0) or 0
            relevance = sum(1 for w in topic_kw if w in combined)
            if relevance < 2:
                continue

            # S1: Numbers with units (broad)
            for m in re.finditer(r"(\d[\d\.eE\+\-]*\s*(?:K|eV|meV|GeV|GPa|MPa|Pa|cm|nm|um|GHz|THz|Hz|Mpc|kpc|pc|yr|s|ms|us|ns|ohm|V|T|W|J|mol|rad|deg|ppm|ppb|arcsec|arcmin|dB|barn|%))", combined):
                findings.append({"type":"measurement","finding":m.group(0)[:100],"source":title[:60],"citations":cits})

            # S2: Key claim sentences
            for sent in re.split(r"[.!?]\s+", abstract):
                sl = sent.lower().strip()
                if len(sl) < 30: continue
                hits = sum(1 for w in topic_kw if w in sl)
                if hits >= 2 and re.search(r"\d", sl):
                    findings.append({"type":"claim","finding":sent.strip()[:200],"source":title[:60],"citations":cits})

            # S3: Equations in text
            for m in re.finditer(r"([A-Za-z_][\w]*\s*=\s*[\d\.eE\+\-]+[\w\s/\*]*)", combined):
                findings.append({"type":"equation","finding":m.group(0)[:100],"source":title[:60],"citations":cits})

            # S4: Observed/measured/found
            for pat in [r"(?:observed|measured|found|reported|determined|demonstrated)\s+.{10,120}",
                        r"(?:consistent with|in agreement|supports|confirms)\s+.{10,80}"]:
                for m in re.finditer(pat, combined):
                    findings.append({"type":"comparison","finding":m.group(0)[:150],"source":title[:60],"citations":cits})

            # S5: Domain-specific patterns (capped per paper to avoid noise)
            domain_count = 0
            for pat in [r"filling factor.{0,10}\d[\d/]*",
                        r"cross[- ]section.{0,10}\d[\d\.eE\+\-]*",
                        r"critical temperature.{0,10}\d[\d\.]*",
                        r"energy gap.{0,10}\d[\d\.eE\+\-]*",
                        r"coherence time.{0,10}\d[\d\.eE\+\-]*",
                        r"error rate.{0,10}\d[\d\.eE\+\-]*",
                        r"braiding\s+.{5,60}",
                        r"topological\s+.{5,60}",
                        r"non.abelian\s+.{5,60}",
                        r"anyonic\s+.{5,60}",
                        r"quantum\s+(?:error|correction|hall|state)\s+.{5,60}"]:
                if domain_count >= 5:
                    break
                for m in re.finditer(pat, combined):
                    if domain_count >= 5:
                        break
                    findings.append({"type":"domain","finding":m.group(0)[:120],"source":title[:60],"citations":cits})
                    domain_count += 1
                for m in re.finditer(pat, combined):
                    findings.append({"type":"domain","finding":m.group(0)[:120],"source":title[:60],"citations":cits})

        # Deduplicate
        seen = set()
        unique = []
        for f in findings:
            key = f["finding"][:50].lower()
            if key not in seen:
                seen.add(key)
                unique.append(f)

        cit_boost = sum(min(0.2, f.get("citations",0)*0.005) for f in unique)
        quality = min(1.0, len(unique)*0.03 + cit_boost)

        relevant = 0
        for p in (papers or []):
            c = ((p.get("title") or "") + " " + (p.get("abstract") or "")).lower()
            if sum(1 for w in topic_kw if w in c) >= 2:
                relevant += 1

        return {"findings": unique[:25], "total_papers": len(papers or []),
                "relevant_papers": relevant, "quality_score": round(quality, 3),
                "by_type": {
                    "measurements": sum(1 for f in unique if f.get("type")=="measurement"),
                    "claims": sum(1 for f in unique if f.get("type")=="claim"),
                    "equations": sum(1 for f in unique if f.get("type")=="equation"),
                    "comparisons": sum(1 for f in unique if f.get("type")=="comparison"),
                    "domain": sum(1 for f in unique if f.get("type")=="domain"),
                }}

    def _ground_mechanisms(self, mechanisms, evidence):
        grounded = []
        ungrounded = []
        ev_text = " ".join(f.get("finding","") for f in evidence.get("findings",[])).lower()
        ev_words = set(w for w in ev_text.split() if len(w) > 4)
        for m in (mechanisms or []):
            if not isinstance(m, dict): continue
            desc = (m.get("description") or m.get("mechanism") or "").lower()
            # Also include derivation, steps, and mathematical_model in the check
            derivation = m.get("derivation", "")
            if isinstance(derivation, list):
                derivation = " ".join(str(d) for d in derivation)
            steps_text = " ".join(str(s) for s in (m.get("steps") or []))
            math_model = m.get("mathematical_model", "")
            full_text = desc + " " + str(derivation) + " " + steps_text + " " + str(math_model)
            mech_words = set(w for w in full_text.lower().split() if len(w) > 4)
            overlap = len(ev_words & mech_words)
            # Grounding criteria: word overlap OR has structured derivation OR has math model
            has_derivation = any(kw in full_text.lower() for kw in [
                "therefore", "thus", "it follows", "substituting", "solving",
                "deriving", "from this", "we obtain", "we get", "yielding",
                "step 1", "step 2", "step 3", "starting from", "governing equation",
            ])
            has_math = bool(math_model) and len(str(math_model)) > 10
            is_grounded = overlap >= 2 or len(desc) > 200 or (has_derivation and has_math)
            entry = {"name": m.get("name","?"), "evidence_refs": overlap,
                     "has_derivation": has_derivation, "has_math": has_math,
                     "is_grounded": is_grounded}
            (grounded if is_grounded else ungrounded).append(entry)
        score = len(grounded) / max(1, len(grounded) + len(ungrounded))
        return {"grounded_mechanisms": grounded, "ungrounded_mechanisms": ungrounded, "grounding_score": round(score, 3)}

    def _ground_equations(self, mechanisms, theories, mech_grounding):
        equations = []
        for source in [(mechanisms or []), (theories or [])]:
            for item in source:
                if not isinstance(item, dict): continue
                desc = item.get("description","") + " " + item.get("mathematical_model","")
                # Also read derivation field (LLM stores derivations here)
                derivation = item.get("derivation", "")
                if isinstance(derivation, str):
                    desc += " " + derivation
                elif isinstance(derivation, list):
                    for d in derivation:
                        if isinstance(d, dict):
                            desc += " " + str(d.get("step", "")) + " " + " ".join(str(c) for c in d.get("content", []))
                        else:
                            desc += " " + str(d)
                for match in re.finditer(r"([A-Za-z_][\w]*)\s*=\s*([^,.;\n]{5,80})", desc):
                    var, expr = match.group(1), match.group(2).strip()
                    has_nums = any(c.isdigit() for c in expr)
                    equations.append({"variable": var, "expression": expr[:60], "has_numbers": has_nums, "is_grounded": has_nums})
        grounded = [e for e in equations if e.get("is_grounded")]
        score = len(grounded) / max(1, len(equations)) if equations else 0
        return {"equations": equations[:20], "grounded_equations": grounded, "grounding_score": round(score, 3)}

    def _ground_predictions(self, theories, eq_grounding):
        predictions = []
        for t in (theories or []):
            if not isinstance(t, dict): continue
            for p in (t.get("predictions") or []):
                pred = p.get("statement", p.get("description","")) if isinstance(p, dict) else str(p)
                if not pred: continue
                has_nums = any(c.isdigit() for c in pred)
                has_method = any(w in pred.lower() for w in ["measure","observe","detect","test","experiment","spectroscopy","imaging"])
                is_grounded = has_nums and has_method
                predictions.append({"prediction": pred[:200], "has_numbers": has_nums, "has_test_method": has_method, "is_grounded": is_grounded})
        grounded = [p for p in predictions if p.get("is_grounded")]
        score = len(grounded) / max(1, len(predictions)) if predictions else 0
        return {"predictions": predictions, "grounded_predictions": grounded, "grounding_score": round(score, 3)}
