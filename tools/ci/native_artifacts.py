"""Verified retrieval of GitHub Actions artifacts for APGR native CI.

Every check is mandatory: the artifact must belong to the current workflow run
of the one fixed repository, be unexpired, carry the expected name and
``sha256:`` digest, and its archive bytes (downloaded here with the job's read
token) must hash to that digest.  A directory produced by a download action is
trusted only after each file matches the verified archive member for member.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

API_ROOT = "https://api.github.com"
EXPECTED_REPO = "Knowledge-Forge-AI/agentic-praxis-grimoire"
EXPECTED_REPO_ID = 1306002537
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_RE = re.compile(r"^[1-9][0-9]{0,18}$")
MAX_JSON_BYTES = 1 << 20
MAX_ARCHIVE_BYTES = 4 << 30
CHUNK = 1 << 20
MAX_REDIRECTS = 3
REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
USER_AGENT = "apgr-native-ci"


class ArtifactError(ValueError):
    """Artifact identity, download, or content verification failure."""


@dataclass(frozen=True)
class ArtifactContext:
    token: str
    run_id: str
    repository: str = EXPECTED_REPO


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _open(request: urllib.request.Request) -> Any:
    """Single network seam; the opener never follows redirects on its own."""
    return _OPENER.open(request, timeout=300)


def context_from_env(environ: Mapping[str, str] | None = None) -> ArtifactContext:
    env = os.environ if environ is None else environ
    token = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    if not token:
        raise ArtifactError("a GitHub read token (GITHUB_TOKEN or GH_TOKEN) is required")
    repository = env.get("GITHUB_REPOSITORY")
    if repository != EXPECTED_REPO:
        raise ArtifactError(f"GITHUB_REPOSITORY must be {EXPECTED_REPO}, got: {repository}")
    run_id = env.get("GITHUB_RUN_ID", "")
    if not ID_RE.match(run_id):
        raise ArtifactError("GITHUB_RUN_ID must be the numeric current run identifier")
    return ArtifactContext(token=token, run_id=run_id, repository=repository)


def _fetch(
    url: str, ctx: ArtifactContext, accept: str, limit: int, on_chunk: Callable[[bytes], None]
) -> int:
    """GET one API URL, following bounded HTTPS redirects without credentials."""
    if ctx.repository != EXPECTED_REPO or not url.startswith(f"{API_ROOT}/repos/{ctx.repository}/actions/"):
        raise ArtifactError("refusing to contact a URL outside the fixed repository API")
    headers = {
        "Authorization": f"Bearer {ctx.token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }
    for _ in range(MAX_REDIRECTS + 1):
        try:
            response = _open(urllib.request.Request(url, headers=headers))
        except urllib.error.HTTPError as error:
            if error.code not in REDIRECT_CODES:
                raise ArtifactError(f"GitHub request failed: HTTP {error.code}") from error
            location = error.headers.get("Location") if error.headers is not None else None
            if getattr(error, "fp", None) is not None:
                error.close()
            if not location or not location.startswith("https://"):
                raise ArtifactError("GitHub redirect target is missing or not HTTPS") from error
            url, headers = location, {"User-Agent": USER_AGENT}
            continue
        except (urllib.error.URLError, OSError) as error:
            raise ArtifactError(f"GitHub request failed: {type(error).__name__}") from error
        total = 0
        with response:
            while chunk := response.read(CHUNK):
                total += len(chunk)
                if total > limit:
                    raise ArtifactError("GitHub response exceeds the permitted size")
                on_chunk(chunk)
        return total
    raise ArtifactError("GitHub request exceeded the redirect limit")


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as error:
        raise ArtifactError("artifact expiry timestamp is invalid") from error
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def verify_artifact_metadata(
    ctx: ArtifactContext,
    artifact_id: str,
    expected_digest: str,
    expected_name: str,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Require the exact artifact in the current run; every field is mandatory."""
    if not isinstance(artifact_id, str) or not ID_RE.match(artifact_id):
        raise ArtifactError(f"artifact id must be a decimal identifier: {artifact_id!r}")
    if not isinstance(expected_digest, str) or not DIGEST_RE.match(expected_digest):
        raise ArtifactError(f"artifact digest must be sha256:<64 hex>: {expected_digest!r}")
    if not expected_name:
        raise ArtifactError("expected artifact name is required")
    parts: list[bytes] = []
    _fetch(
        f"{API_ROOT}/repos/{ctx.repository}/actions/artifacts/{artifact_id}",
        ctx, "application/vnd.github+json", MAX_JSON_BYTES, parts.append,
    )
    try:
        meta = json.loads(b"".join(parts).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ArtifactError("artifact metadata is malformed") from error
    if not isinstance(meta, dict):
        raise ArtifactError("artifact metadata is not an object")
    if meta.get("id") != int(artifact_id) or isinstance(meta.get("id"), bool):
        raise ArtifactError(f"artifact metadata names a different artifact: {meta.get('id')!r}")
    if meta.get("name") != expected_name:
        raise ArtifactError(f"artifact name mismatch: {meta.get('name')!r} != {expected_name!r}")
    if meta.get("expired") is not False:
        raise ArtifactError(f"artifact {artifact_id} is expired or lacks an expiry state")
    if _parse_time(meta.get("expires_at")) <= (now or datetime.now(timezone.utc)):
        raise ArtifactError(f"artifact {artifact_id} has passed its expiry time")
    digest = meta.get("digest")
    if not isinstance(digest, str) or not DIGEST_RE.match(digest):
        raise ArtifactError(f"artifact {artifact_id} metadata carries no valid sha256 digest")
    if digest != expected_digest:
        raise ArtifactError(f"artifact {artifact_id} digest changed: {digest} != {expected_digest}")
    run = meta.get("workflow_run")
    if not isinstance(run, dict) or str(run.get("id")) != ctx.run_id:
        raise ArtifactError(f"artifact {artifact_id} does not belong to run {ctx.run_id}")
    if run.get("repository_id") != EXPECTED_REPO_ID or run.get("head_repository_id") != EXPECTED_REPO_ID:
        raise ArtifactError(f"artifact {artifact_id} was produced outside the fixed repository")
    if not _positive_int(meta.get("size_in_bytes")) or meta["size_in_bytes"] > MAX_ARCHIVE_BYTES:
        raise ArtifactError(f"artifact {artifact_id} has an invalid archive size")
    return meta


def _safe_member(name: str) -> str:
    parts = PurePosixPath(name).parts
    if (
        not name or name.startswith("/") or "\\" in name or "\x00" in name
        or (len(name) > 1 and name[0].isalpha() and name[1] == ":")
        or not parts or any(part in ("", ".", "..") for part in parts)
    ):
        raise ArtifactError(f"unsafe archive member path: {name!r}")
    return PurePosixPath(*parts).as_posix()


def _digest_stream(stream: Any) -> tuple[str, int]:
    hasher, size = hashlib.sha256(), 0
    while chunk := stream.read(CHUNK):
        hasher.update(chunk)
        size += len(chunk)
    return hasher.hexdigest(), size


def _archive_members(archive_path: Path) -> tuple[dict[str, tuple[str, int]], set[str]]:
    files: dict[str, tuple[str, int]] = {}
    directories: set[str] = set()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for info in archive.infolist():
                is_dir = info.filename.endswith("/")
                name = _safe_member(info.filename.rstrip("/"))
                kind = stat.S_IFMT((info.external_attr >> 16) & 0xFFFF)
                if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or (is_dir and kind == stat.S_IFREG):
                    raise ArtifactError(f"archive contains a link or special member: {name}")
                if name in files or name in directories:
                    raise ArtifactError(f"archive contains a duplicate member: {name}")
                if is_dir:
                    directories.add(name)
                    continue
                with archive.open(info) as stream:
                    files[name] = _digest_stream(stream)
    except (OSError, zipfile.BadZipFile) as error:
        raise ArtifactError("downloaded artifact archive is malformed") from error
    return files, directories


def _tree_members(root: Path) -> tuple[dict[str, tuple[str, int]], set[str]]:
    files: dict[str, tuple[str, int]] = {}
    directories: set[str] = set()
    for current, dirs, names in os.walk(root, followlinks=False):
        base = Path(current)
        for entry in [*dirs, *names]:
            path = base / entry
            mode = path.lstat().st_mode
            rel = path.relative_to(root).as_posix()
            if stat.S_ISLNK(mode):
                raise ArtifactError(f"extracted directory contains a symlink: {rel}")
            if stat.S_ISDIR(mode):
                directories.add(rel)
            elif stat.S_ISREG(mode):
                with path.open("rb") as stream:
                    files[rel] = _digest_stream(stream)
            else:
                raise ArtifactError(f"extracted directory contains a special file: {rel}")
    return files, directories


def compare_archive_to_directory(archive_path: Path, extracted: Path) -> int:
    """Require the extracted tree to equal the archive: no extra/missing/linked paths."""
    if extracted.is_symlink() or not extracted.is_dir():
        raise ArtifactError(f"extracted artifact must be a direct directory: {extracted}")
    expected_files, expected_dirs = _archive_members(archive_path)
    actual_files, actual_dirs = _tree_members(extracted)
    implied = {str(parent) for name in expected_files for parent in PurePosixPath(name).parents} - {"."}
    for name in expected_files:
        if name in expected_dirs or any(str(p) in expected_files for p in PurePosixPath(name).parents):
            raise ArtifactError(f"archive member collides with a directory: {name}")
    missing = sorted(set(expected_files) - set(actual_files))
    extra = sorted(set(actual_files) - set(expected_files))
    extra_dirs = sorted(actual_dirs - implied - expected_dirs)
    absent_dirs = sorted(expected_dirs - actual_dirs)
    if missing or extra or extra_dirs or absent_dirs:
        raise ArtifactError(
            f"extracted artifact differs from archive: missing={missing}, extra={extra}, "
            f"extra_dirs={extra_dirs}, missing_dirs={absent_dirs}"
        )
    for name, observed in expected_files.items():
        if actual_files[name] != observed:
            raise ArtifactError(f"extracted artifact file differs from archive: {name}")
    return len(expected_files)


def verify_downloaded_artifact(
    ctx: ArtifactContext,
    artifact_id: str,
    expected_digest: str,
    expected_name: str,
    extracted: Path,
    *,
    scratch: Path,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify metadata, hash the real archive bytes, and bind them to ``extracted``."""
    meta = verify_artifact_metadata(ctx, artifact_id, expected_digest, expected_name, now=now)
    if scratch.is_symlink() or not scratch.is_dir():
        raise ArtifactError(f"scratch directory must be a direct directory: {scratch}")
    with tempfile.TemporaryDirectory(prefix="apgr-archive-", dir=scratch) as temporary:
        archive_path = Path(temporary) / "artifact.zip"
        hasher = hashlib.sha256()
        with archive_path.open("xb") as sink:
            def keep(chunk: bytes) -> None:
                hasher.update(chunk)
                sink.write(chunk)

            size = _fetch(
                f"{API_ROOT}/repos/{ctx.repository}/actions/artifacts/{artifact_id}/zip",
                ctx, "application/vnd.github+json", meta["size_in_bytes"], keep,
            )
        if size != meta["size_in_bytes"]:
            raise ArtifactError(f"artifact {artifact_id} archive size differs from its metadata")
        actual = f"sha256:{hasher.hexdigest()}"
        if actual != expected_digest:
            raise ArtifactError(f"artifact {artifact_id} archive hash mismatch: {actual} != {expected_digest}")
        files = compare_archive_to_directory(archive_path, extracted)
    return {"artifact_id": artifact_id, "artifact_digest": actual, "name": expected_name, "files": files}
