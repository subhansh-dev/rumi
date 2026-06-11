"""
math_chain.py - Explicit math derivation chain for mechanisms.

Pipeline: Mechanism -> Equation -> Parameter -> Derivation -> Numerical Example
"""


class MathChain:
    def __init__(self, llm_call=None):
        self.llm_call = llm_call

    def process_mechanisms(self, mechanisms, topic, domain):
        if not self.llm_call or not mechanisms:
            return mechanisms
        for m in mechanisms:
            if not isinstance(m, dict):
                continue
            name = m.get("name", "?")
            desc = m.get("description", m.get("mechanism", ""))
            existing_model = m.get("mathematical_model", "")
            if existing_model and "equation to be derived" not in existing_model.lower():
                if len(existing_model) > 20:
                    continue
            eq_result = self._derive_equation(name, desc, topic, domain)
            if eq_result:
                m["mathematical_model"] = eq_result.get("equation", existing_model)
                m["equation_description"] = eq_result.get("description", "")
                m["equation_variables"] = eq_result.get("variables", [])
            eq = m.get("mathematical_model", "")
            if eq and "equation to be derived" not in eq.lower():
                param_result = self._estimate_parameters(name, eq, desc, topic, domain)
                if param_result:
                    m["key_parameters"] = param_result.get("parameters", [])
                    m["derivation_steps"] = param_result.get("derivation_steps", [])
            params = m.get("key_parameters", [])
            if eq and params and "equation to be derived" not in eq.lower():
                num_result = self._numerical_validation(name, eq, params, desc, topic, domain)
                if num_result:
                    m["numerical_example"] = num_result.get("example", "")
                    m["numerical_result"] = num_result.get("result", "")
                    m["physical_plausibility"] = num_result.get("plausibility", "")
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
