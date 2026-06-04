"""discovery/json_extract.py — Robust JSON extraction from LLM responses.

Handles: markdown code blocks, LaTeX braces, prose wrapping, trailing commas.
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

    raw = raw.strip()

    # Strip markdown code blocks
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        raw = raw.rsplit("```", 1)[0].strip()

    # Find JSON start
    json_start = None

    # Method 1: Search for expected key (e.g., {"theories": ...})
    if expected_key:
        match = re.search(r'\{\s*"' + re.escape(expected_key) + '"', raw)
        if match:
            json_start = match.start()

    # Method 2: Find first { followed by a quote (skip LaTeX/math braces)
    if json_start is None:
        for i, ch in enumerate(raw):
            if ch == '{':
                rest = raw[i + 1:].lstrip()
                if rest and rest[0] == '"':
                    json_start = i
                    break

    if json_start is None:
        return None

    # Find matching closing brace (depth tracking)
    depth = 0
    json_end = None
    for i in range(json_start, len(raw)):
        if raw[i] == '{':
            depth += 1
        elif raw[i] == '}':
            depth -= 1
            if depth == 0:
                json_end = i + 1
                break

    if json_end is None:
        return None

    json_str = raw[json_start:json_end]

    # Try parsing with progressive fixes
    for attempt in range(3):
        try:
            result = json.loads(json_str)
            return result if isinstance(result, dict) else None
        except json.JSONDecodeError:
            if attempt == 0:
                # Fix trailing commas
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
            elif attempt == 1:
                # Try extracting just the expected key's value
                if expected_key:
                    arr_match = re.search(
                        r'"' + re.escape(expected_key) + r'"\s*:\s*(\[[\s\S]*\])',
                        json_str
                    )
                    if arr_match:
                        try:
                            arr = json.loads(arr_match.group(1))
                            return {expected_key: arr}
                        except json.JSONDecodeError:
                            pass

    return None
