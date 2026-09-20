"""Bounded D1 response extraction; deliberately separate from Work Review JSON."""
import json
import re
from collections.abc import Mapping

MAX_D1_RESPONSE_CHARS = 65536
MAX_D1_STREAM_BYTES = 16 * 1024 * 1024


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _load(text):
    def invalid_constant(_value):
        raise ValueError("non-JSON constant")
    return json.loads(text, object_pairs_hook=_unique_object, parse_constant=invalid_constant)


def response_from_text(text):
    """Accept bare objects or one complete json fence, never prose substrings."""
    if len(text) > MAX_D1_RESPONSE_CHARS:
        return None, "response too large"
    try:
        value = _load(text)
    except json.JSONDecodeError:
        pass
    except (ValueError, RecursionError) as error:
        return None, "duplicate JSON key" if str(error) == "duplicate JSON key" else "malformed JSON"
    else:
        return (value, None) if isinstance(value, dict) else (None, "non-JSON response")

    # Count all fence delimiters, including unsupported fence languages/styles.
    # This refuses an extra block rather than choosing the most plausible JSON.
    lines = text.splitlines()
    fences = [(i, line.strip()) for i, line in enumerate(lines)
              if re.match(r"^ {0,3}(?:`{3,}|~{3,})", line)]
    if not fences:
        return None, "non-JSON response"
    if len(fences) > 2:
        return None, "ambiguous response: multiple fenced blocks"
    if len(fences) != 2 or fences[1][1] != "```":
        return None, "unterminated response fence"
    if fences[0][1] != "```json":
        return None, "non-JSON response"
    body = "\n".join(lines[fences[0][0] + 1:fences[1][0]])
    try:
        value = _load(body)
    except (ValueError, RecursionError) as error:
        return None, "duplicate JSON key" if str(error) == "duplicate JSON key" else "malformed fenced JSON"
    return (value, None) if isinstance(value, dict) else (None, "malformed fenced JSON")


def _from_stream(raw):
    if len(raw) > MAX_D1_STREAM_BYTES:
        return None, "response stream too large"
    try:
        text = raw.decode("utf-8")
        # Preserve standalone (including pretty-printed) bare JSON support.
        whole = _load(text)
    except UnicodeDecodeError:
        return None, "malformed response stream"
    except json.JSONDecodeError:
        whole = None
    except (ValueError, RecursionError) as error:
        return None, "duplicate JSON key" if str(error) == "duplicate JSON key" else "malformed response stream"
    if isinstance(whole, dict) and "type" not in whole:
        return response_from_text(text)
    try:
        events = [_load(line) for line in text.splitlines() if line.strip()]
    except (ValueError, RecursionError) as error:
        return None, "duplicate JSON key" if str(error) == "duplicate JSON key" else "malformed response stream"
    if any(not isinstance(event, dict) for event in events):
        return None, "malformed response stream"
    terminals = [event for event in events if event.get("type") == "result"]
    if len(terminals) > 1:
        return None, "ambiguous response: multiple terminal candidates"
    if not terminals or events[-1] is not terminals[0]:
        return None, "non-JSON response"
    value = terminals[0].get("result")
    if isinstance(value, str):
        return response_from_text(value)
    return (value, None) if isinstance(value, dict) else (None, "non-JSON response")


def response_candidate(output):
    """Interpret only terminal provider results or explicit standalone responses."""
    if isinstance(output, bytes):
        return _from_stream(output)
    if isinstance(output, str):
        return response_from_text(output)
    if isinstance(output, Mapping):
        candidate = output.get("review_response") or output.get("d1_response")
        if isinstance(candidate, Mapping):
            return candidate, None
        if "schema" in output:
            return output, None
        result = output.get("result")
        if isinstance(result, Mapping):
            result = result.get("value") or result.get("result")
        if isinstance(result, str):
            return response_from_text(result)
        if isinstance(result, Mapping):
            return result, None
    return None, "non-JSON response"
