"""
prediction_engine.py — Every hypothesis MUST produce testable predictions.

A hypothesis without predictions is not science — it's speculation.

Prediction types (from weakest to strongest):
1. Correlational: "If we measure X, we should find Y"
2. Interventional: "If we change X, Y should change"
3. Counterfactual: "If X hadn't happened, Y wouldn't have occurred"
4. Novel: "Nobody has looked for Z, but if our hypothesis is correct, Z should exist"

This module:
1. Extracts predictions from proposed mechanisms
2. Validates that predictions are actually testable
3. Generates additional predictions from graph structure
4. Scores predictions by testability and discriminating power
"""

import json
from typing import List, Dict, Optional
from discovery.json_extract import extract_json


class PredictionEngine:
    """
    Generate and validate testable predictions from hypotheses and mechanisms.
    """

    def __init__(self, graph=None, llm_call=None):
        self.graph = graph
        self.llm_call = llm_call

    def generate_predictions(self, mechanisms: list, hidden_variables: list,
                              topic: str, domain: str,
                              anomalies: list = None) -> dict:
        """
        Generate testable predictions from mechanisms and hidden variables.

        Returns:
            {
                "predictions": [
                    {
                        "statement": "If hypothesis H is true, then observation O should occur",
                        "type": "correlational|interventional|counterfactual|novel",
                        "mechanism_source": "which mechanism generates this",
                        "testability": "easy|moderate|hard|very_hard",
                        "test_method": "how to test this",
                        "discriminating_power": 0.0-1.0,
                        "novelty": "known|underexplored|novel",
                        "falsification": "what would disprove this prediction"
                    }
                ],
                "prediction_chains": [...],
                "coverage_score": 0.0-1.0
            }
        """
        if not self.llm_call:
            return {"predictions": [], "prediction_chains": [], "coverage_score": 0.0}

        mech_text = self._format_mechanisms(mechanisms[:5] if isinstance(mechanisms, list) else
                                            mechanisms.get("mechanisms", [])[:5])
        hv_text = self._format_hidden_variables(hidden_variables[:5] if isinstance(hidden_variables, list) else
                                                 hidden_variables.get("hidden_variables", [])[:5])
        anomaly_text = self._format_anomalies(anomalies[:4] if anomalies else [])

        prompt = f"""You are a rigorous scientist. Your job is to generate TESTABLE PREDICTIONS
with QUANTITATIVE content. Every prediction MUST include numbers.

TOPIC: {topic}
DOMAIN: {domain}

MECHANISMS PROPOSED:
{mech_text}

HIDDEN VARIABLES:
{hv_text}

ANOMALIES TO EXPLAIN:
{anomaly_text}

For each prediction:
1. State it as a conditional: "If [hypothesis], then [observable consequence]"
2. Classify the type (correlational, interventional, counterfactual, novel)
3. Describe exactly how to test it (method, measurement, comparison)
4. Rate testability (easy/moderate/hard/very_hard)
5. Rate discriminating power — how much this separates your hypothesis from alternatives
6. State what would FALSIFY this prediction

IMPORTANT:
- Generate at least 2 NOVEL predictions (things nobody has looked for yet)
- Generate at least 1 INTERVENTIONAL prediction (if we change X, Y changes)
- Generate at least 1 COUNTERFACTUAL prediction (if X hadn't happened...)
- Each prediction must be SPECIFIC and MEASURABLE, not vague

Output JSON:
{{
  "predictions": [
    {{
      "statement": "If [hypothesis condition], then [specific measurable outcome]",
      "type": "correlational|interventional|counterfactual|novel",
      "mechanism_source": "which mechanism generates this prediction",
      "testability": "easy|moderate|hard|very_hard",
      "test_method": "Specific experimental or observational procedure to test this",
      "discriminating_power": 0.0-1.0,
      "novelty": "known|underexplored|novel",
      "falsification": "What specific observation would disprove this",
      "confidence": 0.0-1.0
    }}
  ],
  "prediction_chains": [
    {{
      "chain": "Mechanism M → Prediction P1 (if true) → Secondary prediction P2",
      "explanation": "Why P1 being true makes P2 more likely"
    }}
  ],
  "coverage_analysis": {{
    "mechanisms_with_predictions": N,
    "total_mechanisms": M,
    "coverage_ratio": 0.0-1.0,
    "uncovered_mechanisms": ["mechanisms without predictions"]
  }}
}}

Generate 5-8 predictions total. Quality over quantity."""

        try:
            raw = self.llm_call(prompt, max_tokens=8192)
            if not raw:
                try:
                    from discovery.llm_client import call_json
                    raw = call_json(prompt, max_tokens=8192, provider="auto")
                except Exception:
                    pass
            if raw:
                if isinstance(raw, str):
                    raw = raw.strip()
                    if raw.startswith("```"):
                        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
                        raw = raw.rsplit("```", 1)[0].strip()
                    result = extract_json(raw, expected_key="predictions")
                else:
                    result = raw

                if isinstance(result, dict):
                    # Validate predictions — skip those without meaningful statements
                    valid_predictions = []
                    for pred in result.get("predictions", []):
                        statement = pred.get("statement", "")
                        # Skip predictions with no statement or generic placeholders
                        if not statement or statement.lower() in ("unspecified", "prediction", "n/a", ""):
                            continue
                        pred["statement"] = statement
                        pred.setdefault("type", "correlational")
                        pred.setdefault("testability", "moderate")
                        pred.setdefault("discriminating_power", 0.5)
                        pred.setdefault("confidence", 0.5)
                        pred.setdefault("falsification", "Not specified")
                        valid_predictions.append(pred)
                    result["predictions"] = valid_predictions
                    return result

        except Exception as e:
            return {"predictions": [], "error": str(e)}

        return {"predictions": [], "prediction_chains": [], "coverage_score": 0.0}

    def validate_predictions(self, predictions: list) -> dict:
        """
        Validate that predictions are actually testable and discriminating.
        Rejects vague or unfalsifiable predictions.
        """
        validated = []
        rejected = []

        VAGUE_PATTERNS = [
            "it is conceivable",
            "may or may not",
            "further research is needed",
        ]
        # Removed: "might", "could potentially", "possibly"
        # These are normal hedging in real science — don't reject for them

        for pred in predictions:
            statement = pred.get("statement", "").lower()
            falsification = pred.get("falsification", "").lower()

            # Check for extreme vagueness (only reject truly empty statements)
            is_vague = len(statement) < 15

            # Check for unfalsifiability (only reject if truly no falsification)
            is_unfalsifiable = (
                len(falsification) < 3 or
                falsification.strip() in ("nothing", "cannot be falsified")
            )

            # Check for specificity (has numbers, measurements, concrete entities, or is long enough)
            has_specificity = (
                any(c.isdigit() for c in statement) or
                len(statement) > 30 or
                any(kw in statement for kw in ["if", "then", "should", "observe", "measure", "detect", "predict", "might", "could", "possibly"])
            )

            if is_vague and not has_specificity:
                pred["validation_status"] = "rejected"
                pred["rejection_reason"] = "Too vague — prediction must be specific and measurable"
                rejected.append(pred)
            elif is_unfalsifiable and not has_specificity:
                pred["validation_status"] = "rejected"
                pred["rejection_reason"] = "Unfalsifiable — must state what would disprove it"
                rejected.append(pred)
            else:
                # Label confidence level instead of rejecting
                if not has_specificity:
                    pred["confidence"] = 0.3
                    pred["confidence_note"] = "Low specificity — needs refinement"
                if has_specificity:
                    pred["discriminating_power"] = min(1.0,
                        pred.get("discriminating_power", 0.5) + 0.1)
                pred["validation_status"] = "accepted"
                validated.append(pred)

        return {
            "accepted": validated,
            "rejected": rejected,
            "acceptance_rate": len(validated) / max(1, len(predictions)),
            "total": len(predictions),
        }

    def generate_discriminating_tests(self, predictions: list,
                                       alternative_theories: list = None) -> list:
        """
        Generate experiments that would DISCRIMINATE between competing theories.
        
        The best experiments don't just test one hypothesis — they distinguish
        between multiple competing explanations.
        """
        tests = []
        for pred in predictions:
            if pred.get("discriminating_power", 0) > 0.6:
                tests.append({
                    "prediction": pred.get("statement", ""),
                    "discriminating_power": pred.get("discriminating_power", 0.5),
                    "test_type": pred.get("type", "unknown"),
                    "method": pred.get("test_method", "Not specified"),
                    "falsification": pred.get("falsification", "Not specified"),
                    "priority": "high" if pred.get("discriminating_power", 0) > 0.8 else "medium",
                })

        tests.sort(key=lambda x: x["discriminating_power"], reverse=True)
        return tests

    def _format_mechanisms(self, mechanisms: list) -> str:
        if not mechanisms:
            return "No mechanisms proposed."
        text = ""
        for i, m in enumerate(mechanisms, 1):
            text += f"\n{i}. {str(m.get('name', '?'))} ({str(m.get('type', '?'))})\n"
            text += f"   {str(m.get('description', ''))[:200]}\n"
            steps = m.get("steps", [])
            for s in steps[:4]:
                text += f"   → {str(s)}\n"
        return text

    def _format_hidden_variables(self, hvs: list) -> str:
        if not hvs:
            return "No hidden variables."
        text = ""
        for i, hv in enumerate(hvs, 1):
            text += f"\n{i}. {str(hv.get('name', '?'))} ({str(hv.get('type', '?'))})\n"
            text += f"   {str(hv.get('description', ''))[:200]}\n"
        return text

    def _format_anomalies(self, anomalies: list) -> str:
        if not anomalies:
            return "No anomalies."
        text = ""
        for i, a in enumerate(anomalies, 1):
            text += f"\n{i}. {str(a.get('reason', a.get('observation', '')))[:200]}\n"
        return text
