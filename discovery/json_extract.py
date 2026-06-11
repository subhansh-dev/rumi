"""discovery/json_extract.py — Robust JSON extraction from LLM responses.

Handles: markdown code blocks, LaTeX braces, prose wrapping, trailing commas,
truncated JSON (missing closing braces), arrays at top level, thinking tags,
reasoning prefixes, and all common LLM output quirks.
"""

import json
import re


def extract_json(raw: str, expected_key: str = None) -> dict | None:
    """Extract JSON from an LLM response that may contain prose, markdown, or LaTeX.

    Args:
        raw: The LLM response string
        expected_key: If set, search for {"expected_key": ...} first (e.g., "theories")

    Returns:
        Parsed dict or None if extraction fails
    """
    if not raw or not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text:
        return None

    # ── Step 0: Pre-clean common LLM artifacts ──

    # Strip thinking/reasoning tags (Gemini, some open models)
    text = re.sub(r'<thinking>[\s\S]*?</thinking>', '', text).strip()
    text = re.sub(r'<reasoning>[\s\S]*?</reasoning>', '', text).strip()
    text = re.sub(r'<\|begin_of_thought\|>[\s\S]*?<\|end_of_thought\|>', '', text).strip()

    # Strip markdown code blocks (```json ... ``` or ``` ... ```)
    code_block = re.search(r'```(?:json|JSON)?\s*\n?([\s\S]*?)```', text)
    if code_block:
        text = code_block.group(1).strip()

    # Strip common prose prefixes like "Here's the JSON:" or "Here are the theories:"
    text = re.sub(r'^(?:here(?:\'s| is| are)|the following|below is|output|result|response)[\s\S]*?(?=[\[{])', '', text, flags=re.IGNORECASE).strip()

    # If text starts with prose and then has JSON, try to find the JSON part
    # Look for the first { or [ that starts a real JSON structure
    json_start = None

    # Method 1: Search for expected key (e.g., {"theories": ...})
    if expected_key:
        match = re.search(r'\{\s*"' + re.escape(expected_key) + r'"\s*:', text)
        if match:
            json_start = match.start()

    # Method 2: Find first { or [ followed by a quote or nested structure
    if json_start is None:
        for i, ch in enumerate(text):
            if ch in ('{', '['):
                rest = text[i + 1:].lstrip()
                if rest and rest[0] in ('"', '{', '['):
                    json_start = i
                    break

    if json_start is None:
        # Last resort: try parsing the whole thing
        try:
            result = json.loads(text)
            if isinstance(result, (dict, list)):
                return _wrap(result, expected_key)
        except (json.JSONDecodeError, ValueError):
            pass
        # ULTIMATE FALLBACK: regex for JSON objects in pure prose
        return _regex_extract_json(text, expected_key)

    # ── Step 1: Try to find a complete JSON block ──
    json_str = text[json_start:]
    result = _try_parse_json(json_str, expected_key)
    if result is not None:
        return result

    # ── Step 2: Try progressive trimming from end ──
    for trim in range(1, min(200, len(json_str))):
        candidate = json_str[:-trim].rstrip()
        if not candidate:
            break
        result = _try_parse_json(candidate, expected_key)
        if result is not None:
            return result

    # ── Step 3: Try finding the LAST complete JSON block ──
    last_close = _find_last_balanced_json(text, json_start)
    if last_close and last_close > json_start:
        result = _try_parse_json(text[json_start:last_close], expected_key)
        if result is not None:
            return result

    # ── Step 4: Regex fallback for prose-wrapped JSON ──
    return _regex_extract_json(text, expected_key)


def _regex_extract_json(text: str, expected_key: str = None) -> dict | None:
    """Last resort: extract JSON objects from prose text using brace counting."""
    # Try to find JSON with expected key using brace counting
    if expected_key:
        key_pattern = '"' + re.escape(expected_key) + '"'
        for match in re.finditer(key_pattern, text):
            # Walk backwards to find the opening { of this JSON object
            start = match.start()
            while start > 0 and text[start] != '{':
                start -= 1
            if start >= 0 and text[start] == '{':
                # Use brace counting to find the matching closing }
                end = _find_balanced_close(text, start)
                if end > start:
                    candidate = text[start:end + 1]
                    result = _try_parse_json(candidate, expected_key)
                    if result is not None:
                        return result

    # Try brace-counting extraction for all JSON objects
    candidates = []
    i = 0
    while i < len(text):
        if text[i] == '{':
            end = _find_balanced_close(text, i)
            if end > i and end - i > 30:  # minimum size filter
                candidates.append(text[i:end + 1])
                i = end + 1
                continue
        elif text[i] == '[':
            end = _find_balanced_close(text, i)
            if end > i and end - i > 30:
                candidates.append(text[i:end + 1])
                i = end + 1
                continue
        i += 1

    # Try parsing candidates, largest first
    for candidate in sorted(candidates, key=len, reverse=True)[:10]:
        result = _try_parse_json(candidate, expected_key)
        if result is not None:
            return result

    return None


def _find_balanced_close(text: str, open_pos: int) -> int:
    """Find the matching closing brace/bracket using balanced counting."""
    open_char = text[open_pos]
    close_char = '}' if open_char == '{' else ']'
    depth = 0
    in_string = False
    escape_next = False

    for i in range(open_pos, len(text)):
        c = text[i]

        if escape_next:
            escape_next = False
            continue

        if c == '\\' and in_string:
            escape_next = True
            continue

        if c == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if c == open_char:
            depth += 1
        elif c == close_char:
            depth -= 1
            if depth == 0:
                return i

    return -1


def _try_parse_json(json_str: str, expected_key: str = None) -> dict | None:
    """Try to parse a JSON string with progressive fixes."""
    if not json_str:
        return None

    # Fix trailing commas
    cleaned = re.sub(r',\s*([}\]])', r'\1', json_str)

    # Fix unescaped newlines inside strings
    cleaned = _fix_newlines_in_strings(cleaned)

    # Try parsing with progressive fixes
    for attempt in range(6):
        try:
            if attempt == 0:
                result = json.loads(cleaned)
            elif attempt == 1:
                # Try original without newline fix
                result = json.loads(json_str)
            elif attempt == 2:
                # Try with trailing comma fix only
                result = json.loads(re.sub(r',\s*([}\]])', r'\1', json_str))
            elif attempt == 3:
                # Try extracting just the expected key's value as array
                if expected_key:
                    arr_match = re.search(
                        r'"' + re.escape(expected_key) + r'"\s*:\s*(\[[\s\S]*\])',
                        cleaned
                    )
                    if arr_match:
                        arr = json.loads(arr_match.group(1))
                        return {expected_key: arr}
                continue
            elif attempt == 4:
                # Try wrapping in object if it's a bare array
                if cleaned.startswith('['):
                    result = json.loads(cleaned)
                    key = expected_key or "items"
                    return {key: result}
                continue
            elif attempt == 5:
                # Try removing any remaining markdown or comments
                no_comments = re.sub(r'//.*?$', '', cleaned, flags=re.MULTILINE)
                no_comments = re.sub(r'/\*[\s\S]*?\*/', '', no_comments)
                result = json.loads(no_comments)

            if isinstance(result, (dict, list)):
                return _wrap(result, expected_key)
        except (json.JSONDecodeError, ValueError):
            continue

    return None


def _fix_newlines_in_strings(s: str) -> str:
    """Fix literal newlines inside JSON strings (common LLM error)."""
    result = []
    in_string = False
    escape_next = False
    for ch in s:
        if escape_next:
            result.append(ch)
            escape_next = False
            continue
        if ch == '\\' and in_string:
            result.append(ch)
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch == '\n':
            result.append('\\n')
            continue
        if in_string and ch == '\r':
            result.append('\\r')
            continue
        result.append(ch)
    return ''.join(result)


def _find_last_balanced_json(text: str, start: int) -> int | None:
    """Find the end position of the last balanced JSON structure starting at `start`."""
    if start >= len(text):
        return None
    open_char = text[start]
    close_char = '}' if open_char == '{' else ']'
    depth = 0
    in_string = False
    escape_next = False
    last_valid_end = None

    for i in range(start, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                last_valid_end = i + 1
                break

    return last_valid_end


def _wrap(result, expected_key):
    """Wrap result in expected_key dict if needed."""
    # Semantic alias mapping — LLMs often use different names for the same concept
    ALIAS_MAP = {
        "mechanisms": ["hypotheses", "theories", "explanations", "pathways",
                       "causal_mechanisms", "causal_pathways", "mechanisms_list",
                       "novel_theory", "proposed_mechanisms", "candidate_mechanisms"],
        "theories": ["hypotheses", "mechanisms", "explanations", "models",
                     "theories_list", "competing_theories", "novel_theory",
                     "proposed_theories", "candidate_theories"],
        "hidden_variables": ["variables", "hidden_factors", "proposed_variables",
                             "latent_variables", "unknowns", "novel_variables"],
        "predictions": ["testable_predictions", "forecast", "forecasts",
                        "predictions_list", "testable_claims"],
        "contradictions": ["conflicts", "discrepancies", "inconsistencies"],
        "findings": ["results", "discoveries", "observations"],
    }
    if isinstance(result, dict):
        # If expected_key not found, look for similar keys
        if expected_key and expected_key not in result:
            # Try common alternatives
            candidates = [
                expected_key,
                expected_key.rstrip('s'),       # "mechanisms" → "mechanism"
                expected_key + 's',              # "mechanism" → "mechanisms"
                'new_' + expected_key,           # "mechanisms" → "new_mechanisms"
                'proposed_' + expected_key,      # "hidden_variables" → "proposed_hidden_variables"
                expected_key.replace('_', ' '),  # "hidden_variables" → "hidden variables"
            ]
            # Add semantic aliases (e.g., "hypotheses" when looking for "mechanisms")
            aliases = ALIAS_MAP.get(expected_key, [])
            candidates.extend(aliases)
            for candidate in candidates:
                if candidate in result:
                    val = result[candidate]
                    if isinstance(val, list):
                        return {expected_key: val}
                    elif isinstance(val, dict):
                        return {expected_key: [val]}
            # Search for any key containing the expected_key as substring
            for k, v in result.items():
                if isinstance(v, list) and expected_key in k.lower():
                    return {expected_key: v}
            # Canonical fallback: find ANY key with a list of dicts (the actual content)
            # This handles any model/format without hardcoding specific key names
            list_of_dicts = [(k, v) for k, v in result.items()
                             if isinstance(v, list) and v and isinstance(v[0], dict)]
            if list_of_dicts:
                # Pick the largest list (most likely the main content)
                best = max(list_of_dicts, key=lambda kv: len(kv[1]))
                return {expected_key: best[1]}
            # If result has a single list value, use that
            list_vals = [(k, v) for k, v in result.items() if isinstance(v, list) and v]
            if len(list_vals) == 1:
                return {expected_key: list_vals[0][1]}
            # If result looks like a single item (has description/predictions/etc), wrap it
            if any(k in result for k in ["description", "name", "type", "predictions", "hypothesis"]):
                # Check if it's a single item that should be in an array
                has_list_vals = any(isinstance(v, list) for v in result.values())
                if not has_list_vals:
                    return {expected_key: [result]}
        return result
    if isinstance(result, list):
        key = expected_key or "items"
        return {key: result}
    return None
