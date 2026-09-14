"""Robust extraction of a single JSON object from LLM output.

LLMs frequently wrap JSON in code fences, add prose before/after, or emit raw
control characters (unescaped newlines/tabs) inside string values. This helper
recovers a valid object from those common deviations instead of failing on the
first ``json.JSONDecodeError``. Shared so SOP ingestion has the same robustness
the KB pipeline already has.
"""

import json
from typing import Any


def _unwrap_fenced_json(content: str) -> str:
    stripped = content.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    if lines and lines[0].strip().lower() == "json":
        lines = lines[1:]
    return "\n".join(lines).strip()


def _extract_outer_json_object(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return content
    return content[start : end + 1]


def _escape_control_chars_in_json_strings(content: str) -> str:
    """Escape raw newlines/tabs/carriage returns that appear inside JSON string
    literals (the most common reason ``json.loads`` rejects LLM output)."""
    result: list[str] = []
    in_string = False
    escaped = False
    for char in content:
        if in_string:
            if escaped:
                result.append(char)
                escaped = False
                continue
            if char == "\\":
                result.append(char)
                escaped = True
                continue
            if char == '"':
                result.append(char)
                in_string = False
                continue
            if char == "\n":
                result.append("\\n")
                continue
            if char == "\r":
                result.append("\\r")
                continue
            if char == "\t":
                result.append("\\t")
                continue
            result.append(char)
            continue
        result.append(char)
        if char == '"':
            in_string = True
    return "".join(result)


def parse_json_object(content: str) -> dict[str, Any] | None:
    """Best-effort parse of a single JSON object from raw LLM text.

    Returns the parsed dict, or None if nothing usable could be recovered.
    """
    if not content or not content.strip():
        return None
    unwrapped = _unwrap_fenced_json(content)
    for candidate in (unwrapped, _extract_outer_json_object(unwrapped)):
        candidate = candidate.strip()
        if not candidate:
            continue
        for attempt in (candidate, _escape_control_chars_in_json_strings(candidate)):
            try:
                parsed = json.loads(attempt)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
    return None
