"""Change derivation, policy evaluation, and deterministic rendering."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Iterable

from .git_adapter import Entry, GitRepository
from .inspection import BlobInspection, inspect_blob
from .policy import ExceptionRule, Policy


@dataclass(frozen=True, slots=True)
class Change:
    change_class: str
    path: str
    old_path: str | None
    before: Entry | None
    after: Entry | None


def derive_changes(
    before: dict[str, Entry], after: dict[str, Entry]
) -> list[Change]:
    changes: list[Change] = []
    common = sorted(set(before) & set(after))
    for path in common:
        old, new = before[path], after[path]
        if old.oid != new.oid:
            changes.append(Change("modify", path, None, old, new))
        elif old.mode != new.mode:
            changes.append(Change("mode", path, None, old, new))
    removed = {path: before[path] for path in sorted(set(before) - set(after))}
    added = {path: after[path] for path in sorted(set(after) - set(before))}
    for old_path in list(removed):
        old = removed[old_path]
        matches = [
            path
            for path, entry in added.items()
            if entry.oid == old.oid
        ]
        if matches:
            new_path = matches[0]
            changes.append(
                Change("rename", new_path, old_path, old, added.pop(new_path))
            )
            removed.pop(old_path)
    changes.extend(
        Change("delete", path, None, entry, None)
        for path, entry in removed.items()
    )
    changes.extend(
        Change("add", path, None, None, entry)
        for path, entry in added.items()
    )
    return sorted(changes, key=lambda item: (item.path, item.change_class))


def tree_changes(entries: dict[str, Entry]) -> list[Change]:
    return [
        Change("tree", path, None, None, entry)
        for path, entry in sorted(entries.items())
    ]


def _matching_exception(
    rule: ExceptionRule,
    entry: Entry,
    inspection: BlobInspection,
) -> bool:
    return (
        rule.exact_path == entry.path
        and entry.mode in rule.allowed_git_modes
        and rule.exact_blob_oid == entry.oid
        and entry.size <= rule.maximum_bytes
        and rule.classification == inspection.classification
    )


def _violation(
    control: str,
    path: str,
    observed: int | str,
    limit: int | str,
) -> dict[str, Any]:
    return {
        "control": control,
        "limit": limit,
        "observed": observed,
        "path": path,
    }


def _change_record(change: Change) -> dict[str, Any]:
    before_size = change.before.size if change.before else 0
    after_size = change.after.size if change.after else 0
    return {
        "before_blob_bytes": before_size,
        "change_class": change.change_class,
        "old_path": change.old_path,
        "path": change.path,
        "resulting_blob_bytes": after_size,
        "review_bytes": before_size + after_size,
    }


def evaluate(
    repository: GitRepository,
    policy: Policy,
    changes: list[Change],
    *,
    mode: str,
    revision: str,
    before_entries: dict[str, Entry],
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    exceptions_used: set[str] = set()
    payloads: dict[str, bytes] = {}
    inspections: dict[tuple[str, str, str], BlobInspection] = {}
    overrides_by_entry: dict[tuple[str, str, str], set[str]] = {}
    resulting: list[Entry] = []

    def inspection_for(entry: Entry) -> BlobInspection:
        key = (entry.oid, entry.path, entry.mode)
        if key not in inspections:
            if entry.oid not in payloads:
                payloads[entry.oid] = repository.blob(entry.oid)
            inspections[key] = inspect_blob(
                entry.path,
                entry.mode,
                payloads[entry.oid],
                policy,
            )
        return inspections[key]

    for change in changes:
        entry = change.after
        if entry is None:
            continue
        resulting.append(entry)
        inspected = inspection_for(entry)
        matching = [
            item
            for item in policy.exceptions
            if _matching_exception(item, entry, inspected)
        ]
        overrides = set().union(*(item.overrides for item in matching))
        overrides_by_entry[(entry.oid, entry.path, entry.mode)] = overrides
        exceptions_used.update(item.id for item in matching)
        if inspected.classification == "generated-derived-evidence":
            if (
                entry.size > policy.maximum_generated_derived_evidence_blob_bytes
                and "generated_blob_bytes" not in overrides
            ):
                violations.append(
                    _violation(
                        "generated_blob_bytes",
                        entry.path,
                        entry.size,
                        policy.maximum_generated_derived_evidence_blob_bytes,
                    )
                )
        elif (
            entry.size > policy.maximum_ordinary_tracked_blob_bytes
            and "ordinary_blob_bytes" not in overrides
        ):
            violations.append(
                _violation(
                    "ordinary_blob_bytes",
                    entry.path,
                    entry.size,
                    policy.maximum_ordinary_tracked_blob_bytes,
                )
            )
        if (
            inspected.longest_line_bytes is not None
            and inspected.longest_line_bytes > policy.maximum_one_line_text_bytes
            and "text_line_bytes" not in overrides
        ):
            violations.append(
                _violation(
                    "text_line_bytes",
                    entry.path,
                    inspected.longest_line_bytes,
                    policy.maximum_one_line_text_bytes,
                )
            )
        if inspected.lfs_pointer and "lfs_pointer_treatment" not in overrides:
            violations.append(
                _violation("lfs_pointer_treatment", entry.path, "lfs-pointer", "reject")
            )
        if inspected.archive and "archive_treatment" not in overrides:
            violations.append(
                _violation("archive_treatment", entry.path, "archive", "reject")
            )
        elif inspected.binary and "binary_treatment" not in overrides:
            violations.append(
                _violation(
                    "binary_treatment",
                    entry.path,
                    "binary",
                    "exact-exception-required",
                )
            )
    before_oids = {entry.oid for entry in before_entries.values()}
    new_entries_by_oid: dict[str, list[Entry]] = {}
    for entry in resulting:
        if mode == "tree" or entry.oid not in before_oids:
            new_entries_by_oid.setdefault(entry.oid, []).append(entry)
    aggregate_new = sum(entries[0].size for entries in new_entries_by_oid.values())
    generated_review_entries = [
        change.after
        for change in changes
        if change.after is not None
        and change.change_class in {"add", "modify", "rename", "tree"}
        and inspection_for(change.after).classification
        == "generated-derived-evidence"
    ]
    aggregate_generated = sum(entry.size for entry in generated_review_entries)
    aggregate_generated_without_exceptions = sum(
        entry.size
        for entry in generated_review_entries
        if "generated_aggregate_bytes"
        not in overrides_by_entry.get((entry.oid, entry.path, entry.mode), set())
    )
    if (
        mode != "tree"
        and aggregate_generated_without_exceptions
        > policy.maximum_aggregate_generated_derived_evidence_bytes_per_change
    ):
        violations.append(
            _violation(
                "generated_aggregate_bytes",
                "<change>",
                aggregate_generated_without_exceptions,
                policy.maximum_aggregate_generated_derived_evidence_bytes_per_change,
            )
        )
    largest_line = max(
        (
            (inspection.longest_line_bytes, entry.path)
            for entry in resulting
            if (inspection := inspection_for(entry)).longest_line_bytes is not None
        ),
        default=(0, ""),
    )
    resulting_rows = sorted(
        (
            {"bytes": entry.size, "oid": entry.oid, "path": entry.path}
            for entry in {entry.oid: entry for entry in resulting}.values()
        ),
        key=lambda item: (-item["bytes"], item["path"]),
    )[:10]
    rewritten = sorted(
        (
            {
                "after_bytes": change.after.size,
                "before_bytes": change.before.size,
                "path": change.path,
                "review_bytes": change.before.size + change.after.size,
            }
            for change in changes
            if change.before is not None
            and change.after is not None
            and change.before.oid != change.after.oid
        ),
        key=lambda item: (-item["review_bytes"], item["path"]),
    )[:10]
    return {
        "aggregate_generated_evidence_bytes": aggregate_generated,
        "aggregate_new_blob_bytes": aggregate_new,
        "changes": [_change_record(change) for change in changes],
        "exceptions_used": sorted(exceptions_used),
        "largest_resulting_blobs": resulting_rows,
        "largest_rewritten_blobs": rewritten,
        "largest_text_line": {
            "bytes": largest_line[0],
            "path": largest_line[1],
        },
        "mode": mode,
        "policy_limits": {
            "generated_aggregate_bytes": policy.maximum_aggregate_generated_derived_evidence_bytes_per_change,
            "generated_blob_bytes": policy.maximum_generated_derived_evidence_blob_bytes,
            "ordinary_blob_bytes": policy.maximum_ordinary_tracked_blob_bytes,
            "text_line_bytes": policy.maximum_one_line_text_bytes,
        },
        "result": "violation" if violations else "pass",
        "revision": revision,
        "schema_version": 1,
        "violations": sorted(
            violations,
            key=lambda item: (item["path"], item["control"]),
        ),
    }


def render_json(result: dict[str, Any]) -> str:
    return json.dumps(
        result,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ) + "\n"


def render_text(result: dict[str, Any]) -> str:
    lines = [
        f"APG change-size check: {result['result']}",
        f"mode: {result['mode']}",
        f"revision: {result['revision']}",
        f"changes: {len(result['changes'])}",
        f"aggregate new blob bytes: {result['aggregate_new_blob_bytes']}",
        "aggregate generated-evidence bytes: "
        f"{result['aggregate_generated_evidence_bytes']}",
        "largest text line: "
        f"{result['largest_text_line']['bytes']} "
        f"{result['largest_text_line']['path'] or 'NONE'}",
        "largest resulting blobs:",
    ]
    lines.extend(
        f"  {item['bytes']} {item['path']}"
        for item in result["largest_resulting_blobs"]
    )
    if not result["largest_resulting_blobs"]:
        lines.append("  NONE")
    lines.append("largest rewritten blobs:")
    lines.extend(
        f"  {item['review_bytes']} {item['path']}"
        for item in result["largest_rewritten_blobs"]
    )
    if not result["largest_rewritten_blobs"]:
        lines.append("  NONE")
    lines.append(
        "exceptions used: "
        + (", ".join(result["exceptions_used"]) if result["exceptions_used"] else "NONE")
    )
    lines.append("violations:")
    lines.extend(
        f"  {item['control']} {item['path']} observed={item['observed']} "
        f"limit={item['limit']}"
        for item in result["violations"]
    )
    if not result["violations"]:
        lines.append("  NONE")
    return "\n".join(lines) + "\n"
