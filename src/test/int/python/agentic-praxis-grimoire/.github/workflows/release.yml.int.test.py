"""Execute the release-asset verification step against a fake GitHub API."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import warnings
import zipfile
from pathlib import Path

import pytest

from src.test.apg_test_support import repository_root

REPOSITORY_ROOT = repository_root(__file__)
NATIVE_JOBS = (
    "native-guard", "native-darwin-arm64", "native-linux-x64", "native-linux-arm64", "native-assemble",
    "native-consumer-darwin-arm64", "native-consumer-linux-x64", "native-consumer-linux-arm64",
    "native-release-scans", "native-release-candidate-gate",
)
PUBLIC_RECEIPT_JOBS = (
    "guard", "static-analysis", "policy", "unit-integration", "closure", "go",
    "codeql-go", "codeql-python", "codeql-javascript-typescript", "codeql-actions",
)
PUBLIC_CHECKS = (
    "guard", "static-analysis", "policy", "unit-integration", "closure", "go", "codeql (go)",
    "codeql (python)", "codeql (javascript-typescript)", "codeql (actions)", "public-pr-gate",
)
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "release.yml"
VERSION = (
    REPOSITORY_ROOT / "src" / "agentic_praxis_grimoire" / "VERSION"
).read_text(encoding="utf-8").strip()
DEFAULT_TAG = f"v{VERSION}"


def _distribution_filenames(version: str) -> tuple[list[str], str, str]:
    wheel_darwin = f"agentic_praxis_grimoire-{version}-py3-none-macosx_11_0_arm64.whl"
    wheel_linux_x64 = f"agentic_praxis_grimoire-{version}-py3-none-manylinux_2_17_x86_64.whl"
    wheel_linux_arm64 = f"agentic_praxis_grimoire-{version}-py3-none-manylinux_2_17_aarch64.whl"
    wheels = [wheel_darwin, wheel_linux_x64, wheel_linux_arm64]
    sdist = f"agentic_praxis_grimoire-{version}.tar.gz"
    npm_tarball = f"knowledge-forge-ai-apgr-{version}.tgz"
    return wheels, sdist, npm_tarball


WHEELS, SDIST, NPM_TARBALL = _distribution_filenames(VERSION)
WHEEL_DARWIN, WHEEL_LINUX_X64, WHEEL_LINUX_ARM64 = WHEELS
EXPECTED_PYTHON_DIST = [*WHEELS, SDIST]
MANIFEST_NAME = "apg-distribution-manifest.json"


def _verification_script() -> str:
    workflow = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    return "\n".join(
        step["run"]
        for step in workflow["jobs"]["publish"]["steps"][:2]
        if "run" in step
    )


def _write_native_zip(path: Path, mutation: str | None) -> None:
    members = {job: {"name": job, "status": "passed", "source_commit": "6" * 40, "source_tree": "f" * 40, "pr_head_sha": "e" * 40, "pr_base_sha": "a" * 40} for job in NATIVE_JOBS[:-1]}
    index: dict[str, object] = {
        "schema": "apgr.native-rc-index/v1",
        "status": "passed",
        "source_commit": "6" * 40,
        "source_tree": "f" * 40,
        "pr_head_sha": "e" * 40,
        "pr_base_sha": "a" * 40,
        "members": members,
        "retention_class": "routine",
        "lane_artifacts": {"fixture": {}},
        "bundle_artifact": {"fixture": {}},
    }
    entries = ["native-rc-index.json"]
    if mutation == "schema":
        index["schema"] = "apgr.native-rc-index/v0"
    elif mutation == "status":
        index["status"] = "failed"
    elif mutation == "member-missing":
        del members["native-assemble"]
    elif mutation == "member-extra":
        members["native-extra"] = "success"
    elif mutation == "member-red":
        members["native-release-scans"]["status"] = "failed"
    elif mutation == "no-members":
        del index["members"]
    elif mutation in {"source_commit", "source_tree", "pr_head_sha", "pr_base_sha"}:
        index[mutation] = "9" * 40
    elif mutation == "legacy-matrix-jobs":
        index["matrix"] = {"status": "passed", "jobs": index.pop("members")}
    elif mutation == "no-index":
        entries = ["matrix-aggregate.json"]
    elif mutation == "extra-member":
        entries.append("payload.bin")
    elif mutation == "duplicate-index":
        entries.append("native-rc-index.json")
    elif mutation is not None:
        raise AssertionError(mutation)
    with warnings.catch_warnings(), zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        warnings.simplefilter("ignore")
        for entry in entries:
            archive.writestr(entry, json.dumps(index, sort_keys=True, separators=(",", ":")) + "\n")


def _fixture(
    tmp_path: Path,
    *,
    native_mutation: str | None = None,
    corrupt_wheel: bool = False,
    corrupt_sdist: bool = False,
    manifest_corrupt_wheel_hash: bool = False,
    manifest_corrupt_version: bool = False,
    manifest_missing_wheel: bool = False,
    tag: str = DEFAULT_TAG,
    fixture_version: str | None = None,
    extra_wheel: bool = False,
    extra_sdist: bool = False,
    universal_wheel: bool = False,
    draft: bool = False,
    prerelease: bool = False,
    omit_asset: bool = False,
    duplicate_asset: bool = False,
    malformed_checksums: bool = False,
    include_non_python_assets: bool = True,
    manifest_source_mismatch: bool = False,
    manifest_pr_source: bool = False,
    aggregate_failed: bool = False,
    omit_receipt: str | None = None,
    aggregate_trailer: str = "",
) -> tuple[Path, Path]:
    active_version = fixture_version if fixture_version is not None else VERSION
    active_wheels, active_sdist, active_npm = _distribution_filenames(active_version)
    active_wheel_darwin = active_wheels[0]

    assets = tmp_path / "assets"
    assets.mkdir()
    asset_map: dict[str, bytes] = {
        active_wheels[0]: b"exact darwin wheel bytes",
        active_wheels[1]: b"exact linux x64 wheel bytes",
        active_wheels[2]: b"exact linux arm64 wheel bytes",
        active_sdist: b"exact normalized sdist bytes",
    }

    digests: dict[str, str] = {}
    for name, content in asset_map.items():
        digests[name] = hashlib.sha256(content).hexdigest()

    if corrupt_wheel:
        digests[active_wheels[0]] = "0" * 64
    if corrupt_sdist:
        digests[active_sdist] = "0" * 64

    wheels_manifest = [
        {"name": active_wheels[0], "sha256": digests[active_wheels[0]]},
        {"name": active_wheels[1], "sha256": digests[active_wheels[1]]},
        {"name": active_wheels[2], "sha256": digests[active_wheels[2]]},
    ]
    if manifest_corrupt_wheel_hash:
        wheels_manifest[0]["sha256"] = "f" * 64
    if manifest_missing_wheel:
        wheels_manifest = wheels_manifest[:2]

    manifest_obj = {
        "schema_version": "apg.distribution-manifest/v1",
        "version": "0.7.0" if manifest_corrupt_version else active_version,
        "python": {
            "package": "agentic-praxis-grimoire",
            "wheels": wheels_manifest,
            "sdist": {
                "name": active_sdist,
                "sha256": digests[active_sdist],
            },
        },
    }
    if active_version in ("0.11.0", "0.12.0", "0.13.0"):
        manifest_obj["source_commit"] = "a" * 40 if manifest_source_mismatch else "b" * 40
        if manifest_pr_source:
            manifest_obj["source_commit"] = "6" * 40  # Native bundle source is the tested PR merge ref.
        manifest_obj["source_tree"] = "e" * 40 if manifest_source_mismatch else "f" * 40

    if include_non_python_assets:
        asset_map[active_npm] = b"exact npm tarball bytes"
        digests[active_npm] = hashlib.sha256(asset_map[active_npm]).hexdigest()
        manifest_bytes = json.dumps(manifest_obj, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        asset_map[MANIFEST_NAME] = manifest_bytes
        digests[MANIFEST_NAME] = hashlib.sha256(manifest_bytes).hexdigest()

    for name, content in asset_map.items():
        (assets / name).write_bytes(content)

    manifest_lines = [f"{digests[name]}  {name}" for name in sorted(asset_map)]
    if malformed_checksums:
        manifest_lines.append(f"{digests[active_sdist]}  {active_sdist}")

    (assets / "SHA256SUMS").write_text(
        "\n".join(manifest_lines) + "\n",
        encoding="ascii",
    )

    receipt_jobs = tuple(job for job in PUBLIC_RECEIPT_JOBS if job != omit_receipt)
    aggregate_members = {
        job: {
            "schema": "apg-matrix-receipt-v1",
            "job": job,
            "status": "failure" if aggregate_failed and job == "policy" else "success",
            "sha": "6" * 40,
            "timestamp": "2026-09-12T00:00:00Z",
            "artifacts": {},
            "pr_head_sha": "e" * 40,
            "pr_base_sha": "a" * 40,
            "workflow_sha256": "1" * 64,
        }
        for job in receipt_jobs
    }
    aggregate = {
        "schema": "apg-matrix-aggregate-v1",
        "timestamp": "2026-09-12T00:00:00Z",
        "success": not aggregate_failed,
        "required_members_count": len(receipt_jobs),
        "verified_members_count": len(receipt_jobs),
        "errors": ["job policy did not succeed: status=failure"] if aggregate_failed else [],
        "members": aggregate_members,
    }
    with zipfile.ZipFile(tmp_path / "aggregate-gate.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "matrix-aggregate.json",
            json.dumps(aggregate, sort_keys=True, separators=(",", ":")) + "\n" + aggregate_trailer,
        )
    _write_native_zip(tmp_path / "native-gate.zip", native_mutation)

    release_assets = [
        {"id": idx + 1, "name": name}
        for idx, name in enumerate(sorted([*asset_map.keys(), "SHA256SUMS"]))
    ]

    if extra_wheel:
        (assets / "unexpected.whl").write_bytes(b"extra wheel")
        release_assets.append({"id": 101, "name": "unexpected.whl"})
    if universal_wheel:
        universal_name = f"agentic_praxis_grimoire-{active_version}-py3-none-any.whl"
        (assets / universal_name).write_bytes(b"universal wheel")
        release_assets.append({"id": 102, "name": universal_name})
    if extra_sdist:
        extra_sdist_name = f"agentic_praxis_grimoire-{active_version}-extra.tar.gz"
        (assets / extra_sdist_name).write_bytes(b"extra sdist")
        release_assets.append({"id": 103, "name": extra_sdist_name})
    if duplicate_asset:
        release_assets.append({"id": 104, "name": active_wheel_darwin})
    if omit_asset:
        # remove one of the required wheels
        release_assets = [a for a in release_assets if a["name"] != active_wheel_darwin]

    event = tmp_path / "event.json"
    event.write_text(
        json.dumps(
            {
                "release": {
                    "id": 84,
                    "tag_name": tag,
                    "draft": draft,
                    "prerelease": prerelease,
                    "assets": release_assets,
                }
            }
        ),
        encoding="utf-8",
    )
    return assets, event


def _run(
    tmp_path: Path,
    *,
    shell_executable: str | Path | None = None,
    corrupt_wheel: bool = False,
    corrupt_sdist: bool = False,
    manifest_corrupt_wheel_hash: bool = False,
    manifest_corrupt_version: bool = False,
    manifest_missing_wheel: bool = False,
    tag: str = DEFAULT_TAG,
    fixture_version: str | None = None,
    extra_wheel: bool = False,
    extra_sdist: bool = False,
    universal_wheel: bool = False,
    draft: bool = False,
    prerelease: bool = False,
    omit_asset: bool = False,
    duplicate_asset: bool = False,
    malformed_checksums: bool = False,
    include_non_python_assets: bool = True,
    approved_review: bool = True,
    review_changed_after_approval: bool = False,
    governance_waiver: str | None = None,
    raw_pr_body: str | None = None,
    workflow_bound: bool = True,
    manifest_source_mismatch: bool = False,
    manifest_pr_source: bool = False,
    aggregate_missing: bool = False,
    aggregate_mismatch: bool = False,
    aggregate_parent_mismatch: bool = False,
    aggregate_failed: bool = False,
    omit_receipt: str | None = None,
    omit_job: str | None = None,
    aggregate_trailer: str = "",
    repository: str = "Knowledge-Forge-AI/agentic-praxis-grimoire",
    native_mutation: str | None = None,
    native_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    assets, event = _fixture(
        tmp_path,
        native_mutation=native_mutation,
        corrupt_wheel=corrupt_wheel,
        corrupt_sdist=corrupt_sdist,
        manifest_corrupt_wheel_hash=manifest_corrupt_wheel_hash,
        manifest_corrupt_version=manifest_corrupt_version,
        manifest_missing_wheel=manifest_missing_wheel,
        tag=tag,
        fixture_version=fixture_version,
        extra_wheel=extra_wheel,
        extra_sdist=extra_sdist,
        universal_wheel=universal_wheel,
        draft=draft,
        prerelease=prerelease,
        omit_asset=omit_asset,
        duplicate_asset=duplicate_asset,
        malformed_checksums=malformed_checksums,
        include_non_python_assets=include_non_python_assets,
        manifest_source_mismatch=manifest_source_mismatch,
        manifest_pr_source=manifest_pr_source,
        aggregate_failed=aggregate_failed,
        omit_receipt=omit_receipt,
        aggregate_trailer=aggregate_trailer,
    )
    commands = tmp_path / "bin"
    commands.mkdir()
    fake = commands / "gh"
    fake.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys

event_path = Path(os.environ["GITHUB_EVENT_PATH"])
event = json.loads(event_path.read_text(encoding="utf-8"))
event_tag = event.get("release", {}).get("tag_name", "v0.13.0")
predecessor_tag = "v0.12.0"
api_path = sys.argv[-1]
accepted_base = "a" * 40
merged_commit = "b" * 40
tag_object = "c" * 40
accepted_tag_object = "d" * 40
pr_head = "e" * 40
tested_sha = "6" * 40
run_id = "123"
native_run_id = "456"
native_mode = os.environ.get("APG_NATIVE_RUN", "")
if api_path.endswith("/git/ref/tags/" + event_tag):
    value = {"object": {"sha": tag_object, "type": "tag"}}
elif api_path.endswith("/git/tags/" + tag_object):
    value = {"object": {"sha": merged_commit, "type": "commit"}}
elif api_path.endswith("/git/ref/tags/" + predecessor_tag):
    value = {"object": {"sha": accepted_tag_object, "type": "tag"}}
elif api_path.endswith("/git/tags/" + accepted_tag_object):
    value = {"object": {"sha": accepted_base, "type": "commit"}}
elif f"/compare/{accepted_base}..." in api_path:
    value = {"status": "ahead", "behind_by": 0}
elif api_path.endswith("/commits/" + merged_commit):
    value = {
        "parents": [{"sha": accepted_base}],
        "commit": {
            "tree": {"sha": "f" * 40},
            "message": f"Release {event_tag}\\n\\nfixture",
        },
    }
elif api_path.endswith("/commits/" + tested_sha):
    value = {
        "parents": [
            {"sha": accepted_base},
            {
                "sha": "9" * 40
                if os.environ.get("APG_AGGREGATE_PARENT_MISMATCH") == "1"
                else pr_head
            },
        ],
        "commit": {
            "tree": {
                "sha": "0" * 40
                if os.environ.get("APG_AGGREGATE_MISMATCH") == "1"
                else "f" * 40
            },
        },
    }
elif api_path.endswith("/commits/" + merged_commit + "/pulls"):
    value = [{
        "number": 42,
        "base": {"ref": "main"},
        "head": {
            "ref": "staging",
            "repo": {"full_name": "Knowledge-Forge-AI/agentic-praxis-grimoire"},
            "sha": pr_head,
        },
        "merged_at": "2026-09-12T00:00:00Z",
        "merge_commit_sha": merged_commit,
    }]
elif api_path.endswith("/pulls/42"):
    value = {
        "number": 42,
        "base": {"ref": "main"},
        "head": {
            "ref": "staging",
            "repo": {"full_name": "Knowledge-Forge-AI/agentic-praxis-grimoire"},
            "sha": pr_head,
        },
        "body": os.environ.get("APG_PR_BODY", ""),
        "merged_at": "2026-09-12T00:00:00Z",
        "merge_commit_sha": merged_commit,
    }
elif api_path.endswith("/pulls/42/reviews"):
    if os.environ.get("APG_APPROVED_REVIEW") != "1":
        value = [[]]
    elif os.environ.get("APG_REVIEW_CHANGED_AFTER_APPROVAL") == "1":
        value = [[
            {
                "id": 1,
                "state": "APPROVED",
                "commit_id": pr_head,
                "user": {"login": "reviewer"},
            },
            {
                "id": 2,
                "state": "CHANGES_REQUESTED",
                "commit_id": pr_head,
                "user": {"login": "reviewer"},
            },
        ]]
    else:
        value = [[{
            "id": 1,
            "state": "APPROVED",
            "commit_id": pr_head,
            "user": {"login": "reviewer"},
        }]]
elif "/actions/runs?" in api_path:
    runs = [{
        "id": int(run_id),
        "path": ".github/workflows/public-pr.yml" if os.environ.get("APG_WORKFLOW_BOUND") == "1" else ".github/workflows/other.yml",
        "event": "pull_request",
        "status": "completed",
        "conclusion": "success",
        "head_branch": "staging",
        "head_sha": pr_head,
        "head_repository": {"full_name": "Knowledge-Forge-AI/agentic-praxis-grimoire"},
        "pull_requests": [{"number": 42}],
        "updated_at": "2026-09-12T00:00:00Z",
    }]
    if native_mode != "missing":
        runs.append({
            "id": int(native_run_id),
            "path": ".github/workflows/other.yml" if native_mode == "unbound" else ".github/workflows/native-qualification.yml",
            "event": "pull_request",
            "status": "in_progress" if native_mode == "in-progress" else "completed",
            "conclusion": "failure" if native_mode == "red" else (None if native_mode == "in-progress" else "success"),
            "head_branch": "staging",
            "head_sha": "9" * 40 if native_mode == "other-head" else pr_head,
            "head_repository": {"full_name": "Knowledge-Forge-AI/agentic-praxis-grimoire"},
            "pull_requests": [{"number": 42}],
            "updated_at": "2026-09-12T00:00:01Z",
        })
    value = [{"total_count": len(runs), "workflow_runs": runs}]
elif "/actions/runs/" + native_run_id + "/jobs?" in api_path:
    names = [n for n in json.loads(os.environ["APG_NATIVE_JOB_NAMES"]) if n != os.environ.get("APG_NATIVE_OMIT_JOB")]
    names += [n for n in (os.environ.get("APG_NATIVE_EXTRA_JOB"), os.environ.get("APG_NATIVE_DUP_JOB")) if n]
    states = dict(item.split("=", 1) for item in os.environ.get("APG_NATIVE_JOB_STATE", "").split(";") if item)
    value = [{"total_count": len(names), "jobs": [
        {
            "name": name,
            "head_sha": "9" * 40 if name == os.environ.get("APG_NATIVE_WRONG_HEAD_JOB") else pr_head,
            "status": "completed",
            "conclusion": states.get(name, "success"),
            "completed_at": "2026-09-12T00:00:00Z",
        }
        for name in names
    ]}]
elif "/actions/runs/" + native_run_id + "/artifacts?" in api_path:
    native_zip = Path(os.environ["APG_NATIVE_ZIP"])
    mode = os.environ.get("APG_NATIVE_ARTIFACT", "")
    artifact = {
        "id": 888,
        "name": "native-release-candidate-gate-result",
        "size_in_bytes": 0 if mode == "empty" else native_zip.stat().st_size,
        "expired": mode == "expired",
        "digest": "sha256:" + hashlib.sha256(b"tampered" if mode == "tamper" else native_zip.read_bytes()).hexdigest(),
        "workflow_run": {"id": int(native_run_id), "head_branch": "staging", "head_sha": pr_head},
    }
    if mode == "no-digest":
        del artifact["digest"]
    if mode == "malformed-digest":
        artifact["digest"] = "md5:" + "0" * 32
    artifacts = [] if mode == "missing" else [artifact]
    if mode == "duplicate":
        artifacts.append(dict(artifact, id=889))
    value = [{"total_count": len(artifacts), "artifacts": artifacts}]
elif "/actions/artifacts/888/zip" in api_path:
    with Path(os.environ["APG_NATIVE_ZIP"]).open("rb") as source:
        shutil.copyfileobj(source, sys.stdout.buffer)
    raise SystemExit(0)
elif "/actions/runs/" + run_id + "/jobs?" in api_path:
    names = json.loads(os.environ["APG_PUBLIC_JOB_NAMES"])
    names = [name for name in names if name != os.environ.get("APG_OMIT_JOB")]
    value = [{"total_count": len(names), "jobs": [
        {
            "name": name,
            "head_sha": pr_head,
            "status": "completed",
            "conclusion": "success",
            "completed_at": "2026-09-12T00:00:00Z",
        }
        for name in names
    ]}]
elif "/actions/runs/" + run_id + "/artifacts?" in api_path:
    aggregate = Path(os.environ["APG_AGGREGATE_ZIP"])
    artifacts = [] if os.environ.get("APG_AGGREGATE_MISSING") == "1" else [{
        "id": 777,
        "name": "public-pr-gate-result",
        "size_in_bytes": aggregate.stat().st_size,
        "expired": False,
        "digest": "sha256:" + hashlib.sha256(aggregate.read_bytes()).hexdigest(),
        "workflow_run": {"id": int(run_id), "head_branch": "staging", "head_sha": pr_head},
    }]
    value = [{"total_count": len(artifacts), "artifacts": artifacts}]
elif "/actions/artifacts/777/zip" in api_path:
    with Path(os.environ["APG_AGGREGATE_ZIP"]).open("rb") as source:
        shutil.copyfileobj(source, sys.stdout.buffer)
    raise SystemExit(0)
else:
    asset_id = int(api_path.rsplit("/", 1)[-1])
    name = next(a["name"] for a in event["release"]["assets"] if a["id"] == asset_id)
    with (Path(os.environ["APG_FAKE_ASSETS"]) / name).open("rb") as source:
        shutil.copyfileobj(source, sys.stdout.buffer)
    raise SystemExit(0)
print(json.dumps(value), end="")
""",
        encoding="utf-8",
    )
    fake.chmod(0o700)
    environment = {
        "APG_FAKE_ASSETS": os.fspath(assets),
        "GH_TOKEN": "bounded-test-token",
        "APG_APPROVED_REVIEW": "1" if approved_review else "0",
        "APG_REVIEW_CHANGED_AFTER_APPROVAL": "1" if review_changed_after_approval else "0",
        "APG_PR_BODY": (
            raw_pr_body
            if raw_pr_body is not None
            else (f"<!-- BEGIN_GOVERNANCE_WAIVER -->\n{governance_waiver}\n<!-- END_GOVERNANCE_WAIVER -->" if governance_waiver else "")
        ),
        "APG_WORKFLOW_BOUND": "1" if workflow_bound else "0",
        "APG_AGGREGATE_MISSING": "1" if aggregate_missing else "0",
        "APG_AGGREGATE_MISMATCH": "1" if aggregate_mismatch else "0",
        "APG_AGGREGATE_PARENT_MISMATCH": "1" if aggregate_parent_mismatch else "0",
        "APG_AGGREGATE_ZIP": os.fspath(tmp_path / "aggregate-gate.zip"),
        "APG_OMIT_JOB": omit_job or "",
        "APG_PUBLIC_JOB_NAMES": json.dumps(PUBLIC_CHECKS),
        "APG_NATIVE_JOB_NAMES": json.dumps(NATIVE_JOBS),
        "APG_NATIVE_ZIP": os.fspath(tmp_path / "native-gate.zip"),
        "GITHUB_EVENT_PATH": os.fspath(event),
        "GITHUB_REPOSITORY": repository,
        "RUNNER_TEMP": os.fspath(tmp_path),
        "PATH": os.fspath(commands) + os.pathsep + os.environ["PATH"],
        **(native_env or {}),
    }
    if shell_executable is not None:
        target_shell = str(shell_executable)
    else:
        bash_bin = os.environ.get("APG_BASH")
        if not bash_bin or not os.access(bash_bin, os.X_OK):
            bash_bin = "bash"
        target_shell = bash_bin
    return subprocess.run(
        [target_shell, "-c", _verification_script()],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_verification_step_fails_closed_under_non_bash_shell(
    tmp_path: Path,
) -> None:
    sh_bin = Path("/bin/sh")
    if not sh_bin.is_file() or not os.access(sh_bin, os.X_OK):
        pytest.skip("/bin/sh is not available on this platform")

    # Negative test: /bin/sh lacks process substitution < <(...) and must fail
    # closed with a syntax error when provided the complete fixture environment.
    sh_root = tmp_path / "sh_test"
    sh_root.mkdir()
    result = _run(sh_root, shell_executable=sh_bin)
    assert result.returncode != 0
    assert "syntax error" in result.stderr.lower()
    assert "<" in result.stderr

    # Control test: ensure a valid shell passes with the same fixture.
    control_root = tmp_path / "control"
    control_root.mkdir()
    system_bash = Path("/bin/bash")
    control_shell = str(system_bash) if system_bash.is_file() else None
    control_result = _run(control_root, shell_executable=control_shell)
    assert control_result.returncode == 0, control_result.stderr


def test_verification_step_succeeds_under_macos_system_bash(
    tmp_path: Path,
) -> None:
    system_bash = Path("/bin/bash")
    if not system_bash.is_file() or not os.access(system_bash, os.X_OK):
        pytest.skip("/bin/bash is not available on this platform")

    marker = tmp_path / "selected_shell.marker"
    wrapper = tmp_path / "system_bash_wrapper.sh"
    wrapper.write_text(
        f"#!/bin/sh\n"
        f"version=$(\"{system_bash}\" --version | head -n 1)\n"
        f"echo \"{system_bash} $version\" > \"{marker}\"\n"
        f"exec \"{system_bash}\" \"$@\"\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o700)

    result = _run(tmp_path, shell_executable=wrapper)
    assert result.returncode == 0, result.stderr
    assert marker.is_file()
    marker_content = marker.read_text(encoding="utf-8").strip()
    assert marker_content.startswith(str(system_bash))
    assert "gnu bash" in marker_content.lower() or "version" in marker_content.lower()

    verified = tmp_path / "verified-dist"
    assert sorted(path.name for path in verified.iterdir()) == sorted(EXPECTED_PYTHON_DIST)
    assert (verified / WHEEL_DARWIN).read_bytes() == b"exact darwin wheel bytes"
    assert (verified / WHEEL_LINUX_X64).read_bytes() == b"exact linux x64 wheel bytes"
    assert (verified / WHEEL_LINUX_ARM64).read_bytes() == b"exact linux arm64 wheel bytes"
    assert (verified / SDIST).read_bytes() == b"exact normalized sdist bytes"
    assert sorted(path.name for path in (tmp_path / "manifests").iterdir()) == [
        "SHA256SUMS",
        "apg-distribution-manifest.json",
    ]
    assert (tmp_path / "aggregate-gate" / "matrix-aggregate.json").is_file()


def test_verification_step_selects_the_exact_checked_distribution_paths(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    verified = tmp_path / "verified-dist"
    assert sorted(path.name for path in verified.iterdir()) == sorted(EXPECTED_PYTHON_DIST)
    assert (verified / WHEEL_DARWIN).read_bytes() == b"exact darwin wheel bytes"
    assert (verified / WHEEL_LINUX_X64).read_bytes() == b"exact linux x64 wheel bytes"
    assert (verified / WHEEL_LINUX_ARM64).read_bytes() == b"exact linux arm64 wheel bytes"
    assert (verified / SDIST).read_bytes() == b"exact normalized sdist bytes"
    assert sorted(path.name for path in (tmp_path / "manifests").iterdir()) == [
        "SHA256SUMS",
        "apg-distribution-manifest.json",
    ]
    assert (tmp_path / "aggregate-gate" / "matrix-aggregate.json").is_file()


def test_verification_step_stops_on_wheel_checksum_mismatch(tmp_path: Path) -> None:
    result = _run(tmp_path, corrupt_wheel=True)

    assert result.returncode != 0


def test_verification_step_stops_on_sdist_checksum_mismatch(tmp_path: Path) -> None:
    result = _run(tmp_path, corrupt_sdist=True)

    assert result.returncode != 0


def test_verification_step_stops_on_manifest_wheel_hash_mismatch(tmp_path: Path) -> None:
    result = _run(tmp_path, manifest_corrupt_wheel_hash=True)

    assert result.returncode != 0


def test_verification_step_stops_on_manifest_version_mismatch(tmp_path: Path) -> None:
    result = _run(tmp_path, manifest_corrupt_version=True)

    assert result.returncode != 0


def test_verification_step_stops_on_manifest_missing_wheel(tmp_path: Path) -> None:
    result = _run(tmp_path, manifest_missing_wheel=True)

    assert result.returncode != 0


def test_verification_step_requires_current_approved_review(tmp_path: Path) -> None:
    result = _run(tmp_path, approved_review=False)

    assert result.returncode != 0


def test_verification_step_rejects_a_later_changes_requested_review(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, review_changed_after_approval=True)

    assert result.returncode != 0


def test_verification_step_accepts_governance_waiver_when_approved_review_absent(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        approved_review=False,
        governance_waiver="Manager authorization per ADR 0068 / Scope D",
    )

    assert result.returncode == 0


def test_verification_step_rejects_unbounded_governance_waiver(
    tmp_path: Path,
) -> None:
    result = _run(
        tmp_path,
        approved_review=False,
        raw_pr_body="Governance Waiver: Manager authorization per ADR 0068 / Scope D",
    )

    assert result.returncode != 0


def test_verification_step_requires_public_pr_workflow_check_provenance(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, workflow_bound=False)

    assert result.returncode != 0


def test_verification_step_requires_the_aggregate_gate_artifact(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, aggregate_missing=True)

    assert result.returncode != 0


def test_verification_step_binds_aggregate_candidate_tree_to_merged_tree(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, aggregate_mismatch=True)

    assert result.returncode != 0


def test_verification_step_requires_base_and_pr_head_candidate_parents(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, aggregate_parent_mismatch=True)

    assert result.returncode != 0


def test_verification_step_rejects_a_failed_aggregate_gate(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, aggregate_failed=True)

    assert result.returncode != 0


def test_verification_step_binds_manifest_to_observed_merged_source(
    tmp_path: Path,
) -> None:
    result = _run(tmp_path, manifest_source_mismatch=True)

    assert result.returncode != 0


def test_pr_native_bundle_cannot_satisfy_squash_publication_until_reconciled(tmp_path: Path) -> None:
    result = _run(tmp_path, manifest_pr_source=True)
    assert result.returncode != 0
    assert (tmp_path / "native-gate" / "native-rc-index.json").is_file()
    manifest = json.loads((tmp_path / "manifests" / MANIFEST_NAME).read_text())
    assert manifest["source_commit"] == "6" * 40
    assert "v0.13 provenance blocked" in json.loads(WORKFLOW.read_text())["name"]


# These historical rejection cases assume monotonically increasing releases;
# restoring one as VERSION requires revisiting the corresponding negative.
@pytest.mark.parametrize(
    "arguments",
    (
        {"tag": "v0.6.0"},
        {"tag": "v0.7.1"},
        {"tag": "v0.8.1"},
        {"tag": "v0.9.0"},
        {"tag": "v0.10.0"},
        {"fixture_version": "0.9.0"},
        {"fixture_version": "0.9.0", "tag": "v0.9.0"},
        {"fixture_version": "0.10.0"},
        {"fixture_version": "0.10.0", "tag": "v0.10.0"},
        {"extra_wheel": True},
        {"universal_wheel": True},
        {"extra_sdist": True},
        {"draft": True},
        {"prerelease": True},
        {"omit_asset": True},
        {"duplicate_asset": True},
        {"malformed_checksums": True},
        {"repository": "unexpected/example"},
    ),
)
def test_verification_step_rejects_unexpected_release_identity(
    tmp_path: Path, arguments: dict[str, object]
) -> None:
    result = _run(tmp_path, **arguments)

    assert result.returncode != 0


@pytest.mark.parametrize("job", PUBLIC_CHECKS)
def test_verification_step_requires_every_reduced_public_check(tmp_path: Path, job: str) -> None:
    result = _run(tmp_path, omit_job=job)

    assert result.returncode != 0
    assert f"required PR job did not succeed: {job}" in result.stderr


@pytest.mark.parametrize("receipt", PUBLIC_RECEIPT_JOBS)
def test_verification_step_requires_every_public_matrix_receipt(tmp_path: Path, receipt: str) -> None:
    result = _run(tmp_path, omit_receipt=receipt)

    assert result.returncode != 0
    assert "aggregate gate receipt is missing" in result.stderr


def test_release_verifies_native_gate_evidence_for_the_same_pr_head_and_merge_tree(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    index = json.loads((tmp_path / "native-gate" / "native-rc-index.json").read_text(encoding="utf-8"))
    assert index["schema"] == "apgr.native-rc-index/v1" and index["status"] == "passed"
    assert len(index["members"]) == 9


def test_release_rejects_legacy_matrix_jobs_member_shape(tmp_path: Path) -> None:
    result = _run(tmp_path, native_mutation="legacy-matrix-jobs")

    assert result.returncode != 0
    assert "native gate index is not bound" in result.stderr


@pytest.mark.parametrize("mode", ("missing", "unbound", "red", "other-head", "in-progress"))
def test_release_requires_one_successful_native_run_bound_to_the_pr_head(tmp_path: Path, mode: str) -> None:
    result = _run(tmp_path, native_env={"APG_NATIVE_RUN": mode})

    assert result.returncode != 0


@pytest.mark.parametrize("state", ("failure", "skipped", "cancelled"))
@pytest.mark.parametrize("job", NATIVE_JOBS)
def test_release_rejects_any_non_successful_native_job(tmp_path: Path, job: str, state: str) -> None:
    result = _run(tmp_path, native_env={"APG_NATIVE_JOB_STATE": f"{job}={state}"})

    assert result.returncode != 0
    assert f"required native job did not succeed: {job}" in result.stderr


@pytest.mark.parametrize("variable, value", (
    ("APG_NATIVE_OMIT_JOB", "native-assemble"),
    ("APG_NATIVE_EXTRA_JOB", "native-extra"),
    ("APG_NATIVE_DUP_JOB", "native-assemble"),
    ("APG_NATIVE_DUP_JOB", "native-release-candidate-gate"),
))
def test_release_requires_the_exact_native_job_set_without_duplicates(
    tmp_path: Path, variable: str, value: str
) -> None:
    result = _run(tmp_path, native_env={variable: value})

    assert result.returncode != 0
    assert "native workflow job set is not exact" in result.stderr


def test_release_rejects_native_jobs_from_another_head(tmp_path: Path) -> None:
    result = _run(tmp_path, native_env={"APG_NATIVE_WRONG_HEAD_JOB": "native-guard"})

    assert result.returncode != 0
    assert "required native job did not succeed: native-guard" in result.stderr


@pytest.mark.parametrize("mode, message", (
    ("missing", "absent or ambiguous"),
    ("duplicate", "absent or ambiguous"),
    ("expired", "absent or ambiguous"),
    ("empty", "native gate artifact is empty"),
    ("malformed-digest", "native gate artifact digest is malformed"),
    ("tamper", "native gate artifact digest mismatch"),
    ("no-digest", ""),
))
def test_release_requires_the_native_gate_artifact_to_match_its_cryptographic_digest(
    tmp_path: Path, mode: str, message: str
) -> None:
    result = _run(tmp_path, native_env={"APG_NATIVE_ARTIFACT": mode})

    assert result.returncode != 0
    assert message in result.stderr


@pytest.mark.parametrize("mutation", (
    "schema", "status", "member-missing", "member-extra", "member-red", "no-members",
    "source_commit", "source_tree", "pr_head_sha", "pr_base_sha",
))
def test_release_rejects_a_tampered_native_rc_index(tmp_path: Path, mutation: str) -> None:
    result = _run(tmp_path, native_mutation=mutation)

    assert result.returncode != 0
    assert "native gate index is not bound to expected commit/tree/head/base" in result.stderr


@pytest.mark.parametrize("mutation, message", (
    ("no-index", "must contain exactly one native-rc-index.json"),
    ("duplicate-index", "must contain exactly one native-rc-index.json"),
        ("extra-member", "native gate artifact must contain exactly one index"),
))
def test_release_requires_exactly_one_native_rc_index_in_the_gate_zip(
    tmp_path: Path, mutation: str, message: str
) -> None:
    result = _run(tmp_path, native_mutation=mutation)

    assert result.returncode != 0
    assert message in result.stderr


def test_release_never_falls_back_to_building_locally() -> None:
    script = _verification_script()

    for token in ("go build", "go test", "nix build", "npm ci", "pip install", "gh workflow run"):
        assert token not in script


def test_workflow_receipt_set_matches_public_pr_matrix_members() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "matrix_receipts_for_release", REPOSITORY_ROOT / "release/ci/matrix_receipts.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run = json.loads(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["publish"]["steps"][1]["run"]
    line = next(item for item in run.splitlines() if item.startswith("required_receipts="))
    assert set(json.loads(line.split("=", 1)[1].strip("'"))) == module.DEFAULT_MEMBER_JOBS
    assert "expected_tag=v0.13.0" in run and "/git/ref/tags/v0.12.0" in run


def test_verification_accepts_only_the_exact_matrix_success_trailer(tmp_path: Path) -> None:
    # public-pr-gate redirects `matrix_receipts.py verify`, which prints JSON and
    # then "PASSED: matrix completeness verified", into the aggregate artifact.
    (tmp_path / "passed").mkdir()
    (tmp_path / "other").mkdir()
    accepted = _run(tmp_path / "passed", aggregate_trailer="PASSED: matrix completeness verified\n")
    assert accepted.returncode == 0, accepted.stderr
    refused = _run(tmp_path / "other", aggregate_trailer="PASSED: something else\n")
    assert refused.returncode != 0
    assert "unexpected aggregate trailer" in refused.stderr


def test_aggregate_artifact_zip_is_requested_with_the_rest_api_media_type() -> None:
    run = json.loads(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["publish"]["steps"][1]["run"]
    assert ("gh api -H 'Accept: application/vnd.github+json' "
            '"/repos/$GITHUB_REPOSITORY/actions/artifacts/$aggregate_artifact_id/zip"') in run
    assert list(json.loads(WORKFLOW.read_text(encoding="utf-8"))["on"]) == ["release"]
