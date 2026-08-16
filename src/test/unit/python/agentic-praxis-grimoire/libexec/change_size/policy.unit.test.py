"""Unit contracts for the closed APG change-size policy and blob inspection."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from change_size import inspection, policy  # noqa: E402


def policy_value() -> dict[str, object]:
    return {
        "classification": {
            "archive_extensions": [".gz", ".tar", ".zip"],
            "archive_signatures": [
                {"hex": "1f8b08", "offset": 0},
                {"hex": "504b0304", "offset": 0},
            ],
            "archive_treatment": "reject-by-default",
            "binary_treatment": "exact-exception-required",
            "generated_derived_evidence_globs": [
                "private/evaluations/**/*.json",
                "private/evaluations/**/*.jsonl",
            ],
            "lfs_pointer_treatment": "reject",
        },
        "exceptions": [],
        "limits": {
            "maximum_aggregate_generated_derived_evidence_bytes_per_change": 524288,
            "maximum_generated_derived_evidence_blob_bytes": 131072,
            "maximum_one_line_text_bytes": 65536,
            "maximum_ordinary_tracked_blob_bytes": 262144,
        },
        "schema_version": 1,
    }


def write_policy(tmp_path: Path, value: dict[str, object]) -> Path:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_policy_loads_exact_frozen_limits_and_closed_schema(tmp_path: Path) -> None:
    loaded = policy.load_policy(write_policy(tmp_path, policy_value()))
    assert loaded.maximum_ordinary_tracked_blob_bytes == 262144
    assert loaded.maximum_generated_derived_evidence_blob_bytes == 131072
    assert loaded.maximum_aggregate_generated_derived_evidence_bytes_per_change == 524288
    assert loaded.maximum_one_line_text_bytes == 65536
    assert loaded.generated_derived_evidence_globs[-1].endswith("*.jsonl")
    assert loaded.exceptions == ()

    unknown = policy_value()
    unknown["unknown"] = True
    with pytest.raises(policy.PolicyError, match="unknown"):
        policy.load_policy(write_policy(tmp_path, unknown))


def test_policy_rejects_threshold_inversion_and_incomplete_exception(
    tmp_path: Path,
) -> None:
    inverted = policy_value()
    limits = inverted["limits"]
    assert isinstance(limits, dict)
    limits["maximum_generated_derived_evidence_blob_bytes"] = 300000
    with pytest.raises(policy.PolicyError, match="ordering"):
        policy.load_policy(write_policy(tmp_path, inverted))

    incomplete = policy_value()
    exceptions = incomplete["exceptions"]
    assert isinstance(exceptions, list)
    exceptions.append({"id": "missing-fields"})
    with pytest.raises(policy.PolicyError, match="exception"):
        policy.load_policy(write_policy(tmp_path, incomplete))


def test_exception_requires_exact_path_mode_identity_cap_and_governance(
    tmp_path: Path,
) -> None:
    value = policy_value()
    exceptions = value["exceptions"]
    assert isinstance(exceptions, list)
    exceptions.append(
        {
            "allowed_git_modes": ["100644"],
            "classification": "ordinary",
            "exact_blob_oid": "a" * 40,
            "exact_path": "assets/logo.png",
            "expiry_condition": "any-exact-binding-change",
            "id": "logo",
            "introduced_phase": "APG53",
            "maximum_bytes": 200000,
            "overrides": ["binary_treatment"],
            "owner": "release/public-surface.json",
            "reason": "non-regenerable public asset",
            "review_condition": "any-binding-policy-rights-or-purpose-change",
            "rights_notice_status": "verified-no-notice-required",
        }
    )
    loaded = policy.load_policy(write_policy(tmp_path, value))
    assert loaded.exceptions[0].exact_path == "assets/logo.png"


@pytest.mark.parametrize("value", [0, -1, True, "1"])
def test_positive_integer_validation_rejects_nonpositive_and_bool(value: object) -> None:
    with pytest.raises(policy.PolicyError, match="positive integer"):
        policy._positive(value, "limit")


@pytest.mark.parametrize(
    "value",
    [[], ["value", "value"], ["value", ""], "value"],
)
def test_unique_string_array_validation_rejects_open_shapes(value: object) -> None:
    with pytest.raises(policy.PolicyError, match="unique string array"):
        policy._strings(value, "values")


def test_closed_schema_rejects_non_object() -> None:
    with pytest.raises(policy.PolicyError, match="closed"):
        policy._closed([], {"required"}, "value")


def test_exception_rejects_unsafe_path_bad_oid_mode_and_override() -> None:
    base = {
        "allowed_git_modes": ["100644"],
        "classification": "ordinary",
        "exact_blob_oid": "a" * 40,
        "exact_path": "assets/logo.png",
        "expiry_condition": "any-exact-binding-change",
        "id": "logo",
        "introduced_phase": "APG53",
        "maximum_bytes": 200000,
        "overrides": ["binary_treatment"],
        "owner": "release/public-surface.json",
        "reason": "non-regenerable public asset",
        "review_condition": "any-binding-policy-rights-or-purpose-change",
        "rights_notice_status": "verified-no-notice-required",
    }
    for key, replacement, message in (
        ("exact_path", "../logo.png", "unsafe"),
        ("owner", "../owner", "owner"),
        ("id", "INVALID", "id"),
        ("classification", "binary-asset", "classification"),
        ("introduced_phase", "phase-53", "introduced_phase"),
        ("rights_notice_status", "verified", "rights_notice_status"),
        ("review_condition", "identity changes", "review_condition"),
        ("expiry_condition", "identity changes", "expiry_condition"),
        ("exact_blob_oid", "bad", "blob"),
        ("allowed_git_modes", ["bad"], "mode"),
        ("overrides", ["unknown"], "override"),
    ):
        candidate = dict(base)
        candidate[key] = replacement
        with pytest.raises(policy.PolicyError, match=message):
            policy._exception(candidate)


@pytest.mark.parametrize(
    ("section", "key", "replacement", "message"),
    [
        ("top", "schema_version", 2, "schema_version"),
        ("classification", "archive_treatment", "allow", "archive treatment"),
        ("classification", "binary_treatment", "allow", "binary treatment"),
        ("classification", "lfs_pointer_treatment", "allow", "LFS"),
        ("classification", "archive_signatures", [], "archive signatures"),
        ("top", "exceptions", {}, "exceptions"),
    ],
)
def test_policy_rejects_closed_semantic_control_values(
    section: str,
    key: str,
    replacement: object,
    message: str,
) -> None:
    value = policy_value()
    target = value if section == "top" else value["classification"]
    assert isinstance(target, dict)
    target[key] = replacement
    with pytest.raises(policy.PolicyError, match=message):
        policy.load_policy_bytes(json.dumps(value).encode())


def test_blob_inspection_classifies_generated_text_binary_archive_and_lfs(
    tmp_path: Path,
) -> None:
    loaded = policy.load_policy(write_policy(tmp_path, policy_value()))
    generated = inspection.inspect_blob(
        "private/evaluations/apg99/corpus.jsonl",
        "100644",
        b'{"row":1}\n',
        loaded,
    )
    assert generated.classification == "generated-derived-evidence"
    assert generated.longest_line_bytes == 9
    assert not generated.binary and not generated.archive

    ordinary = inspection.inspect_blob("docs/readme.md", "100644", b"a\nbb\n", loaded)
    assert ordinary.classification == "ordinary"
    assert ordinary.longest_line_bytes == 2

    binary = inspection.inspect_blob("assets/value.bin", "100644", b"a\0b", loaded)
    assert binary.binary
    archive = inspection.inspect_blob("evidence.gz", "100644", b"\x1f\x8b\x08x", loaded)
    assert archive.archive
    lfs = inspection.inspect_blob(
        "evidence.dat",
        "100644",
        b"version https://git-lfs.github.com/spec/v1\n",
        loaded,
    )
    assert lfs.lfs_pointer
