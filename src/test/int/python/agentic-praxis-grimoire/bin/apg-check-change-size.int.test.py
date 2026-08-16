"""Real-Git integration contracts for the APG change-size checker."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "apg-check-change-size"


def run(cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(COMMAND), *arguments],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def git(cwd: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def valid_policy() -> dict[str, object]:
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


def valid_exception() -> dict[str, object]:
    return {
        "allowed_git_modes": ["100644"],
        "classification": "ordinary",
        "exact_blob_oid": "a" * 40,
        "exact_path": "asset.bin",
        "expiry_condition": "any-exact-binding-change",
        "id": "asset",
        "introduced_phase": "APG53",
        "maximum_bytes": 3,
        "overrides": ["binary_treatment"],
        "owner": "release/public-surface.json",
        "reason": "synthetic accepted binary control",
        "review_condition": "any-binding-policy-rights-or-purpose-change",
        "rights_notice_status": "synthetic-test-fixture",
    }


def initialize(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "APG Test")
    git(repo, "config", "user.email", "apg@example.invalid")
    policy_path = repo / "testing" / "apg-change-size-policy.json"
    policy_path.parent.mkdir()
    policy_path.write_text(json.dumps(valid_policy()), encoding="utf-8")
    (repo / "README.md").write_text("baseline\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "baseline")
    return repo


def test_real_git_diagnostic_and_empty_render_boundaries(tmp_path: Path) -> None:
    bare_repo = tmp_path / "bare.git"
    bare_repo.mkdir()
    git(bare_repo, "init", "--bare", "-q")
    assert git(bare_repo, "rev-parse", "--is-bare-repository") == "true"
    assert git(bare_repo, "rev-parse", "--is-inside-work-tree") == "false"

    outside = run(bare_repo, "staged")
    assert outside.returncode == 2
    assert "git error:" in outside.stderr.lower()

    repo = initialize(tmp_path)
    victim = repo / "victim.txt"
    victim.write_text("delete me\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "victim")
    victim.unlink()
    git(repo, "add", "-A")
    deletion = run(repo, "staged")
    assert deletion.returncode == 0, deletion.stderr
    assert "largest resulting blobs:\n  NONE" in deletion.stdout
    assert "largest rewritten blobs:\n  NONE" in deletion.stdout

    git(repo, "reset", "--hard", "-q", "HEAD")
    victim.write_text("rewritten\n", encoding="utf-8")
    git(repo, "add", "victim.txt")
    rewritten = run(repo, "staged")
    assert rewritten.returncode == 0, rewritten.stderr
    assert "largest rewritten blobs:\n  NONE" not in rewritten.stdout

    git(repo, "reset", "--hard", "-q", "HEAD")
    payload = repo / "payload"
    payload.write_text("content\n", encoding="utf-8")
    oid = git(repo, "hash-object", "-w", str(payload))
    payload.unlink()
    git(
        repo,
        "update-index",
        "--add",
        "--cacheinfo",
        f"100644,{oid},bad\nviolations: NONE",
    )
    unsafe = run(repo, "staged")
    assert unsafe.returncode == 2
    assert "tracked path is unsafe" in unsafe.stderr

    git(repo, "reset", "--hard", "-q", "HEAD")
    commit = git(repo, "rev-parse", "HEAD")
    git(repo, "update-index", "--add", "--cacheinfo", f"160000,{commit},vendor/sub")
    staged_gitlink = run(repo, "staged", "--format", "json")
    assert staged_gitlink.returncode == 0, staged_gitlink.stderr
    git(repo, "commit", "-qm", "gitlink boundary")
    tree = run(repo, "tree", "HEAD", "--format", "json")
    assert tree.returncode == 0, tree.stderr

    conflict = subprocess.run(
        ["git", "update-index", "--index-info"],
        cwd=repo,
        input=f"100644 {oid} 1\tconflict\n",
        text=True,
        capture_output=True,
        check=False,
    )
    assert conflict.returncode == 0, conflict.stderr
    unmerged = run(repo, "staged")
    assert unmerged.returncode == 2
    assert "unmerged index entries" in unmerged.stderr


def test_exact_text_generated_archive_and_ordinary_exceptions(
    tmp_path: Path,
) -> None:
    repo = initialize(tmp_path)
    generated = repo / "private" / "evaluations" / "apg99" / "bulk.jsonl"
    generated.parent.mkdir(parents=True)
    generated.write_bytes(b"x" * 140000)
    archive = repo / "accepted.gz"
    archive.write_text("archive fixture\n", encoding="utf-8")
    ordinary = repo / "ordinary.txt"
    ordinary.write_bytes((b"x" * 99 + b"\n") * 2700)

    def rule(
        identifier: str,
        path: str,
        classification: str,
        maximum: int,
        overrides: list[str],
    ) -> dict[str, object]:
        return {
            "allowed_git_modes": ["100644"],
            "classification": classification,
            "exact_blob_oid": git(repo, "hash-object", str(repo / path)),
            "exact_path": path,
            "expiry_condition": "any-exact-binding-change",
            "id": identifier,
            "introduced_phase": "APG53",
            "maximum_bytes": maximum,
            "overrides": overrides,
            "owner": "testing/apg-change-size-policy.json",
            "reason": "synthetic exact exception control",
            "review_condition": "any-binding-policy-rights-or-purpose-change",
            "rights_notice_status": "synthetic-test-fixture",
        }

    policy_path = repo / "testing" / "apg-change-size-policy.json"
    value = json.loads(policy_path.read_text(encoding="utf-8"))
    value["exceptions"] = [
        rule(
            "generated-text",
            "private/evaluations/apg99/bulk.jsonl",
            "generated-derived-evidence",
            140000,
            ["generated_blob_bytes", "text_line_bytes"],
        ),
        rule(
            "archive",
            "accepted.gz",
            "ordinary",
            archive.stat().st_size,
            ["archive_treatment"],
        ),
        rule(
            "ordinary",
            "ordinary.txt",
            "ordinary",
            ordinary.stat().st_size,
            ["ordinary_blob_bytes"],
        ),
    ]
    policy_path.write_text(json.dumps(value), encoding="utf-8")
    git(repo, "add", ".")
    accepted = run(repo, "staged", "--format", "json")
    assert accepted.returncode == 0, accepted.stderr
    assert json.loads(accepted.stdout)["exceptions_used"] == [
        "archive",
        "generated-text",
        "ordinary",
    ]
    accepted_text = run(repo, "staged")
    assert accepted_text.returncode == 0, accepted_text.stderr
    assert (
        "exceptions used: archive, generated-text, ordinary"
        in accepted_text.stdout
    )


def test_help_usage_and_small_staged_source_pass_with_canonical_json(
    tmp_path: Path,
) -> None:
    repo = initialize(tmp_path)
    help_result = run(repo, "--help")
    assert help_result.returncode == 0
    assert "apg-check-change-size staged" in help_result.stdout
    assert run(repo).returncode == 2

    (repo / "libexec").mkdir()
    (repo / "libexec" / "small.py").write_text("print('ok')\n", encoding="utf-8")
    git(repo, "add", ".")
    checked = run(repo, "staged", "--format", "json")
    assert checked.returncode == 0, checked.stderr
    assert checked.stdout.endswith("\n")
    assert checked.stdout == json.dumps(
        json.loads(checked.stdout),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ) + "\n"
    assert str(repo) not in checked.stdout
    assert json.loads(checked.stdout)["result"] == "pass"
    text = run(repo, "staged")
    assert text.returncode == 0
    assert "largest resulting blobs:" in text.stdout
    assert "violations:\n  NONE" in text.stdout


def test_apg52_style_generated_jsonl_and_hidden_archive_fail(
    tmp_path: Path,
) -> None:
    repo = initialize(tmp_path)
    evidence = repo / "private" / "evaluations" / "apg99"
    evidence.mkdir(parents=True)
    (evidence / "corpus-artifacts.jsonl").write_bytes(b'{"row":"' + b"x" * 140000 + b'"}\n')
    git(repo, "add", ".")
    bulk = run(repo, "staged", "--format", "json")
    assert bulk.returncode == 1
    payload = json.loads(bulk.stdout)
    controls = {item["control"] for item in payload["violations"]}
    assert "generated_blob_bytes" in controls
    assert "text_line_bytes" in controls

    git(repo, "reset", "--hard", "-q", "HEAD")
    archive = repo / "private" / "evaluations" / "apg99" / "bulk.gz"
    archive.parent.mkdir(parents=True)
    archive.write_bytes(b"\x1f\x8b\x08" + b"x" * 100)
    git(repo, "add", ".")
    hidden = run(repo, "staged", "--format", "json")
    assert hidden.returncode == 1
    assert any(
        item["control"] == "archive_treatment"
        for item in json.loads(hidden.stdout)["violations"]
    )


def test_generated_evidence_aggregate_limit_catches_bulk_rows(tmp_path: Path) -> None:
    repo = initialize(tmp_path)
    evidence = repo / "private" / "evaluations" / "apg99"
    evidence.mkdir(parents=True)
    for index, name in enumerate(
        (
            "corpus-artifacts.jsonl",
            "corpus-exclusions.jsonl",
            "corpus-measurements.jsonl",
        )
    ):
        row = (
            b'{"kind":'
            + str(index).encode("ascii")
            + b',"value":"'
            + b"x" * 80
            + b'"}\n'
        )
        (evidence / name).write_bytes(row * 2000)
    git(repo, "add", ".")
    result = run(repo, "staged", "--format", "json")
    assert result.returncode == 1
    assert any(
        item["control"] == "generated_aggregate_bytes"
        for item in json.loads(result.stdout)["violations"]
    )


def test_reused_blob_path_classification_and_generated_aggregate(
    tmp_path: Path,
) -> None:
    repo = initialize(tmp_path)
    fixtures = repo / "fixtures"
    fixtures.mkdir()
    ordinary = fixtures / "ordinary.txt"
    ordinary.write_bytes(b"x" * 140000)
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "ordinary fixture")

    generated = repo / "private" / "evaluations" / "apg99"
    generated.mkdir(parents=True)
    (generated / "same.jsonl").write_bytes(ordinary.read_bytes())
    git(repo, "add", ".")
    same_oid = run(repo, "staged", "--format", "json")
    assert same_oid.returncode == 1
    same_payload = json.loads(same_oid.stdout)
    assert any(
        item["control"] == "generated_blob_bytes"
        and item["path"].endswith("same.jsonl")
        for item in same_payload["violations"]
    )

    git(repo, "reset", "--hard", "-q", "HEAD")
    for index in range(5):
        payload = (bytes([65 + index]) * 99 + b"\n") * 1200
        (fixtures / f"{index}.txt").write_bytes(payload)
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "aggregate fixtures")
    generated.mkdir(parents=True)
    for index in range(5):
        (generated / f"{index}.jsonl").write_bytes(
            (fixtures / f"{index}.txt").read_bytes()
        )
    git(repo, "add", ".")
    aggregate = run(repo, "staged", "--format", "json")
    assert aggregate.returncode == 1
    aggregate_payload = json.loads(aggregate.stdout)
    assert aggregate_payload["aggregate_new_blob_bytes"] == 0
    assert aggregate_payload["aggregate_generated_evidence_bytes"] == 600000
    assert any(
        item["control"] == "generated_aggregate_bytes"
        for item in aggregate_payload["violations"]
    )
    policy_path = repo / "testing" / "apg-change-size-policy.json"
    value = json.loads(policy_path.read_text(encoding="utf-8"))
    first_path = "private/evaluations/apg99/0.jsonl"
    first_oid = git(repo, "hash-object", str(repo / first_path))
    value["exceptions"] = [
        {
            "allowed_git_modes": ["100644"],
            "classification": "generated-derived-evidence",
            "exact_blob_oid": first_oid,
            "exact_path": first_path,
            "expiry_condition": "any-exact-binding-change",
            "id": "bounded-generated-fixture",
            "introduced_phase": "APG53",
            "maximum_bytes": 120000,
            "overrides": ["generated_aggregate_bytes"],
            "owner": "testing/apg-change-size-policy.json",
            "reason": "synthetic aggregate exception control",
            "review_condition": "any-binding-policy-rights-or-purpose-change",
            "rights_notice_status": "synthetic-test-fixture",
        }
    ]
    policy_path.write_text(json.dumps(value), encoding="utf-8")
    git(repo, "add", ".")
    accepted = run(repo, "staged", "--format", "json")
    assert accepted.returncode == 0, accepted.stderr
    assert json.loads(accepted.stdout)["exceptions_used"] == [
        "bounded-generated-fixture"
    ]


def test_staged_change_classes_unique_blobs_and_review_impact(tmp_path: Path) -> None:
    repo = initialize(tmp_path)
    (repo / "rename.txt").write_text("rename\n", encoding="utf-8")
    (repo / "mode.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (repo / "delete.txt").write_text("delete\n", encoding="utf-8")
    (repo / "modify.txt").write_text("before\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fixtures")

    git(repo, "mv", "rename.txt", "renamed.txt")
    os.chmod(repo / "mode.sh", 0o755)
    (repo / "delete.txt").unlink()
    (repo / "modify.txt").write_text("after\n", encoding="utf-8")
    (repo / "added.txt").write_text("same blob\n", encoding="utf-8")
    (repo / "duplicate.txt").write_text("same blob\n", encoding="utf-8")
    git(repo, "add", "-A")
    result = run(repo, "staged", "--format", "json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    classes = {item["change_class"] for item in payload["changes"]}
    assert {"add", "delete", "mode", "rename"} <= classes
    added_sizes = [
        item["resulting_blob_bytes"]
        for item in payload["changes"]
        if item["path"] in {"added.txt", "duplicate.txt"}
    ]
    assert sum(added_sizes) > payload["aggregate_new_blob_bytes"]
    assert payload["largest_rewritten_blobs"]


def test_commit_tree_and_malformed_policy_modes(tmp_path: Path) -> None:
    repo = initialize(tmp_path)
    (repo / "source.py").write_text("value = 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "source")
    commit = git(repo, "rev-parse", "HEAD")
    for arguments in (
        ("commit", commit, "--format", "json"),
        ("tree", commit, "--format", "json"),
        ("tree", "--format", "json"),
    ):
        result = run(repo, *arguments)
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["result"] == "pass"

    (repo / "testing" / "apg-change-size-policy.json").write_text(
        '{"schema_version":1,"unknown":true}\n',
        encoding="utf-8",
    )
    git(repo, "add", "testing/apg-change-size-policy.json")
    malformed = run(repo, "staged", "--format", "json")
    assert malformed.returncode == 2
    assert malformed.stdout == ""
    assert "policy error:" in malformed.stderr


def test_root_commit_binary_exception_and_additional_refusals(tmp_path: Path) -> None:
    repo = initialize(tmp_path)
    root_commit = git(repo, "rev-list", "--max-parents=0", "HEAD")
    root = run(repo, "commit", root_commit, "--format", "json")
    assert root.returncode == 0, root.stderr

    asset = repo / "asset.bin"
    asset.write_bytes(b"a\0b")
    oid = git(repo, "hash-object", str(asset))
    value = valid_policy()
    exceptions = value["exceptions"]
    assert isinstance(exceptions, list)
    exceptions.append(
        {
            "allowed_git_modes": ["100644"],
            "classification": "ordinary",
            "exact_blob_oid": oid,
            "exact_path": "asset.bin",
            "expiry_condition": "any-exact-binding-change",
            "id": "asset",
            "introduced_phase": "APG53",
            "maximum_bytes": 3,
            "overrides": ["binary_treatment"],
            "owner": "release/public-surface.json",
            "reason": "synthetic accepted binary control",
            "review_condition": "any-binding-policy-rights-or-purpose-change",
            "rights_notice_status": "synthetic-test-fixture",
        }
    )
    (repo / "testing" / "apg-change-size-policy.json").write_text(
        json.dumps(value), encoding="utf-8"
    )
    git(repo, "add", ".")
    accepted = run(repo, "staged", "--format", "json")
    assert accepted.returncode == 0, accepted.stderr
    assert json.loads(accepted.stdout)["exceptions_used"] == ["asset"]

    git(repo, "reset", "--hard", "-q", "HEAD")
    (repo / "ordinary.txt").write_bytes(b"x" * 262145)
    (repo / "raw.bin").write_bytes(b"a\0b")
    (repo / "pointer.dat").write_bytes(
        b"version https://git-lfs.github.com/spec/v1\n"
    )
    git(repo, "add", ".")
    refused = run(repo, "staged")
    assert refused.returncode == 1
    assert "ordinary_blob_bytes" in refused.stdout
    assert "binary_treatment" in refused.stdout
    assert "lfs_pointer_treatment" in refused.stdout


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("schema_version",), 2),
        (("limits", "maximum_one_line_text_bytes"), 300000),
        (("classification", "archive_treatment"), "allow"),
        (("classification", "binary_treatment"), "allow"),
        (("classification", "lfs_pointer_treatment"), "allow"),
        (("classification", "archive_signatures"), []),
        (("classification", "archive_signatures", 0, "offset"), -1),
        (("classification", "archive_signatures", 0, "offset"), "invalid"),
        (("classification", "archive_signatures", 0, "hex"), ""),
        (("exceptions",), "not-an-array"),
        (("exceptions",), [{"id": "incomplete"}]),
    ],
)
def test_malformed_policy_families_fail_closed(
    tmp_path: Path,
    path: tuple[object, ...],
    replacement: object,
) -> None:
    repo = initialize(tmp_path)
    value = valid_policy()
    owner: object = value
    for component in path[:-1]:
        assert isinstance(owner, (dict, list))
        owner = owner[component]  # type: ignore[index]
    assert isinstance(owner, (dict, list))
    owner[path[-1]] = replacement  # type: ignore[index]
    (repo / "testing" / "apg-change-size-policy.json").write_text(
        json.dumps(value), encoding="utf-8"
    )
    git(repo, "add", "testing/apg-change-size-policy.json")
    result = run(repo, "staged")
    assert result.returncode == 2
    assert "policy error:" in result.stderr


@pytest.mark.parametrize(
    "scenario",
    [
        "empty-string",
        "unsafe-path",
        "bad-oid",
        "bad-mode",
        "bad-override",
        "empty-overrides",
        "bad-owner",
        "bad-id",
        "bad-classification",
        "bad-phase",
        "bad-rights",
        "bad-review",
        "bad-expiry",
        "lfs-override",
        "bad-hex",
        "non-list-signatures",
        "bad-maximum",
        "duplicate-id",
        "duplicate-path",
    ],
)
def test_malformed_exception_and_signature_families_fail_closed(
    tmp_path: Path,
    scenario: str,
) -> None:
    repo = initialize(tmp_path)
    value = valid_policy()
    item = valid_exception()
    if scenario == "empty-string":
        item["reason"] = ""
    elif scenario == "unsafe-path":
        item["exact_path"] = "../asset.bin"
    elif scenario == "bad-oid":
        item["exact_blob_oid"] = "bad"
    elif scenario == "bad-mode":
        item["allowed_git_modes"] = ["bad"]
    elif scenario == "bad-override":
        item["overrides"] = ["unknown"]
    elif scenario == "empty-overrides":
        item["overrides"] = []
    elif scenario == "bad-owner":
        item["owner"] = "../owner"
    elif scenario == "bad-id":
        item["id"] = "INVALID"
    elif scenario == "bad-classification":
        item["classification"] = "binary-asset"
    elif scenario == "bad-phase":
        item["introduced_phase"] = "phase-53"
    elif scenario == "bad-rights":
        item["rights_notice_status"] = "verified"
    elif scenario == "bad-review":
        item["review_condition"] = "identity changes"
    elif scenario == "bad-expiry":
        item["expiry_condition"] = "identity changes"
    elif scenario == "lfs-override":
        item["overrides"] = ["lfs_pointer_treatment"]
    elif scenario == "bad-hex":
        value["classification"]["archive_signatures"][0]["hex"] = "not-hex"  # type: ignore[index]
    elif scenario == "non-list-signatures":
        value["classification"]["archive_signatures"] = "not-a-list"  # type: ignore[index]
    elif scenario == "bad-maximum":
        item["maximum_bytes"] = 0
    if scenario.startswith("duplicate"):
        second = dict(item)
        if scenario == "duplicate-id":
            second["exact_path"] = "other.bin"
        else:
            second["id"] = "other"
        value["exceptions"] = [item, second]
    else:
        value["exceptions"] = [item]
    (repo / "testing" / "apg-change-size-policy.json").write_text(
        json.dumps(value), encoding="utf-8"
    )
    git(repo, "add", "testing/apg-change-size-policy.json")
    result = run(repo, "staged")
    assert result.returncode == 2
    assert "policy error:" in result.stderr


@pytest.mark.parametrize("payload", ["[]", "{not-json"])
def test_nonobject_and_invalid_json_policy_fail_closed(
    tmp_path: Path,
    payload: str,
) -> None:
    repo = initialize(tmp_path)
    (repo / "testing" / "apg-change-size-policy.json").write_text(
        payload, encoding="utf-8"
    )
    git(repo, "add", "testing/apg-change-size-policy.json")
    result = run(repo, "staged")
    assert result.returncode == 2
    assert "policy error:" in result.stderr
