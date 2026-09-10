"""Bounded stdlib test and evaluation contract for APG122 SVG language profile.

Implements bounded static, syntactic, and structural analysis using Python standard library
(xml.etree.ElementTree, re, json, pathlib, math, typing).

Explicit Disclaimers:
This contract executes bounded static and syntactic analysis using Python standard library.
It makes NO claim of visual rendering proof, pixel rasterization accuracy,
GPU rendering fidelity, or browser accessibility-tree computation proof.
Lexical security scan is a fixture-only adverse signal detector for contract testing,
NOT an execution-grade sanitizer or security barrier.
Optimization evaluation performs conservative structural comparison of checked semantics only,
with NO general equivalence claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import re
from typing import Any, Dict, List, NoReturn, Optional, Set, Tuple
import xml.etree.ElementTree as ET

# Bounded Limits to prevent denial-of-service, zip-bombs, and deep recursion
MAX_SVG_BYTES: int = 512 * 1024  # 512 KB
MAX_DOM_DEPTH: int = 32
MAX_ELEMENT_COUNT: int = 5000
MAX_USE_DEPTH: int = 16

PROOF_DISCLAIMER: str = (
    "This contract executes bounded static and syntactic analysis using Python standard library. "
    "It makes NO claim of visual rendering proof, pixel rasterization accuracy, "
    "GPU rendering fidelity, or browser accessibility-tree computation proof."
)

LEXICAL_SCAN_DISCLAIMER: str = (
    "Lexical security scan is a fixture-only adverse signal detector for contract testing, "
    "NOT an execution-grade sanitizer or security barrier."
)

OPTIMIZATION_DISCLAIMER: str = (
    "Optimization evaluation performs conservative structural comparison of checked semantics only, "
    "with NO general equivalence claim."
)

SVG_NAMESPACE: str = "http://www.w3.org/2000/svg"
XLINK_NAMESPACE: str = "http://www.w3.org/1999/xlink"

SELECTIONS: Tuple[str, ...] = (
    "selected",
    "embedded-route",
    "route-to-owner",
    "non-trigger",
)

RESPONSES: Tuple[str, ...] = (
    "proceed-routine",
    "inspect-before-judgment",
    "bounded-local-decision",
    "stop-and-escalate",
)

ROUTES: Tuple[str, ...] = (
    "css-language-profile",
    "javascript-language-profile",
    "jsx-language-profile",
    "react-component-profile",
    "html-owner",
    "security-owner",
    "accessibility-owner",
    "visual-validation-owner",
    "font-owner",
    "performance-owner",
    "project-configuration",
    "not-applicable",
)

A11Y_MODES: Tuple[str, ...] = (
    "meaningful",
    "decorative",
    "interactive",
    "ambiguous",
)

CLAUSE_IDS: Tuple[str, ...] = (
    "SVG-01-DOC-STRUCTURE",
    "SVG-02-VIEWBOX-SIZING",
    "SVG-03-PATHS-GEOMETRY",
    "SVG-04-TRANSFORMS-COORDS",
    "SVG-05-PAINT-CURRENTCOLOR",
    "SVG-06-GRADIENTS-PATTERNS",
    "SVG-07-DEFS-SYMBOLS-USE",
    "SVG-08-CLIPPING-MASKING",
    "SVG-09-TEXT-TYPOGRAPHY",
    "SVG-10-FILTER-EFFECTS",
    "SVG-11-DOM-INTERACTION",
    "SVG-12-A11Y-SEMANTICS",
    "SVG-13-SECURITY-PROCESSING",
    "SVG-14-SERIALIZATION-OPT",
    "SVG-15-ROUTING-BOUNDARIES",
)

CATEGORIES: Tuple[str, ...] = (
    "geometry-and-sizing",
    "sprites-and-use",
    "sprites-and-use-negative",
    "paint-and-masking",
    "transforms-negative",
    "accessibility",
    "paint-and-theming",
    "security-negative",
    "resource-contexts",
    "serialization-negative",
    "optimization-negative",
    "optimization-safe",
    "boundaries",
    "performance-limits",
)

SCENARIO_ROW_KEYS: Tuple[str, ...] = (
    "id",
    "purpose",
    "category",
    "fixture_file",
    "selection",
    "response",
    "route",
    "clauses",
    "invariants",
)

SUPPORTED_PATH_COMMANDS: Set[str] = {"M", "m", "L", "l", "H", "h", "V", "v", "Z", "z"}
UNSUPPORTED_PATH_COMMANDS: Set[str] = {"C", "c", "S", "s", "Q", "q", "T", "t", "A", "a"}
SUPPORTED_TRANSFORM_FUNCTIONS: Set[str] = {"matrix", "translate", "scale", "rotate", "skewX", "skewY"}


class SvgContractError(ValueError):
    """Base error for SVG contract violations."""


class BoundedLimitExceededError(SvgContractError):
    """Input exceeds explicit bounded resource limits."""


class SvgSecurityError(SvgContractError):
    """Security violation detected (active content, XXE, etc.)."""


def fail(message: str) -> NoReturn:
    raise SvgContractError(message)


def _strip_ns(tag: str) -> str:
    """Return local name of an XML tag."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def validate_bounded_input(content: str | bytes) -> bytes:
    """Verify input does not exceed maximum byte size limit."""
    raw_bytes = content.encode("utf-8") if isinstance(content, str) else content
    if len(raw_bytes) > MAX_SVG_BYTES:
        raise BoundedLimitExceededError(
            f"SVG content size {len(raw_bytes)} bytes exceeds limit {MAX_SVG_BYTES} bytes"
        )
    return raw_bytes


def _measure_dom_bounds(root: ET.Element) -> Tuple[int, int]:
    """Iteratively measure max depth and element count, aborting early if limits exceeded.

    Avoids Python recursion limit crashes on deep fixtures.
    """
    stack: List[Tuple[ET.Element, int]] = [(root, 1)]
    total_count = 0
    max_depth = 1

    while stack:
        elem, depth = stack.pop()
        total_count += 1

        if total_count > MAX_ELEMENT_COUNT:
            raise BoundedLimitExceededError(
                f"SVG element count {total_count} exceeds limit {MAX_ELEMENT_COUNT}"
            )
        if depth > max_depth:
            max_depth = depth
        if depth > MAX_DOM_DEPTH:
            raise BoundedLimitExceededError(
                f"SVG DOM depth {depth} exceeds limit {MAX_DOM_DEPTH}"
            )

        for child in elem:
            stack.append((child, depth + 1))

    return max_depth, total_count


def check_xml_well_formedness(svg_text: str) -> Tuple[bool, Optional[str], Optional[ET.Element]]:
    """Check XML syntax, namespace, lowercase root tag, and bounded limits.

    All DOCTYPE and ENTITY declarations are rejected prior to XML parsing to prevent XXE.
    Root element MUST be lowercase 'svg' in exact SVG namespace (http://www.w3.org/2000/svg).
    """
    raw_bytes = validate_bounded_input(svg_text)

    # 1. Prohibit ALL DOCTYPE and ENTITY declarations before parse (XXE / DTD expansion prevention)
    if re.search(r"<!DOCTYPE\b", svg_text, re.IGNORECASE) or re.search(r"<!ENTITY\b", svg_text, re.IGNORECASE):
        return False, "Prohibited DOCTYPE or ENTITY declaration", None

    # 2. Parse XML
    try:
        root = ET.fromstring(raw_bytes)
    except ET.ParseError as err:
        return False, f"XML parse error: {err}", None

    # 3. Iterative DOM bounds check (early abort on depth or flood)
    _measure_dom_bounds(root)

    # 4. Root element MUST be exact lowercase 'svg' and exact SVG namespace
    if root.tag != f"{{{SVG_NAMESPACE}}}svg":
        local_tag = _strip_ns(root.tag)
        if local_tag != "svg":
            return False, f"Root element must be lowercase 'svg', got '{local_tag}'", None
        return False, f"Root element must declare exact SVG namespace '{SVG_NAMESPACE}', got '{root.tag}'", None

    return True, None, root


def scan_security_violations(svg_text: str) -> List[str]:
    """Scan SVG source for lexical adverse signals (active content, scripts, and XXE).

    DISCLAIMER: This is a fixture-only lexical adverse signal detector for contract
    evaluation and testing. It is NOT an execution-grade sanitizer or security barrier.
    """
    violations: List[str] = []

    # 1. DOCTYPE / ENTITY declarations (XXE)
    if re.search(r"<!DOCTYPE\s+[^>]*\bSYSTEM\b", svg_text, re.IGNORECASE):
        violations.append("XML external entity declaration (DOCTYPE SYSTEM) detected")
    elif re.search(r"<!DOCTYPE\b", svg_text, re.IGNORECASE):
        violations.append("XML DOCTYPE declaration detected")
    elif re.search(r"<!ENTITY\s+", svg_text, re.IGNORECASE):
        violations.append("XML entity declaration (ENTITY) detected")

    # 2. <script> tags
    if re.search(r"<\s*([a-zA-Z0-9_-]+:)?script\b", svg_text, re.IGNORECASE):
        violations.append("Active <script> tag detected")

    # 3. Inline event handler attributes (onclick, onload, onerror, onmouseover, etc.)
    event_handlers = re.findall(r"""\b(on[a-z]{3,20})\s*=\s*["'][^"']*["']""", svg_text, re.IGNORECASE)
    if event_handlers:
        for handler in sorted(set(event_handlers)):
            violations.append(f"Inline event handler '{handler}' detected")

    # 4. javascript: URIs in href, xlink:href, or src
    if re.search(r"""(?:href|xlink:href|src)\s*=\s*["']\s*javascript:""", svg_text, re.IGNORECASE):
        violations.append("Active 'javascript:' URI detected in link or reference")

    # 5. <foreignObject> embedding active content
    fo_match = re.search(
        r"<\s*([a-zA-Z0-9_-]+:)?foreignObject\b[^>]*>(.*?)</\s*([a-zA-Z0-9_-]+:)?foreignObject\s*>",
        svg_text,
        re.IGNORECASE | re.DOTALL,
    )
    if fo_match:
        fo_content = fo_match.group(2)
        if re.search(r"<\s*script\b", fo_content, re.IGNORECASE) or re.search(r"\bon[a-z]+\s*=", fo_content, re.IGNORECASE):
            violations.append("Active script or event handler detected inside <foreignObject>")

    return violations


TRANSFORM_FN_RE = re.compile(
    r"""(?P<fn>matrix|translate|scale|rotate|skewX|skewY)\s*\(\s*(?P<args>[^)]*)\s*\)"""
)


def validate_transforms(root: ET.Element) -> List[Dict[str, Any]]:
    """Validate syntax, parameter counts, finite numbers, and separators in transforms."""
    errors: List[Dict[str, Any]] = []

    for elem in root.iter():
        transform_str = elem.get("transform")
        if not transform_str:
            continue

        local_tag = _strip_ns(elem.tag)
        elem_id = elem.get("id", f"<{local_tag}>")
        transformed_cleaned = transform_str.strip()

        if transformed_cleaned.count("(") != transformed_cleaned.count(")"):
            errors.append({
                "element": elem_id,
                "transform": transform_str,
                "error": "Malformed transform: unmatched parentheses",
            })
            continue

        # Reject malformed consecutive commas
        if re.search(r",\s*,", transformed_cleaned):
            errors.append({
                "element": elem_id,
                "transform": transform_str,
                "error": "Malformed transform: consecutive commas detected",
            })
            continue

        matches = list(TRANSFORM_FN_RE.finditer(transformed_cleaned))

        if not matches:
            fn_attempt = re.search(r"\b([a-zA-Z0-9_-]+)\s*\(", transformed_cleaned)
            if fn_attempt and fn_attempt.group(1) not in SUPPORTED_TRANSFORM_FUNCTIONS:
                errors.append({
                    "element": elem_id,
                    "transform": transform_str,
                    "error": f"Malformed transform: unsupported transform function '{fn_attempt.group(1)}'",
                })
            else:
                errors.append({
                    "element": elem_id,
                    "transform": transform_str,
                    "error": "Malformed transform: no valid transform functions recognized",
                })
            continue

        # Check for unparsed intermediate or trailing characters
        reconstructed = "".join(m.group(0) for m in matches)
        clean_orig = re.sub(r"[\s,]+", "", transformed_cleaned)
        clean_recon = re.sub(r"[\s,]+", "", reconstructed)
        if clean_orig != clean_recon:
            errors.append({
                "element": elem_id,
                "transform": transform_str,
                "error": "Malformed transform: contains unrecognized characters or unmatched parentheses",
            })
            continue

        for m in matches:
            fn = m.group("fn")
            args_str = m.group("args").strip()

            if re.search(r",\s*,", args_str):
                errors.append({
                    "element": elem_id,
                    "transform": transform_str,
                    "error": f"Function '{fn}' contains malformed consecutive comma separators in '{args_str}'",
                })
                continue

            raw_args = [tok for tok in re.split(r"[\s,]+", args_str) if tok]

            numeric_args: List[float] = []
            valid_numbers = True
            for tok in raw_args:
                try:
                    val = float(tok)
                    if not math.isfinite(val):
                        valid_numbers = False
                        break
                    numeric_args.append(val)
                except ValueError:
                    valid_numbers = False
                    break

            if not valid_numbers:
                errors.append({
                    "element": elem_id,
                    "transform": transform_str,
                    "error": f"Function '{fn}' contains non-numeric or non-finite argument in '{args_str}'",
                })
                continue

            arg_count = len(numeric_args)
            if fn == "matrix" and arg_count != 6:
                errors.append({
                    "element": elem_id,
                    "transform": transform_str,
                    "error": f"Function 'matrix' requires exactly 6 arguments, got {arg_count}",
                })
            elif fn == "translate" and arg_count not in (1, 2):
                errors.append({
                    "element": elem_id,
                    "transform": transform_str,
                    "error": f"Function 'translate' requires 1 or 2 arguments, got {arg_count}",
                })
            elif fn == "scale" and arg_count not in (1, 2):
                errors.append({
                    "element": elem_id,
                    "transform": transform_str,
                    "error": f"Function 'scale' requires 1 or 2 arguments, got {arg_count}",
                })
            elif fn == "rotate" and arg_count not in (1, 3):
                errors.append({
                    "element": elem_id,
                    "transform": transform_str,
                    "error": f"Function 'rotate' requires 1 or 3 arguments, got {arg_count}",
                })
            elif fn in ("skewX", "skewY") and arg_count != 1:
                errors.append({
                    "element": elem_id,
                    "transform": transform_str,
                    "error": f"Function '{fn}' requires exactly 1 argument, got {arg_count}",
                })

    return errors


def _matrix_multiply(m1: List[float], m2: List[float]) -> List[float]:
    """Multiply two 2D affine transformation matrices [a, b, c, d, e, f]."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return [
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    ]


def _parse_single_transform_matrix(fn: str, args: List[float]) -> List[float]:
    """Compute 2D affine matrix for an individual transform function."""
    if fn == "matrix":
        return args
    elif fn == "translate":
        tx = args[0]
        ty = args[1] if len(args) > 1 else 0.0
        return [1.0, 0.0, 0.0, 1.0, tx, ty]
    elif fn == "scale":
        sx = args[0]
        sy = args[1] if len(args) > 1 else sx
        return [sx, 0.0, 0.0, sy, 0.0, 0.0]
    elif fn == "rotate":
        angle_rad = math.radians(args[0])
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        rot_m = [cos_a, sin_a, -sin_a, cos_a, 0.0, 0.0]
        if len(args) == 3:
            cx, cy = args[1], args[2]
            t1 = [1.0, 0.0, 0.0, 1.0, cx, cy]
            t2 = [1.0, 0.0, 0.0, 1.0, -cx, -cy]
            return _matrix_multiply(_matrix_multiply(t1, rot_m), t2)
        return rot_m
    elif fn == "skewX":
        tan_a = math.tan(math.radians(args[0]))
        return [1.0, 0.0, tan_a, 1.0, 0.0, 0.0]
    elif fn == "skewY":
        tan_a = math.tan(math.radians(args[0]))
        return [1.0, tan_a, 0.0, 1.0, 0.0, 0.0]
    raise SvgContractError(f"Unsupported transform function: {fn}")


def apply_transform_to_point(transform_str: str, point: Tuple[float, float]) -> Tuple[float, float]:
    """Parse transform attribute and apply 2D affine transformation to point (x, y).

    In SVG, functions in a transform list are applied in composite product order.
    """
    matches = list(TRANSFORM_FN_RE.finditer(transform_str.strip()))
    if not matches:
        raise SvgContractError(f"No valid transform functions in: {transform_str}")

    composite: List[float] = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
    for m in matches:
        fn = m.group("fn")
        args_str = m.group("args").strip()
        args = [float(t) for t in re.split(r"[\s,]+", args_str) if t]
        fn_m = _parse_single_transform_matrix(fn, args)
        composite = _matrix_multiply(composite, fn_m)

    x, y = point
    a, b, c, d, e, f = composite
    new_x = a * x + c * y + e
    new_y = b * x + d * y + f
    return (round(new_x, 6), round(new_y, 6))


def validate_path_data(d_str: str) -> Dict[str, Any]:
    """Validate SVG path data syntax against bounded explicit-command geometry subset.

    Supported subset: M/m, L/l, H/h, V/v, Z/z (straight-line geometry).
    Unsupported commands: C/c, S/s, Q/q, T/t, A/a (curves and arcs) explicitly classified.
    """
    errors: List[str] = []
    unsupported_commands: List[str] = []
    cleaned = d_str.strip()

    if not cleaned:
        return {
            "is_valid": True,
            "supported_subset": True,
            "unsupported_commands": [],
            "errors": [],
            "command_count": 0,
        }

    # Reject malformed separators (e.g. consecutive commas)
    if re.search(r",\s*,", cleaned):
        errors.append("Malformed path data: consecutive commas detected")

    # Match numbers (including nan and inf) before individual command letters
    token_pattern = re.compile(
        r"""(?P<comma>,)|(?P<num>[-+]?(?:(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?|nan|inf(?:inity)?))|(?P<cmd>[a-zA-Z])|(?P<invalid>[^\s,a-zA-Z0-9.\-+]+)""",
        re.IGNORECASE,
    )

    tokens: List[Tuple[str, str]] = []
    pos = 0
    while pos < len(cleaned):
        m = token_pattern.match(cleaned, pos)
        if not m:
            if cleaned[pos].isspace():
                pos += 1
                continue
            errors.append(f"Unrecognized character '{cleaned[pos]}' at index {pos}")
            pos += 1
            continue

        kind = m.lastgroup
        val = m.group(0)
        pos = m.end()

        if kind == "invalid":
            errors.append(f"Malformed token '{val}' in path data")
        elif kind != "comma":
            tokens.append((kind, val))

    cmd_count = 0
    curr_cmd: Optional[str] = None
    curr_coords: List[float] = []

    def flush_command(cmd: str, coords: List[float]) -> None:
        nonlocal cmd_count
        cmd_count += 1
        upper_cmd = cmd.upper()
        if upper_cmd in ("C", "S", "Q", "T", "A"):
            if upper_cmd not in unsupported_commands:
                unsupported_commands.append(upper_cmd)
        elif upper_cmd not in ("M", "L", "H", "V", "Z"):
            errors.append(f"Unknown path command '{cmd}'")
            return

        if upper_cmd in ("M", "L"):
            if len(coords) < 2 or len(coords) % 2 != 0:
                errors.append(
                    f"Command '{cmd}' requires pairs of coordinates (x y), got {len(coords)}"
                )
        elif upper_cmd in ("H", "V"):
            if len(coords) < 1:
                errors.append(f"Command '{cmd}' requires at least 1 coordinate, got 0")
        elif upper_cmd == "Z":
            if len(coords) > 0:
                errors.append(f"Command '{cmd}' takes no coordinates, got {len(coords)}")

    for kind, val in tokens:
        if kind == "cmd":
            if curr_cmd is not None:
                flush_command(curr_cmd, curr_coords)
                curr_coords = []
            curr_cmd = val
        elif kind == "num":
            if curr_cmd is None:
                errors.append(f"Leading coordinate '{val}' without command")
                continue
            try:
                f_val = float(val)
                if not math.isfinite(f_val):
                    errors.append(f"Non-finite coordinate '{val}' in path")
                curr_coords.append(f_val)
            except ValueError:
                errors.append(f"Invalid number '{val}' in path")

    if curr_cmd is not None:
        flush_command(curr_cmd, curr_coords)

    is_valid = len(errors) == 0
    supported_subset = is_valid and len(unsupported_commands) == 0

    return {
        "is_valid": is_valid,
        "supported_subset": supported_subset,
        "unsupported_commands": unsupported_commands,
        "errors": errors,
        "command_count": cmd_count,
    }


@dataclass
class CycleDetectionResult:
    has_cycle: bool
    cycle_paths: List[List[str]] = field(default_factory=list)
    reference_graph: Dict[str, List[str]] = field(default_factory=dict)
    duplicate_ids: List[str] = field(default_factory=list)
    missing_targets: List[str] = field(default_factory=list)
    max_depth: int = 0
    depth_limit_exceeded: bool = False


def detect_sprite_cycles(root: ET.Element) -> CycleDetectionResult:
    """Build directed graph of <use> references, detect cycles, duplicates, missing targets, and depth."""
    seen_ids: Set[str] = set()
    duplicate_ids: List[str] = []

    # Map parent relationships for ancestor lookup
    parent_map: Dict[ET.Element, ET.Element] = {}
    for p in root.iter():
        for c in p:
            parent_map[c] = p

    # Collect IDs and detect duplicate IDs
    for elem in root.iter():
        elem_id = elem.get("id")
        if elem_id:
            if elem_id in seen_ids:
                if elem_id not in duplicate_ids:
                    duplicate_ids.append(elem_id)
            seen_ids.add(elem_id)

    graph: Dict[str, List[str]] = {i: [] for i in seen_ids}
    missing_targets: List[str] = []
    cycle_paths: List[List[str]] = []

    def _get_ancestor_ids(elem: ET.Element) -> List[str]:
        ancestors: List[str] = []
        curr = parent_map.get(elem)
        while curr is not None:
            cid = curr.get("id")
            if cid:
                ancestors.append(cid)
            curr = parent_map.get(curr)
        return ancestors

    for elem in root.iter():
        local_tag = _strip_ns(elem.tag).lower()
        if local_tag == "use":
            href = elem.get("href") or elem.get(f"{{{XLINK_NAMESPACE}}}href")
            if not href:
                continue
            if not href.startswith("#"):
                continue
            target_id = href[1:]

            if target_id not in seen_ids:
                if target_id not in missing_targets:
                    missing_targets.append(target_id)
                continue

            use_id = elem.get("id")
            if use_id:
                if use_id == target_id:
                    cycle_paths.append([use_id, target_id])
                if target_id not in graph.setdefault(use_id, []):
                    graph[use_id].append(target_id)

            # Check containment ancestor dependencies
            ancestor_ids = _get_ancestor_ids(elem)
            if target_id in ancestor_ids:
                idx = ancestor_ids.index(target_id)
                c_path = [target_id] + list(reversed(ancestor_ids[:idx])) + [target_id]
                cycle_paths.append(c_path)

            for anc_id in ancestor_ids:
                if target_id not in graph.setdefault(anc_id, []):
                    graph[anc_id].append(target_id)

    # Detect cycles via DFS
    visited: Set[str] = set()
    rec_stack: List[str] = []

    def dfs(node: str) -> None:
        rec_stack.append(node)
        visited.add(node)
        for neighbor in graph.get(node, []):
            if neighbor in rec_stack:
                idx = rec_stack.index(neighbor)
                cycle_paths.append(list(rec_stack[idx:]) + [neighbor])
            elif neighbor not in visited:
                dfs(neighbor)
        rec_stack.pop()

    for node in list(graph.keys()):
        if node not in visited:
            dfs(node)

    # Compute max chain depth if no cycles
    max_chain_depth = 0
    if not cycle_paths:
        memo_depth: Dict[str, int] = {}

        def compute_depth(node: str, path_set: Set[str]) -> int:
            if node in memo_depth:
                return memo_depth[node]
            if node in path_set:
                return 0
            path_set.add(node)
            m_d = 0
            for neighbor in graph.get(node, []):
                d = 1 + compute_depth(neighbor, path_set)
                if d > m_d:
                    m_d = d
            path_set.remove(node)
            memo_depth[node] = m_d
            return m_d

        for node in graph:
            d = compute_depth(node, set())
            if d > max_chain_depth:
                max_chain_depth = d

    depth_limit_exceeded = max_chain_depth > MAX_USE_DEPTH
    if depth_limit_exceeded:
        raise BoundedLimitExceededError(
            f"Sprite <use> chain depth {max_chain_depth} exceeds limit {MAX_USE_DEPTH}"
        )

    return CycleDetectionResult(
        has_cycle=len(cycle_paths) > 0,
        cycle_paths=cycle_paths,
        reference_graph=graph,
        duplicate_ids=duplicate_ids,
        missing_targets=missing_targets,
        max_depth=max_chain_depth,
        depth_limit_exceeded=depth_limit_exceeded,
    )


def classify_accessibility(root: ET.Element) -> Dict[str, Any]:
    """Classify SVG accessibility semantics and verify bounded label evidence.

    DISCLAIMER: This function checks structural accessible naming patterns and ARIA heuristics.
    It does NOT constitute proof of WCAG 2.2 conformance or browser accessibility-tree computation.
    """
    aria_hidden = root.get("aria-hidden", "").strip().lower()
    focusable = root.get("focusable", "").strip().lower()
    role = root.get("role", "").strip().lower()
    tabindex = root.get("tabindex")

    # Find <title> and <desc> child elements
    titles: List[str] = []
    descs: List[str] = []
    for child in root:
        child_tag = _strip_ns(child.tag).lower()
        if child_tag == "title" and child.text and child.text.strip():
            titles.append(child.text.strip())
        elif child_tag == "desc" and child.text and child.text.strip():
            descs.append(child.text.strip())

    aria_label = root.get("aria-label", "").strip()
    aria_labelledby = root.get("aria-labelledby", "").strip()

    # Defined IDs in document for resolving aria-labelledby references
    defined_ids: Set[str] = {elem.get("id") for elem in root.iter() if elem.get("id")}

    dangling_aria_labelledby: List[str] = []
    aria_labelledby_valid = False
    if aria_labelledby:
        tokens = [tok for tok in aria_labelledby.split() if tok]
        missing_ids = [tok for tok in tokens if tok not in defined_ids]
        if missing_ids:
            dangling_aria_labelledby = missing_ids
            aria_labelledby_valid = False
        else:
            aria_labelledby_valid = len(tokens) > 0

    bounded_label_evidence = bool(titles or aria_label or aria_labelledby_valid)
    is_aria_hidden = aria_hidden == "true"
    is_presentation_role = role in ("presentation", "none")

    # Interactive elements check
    interactive_tags = {"a", "button"}
    has_interactive_elements = any(_strip_ns(elem.tag).lower() in interactive_tags for elem in root.iter())
    is_interactive = bool(tabindex is not None or role in ("button", "link") or has_interactive_elements)

    if is_interactive:
        mode = "interactive"
    elif is_aria_hidden or (is_presentation_role and not bounded_label_evidence):
        mode = "decorative"
    elif bounded_label_evidence or role == "img":
        mode = "meaningful"
    else:
        mode = "ambiguous"

    naming_pattern_present = False
    if not dangling_aria_labelledby:
        if mode == "decorative" and is_aria_hidden:
            naming_pattern_present = True
        elif mode == "meaningful" and bounded_label_evidence and role == "img":
            naming_pattern_present = True
        elif mode == "interactive" and bounded_label_evidence:
            naming_pattern_present = True

    return {
        "mode": mode,
        "aria_hidden": is_aria_hidden,
        "focusable": focusable,
        "role": role,
        "tabindex": tabindex,
        "bounded_label_evidence": bounded_label_evidence,
        "titles": titles,
        "descs": descs,
        "aria_label": aria_label,
        "aria_labelledby": aria_labelledby,
        "dangling_aria_labelledby": dangling_aria_labelledby,
        "naming_pattern_present": naming_pattern_present,
    }


def check_viewbox_and_sizing(root: ET.Element) -> Dict[str, Any]:
    """Parse and validate viewBox, aspect ratio, and fluid sizing parameters."""
    viewbox_str = root.get("viewBox")
    preserve_aspect = root.get("preserveAspectRatio", "xMidYMid meet").strip()
    width = root.get("width")
    height = root.get("height")

    parsed_viewbox: Optional[Tuple[float, float, float, float]] = None
    is_valid_viewbox = False
    viewbox_error: Optional[str] = None

    if viewbox_str is not None:
        raw_vb = viewbox_str.strip()
        if re.search(r",\s*,", raw_vb):
            viewbox_error = f"Malformed separators in viewBox '{viewbox_str}'"
        elif re.search(r"[^0-9eE\.\,\-\+\s]", raw_vb):
            viewbox_error = f"Malformed characters in viewBox '{viewbox_str}'"
        else:
            tokens = [tok for tok in re.split(r"[\s,]+", raw_vb) if tok]
            if len(tokens) == 4:
                try:
                    coords = [float(t) for t in tokens]
                    if not all(math.isfinite(c) for c in coords):
                        viewbox_error = f"Non-finite numbers in viewBox '{viewbox_str}'"
                    else:
                        min_x, min_y, vb_w, vb_h = coords
                        if vb_w <= 0 or vb_h <= 0:
                            viewbox_error = f"viewBox width ({vb_w}) and height ({vb_h}) must be strictly positive"
                        else:
                            parsed_viewbox = (min_x, min_y, vb_w, vb_h)
                            is_valid_viewbox = True
                except ValueError:
                    viewbox_error = f"Non-numeric values in viewBox '{viewbox_str}'"
            else:
                viewbox_error = f"viewBox requires exactly 4 numbers, got {len(tokens)}"

    fluid_sizing_attributes = is_valid_viewbox and (not width or width == "100%") and (not height or height == "100%")

    return {
        "has_viewbox": bool(viewbox_str),
        "viewbox_str": viewbox_str,
        "parsed_viewbox": parsed_viewbox,
        "is_valid_viewbox": is_valid_viewbox,
        "viewbox_error": viewbox_error,
        "preserve_aspect_ratio": preserve_aspect,
        "width": width,
        "height": height,
        "fluid_sizing_attributes": fluid_sizing_attributes,
    }


def check_paint_and_currentcolor(root: ET.Element) -> Dict[str, Any]:
    """Analyze paint attributes and currentColor usage."""
    currentcolor_elements: List[str] = []
    gradient_references: List[str] = []
    missing_id_references: List[str] = []

    defined_ids: Set[str] = {elem.get("id") for elem in root.iter() if elem.get("id")}
    paint_attrs = ("fill", "stroke")
    url_re = re.compile(r"""url\(\s*['"]?#([^'")]+)['"]?\s*\)""")

    for elem in root.iter():
        elem_id = elem.get("id", f"<{_strip_ns(elem.tag)}>")
        for attr in paint_attrs:
            val = elem.get(attr, "").strip()
            if val.lower() == "currentcolor":
                currentcolor_elements.append(f"{elem_id}[{attr}=currentColor]")
            else:
                m = url_re.search(val)
                if m:
                    target_id = m.group(1)
                    gradient_references.append(target_id)
                    if target_id not in defined_ids:
                        missing_id_references.append(target_id)

        style_str = elem.get("style", "")
        if "currentColor" in style_str:
            currentcolor_elements.append(f"{elem_id}[style]")

    return {
        "has_currentcolor": len(currentcolor_elements) > 0,
        "currentcolor_elements": currentcolor_elements,
        "gradient_references": gradient_references,
        "missing_id_references": missing_id_references,
        "is_paint_valid": len(missing_id_references) == 0,
    }


def check_clipping_and_masking(root: ET.Element) -> Dict[str, Any]:
    """Analyze clipPath and mask definitions and references."""
    defined_clips: Set[str] = set()
    defined_masks: Dict[str, str] = {}
    clip_references: List[str] = []
    mask_references: List[str] = []
    missing_clips: List[str] = []
    missing_masks: List[str] = []

    for elem in root.iter():
        tag = _strip_ns(elem.tag)
        elem_id = elem.get("id")
        if tag == "clipPath" and elem_id:
            defined_clips.add(elem_id)
        elif tag == "mask" and elem_id:
            mask_type = elem.get("mask-type", "luminance").strip()
            defined_masks[elem_id] = mask_type

    url_re = re.compile(r"""url\(\s*['"]?#([^'")]+)['"]?\s*\)""")

    for elem in root.iter():
        clip_val = elem.get("clip-path", "")
        m_clip = url_re.search(clip_val)
        if m_clip:
            c_id = m_clip.group(1)
            clip_references.append(c_id)
            if c_id not in defined_clips:
                missing_clips.append(c_id)

        mask_val = elem.get("mask", "")
        m_mask = url_re.search(mask_val)
        if m_mask:
            m_id = m_mask.group(1)
            mask_references.append(m_id)
            if m_id not in defined_masks:
                missing_masks.append(m_id)

    return {
        "defined_clips": list(defined_clips),
        "defined_masks": defined_masks,
        "clip_references": clip_references,
        "mask_references": mask_references,
        "missing_clips": missing_clips,
        "missing_masks": missing_masks,
        "is_valid": len(missing_clips) == 0 and len(missing_masks) == 0,
    }


GRAPHIC_TAGS: Set[str] = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text", "tspan"}


def _checked_xml_structure(element: ET.Element, text_sensitive: bool = False) -> tuple:
    """Conservative fixture identity, ignoring only inter-element indentation.

    This is not rendering equivalence. All attributes, order, nesting and text
    content are retained. Whitespace in text, style and script regions is exact.
    ElementTree's default parser omits comments; fixtures authorize that removal.
    """
    text_sensitive = text_sensitive or _strip_ns(element.tag) in {
        "text", "tspan", "textPath", "title", "desc", "style", "script"
    } or element.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve"
    def content(value: str | None, sensitive: bool) -> str:
        value = value or ""
        return value if sensitive or value.strip() else ""
    return (
        element.tag, tuple(sorted(element.attrib.items())),
        content(element.text, text_sensitive),
        tuple((_checked_xml_structure(child, text_sensitive), content(child.tail, text_sensitive)) for child in element),
    )


def evaluate_optimization_safety(original_svg: str, optimized_svg: str) -> Dict[str, Any]:
    """Check conservative XML structure for the fixture's permitted cleanup.

    A pass proves only this structural comparison, never arbitrary optimizer
    safety, resource safety, accessible trees or equivalent browser rendering.
    """
    orig_ok, orig_err, orig_root = check_xml_well_formedness(original_svg)
    opt_ok, opt_err, opt_root = check_xml_well_formedness(optimized_svg)
    if not orig_ok or orig_root is None:
        return {"preserved_checked_structure": False, "defects": [f"Original SVG is malformed: {orig_err}"]}
    if not opt_ok or opt_root is None:
        return {"preserved_checked_structure": False, "defects": [f"Optimized SVG is malformed: {opt_err}"]}
    defects = []
    if orig_root.get("viewBox") != opt_root.get("viewBox"):
        defects.append("viewBox changed or removed")
    if classify_accessibility(orig_root)["titles"] != classify_accessibility(opt_root)["titles"]:
        defects.append("title text changed or removed")
    if check_paint_and_currentcolor(opt_root)["missing_id_references"]:
        defects.append("paint ID references became unresolved")
    if _checked_xml_structure(orig_root) != _checked_xml_structure(opt_root):
        defects.append("checked XML structure changed: attributes, geometry, names, text, order or nesting")
    original_bytes = len(original_svg.encode("utf-8"))
    optimized_bytes = len(optimized_svg.encode("utf-8"))
    return {
        "preserved_checked_structure": not defects,
        "defects": defects,
        "original_bytes": original_bytes,
        "optimized_bytes": optimized_bytes,
        "reduction_bytes": original_bytes - optimized_bytes,
    }


def _strict_json_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    """JSON object hook rejecting duplicate keys."""
    res: Dict[str, Any] = {}
    for k, v in pairs:
        if k in res:
            fail(f"Duplicate JSON key: {k}")
        res[k] = v
    return res


def load_scenario_fixture(fixture_path: Path) -> Dict[str, Any]:
    """Load and validate scenarios fixture JSON with strict schema and frozen vocabulary."""
    if not fixture_path.is_file():
        fail(f"Fixture file not found: {fixture_path}")

    data = json.loads(fixture_path.read_text(encoding="utf-8"), object_pairs_hook=_strict_json_object)

    if not isinstance(data, dict):
        fail("Fixture root must be a JSON object")

    if data.get("schema_version") != 1:
        fail(f"Expected schema_version 1, got {data.get('schema_version')}")

    authority = data.get("authority")
    if not isinstance(authority, dict) or authority.get("phase") != "APG122":
        fail("Invalid or missing APG122 authority block")

    vocab = data.get("vocabulary")
    if not isinstance(vocab, dict):
        fail("Missing required vocabulary block")

    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        fail("Fixture rows must be a non-empty list")

    seen_ids: Set[str] = set()
    id_pattern = re.compile(r"^APG122-SVG-\d{3}$")

    for row in rows:
        if not isinstance(row, dict):
            fail("Each scenario row must be a JSON object")

        row_keys = set(row.keys())
        if row_keys != set(SCENARIO_ROW_KEYS):
            missing = set(SCENARIO_ROW_KEYS) - row_keys
            extra = row_keys - set(SCENARIO_ROW_KEYS)
            fail(f"Row has invalid keys: missing {missing}, unexpected {extra}")

        row_id = row.get("id")
        if not isinstance(row_id, str) or not id_pattern.match(row_id):
            fail(f"Invalid row ID format: '{row_id}'")
        if row_id in seen_ids:
            fail(f"Duplicate scenario ID: {row_id}")
        seen_ids.add(row_id)

        category = row.get("category")
        if category not in CATEGORIES:
            fail(f"Row {row_id} has unknown category '{category}'")

        purpose = row.get("purpose")
        if not isinstance(purpose, str) or not purpose.strip():
            fail(f"Row {row_id} missing non-empty 'purpose'")

        fixture_file = row.get("fixture_file")
        if not isinstance(fixture_file, str) or not fixture_file.endswith(".svg"):
            fail(f"Row {row_id} fixture_file must be a .svg file")
        if ".." in fixture_file or "/" in fixture_file or "\\" in fixture_file:
            fail(f"Row {row_id} fixture_file contains invalid path traversal: '{fixture_file}'")

        target_path = fixture_path.parent / fixture_file
        if not target_path.is_file():
            fail(f"Fixture file '{fixture_file}' referenced by row {row_id} does not exist")

        selection = row.get("selection")
        if selection not in SELECTIONS:
            fail(f"Row {row_id} has invalid selection '{selection}'")

        response = row.get("response")
        if response not in RESPONSES:
            fail(f"Row {row_id} has invalid response '{response}'")

        route = row.get("route")
        if route not in ROUTES:
            fail(f"Row {row_id} has invalid route '{route}'")

        clauses = row.get("clauses")
        if not isinstance(clauses, list) or not clauses:
            fail(f"Row {row_id} must have non-empty clauses list")
        for c in clauses:
            if c not in CLAUSE_IDS:
                fail(f"Row {row_id} references unknown clause '{c}'")

        invariants = row.get("invariants")
        if not isinstance(invariants, list) or not invariants:
            fail(f"Row {row_id} must have non-empty invariants list")
        for inv in invariants:
            if not isinstance(inv, str) or not inv.strip():
                fail(f"Row {row_id} contains empty invariant")

    return data


def evaluate_scenario_row(row: Dict[str, Any], fixtures_dir: Path) -> Dict[str, Any]:
    """Evaluate a single scenario row, reporting navigation-only handoffs without semantic replay."""
    row_id = row["id"]
    category = row["category"]
    route = row["route"]
    response = row["response"]
    # Frozen scenario outcome binding; category changes cannot silently choose
    # a weaker branch. This binds navigation, not prose semantic equivalence.
    expected = (
        ("geometry-and-sizing", "proceed-routine"),
        ("sprites-and-use", "proceed-routine"),
        ("sprites-and-use-negative", "stop-and-escalate"),
        ("sprites-and-use-negative", "stop-and-escalate"),
        ("paint-and-masking", "proceed-routine"),
        ("transforms-negative", "stop-and-escalate"),
        ("accessibility", "proceed-routine"),
        ("accessibility", "proceed-routine"),
        ("paint-and-theming", "proceed-routine"),
        ("security-negative", "stop-and-escalate"),
        ("security-negative", "stop-and-escalate"),
        ("security-negative", "stop-and-escalate"),
        ("security-negative", "stop-and-escalate"),
        ("resource-contexts", "proceed-routine"),
        ("serialization-negative", "stop-and-escalate"),
        ("optimization-negative", "stop-and-escalate"),
        ("optimization-safe", "proceed-routine"),
        ("boundaries", "bounded-local-decision"),
        ("boundaries", "proceed-routine"),
        ("boundaries", "inspect-before-judgment"),
        ("boundaries", "proceed-routine"),
        ("accessibility", "inspect-before-judgment"),
        ("performance-limits", "stop-and-escalate"),
        ("boundaries", "proceed-routine"),
    )
    outcomes = {f"APG122-SVG-{i:03d}": value for i, value in enumerate(expected, 1)}
    if outcomes.get(row_id) != (category, response):
        fail("scenario category/response differs from frozen outcome")
    fixture_file = row["fixture_file"]
    if Path(fixture_file).name != fixture_file or ".." in fixture_file or "\\" in fixture_file:
        fail("unsupported fixture path")
    file_path = fixtures_dir / fixture_file
    content = file_path.read_text(encoding="utf-8")

    is_navigation_only = category in ("boundaries", "performance-limits")

    if is_navigation_only:
        return {
            "id": row_id,
            "category": category,
            "mode": "navigation-only",
            "reporting": "navigation-only",
            "route": route,
            "response": response,
            "status": "passed",
        }

    # Semantic evaluation of internal SVG categories
    if response == "stop-and-escalate":
        if category == "security-negative":
            is_ok, err, _ = check_xml_well_formedness(content)
            violations = scan_security_violations(content)
            assert (not is_ok and "Prohibited" in str(err)) or len(violations) > 0, (
                f"{row_id}: Expected security failure"
            )
        elif category == "sprites-and-use-negative":
            _, _, root = check_xml_well_formedness(content)
            assert root is not None
            cycle_res = detect_sprite_cycles(root)
            assert cycle_res.has_cycle is True, f"{row_id}: Expected cycle detection"
        elif category == "transforms-negative":
            _, _, root = check_xml_well_formedness(content)
            assert root is not None
            t_errors = validate_transforms(root)
            assert len(t_errors) > 0, f"{row_id}: Expected transform errors"
        elif category == "serialization-negative":
            is_ok, _, _ = check_xml_well_formedness(content)
            assert is_ok is False, f"{row_id}: Expected XML parsing failure"
        elif category == "optimization-negative":
            orig = (fixtures_dir / "text-a11y-meaningful.svg").read_text(encoding="utf-8")
            opt_res = evaluate_optimization_safety(orig, content)
            assert opt_res["preserved_checked_structure"] is False, f"{row_id}: Expected optimization unsafe"

    elif response == "proceed-routine":
        is_ok, err, root = check_xml_well_formedness(content)
        assert is_ok is True and root is not None, f"{row_id}: Must be well-formed: {err}"
        violations = scan_security_violations(content)
        assert len(violations) == 0, f"{row_id}: Must have zero security violations"

        if category == "geometry-and-sizing":
            vb_info = check_viewbox_and_sizing(root)
            assert vb_info["is_valid_viewbox"] is True
            assert vb_info["fluid_sizing_attributes"] is True
        elif category == "sprites-and-use":
            cycle_res = detect_sprite_cycles(root)
            assert cycle_res.has_cycle is False
            assert len(cycle_res.duplicate_ids) == 0
            assert len(cycle_res.missing_targets) == 0
        elif category == "paint-and-masking":
            cm_info = check_clipping_and_masking(root)
            assert cm_info["is_valid"] is True
        elif category == "paint-and-theming":
            paint_info = check_paint_and_currentcolor(root)
            assert paint_info["has_currentcolor"] is True
        elif category == "resource-contexts":
            for elem in root.iter():
                href = elem.get("href") or elem.get(f"{{{XLINK_NAMESPACE}}}href")
                if href:
                    assert href.startswith("#"), f"{row_id}: External href forbidden in image mode"
        elif category == "accessibility":
            a11y = classify_accessibility(root)
            if row_id == "APG122-SVG-007":
                assert a11y["mode"] == "meaningful"
                assert a11y["bounded_label_evidence"] is True
                assert a11y["naming_pattern_present"] is True
            elif row_id == "APG122-SVG-008":
                assert a11y["mode"] == "decorative"
                assert a11y["aria_hidden"] is True
                assert a11y["naming_pattern_present"] is True
        elif category == "optimization-safe":
            unopt = (fixtures_dir / "safe-unoptimized-source.svg").read_text(encoding="utf-8")
            opt_res = evaluate_optimization_safety(unopt, content)
            assert opt_res["preserved_checked_structure"] is True
            assert opt_res["reduction_bytes"] > 0

    elif response == "inspect-before-judgment":
        if category == "accessibility":
            is_ok, _, root = check_xml_well_formedness(content)
            assert is_ok is True and root is not None
            a11y = classify_accessibility(root)
            assert a11y["mode"] == "ambiguous"
            assert a11y["bounded_label_evidence"] is False

    return {
        "id": row_id,
        "category": category,
        "mode": "semantic-evaluation",
        "reporting": "semantic-evaluation",
        "route": route,
        "response": response,
        "status": "passed",
    }
