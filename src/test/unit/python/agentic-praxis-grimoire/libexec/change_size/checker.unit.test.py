"""Pure change derivation, evaluation, and rendering contracts."""

from __future__ import annotations

from pathlib import Path
import sys

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

from change_size import checker, policy  # noqa: E402
from change_size.git_adapter import Entry  # noqa: E402


class Repository:
    def __init__(self, blobs: dict[str, bytes]) -> None:
        self.blobs = blobs

    def blob(self, oid: str) -> bytes:
        return self.blobs[oid]


def configured_policy(*, exception: policy.ExceptionRule | None = None) -> policy.Policy:
    return policy.Policy(
        maximum_ordinary_tracked_blob_bytes=10,
        maximum_generated_derived_evidence_blob_bytes=8,
        maximum_aggregate_generated_derived_evidence_bytes_per_change=12,
        maximum_one_line_text_bytes=5,
        generated_derived_evidence_globs=("private/**/*.jsonl",),
        archive_extensions=(".gz",),
        archive_signatures=(policy.ArchiveSignature(0, b"PK"),),
        archive_treatment="reject-by-default",
        binary_treatment="exact-exception-required",
        lfs_pointer_treatment="reject",
        exceptions=(() if exception is None else (exception,)),
    )


def entry(path: str, oid: str, size: int, mode: str = "100644") -> Entry:
    return Entry(path, mode, oid, size)


def test_change_derivation_covers_all_classes_and_tree() -> None:
    before = {
        "delete": entry("delete", "a" * 40, 1),
        "mode": entry("mode", "b" * 40, 1),
        "modify": entry("modify", "c" * 40, 1),
        "old": entry("old", "d" * 40, 1),
    }
    after = {
        "add": entry("add", "e" * 40, 1),
        "mode": entry("mode", "b" * 40, 1, "100755"),
        "modify": entry("modify", "f" * 40, 2),
        "new": entry("new", "d" * 40, 1),
    }
    changes = checker.derive_changes(before, after)
    assert {item.change_class for item in changes} == {
        "add",
        "delete",
        "mode",
        "modify",
        "rename",
    }
    assert checker.tree_changes({"x": entry("x", "a" * 40, 1)})[0].change_class == "tree"


def test_evaluation_reports_each_control_aggregate_unique_blobs_and_rewrites() -> None:
    entries = [
        entry("private/evaluations/x/a.jsonl", "a" * 40, 9),
        entry("private/evaluations/x/b.jsonl", "b" * 40, 7),
        entry("ordinary.txt", "c" * 40, 11),
        entry("archive.gz", "d" * 40, 2),
        entry("binary.dat", "e" * 40, 3),
        entry("pointer", "f" * 40, 44),
    ]
    blobs = {
        "a" * 40: b"123456",
        "b" * 40: b"123456",
        "c" * 40: b"ordinary text",
        "d" * 40: b"PK",
        "e" * 40: b"a\0b",
        "f" * 40: b"version https://git-lfs.github.com/spec/v1\n",
        "0" * 40: b"old",
    }
    changes = [
        checker.Change("modify", entries[0].path, None, entry(entries[0].path, "0" * 40, 3), entries[0]),
        checker.Change("delete", "deleted", None, entry("deleted", "0" * 40, 3), None),
        *(checker.Change("add", item.path, None, None, item) for item in entries[1:]),
    ]
    result = checker.evaluate(
        Repository(blobs),  # type: ignore[arg-type]
        configured_policy(),
        changes,
        mode="staged",
        revision="HEAD",
        before_entries={"old": entry("old", "0" * 40, 3)},
    )
    controls = {item["control"] for item in result["violations"]}
    assert {
        "archive_treatment",
        "binary_treatment",
        "generated_aggregate_bytes",
        "generated_blob_bytes",
        "lfs_pointer_treatment",
        "ordinary_blob_bytes",
        "text_line_bytes",
    } <= controls
    assert result["result"] == "violation"
    assert result["largest_rewritten_blobs"]
    assert result["aggregate_new_blob_bytes"] == sum(item.size for item in entries)
    assert checker.render_json(result).endswith("\n")
    rendered = checker.render_text(result)
    assert "largest resulting blobs:" in rendered and "violations:" in rendered


def test_exact_exception_overrides_controls_and_tree_has_no_aggregate_violation() -> None:
    item = entry("asset.bin", "a" * 40, 3)
    exception = policy.ExceptionRule(
        id="asset",
        exact_path=item.path,
        classification="ordinary",
        allowed_git_modes=(item.mode,),
        exact_blob_oid=item.oid,
        maximum_bytes=3,
        overrides=("binary_treatment",),
        owner="release/public-surface.json",
        reason="accepted asset",
        rights_notice_status="verified-no-notice-required",
        introduced_phase="APG53",
        review_condition="any-binding-policy-rights-or-purpose-change",
        expiry_condition="any-exact-binding-change",
    )
    result = checker.evaluate(
        Repository({item.oid: b"a\0b"}),  # type: ignore[arg-type]
        configured_policy(exception=exception),
        checker.tree_changes({item.path: item}),
        mode="tree",
        revision="HEAD",
        before_entries={},
    )
    assert result["exceptions_used"] == ["asset"]
    assert result["violations"] == []
    empty = checker.evaluate(
        Repository({}),  # type: ignore[arg-type]
        configured_policy(),
        [],
        mode="staged",
        revision="HEAD",
        before_entries={},
    )
    assert "NONE" in checker.render_text(empty)


def test_same_blob_is_classified_per_path_and_counted_generated_once() -> None:
    oid = "9" * 40
    ordinary = entry("a.txt", oid, 9)
    generated = entry("private/evaluations/apg99/bulk.jsonl", oid, 9)
    result = checker.evaluate(
        Repository({oid: b"row\n"}),  # type: ignore[arg-type]
        configured_policy(),
        [
            checker.Change("add", ordinary.path, None, None, ordinary),
            checker.Change("add", generated.path, None, None, generated),
        ],
        mode="staged",
        revision="HEAD",
        before_entries={},
    )
    assert result["aggregate_new_blob_bytes"] == 9
    assert result["aggregate_generated_evidence_bytes"] == 9
    assert any(
        item["control"] == "generated_blob_bytes"
        and item["path"] == generated.path
        for item in result["violations"]
    )


def test_exact_generated_aggregate_exception_excludes_only_bound_blob() -> None:
    first = entry("private/evaluations/apg99/a.jsonl", "7" * 40, 7)
    second = entry("private/evaluations/apg99/b.jsonl", "8" * 40, 7)
    exception = policy.ExceptionRule(
        id="bulk-a",
        exact_path=first.path,
        classification="generated-derived-evidence",
        allowed_git_modes=(first.mode,),
        exact_blob_oid=first.oid,
        maximum_bytes=first.size,
        overrides=("generated_aggregate_bytes",),
        owner="testing/apg-change-size-policy.json",
        reason="bounded generated evidence fixture",
        rights_notice_status="synthetic-test-fixture",
        introduced_phase="APG53",
        review_condition="any-binding-policy-rights-or-purpose-change",
        expiry_condition="any-exact-binding-change",
    )
    result = checker.evaluate(
        Repository({first.oid: b"a\n", second.oid: b"b\n"}),  # type: ignore[arg-type]
        configured_policy(exception=exception),
        [
            checker.Change("add", first.path, None, None, first),
            checker.Change("add", second.path, None, None, second),
        ],
        mode="staged",
        revision="HEAD",
        before_entries={},
    )
    assert result["aggregate_generated_evidence_bytes"] == 14
    assert not any(
        item["control"] == "generated_aggregate_bytes"
        for item in result["violations"]
    )
    assert result["exceptions_used"] == ["bulk-a"]


def test_generated_aggregate_counts_added_paths_reusing_existing_blobs() -> None:
    first = entry("private/evaluations/apg99/a.jsonl", "1" * 40, 7)
    second = entry("private/evaluations/apg99/b.jsonl", "2" * 40, 7)
    before = {
        "fixtures/a.txt": entry("fixtures/a.txt", first.oid, first.size),
        "fixtures/b.txt": entry("fixtures/b.txt", second.oid, second.size),
    }
    result = checker.evaluate(
        Repository({first.oid: b"a\n", second.oid: b"b\n"}),  # type: ignore[arg-type]
        configured_policy(),
        [
            checker.Change("add", first.path, None, None, first),
            checker.Change("add", second.path, None, None, second),
        ],
        mode="staged",
        revision="HEAD",
        before_entries=before,
    )
    assert result["aggregate_new_blob_bytes"] == 0
    assert result["aggregate_generated_evidence_bytes"] == 14
    assert any(
        item["control"] == "generated_aggregate_bytes"
        for item in result["violations"]
    )


def test_generated_aggregate_counts_renames_into_generated_paths() -> None:
    first = entry("private/evaluations/apg99/a.jsonl", "3" * 40, 7)
    second = entry("private/evaluations/apg99/b.jsonl", "4" * 40, 7)
    old_first = entry("fixtures/a.txt", first.oid, first.size)
    old_second = entry("fixtures/b.txt", second.oid, second.size)
    result = checker.evaluate(
        Repository({first.oid: b"a\n", second.oid: b"b\n"}),  # type: ignore[arg-type]
        configured_policy(),
        [
            checker.Change("rename", first.path, old_first.path, old_first, first),
            checker.Change("rename", second.path, old_second.path, old_second, second),
        ],
        mode="staged",
        revision="HEAD",
        before_entries={
            old_first.path: old_first,
            old_second.path: old_second,
        },
    )
    assert result["aggregate_generated_evidence_bytes"] == 14
    assert any(
        item["control"] == "generated_aggregate_bytes"
        for item in result["violations"]
    )
