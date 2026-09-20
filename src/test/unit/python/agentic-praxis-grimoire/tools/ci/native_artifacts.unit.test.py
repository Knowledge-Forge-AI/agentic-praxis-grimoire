"""Unit tests for tools/ci/native_artifacts.py (network seam monkeypatched)."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import stat
from typing import Any
import urllib.error
import warnings
import zipfile

import pytest

from tools.ci import native_artifacts as na

REPO = na.EXPECTED_REPO
RUN_ID = "424242"
ARTIFACT_ID = "9001"
NAME = "native-linux-x64"
FILES = {"lane-seal.json": b'{"a":1}\n', "linux-x64/apgr": b"binary-bytes", "linux-x64/go-version-m.txt": b"go1.26.9\n"}


class FakeGitHub:
    """Replacement for the single network seam; records every request."""

    def __init__(self) -> None:
        self.routes: dict[str, Any] = {}
        self.calls: list[tuple[str, dict[str, str]]] = []

    def __call__(self, request: Any) -> io.BytesIO:
        self.calls.append((request.full_url, {k.lower(): v for k, v in request.header_items()}))
        outcome = self.routes.get(request.full_url)
        if outcome is None:
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)
        if isinstance(outcome, BaseException):
            raise outcome
        return io.BytesIO(outcome)


def meta_url(artifact_id: str = ARTIFACT_ID) -> str:
    return f"{na.API_ROOT}/repos/{REPO}/actions/artifacts/{artifact_id}"


def zip_url(artifact_id: str = ARTIFACT_ID) -> str:
    return meta_url(artifact_id) + "/zip"


def digest_of(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def make_zip(files: dict[str, bytes], *, extra: list[tuple[zipfile.ZipInfo, bytes]] = ()) -> bytes:
    buffer = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, data in files.items():
                archive.writestr(name, data)
            for info, data in extra:
                archive.writestr(info, data)
    return buffer.getvalue()


def metadata(data: bytes, **override: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "id": int(ARTIFACT_ID), "name": NAME, "size_in_bytes": len(data), "expired": False,
        "expires_at": "2099-01-01T00:00:00Z", "digest": digest_of(data),
        "workflow_run": {"id": int(RUN_ID), "repository_id": na.EXPECTED_REPO_ID, "head_repository_id": na.EXPECTED_REPO_ID},
    }
    doc.update(override)
    return doc


@pytest.fixture()
def gh(monkeypatch: pytest.MonkeyPatch) -> FakeGitHub:
    fake = FakeGitHub()
    monkeypatch.setattr(na, "_open", fake)
    return fake


@pytest.fixture()
def ctx() -> na.ArtifactContext:
    return na.ArtifactContext(token="read-token-value", run_id=RUN_ID)


def serve(gh: FakeGitHub, archive: bytes, **override: Any) -> None:
    gh.routes[meta_url()] = json.dumps(metadata(archive, **override)).encode()
    gh.routes[zip_url()] = archive


def extracted(tmp_path: Path, files: dict[str, bytes] = FILES) -> Path:
    root = tmp_path / "lane"
    for name, data in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(data)
    return root


def verify(ctx: na.ArtifactContext, tmp_path: Path, archive: bytes, root: Path, **kwargs: Any) -> dict[str, Any]:
    scratch = tmp_path / "scratch"
    scratch.mkdir(exist_ok=True)
    return na.verify_downloaded_artifact(ctx, ARTIFACT_ID, kwargs.pop("digest", digest_of(archive)), NAME, root, scratch=scratch, **kwargs)


def test_context_requires_token_repository_and_run(monkeypatch: pytest.MonkeyPatch) -> None:
    good = {"GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": REPO, "GITHUB_RUN_ID": RUN_ID}
    assert na.context_from_env(good).run_id == RUN_ID
    assert na.context_from_env({**good, "GITHUB_TOKEN": "", "GH_TOKEN": "fallback"}).token == "fallback"
    with pytest.raises(na.ArtifactError, match="read token"):
        na.context_from_env({**good, "GITHUB_TOKEN": ""})
    with pytest.raises(na.ArtifactError, match="GITHUB_REPOSITORY"):
        na.context_from_env({**good, "GITHUB_REPOSITORY": "someone/else"})
    for bad_run in ("", "abc", "0", "12 3"):
        with pytest.raises(na.ArtifactError, match="GITHUB_RUN_ID"):
            na.context_from_env({**good, "GITHUB_RUN_ID": bad_run})


def test_no_token_means_no_network_attempt(gh: FakeGitHub) -> None:
    with pytest.raises(na.ArtifactError):
        na.context_from_env({"GITHUB_REPOSITORY": REPO, "GITHUB_RUN_ID": RUN_ID})
    assert gh.calls == []


def test_metadata_success_sends_bearer_token(gh: FakeGitHub, ctx: na.ArtifactContext) -> None:
    archive = make_zip(FILES)
    serve(gh, archive)
    meta = na.verify_artifact_metadata(ctx, ARTIFACT_ID, digest_of(archive), NAME)
    assert meta["size_in_bytes"] == len(archive)
    url, headers = gh.calls[0]
    assert url == meta_url()
    assert headers["authorization"] == "Bearer read-token-value"


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"workflow_run": {"id": 1, "repository_id": na.EXPECTED_REPO_ID, "head_repository_id": na.EXPECTED_REPO_ID}}, "does not belong to run"),
        ({"workflow_run": None}, "does not belong to run"),
        ({"workflow_run": {"id": int(RUN_ID), "repository_id": 7, "head_repository_id": 7}}, "outside the fixed repository"),
        ({"workflow_run": {"id": int(RUN_ID), "repository_id": na.EXPECTED_REPO_ID, "head_repository_id": 7}}, "outside the fixed repository"),
        ({"expired": True}, "expired"),
        ({"expired": None}, "expired"),
        ({"expires_at": "2001-01-01T00:00:00Z"}, "passed its expiry"),
        ({"expires_at": "not-a-time"}, "expiry timestamp"),
        ({"name": "native-darwin-arm64"}, "name mismatch"),
        ({"id": 12}, "different artifact"),
        ({"digest": "sha256:" + "0" * 64}, "digest changed"),
        ({"digest": None}, "no valid sha256 digest"),
        ({"digest": "md5:abc"}, "no valid sha256 digest"),
        ({"size_in_bytes": 0}, "invalid archive size"),
        ({"size_in_bytes": True}, "invalid archive size"),
    ],
)
def test_metadata_negative_fixtures(gh: FakeGitHub, ctx: na.ArtifactContext, override: dict[str, Any], message: str) -> None:
    archive = make_zip(FILES)
    serve(gh, archive, **override)
    with pytest.raises(na.ArtifactError, match=message):
        na.verify_artifact_metadata(ctx, ARTIFACT_ID, digest_of(archive), NAME, now=datetime(2026, 10, 11, tzinfo=timezone.utc))


def test_metadata_missing_digest_key_is_fatal_not_skipped(gh: FakeGitHub, ctx: na.ArtifactContext) -> None:
    archive = make_zip(FILES)
    doc = metadata(archive)
    del doc["digest"]
    gh.routes[meta_url()] = json.dumps(doc).encode()
    with pytest.raises(na.ArtifactError, match="no valid sha256 digest"):
        na.verify_artifact_metadata(ctx, ARTIFACT_ID, digest_of(archive), NAME)


@pytest.mark.parametrize("body", [b"not json", b"[1, 2]", b"\xff\xfe"])
def test_metadata_malformed_body(gh: FakeGitHub, ctx: na.ArtifactContext, body: bytes) -> None:
    gh.routes[meta_url()] = body
    with pytest.raises(na.ArtifactError, match="malformed|not an object"):
        na.verify_artifact_metadata(ctx, ARTIFACT_ID, "sha256:" + "a" * 64, NAME)


def test_metadata_rejects_bad_expectations_without_network(gh: FakeGitHub, ctx: na.ArtifactContext) -> None:
    for artifact_id, digest, name, message in (
        ("12/../3", "sha256:" + "a" * 64, NAME, "decimal identifier"),
        ("0", "sha256:" + "a" * 64, NAME, "decimal identifier"),
        (ARTIFACT_ID, "", NAME, "sha256"),
        (ARTIFACT_ID, "sha256:" + "A" * 64, NAME, "sha256"),
        (ARTIFACT_ID, "sha256:" + "a" * 64, "", "name is required"),
    ):
        with pytest.raises(na.ArtifactError, match=message):
            na.verify_artifact_metadata(ctx, artifact_id, digest, name)
    assert gh.calls == []


def test_http_error_and_transport_failure_are_fatal(gh: FakeGitHub, ctx: na.ArtifactContext) -> None:
    with pytest.raises(na.ArtifactError, match="HTTP 404"):
        na.verify_artifact_metadata(ctx, ARTIFACT_ID, "sha256:" + "a" * 64, NAME)
    gh.routes[meta_url()] = urllib.error.URLError("dns failure")
    with pytest.raises(na.ArtifactError, match="URLError"):
        na.verify_artifact_metadata(ctx, ARTIFACT_ID, "sha256:" + "a" * 64, NAME)


def test_fetch_refuses_urls_outside_the_fixed_repository(gh: FakeGitHub, ctx: na.ArtifactContext) -> None:
    for url in ("https://api.github.com/repos/other/repo/actions/artifacts/1", "https://evil.example/x", "http://api.github.com/repos/x"):
        with pytest.raises(na.ArtifactError, match="outside the fixed repository"):
            na._fetch(url, ctx, "application/json", 10, lambda chunk: None)
    with pytest.raises(na.ArtifactError, match="outside the fixed repository"):
        na._fetch(meta_url(), na.ArtifactContext(token="t", run_id=RUN_ID, repository="other/repo"), "application/json", 10, lambda chunk: None)
    assert gh.calls == []


def test_download_success_follows_redirect_without_credentials(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path) -> None:
    archive = make_zip(FILES)
    serve(gh, archive)
    blob = "https://blob.example.test/signed?sig=abc"
    gh.routes[zip_url()] = urllib.error.HTTPError(zip_url(), 302, "Found", {"Location": blob}, None)
    gh.routes[blob] = archive
    result = verify(ctx, tmp_path, archive, extracted(tmp_path))
    assert result == {"artifact_id": ARTIFACT_ID, "artifact_digest": digest_of(archive), "name": NAME, "files": 3}
    by_url = dict(gh.calls)
    assert "authorization" in by_url[zip_url()]
    assert "authorization" not in by_url[blob]
    assert not list((tmp_path / "scratch").iterdir())


def test_download_hash_mismatch_is_fatal_even_when_metadata_agrees(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path) -> None:
    archive = make_zip(FILES)
    swapped = make_zip({**FILES, "linux-x64/apgr": b"BINARY-bytes"})
    assert len(swapped) == len(archive)
    serve(gh, archive)
    gh.routes[zip_url()] = swapped
    with pytest.raises(na.ArtifactError, match="archive hash mismatch"):
        verify(ctx, tmp_path, archive, extracted(tmp_path))


def test_download_size_differs_from_metadata(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path) -> None:
    archive = make_zip(FILES)
    serve(gh, archive, size_in_bytes=len(archive) + 5)
    with pytest.raises(na.ArtifactError, match="size differs"):
        verify(ctx, tmp_path, archive, extracted(tmp_path))


def test_download_larger_than_metadata_size_is_cut_off(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path) -> None:
    archive = make_zip(FILES)
    serve(gh, archive, size_in_bytes=len(archive) - 1)
    with pytest.raises(na.ArtifactError, match="exceeds the permitted size"):
        verify(ctx, tmp_path, archive, extracted(tmp_path))


@pytest.mark.parametrize("hops", [["http://insecure.example.test/a"], [""], ["https://a.test/1", "https://a.test/2", "https://a.test/3", "https://a.test/4"]])
def test_download_redirect_policy(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path, hops: list[str]) -> None:
    archive = make_zip(FILES)
    serve(gh, archive)
    previous = zip_url()
    for target in hops:
        gh.routes[previous] = urllib.error.HTTPError(previous, 302, "Found", {"Location": target}, None)
        previous = target
    with pytest.raises(na.ArtifactError, match="redirect"):
        verify(ctx, tmp_path, archive, extracted(tmp_path))


def tree_case(tmp_path: Path, name: str) -> Path:
    root = extracted(tmp_path)
    if name == "extra":
        (root / "stray.txt").write_bytes(b"x")
    elif name == "missing":
        (root / "linux-x64" / "go-version-m.txt").unlink()
    elif name == "changed":
        (root / "linux-x64" / "apgr").write_bytes(b"BINARY-bytes")
    elif name == "symlink-file":
        (root / "linux-x64" / "go-version-m.txt").unlink()
        (root / "linux-x64" / "go-version-m.txt").symlink_to(root / "lane-seal.json")
    elif name == "symlink-dir":
        (root / "alias").symlink_to(root / "linux-x64")
    elif name == "empty-dir":
        (root / "unexpected-empty").mkdir()
    return root


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("extra", "extra=\\['stray.txt'\\]"),
        ("missing", "missing=\\['linux-x64/go-version-m.txt'\\]"),
        ("changed", "differs from archive: linux-x64/apgr"),
        ("symlink-file", "symlink"),
        ("symlink-dir", "symlink"),
        ("empty-dir", "extra_dirs=\\['unexpected-empty'\\]"),
    ],
)
def test_extracted_directory_must_equal_archive(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path, case: str, message: str) -> None:
    archive = make_zip(FILES)
    serve(gh, archive)
    with pytest.raises(na.ArtifactError, match=message):
        verify(ctx, tmp_path, archive, tree_case(tmp_path, case))


def test_extracted_must_be_a_direct_directory(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path) -> None:
    archive = make_zip(FILES)
    serve(gh, archive)
    real = extracted(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(real)
    with pytest.raises(na.ArtifactError, match="direct directory"):
        verify(ctx, tmp_path, archive, alias)


def hostile_zip(name: str) -> bytes:
    link = zipfile.ZipInfo("lane-seal.json")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    special = zipfile.ZipInfo("lane-seal.json")
    special.external_attr = (stat.S_IFIFO | 0o644) << 16
    cases = {
        "traversal": make_zip({"../escape": b"x"}),
        "absolute": make_zip({"/etc/passwd": b"x"}),
        "backslash": make_zip({"a\\b": b"x"}),
        "dotdot-inner": make_zip({"a/../b": b"x"}),
        "link": make_zip({}, extra=[(link, b"target")]),
        "special": make_zip({}, extra=[(special, b"")]),
        "duplicate": make_zip({}, extra=[(zipfile.ZipInfo("dup"), b"1"), (zipfile.ZipInfo("dup"), b"2")]),
    }
    return cases[name]


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("traversal", "unsafe archive member"), ("absolute", "unsafe archive member"), ("backslash", "unsafe archive member"),
        ("dotdot-inner", "unsafe archive member"), ("link", "link or special"), ("special", "link or special"), ("duplicate", "duplicate member"),
    ],
)
def test_hostile_archive_members_are_rejected(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path, case: str, message: str) -> None:
    archive = hostile_zip(case)
    serve(gh, archive)
    with pytest.raises(na.ArtifactError, match=message):
        verify(ctx, tmp_path, archive, extracted(tmp_path))


def test_malformed_archive_bytes(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path) -> None:
    archive = b"this is not a zip archive"
    serve(gh, archive)
    with pytest.raises(na.ArtifactError, match="malformed"):
        verify(ctx, tmp_path, archive, extracted(tmp_path))


def test_archive_directory_entries_must_exist_on_disk(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path) -> None:
    archive = make_zip({**FILES, "kept-empty/": b""})
    serve(gh, archive)
    with pytest.raises(na.ArtifactError, match="missing_dirs=\\['kept-empty'\\]"):
        verify(ctx, tmp_path, archive, extracted(tmp_path))
    (tmp_path / "lane" / "kept-empty").mkdir()
    assert verify(ctx, tmp_path, archive, tmp_path / "lane")["files"] == 3


def test_scratch_must_be_a_direct_directory(gh: FakeGitHub, ctx: na.ArtifactContext, tmp_path: Path) -> None:
    archive = make_zip(FILES)
    serve(gh, archive)
    with pytest.raises(na.ArtifactError, match="scratch"):
        na.verify_downloaded_artifact(ctx, ARTIFACT_ID, digest_of(archive), NAME, extracted(tmp_path), scratch=tmp_path / "absent")
