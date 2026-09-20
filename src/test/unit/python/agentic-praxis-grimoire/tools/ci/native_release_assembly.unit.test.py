"""Unit tests for tools/ci/native_release_assembly.py.

GitHub is replaced at the single network seam of ``native_artifacts``.  Most
tests substitute recording packagers (fake bytes); one test drives the real
canonical packagers over synthetic Go binaries.  No Go, Nix or Node is used.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
from types import SimpleNamespace
from typing import Any, Callable
import urllib.error
import zipfile
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[7] / "libexec"))
import apg_go_build as go_build
import apg_go_buildinfo as buildinfo

from tools.ci import native_artifacts as na
from tools.ci import native_release_assembly as assembly
from tools.ci.native_seal import (
    CANONICAL_TARGETS,
    REQUIRED_LANES,
    SealError,
    build_lane_seal,
    canonical_json,
    sha256_file,
    verify_bundle_seal,
    verify_scan_receipt,
)

COMMIT, TREE, HEAD, BASE = "a" * 40, "b" * 40, "c" * 40, "d" * 40
RUN_ID = "777"
GO_SLUGS = ("darwin-arm64", "linux-amd64", "linux-arm64")
PY_NAMES = (
    "agentic_praxis_grimoire-0.13.0-py3-none-macosx_11_0_arm64.whl",
    "agentic_praxis_grimoire-0.13.0-py3-none-manylinux_2_17_aarch64.whl",
    "agentic_praxis_grimoire-0.13.0-py3-none-manylinux_2_17_x86_64.whl",
    "agentic_praxis_grimoire-0.13.0.tar.gz",
)
NPM_NAMES = (
    "knowledge-forge-ai-apgr-0.13.0.tgz",
    "knowledge-forge-ai-apgr-darwin-arm64-0.13.0.tgz",
    "knowledge-forge-ai-apgr-linux-arm64-0.13.0.tgz",
    "knowledge-forge-ai-apgr-linux-x64-0.13.0.tgz",
)


class FakeGitHub:
    def __init__(self) -> None:
        self.routes: dict[str, Any] = {}
        self.calls: list[str] = []

    def __call__(self, request: Any) -> io.BytesIO:
        self.calls.append(request.full_url)
        outcome = self.routes.get(request.full_url)
        if outcome is None:
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)
        return io.BytesIO(outcome)


def artifact_url(artifact_id: str, suffix: str = "") -> str:
    return f"{na.API_ROOT}/repos/{na.EXPECTED_REPO}/actions/artifacts/{artifact_id}{suffix}"


def digest_of(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def zip_dir(root: Path) -> bytes:
    """Deterministic archive: fixed timestamps, so re-zipping an unchanged tree gives equal bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                info = zipfile.ZipInfo(path.relative_to(root).as_posix(), date_time=(2020, 1, 1, 0, 0, 0))
                info.external_attr = 0o644 << 16
                archive.writestr(info, path.read_bytes())
    return buffer.getvalue()


def recorded_text(target: str, go_version: str, arch: str | None = None) -> str:
    goos, goarch = target.split("/")
    return (
        f"/lane/apgr: {go_version}\n\tpath\t{go_build.MODULE}/cmd/apgr\n\tmod\t{go_build.MODULE}\t(devel)\t\n"
        f"\tbuild\t-buildvcs=false\n\tbuild\t-trimpath=true\n\tbuild\tCGO_ENABLED=0\n"
        f"\tbuild\tGOARCH={arch or goarch}\n\tbuild\tGOOS={goos}\n"
    )


def write_lane(root: Path, lane: str, *, nested: bool, commit: str = COMMIT, tree: str = TREE, go_version: str = "go1.26.9",
               recorded_arch: str | None = None, nix: dict[str, Any] | None = None, drop_nix: tuple[str, ...] = ()) -> tuple[Path, dict[str, Any]]:
    spec = CANONICAL_TARGETS[lane]
    lane_root = root / lane
    files = lane_root / spec["slug"] if nested else lane_root
    files.mkdir(parents=True)
    target = spec["target"]
    version, corpus = go_build.identities(assembly.ROOT)
    binary = buildinfo.make_synthetic_binary(target=target, go_version=go_version, format_type="macho" if target.startswith("darwin") else "elf")
    (files / "apgr").write_bytes(binary)
    (files / "apgr").chmod(0o755)
    manifest = go_build._manifest(target=target, version=version, corpus=corpus, binary=binary)
    (files / "apgr.binary-manifest.json").write_bytes(go_build.render_manifest(manifest))
    (files / "go-version-m.txt").write_text(recorded_text(target, go_version, recorded_arch), encoding="utf-8")
    evidence = {"schema_version": assembly.NIX_EVIDENCE_SCHEMA, "lane": lane, "target": target,
                "compiler_version": "go1.26.9", "status": "passed", "native_execution": True, **(nix or {})}
    for key in drop_nix:
        del evidence[key]
    (files / "nix-evidence.json").write_bytes(canonical_json(evidence))
    evidence.update({"profile_removed": True,
                     "store_smoke": {"controller_generation": {"reason": "installed_immutable_runtime"}},
                     "profile_smoke": {"controller_generation": {"reason": "installed_immutable_runtime"}}})
    (files / "nix-evidence.json").write_bytes(canonical_json(evidence))
    (files / "nix-compiler-identity.txt").write_text("go1.26.9\n")
    (files / "go-tests.log").write_text("native tests/vet/race fixture\n")
    os.environ.update(RUNNER_OS="macOS" if target.startswith("darwin") else "Linux",
                      RUNNER_ARCH="X64" if target.endswith("amd64") else "ARM64",
                      ImageOS="fixture", ImageVersion="fixture")
    return lane_root, build_lane_seal(lane, target, spec["slug"], commit, tree, files)


def serve(gh: FakeGitHub, artifact_id: str, artifact_name: str, data: bytes, **override: Any) -> None:
    doc = {
        "id": int(artifact_id), "name": artifact_name, "size_in_bytes": len(data), "expired": False,
        "expires_at": "2099-01-01T00:00:00Z", "digest": digest_of(data),
        "workflow_run": {"id": int(RUN_ID), "repository_id": na.EXPECTED_REPO_ID, "head_repository_id": na.EXPECTED_REPO_ID},
        **override,
    }
    gh.routes[artifact_url(artifact_id)] = json.dumps(doc).encode()
    gh.routes[artifact_url(artifact_id, "/zip")] = data


def make_world(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch, lane_options: dict[str, dict[str, Any]] | None = None) -> SimpleNamespace:
    lanes = tmp_path / "lanes"
    lanes.mkdir()
    inputs: dict[str, dict[str, str]] = {}
    seals: dict[str, Any] = {}
    for index, lane in enumerate(REQUIRED_LANES, start=1):
        lane_root, seal = write_lane(lanes, lane, nested=lane == "native-linux-x64", **(lane_options or {}).get(lane, {}))
        data = zip_dir(lane_root)
        artifact_id = str(100 + index)
        serve(gh, artifact_id, lane, data)
        inputs[lane] = {"seal_sha256": seal["seal_sha256"], "artifact_id": artifact_id, "artifact_digest": digest_of(data)}
        seals[lane] = seal
    monkeypatch.setenv("NATIVE_INPUTS_JSON", json.dumps(inputs))
    return SimpleNamespace(lanes=lanes, inputs=inputs, seals=seals, out=tmp_path / "bundle-out", tmp=tmp_path)


class Spies:
    """Recording stand-ins for the three canonical packagers (fake bytes)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.npm_drift = False
        self.python_status = "ok"
        self.identity = (COMMIT, TREE)

    @property
    def names(self) -> list[str]:
        return [call[0] for call in self.calls]

    def prebuilt(self, source: Path, artifact_root: Path, output: Path, work_root: Path) -> dict[str, Any]:
        self.calls.append(("prebuilt", (source, artifact_root, output, work_root), {}))
        for slug in GO_SLUGS:
            for name in ("apgr", "apgr.binary-manifest.json", "go-version-m.txt"):
                assert (artifact_root / slug / name).is_file()
        assert os.access(artifact_root / "linux-amd64" / "apgr", os.X_OK)
        assert not output.exists() and work_root.is_dir() and not any(work_root.iterdir())
        output.mkdir(mode=0o700)
        for name in PY_NAMES:
            (output / name).write_bytes(f"py:{name}".encode())
        (output / "SHA256SUMS").write_bytes(b"python-only-sums\n")
        return {"status": self.python_status}

    def npm(self, source_root: Path, artifact_root: Path, output: Path, *, artifacts: Any = None, work_root: Path | None = None) -> tuple[()]:
        ordinal = self.names.count("npm")
        self.calls.append(("npm", (source_root, artifact_root, output), {"work_root": work_root, "artifacts": artifacts}))
        output.mkdir(parents=True)
        for name in NPM_NAMES:
            suffix = "-drift" if self.npm_drift and ordinal == 1 else ""
            (output / name).write_bytes(f"npm:{name}{suffix}".encode())
        return ()

    def build(self, source_root: Path, go: Path, python: Path, npm_dir: Path, output: Path) -> dict[str, Any]:
        self.calls.append(("candidate.build", (source_root, go, python, npm_dir, output), {}))
        output.mkdir()
        manifest = output / assembly.candidate.MANIFEST_NAME
        manifest.write_bytes(b'{"schema_version":"apg.distribution-manifest/v1"}\n')
        rows = {f"go/{slug}/{name}": sha256_file(go / slug / name) for slug in GO_SLUGS for name in ("apgr", "apgr.binary-manifest.json")}
        rows.update({f"python/{p.name}": sha256_file(p) for p in python.iterdir() if p.name != "SHA256SUMS"})
        rows.update({f"npm/{p.name}": sha256_file(p) for p in npm_dir.iterdir()})
        rows[manifest.name] = sha256_file(manifest)
        (output / "SHA256SUMS").write_text("".join(f"{digest}  {name}\n" for name, digest in sorted(rows.items())), encoding="ascii")
        return {"source_commit": self.identity[0], "source_tree": self.identity[1]}

    def check(self, manifest_path: Path, source_root: Path, go: Path, python: Path, npm_dir: Path) -> dict[str, Any]:
        self.calls.append(("candidate.check", (manifest_path, source_root, go, python, npm_dir), {}))
        assert manifest_path.is_file() and go.is_dir() and python.is_dir() and npm_dir.is_dir()
        return {}

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(assembly.prebuilt, "build_prebuilt_bundle", self.prebuilt)
        monkeypatch.setattr(assembly.npm, "build_packages", self.npm)
        monkeypatch.setattr(assembly.candidate, "build", self.build)
        monkeypatch.setattr(assembly.candidate, "check", self.check)


@pytest.fixture(autouse=True)
def hermetic(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("GITHUB_WORKSPACE", "GITHUB_OUTPUT", "APGR_ALLOW_WORKSPACE_OUTPUT", "GH_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    for key, value in (("SOURCE_COMMIT", COMMIT), ("SOURCE_TREE", TREE), ("PR_HEAD_SHA", HEAD), ("PR_BASE_SHA", BASE),
                       ("GITHUB_TOKEN", "read-token"), ("GITHUB_REPOSITORY", na.EXPECTED_REPO), ("GITHUB_RUN_ID", RUN_ID)):
        monkeypatch.setenv(key, value)

    def refuse(*_args: Any, **_kwargs: Any) -> None:
        pytest.fail("a process was spawned during assembly")

    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(os, "system", refuse)


@pytest.fixture()
def gh(monkeypatch: pytest.MonkeyPatch) -> FakeGitHub:
    fake = FakeGitHub()
    monkeypatch.setattr(na, "_open", fake)
    return fake


@pytest.fixture()
def spies(monkeypatch: pytest.MonkeyPatch) -> Spies:
    recorder = Spies()
    recorder.install(monkeypatch)
    return recorder


def leftovers(tmp_path: Path) -> list[str]:
    return [p.name for p in tmp_path.iterdir() if p.name.startswith(".apgr-assemble-")]


@pytest.fixture()
def assembled(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    world = make_world(tmp_path, gh, monkeypatch)
    world.seal = assembly.run_assemble(world.lanes, world.out)
    data = zip_dir(world.out)
    serve(gh, "104", assembly.BUNDLE_ARTIFACT_NAME, data)
    monkeypatch.setenv("NATIVE_BUNDLE_JSON", json.dumps({"artifact_id": "104", "artifact_digest": digest_of(data),
                                                       "seal_sha256": world.seal["bundle_seal_sha256"]}))
    return world


# --------------------------------------------------------------------------- assemble


def test_module_cannot_spawn_processes_or_name_go() -> None:
    tree = ast.parse(Path(assembly.__file__).read_text(encoding="utf-8"))
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert "subprocess" not in imported
    source = Path(assembly.__file__).read_text(encoding="utf-8")
    assert "shutil.which" not in source and "os.system" not in source


def test_assemble_calls_canonical_packagers_in_order(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    gh_output = tmp_path / "github-output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(gh_output))
    world = make_world(tmp_path, gh, monkeypatch)
    seal = assembly.run_assemble(world.lanes, world.out)

    assert spies.names == ["prebuilt", "npm", "npm", "candidate.build", "candidate.check", "candidate.check"]
    prebuilt_call, npm_a, npm_b, build_call, stage_check, export_check = spies.calls
    assert prebuilt_call[1][0] == assembly.ROOT
    assert [p.name for p in prebuilt_call[1][1:]] == ["go", "python", "py-work"]
    assert [npm_a[1][2].name, npm_b[1][2].name] == ["npm-a", "npm-b"]
    assert npm_a[1][1] == npm_b[1][1] and npm_a[2]["work_root"] == npm_b[2]["work_root"] and npm_a[2]["work_root"].name == "npm-work"
    assert [p.name for p in build_call[1][1:]] == ["go", "python", "npm-a", "candidate"]
    assert stage_check[1][0].parent.name == "candidate" and stage_check[1][3].name == "python"
    assert export_check[1][0].parent.name == "bundle" and [p.name for p in export_check[1][2:]] == ["go", "python", "npm"]

    files = sorted(p.relative_to(world.out).as_posix() for p in world.out.rglob("*") if p.is_file())
    assert len(files) == assembly.BUNDLE_FILE_COUNT + 1
    assert "release-bundle-seal.json" in files and not any(name.endswith("go-version-m.txt") for name in files)
    assert [f for f in files if f.startswith("go/")] == [f"go/{slug}/{n}" for slug in GO_SLUGS for n in ("apgr", "apgr.binary-manifest.json")]
    assert all(os.access(world.out / f"go/{slug}/apgr", os.X_OK) for slug in GO_SLUGS)
    assert verify_bundle_seal(world.out)["bundle_seal_sha256"] == seal["bundle_seal_sha256"]
    assert seal["lane_seals"] == {lane: world.seals[lane]["seal_sha256"] for lane in REQUIRED_LANES}
    assert seal["source_commit"] == COMMIT and seal["source_tree"] == TREE
    assert gh_output.read_text(encoding="utf-8") == f"bundle_seal_sha256={seal['bundle_seal_sha256']}\n"
    assert leftovers(tmp_path) == []
    assert len(gh.calls) == 6  # metadata + archive per lane; nothing else


@pytest.mark.parametrize("kind", ["directory", "file", "symlink"])
def test_preexisting_output_is_never_accepted(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    if kind == "directory":
        world.out.mkdir()
    elif kind == "file":
        world.out.write_bytes(b"x")
    else:
        world.out.symlink_to(tmp_path)
    with pytest.raises(assembly.AssemblyError, match="must not already exist"):
        assembly.run_assemble(world.lanes, world.out)
    assert spies.calls == [] and gh.calls == []


def test_python_packager_failure_status_is_fatal_and_cleans_up(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    spies.python_status = "failed"
    world = make_world(tmp_path, gh, monkeypatch)
    with pytest.raises(assembly.AssemblyError, match="did not report success"):
        assembly.run_assemble(world.lanes, world.out)
    assert not world.out.exists() and leftovers(tmp_path) == []


def test_npm_ab_divergence_is_fatal(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    spies.npm_drift = True
    world = make_world(tmp_path, gh, monkeypatch)
    with pytest.raises(assembly.AssemblyError, match="npm A/B builds are not byte-identical"):
        assembly.run_assemble(world.lanes, world.out)
    assert "candidate.build" not in spies.names and not world.out.exists()


@pytest.mark.parametrize("identity", [("e" * 40, TREE), (COMMIT, "f" * 40), ("", "")])
def test_manifest_source_identity_must_match(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch, identity: tuple[str, str]) -> None:
    spies.identity = identity
    world = make_world(tmp_path, gh, monkeypatch)
    with pytest.raises(assembly.AssemblyError, match="source identity differs"):
        assembly.run_assemble(world.lanes, world.out)
    assert not world.out.exists()


@pytest.mark.parametrize(
    "raw",
    [
        None, "", "not json", "[]", '{"native-darwin-arm64": {}}',
        '{"native-darwin-arm64":{"seal_sha256":"%s","artifact_id":"1","artifact_digest":"sha256:%s"},"native-darwin-arm64":{}}' % ("a" * 64, "a" * 64),
    ],
)
def test_input_document_shape_is_enforced(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch, raw: str | None) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    if raw is None:
        monkeypatch.delenv("NATIVE_INPUTS_JSON")
    else:
        monkeypatch.setenv("NATIVE_INPUTS_JSON", raw)
    with pytest.raises(assembly.AssemblyError):
        assembly.run_assemble(world.lanes, world.out)
    assert spies.calls == []


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda inputs: inputs.pop("native-linux-arm64"), "exactly the three native lanes"),
        (lambda inputs: inputs.update({"native-extra": dict(inputs["native-linux-arm64"])}), "exactly the three native lanes"),
        (lambda inputs: inputs["native-linux-arm64"].pop("artifact_digest"), "must carry exactly"),
        (lambda inputs: inputs["native-linux-arm64"].update({"extra": "x"}), "must carry exactly"),
        (lambda inputs: inputs["native-linux-arm64"].update({"seal_sha256": "xyz"}), "seal_sha256 is malformed"),
        (lambda inputs: inputs["native-linux-arm64"].update({"artifact_id": "0"}), "artifact_id is malformed"),
        (lambda inputs: inputs["native-linux-arm64"].update({"artifact_digest": ""}), "artifact_digest is malformed"),
        (lambda inputs: inputs["native-linux-arm64"].update({"artifact_digest": "a" * 64}), "artifact_digest is malformed"),
        (lambda inputs: inputs["native-linux-arm64"].update({"artifact_id": 7}), "must be strings"),
    ],
)
def test_input_field_negatives_make_no_network_call(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch,
                                                    edit: Callable[[dict[str, Any]], Any], message: str) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    inputs = copy.deepcopy(world.inputs)
    edit(inputs)
    monkeypatch.setenv("NATIVE_INPUTS_JSON", json.dumps(inputs))
    with pytest.raises(assembly.AssemblyError, match=message):
        assembly.run_assemble(world.lanes, world.out)
    assert gh.calls == [] and spies.calls == []


@pytest.mark.parametrize("variable", ["SOURCE_COMMIT", "SOURCE_TREE", "PR_HEAD_SHA", "PR_BASE_SHA"])
@pytest.mark.parametrize("value", [None, "abc", "A" * 40])
def test_source_and_pr_identity_are_mandatory(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch, variable: str, value: str | None) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    if value is None:
        monkeypatch.delenv(variable)
    else:
        monkeypatch.setenv(variable, value)
    with pytest.raises(assembly.AssemblyError, match=f"{variable} must be"):
        assembly.run_assemble(world.lanes, world.out)
    assert gh.calls == []


def test_lane_seal_must_match_native_inputs(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    inputs = copy.deepcopy(world.inputs)
    inputs["native-darwin-arm64"]["seal_sha256"] = "0" * 64
    monkeypatch.setenv("NATIVE_INPUTS_JSON", json.dumps(inputs))
    with pytest.raises(assembly.AssemblyError, match="seal differs from NATIVE_INPUTS_JSON"):
        assembly.run_assemble(world.lanes, world.out)
    assert spies.calls == []


@pytest.mark.parametrize(
    ("options", "message"),
    [
        ({"commit": "e" * 40}, "source commit differs"),
        ({"tree": "e" * 40}, "source tree differs"),
        ({"go_version": "go1.25.10"}, "binary build info failed validation"),
        ({"recorded_arch": "wrongarch"}, "binary build info failed validation"),
        ({"nix": {"native_execution": False}}, "does not prove native"),
        ({"drop_nix": ("native_execution",)}, "does not prove native"),
        ({"nix": {"compiler_version": "go1.25.10"}}, "does not prove native"),
        ({"nix": {"status": "failed"}}, "does not prove native"),
        ({"nix": {"target": "linux/riscv64"}}, "does not prove native"),
    ],
)
def test_lane_content_negatives(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch, options: dict[str, Any], message: str) -> None:
    world = make_world(tmp_path, gh, monkeypatch, lane_options={"native-linux-arm64": options})
    with pytest.raises(assembly.AssemblyError, match=message):
        assembly.run_assemble(world.lanes, world.out)
    assert spies.calls == [] and leftovers(tmp_path) == []


def test_wrong_architecture_binary_is_rejected(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    # An amd64 binary sealed (and archived) as the arm64 lane's payload.
    donor = world.lanes / "native-linux-x64" / "linux-x64" / "apgr"
    victim_dir = world.lanes / "native-linux-arm64"
    (victim_dir / "apgr").write_bytes(donor.read_bytes())
    seal = build_lane_seal("native-linux-arm64", "linux/arm64", "linux-arm64", COMMIT, TREE, victim_dir)
    data = zip_dir(victim_dir)
    serve(gh, "103", "native-linux-arm64", data)
    inputs = copy.deepcopy(world.inputs)
    inputs["native-linux-arm64"].update({"seal_sha256": seal["seal_sha256"], "artifact_digest": digest_of(data)})
    monkeypatch.setenv("NATIVE_INPUTS_JSON", json.dumps(inputs))
    with pytest.raises(assembly.AssemblyError, match="binary build info failed validation"):
        assembly.run_assemble(world.lanes, world.out)


@pytest.mark.parametrize("case", ["both", "neither", "nested-with-sibling"])
def test_lane_layout_must_be_unambiguous(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    root = world.lanes / "native-linux-x64"
    if case == "both":
        (root / "lane-seal.json").write_bytes((root / "linux-x64" / "lane-seal.json").read_bytes())
    elif case == "neither":
        (root / "linux-x64" / "lane-seal.json").unlink()
    else:
        (root / "stray.txt").write_bytes(b"x")
    serve(gh, "102", "native-linux-x64", zip_dir(root))
    inputs = copy.deepcopy(world.inputs)
    inputs["native-linux-x64"]["artifact_digest"] = digest_of(zip_dir(root))
    monkeypatch.setenv("NATIVE_INPUTS_JSON", json.dumps(inputs))
    with pytest.raises(assembly.AssemblyError, match="exactly one lane-seal.json|unexpected entries"):
        assembly.run_assemble(world.lanes, world.out)
    assert spies.calls == []


def test_missing_downloaded_lane_directory(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    for path in sorted((world.lanes / "native-darwin-arm64").iterdir()):
        path.unlink()
    (world.lanes / "native-darwin-arm64").rmdir()
    with pytest.raises(SealError, match="unavailable"):
        assembly.run_assemble(world.lanes, world.out)


# ----- network and archive negatives (the real native_artifacts code, fake transport)


def test_missing_token_fails_before_any_network_or_packaging(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    monkeypatch.delenv("GITHUB_TOKEN")
    with pytest.raises(na.ArtifactError, match="read token"):
        assembly.run_assemble(world.lanes, world.out)
    assert gh.calls == [] and spies.calls == []


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"workflow_run": {"id": 1, "repository_id": na.EXPECTED_REPO_ID, "head_repository_id": na.EXPECTED_REPO_ID}}, "does not belong to run"),
        ({"workflow_run": {"id": int(RUN_ID), "repository_id": 5, "head_repository_id": 5}}, "outside the fixed repository"),
        ({"expired": True}, "expired"),
        ({"name": "native-linux-x64"}, "name mismatch"),
        ({"digest": "sha256:" + "0" * 64}, "digest changed"),
        ({"digest": None}, "no valid sha256 digest"),
    ],
)
def test_github_identity_negatives(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch,
                                   override: dict[str, Any], message: str) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    genuine = gh.routes[artifact_url("101", "/zip")]
    assert zip_dir(world.lanes / "native-darwin-arm64") == genuine  # re-zipping is deterministic
    serve(gh, "101", "native-darwin-arm64", genuine, **override)
    with pytest.raises(na.ArtifactError, match=message):
        assembly.run_assemble(world.lanes, world.out)
    assert spies.calls == []


def test_archive_bytes_must_hash_to_the_input_digest(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    genuine = gh.routes[artifact_url("101", "/zip")]
    forged = genuine[:-1] + bytes([genuine[-1] ^ 1])
    gh.routes[artifact_url("101", "/zip")] = forged  # metadata still advertises the genuine digest
    with pytest.raises(na.ArtifactError, match="archive hash mismatch"):
        assembly.run_assemble(world.lanes, world.out)
    assert spies.calls == []


def test_downloaded_directory_must_match_the_verified_archive(tmp_path: Path, gh: FakeGitHub, spies: Spies, monkeypatch: pytest.MonkeyPatch) -> None:
    world = make_world(tmp_path, gh, monkeypatch)
    (world.lanes / "native-darwin-arm64" / "apgr").write_bytes(b"swapped after download")
    with pytest.raises(na.ArtifactError, match="differs from archive"):
        assembly.run_assemble(world.lanes, world.out)
    (world.lanes / "native-darwin-arm64" / "apgr").write_bytes(b"x")
    (world.lanes / "native-darwin-arm64" / "extra").write_bytes(b"x")
    with pytest.raises(na.ArtifactError, match="extra="):
        assembly.run_assemble(world.lanes, world.out)
    assert spies.calls == []


# --------------------------------------------------------------------------- export + check-scan


def test_downloaded_bundle_is_verified_before_packaged_execution(assembled, gh):
    gh.calls.clear()
    seal = assembly.verify_downloaded_bundle(assembled.out, assembled.tmp)
    assert seal == assembled.seal
    assert gh.calls == [artifact_url("104"), artifact_url("104", "/zip")]
    (assembled.out / "npm" / NPM_NAMES[0]).write_bytes(b"substituted")
    with pytest.raises(na.ArtifactError, match="differs from archive"):
        assembly.verify_downloaded_bundle(assembled.out, assembled.tmp)


@pytest.mark.parametrize("raw", ["", "[]", "{}", '{"artifact_id":"1","artifact_id":"2"}',
                                   '{"artifact_id":"0","artifact_digest":"bad","seal_sha256":"bad"}'])
def test_bundle_binding_is_mandatory_and_strict(monkeypatch, raw):
    monkeypatch.setenv("NATIVE_BUNDLE_JSON", raw)
    with pytest.raises(assembly.AssemblyError):
        assembly.parse_bundle_input()


@pytest.mark.parametrize("command", ["export", "check"])
def test_scan_steps_refuse_a_different_expected_bundle(scans_world, monkeypatch, command):
    binding = json.loads(os.environ["NATIVE_BUNDLE_JSON"])
    binding["seal_sha256"] = "0" * 64
    monkeypatch.setenv("NATIVE_BUNDLE_JSON", json.dumps(binding))
    write_scan(scans_world.scans, scans_world.doc)
    with pytest.raises(SealError, match="seal"):
        if command == "export":
            assembly.export_scan_input(scans_world.out, scans_world.scan_out)
        else:
            assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)
    assert not scans_world.scan_out.exists()


def classify(name: str) -> tuple[str, str | None]:
    specs = list(CANONICAL_TARGETS.values())
    if name.startswith("go/"):
        return "go-binary", next(s["target"] for s in specs if s["go_binary"] == name)
    if name.endswith(".whl"):
        return "python-wheel", next(s["target"] for s in specs if s["python_tag"] in name)
    if name.endswith(".tar.gz"):
        return "python-sdist", None
    for spec in specs:
        if spec["npm_slug"] in name:
            return "npm-platform", spec["target"]
    return "npm-launcher", None


def evidence(scans: Path, folder: str, label: str, **extra: Any) -> dict[str, Any]:
    (scans / folder).mkdir(parents=True, exist_ok=True)
    sbom_bytes, grype_bytes = f"sbom {label}".encode(), f"grype {label}".encode()
    (scans / folder / "sbom.syft.json").write_bytes(sbom_bytes)
    (scans / folder / "grype.json").write_bytes(grype_bytes)
    sbom_sha = hashlib.sha256(sbom_bytes).hexdigest()
    return {
        "sbom": {"path": f"{folder}/sbom.syft.json", "sha256": sbom_sha, "package_count": 4, "required_types": [], "missing_types": [],
                 "coverage_status": "passed", "syft_returncode": 0, **extra},
        "grype": {"path": f"{folder}/grype.json", "sha256": hashlib.sha256(grype_bytes).hexdigest(), "input_sbom_sha256": sbom_sha,
                  "match_count": 0, "severity_counts": {}, "blocking_severities": [], "returncode": 0, "status": "passed", **extra},
    }


def build_scan(scans: Path, assets: dict[str, Any]) -> dict[str, Any]:
    policy = assembly._scan_policy()
    go_sha = {name: spec["sha256"] for name, spec in assets.items() if name.startswith("go/")}
    records = []
    for name, spec in sorted(assets.items()):
        kind, platform = classify(name)
        rid = re.sub(r"[^a-z0-9]+", "-", name.lower())
        record: dict[str, Any] = {"id": rid, "kind": kind, "target": name, "target_sha256": spec["sha256"], "target_platform": platform,
                                  "status": "passed", **evidence(scans, f"artifacts/{rid}", name)}
        if kind in ("python-wheel", "npm-platform"):
            record["embedded_binary"] = {"path": "bin/apgr", "sha256": go_sha[f"go/{platform.replace('/', '-')}/apgr"], "matches": True}
        if kind == "python-sdist":
            record["derived_install"] = {
                "installation": {"installer": {"status": "passed", "returncode": 0}}, "source_archive_sha256": spec["sha256"],
                **evidence(scans, f"artifacts/{rid}/derived-install", name + " derived", source_archive_sha256=spec["sha256"]),
            }
            record["coverage_union"] = {"status": "passed", "missing_types": [], "covered_types": ["python"], "required_types": ["python"]}
        records.append(record)
    (scans / "conditional-runtime").mkdir()
    (scans / "conditional-runtime" / "receipt.json").write_bytes(b"{}")
    return {
        "schema": "apg-sbom-scan-v1",
        "status": "passed",
        "source": {"target": ".", "status": "passed", **evidence(scans, "source", "source")},
        "artifacts": records,
        "conditional_dependency": {
            "id": "conditional-python-runtime", "kind": "conditional-dependency", "target": "conditional-runtime/python-3.10", "status": "passed",
            "view": {"target_python": "3.10", "download": {"status": "passed"}, "installation": {"status": "passed"}},
            "receipt": {"path": "conditional-runtime/receipt.json", "sha256": hashlib.sha256(b"{}").hexdigest()},
            **evidence(scans, "conditional-runtime/python-3.10", "conditional"),
        },
        "scanner": {"syft": {"version": policy["syft"], "binary_sha256": "1" * 64}, "grype": {"version": policy["grype"], "binary_sha256": "2" * 64}},
        "database": {"valid": True, "update_check": "command-observed", "update": {"status": "passed"}, "database_sha256": "3" * 64,
                     "age_hours": 3.5, "max_age_hours": policy["max_age"]},
        "policy": {"grype_fail_on": "high", "custom_ignores": [], "catalogers": "all", "lower_severities_retained": True,
                   "empty_or_unsupported_inventory_is_clean": False},
        "summary": {"artifact_count": 11, "conditional_dependency_count": 1, "sbom_count": 14, "conditional_sbom_count": 1, "grype_count": 14,
                    "conditional_grype_count": 1, "coverage_gaps": [], "policy_findings": [], "tool_failures": [], "severity_counts": {"low": 2},
                    "status": "passed"},
    }


def write_scan(scans: Path, doc: dict[str, Any]) -> None:
    (scans / "scan-results.json").write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@pytest.fixture()
def scans_world(assembled: SimpleNamespace) -> SimpleNamespace:
    scans = assembled.tmp / "scans"
    scans.mkdir()
    assembled.scans = scans
    assembled.doc = build_scan(scans, assembled.seal["assets"])
    assembled.scan_out = assembled.tmp / "scan-out"
    return assembled


def rec(doc: dict[str, Any], fragment: str) -> dict[str, Any]:
    return next(r for r in doc["artifacts"] if fragment in r["target"])


def test_export_scan_input_is_exactly_the_scanner_file_set(assembled: SimpleNamespace) -> None:
    target = assembled.tmp / "scan-input"
    names = assembly.export_scan_input(assembled.out, target)
    on_disk = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
    assert on_disk == sorted(names) and len(names) == assembly.BUNDLE_FILE_COUNT
    assert "release-bundle-seal.json" not in on_disk
    assert all(os.access(target / f"go/{slug}/apgr", os.X_OK) for slug in GO_SLUGS)
    with pytest.raises(assembly.AssemblyError, match="must not already exist"):
        assembly.export_scan_input(assembled.out, target)


@pytest.mark.parametrize("victim", ["SHA256SUMS", "apg-distribution-manifest.json", "go/linux-amd64/apgr.binary-manifest.json", "npm/" + NPM_NAMES[0]])
def test_export_detects_bundle_tampering(assembled: SimpleNamespace, victim: str) -> None:
    with (assembled.out / victim).open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises((assembly.AssemblyError, SealError)):
        assembly.export_scan_input(assembled.out, assembled.tmp / "scan-input")
    assert not (assembled.tmp / "scan-input").exists()


def test_check_scan_accepts_the_complete_strict_document(scans_world: SimpleNamespace) -> None:
    write_scan(scans_world.scans, scans_world.doc)
    receipt = assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)
    assert receipt["asset_count"] == 11 and receipt["scan_count"] == 14 and receipt["status"] == "passed"
    assert receipt["bundle_seal_sha256"] == scans_world.seal["bundle_seal_sha256"]
    assert receipt["scans_digest"] == sha256_file(scans_world.scan_out / "scan-results.json")
    assert verify_scan_receipt(scans_world.scan_out / "scan-receipt.json", expected_bundle_seal=receipt["bundle_seal_sha256"])["status"] == "passed"
    assert (scans_world.scan_out / "scan-results.json").read_bytes() == (scans_world.scans / "scan-results.json").read_bytes()
    with pytest.raises(assembly.AssemblyError, match="already exists"):
        assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)


def _set(path: tuple[str, ...], value: Any) -> Callable[[dict[str, Any]], None]:
    def apply(doc: dict[str, Any]) -> None:
        node: Any = doc
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
    return apply


def _in_record(fragment: str, *path: str, value: Any = None, delete: bool = False) -> Callable[[dict[str, Any]], None]:
    def apply(doc: dict[str, Any]) -> None:
        node = rec(doc, fragment)
        for key in path[:-1]:
            node = node[key]
        if delete:
            del node[path[-1]]
        else:
            node[path[-1]] = value
    return apply


def _pop_artifact(doc: dict[str, Any]) -> None:
    doc["artifacts"].pop()


def _duplicate_artifact(doc: dict[str, Any]) -> None:
    doc["artifacts"][1] = copy.deepcopy(doc["artifacts"][0])


def _drop_summary(doc: dict[str, Any]) -> None:
    del doc["summary"]


SCAN_NEGATIVES = [
    ("schema", _set(("schema",), "apg-sbom-scan-v2"), "unexpected scan results schema"),
    ("status", _set(("status",), "failed"), "status is not passed"),
    ("no-summary", _drop_summary, "lack a summary"),
    ("artifact-count-10", _set(("summary", "artifact_count"), 10), "artifact_count"),
    ("sbom-count-13", _set(("summary", "sbom_count"), 13), "sbom_count"),
    ("grype-count-13", _set(("summary", "grype_count"), 13), "grype_count"),
    ("conditional-sbom-0", _set(("summary", "conditional_sbom_count"), 0), "conditional_sbom_count"),
    ("coverage-gaps", _set(("summary", "coverage_gaps"), ["x"]), "coverage_gaps"),
    ("policy-findings", _set(("summary", "policy_findings"), ["x"]), "policy_findings"),
    ("tool-failures", _set(("summary", "tool_failures"), ["x"]), "tool_failures"),
    ("summary-blocked", _set(("summary", "status"), "blocked"), "summary status"),
    ("high-severity", _set(("summary", "severity_counts"), {"high": 1}), "High/Critical"),
    ("ten-records", _pop_artifact, "exactly 11 artifact records"),
    ("duplicate-record", _duplicate_artifact, "duplicate or malformed artifact record"),
    ("foreign-target", _in_record("go/darwin", "target", value="go/other/apgr"), "scan targets differ"),
    ("unbound-digest", _in_record("linux-amd64/apgr", "target_sha256", value="0" * 64), "not bound to the sealed asset digest"),
    ("record-failed", _in_record(".tar.gz", "status", value="policy-finding"), "did not pass"),
    ("wrong-kind", _in_record(".whl", "kind", value="npm-launcher"), "unexpected kind"),
    ("sbom-gap", _in_record("darwin-arm64/apgr", "sbom", "coverage_status", value="coverage-gap"), "SBOM coverage is incomplete"),
    ("sbom-missing-types", _in_record("darwin-arm64/apgr", "sbom", "missing_types", value=["go-module"]), "SBOM coverage is incomplete"),
    ("syft-failed", _in_record("darwin-arm64/apgr", "sbom", "syft_returncode", value=1), "Syft did not exit cleanly"),
    ("empty-sbom", _in_record("darwin-arm64/apgr", "sbom", "package_count", value=0), "SBOM is empty"),
    ("grype-blocking", _in_record("darwin-arm64/apgr", "grype", "blocking_severities", value=["high"]), "Grype policy did not pass"),
    ("grype-rc2", _in_record("darwin-arm64/apgr", "grype", "returncode", value=2), "Grype policy did not pass"),
    ("grype-input", _in_record("darwin-arm64/apgr", "grype", "input_sbom_sha256", value="9" * 64), "Grype input is not its SBOM"),
    ("embedded-sha", _in_record(".whl", "embedded_binary", "sha256", value="0" * 64), "does not embed the sealed"),
    ("embedded-flag", _in_record(".whl", "embedded_binary", "matches", value=False), "does not embed the sealed"),
    ("embedded-missing", _in_record(".whl", "embedded_binary", delete=True), "does not embed the sealed"),
    ("no-derived", _in_record(".tar.gz", "derived_install", delete=True), "lacks its derived-install"),
    ("derived-failed", _in_record(".tar.gz", "derived_install", "installation", "installer", "status", value="failed"), "derived installation did not pass"),
    ("derived-unbound", _in_record(".tar.gz", "derived_install", "source_archive_sha256", value="0" * 64), "not bound to the sealed sdist"),
    ("derived-sbom-unbound", _in_record(".tar.gz", "derived_install", "sbom", "source_archive_sha256", value="0" * 64), "derived sbom is not bound"),
    ("union-gap", _in_record(".tar.gz", "coverage_union", "status", value="coverage-gap"), "coverage union is incomplete"),
    ("conditional-failed", _set(("conditional_dependency", "status"), "tool-failure"), "conditional dependency scan did not pass"),
    ("conditional-view", _set(("conditional_dependency", "view", "target_python"), "3.11"), "conditional dependency view did not pass"),
    ("conditional-receipt", _set(("conditional_dependency", "receipt"), None), "receipt is missing"),
    ("source-failed", _set(("source", "status"), "coverage-gap"), "source scan did not pass"),
    ("db-invalid", _set(("database", "valid"), False), "update/validity evidence"),
    ("db-update-failed", _set(("database", "update", "status"), "failed"), "update/validity evidence"),
    ("db-unchecked", _set(("database", "update_check"), "skipped"), "update/validity evidence"),
    ("db-stale", _set(("database", "age_hours"), 121), "stale"),
    ("db-age-policy", _set(("database", "max_age_hours"), 500), "stale or its age policy"),
    ("db-negative-age", _set(("database", "age_hours"), -1), "stale"),
    ("ignores", _set(("policy", "custom_ignores"), [{"id": "CVE-1"}]), "maintained strict policy"),
    ("fail-on", _set(("policy", "grype_fail_on"), "critical"), "maintained strict policy"),
    ("syft-version", _set(("scanner", "syft", "version"), "0.0.1"), "pinned version"),
    ("grype-version", _set(("scanner", "grype", "version"), "0.0.1"), "pinned version"),
]


@pytest.mark.parametrize(("mutate", "message"), [pytest.param(m, msg, id=name) for name, m, msg in SCAN_NEGATIVES])
def test_check_scan_negative_documents(scans_world: SimpleNamespace, mutate: Callable[[dict[str, Any]], None], message: str) -> None:
    mutate(scans_world.doc)
    write_scan(scans_world.scans, scans_world.doc)
    with pytest.raises(assembly.AssemblyError, match=message):
        assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)
    assert not scans_world.scan_out.exists()


def test_check_scan_negative_fixture_table_has_no_vacuous_entry(scans_world: SimpleNamespace) -> None:
    for name, mutate, _ in SCAN_NEGATIVES:
        doc = copy.deepcopy(scans_world.doc)
        mutate(doc)
        assert doc != scans_world.doc, name


def test_check_scan_requires_every_evidence_file_by_digest(scans_world: SimpleNamespace) -> None:
    write_scan(scans_world.scans, scans_world.doc)
    victim = scans_world.scans / rec(scans_world.doc, ".tar.gz")["sbom"]["path"]
    original = victim.read_bytes()
    victim.write_bytes(b"substituted")
    with pytest.raises(assembly.AssemblyError, match="scan evidence digest mismatch"):
        assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)
    victim.unlink()
    with pytest.raises(SealError, match="unavailable"):
        assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)
    victim.symlink_to(scans_world.scans / "scan-results.json")
    with pytest.raises(SealError, match="symlink"):
        assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)
    victim.unlink()
    victim.write_bytes(original)
    assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)


@pytest.mark.parametrize("path", ["../escape.json", "/abs/path.json", "a\\b.json", "source/../source/sbom.syft.json"])
def test_check_scan_rejects_unsafe_evidence_paths(scans_world: SimpleNamespace, path: str) -> None:
    scans_world.doc["source"]["sbom"]["path"] = path
    write_scan(scans_world.scans, scans_world.doc)
    with pytest.raises(assembly.AssemblyError, match="unsafe scan evidence path"):
        assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)


def test_check_scan_missing_results_or_symlinked_directory(scans_world: SimpleNamespace) -> None:
    with pytest.raises(SealError, match="unavailable"):
        assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)
    write_scan(scans_world.scans, scans_world.doc)
    alias = scans_world.tmp / "alias"
    alias.symlink_to(scans_world.scans)
    with pytest.raises(SealError, match="symlink"):
        assembly.run_check_scan(scans_world.out, alias, scans_world.scan_out)


def test_check_scan_rejects_changed_bundle_and_json_output(scans_world: SimpleNamespace) -> None:
    write_scan(scans_world.scans, scans_world.doc)
    with pytest.raises(assembly.AssemblyError, match="must be a directory"):
        assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.tmp / "receipt.json")
    with (scans_world.out / "python" / PY_NAMES[0]).open("ab") as stream:
        stream.write(b"changed after sealing")
    with pytest.raises(SealError, match="digest"):
        assembly.run_check_scan(scans_world.out, scans_world.scans, scans_world.scan_out)


def test_cli_reports_failures_and_success(scans_world: SimpleNamespace, capsys: pytest.CaptureFixture[str]) -> None:
    args = ["check-scan", "--bundle", str(scans_world.out), "--scans", str(scans_world.scans), "--output", str(scans_world.scan_out)]
    assert assembly.main(args) == 1
    assert "native_release_assembly error" in capsys.readouterr().err
    write_scan(scans_world.scans, scans_world.doc)
    assert assembly.main(args) == 0
    assert assembly.main(["assemble", "--lanes", str(scans_world.out), "--output", str(scans_world.out)]) == 1


# --------------------------------------------------------------------------- real packagers


def test_real_canonical_packagers_end_to_end(tmp_path: Path, gh: FakeGitHub, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(assembly.candidate, "_source_revision_identity",
                        lambda _root, _version: {"source_commit": COMMIT, "source_tree": TREE})
    world = make_world(tmp_path, gh, monkeypatch)
    seal = assembly.run_assemble(world.lanes, world.out)
    out = world.out

    assert leftovers(tmp_path) == []
    assert len(assembly._tree_digests(out)) == assembly.BUNDLE_FILE_COUNT + 1
    manifest = json.loads((out / assembly.candidate.MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["source_commit"] == COMMIT and manifest["source_tree"] == TREE
    assembly.candidate.check(out / assembly.candidate.MANIFEST_NAME, assembly.ROOT, out / "go", out / "python", out / "npm")
    assert seal["asset_count"] == 11 and set(seal["lane_seals"]) == set(REQUIRED_LANES)

    lane_binaries = {}
    for lane in REQUIRED_LANES:
        spec = CANONICAL_TARGETS[lane]
        source_dir = world.lanes / lane / spec["slug"] if lane == "native-linux-x64" else world.lanes / lane
        lane_binaries[lane] = (source_dir / "apgr").read_bytes()
        assert (out / spec["go_binary"]).read_bytes() == lane_binaries[lane]
        wheel = next((out / "python").glob(f"*{spec['python_tag']}*.whl"))
        with zipfile.ZipFile(wheel) as archive:
            assert archive.read("agentic_praxis_grimoire/bin/apgr") == lane_binaries[lane]
    embedded = set()
    for tarball in sorted((out / "npm").glob("*.tgz")):
        with tarfile.open(tarball, "r:gz") as archive:
            member = archive.getmember("package/bin/apgr") if "package/bin/apgr" in archive.getnames() else None
            if member is not None:
                embedded.add(archive.extractfile(member).read())
    assert embedded == set(lane_binaries.values())

    monkeypatch.setenv("NATIVE_BUNDLE_JSON", json.dumps({"artifact_id": "104", "artifact_digest": "sha256:" + "e" * 64,
                                                       "seal_sha256": seal["bundle_seal_sha256"]}))
    names = assembly.export_scan_input(out, tmp_path / "scan-input")
    assert len(names) == assembly.BUNDLE_FILE_COUNT
    scans = tmp_path / "scans"
    scans.mkdir()
    write_scan(scans, build_scan(scans, seal["assets"]))
    assert assembly.run_check_scan(out, scans, tmp_path / "scan-out")["scan_count"] == 14
