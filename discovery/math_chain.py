"""
math_chain.py - Explicit math derivation chain for mechanisms.
Pipeline: Mechanism -> Equation -> Parameter -> Derivation -> Numerical Example

PARALLELIZED: All independent mechanism derivations run concurrently.
15 mechanisms × 65s each = 16 min sequential → ~65s parallel.
"""

import concurrent.futures

MAX_MATH_WORKERS = 6  # parallel LLM calls for math derivation


class MathChain:
    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def process_mechanisms(self, mechanisms, topic, domain):
        if not self.llm_call or not mechanisms:
            return mechanisms

        # Filter to mechanisms that need equations
        needs_eq = []
        skipped = 0
        for m in mechanisms:
            if not isinstance(m, dict):
                continue
            existing_model = m.get("mathematical_model", "")
            if existing_model and "equation to be derived" not in existing_model.lower():
                if len(existing_model) > 20:
                    skipped += 1
                    continue
            desc = m.get("description", m.get("mechanism", ""))
            if not desc or len(desc) < 20:
                skipped += 1
                print(f"    [MathChain] SKIP '{m.get('name', '?')[:40]}': desc len={len(desc)}, fields={list(m.keys())}", flush=True)
                continue
            needs_eq.append(m)
        if skipped:
            print(f"    [MathChain] {skipped}/{len(mechanisms)} skipped (no desc or already has equation)", flush=True)

        if not needs_eq:
            return mechanisms

        # ── PHASE 1: Derive equations in parallel ──
        def _derive_one(m):
            name = m.get("name", "?")
            desc = m.get("description", m.get("mechanism", ""))
            eq_result = self._derive_equation(name, desc, topic, domain)
            return m, eq_result

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_MATH_WORKERS) as pool:
            futures = {pool.submit(_derive_one, m): m for m in needs_eq}
            for future in concurrent.futures.as_completed(futures):
                try:
                    m, eq_result = future.result()
                    if eq_result:
                        m["mathematical_model"] = eq_result.get("equation", m.get("mathematical_model", ""))
                        m["equation_description"] = eq_result.get("description", "")
                        m["equation_variables"] = eq_result.get("variables", [])
                except Exception:
                    pass

        # ── PHASE 2: Estimate parameters in parallel (for mechanisms that got equations) ──
        needs_params = [m for m in needs_eq
                        if m.get("mathematical_model", "")
                        and "equation to be derived" not in m.get("mathematical_model", "").lower()]

        def _params_one(m):
            name = m.get("name", "?")
            eq = m.get("mathematical_model", "")
            desc = m.get("description", m.get("mechanism", ""))
            return m, self._estimate_parameters(name, eq, desc, topic, domain)

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_MATH_WORKERS) as pool:
            futures = {pool.submit(_params_one, m): m for m in needs_params}
            for future in concurrent.futures.as_completed(futures):
                try:
                    m, param_result = future.result()
                    if param_result:
                        m["key_parameters"] = param_result.get("parameters", [])
                        m["derivation_steps"] = param_result.get("derivation_steps", [])
                except Exception:
                    pass

        # ── PHASE 3: Numerical validation in parallel (for mechanisms with params) ──
        needs_validation = [m for m in needs_params
                            if m.get("key_parameters")
                            and "equation to be derived" not in m.get("mathematical_model", "").lower()]

        def _validate_one(m):
            name = m.get("name", "?")
            eq = m.get("mathematical_model", "")
            params = m.get("key_parameters", [])
            desc = m.get("description", m.get("mechanism", ""))
            return m, self._numerical_validation(name, eq, params, desc, topic, domain)

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_MATH_WORKERS) as pool:
            futures = {pool.submit(_validate_one, m): m for m in needs_validation}
            for future in concurrent.futures.as_completed(futures):
                try:
                    m, num_result = future.result()
                    if num_result:
                        m["numerical_example"] = num_result.get("example", "")
                        m["numerical_result"] = num_result.get("result", "")
                        m["physical_plausibility"] = num_result.get("plausibility", "")
                except Exception:
                    pass

        return mechanisms

    def _derive_equation(self, name, description, topic, domain):
        if not description or len(description) < 20:
            return None
        prompt = (
            "You are a theoretical physicist. Given this mechanism, derive the governing equation.\n\n"
            "MECHANISM: " + name + "\n"
            "DESCRIPTION: " + description[:600] + "\n"
            "TOPIC: " + topic + "\n"
            "DOMAIN: " + domain + "\n\n"
            "Your task:\n"
            "1. Identify what physical quantity this mechanism affects\n"
            "2. Write the governing equation using standard physics notation\n"
            "3. Define all variables with their physical meaning and units\n"
            "4. If no exact equation exists, write the best approximate equation\n\n"
            "BAD: The rate depends on temperature (no equation)\n"
            "GOOD: R(omega) = 1 - exp(-omega/omega_c) where omega_c is the cutoff frequency\n\n"
            "Output JSON:\n"
            '{"equation": "the equation", "description": "what it means physically", '
            '"variables": [{"symbol": "R(omega)", "meaning": "reflectivity", "units": "dimensionless"}], '
            '"derivation_basis": "from quantum field theory"}'
        )
        try:
            raw = self.llm_call(prompt, max_tokens=2000)
            if raw:
                from discovery.json_extract import extract_json
                result = extract_json(raw)
                if result and isinstance(result, dict) and result.get("equation"):
                    return result
        except Exception:
            pass
        return None

    def _estimate_parameters(self, name, equation, description, topic, domain):
        prompt = (
            "You are a physicist estimating parameters for a mechanism.\n\n"
            "MECHANISM: " + name + "\n"
            "EQUATION: " + equation + "\n"
            "DESCRIPTION: " + description[:400] + "\n"
            "TOPIC: " + topic + "\n"
            "DOMAIN: " + domain + "\n\n"
            "For each variable in the equation:\n"
            "1. If known constant, cite value and source\n"
            "2. If derivable, show derivation\n"
            "3. If estimated, give order-of-magnitude with reasoning\n\n"
            "Also provide step-by-step derivation from assumptions to equation.\n\n"
            "Output JSON:\n"
            '{"parameters": [{"name": "param_name", "value": "value", "units": "units", '
            '"source": "derived|cited|estimated", "source_detail": "how you got this"}],\n'
            ' "derivation_steps": ["Step 1: ...", "Step 2: ..."]}'
        )
        try:
            raw = self.llm_call(prompt, max_tokens=3000)
            if raw:
                from discovery.json_extract import extract_json
                result = extract_json(raw)
                if result and isinstance(result, dict):
                    return result
        except Exception:
            pass
        return None

    def _numerical_validation(self, name, equation, parameters, description, topic, domain):
        param_text = ""
        for p in (parameters or [])[:6]:
            if isinstance(p, dict):
                param_text += "  {} = {} {}\n".format(
                    p.get("name", "?"), p.get("value", "?"), p.get("units", ""))
        prompt = (
            "You are a physicist doing a numerical check.\n\n"
            "MECHANISM: " + name + "\n"
            "EQUATION: " + equation + "\n"
            "PARAMETERS:\n" + param_text +
            "DESCRIPTION: " + description[:300] + "\n\n"
            "Plug in values, compute result, check if physically reasonable.\n\n"
            "BAD: The effect is significant (no numbers)\n"
            "GOOD: For M = 10 M_sun, omega_c = 3e4 rad/s, R(10^15) = 0.73\n\n"
            "Output JSON:\n"
            '{"example": "For M = 10 M_sun: omega_c = ...", '
            '"result": "R = 0.73 meaning ...", '
            '"plausibility": "consistent with ..."}'
        )
        try:
            raw = self.llm_call(prompt, max_tokens=2000)
            if raw:
                from discovery.json_extract import extract_json
                result = extract_json(raw)
                if result and isinstance(result, dict):
                    return result
        except Exception:
            pass
        return None
