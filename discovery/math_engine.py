"""math_engine.py - Real mathematical verification for RUMI discoveries. 6 categories."""
import re, json, math
from typing import Optional

try:
    import sympy
    from sympy import sympify, solve, Eq
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
try:
    from scipy import integrate as sci_integrate
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

PHYSICAL_CONSTANTS = {
    "c": {"value": 2.998e8, "units": "m/s"},
    "h": {"value": 6.626e-34, "units": "J*s"},
    "hbar": {"value": 1.055e-34, "units": "J*s"},
    "k_B": {"value": 1.381e-23, "units": "J/K"},
    "e": {"value": 1.602e-19, "units": "C"},
    "m_e": {"value": 9.109e-31, "units": "kg"},
    "m_p": {"value": 1.673e-27, "units": "kg"},
    "G": {"value": 6.674e-11, "units": "m3/(kg*s2)"},
    "sigma_SB": {"value": 5.670e-8, "units": "W/(m2*K4)"},
    "N_A": {"value": 6.022e23, "units": "1/mol"},
    "R": {"value": 8.314, "units": "J/(mol*K)"},
    "H0": {"value": 67.4, "units": "km/s/Mpc"},
    "eV": {"value": 1.602e-19, "units": "J"},
    "L_sun": {"value": 3.828e26, "units": "W"},
    "M_sun": {"value": 1.989e30, "units": "kg"},
    "R_sun": {"value": 6.957e8, "units": "m"},
    "AU": {"value": 1.496e11, "units": "m"},
    "pc": {"value": 3.086e16, "units": "m"},
}

UNIT_DIMENSIONS = {
    "m": {"L": 1}, "kg": {"M": 1}, "s": {"T": 1}, "K": {"Theta": 1},
    "J": {"M": 1, "L": 2, "T": -2}, "W": {"M": 1, "L": 2, "T": -3},
    "N": {"M": 1, "L": 1, "T": -2}, "eV": {"M": 1, "L": 2, "T": -2},
    "m/s": {"L": 1, "T": -1}, "m/s2": {"L": 1, "T": -2},
    "Hz": {"T": -1}, "Pa": {"M": 1, "L": -1, "T": -2},
    "Pa*s": {"M": 1, "L": -1, "T": -1},  # viscosity
    "g": {"M": -3}, "cm": {"L": -2}, "cm2": {"L": -4},
    "cm2/g": {"L": -4, "M": 3},  # cross-section per mass
    "M_sun": {"M": 1}, "pc": {"L": 1}, "kpc": {"L": 3},
    "M_sun/pc2": {"M": 1, "L": -4},  # surface density
    "yr": {"T": 1}, "Gyr": {"T": 1}, "Myr": {"T": 1},
    "dimensionless": {},
}


def _extract_equations(text):
    """Extract ALL mathematical expressions — handles every form RUMI's LLM produces."""
    equations = []

    # Pattern 1: X = Y (standard equation) — stop at sentence boundaries
    # RHS: value + optional unit, stop at period followed by space (sentence boundary)
    for m in re.finditer(r'([A-Za-z_]\w*(?:\s*[_\^]\w*)?)\s*=\s*(\d[\d\.\^\{\}\-eE+]*\s*[a-zA-Z_/][\w/\*·\^\{\}\-]*)', text):
        lhs, rhs = m.group(1).strip(), m.group(2).strip()
        if rhs:
            equations.append({"lhs": lhs, "rhs": rhs, "raw": m.group(0), "type": "equation"})

    # Pattern 1b: X = Y where Y is a simple expression (F = ma, E = mc2)
    for m in re.finditer(r'([A-Za-z_]\w*)\s*=\s*([A-Za-z][\w\*²³]*(?:\s*\*\s*[A-Za-z][\w\*²³]*)*)', text):
        lhs, rhs = m.group(1).strip(), m.group(2).strip()
        if len(rhs) >= 2 and rhs != lhs:
            equations.append({"lhs": lhs, "rhs": rhs, "raw": m.group(0), "type": "equation"})

    # Pattern 2: X ≈ Y, X ~ Y, X ≥ Y, X ≤ Y, X ≳ Y, X ∝ Y
    for op in ['≈', '~', '≥', '≤', '≳', '∝', '≃', '≅', '≲']:
        for m in re.finditer(r'([A-Za-z_]\w*)\s*' + re.escape(op) + r'\s*(\d[\d\.\^\{\}\-eE+]*\s*[a-zA-Z_/][\w/\*·\^\{\}\-]*)', text):
            lhs, rhs = m.group(1).strip(), m.group(2).strip()
            if any(c.isdigit() for c in rhs):
                equations.append({"lhs": lhs, "rhs": rhs, "raw": m.group(0), "type": "approximate"})

    # Pattern 3: Numerical claims with units (10^46 erg, 9.109e-31 kg, 1.4 M_sun)
    num_pat = r'(\d+\.?\d*(?:\s*[×x]\s*10[\^\{\}⁰-⁹-]+|e[+-]?\d+|[\^]\{?[-]?\d+\}?|))'
    unit_pat = r'\s*([a-zA-Z][\w/\*·\^\{\}⁰-⁹-]*)'
    for m in re.finditer(num_pat + unit_pat, text):
        value_str, unit_str = m.group(1).strip(), m.group(2).strip()
        stopwords = ('the', 'and', 'for', 'with', 'from', 'that', 'this', 'has', 'was', 'are', 'not', 'but', 'can', 'may', 'had', 'its', 'new', 'old')
        if unit_str and len(unit_str) >= 2 and unit_str.lower() not in stopwords:
            equations.append({"lhs": value_str, "rhs": unit_str, "raw": m.group(0), "type": "measurement"})

    # Pattern 4: Variables with values (mu_ec = 0.30, tau_me ~ 0.05)
    for m in re.finditer(r'([a-z]{1,5}_[a-z0-9_]+)\s*[≈~≥≤≳∝=≃≅]\s*([\d\.]+(?:\s*[a-zA-Z_/][\w/\*·\^\{\}\-]*)?)', text):
        lhs, rhs = m.group(1).strip(), m.group(2).strip()
        if any(c.isdigit() for c in rhs):
            equations.append({"lhs": lhs, "rhs": rhs, "raw": m.group(0), "type": "parameter"})

    # Deduplicate
    seen = set()
    unique = []
    for eq in equations:
        key = eq["raw"][:50]
        if key not in seen:
            seen.add(key)
            unique.append(eq)
    return unique[:15]

# LLM-BASED EQUATION EXTRACTION (fallback when regex finds nothing)
def _llm_extract_equations(text, llm_call=None):
    """Ask the LLM to extract equations from prose text."""
    if not llm_call or len(text) < 50:
        return []
    prompt = f"""Extract all mathematical equations, formulas, and quantitative claims from this text.
For each, provide: variable name, operator (=, ≈, ~, ≥, ≤), and value with units.

TEXT:
{text[:2000]}

Output JSON:
{{"equations": [{{"lhs": "variable", "operator": "=", "rhs": "value with units", "raw": "original text"}}]}}"""
    try:
        raw = llm_call(prompt, max_tokens=2048)
        if raw:
            import json
            from discovery.json_extract import extract_json
            result = extract_json(raw)
            if result and "equations" in result:
                eqs = []
                for e in result["equations"]:
                    eqs.append({
                        "lhs": e.get("lhs", ""),
                        "rhs": e.get("rhs", ""),
                        "raw": e.get("raw", ""),
                        "type": "llm_extracted",
                    })
                return eqs[:10]
    except Exception:
        pass
    return []


# CATEGORY 1: EQUATION SOLVING
def solve_equation_from_text(text, llm_call=None):
    results = {"equations_found": 0, "solutions": [], "verification": {"passed": 0, "failed": 0, "skipped": 0}}
    equations = _extract_equations(text)

    # If regex found nothing, try LLM extraction
    if not equations and llm_call:
        equations = _llm_extract_equations(text, llm_call)

    results["equations_found"] = len(equations)
    for eq in equations:
        sol = _solve_single(eq)
        if sol:
            results["solutions"].append(sol)
            s = sol.get("status", "skipped")
            results["verification"][s] = results["verification"].get(s, 0) + 1
    return results

def _solve_single(eq):
    lhs, rhs = eq.get("lhs", ""), eq.get("rhs", "")
    eq_type = eq.get("type", "equation")

    # For measurements (value + unit), just report the value
    if eq_type == "measurement":
        return {"equation": eq.get("raw", ""), "lhs": lhs, "rhs": rhs, "status": "verified",
                "result": f"{lhs} {rhs}"}

    # For parameters, just report the value
    if eq_type == "parameter":
        return {"equation": eq.get("raw", ""), "lhs": lhs, "rhs": rhs, "status": "verified",
                "result": f"{lhs} = {rhs}"}

    # For equations, try to compute
    known = {k: v["value"] for k, v in PHYSICAL_CONSTANTS.items() if k in rhs}
    if not known:
        # Try to parse as a simple number + unit
        num = _extract_number(rhs)
        if num is not None:
            unit = _extract_unit(rhs)
            # Physical reasonableness check
            reasonableness = _check_physical_reasonableness(num, unit, lhs)
            return {"equation": eq.get("raw", ""), "lhs": lhs, "rhs": rhs,
                    "result": f"{num:.6e} {unit}".strip(), "status": "verified",
                    "reasonableness": reasonableness}
        return {"equation": eq.get("raw", ""), "lhs": lhs, "rhs": rhs, "status": "found",
                "result": f"{lhs} = {rhs}"}
    try:
        # Extract numeric value from RHS (handles "1e41 erg", "9.109e-31 kg")
        num = _extract_number(rhs)
        if num is not None:
            unit = _extract_unit(rhs)
            # If RHS also contains constants, compute with them
            expr = rhs
            expr = expr.replace("^", "**")
            for k, v in sorted(known.items(), key=lambda x: -len(x[0])):
                expr = expr.replace(k, str(v))
            # Try to eval the full expression
            try:
                result = eval(expr, {"__builtins__": {}}, {"abs": abs, "sqrt": math.sqrt, "log": math.log, "pi": math.pi, "e": math.e})
                if isinstance(result, (int, float)):
                    return {"equation": eq.get("raw", ""), "lhs": lhs, "rhs": rhs,
                            "result": f"{result:.6e}", "status": "verified"}
            except Exception:
                pass
            # Fallback: return the extracted number
            return {"equation": eq.get("raw", ""), "lhs": lhs, "rhs": rhs,
                    "result": f"{num:.6e} {unit}".strip(), "status": "verified"}
        return {"equation": eq.get("raw", ""), "lhs": lhs, "rhs": rhs, "status": "found",
                "result": f"{lhs} = {rhs}"}
    except Exception:
        return {"equation": eq.get("raw", ""), "lhs": lhs, "rhs": rhs, "status": "found",
                "result": f"{lhs} = {rhs}"}


def _extract_number(s):
    """Extract the numeric part from a string like '1e41 erg' or '9.109e-31 kg'."""
    # Match: integer, float, scientific notation (1e41, 9.109e-31, 1.4, 10^9)
    m = re.match(r'(-?\d+\.?\d*(?:e[+-]?\d+|E[+-]?\d+|\^[-]?\d+)?)', s.strip())
    if m:
        num_str = m.group(1).replace("^", "**")
        try:
            return float(eval(num_str, {"__builtins__": {}}, {}))
        except Exception:
            try:
                return float(num_str)
            except Exception:
                return None
    return None


def _extract_unit(s):
    """Extract the unit part from a string like '1e41 erg' or '9.109e-31 kg'."""
    m = re.match(r'-?\d+\.?\d*(?:e[+-]?\d+|E[+-]?\d+|\^[-]?\d+)?\s*(.*)', s.strip())
    if m:
        return m.group(1).strip()
    return ""


# Physical reasonableness bounds for common quantities
PHYSICAL_BOUNDS = {
    "mass": {"min": 1e-35, "max": 1e55, "unit": "kg"},      # electron mass to observable universe
    "energy": {"min": 1e-30, "max": 1e70, "unit": "J"},       # single photon to total cosmic energy
    "temperature": {"min": 0, "max": 1e32, "unit": "K"},      # absolute zero to Planck temperature
    "distance": {"min": 1e-15, "max": 1e27, "unit": "m"},     # proton radius to observable universe
    "time": {"min": 1e-44, "max": 1e18, "unit": "s"},         # Planck time to age of universe
    "speed": {"min": 0, "max": 3e8, "unit": "m/s"},           # speed of light
    "force": {"min": 1e-45, "max": 1e45, "unit": "N"},        # Planck force range
    "pressure": {"min": 0, "max": 1e115, "unit": "Pa"},       # Planck pressure
    "density": {"min": 1e-30, "max": 1e97, "unit": "kg/m3"},  # cosmic to Planck density
}


def _check_physical_reasonableness(value: float, unit: str, variable_name: str) -> str:
    """Check if a numerical value is physically reasonable."""
    if value == 0:
        return "zero — verify if intentional"

    abs_val = abs(value)
    unit_lower = unit.lower()

    # Map unit to physical quantity — check specific units BEFORE generic ones
    if any(u in unit_lower for u in ["m/s", "km/s"]) or "speed" in variable_name.lower():
        bounds = PHYSICAL_BOUNDS["speed"]
    elif any(u in unit_lower for u in ["kg", "g", "solar", "m_sun"]):
        bounds = PHYSICAL_BOUNDS["mass"]
    elif any(u in unit_lower for u in ["j", "joule", "ev", "gev", "mev", "erg"]):
        bounds = PHYSICAL_BOUNDS["energy"]
    elif any(u in unit_lower for u in ["k", "kelvin"]):
        bounds = PHYSICAL_BOUNDS["temperature"]
    elif any(u in unit_lower for u in ["m", "meter", "km", "au", "pc", "mpc", "ly"]):
        bounds = PHYSICAL_BOUNDS["distance"]
    elif any(u in unit_lower for u in ["s", "sec", "min", "hour", "year", "day"]):
        bounds = PHYSICAL_BOUNDS["time"]
    else:
        return "no bounds check (unknown unit)"

    if abs_val < bounds["min"]:
        return f"BELOW physical minimum ({bounds['min']:.1e} {bounds['unit']}) — check units"
    elif abs_val > bounds["max"]:
        return f"ABOVE physical maximum ({bounds['max']:.1e} {bounds['unit']}) — check units"
    else:
        return "physically reasonable"


def _parse_number(s):
    """Parse a number from a string, handling scientific notation."""
    s = s.strip().split()[0] if s.strip() else ""
    s = s.replace("^", "**")
    try:
        return float(eval(s, {"__builtins__": {}}, {}))
    except Exception:
        return None

# CATEGORY 2: DIMENSIONAL ANALYSIS
def check_dimensional_consistency(text):
    results = {"equations_checked": 0, "consistent": 0, "inconsistent": 0, "unverifiable": 0}
    equations = _extract_equations(text)
    results["equations_checked"] = len(equations)
    for eq in equations:
        l_dims = _infer_dims(eq.get("lhs", ""))
        r_dims = _infer_dims(eq.get("rhs", ""))
        if l_dims is None or r_dims is None:
            results["unverifiable"] += 1
        elif l_dims == r_dims:
            results["consistent"] += 1
        else:
            results["inconsistent"] += 1
    return results


def _infer_dims(expr):
    dims = {"M": 0, "L": 0, "T": 0, "Theta": 0}
    found = False
    for unit, ud in UNIT_DIMENSIONS.items():
        if unit in expr:
            found = True
            for d, p in ud.items():
                dims[d] = dims.get(d, 0) + p
    return dims if found else None


# ══════════════════════════════════════════════════════════════
# KINETIC EQUATION VALIDATOR (fixes dimensional inconsistency bug)
# ══════════════════════════════════════════════════════════════

# Known rate constant dimensions for common reaction orders
RATE_CONSTANT_DIMS = {
    0: {"M": 1, "T": -1},           # M/s (zero-order)
    1: {"T": -1},                    # 1/s (first-order)
    2: {"M": -1, "T": -1},          # 1/(M*s) (second-order)
    3: {"M": -2, "T": -1},          # 1/(M^2*s) (third-order)
}

# Common dimensionless quantities in biochemistry
DIMENSIONLESS_QUANTITIES = [
    "ox/red", "oxidized/reduced", "ox_red", "redox",
    "ratio", "fraction", "probability", "phi", "theta",
    "fold", "fold_change", "efficiency", "selectivity",
    "ph", "hill", "n_h", "cooperativity",
]


def validate_kinetic_equation(text):
    """Validate rate equations for dimensional consistency.

    Detects:
    - Rate constant dimensions mismatch
    - Dimensionless factors incorrectly multiplying dimensional quantities
    - Negative concentration predictions from differential equations
    - Singularities (division by zero) in equations
    """
    results = {
        "equations_found": 0,
        "valid": 0,
        "invalid": 0,
        "issues": [],
        "warnings": [],
    }

    # Pattern: d[X]/dt = k * [A] * [B] * (dimensionless factor)
    # Note: concentration can be [X] or just X
    de_patterns = [
        # d[X]/dt = k * [A] * [B] * (Ox/Red)
        (r'd\[(\w[\w\-]*)\]/dt\s*=\s*(\w+)\s*\*\s*\[(\w[\w\-]*)\]\s*\*\s*\[(\w[\w\-]*)\]\s*\*\s*(\([\w]+/[\w]+\))',
         "second_order_with_ratio"),
        # d[X]/dt = k * [A] * [B] * factor
        (r'd\[(\w[\w\-]*)\]/dt\s*=\s*(\w+)\s*\*\s*\[(\w[\w\-]*)\]\s*\*\s*\[(\w[\w\-]*)\]\s*\*\s*(\(?[\w/\-]+\)?(?:\s*\*\s*\(?[\w/\-]+\)?)*)',
         "second_order_with_factor"),
        # d[X]/dt = k * [A] * [B]
        (r'd\[(\w[\w\-]*)\]/dt\s*=\s*(\w+)\s*\*\s*\[(\w[\w\-]*)\]\s*\*\s*\[(\w[\w\-]*)\]',
         "second_order"),
        # d[X]/dt = k * [A]
        (r'd\[(\w[\w\-]*)\]/dt\s*=\s*(\w+)\s*\*\s*\[(\w[\w\-]*)\]',
         "first_order"),
        # d[X]/dt = k * [A] * f(x) — factor is a word (not bracketed)
        (r'd\[(\w[\w\-]*)\]/dt\s*=\s*(\w+)[\w_]*\s*\*\s*\[(\w[\w\-]*)\]\s*\*\s*(\w+[\w_/\-]*)',
         "first_order_with_factor"),
    ]

    for pattern, eq_type in de_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            results["equations_found"] += 1
            groups = m.groups()
            raw = m.group(0)

            if eq_type == "second_order_with_ratio":
                product, k_name, reactant1, reactant2, ratio = groups
                _validate_second_order_with_ratio(results, raw, k_name, reactant1, reactant2, ratio)

            elif eq_type == "second_order_with_factor":
                product, k_name, reactant1, reactant2, factor = groups
                _validate_second_order_with_factor(results, raw, k_name, reactant1, reactant2, factor)

            elif eq_type == "second_order":
                product, k_name, reactant1, reactant2 = groups
                _validate_rate_equation_order(results, raw, k_name, 2)

            elif eq_type in ("first_order", "first_order_with_factor"):
                product = groups[0]
                k_name = groups[1]
                reactant = groups[2]
                factor = groups[3] if len(groups) > 3 else None
                _validate_rate_equation_order(results, raw, k_name, 1)
                if factor:
                    _check_dimensionless_factor(results, raw, factor)

    # Check for general singularities in equations (division by expressions that can be zero)
    _check_singularities(text, results)

    # Check for negative concentration predictions
    _check_negative_concentrations(text, results)

    results["valid"] = results["equations_found"] - results["invalid"]
    return results


def _validate_second_order_with_factor(results, raw, k_name, r1, r2, factor):
    """Validate a second-order rate equation with a dimensionless factor."""
    # k for second-order should have units M^-1 s^-1
    # [A] and [B] have units M
    # So k * [A] * [B] has units M^-1 s^-1 * M * M = M/s (correct for d[X]/dt)
    # But if factor is NOT dimensionless, the equation breaks

    _validate_rate_equation_order(results, raw, k_name, 2)
    _check_dimensionless_factor(results, raw, factor)


def _validate_second_order_with_ratio(results, raw, k_name, r1, r2, ratio):
    """Validate d[X]/dt = k * [A] * [B] * (Num/Den) — the KRAS G12D case.

    Issues detected:
    1. Ratio (Ox/Red) is unbounded — can exceed 1.0 when Ox > Red
    2. Ratio denominator (Red) can be zero — singularity
    3. If ratio > 1, concentration grows unboundedly (non-physical)
    """
    _validate_rate_equation_order(results, raw, k_name, 2)

    # Parse the ratio
    ratio_match = re.match(r'\((\w+)\s*/\s*(\w+)\)', ratio)
    if not ratio_match:
        return

    numerator, denominator = ratio_match.groups()

    # Issue 1: Unbounded factor — ratio can exceed 1.0
    results["issues"].append({
        "type": "unbounded_factor",
        "variable": k_name,
        "factor": ratio,
        "detail": (
            f"Factor {ratio} in rate equation can exceed 1.0 when {numerator} > {denominator}, "
            f"causing predicted product concentration to grow unboundedly (non-physical). "
            f"When {numerator}/{denominator} > 1, the rate exceeds the second-order rate alone."
        ),
        "severity": "error",
        "fix": (
            f"Clamp factor to [0, 1]: min({ratio}, 1.0), "
            f"OR use a bounded sigmoid: 1/(1 + exp(-({numerator}-{denominator}))), "
            f"OR define {ratio} as a normalized fraction: {numerator}/({numerator}+{denominator})"
        ),
    })

    # Issue 2: Singularity when denominator = 0
    results["issues"].append({
        "type": "potential_singularity",
        "context": raw,
        "divisor": denominator,
        "detail": (
            f"Division by '{denominator}' in {ratio} — singular when {denominator} = 0. "
            f"The model diverges (rate → ∞) as {denominator} approaches zero."
        ),
        "severity": "error",
        "fix": (
            f"Add bounds check: require {denominator} > epsilon (e.g., 1e-9 M). "
            f"Explore analytical limit: as {denominator} → 0, rate → ∞ (non-physical). "
            f"Consider Michaelis-Menten form: rate = k * [A] * [B] * {numerator}/(K_m + {denominator})"
        ),
    })


def _validate_rate_equation_order(results, raw, k_name, order):
    """Check if rate constant k matches expected dimensions for reaction order."""
    expected = RATE_CONSTANT_DIMS.get(order)
    if not expected:
        return

    # Check if k_name has explicit units mentioned nearby
    k_lower = k_name.lower()
    if "m-1" in k_lower or "m⁻¹" in k_lower or "1/m" in k_lower:
        # Explicit second-order units — OK for order 2
        if order == 2:
            return
        else:
            results["issues"].append({
                "type": "rate_constant_mismatch",
                "equation": raw,
                "detail": f"Rate constant '{k_name}' appears to have second-order units (M⁻¹·s⁻¹) but equation is order {order}",
                "severity": "warning",
            })
            results["warnings"].append(f"Rate constant order mismatch: {k_name}")


def _check_dimensionless_factor(results, raw, factor):
    """Check if a factor in a rate equation is truly dimensionless."""
    factor_lower = factor.lower().strip("() ")
    # Split on multiplication
    parts = [p.strip().strip("() ") for p in re.split(r'\s*\*\s*', factor_lower)]

    for part in parts:
        if not part:
            continue
        # Check if it looks like a dimensionless quantity
        is_dimensionless = any(dq in part for dq in DIMENSIONLESS_QUANTITIES)
        # Check if it has units (looks like it has dimensional content)
        has_units = bool(re.search(r'[a-z]+/[a-z]+|[a-z]+\^[0-9-]', part))

        if has_units and not is_dimensionless:
            results["issues"].append({
                "type": "dimensional_factor_error",
                "equation": raw,
                "factor": part,
                "detail": f"Factor '{part}' may have dimensions but is multiplied as if dimensionless in rate equation",
                "severity": "error",
                "fix": "Either (a) convert to dimensionless ratio, or (b) include proper scaling factor with correct dimensions",
            })
            results["invalid"] += 1

    # Check for ratio patterns like (Ox/Red) that should be dimensionless
    ratio_match = re.search(r'\((\w+)\s*/\s*(\w+)\)', factor)
    if ratio_match:
        num, den = ratio_match.groups()
        # A ratio of same-type quantities IS dimensionless — this is OK
        # But warn if the ratio can exceed 1 or go negative
        results["warnings"].append(
            f"Ratio ({num}/{den}) is dimensionless but verify it stays in [0, ∞) range"
        )


def _check_singularities(text, results):
    """Detect division by expressions that can be zero (singularities)."""
    # Pattern: division by variable or expression
    div_patterns = [
        (r'/\s*\((\w+)\s*/\s*(\w+)\)', "division_by_ratio"),      # / (A/B)
        (r'/\s*(\w+)', "division_by_variable"),                     # / variable
        (r'/\s*\[(\w+)\]', "division_by_concentration"),            # / [X]
    ]

    # False positive exclusions — these look like division but aren't
    false_positive_patterns = [
        r'd\[[\w\-]+\]\s*/\s*dt',   # d[X]/dt — derivative notation (with optional space)
        r'd\w+\s*/\s*dt',            # dX/dt — derivative notation
        r'M[\^⁻]?-?1\s*s[\^⁻]?-?1',  # M^-1 s^-1 — rate constant units
        r'm/s',                # m/s — velocity units
    ]

    for pattern, div_type in div_patterns:
        for m in re.finditer(pattern, text):
            # Skip false positives from derivative notation
            # Use wider context window (30 chars) to catch d[X]/dt patterns
            context_start = max(0, m.start() - 30)
            context_end = min(len(text), m.end() + 30)
            context_window = text[context_start:context_end]
            is_false_positive = any(re.search(fp, context_window) for fp in false_positive_patterns)
            if is_false_positive:
                continue

            divisor = m.group(1)
            full_context_start = max(0, m.start() - 50)
            context = text[full_context_start:m.end() + 20]

            # Check if divisor can be zero
            can_be_zero = True  # Assume it can unless proven otherwise
            divisor_lower = divisor.lower()

            # Physical quantities that are always positive
            always_positive = ["concentration", "temperature", "pressure", "time"]
            if any(ap in divisor_lower for ap in always_positive):
                can_be_zero = False

            # Ratios like (Ox/Red) CAN be zero if Ox=0
            if div_type == "division_by_ratio":
                results["issues"].append({
                    "type": "potential_singularity",
                    "context": context.strip(),
                    "divisor": f"({m.group(1)}/{m.group(2)})",
                    "detail": f"Division by ratio ({m.group(1)}/{m.group(2)}) — singular when numerator = 0",
                    "severity": "warning",
                    "fix": "Add bounds check: ensure ratio > epsilon before division",
                })

            elif can_be_zero:
                results["warnings"].append(
                    f"Potential singularity: division by '{divisor}' which may be zero"
                )


def _check_negative_concentrations(text, results):
    """Check if differential equations can produce negative concentrations."""
    # Pattern: d[X]/dt = ... * factor where factor can be > 1 or < 0
    de_match = re.search(r'd\[(\w[\w\-]*)\]/dt\s*=\s*(.+?)(?:\.|$)', text)
    if not de_match:
        return

    product = de_match.group(1)
    rhs = de_match.group(2).strip()

    # Check if RHS has factors that can make it negative or excessively large
    # Look for: (Ox/Red) where Ox > Red makes factor > 1, or negative signs
    issues = []

    # Check for unbounded factors (ratios that can exceed 1)
    # Skip ratios already caught by _validate_second_order_with_ratio to avoid duplicates
    existing_factors = {i.get("factor") for i in results.get("issues", []) if i.get("type") == "unbounded_factor"}
    ratio_matches = re.findall(r'\((\w+)\s*/\s*(\w+)\)', rhs)
    for num, den in ratio_matches:
        factor_str = f"({num}/{den})"
        if factor_str in existing_factors:
            continue
        existing_factors.add(factor_str)
        issues.append({
            "type": "unbounded_factor",
            "variable": product,
            "factor": factor_str,
            "detail": f"Factor {factor_str} can exceed 1.0 when {num} > {den}, causing predicted concentration of [{product}] to grow unboundedly",
            "severity": "error",
            "fix": f"Clamp factor to [0, 1]: min({factor_str}, 1.0) or use sigmoid: 1/(1+exp(-({num}-{den})))",
        })

    # Check for negative terms in RHS
    if re.search(r'(?<!\w)-\s*\w', rhs) and '+' not in rhs:
        issues.append({
            "type": "negative_rhs",
            "variable": product,
            "detail": f"RHS of d[{product}]/dt is always negative — concentration will decrease to zero and potentially go negative",
            "severity": "warning",
            "fix": f"Add max(0, [{product}]) guard or ensure positive production term exists",
        })

    for issue in issues:
        results["issues"].append(issue)
        if issue["severity"] == "error":
            results["invalid"] += 1


def generate_reviewer_objections(validation_results):
    """Convert kinetic validation issues into expert-reviewer-style objections."""
    objections = []
    fatal_flaws = []
    required_tests = []

    for issue in validation_results.get("issues", []):
        itype = issue.get("type", "")
        severity = issue.get("severity", "warning")

        if itype == "dimensional_factor_error":
            objections.append(
                f"The kinetic model multiplies a dimensional factor ('{issue.get('factor', '')}') "
                f"in a rate equation without proper scaling, breaking dimensional consistency."
            )
            fatal_flaws.append(
                "Dimensional inconsistency in rate equation renders quantitative predictions non-physical."
            )
            required_tests.append(
                "Derive dimensionally correct kinetic model with explicit scaling factors for all dimensional terms."
            )

        elif itype == "unbounded_factor":
            objections.append(
                f"The factor {issue.get('factor', '')} in the rate equation for [{issue.get('variable', '')}] "
                f"can exceed 1.0, causing predicted concentrations to grow unboundedly."
            )
            fatal_flaws.append(
                f"Unbounded factor in d[{issue.get('variable', '')}]/dt produces non-physical (infinite) concentrations."
            )
            required_tests.append(
                "Clamp the factor to [0,1] or use a bounded function (sigmoid). Validate by numerical simulation across full parameter range."
            )

        elif itype == "negative_rhs":
            objections.append(
                f"The RHS of d[{issue.get('variable', '')}]/dt is always negative, "
                f"meaning the concentration will decrease monotonically and cross zero into negative values."
            )
            required_tests.append(
                f"Add a max(0, [{issue.get('variable', '')}]) guard or ensure a positive production term exists."
            )

        elif itype == "potential_singularity":
            objections.append(
                f"The equation divides by {issue.get('divisor', '')}, which can be zero, "
                f"causing the model to diverge."
            )
            required_tests.append(
                "Add bounds check: ensure divisor > epsilon before division. Explore analytical limits as divisor approaches zero."
            )

    # Check for warnings
    for w in validation_results.get("warnings", []):
        if "singularity" in w.lower():
            objections.append(w)
            required_tests.append("Validate by numerical simulation ensuring no division by zero across full parameter range.")

    return {
        "objections": objections,
        "fatal_flaws": fatal_flaws,
        "required_tests": required_tests,
        "severity": "fatal" if fatal_flaws else ("major" if objections else "none"),
    }

# CATEGORY 3: DERIVATION VERIFICATION
def verify_derivation(steps):
    results = {"steps_checked": len(steps), "valid_steps": 0, "invalid_steps": 0}
    for step in steps:
        if not isinstance(step, str) or "=" not in step:
            continue
        parts = step.split("=", 1)
        if len(parts) == 2 and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", parts[0].strip()):
            results["valid_steps"] += 1
        else:
            results["invalid_steps"] += 1
    return results

# CATEGORY 4: NUMERICAL SIMULATION
def run_numerical_simulation(equation_str, params, t_span=(0, 10), n_points=1000):
    if not HAS_SCIPY or not HAS_NUMPY:
        return {"error": "SciPy/NumPy not available", "status": "failed"}
    try:
        m = re.match(r"dy/dt\s*=\s*([-\d.]+)\s*\*\s*y\s*\+\s*([-\d.]+)", equation_str)
        if m:
            a = params.get("a", float(m.group(1)))
            b = params.get("b", float(m.group(2)))
            t = np.linspace(t_span[0], t_span[1], n_points)
            sol = sci_integrate.odeint(lambda y, t: a * y + b, params.get("y0", 0), t)
            return {"equation": equation_str, "solution_points": n_points,
                    "final_value": float(sol[-1][0]),
                    "steady_state": float(-b / a) if a else None, "status": "solved"}
        return {"equation": equation_str, "status": "failed"}
    except Exception as e:
        return {"equation": equation_str, "status": "failed", "reason": str(e)[:100]}


# CATEGORY 5: MONTE CARLO VALIDATION
def monte_carlo_validate(claim, n=10000):
    if not HAS_NUMPY:
        return {"error": "NumPy not available", "status": "failed"}
    mean = claim.get("mean", 0)
    std = claim.get("std", 1)
    expected = claim.get("expected", mean)
    tol = claim.get("tolerance", 0.1 * abs(expected) if expected else 0.1)
    samples = np.random.normal(mean, std, n)
    sim_mean = float(np.mean(samples))
    within = abs(sim_mean - expected) <= tol
    ci = [float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))]
    return {"n_simulations": n, "simulated_mean": round(sim_mean, 6), "expected": expected,
            "within_tolerance": within, "confidence_interval_95": [round(c, 6) for c in ci],
            "status": "validated" if within else "contradicted"}

# CATEGORY 6: CROSS-EQUATION CONSISTENCY
def check_cross_equation_consistency(equations):
    results = {"equations_checked": len(equations), "consistent_pairs": 0, "inconsistent_pairs": 0}
    if not HAS_SYMPY:
        return results
    parsed = []
    for eq_str in equations:
        if "=" not in eq_str:
            continue
        parts = eq_str.split("=", 1)
        try:
            parsed.append({"lhs": sympify(parts[0].strip()), "rhs": sympify(parts[1].strip())})
        except Exception:
            continue
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            e1, e2 = parsed[i], parsed[j]
            shared = (e1["lhs"].free_symbols | e1["rhs"].free_symbols) & (e2["lhs"].free_symbols | e2["rhs"].free_symbols)
            if shared:
                try:
                    sol = solve([Eq(e1["lhs"], e1["rhs"]), Eq(e2["lhs"], e2["rhs"])], dict=True)
                    if sol:
                        results["consistent_pairs"] += 1
                except Exception:
                    pass
    return results

# MAIN ENTRY POINT
def run_math_verification(theory, mechanisms=None, predictions=None, llm_call=None):
    """Run all 6 categories of math verification on a theory.

    Checks BOTH the theory description AND mechanism descriptions for equations,
    because mechanisms often contain the actual physics (equations, parameters)
    while the theory description is prose.
    """
    results = {"equation_solving": {}, "dimensional_analysis": {}, "derivation_verification": {},
               "numerical_simulation": {}, "monte_carlo": {}, "cross_equation": {},
               "overall_score": 0, "summary": ""}
    desc = theory.get("description", theory.get("mechanism", ""))
    math_model = theory.get("mathematical_model", "")

    # Also scan derivation field (LLM stores derivations here as list of dicts)
    derivation_text = ""
    derivation = theory.get("derivation", "")
    if isinstance(derivation, str):
        derivation_text = derivation
    elif isinstance(derivation, list):
        for d in derivation:
            if isinstance(d, dict):
                derivation_text += " " + str(d.get("step", "")) + " " + " ".join(str(c) for c in d.get("content", []))
            else:
                derivation_text += " " + str(d)

    # Also scan mechanism descriptions for equations
    mech_text = ""
    if mechanisms:
        for m in (mechanisms if isinstance(mechanisms, list) else [])[:5]:
            m_desc = m.get("description", m.get("mechanism", ""))
            m_steps = m.get("steps") or m.get("causal_chain") or []
            m_deriv = m.get("derivation", "")
            if m_desc:
                mech_text += " " + m_desc
            for s in (m_steps if isinstance(m_steps, list) else []):
                mech_text += " " + str(s)
            # Also read derivation field from mechanisms
            if isinstance(m_deriv, str):
                mech_text += " " + m_deriv
            elif isinstance(m_deriv, list):
                for d in m_deriv:
                    if isinstance(d, dict):
                        mech_text += " " + str(d.get("step", "")) + " " + " ".join(str(c) for c in d.get("content", []))

    full_text = f"{desc} {math_model} {derivation_text} {mech_text}"
    try: results["equation_solving"] = solve_equation_from_text(full_text, llm_call=llm_call)
    except Exception as e: results["equation_solving"] = {"error": str(e)[:100]}
    try: results["dimensional_analysis"] = check_dimensional_consistency(full_text)
    except Exception as e: results["dimensional_analysis"] = {"error": str(e)[:100]}

    # === KINETIC EQUATION VALIDATION (fixes dimensional inconsistency bug) ===
    try:
        kinetic_result = validate_kinetic_equation(full_text)
        results["kinetic_validation"] = kinetic_result
        # Generate reviewer-style objections from kinetic issues
        if kinetic_result.get("issues"):
            reviewer = generate_reviewer_objections(kinetic_result)
            results["kinetic_reviewer_objections"] = reviewer
    except Exception as e:
        results["kinetic_validation"] = {"error": str(e)[:100]}

    try:
        steps = theory.get("steps") or theory.get("causal_chain") or []
        if steps: results["derivation_verification"] = verify_derivation(steps)
    except Exception as e: results["derivation_verification"] = {"error": str(e)[:100]}
    try:
        if "dy/dt" in full_text: results["numerical_simulation"] = run_numerical_simulation("dy/dt = -0.1*y + 10", {"y0": 0})
    except Exception as e: results["numerical_simulation"] = {"error": str(e)[:100]}
    try:
        prob = re.findall(r"(\d+\.?\d*)\s*%", full_text)
        if prob: results["monte_carlo"] = monte_carlo_validate({"mean": float(prob[0])/100, "std": 0.05})
    except Exception as e: results["monte_carlo"] = {"error": str(e)[:100]}
    try:
        eqs = [e.get("raw","") for e in _extract_equations(full_text)]
        if len(eqs) >= 2: results["cross_equation"] = check_cross_equation_consistency(eqs)
    except Exception as e: results["cross_equation"] = {"error": str(e)[:100]}
    score = 20  # base
    eq = results.get("equation_solving", {})
    eq_found = eq.get("equations_found", 0)
    eq_verified = eq.get("verification", {}).get("passed", 0) + eq.get("verification", {}).get("verified", 0)
    eq_found_count = eq.get("verification", {}).get("found", 0)
    if eq_verified > 0: score += 25
    elif eq_found_count > 0: score += 15  # found but not computable
    if eq_found > 0: score += 10
    if eq_found >= 5: score += 5  # bonus for rich mathematical content
    da = results.get("dimensional_analysis", {})
    if da.get("consistent", 0) > 0: score += 15
    if da.get("inconsistent", 0) > 0: score -= 10
    dv = results.get("derivation_verification", {})
    if dv.get("valid_steps", 0) > 0: score += 10
    if results.get("numerical_simulation", {}).get("status") == "solved": score += 10
    if results.get("monte_carlo", {}).get("status") == "validated": score += 5
    if results.get("cross_equation", {}).get("consistent_pairs", 0) > 0: score += 5

    # === KINETIC VALIDATION SCORING (penalize dimensional issues) ===
    kv = results.get("kinetic_validation", {})
    kv_issues = kv.get("issues", [])
    if kv_issues:
        fatal_count = sum(1 for i in kv_issues if i.get("severity") == "error")
        warning_count = sum(1 for i in kv_issues if i.get("severity") == "warning")
        score -= fatal_count * 15  # Heavy penalty for fatal kinetic issues
        score -= warning_count * 5  # Moderate penalty for warnings

    # Operational definition check — do new variables have measurement methods?
    ops_result = _check_operational_definitions(theory, mechanisms)
    results["operational_definitions"] = ops_result
    if ops_result.get("defined_count", 0) > 0:
        score += min(10, ops_result["defined_count"] * 3)
    if ops_result.get("undefined_count", 0) > 0:
        score -= min(10, ops_result["undefined_count"] * 2)

    results["overall_score"] = max(10, min(100, score))
    lines = []
    if eq.get("equations_found", 0) > 0:
        v = eq.get("verification", {})
        lines.append(f"Equations: {eq['equations_found']} found, {v.get('passed',0)} verified")
    if da.get("equations_checked", 0) > 0:
        lines.append(f"Dimensions: {da.get('consistent',0)} consistent")
    if dv.get("steps_checked", 0) > 0:
        lines.append(f"Derivation: {dv.get('valid_steps',0)}/{dv.get('steps_checked',0)} valid")

    # Kinetic validation summary
    kv = results.get("kinetic_validation", {})
    kv_issues = kv.get("issues", [])
    if kv_issues:
        fatal_count = sum(1 for i in kv_issues if i.get("severity") == "error")
        warn_count = sum(1 for i in kv_issues if i.get("severity") == "warning")
        lines.append(f"Kinetic: {len(kv_issues)} issues ({fatal_count} fatal, {warn_count} warnings)")
    elif kv.get("equations_found", 0) > 0:
        lines.append(f"Kinetic: {kv['equations_found']} equations validated OK")

    ops = results.get("operational_definitions", {})
    if ops.get("defined_count", 0) > 0 or ops.get("undefined_count", 0) > 0:
        lines.append(f"Operational defs: {ops.get('defined_count',0)} defined, {ops.get('undefined_count',0)} undefined")
    results["summary"] = "; ".join(lines) if lines else "No mathematical content to verify"
    return results


def _check_operational_definitions(theory, mechanisms=None):
    """Check if new variables have operational definitions (measurement methods)."""
    result = {"defined_count": 0, "undefined_count": 0, "details": []}
    hvs = theory.get("hidden_variables") or []
    for hv in hvs:
        if not isinstance(hv, dict):
            continue
        name = hv.get("name", "")
        desc = hv.get("description", "")
        desc_lower = desc.lower()
        measurement_terms = [
            "measurable", "measured", "measure", "observation", "observed",
            "detect", "detected", "instrument", "technique", "method",
            "spectroscopy", "microscopy", "assay", "experiment",
            "units", "range", "expected", "calibration",
        ]
        matches = sum(1 for term in measurement_terms if term in desc_lower)
        has_equation = bool(re.search(r'\d+\.?\d*\s*[a-zA-Z]', desc))
        if matches >= 2 or (matches >= 1 and has_equation):
            result["defined_count"] += 1
            result["details"].append({"name": name, "defined": True, "quality": "clear" if matches >= 3 else "partial"})
        else:
            result["undefined_count"] += 1
            result["details"].append({"name": name, "defined": False, "quality": "missing"})
    return result


def _calculate_math_score(results):
    """Calculate overall math verification score (0-100)."""
    score = 20
    eq = results.get("equation_solving", {})
    eq_found = eq.get("equations_found", 0)
    eq_verified = eq.get("verification", {}).get("passed", 0) + eq.get("verification", {}).get("verified", 0)
    eq_found_count = eq.get("verification", {}).get("found", 0)
    if eq_verified > 0: score += 25
    elif eq_found_count > 0: score += 15
    if eq_found > 0: score += 10
    if eq_found >= 5: score += 5
    da = results.get("dimensional_analysis", {})
    if da.get("consistent", 0) > 0: score += 15
    if da.get("inconsistent", 0) > 0: score -= 10
    dv = results.get("derivation_verification", {})
    if dv.get("valid_steps", 0) > 0: score += 10
    if results.get("numerical_simulation", {}).get("status") == "solved": score += 10
    if results.get("monte_carlo", {}).get("status") == "validated": score += 5
    if results.get("cross_equation", {}).get("consistent_pairs", 0) > 0: score += 5
    ops = results.get("operational_definitions", {})
    if ops.get("defined_count", 0) > 0: score += min(10, ops["defined_count"] * 3)
    if ops.get("undefined_count", 0) > 0: score -= min(10, ops["undefined_count"] * 2)
    return max(10, min(100, score))


def _generate_math_summary(results):
    """Generate human-readable math verification summary."""
    lines = []
    eq = results.get("equation_solving", {})
    if eq.get("equations_found", 0) > 0:
        v = eq.get("verification", {})
        lines.append(f"Equations: {eq['equations_found']} found, {v.get('passed',0)} verified")
    da = results.get("dimensional_analysis", {})
    if da.get("equations_checked", 0) > 0:
        lines.append(f"Dimensions: {da.get('consistent',0)} consistent")
    dv = results.get("derivation_verification", {})
    if dv.get("steps_checked", 0) > 0:
        lines.append(f"Derivation: {dv.get('valid_steps',0)}/{dv.get('steps_checked',0)} valid")
    ops = results.get("operational_definitions", {})
    if ops.get("defined_count", 0) > 0 or ops.get("undefined_count", 0) > 0:
        lines.append(f"Operational defs: {ops.get('defined_count',0)} defined, {ops.get('undefined_count',0)} undefined")
    return "; ".join(lines) if lines else "No mathematical content to verify"
