"""
observability_checker.py - Can we actually measure this prediction?
A prediction you cannot test is not a prediction.
"""
import re

INSTRUMENT_LIMITS = {
    "weak_lensing": {"name": "HST/Euclid", "floor": 0.005, "unit": "kappa"},
    "strong_lensing": {"name": "HST strong lensing", "floor": 0.001, "unit": "kappa"},
    "spectroscopy": {"name": "VLT/Keck", "floor": 0.1, "unit": "km/s"},
    "xray": {"name": "Chandra/XMM", "floor": 0.001, "unit": "counts"},
    "gravitational_wave": {"name": "LIGO/Virgo", "floor": 1e-21, "unit": "strain"},
    "resistivity": {"name": "PPMS", "floor": 1e-9, "unit": "ohm*cm"},
    "magnetometry": {"name": "SQUID", "floor": 1e-8, "unit": "emu"},
    "temperature": {"name": "Dilution fridge", "floor": 0.001, "unit": "K"},
    "pressure": {"name": "Diamond anvil", "floor": 0.1, "unit": "GPa"},
}

class ObservabilityChecker:
    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def check_predictions(self, predictions, domain=""):
        results = []
        for p in (predictions or []):
            pred = p.get("statement", p.get("description","")) if isinstance(p, dict) else str(p)
            if not pred: continue
            check = self._check_single(pred, domain)
            results.append(check)
        accessible = [r for r in results if r["is_accessible"]]
        return {"total": len(results), "accessible": len(accessible),
                "inaccessible": len(results) - len(accessible),
                "accessibility_rate": len(accessible) / max(1, len(results)),
                "details": results}

    def _check_single(self, pred, domain):
        pred_lower = pred.lower()
        magnitudes = re.findall(r"(\d[\d\.eE\+\-]*)\s*(\w+)", pred)
        instrument = self._identify_instrument(pred_lower)
        is_accessible = True
        reason = ""
        if instrument:
            floor = instrument.get("floor", 0)
            for mag_str, unit in magnitudes:
                try:
                    mag = float(mag_str)
                    if 0 < mag < floor:
                        is_accessible = False
                        reason = f"Signal {mag} below {instrument[chr(110)+chr(97)+chr(109)+chr(101)]} floor ({floor})"
                        break
                except: continue
        return {"prediction": pred[:150], "is_accessible": is_accessible,
                "reason": reason, "instrument": instrument.get("name","unknown") if instrument else "unknown"}

    def _identify_instrument(self, pred):
        if "lensing" in pred or "convergence" in pred: return INSTRUMENT_LIMITS["weak_lensing"]
        if "spectroscop" in pred: return INSTRUMENT_LIMITS["spectroscopy"]
        if "resistiv" in pred: return INSTRUMENT_LIMITS["resistivity"]
        if "temperature" in pred or "tc " in pred: return INSTRUMENT_LIMITS["temperature"]
        if "pressure" in pred: return INSTRUMENT_LIMITS["pressure"]
        if "cross-section" in pred: return INSTRUMENT_LIMITS["gravitational_wave"]
        return None

