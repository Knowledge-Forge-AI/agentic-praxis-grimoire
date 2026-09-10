#!/usr/bin/env python3
"""Maintained unit test suite for APG122 SVG language profile.

Mirrors owner skills/svg-language-profile/SKILL.md.
Asserts bounded predicates, negative mutation controls, cycle detection, security scanning,
accessibility classification, path geometry subset, transform point noncommutativity,
and optimization safety independent of leaf token checks.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import pytest

from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg122_svg_contract import (  # noqa: E402
    BoundedLimitExceededError,
    CATEGORIES,
    CLAUSE_IDS,
    LEXICAL_SCAN_DISCLAIMER,
    MAX_DOM_DEPTH,
    MAX_ELEMENT_COUNT,
    MAX_SVG_BYTES,
    MAX_USE_DEPTH,
    OPTIMIZATION_DISCLAIMER,
    PROOF_DISCLAIMER,
    SCENARIO_ROW_KEYS,
    SVG_NAMESPACE,
    SvgContractError,
    apply_transform_to_point,
    check_clipping_and_masking,
    check_paint_and_currentcolor,
    check_viewbox_and_sizing,
    check_xml_well_formedness,
    classify_accessibility,
    detect_sprite_cycles,
    evaluate_optimization_safety,
    evaluate_scenario_row,
    load_scenario_fixture,
    scan_security_violations,
    validate_bounded_input,
    validate_path_data,
    validate_transforms,
)

FIXTURES_DIR = ROOT / "src/test/fixtures/apg122-svg"
SCENARIOS_PATH = FIXTURES_DIR / "scenarios.json"
ARCH_PATH = ROOT / "docs/architecture/v0-10-svg-language-profile.md"


def test_leaf_clause_navigation_is_exact() -> None:
    """Navigation evidence only; semantic predicates remain fixture-owned."""
    import re

    leaf = (ROOT / "skills/svg-language-profile/SKILL.md").read_text(encoding="utf-8")
    anchors = re.findall(r"\*\*(SVG-\d{2}-[A-Z0-9-]+)\.\*\*", leaf)
    assert len(anchors) == len(set(anchors))
    assert set(anchors) == set(CLAUSE_IDS)


def test_architecture_specification_coherence() -> None:
    """Verify architecture doc covers all stable clause IDs, primary sources, and bounds."""
    assert ARCH_PATH.is_file(), "Architecture document must exist"
    arch_text = ARCH_PATH.read_text(encoding="utf-8")

    # Verify all 15 stable clause IDs are explicitly specified in architecture document
    for clause_id in CLAUSE_IDS:
        assert clause_id in arch_text, f"Clause {clause_id} must be present in architecture document"

    # Verify primary standards and normative canonical sources are cited by URL / link
    for spec_link in (
        "w3.org/TR/SVG2",
        "w3.org/TR/SVG11",
        "html.spec.whatwg.org",
        "w3.org/TR/xml",
        "w3.org/TR/css-transforms",
        "w3.org/TR/css-masking",
        "w3.org/TR/filter-effects",
        "w3.org/TR/WCAG",
    ):
        assert spec_link.lower() in arch_text.lower(), f"Primary spec link {spec_link} must be cited"

    # Verify non-owner handoff boundary routes
    for non_owner in ("css-language-profile", "javascript-language-profile", "jsx-language-profile"):
        assert non_owner in arch_text, f"Non-owner boundary {non_owner} must be cited"

    # Verify explicit proof disclaimers
    assert "rasterization proof" in arch_text
    assert "accessibility-tree computation proof" in arch_text


def test_scenarios_fixture_schema_and_vocabulary() -> None:
    """Verify scenarios fixture JSON schema, authority, vocabulary, and file existence."""
    fixture = load_scenario_fixture(SCENARIOS_PATH)

    assert fixture["schema_version"] == 1
    assert fixture["authority"]["phase"] == "APG122"
    assert "disclaimer" in fixture["authority"]

    rows = fixture["rows"]
    assert len(rows) == 24, "Must contain exactly 24 scenarios"

    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "All scenario IDs must be unique"
    for r_id in ids:
        assert r_id.startswith("APG122-SVG-")

    # Verify every fixture file referenced exists in FIXTURES_DIR without path traversal
    for row in rows:
        fixture_file = row["fixture_file"]
        assert ".." not in fixture_file and "/" not in fixture_file and "\\" not in fixture_file
        file_path = FIXTURES_DIR / fixture_file
        assert file_path.is_file(), f"Fixture file {fixture_file} for scenario {row['id']} must exist"

        # Verify exact frozen row keys
        assert set(row.keys()) == set(SCENARIO_ROW_KEYS)
        assert row["category"] in CATEGORIES


def test_scenario_fixture_schema_mutation_controls(tmp_path: Path) -> None:
    """Mutation controls: reject unknown categories, invalid keys, and path traversal."""
    import json

    base_fixture = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))

    # 1. Unknown category rejection
    bad_cat = json.loads(json.dumps(base_fixture))
    bad_cat["rows"][0]["category"] = "unknown-arbitrary-category"
    bad_cat_file = tmp_path / "bad_cat.json"
    bad_cat_file.write_text(json.dumps(bad_cat), encoding="utf-8")
    with pytest.raises(SvgContractError, match="unknown category"):
        load_scenario_fixture(bad_cat_file)

    # 2. Path traversal rejection
    bad_path = json.loads(json.dumps(base_fixture))
    bad_path["rows"][0]["fixture_file"] = "../etc/passwd.svg"
    bad_path_file = tmp_path / "bad_path.json"
    bad_path_file.write_text(json.dumps(bad_path), encoding="utf-8")
    with pytest.raises(SvgContractError, match="path traversal"):
        load_scenario_fixture(bad_path_file)

    # 3. Missing required key rejection
    bad_keys = json.loads(json.dumps(base_fixture))
    del bad_keys["rows"][0]["invariants"]
    bad_keys_file = tmp_path / "bad_keys.json"
    bad_keys_file.write_text(json.dumps(bad_keys), encoding="utf-8")
    with pytest.raises(SvgContractError, match="invalid keys"):
        load_scenario_fixture(bad_keys_file)

    # 4. Extra unexpected key rejection
    extra_keys = json.loads(json.dumps(base_fixture))
    extra_keys["rows"][0]["unapproved_extra_field"] = True
    extra_keys_file = tmp_path / "extra_keys.json"
    extra_keys_file.write_text(json.dumps(extra_keys), encoding="utf-8")
    with pytest.raises(SvgContractError, match="invalid keys"):
        load_scenario_fixture(extra_keys_file)


def test_responsive_logo_illustration_predicates() -> None:
    """Test responsive logo + illustration geometry, sizing, and viewBox validity."""
    content = (FIXTURES_DIR / "responsive-logo-illustration.svg").read_text(encoding="utf-8")

    is_ok, err, root = check_xml_well_formedness(content)
    assert is_ok and root is not None, f"Should be well-formed XML: {err}"

    # Viewbox and fluid sizing checks
    vb_info = check_viewbox_and_sizing(root)
    assert vb_info["has_viewbox"] is True
    assert vb_info["is_valid_viewbox"] is True
    assert vb_info["parsed_viewbox"] == (0.0, 0.0, 800.0, 600.0)
    assert vb_info["preserve_aspect_ratio"] == "xMidYMid meet"
    assert vb_info["fluid_sizing_attributes"] is True

    # Security checks
    violations = scan_security_violations(content)
    assert len(violations) == 0, f"Expected 0 violations, got {violations}"

    # Paint & defs checks
    paint_info = check_paint_and_currentcolor(root)
    assert paint_info["is_paint_valid"] is True
    assert "bg-grad" in paint_info["gradient_references"]
    assert "brand-grad" in paint_info["gradient_references"]

    # Path data subset validation on emblem geometry
    emblem_path_elem = root.find(f".//{{{SVG_NAMESPACE}}}path")
    assert emblem_path_elem is not None
    emblem_d = emblem_path_elem.get("d", "")
    p_info = validate_path_data(emblem_d)
    assert p_info["is_valid"] is True
    assert p_info["supported_subset"] is True
    assert p_info["command_count"] >= 5


def test_bounded_path_data_geometry_subset() -> None:
    """Test path data parser supporting M/L/H/V/Z subset and explicitly classifying unsupported commands."""
    # 1. Valid supported straight-line subset
    valid_path = "M 10 20 L 30 40 H 50 V 60 Z"
    res_valid = validate_path_data(valid_path)
    assert res_valid["is_valid"] is True
    assert res_valid["supported_subset"] is True
    assert len(res_valid["unsupported_commands"]) == 0
    assert len(res_valid["errors"]) == 0

    # 2. Unsupported curves (C, S, Q, T) and arcs (A) explicitly classified
    curves_path = "M 0 0 C 10 20, 30 40, 50 60 S 70 80, 90 100 Q 110 120, 130 140 T 150 160 A 5 5 0 0 1 200 200 Z"
    res_curves = validate_path_data(curves_path)
    assert res_curves["is_valid"] is True
    assert res_curves["supported_subset"] is False
    assert set(res_curves["unsupported_commands"]) == {"C", "S", "Q", "T", "A"}

    # 3. Negative control: missing coordinate for command
    res_missing = validate_path_data("M 10")
    assert res_missing["is_valid"] is False
    assert any("requires pairs of coordinates" in e for e in res_missing["errors"])

    # 4. Negative control: malformed consecutive commas
    res_commas = validate_path_data("M 10,,20 L 30 40")
    assert res_commas["is_valid"] is False
    assert any("consecutive commas" in e for e in res_commas["errors"])

    # 5. Negative control: unknown command letter
    res_unknown = validate_path_data("M 10 20 X 30 40")
    assert res_unknown["is_valid"] is False
    assert any("Unknown path command" in e for e in res_unknown["errors"])

    # 6. Negative control: non-finite numbers
    res_nan = validate_path_data("M 10 nan L 30 40")
    assert res_nan["is_valid"] is False
    assert any("Non-finite" in e for e in res_nan["errors"])


def test_point_transform_noncommutativity() -> None:
    """Test exact 2D point transformation verifying matrix multiplication noncommutativity."""
    point = (10.0, 0.0)

    # Transform 1: Translate then Rotate
    # In SVG: transform="translate(100, 0) rotate(90)" -> net: M_translate * M_rotate
    # Rotate(90) on (10, 0) -> (0, 10), then Translate(100, 0) -> (100, 10)
    p1 = apply_transform_to_point("translate(100, 0) rotate(90)", point)
    assert math.isclose(p1[0], 100.0, abs_tol=1e-5)
    assert math.isclose(p1[1], 10.0, abs_tol=1e-5)

    # Transform 2: Rotate then Translate (reversed order)
    # In SVG: transform="rotate(90) translate(100, 0)" -> net: M_rotate * M_translate
    # Translate(100, 0) on (10, 0) -> (110, 0), then Rotate(90) -> (0, 110)
    p2 = apply_transform_to_point("rotate(90) translate(100, 0)", point)
    assert math.isclose(p2[0], 0.0, abs_tol=1e-5)
    assert math.isclose(p2[1], 110.0, abs_tol=1e-5)

    # Explicit noncommutativity proof
    assert p1 != p2, f"Matrix multiplication must be non-commutative: {p1} != {p2}"


def test_geometry_transform_negative_controls() -> None:
    """Test geometry transform syntax validator catching malformed parameters and separators."""
    content = (FIXTURES_DIR / "geometry-transform-negative.svg").read_text(encoding="utf-8")
    _, _, root = check_xml_well_formedness(content)
    assert root is not None

    errors = validate_transforms(root)
    assert len(errors) >= 3, f"Should find at least 3 transform errors, found {len(errors)}"

    error_messages = [e["error"] for e in errors]
    assert any("matrix" in msg and "requires exactly 6 arguments" in msg for msg in error_messages)
    assert any("scale" in msg and "non-numeric" in msg for msg in error_messages)
    assert any("unmatched parentheses" in msg or "unrecognized characters" in msg for msg in error_messages)

    # Mutation control: consecutive commas in transform arguments
    xml_commas = f'<svg xmlns="{SVG_NAMESPACE}"><g transform="translate(10,,20)" /></svg>'
    _, _, root_commas = check_xml_well_formedness(xml_commas)
    assert root_commas is not None
    errs_commas = validate_transforms(root_commas)
    assert any("consecutive commas" in e["error"] for e in errs_commas)

    # Mutation control: unsupported transform function rejection
    xml_unsupported = f'<svg xmlns="{SVG_NAMESPACE}"><g transform="perspective(500px)" /></svg>'
    _, _, root_unsup = check_xml_well_formedness(xml_unsupported)
    assert root_unsup is not None
    errs_unsup = validate_transforms(root_unsup)
    assert any("unsupported transform function" in e["error"] for e in errs_unsup)


def test_sprite_references_valid_and_cycles() -> None:
    """Test sprite symbol definitions, use instantiations, and cycle detection."""
    # 1. Valid sprite references
    valid_content = (FIXTURES_DIR / "sprite-references-valid.svg").read_text(encoding="utf-8")
    _, _, valid_root = check_xml_well_formedness(valid_content)
    assert valid_root is not None
    res_valid = detect_sprite_cycles(valid_root)
    assert res_valid.has_cycle is False, "Valid sprites must have no reference cycles"
    assert len(res_valid.duplicate_ids) == 0
    assert len(res_valid.missing_targets) == 0
    assert res_valid.max_depth <= MAX_USE_DEPTH

    # 2. Direct cycle control (#sym-direct -> #sym-direct)
    direct_content = (FIXTURES_DIR / "sprite-cycle-direct.svg").read_text(encoding="utf-8")
    _, _, direct_root = check_xml_well_formedness(direct_content)
    assert direct_root is not None
    res_direct = detect_sprite_cycles(direct_root)
    assert res_direct.has_cycle is True, "Direct cycle must be detected"
    assert any("sym-direct" in path for path in res_direct.cycle_paths)

    # 3. Indirect mutual recursion cycle control (A -> B -> A)
    indirect_content = (FIXTURES_DIR / "sprite-cycle-indirect.svg").read_text(encoding="utf-8")
    _, _, indirect_root = check_xml_well_formedness(indirect_content)
    assert indirect_root is not None
    res_indirect = detect_sprite_cycles(indirect_root)
    assert res_indirect.has_cycle is True, "Indirect cycle must be detected"
    all_nodes = [node for path in res_indirect.cycle_paths for node in path]
    assert "sym-node-a" in all_nodes
    assert "sym-node-b" in all_nodes


def test_sprite_mutation_controls() -> None:
    """Mutation controls: duplicate IDs, missing href targets, containment ancestor cycle, and MAX_USE_DEPTH."""
    # 1. Duplicate ID detection
    xml_dup = f'<svg xmlns="{SVG_NAMESPACE}"><g id="dup-node" /><circle id="dup-node" r="10" /></svg>'
    _, _, root_dup = check_xml_well_formedness(xml_dup)
    assert root_dup is not None
    res_dup = detect_sprite_cycles(root_dup)
    assert "dup-node" in res_dup.duplicate_ids

    # 2. Missing href target in <use>
    xml_missing = f'<svg xmlns="{SVG_NAMESPACE}"><use href="#nonexistent-id" /></svg>'
    _, _, root_missing = check_xml_well_formedness(xml_missing)
    assert root_missing is not None
    res_missing = detect_sprite_cycles(root_missing)
    assert "nonexistent-id" in res_missing.missing_targets

    # 3. Containment ancestor cycle: element containing a use referencing its ancestor
    xml_containment = (
        f'<svg xmlns="{SVG_NAMESPACE}">'
        f'<g id="ancestor-card"><g><use href="#ancestor-card" /></g></g>'
        f'</svg>'
    )
    _, _, root_cont = check_xml_well_formedness(xml_containment)
    assert root_cont is not None
    res_cont = detect_sprite_cycles(root_cont)
    assert res_cont.has_cycle is True
    assert any("ancestor-card" in path for path in res_cont.cycle_paths)

    # 4. Exceeding MAX_USE_DEPTH raises BoundedLimitExceededError
    chain_elements = []
    for i in range(MAX_USE_DEPTH + 2):
        chain_elements.append(
            f'<g id="node-{i}"><use href="#node-{i + 1}" /></g>'
        )
    chain_elements.append(f'<g id="node-{MAX_USE_DEPTH + 2}" />')
    xml_chain = f'<svg xmlns="{SVG_NAMESPACE}"><defs>{"".join(chain_elements)}</defs></svg>'
    _, _, root_chain = check_xml_well_formedness(xml_chain)
    assert root_chain is not None
    with pytest.raises(BoundedLimitExceededError, match="chain depth .* exceeds limit"):
        detect_sprite_cycles(root_chain)


def test_gradient_clip_and_luminance_mask() -> None:
    """Test composition of linearGradient, clipPath, and luminance mask."""
    content = (FIXTURES_DIR / "gradient-clip-mask.svg").read_text(encoding="utf-8")
    _, _, root = check_xml_well_formedness(content)
    assert root is not None

    clip_mask_info = check_clipping_and_masking(root)
    assert clip_mask_info["is_valid"] is True
    assert "star-clip" in clip_mask_info["defined_clips"]
    assert "star-clip" in clip_mask_info["clip_references"]
    assert "fade-mask" in clip_mask_info["defined_masks"]
    assert clip_mask_info["defined_masks"]["fade-mask"] == "luminance"
    assert len(clip_mask_info["missing_clips"]) == 0
    assert len(clip_mask_info["missing_masks"]) == 0


def test_accessibility_semantics_classification() -> None:
    """Test accessibility classification for meaningful, decorative, and ambiguous SVGs."""
    # Meaningful SVG
    meaningful_content = (FIXTURES_DIR / "text-a11y-meaningful.svg").read_text(encoding="utf-8")
    _, _, m_root = check_xml_well_formedness(meaningful_content)
    assert m_root is not None
    m_info = classify_accessibility(m_root)
    assert m_info["mode"] == "meaningful"
    assert m_info["role"] == "img"
    assert m_info["bounded_label_evidence"] is True
    assert "Quarterly Revenue Growth Chart" in m_info["titles"]
    assert m_info["naming_pattern_present"] is True
    assert len(m_info["dangling_aria_labelledby"]) == 0

    # Decorative SVG
    decorative_content = (FIXTURES_DIR / "text-a11y-decorative.svg").read_text(encoding="utf-8")
    _, _, d_root = check_xml_well_formedness(decorative_content)
    assert d_root is not None
    d_info = classify_accessibility(d_root)
    assert d_info["mode"] == "decorative"
    assert d_info["aria_hidden"] is True
    assert d_info["focusable"] == "false"
    assert len(d_info["titles"]) == 0
    assert d_info["naming_pattern_present"] is True

    # Ambiguous SVG (neither decorative nor meaningful labels)
    image_mode_content = (FIXTURES_DIR / "resource-context-image-mode.svg").read_text(encoding="utf-8")
    _, _, img_root = check_xml_well_formedness(image_mode_content)
    assert img_root is not None
    img_info = classify_accessibility(img_root)
    assert img_info["mode"] == "ambiguous"
    assert img_info["bounded_label_evidence"] is False
    assert img_info["naming_pattern_present"] is False


def test_accessibility_dangling_aria_labelledby_mutation_control() -> None:
    """Mutation control: reject dangling aria-labelledby references and never treat as valid label evidence."""
    # Dangling aria-labelledby referencing nonexistent ID
    dangling_xml = (
        f'<svg xmlns="{SVG_NAMESPACE}" role="img" aria-labelledby="nonexistent-title-id">'
        f'<rect width="100" height="100" />'
        f'</svg>'
    )
    _, _, root = check_xml_well_formedness(dangling_xml)
    assert root is not None
    info = classify_accessibility(root)
    assert "nonexistent-title-id" in info["dangling_aria_labelledby"]
    assert info["bounded_label_evidence"] is False
    assert info["naming_pattern_present"] is False

    # Valid aria-labelledby referencing existing ID
    valid_xml = (
        f'<svg xmlns="{SVG_NAMESPACE}" role="img" aria-labelledby="real-title-id">'
        f'<title id="real-title-id">Valid Label</title>'
        f'<rect width="100" height="100" />'
        f'</svg>'
    )
    _, _, root_v = check_xml_well_formedness(valid_xml)
    assert root_v is not None
    info_v = classify_accessibility(root_v)
    assert len(info_v["dangling_aria_labelledby"]) == 0
    assert info_v["bounded_label_evidence"] is True
    assert info_v["naming_pattern_present"] is True


def test_css_presentation_and_currentcolor() -> None:
    """Test currentColor recognition on strokes and fills for theme adaptation."""
    content = (FIXTURES_DIR / "css-currentcolor.svg").read_text(encoding="utf-8")
    _, _, root = check_xml_well_formedness(content)
    assert root is not None

    paint_info = check_paint_and_currentcolor(root)
    assert paint_info["has_currentcolor"] is True
    assert any("stroke=currentColor" in e for e in paint_info["currentcolor_elements"])


def test_security_active_content_negative_controls() -> None:
    """Test detection and escalation of active scripts, event handlers, foreignObject, and XXE."""
    # 1. Script injection
    script_svg = (FIXTURES_DIR / "unsafe-script-control.svg").read_text(encoding="utf-8")
    violations_script = scan_security_violations(script_svg)
    assert any("<script>" in v for v in violations_script)

    # 2. Inline event handler (onclick, onload)
    handler_svg = (FIXTURES_DIR / "unsafe-event-handler.svg").read_text(encoding="utf-8")
    violations_handler = scan_security_violations(handler_svg)
    assert any("onclick" in v.lower() for v in violations_handler)
    assert any("onload" in v.lower() for v in violations_handler)

    # 3. ForeignObject script
    fo_svg = (FIXTURES_DIR / "unsafe-foreignobject-script.svg").read_text(encoding="utf-8")
    violations_fo = scan_security_violations(fo_svg)
    assert any("foreignObject" in v for v in violations_fo)

    # 4. XXE DOCTYPE SYSTEM
    xxe_svg = (FIXTURES_DIR / "unsafe-xxe-doctype.svg").read_text(encoding="utf-8")
    violations_xxe = scan_security_violations(xxe_svg)
    assert any("DOCTYPE" in v for v in violations_xxe)


def test_xml_preparse_dtd_and_root_namespace_mutation_controls() -> None:
    """Mutation controls: refuse all DTD/entities pre-parse, require lowercase svg and exact namespace."""
    # 1. Any DOCTYPE refused pre-parse (even without SYSTEM)
    doc_with_dtd = f'<!DOCTYPE svg><svg xmlns="{SVG_NAMESPACE}"><rect width="10" height="10" /></svg>'
    is_ok, err, _ = check_xml_well_formedness(doc_with_dtd)
    assert is_ok is False
    assert "Prohibited DOCTYPE" in str(err)

    # 2. ENTITY declaration refused pre-parse
    doc_with_entity = f'<!ENTITY foo "bar"><svg xmlns="{SVG_NAMESPACE}"><rect width="10" height="10" /></svg>'
    is_ok, err, _ = check_xml_well_formedness(doc_with_entity)
    assert is_ok is False
    assert "Prohibited DOCTYPE or ENTITY" in str(err)

    # 3. Uppercase root <SVG> rejected
    uppercase_svg = f'<SVG xmlns="{SVG_NAMESPACE}"><rect width="10" height="10" /></SVG>'
    is_ok, err, _ = check_xml_well_formedness(uppercase_svg)
    assert is_ok is False
    assert "lowercase 'svg'" in str(err)

    # 4. Missing xmlns namespace declaration rejected
    no_ns_svg = '<svg viewBox="0 0 10 10"><rect width="10" height="10" /></svg>'
    is_ok, err, _ = check_xml_well_formedness(no_ns_svg)
    assert is_ok is False
    assert "exact SVG namespace" in str(err)

    # 5. Wrong XML namespace rejected
    wrong_ns_svg = '<svg xmlns="http://example.com/other"><rect width="10" height="10" /></svg>'
    is_ok, err, _ = check_xml_well_formedness(wrong_ns_svg)
    assert is_ok is False
    assert "exact SVG namespace" in str(err)


def test_resource_context_image_mode() -> None:
    """Test self-contained image resource context without external references or scripts."""
    content = (FIXTURES_DIR / "resource-context-image-mode.svg").read_text(encoding="utf-8")
    is_ok, _, root = check_xml_well_formedness(content)
    assert is_ok and root is not None

    violations = scan_security_violations(content)
    assert len(violations) == 0, "Image mode SVG must have zero security violations"

    # Verify no external hrefs
    for elem in root.iter():
        href = elem.get("href") or elem.get("{http://www.w3.org/1999/xlink}href")
        if href:
            assert href.startswith("#"), f"Image mode forbids external reference: {href}"


def test_malformed_xml_negative_control() -> None:
    """Test XML syntax parsing rejection on malformed unclosed tags."""
    content = (FIXTURES_DIR / "malformed-unsupported-tags.svg").read_text(encoding="utf-8")
    is_ok, err, root = check_xml_well_formedness(content)
    assert is_ok is False
    assert root is None
    assert "XML parse error" in str(err) or "unclosed" in str(err).lower()


def test_destructive_vs_safe_optimization_controls() -> None:
    """Test optimization evaluation distinguishing safe cleanup from destructive defects and precision loss."""
    orig_content = (FIXTURES_DIR / "text-a11y-meaningful.svg").read_text(encoding="utf-8")
    destructive_content = (FIXTURES_DIR / "destructive-optimization-control.svg").read_text(encoding="utf-8")
    safe_content = (FIXTURES_DIR / "safe-optimized.svg").read_text(encoding="utf-8")
    unopt_source = (FIXTURES_DIR / "safe-unoptimized-source.svg").read_text(encoding="utf-8")

    # 1. Comparing original with destructive optimization
    dest_eval = evaluate_optimization_safety(orig_content, destructive_content)
    assert dest_eval["preserved_checked_structure"] is False, "Destructive optimization must fail"
    defects = dest_eval["defects"]
    assert any("viewBox" in d for d in defects), "Must catch stripped viewBox"
    assert any("title" in d.lower() or "a11y" in d.lower() for d in defects), "Must catch stripped title/a11y"
    assert any("paint ID references" in d for d in defects), "Must catch broken paint ID reference"

    # 2. Safe optimization whitespace/comment normalization positive control
    safe_eval = evaluate_optimization_safety(unopt_source, safe_content)
    assert safe_eval["preserved_checked_structure"] is True, "Safe comment/whitespace stripping must pass"
    assert len(safe_eval["defects"]) == 0
    assert safe_eval["reduction_bytes"] > 0, "Optimization must successfully reduce byte size"

    # 3. Mutation control: coordinate precision loss failure
    precision_loss_svg = safe_content.replace('rx="8"', 'rx="7.5"')
    prec_eval = evaluate_optimization_safety(safe_content, precision_loss_svg)
    assert prec_eval["preserved_checked_structure"] is False, "Coordinate precision change must be flagged"
    assert any("checked XML structure changed" in d for d in prec_eval["defects"])


def test_explicit_bounded_limits_enforcement() -> None:
    """Test rejection of oversized payloads, deep DOM nesting, and element floods."""
    # 1. Oversized byte payload (> 512 KB)
    huge_bytes = f'<svg xmlns="{SVG_NAMESPACE}">' + (" " * (MAX_SVG_BYTES + 1024)) + "</svg>"
    with pytest.raises(BoundedLimitExceededError, match="exceeds limit"):
        validate_bounded_input(huge_bytes)

    # 2. DOM depth limit (> 32)
    deep_xml = f'<svg xmlns="{SVG_NAMESPACE}">' + ("<g>" * (MAX_DOM_DEPTH + 5)) + ("</g>" * (MAX_DOM_DEPTH + 5)) + "</svg>"
    with pytest.raises(BoundedLimitExceededError, match="DOM depth .* exceeds limit"):
        check_xml_well_formedness(deep_xml)

    # 3. Element count limit (> 5000)
    flood_xml = f'<svg xmlns="{SVG_NAMESPACE}">' + ("<circle r='1'/>" * (MAX_ELEMENT_COUNT + 100)) + "</svg>"
    with pytest.raises(BoundedLimitExceededError, match="element count .* exceeds limit"):
        check_xml_well_formedness(flood_xml)


def test_proof_disclaimer_and_no_rendering_claims() -> None:
    """Verify that contract explicitly disclaims visual rendering, rasterization, and a11y tree proof."""
    assert "visual rendering proof" in PROOF_DISCLAIMER
    assert "accessibility-tree computation proof" in PROOF_DISCLAIMER
    assert "pixel rasterization accuracy" in PROOF_DISCLAIMER
    assert "fixture-only adverse signal" in LEXICAL_SCAN_DISCLAIMER
    assert "NO general equivalence claim" in OPTIMIZATION_DISCLAIMER


def test_all_scenarios_evaluation_coherence() -> None:
    """Evaluate every scenario in scenarios.json, reporting navigation-only handoffs and asserting all categories."""
    fixture = load_scenario_fixture(SCENARIOS_PATH)
    rows = fixture["rows"]

    tested_categories = set()
    navigation_only_ids = []
    semantic_ids = []

    for row in rows:
        r_id = row["id"]
        category = row["category"]
        tested_categories.add(category)

        res = evaluate_scenario_row(row, FIXTURES_DIR)
        assert res["status"] == "passed", f"Scenario {r_id} failed evaluation: {res}"

        if res["mode"] == "navigation-only":
            navigation_only_ids.append(r_id)
            assert res["reporting"] == "navigation-only"
        else:
            semantic_ids.append(r_id)
            assert res["reporting"] == "semantic-evaluation"

    # Verify no category was silently skipped: all 14 frozen categories must be tested
    assert tested_categories == set(CATEGORIES), f"Categories omitted from testing: {set(CATEGORIES) - tested_categories}"

    # Verify navigation-only reporting count and semantic count
    assert navigation_only_ids == [f"APG122-SVG-{n:03d}" for n in (18, 19, 20, 21, 23, 24)]
    assert len(semantic_ids) == 18, "Only the 18 bounded semantic rows may claim evaluation"


@pytest.mark.parametrize("before,after", [
    ('aria-labelledby="safe-opt-title"', 'aria-labelledby="missing"'),
    ('stop-color="#0284c7"', 'stop-color="#ffffff"'),
    ('id="safe-grad"', 'id="renamed-grad"'),
    ('role="img"', 'role="presentation"'),
    ('cx="50"', 'cx="50.00000000000000000001"'),
])
def test_optimization_rejects_reference_paint_role_and_precision_changes(before, after):
    content = (FIXTURES_DIR / "safe-optimized.svg").read_text()
    assert before in content
    assert not evaluate_optimization_safety(content, content.replace(before, after))["preserved_checked_structure"]


def test_text_whitespace_and_child_order_are_not_optimization_noise():
    content = '<svg xmlns="http://www.w3.org/2000/svg"><text>A <tspan>B</tspan> C</text></svg>'
    assert not evaluate_optimization_safety(content, content.replace('A ', 'A'))["preserved_checked_structure"]
    content = '<svg xmlns="http://www.w3.org/2000/svg"><rect/><circle/></svg>'
    assert not evaluate_optimization_safety(content, content.replace('<rect/><circle/>', '<circle/><rect/>'))["preserved_checked_structure"]


def test_scenario_response_cannot_skip_its_predicate():
    from apg122_svg_contract import SvgContractError, evaluate_scenario_row
    row = dict(load_scenario_fixture(SCENARIOS_PATH)["rows"][0])
    row["response"] = "bounded-local-decision"
    with pytest.raises(SvgContractError, match="frozen outcome"):
        evaluate_scenario_row(row, FIXTURES_DIR)
