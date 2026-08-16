#!/usr/bin/env python3
"""Schema, mutation, and exact-compiler tests for the APG75 TypeScript fixture."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src/test/support"))

from apg_typescript_fixture_contract import (  # noqa: E402
    FixtureError,
    load_manifest,
    run_compiler,
    validate_compiler_version,
    validate_fixture_readme,
    validate_fixture_projection,
    validate_manifest,
)
from apg_typescript_candidate_contract import load_scenario_fixture  # noqa: E402


FIXTURE_ROOT = ROOT / "src/test/fixtures/apg74-typescript-intended-state"
MANIFEST = load_manifest(FIXTURE_ROOT / "fixture-manifest.json")
SCENARIOS = load_scenario_fixture(
    ROOT / "src/test/fixtures/apg75-typescript-language-profile-scenarios.json"
)


def _case(case_id: str) -> dict[str, object]:
    return next(case for case in MANIFEST["cases"] if case["id"] == case_id)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_manifest_is_complete_and_paths_are_closed() -> None:
    assert len(MANIFEST["cases"]) == 14
    assert _case("APG74-FX-006")["typescript_selection"] == "embedded-route"
    assert _case("APG74-FX-008")["typescript_selection"] == "embedded-route"
    assert _case("APG74-FX-010")["compiler_roles"] == []
    assert _case("APG74-FX-013")["role_identity_state"] == "unresolved"
    assert _case("APG74-FX-014")["role_identity_state"] == "unresolved"
    validate_fixture_projection(MANIFEST, SCENARIOS)


def test_manifest_records_historical_authorship_and_current_lifecycle() -> None:
    assert MANIFEST["fixture"] == "apg74-typescript-intended-state"
    assert MANIFEST["authored_phase"] == "APG74"
    assert MANIFEST["current_phase"] == "APG75A"
    assert MANIFEST["lifecycle"] == "provisionally-integrated"
    assert MANIFEST["authority"] == (
        "ADR 0042 Accepted; ADR 0043 Accepted with amendment"
    )
    assert "phase" not in MANIFEST


def test_fixture_readme_lifecycle_mutations_fail() -> None:
    readme = (FIXTURE_ROOT / "README.md").read_text(encoding="utf-8")
    validate_fixture_readme(readme)
    for mutated in (
        readme.replace("after APG75A", "after APG75"),
        readme.replace("provisionally integrated", "NOT INTEGRATED"),
        readme + "\nThis fixture is BRANCH-ONLY.\n",
    ):
        with pytest.raises(FixtureError, match="lifecycle"):
            validate_fixture_readme(mutated)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("current_phase", "APG75"),
        ("lifecycle", "branch-only"),
        ("authority", "ADR 0043 Proposed; APG75 round-1 corrected state"),
    ],
)
def test_manifest_lifecycle_mutations_fail(field: str, value: str) -> None:
    mutated = deepcopy(MANIFEST)
    mutated[field] = value
    with pytest.raises(FixtureError, match="lifecycle|authority"):
        validate_manifest(mutated, FIXTURE_ROOT)


def test_exact_primary_compiler_and_fixture_smoke_pass() -> None:
    assert validate_compiler_version(FIXTURE_ROOT) == "Version 7.0.2"
    run_compiler(FIXTURE_ROOT, "-p", "tsconfig.json")


def test_ordinary_checked_javascript_and_tsx_have_contrasting_controls(
    tmp_path: Path,
) -> None:
    ordinary = _write(tmp_path / "ordinary.ts", "const count: number = 1; void count;\n")
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(ordinary))
    ordinary_bad = _write(
        tmp_path / "ordinary-negative.ts", "const count: number = 'one'; void count;\n"
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", str(ordinary_bad), expected_exit=1
    )

    checked = _write(
        tmp_path / "checked.js",
        "/** @returns {number} */\nexport function count() { return 1; }\n",
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", "--allowJs", "--checkJs", str(checked)
    )
    checked_bad = _write(
        tmp_path / "checked-negative.js",
        "/** @returns {number} */\nexport function count() { return 'one'; }\n",
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", "--allowJs", "--checkJs",
        str(checked_bad), expected_exit=1,
    )

    host = _write(
        tmp_path / "jsx-host.d.ts",
        "declare namespace JSX { interface Element {} interface IntrinsicElements { badge: { label: string } } }\n",
    )
    tsx = _write(tmp_path / "view.tsx", "export const view = <badge label='ok' />;\n")
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", "--jsx", "preserve", str(host), str(tsx)
    )
    tsx_bad = _write(
        tmp_path / "view-negative.tsx", "export const view = <badge label={false} />;\n"
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", "--jsx", "preserve", str(host),
        str(tsx_bad), expected_exit=1,
    )


def test_declaration_emit_preserves_mts_and_cts_suffixes(tmp_path: Path) -> None:
    ts = _write(tmp_path / "plain.ts", "export const plain = 1;\n")
    mts = _write(tmp_path / "module.mts", "export const esm = 1;\n")
    cts = _write(tmp_path / "module.cts", "export = { cjs: 1 };\n")
    output = tmp_path / "declarations"
    run_compiler(
        FIXTURE_ROOT,
        "--declaration", "--emitDeclarationOnly", "--module", "nodenext",
        "--moduleResolution", "nodenext", "--outDir", str(output), str(ts), str(mts), str(cts),
    )
    assert (output / "plain.d.ts").is_file()
    assert (output / "module.d.mts").is_file()
    assert (output / "module.d.cts").is_file()
    assert not list(output.glob("*.js"))


def test_mts_and_cts_source_kinds_cannot_be_collapsed(tmp_path: Path) -> None:
    bad_cts = _write(tmp_path / "bad.cts", "export const value = 1;\n")
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--module", "nodenext", "--moduleResolution", "nodenext",
        "--verbatimModuleSyntax", str(bad_cts), expected_exit=1,
    )
    bad_mts = _write(tmp_path / "bad.mts", "const value = 1; export = value;\n")
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--module", "nodenext", "--moduleResolution", "nodenext",
        "--verbatimModuleSyntax", str(bad_mts), expected_exit=1,
    )


@pytest.mark.parametrize("case_id", ["APG74-FX-007", "APG74-FX-010", "APG74-FX-013", "APG74-FX-014"])
def test_non_known_identity_cannot_bind_a_concrete_role(case_id: str) -> None:
    mutated = deepcopy(MANIFEST)
    case = next(case for case in mutated["cases"] if case["id"] == case_id)
    case["compiler_roles"] = deepcopy(_case("APG74-FX-001")["compiler_roles"])
    with pytest.raises(FixtureError, match="invents a role"):
        validate_manifest(mutated, FIXTURE_ROOT)


def test_package_surface_cannot_invent_editor_or_api_role() -> None:
    mutated = deepcopy(MANIFEST)
    case = next(case for case in mutated["cases"] if case["id"] == "APG74-FX-009")
    role = deepcopy(case["compiler_roles"][0])
    role["role"] = "editor-language-service"
    case["compiler_roles"].append(role)
    with pytest.raises(FixtureError, match="must not infer an editor or API role"):
        validate_manifest(mutated, FIXTURE_ROOT)


def test_fixture_option_facts_require_values_and_evidence_sets_are_disjoint() -> None:
    valueless = deepcopy(MANIFEST)
    valueless["cases"][0]["option_facts"] = ["strict"]
    with pytest.raises(FixtureError, match="option name without a value"):
        validate_manifest(valueless, FIXTURE_ROOT)

    overlapping = deepcopy(MANIFEST)
    overlapping["cases"][0]["required_evidence"] = [
        overlapping["cases"][0]["present_evidence"][0]
    ]
    with pytest.raises(FixtureError, match="copies present evidence"):
        validate_manifest(overlapping, FIXTURE_ROOT)


def test_product_state_vocabulary_and_retirement_are_exact() -> None:
    temporary = deepcopy(MANIFEST)
    role = temporary["cases"][0]["compiler_roles"][0]
    role["product_state"] = "temporary"
    role["retirement_condition"] = "remove after the host selects TypeScript 7"
    validate_manifest(temporary, FIXTURE_ROOT)

    stale_alias = deepcopy(temporary)
    stale_alias["cases"][0]["compiler_roles"][0]["product_state"] = "temporary-compatibility"
    with pytest.raises(FixtureError, match="unknown product state"):
        validate_manifest(stale_alias, FIXTURE_ROOT)

    no_retirement = deepcopy(temporary)
    no_retirement["cases"][0]["compiler_roles"][0]["retirement_condition"] = "not-applicable"
    with pytest.raises(FixtureError, match="lacks a retirement condition"):
        validate_manifest(no_retirement, FIXTURE_ROOT)

    permanent_retirement = deepcopy(MANIFEST)
    permanent_retirement["cases"][0]["compiler_roles"][0][
        "retirement_condition"
    ] = "later"
    with pytest.raises(FixtureError, match="permanent role has a retirement condition"):
        validate_manifest(permanent_retirement, FIXTURE_ROOT)


@pytest.mark.parametrize(
    "case_id",
    [f"APG74-FX-{index:03d}" for index in range(1, 15)],
)
def test_scenario_projection_rejects_erased_consequences(case_id: str) -> None:
    mutated = deepcopy(SCENARIOS)
    row = next(row for row in mutated["rows"] if row["id"] == case_id)
    row["present_evidence"] = ["unrelated token"]
    row["required_evidence"] = ["unrelated requirement"]
    row["owned_conclusion"] = ""
    row["nonowned_conclusion"] = ""
    row["rollback_or_provenance"] = "x"
    with pytest.raises(FixtureError, match="scenario projection"):
        validate_fixture_projection(MANIFEST, mutated)


def test_fixture_rejects_path_drift_and_generated_output(tmp_path: Path) -> None:
    drifted = deepcopy(MANIFEST)
    drifted["cases"][0]["paths"][0] = "../outside.ts"
    with pytest.raises(FixtureError, match="path identity changed"):
        validate_manifest(drifted, FIXTURE_ROOT)

    substituted = deepcopy(MANIFEST)
    substituted["cases"][0]["paths"][0] = "src/modules/loader.mts"
    with pytest.raises(FixtureError, match="path identity changed"):
        validate_manifest(substituted, FIXTURE_ROOT)

    copied = tmp_path / "fixture"
    shutil.copytree(FIXTURE_ROOT, copied)
    generated = copied / "out"
    generated.mkdir()
    (generated / "generated.js").write_text("export {};\n", encoding="utf-8")
    raw = json.loads((copied / "fixture-manifest.json").read_text(encoding="utf-8"))
    with pytest.raises(FixtureError, match="fixture file set"):
        validate_manifest(raw, copied)

    shutil.rmtree(generated)
    generated = copied / "generated"
    generated.mkdir()
    (generated / "leaked.d.ts").write_text("export {};\n", encoding="utf-8")
    with pytest.raises(FixtureError, match="fixture file set"):
        validate_manifest(raw, copied)


def test_option_state_unknown_source_embodies_indexed_access_consequence() -> None:
    source = (FIXTURE_ROOT / "src/unbound/option-state-unknown.ts").read_text(encoding="utf-8")
    assert "values[0]" in source
    assert "noUncheckedIndexedAccess" in source


def test_exact_optional_and_indexed_access_options_change_results(tmp_path: Path) -> None:
    optional = _write(
        tmp_path / "optional.ts",
        "interface Box { value?: string }\nconst bad: Box = { value: undefined };\n",
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", "--exactOptionalPropertyTypes", str(optional),
        expected_exit=1,
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", "--exactOptionalPropertyTypes", "false", str(optional),
    )

    indexed = _write(
        tmp_path / "indexed.ts",
        "export function first(xs: readonly string[]): string { return xs[0]; }\n",
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", "--noUncheckedIndexedAccess", str(indexed),
        expected_exit=1,
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", "--noUncheckedIndexedAccess", "false", str(indexed),
    )


def test_overload_order_has_no_universal_first_match_shortcut(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "overloads.ts",
        """function choose(value: string): 'general';
function choose(value: 'x'): 'special';
function choose(_value: string): 'general' | 'special' { return 'general'; }
const result: 'special' = choose('x');
type Last = ReturnType<typeof choose>;
const last: Last = 'special';
""",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(source))
    generic_first = _write(
        tmp_path / "overload-generic.ts",
        """function pick<T>(value: T): 'generic';
function pick(value: string): 'string';
function pick(_value: unknown): 'generic' | 'string' { return 'generic'; }
const result: 'generic' = pick('x'); void result;
""",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(generic_first))
    implementation_hidden = _write(
        tmp_path / "overload-hidden.ts",
        """function visible(value: string): string;
function visible(value: string | number): string { return String(value); }
visible(1);
""",
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", str(implementation_hidden), expected_exit=1
    )


def test_generic_inference_and_strict_function_variance_have_controls(tmp_path: Path) -> None:
    positive = _write(
        tmp_path / "generic-positive.ts",
        """function first<T>(values: readonly T[]): T | undefined { return values[0]; }
const inferred: number | undefined = first([1, 2]);
type Handler<T> = (value: T) => void;
const wide: Handler<string | number> = () => undefined;
const narrowEnough: Handler<string> = wide;
void inferred; void narrowEnough;
""",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(positive))
    negative = _write(
        tmp_path / "variance-negative.ts",
        "type Handler<T> = (value: T) => void;\n"
        "const narrow: Handler<string> = () => undefined;\n"
        "const unsafe: Handler<string | number> = narrow; void unsafe;\n",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(negative), expected_exit=1)
    generic_negative = _write(
        tmp_path / "generic-negative.ts",
        "function first<T>(values: readonly T[]): T | undefined { return values[0]; }\n"
        "const inferred: string | undefined = first([1, 2]); void inferred;\n",
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", str(generic_negative), expected_exit=1
    )
    method_near_miss = _write(
        tmp_path / "method-near-miss.ts",
        "interface Wide { handle(value: string | number): void }\n"
        "interface Narrow { handle(value: string): void }\n"
        "declare const narrow: Narrow; const accepted: Wide = narrow; void accepted;\n",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(method_near_miss))


def test_any_unknown_and_never_have_distinct_consequences(tmp_path: Path) -> None:
    positive = _write(
        tmp_path / "top-bottom.ts",
        """declare const unchecked: any;
unchecked.missing();
declare const guarded: unknown;
if (typeof guarded === 'string') guarded.toUpperCase();
function impossible(value: never): never { return value; }
void impossible;
""",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(positive))
    negative = _write(
        tmp_path / "unknown-negative.ts",
        "declare const guarded: unknown; guarded.missing();\n",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(negative), expected_exit=1)
    exhaustive = _write(
        tmp_path / "exhaustive.ts",
        """type Action = { kind: 'start' } | { kind: 'stop' };
function code(event: Action): number {
  switch (event.kind) { case 'start': return 1; case 'stop': return 2; }
  const unreachable: never = event; return unreachable;
}
void code;
""",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(exhaustive))
    nonexhaustive = _write(
        tmp_path / "nonexhaustive.ts",
        """type Action = { kind: 'start' } | { kind: 'stop' };
function code(event: Action): number {
  switch (event.kind) { case 'start': return 1; }
  const unreachable: never = event; return unreachable;
}
void code;
""",
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", str(nonexhaustive), expected_exit=1
    )


def test_static_assertion_emit_contains_no_runtime_shape_validation(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "runtime-boundary.ts",
        """interface Report { target: string; durationMs: number }
export function parse(raw: string): Report { return JSON.parse(raw) as Report; }
""",
    )
    output = tmp_path / "runtime-output"
    run_compiler(
        FIXTURE_ROOT, "--strict", "--target", "es2022", "--module", "esnext",
        "--outDir", str(output), str(source),
    )
    emitted = (output / "runtime-boundary.js").read_text(encoding="utf-8")
    assert "JSON.parse(raw)" in emitted
    assert "durationMs" not in emitted
    assert "Report" not in emitted


def test_satisfies_assertions_and_double_assertion_stay_distinct(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "assertions.ts",
        """const checked = { mode: 'safe' } satisfies { mode: 'safe' | 'fast' };
const literal: 'safe' = checked.mode;
const bypass = ({ a: 1 } as unknown) as { b: string };
void literal; void bypass;
""",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(source))

    impossible = _write(
        tmp_path / "impossible.ts",
        "const invalid = ({ a: 1 }) as { b: string }; void invalid;\n",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(impossible), expected_exit=1)
    contextual = _write(
        tmp_path / "satisfies-context.ts",
        "const value = { mode: 'safe' } satisfies { mode: string };\n"
        "const literal: 'safe' = value.mode; void literal;\n",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(contextual), expected_exit=1)
    excess = _write(
        tmp_path / "satisfies-excess.ts",
        "const value = { mode: 'safe', extra: true } satisfies { mode: 'safe' }; void value;\n",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(excess), expected_exit=1)


def test_const_enum_emit_and_isolated_modules_are_distinct(tmp_path: Path) -> None:
    source = _write(
        tmp_path / "enum.ts",
        "const enum Mode { Read = 1 }\nexport const selected = Mode.Read;\n",
    )
    erased = tmp_path / "erased"
    run_compiler(
        FIXTURE_ROOT, "--target", "es2022", "--module", "esnext", "--outDir", str(erased), str(source),
    )
    erased_text = (erased / "enum.js").read_text(encoding="utf-8")
    assert "Mode =" not in erased_text

    preserved = tmp_path / "preserved"
    run_compiler(
        FIXTURE_ROOT, "--target", "es2022", "--module", "esnext", "--preserveConstEnums",
        "--outDir", str(preserved), str(source),
    )
    preserved_text = (preserved / "enum.js").read_text(encoding="utf-8")
    assert "Mode =" in preserved_text

    isolated = tmp_path / "isolated"
    run_compiler(
        FIXTURE_ROOT, "--target", "es2022", "--module", "esnext", "--isolatedModules",
        "--outDir", str(isolated), str(source),
    )
    isolated_text = (isolated / "enum.js").read_text(encoding="utf-8")
    assert "Mode.Read" in isolated_text
    ambient = _write(tmp_path / "ambient.d.ts", "declare const enum Remote { Value = 1 }\n")
    consumer = _write(tmp_path / "consumer.ts", "export const value = Remote.Value;\n")
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", str(ambient), str(consumer))
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", "--isolatedModules", str(ambient),
        str(consumer), expected_exit=1,
    )


def test_standard_decorator_regime_is_not_legacy_decorator_proof(tmp_path: Path) -> None:
    standard = _write(
        tmp_path / "decorator.ts",
        """function logged(value: (name: string) => string, _context: ClassMethodDecoratorContext) {
  return function (this: unknown, name: string): string { return value.call(this, name); };
}
class Greeter { @logged greet(name: string): string { return `hi ${name}`; } }
void Greeter;
""",
    )
    run_compiler(FIXTURE_ROOT, "--noEmit", "--strict", "--target", "es2022", str(standard))
    invalid = _write(
        tmp_path / "decorator-invalid.ts",
        """function wrong(_value: unknown, _context: ClassMethodDecoratorContext): number { return 1; }
class Greeter { @wrong greet(): string { return 'hi'; } }
""",
    )
    run_compiler(
        FIXTURE_ROOT, "--noEmit", "--strict", "--target", "es2022", str(invalid),
        expected_exit=1,
    )
