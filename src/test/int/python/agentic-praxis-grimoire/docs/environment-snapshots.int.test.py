#!/usr/bin/env python3
"""Data-only contracts for the APG98 bounded ``.flakes`` parity fixtures."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
FIXTURE = ROOT / "src/test/fixtures/apg98-environment"
PROFILE = FIXTURE / "profile-all-validators.json"
EXPECTED_CAPTURE = FIXTURE / "expected-capture.json"
SHELL_CASES = FIXTURE / "shell-and-hook-cases.json"
PROVENANCE = FIXTURE / "provenance.json"

VALIDATORS = {
    "bool",
    "command",
    "host",
    "integer",
    "path",
    "path_list",
    "port",
    "raw_safe",
    "token",
    "token_list",
    "uri",
    "uri_or_path",
}
AUTHORING_PATHS = {
    "nix-darwin/libexec/codex-env/allowlist.py",
    "nix-darwin/libexec/codex-env/snapshot.py",
    "nix-darwin/libexec/codex-env/run.py",
    "nix-darwin/shell/sh_config/common/010_env_snapshot",
    "nix-darwin/config/codex-env/project-env-allowlist.tsv",
    "nix-darwin/config/codex-env/codex-sync-allowlist.tsv",
}


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f"duplicate fixture key: {key}")
        result[key] = value
    return result


def _json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)


def _validator_cases() -> dict[str, dict[str, list[object]]]:
    """Load the companion matrix in either its profile or standalone form."""

    profile = _json(PROFILE)
    assert isinstance(profile, dict)
    embedded = profile.get("validator_cases")
    candidates = sorted(FIXTURE.glob("*validator*.json"))
    if embedded is not None:
        value = embedded
    else:
        standalone = [
            _json(path)
            for path in candidates
            if path.name != PROFILE.name
        ]
        assert len(standalone) == 1, "one validator accepted/rejected matrix is required"
        value = standalone[0]
    if isinstance(value, dict) and "validator_cases" in value:
        value = value["validator_cases"]
    if isinstance(value, list):
        value = {row["validator"]: row for row in value if isinstance(row, dict)}
    assert isinstance(value, dict)
    assert set(value) == VALIDATORS
    normalized: dict[str, dict[str, list[object]]] = {}
    for validator, row in value.items():
        assert isinstance(row, dict)
        assert set(row) == {"accepted", "rejected"}
        assert isinstance(row["accepted"], list) and row["accepted"]
        assert isinstance(row["rejected"], list) and row["rejected"]
        normalized[validator] = row  # type: ignore[assignment]
    return normalized


def test_fixture_source_binding_is_exact_and_read_only() -> None:
    provenance = _json(PROVENANCE)
    assert isinstance(provenance, dict)
    assert provenance["fixture_id"] == "apg98-environment"
    assert provenance["fixture_status"] == "bounded-apg-owned-parity-evidence"
    authority = provenance["source_authority"]
    assert isinstance(authority, dict)
    assert authority["repository"] == ".flakes"
    assert authority["branch"] == "main"
    assert authority["read_only"] is True
    assert authority["exact_binding"] == (
        "publication-excluded APG98 source-binding evidence"
    )
    assert authority["execution_source_state"] == (
        "fresh current-main read-only characterization"
    )
    assert authority["authoring_source_state"] == (
        "phase-authoring baseline retained as evidence"
    )

    files = authority["files"]
    assert isinstance(files, list)
    assert {row["path"] for row in files} == AUTHORING_PATHS
    for row in files:
        assert set(row) <= {"path", "role", "binding"}
        assert row["role"]
        if "binding" in row:
            assert row["binding"] == (
                "publication-excluded APG98 source-binding evidence"
            )

    provenance_text = PROVENANCE.read_text(encoding="utf-8")
    assert not re.search(r"[0-9a-f]{40}", provenance_text)

    ownership = provenance["ownership"]
    assert ownership == {
        "owner": "APG98",
        "expression": "independently authored fixture data and characterization",
        "not_an_oracle": True,
        "not_a_product_default": True,
        "no_live_values_or_paths": True,
        "no_cutover": True,
    }


def test_profile_covers_all_validators_and_each_has_both_outcome_classes() -> None:
    profile = _json(PROFILE)
    assert isinstance(profile, dict)
    assert profile["schema_version"] == "apg.environment-profile/v1"
    entries = profile["entries"]
    assert isinstance(entries, list)
    assert {entry["validator"] for entry in entries} == VALIDATORS
    assert len({entry["name"] for entry in entries}) == len(entries)
    cases = _validator_cases()
    assert set(cases) == VALIDATORS
    for validator, row in cases.items():
        with_case_values = [*row["accepted"], *row["rejected"]]
        assert all(isinstance(value, str) for value in with_case_values), validator

    invalid = _json(FIXTURE / "profile-invalid-cases.json")
    assert isinstance(invalid, list)
    assert {
        "profile-unknown-field",
        "profile-duplicate-json-key",
        "duplicate-name",
        "wildcard-name",
        "malformed-name",
        "unknown-validator",
        "non-positive-limit",
        "invalid-default",
        "control-default",
        "denied-sentinel",
        "sensitive-name",
        "capability-path-exception",
    } <= {row["case_id"] for row in invalid}


def test_capture_fixture_freezes_order_empty_missing_and_fingerprint_inputs() -> None:
    capture = _json(FIXTURE / "capture-environment.json")
    expected = _json(EXPECTED_CAPTURE)
    assert isinstance(capture, dict) and isinstance(expected, dict)
    assert capture["profile_id"] == expected["profile_id"] == "fixture-all-validators"
    environment = capture["environment"]
    assert isinstance(environment, dict)
    assert capture["intentionally_omitted"] == ["APG98_OPTIONAL", "SSH_AUTH_SOCK"]
    assert expected["entries_in_canonical_name_order"] == sorted(
        expected["entries_in_canonical_name_order"]
    )
    assert expected["missing_optional"] == capture["intentionally_omitted"]
    assert expected["excluded_names"] == ["APG98_UNLISTED"]
    assert expected["entry_source"] == "capture"
    assert set(expected["fingerprint_excludes"]) == {
        "capture_timestamp",
        "storage_path",
        "diagnostic_prose",
    }
    assert "APG98_UNLISTED" in environment
    assert "APG98_OPTIONAL" not in environment


def test_shell_snapshot_fixture_characterizes_old_ordering_modes_metadata_and_modes() -> None:
    cases = _json(SHELL_CASES)
    assert isinstance(cases, dict)
    source = cases["source_behavior"]
    assert isinstance(source, dict)
    assert source["shell_detection_precedence"] == [
        "ZSH_VERSION",
        "BASH_VERSION",
        "SHELL-basename",
    ]
    assert set(source["recognized_shells"]) == {"bash", "zsh"}
    modes = source["mode_defaults"]
    assert set(modes) == {"sync", "env-file"}
    assert modes["sync"] == {
        "allowlist": "codex-sync-allowlist.tsv",
        "context": "global",
        "metadata": True,
        "output": "<home>/.codex/runtime/shell-env/latest.<shell>.env",
    }
    assert modes["env-file"]["allowlist"] == "project-env-allowlist.tsv"
    snapshot = source["snapshot"]
    assert snapshot["missing_empty"] == "required-fails-optional-skips"
    assert snapshot["same_content"] == "no-rewrite"
    assert snapshot["directory_mode"] == "0700"
    assert snapshot["file_mode"] == "0600"
    assert set(snapshot["metadata_fields"]) == {
        "allowlist_path",
        "content_sha256",
        "context",
        "entries",
        "generated_at",
        "mode",
        "output_path",
        "rejected",
        "shell",
        "skipped_missing",
    }


def test_allowlist_tsv_fixtures_preserve_old_snapshot_row_order_and_schema() -> None:
    expected_first_rows = {
        "flakes-project-rows.tsv": [
            "PATH",
            "JAVA_HOME",
            "SPRING_PROFILES_ACTIVE",
            "SPRING_APPLICATION_JSON",
        ],
        "flakes-sync-rows.tsv": ["PATH", "MANPATH", "INFOPATH", "SHELL"],
    }
    for filename, first_rows in expected_first_rows.items():
        with (FIXTURE / filename).open(encoding="utf-8", newline="") as stream:
            rows = list(csv.reader(stream, delimiter="\t"))
        assert rows[0] == [
            "name",
            "validator",
            "max_bytes",
            "required",
            "default",
            "description",
        ]
        names = [row[0] for row in rows[1:]]
        assert names[: len(first_rows)] == first_rows
        assert len(names) == len(set(names))
        assert all(len(row) == 6 for row in rows[1:])


def test_parser_safe_and_invalid_fixtures_cover_overlay_and_exact_argv_contract() -> None:
    safe = (FIXTURE / "parser-safe.env").read_text(encoding="utf-8").splitlines()
    assert safe[0].startswith("#")
    assert any(line.startswith("export APG98_PATH=") for line in safe)
    assert any(line.startswith("APG98_COMMAND=") for line in safe)
    token_lines = [line for line in safe if line.startswith("APG98_LEXEM=")]
    assert len(token_lines) == 2
    assert token_lines[-1].endswith("last-value")
    assert "APG98_EMPTY=" in safe
    assert "'" in next(line for line in safe if line.startswith("APG98_COMMAND="))
    assert '"' in next(line for line in safe if line.startswith("APG98_RAW_SAFE="))

    invalid = _json(FIXTURE / "parser-invalid-cases.json")
    assert isinstance(invalid, list)
    expected = {row["expected"] for row in invalid}
    assert {
        "reject-unsupported-line",
        "reject-invalid-name",
        "reject-nul",
        "reject-cr",
        "last-assignment-wins",
    } <= expected
    assert any(row.get("text_escape") == r"APG98_LEXEM=value\u0000tail" for row in invalid)
    assert any(row.get("text_escape") == r"APG98_LEXEM=value\rnext" for row in invalid)

    run = _json(SHELL_CASES)["run_behavior"]
    assert run == {
        "comments_and_blanks": True,
        "plain_and_export_assignments": True,
        "duplicate_assignment": "last-wins",
        "overlay": "inherited-base-plus-snapshot-values",
        "argv": "exact-vector",
        "shell": "never-invoked",
    }


def test_prompt_hook_fixture_covers_install_frequency_missing_command_and_failures() -> None:
    cases = _json(SHELL_CASES)
    assert isinstance(cases, dict)
    hook = cases["prompt_hook"]
    assert hook["bash"] == {
        "registration": "one PROMPT_COMMAND entry, prepended without duplicates",
        "refresh": "immediate and each prompt",
        "failure": "silent non-fatal",
    }
    assert hook["zsh"] == {
        "registration": "add-zsh-hook precmd after removing duplicate",
        "refresh": "immediate and each precmd",
        "failure": "silent non-fatal",
    }
    assert hook["missing_command"] == "silent no-op"


def test_intentional_difference_matrix_names_every_architecture_change() -> None:
    cases = _json(SHELL_CASES)
    assert isinstance(cases, dict)
    differences = " ".join(cases["apg_intentional_differences"]).lower()
    for phrase in (
        "json",
        "explicit map",
        "isolated",
        "sensitive",
        "staleness",
        "lock",
        "no-churn",
    ):
        assert phrase in differences


def test_publishable_fixture_and_environment_docs_have_no_private_paths() -> None:
    docs = (
        ROOT / "docs/environment-snapshots.md",
        ROOT / "docs/environment-snapshot-cutover-contract.md",
    )
    private_path_markers = tuple(
        "/" + component + "/" for component in ("Users", "home", "private")
    )
    for path in (*sorted(FIXTURE.rglob("*")), *docs):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in private_path_markers:
            assert marker not in text
        assert "slair" not in text.lower()
