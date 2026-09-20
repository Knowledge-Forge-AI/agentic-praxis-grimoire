"""Bounded JSONC-compatible normalization for nonce-fenced provider results.

The accepted dialect is JSON plus line comments, block comments, and trailing
commas. It deliberately does not implement JSON5 identifiers, quotes, numbers,
escapes, or other extensions. Normalization preserves input length so callers
can retain raw-decode trailing-content classification.
"""

from __future__ import annotations

import json
from typing import Any, Callable


_JSON_WHITESPACE = " \t\r\n"


class JSONCLexError(ValueError):
    """A string or comment is lexically incomplete."""


def _blank(chars: list[str], index: int) -> None:
    if chars[index] not in "\r\n":
        chars[index] = " "


def _strip_comments(text: str) -> str:
    chars = list(text)
    index = 0
    in_string = False
    escaped = False
    while index < len(chars):
        char = chars[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char != "/" or index + 1 >= len(chars):
            index += 1
            continue
        following = chars[index + 1]
        if following == "/":
            while index < len(chars) and chars[index] not in "\r\n":
                _blank(chars, index)
                index += 1
            continue
        if following != "*":
            index += 1
            continue
        _blank(chars, index)
        _blank(chars, index + 1)
        index += 2
        while index + 1 < len(chars) and chars[index:index + 2] != ["*", "/"]:
            _blank(chars, index)
            index += 1
        if index + 1 >= len(chars):
            raise JSONCLexError("unterminated block comment")
        _blank(chars, index)
        _blank(chars, index + 1)
        index += 2
    if in_string:
        raise JSONCLexError("unterminated string")
    return "".join(chars)


def _strip_trailing_commas(text: str) -> str:
    chars = list(text)
    in_string = False
    escaped = False
    for index, char in enumerate(chars):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char != ",":
            continue
        following = index + 1
        while following < len(chars) and chars[following] in _JSON_WHITESPACE:
            following += 1
        if following < len(chars) and chars[following] in "}]":
            chars[index] = " "
    return "".join(chars)


def normalize(text: str) -> str:
    """Return length-preserving strict JSON for the supported JSONC dialect."""
    return _strip_trailing_commas(_strip_comments(text))


def strip_json_whitespace(text: str) -> str:
    """Strip only JSON's four permitted outer whitespace characters."""
    return text.strip(_JSON_WHITESPACE)


def _reject_constant(value: str) -> Any:
    raise JSONCLexError(f"non-JSON numeric constant: {value}")


def unicode_scalars(value: str) -> str:
    """Reject lone surrogates and normalize valid escaped UTF-16 pairs."""
    if not any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        return value
    result: list[str] = []
    index = 0
    while index < len(value):
        codepoint = ord(value[index])
        if 0xD800 <= codepoint <= 0xDBFF:
            if index + 1 >= len(value):
                raise JSONCLexError("unpaired Unicode surrogate")
            low = ord(value[index + 1])
            if not 0xDC00 <= low <= 0xDFFF:
                raise JSONCLexError("unpaired Unicode surrogate")
            result.append(chr(
                0x10000 + ((codepoint - 0xD800) << 10) + (low - 0xDC00)
            ))
            index += 2
            continue
        if 0xDC00 <= codepoint <= 0xDFFF:
            raise JSONCLexError("unpaired Unicode surrogate")
        result.append(value[index])
        index += 1
    return "".join(result)


def raw_decode(
    text: str,
    *,
    object_pairs_hook: Callable[[list[tuple[str, Any]]], Any],
) -> tuple[Any, str]:
    """Decode one value and return its normalized trailing content."""
    normalized = normalize(text).lstrip(_JSON_WHITESPACE)
    decoder = json.JSONDecoder(
        object_pairs_hook=object_pairs_hook,
        parse_constant=_reject_constant,
    )
    value, consumed = decoder.raw_decode(normalized)
    return value, normalized[consumed:]
