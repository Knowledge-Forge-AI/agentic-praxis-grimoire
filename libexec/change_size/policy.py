"""Closed-schema APG change-size policy loading."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


_OID = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_MODE = re.compile(r"^[0-7]{6}$")
_TOP_KEYS = {"classification", "exceptions", "limits", "schema_version"}
_CLASSIFICATION_KEYS = {
    "archive_extensions",
    "archive_signatures",
    "archive_treatment",
    "binary_treatment",
    "generated_derived_evidence_globs",
    "lfs_pointer_treatment",
}
_LIMIT_KEYS = {
    "maximum_aggregate_generated_derived_evidence_bytes_per_change",
    "maximum_generated_derived_evidence_blob_bytes",
    "maximum_one_line_text_bytes",
    "maximum_ordinary_tracked_blob_bytes",
}
_EXCEPTION_KEYS = {
    "allowed_git_modes",
    "classification",
    "exact_blob_oid",
    "exact_path",
    "expiry_condition",
    "id",
    "introduced_phase",
    "maximum_bytes",
    "overrides",
    "owner",
    "reason",
    "review_condition",
    "rights_notice_status",
}
_OVERRIDES = {
    "archive_treatment",
    "binary_treatment",
    "generated_aggregate_bytes",
    "generated_blob_bytes",
    "ordinary_blob_bytes",
    "text_line_bytes",
}
_CLASSIFICATIONS = {"generated-derived-evidence", "ordinary"}
_RIGHTS_NOTICE_STATUSES = {
    "synthetic-test-fixture",
    "verified-no-notice-required",
    "verified-required-notice-present",
}
_REVIEW_CONDITIONS = {"any-binding-policy-rights-or-purpose-change"}
_EXPIRY_CONDITIONS = {"any-exact-binding-change"}
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PHASE = re.compile(r"^APG[1-9][0-9]*$")


class PolicyError(ValueError):
    """The policy is missing, malformed, open, or internally inconsistent."""


@dataclass(frozen=True, slots=True)
class ArchiveSignature:
    offset: int
    value: bytes


@dataclass(frozen=True, slots=True)
class ExceptionRule:
    id: str
    exact_path: str
    classification: str
    allowed_git_modes: tuple[str, ...]
    exact_blob_oid: str
    maximum_bytes: int
    overrides: tuple[str, ...]
    owner: str
    reason: str
    rights_notice_status: str
    introduced_phase: str
    review_condition: str
    expiry_condition: str


@dataclass(frozen=True, slots=True)
class Policy:
    maximum_ordinary_tracked_blob_bytes: int
    maximum_generated_derived_evidence_blob_bytes: int
    maximum_aggregate_generated_derived_evidence_bytes_per_change: int
    maximum_one_line_text_bytes: int
    generated_derived_evidence_globs: tuple[str, ...]
    archive_extensions: tuple[str, ...]
    archive_signatures: tuple[ArchiveSignature, ...]
    archive_treatment: str
    binary_treatment: str
    lfs_pointer_treatment: str
    exceptions: tuple[ExceptionRule, ...]


def _closed(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        unknown = sorted(set(value) - expected) if isinstance(value, dict) else []
        suffix = f"; unknown keys: {', '.join(unknown)}" if unknown else ""
        raise PolicyError(f"{label} schema is not closed{suffix}")
    return value


def _positive(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise PolicyError(f"{label} must be a positive integer")
    return value


def _strings(value: Any, label: str) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
        or len(set(value)) != len(value)
    ):
        raise PolicyError(f"{label} must be a non-empty unique string array")
    return tuple(value)


def _safe_path(value: str) -> bool:
    path = Path(value)
    return (
        value == path.as_posix()
        and not path.is_absolute()
        and value not in {"", ".", ".."}
        and ".." not in path.parts
        and "\\" not in value
        and not any(ord(character) < 32 or ord(character) == 127 for character in value)
    )


def _exception(value: Any) -> ExceptionRule:
    item = _closed(value, _EXCEPTION_KEYS, "exception")
    strings = {
        key: item[key]
        for key in (
            "classification",
            "exact_blob_oid",
            "exact_path",
            "expiry_condition",
            "id",
            "introduced_phase",
            "owner",
            "reason",
            "review_condition",
            "rights_notice_status",
        )
    }
    if any(not isinstance(value, str) or not value for value in strings.values()):
        raise PolicyError("exception string fields must be non-empty")
    if not _safe_path(strings["exact_path"]):
        raise PolicyError("exception exact_path is unsafe")
    if not _safe_path(strings["owner"]):
        raise PolicyError("exception owner is unsafe")
    if not _ID.fullmatch(strings["id"]):
        raise PolicyError("exception id is invalid")
    if strings["classification"] not in _CLASSIFICATIONS:
        raise PolicyError("exception classification is invalid")
    if not _PHASE.fullmatch(strings["introduced_phase"]):
        raise PolicyError("exception introduced_phase is invalid")
    if strings["rights_notice_status"] not in _RIGHTS_NOTICE_STATUSES:
        raise PolicyError("exception rights_notice_status is invalid")
    if strings["review_condition"] not in _REVIEW_CONDITIONS:
        raise PolicyError("exception review_condition is invalid")
    if strings["expiry_condition"] not in _EXPIRY_CONDITIONS:
        raise PolicyError("exception expiry_condition is invalid")
    if not _OID.fullmatch(strings["exact_blob_oid"]):
        raise PolicyError("exception exact_blob_oid is invalid")
    modes = _strings(item["allowed_git_modes"], "exception allowed_git_modes")
    if any(not _MODE.fullmatch(mode) for mode in modes):
        raise PolicyError("exception Git mode is invalid")
    overrides = _strings(item["overrides"], "exception overrides")
    if set(overrides) - _OVERRIDES:
        raise PolicyError("exception override is unknown")
    return ExceptionRule(
        id=strings["id"],
        exact_path=strings["exact_path"],
        classification=strings["classification"],
        allowed_git_modes=modes,
        exact_blob_oid=strings["exact_blob_oid"],
        maximum_bytes=_positive(item["maximum_bytes"], "exception maximum_bytes"),
        overrides=overrides,
        owner=strings["owner"],
        reason=strings["reason"],
        rights_notice_status=strings["rights_notice_status"],
        introduced_phase=strings["introduced_phase"],
        review_condition=strings["review_condition"],
        expiry_condition=strings["expiry_condition"],
    )


def load_policy_bytes(payload: bytes) -> Policy:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PolicyError("policy is not valid UTF-8 JSON") from error
    top = _closed(value, _TOP_KEYS, "policy")
    if top["schema_version"] != 1:
        raise PolicyError("unsupported policy schema_version")
    limits = _closed(top["limits"], _LIMIT_KEYS, "limits")
    ordinary = _positive(
        limits["maximum_ordinary_tracked_blob_bytes"],
        "maximum ordinary tracked blob bytes",
    )
    generated = _positive(
        limits["maximum_generated_derived_evidence_blob_bytes"],
        "maximum generated-derived evidence blob bytes",
    )
    aggregate = _positive(
        limits["maximum_aggregate_generated_derived_evidence_bytes_per_change"],
        "maximum aggregate generated-derived evidence bytes",
    )
    line = _positive(
        limits["maximum_one_line_text_bytes"],
        "maximum one-line text bytes",
    )
    if not line <= generated <= ordinary <= aggregate:
        raise PolicyError("policy threshold ordering is invalid")
    classification = _closed(
        top["classification"], _CLASSIFICATION_KEYS, "classification"
    )
    archive_treatment = classification["archive_treatment"]
    binary_treatment = classification["binary_treatment"]
    lfs_treatment = classification["lfs_pointer_treatment"]
    if archive_treatment != "reject-by-default":
        raise PolicyError("archive treatment must be reject-by-default")
    if binary_treatment != "exact-exception-required":
        raise PolicyError("binary treatment must require an exact exception")
    if lfs_treatment != "reject":
        raise PolicyError("LFS pointer treatment must be reject")
    signatures_value = classification["archive_signatures"]
    if not isinstance(signatures_value, list) or not signatures_value:
        raise PolicyError("archive signatures must be a non-empty array")
    signatures: list[ArchiveSignature] = []
    for raw in signatures_value:
        item = _closed(raw, {"hex", "offset"}, "archive signature")
        if not isinstance(item["offset"], int) or item["offset"] < 0:
            raise PolicyError("archive signature offset is invalid")
        try:
            decoded = bytes.fromhex(item["hex"])
        except (TypeError, ValueError) as error:
            raise PolicyError("archive signature hex is invalid") from error
        if not decoded:
            raise PolicyError("archive signature must not be empty")
        signatures.append(ArchiveSignature(item["offset"], decoded))
    exceptions_value = top["exceptions"]
    if not isinstance(exceptions_value, list):
        raise PolicyError("exceptions must be an array")
    exceptions = tuple(_exception(item) for item in exceptions_value)
    if len({item.id for item in exceptions}) != len(exceptions):
        raise PolicyError("exception IDs must be unique")
    if len({item.exact_path for item in exceptions}) != len(exceptions):
        raise PolicyError("exception paths must be unique")
    return Policy(
        maximum_ordinary_tracked_blob_bytes=ordinary,
        maximum_generated_derived_evidence_blob_bytes=generated,
        maximum_aggregate_generated_derived_evidence_bytes_per_change=aggregate,
        maximum_one_line_text_bytes=line,
        generated_derived_evidence_globs=_strings(
            classification["generated_derived_evidence_globs"],
            "generated-derived evidence globs",
        ),
        archive_extensions=_strings(
            classification["archive_extensions"], "archive extensions"
        ),
        archive_signatures=tuple(signatures),
        archive_treatment=archive_treatment,
        binary_treatment=binary_treatment,
        lfs_pointer_treatment=lfs_treatment,
        exceptions=exceptions,
    )


def load_policy(path: Path) -> Policy:
    try:
        return load_policy_bytes(path.read_bytes())
    except OSError as error:
        raise PolicyError("cannot read policy") from error
