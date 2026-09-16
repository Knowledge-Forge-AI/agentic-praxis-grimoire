#!/usr/bin/env python3
"""Dedicated helpers for APG public release staging corrections and validation logging.

Separates linear staging correction verification, untagged candidate construction,
and command execution evidence logging from the primary release policy engine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Callable, NoReturn


def run_checked_command(
    arguments: Sequence[str],
    cwd: Path,
    environment: dict[str, str] | None = None,
    *,
    fail: Callable[[str], NoReturn] | None = None,
) -> None:
    """Run a child command and record stdout/stderr in APG_VALIDATION_OUTPUT_LOG."""
    def _fail(msg: str) -> NoReturn:
        if fail is not None:
            fail(msg)
        import apg_public_release as release
        release.fail(msg)

    try:
        result = subprocess.run(
            list(arguments),
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment or os.environ.copy(),
        )
    except OSError as error:
        executable = Path(arguments[0]).name if arguments else "command"
        _fail(f"configured validation could not run: {executable}: {error.strerror or error}")
    log_var = os.environ.get("APG_VALIDATION_OUTPUT_LOG")
    if log_var:
        log_path = Path(log_var)
        if not log_path.is_absolute():
            _fail("validation output log path must be absolute")
        resolved_log = log_path.resolve()
        forbidden = [cwd.resolve(), Path(__file__).resolve().parents[1]]
        if environment and "APG12_PUBLIC_V01_ROOT" in environment:
            forbidden.append(Path(environment["APG12_PUBLIC_V01_ROOT"]).resolve())
        for root in forbidden:
            if resolved_log == root or root in resolved_log.parents or resolved_log in root.parents:
                _fail(f"validation output log path cannot overlap repository or validation roots: {resolved_log}")
        log_payload = (
            f"--- COMMAND: {' '.join(arguments)} ---\n"
            f"RETURNCODE: {result.returncode}\n"
            f"--- STDOUT ---\n"
            f"{result.stdout.decode('utf-8', 'replace')}\n"
            f"--- STDERR ---\n"
            f"{result.stderr.decode('utf-8', 'replace')}\n"
            f"--- END COMMAND ---\n"
        ).encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(os.fspath(resolved_log), flags, 0o600)
            try:
                offset = 0
                while offset < len(log_payload):
                    offset += os.write(fd, log_payload[offset:])
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError as error:
            _fail(f"could not write validation output log: {error.strerror or error}")
    if result.returncode:
        detail = (result.stderr + result.stdout)[-8192:].decode("utf-8", "replace").strip()
        _fail(f"configured validation failed: {' '.join(arguments)}: {detail}")


def verify_candidate_lineage(
    candidate: Any,
    base: Any,
    version: str,
    *,
    untagged: bool = False,
    allow_staging_correction: bool = False,
    correction_parent: str | None = None,
    correction_subject: str | None = None,
    run_git: Callable[..., Any] | None = None,
    text_git: Callable[..., Any] | None = None,
    fail: Callable[[str], NoReturn] | None = None,
) -> None:
    """Validate commit ancestry, parent constraints, branch, and commit subject."""
    import apg_public_release as release
    _run_git = run_git or release.run_git
    _text_git = text_git or release.text_git
    _fail = fail or release.fail

    if allow_staging_correction:
        if not correction_parent:
            _fail("candidate correction check requires an explicit correction_parent")
        if _run_git(candidate.root, ["merge-base", "--is-ancestor", base.head, "HEAD"], allow_failure=True).returncode != 0:
            _fail("candidate release commit does not have the public base in its ancestry")
        parent_record = _text_git(candidate.root, ["rev-list", "--parents", "-n", "1", "HEAD"]).split()
        if len(parent_record) != 2:
            _fail("candidate correction commit must have exactly one parent")
        if parent_record[1] != correction_parent:
            _fail(f"candidate correction parent mismatch: expected {correction_parent}, got {parent_record[1]}")
        expected_branch = "staging"
        if _text_git(candidate.root, ["branch", "--show-current"]) != expected_branch:
            _fail("candidate is on the wrong release branch")
        actual_subject = _text_git(candidate.root, ["log", "-1", "--format=%s"])
        if correction_subject:
            if actual_subject != correction_subject:
                _fail(f"candidate release subject is incorrect: expected {correction_subject}, got {actual_subject}")
        else:
            if not actual_subject or not actual_subject.strip():
                _fail("candidate release subject is empty")
    else:
        if _text_git(candidate.root, ["rev-parse", "HEAD^"]) != base.head:
            _fail("candidate release commit does not have the public base as sole parent")
        parent_record = _text_git(candidate.root, ["rev-list", "--parents", "-n", "1", "HEAD"]).split()
        if len(parent_record) != 2 or parent_record[1] != base.head:
            _fail("candidate release commit must have exactly one parent equal to the public base")
        if _text_git(candidate.root, ["rev-list", "--count", f"{base.head}..HEAD"]) != "1":
            _fail("candidate history must add exactly one commit after the public base")
        expected_branch = "staging" if untagged else f"release/{version}"
        if _text_git(candidate.root, ["branch", "--show-current"]) != expected_branch:
            _fail("candidate is on the wrong release branch")
        if _text_git(candidate.root, ["log", "-1", "--format=%s"]) != f"Release v{version}":
            _fail("candidate release subject is incorrect")


def build_untagged_candidate(
    source: Any,
    base: Any,
    output: Path,
    version: str,
    *,
    staging_parent: str | None = None,
    subject: str | None = None,
    run_git: Callable[..., Any] | None = None,
    text_git: Callable[..., Any] | None = None,
    fail: Callable[[str], NoReturn] | None = None,
    unsafe: Callable[[str], NoReturn] | None = None,
) -> tuple[str, str]:
    """Build the untagged staging candidate used by the public PR."""
    import apg_public_release as release
    _run_git = run_git or release.run_git
    _text_git = text_git or release.text_git
    _fail = fail or release.fail
    _unsafe = unsafe or release.unsafe

    core = version.split("+", 1)[0].split("-", 1)[0]
    if core not in ("0.11.0", "0.12.0"):
        _unsafe("untagged candidate mode is only available for v0.11.0 and v0.12.0")
    release.validate_repository_separation(source, base)
    release.verify_public_release_lineage(
        base,
        accepted_commit=release.PUBLIC_V01_COMMIT,
        accepted_tree=release.PUBLIC_V01_TREE,
        allow_advanced_head=(core == "0.12.0"),
    )
    policy = release.load_policy(
        source,
        expected_surfaces=release.audited_policy_surfaces(version),
        allow_v07_compatibility=True,
        allow_v08_compatibility=True,
        allow_v09_compatibility=True,
        allow_v010_compatibility=True,
        allow_v011_compatibility=True,
    )
    entries = release.public_candidate_entries(source, version, excluded_prefix=b"private/")
    release.validate_versioned_policy_exclusions(entries, version)
    release.validate_critical(entries, policy)
    release.validate_public_symlinks(source, entries)
    release.validate_output_path(output, source.root, base.root)
    if staging_parent is None:
        if not _run_git(
            base.root,
            ["show-ref", "--verify", "--quiet", "refs/heads/staging"],
            allow_failure=True,
        ).returncode:
            _fail("public base already contains the staging branch")
    else:
        if _run_git(
            base.root,
            ["merge-base", "--is-ancestor", base.head, staging_parent],
            allow_failure=True,
        ).returncode != 0:
            _fail("public base is not an ancestor of staging parent")
    if os.path.lexists(output):
        output.rmdir()
    release.initialize_candidate(output, base)
    if staging_parent is not None:
        for line in _run_git(
            base.root, ["rev-list", "--objects", staging_parent, "--no-object-names"]
        ).stdout.splitlines():
            if line:
                release.import_object(base, output, line.decode("ascii"))
    metadata = _text_git(
        base.root,
        ["show", "-s", "--format=%an%x00%ae%x00%aI", base.head],
    ).split("\x00")
    if len(metadata) != 3:
        _fail("public base release metadata is incomplete")
    release.validate_identity(metadata[0], metadata[1])
    release.validate_date(metadata[2])
    _run_git(output, ["config", "user.name", metadata[0]])
    _run_git(output, ["config", "user.email", metadata[1]])
    for entry in entries:
        release.import_object(source, output, entry.oid)
    with tempfile.NamedTemporaryFile(prefix="apg-public-index-", delete=False) as index_file:
        index_path = Path(index_file.name)
    index_path.unlink()
    try:
        payload = b"".join(
            entry.mode.encode("ascii") + b" " + entry.oid.encode("ascii") + b"\t" + entry.path + b"\0"
            for entry in entries
        )
        environment = {"GIT_INDEX_FILE": str(index_path)}
        _run_git(
            output,
            ["update-index", "-z", "--index-info"],
            input_bytes=payload,
            extra_environment=environment,
        )
        tree = _text_git(output, ["write-tree"], extra_environment=environment)
    finally:
        index_path.unlink(missing_ok=True)
    identity_environment = {
        "GIT_AUTHOR_NAME": metadata[0],
        "GIT_AUTHOR_EMAIL": metadata[1],
        "GIT_AUTHOR_DATE": metadata[2],
        "GIT_COMMITTER_NAME": metadata[0],
        "GIT_COMMITTER_EMAIL": metadata[1],
        "GIT_COMMITTER_DATE": metadata[2],
    }
    commit_parent = staging_parent if staging_parent is not None else base.head
    commit_subject = subject or (f"Release v{version}" if staging_parent is None else f"Release v{version} staging correction")
    commit = _text_git(
        output,
        ["commit-tree", tree, "-p", commit_parent, "-m", commit_subject],
        extra_environment=identity_environment,
    )
    _run_git(output, ["update-ref", "refs/heads/staging", commit])
    _run_git(output, ["symbolic-ref", "HEAD", "refs/heads/staging"])
    _run_git(output, ["reset", "--hard", commit])
    if _run_git(source.root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout:
        _fail("source changed during candidate construction")
    if _run_git(base.root, ["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout:
        _fail("base changed during candidate construction")
    return tree, commit


def check_untagged_candidate(
    source: Any,
    base: Any,
    candidate: Any,
    version: str,
    private_policy: str | None = None,
    *,
    allow_staging_correction: bool = False,
    correction_parent: str | None = None,
    correction_subject: str | None = None,
) -> dict[str, object]:
    """Check an untagged v0.11 candidate on the exact staging branch."""
    import apg_public_release as release
    return release.check_candidate(
        source,
        base,
        candidate,
        version,
        private_policy,
        untagged=True,
        allow_staging_correction=allow_staging_correction,
        correction_parent=correction_parent,
        correction_subject=correction_subject,
    )


def normalise_required_checks(
    required_checks: Mapping[str, str] | Sequence[str],
    *,
    fail: Callable[[str], NoReturn] | None = None,
    unsafe: Callable[[str], NoReturn] | None = None,
) -> dict[str, str]:
    """Return the supplied required-check attestation in a stable form."""
    def _fail(msg: str) -> NoReturn:
        if fail is not None:
            fail(msg)
        import apg_public_release as release
        release.fail(msg)

    def _unsafe(msg: str) -> NoReturn:
        if unsafe is not None:
            unsafe(msg)
        import apg_public_release as release
        release.unsafe(msg)

    if isinstance(required_checks, Mapping):
        items = tuple(required_checks.items())
    elif isinstance(required_checks, str):
        _unsafe("approved required checks must be a sequence of names")
    else:
        items = tuple((name, "success") for name in required_checks)
    if not items:
        _unsafe("at least one approved required check is required")
    result: dict[str, str] = {}
    for name, status in items:
        if not isinstance(name, str) or not name.strip():
            _unsafe("approved required check names must be nonempty strings")
        if not isinstance(status, str) or status != "success":
            _fail(f"approved required check did not succeed: {name}")
        if name in result:
            _unsafe(f"approved required checks contain a duplicate: {name}")
        result[name] = status
    return dict(sorted(result.items()))
