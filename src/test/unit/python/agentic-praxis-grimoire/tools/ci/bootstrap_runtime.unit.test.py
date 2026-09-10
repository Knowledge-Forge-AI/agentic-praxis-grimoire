"""Unit contracts for the disposable public CI runtime bootstrap."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
from io import BytesIO
from pathlib import Path
from typing import Self

import pytest

import tools.ci.bootstrap_runtime as bootstrap
from tools.ci.bootstrap_runtime import (
    _ensure_task_root,
    _verify_node,
    install_npm_runtime,
    load_runtime,
    materialize_primary_node,
    materialize_secondary_node,
    write_environment,
)


def test_runtime_manifest_is_exact_and_fail_closed() -> None:
    runtime = load_runtime()
    assert runtime["platform"] == "darwin/arm64"
    assert runtime["primary_node"]["root_owned"] is True
    assert runtime["secondary_node"]["binary_member"].endswith("/bin/node")


def test_runtime_manifest_rejects_duplicate_and_wrong_shape(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema_version":"apg.public-ci-runtime/v1",'
        '"schema_version":"other","platform":"darwin/arm64"}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_runtime(duplicate)

    malformed = tmp_path / "malformed.json"
    malformed.write_text(
        json.dumps(
            {
                "schema_version": "apg.public-ci-runtime/v1",
                "platform": "darwin/arm64",
                "runner": "macos-15",
                "primary_node": {},
                "secondary_node": {},
                "python_packages": None,
                "npm_packages": {},
                "browsers": None,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Python package pins"):
        load_runtime(malformed)


def test_primary_node_uses_flake_enabled_nix_and_verified_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []
    config = {
        "primary_node": {
            "source": "github:NixOS/nixpkgs/revision",
            "attribute": "legacyPackages.aarch64-darwin.nodejs",
            "sha256": "a" * 64,
            "required_root": "/nix/store",
            "root_owned": True,
        }
    }
    monkeypatch.setattr(
        bootstrap.shutil,
        "which",
        lambda name: "/nix/bin/nix" if name == "nix" else None,
    )
    monkeypatch.setattr(bootstrap, "_verify_node", lambda path, **_: path)

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert kwargs["env"] == {"HOME": "/runtime/home"}
        return subprocess.CompletedProcess(command, 0, stdout="/nix/store/node\n", stderr="")

    result = materialize_primary_node(
        config,
        environment={"HOME": "/runtime/home"},
        runner=runner,
    )
    assert result == Path("/nix/store/node/bin/node")
    assert commands == [
        [
            "/nix/bin/nix",
            "--extra-experimental-features",
            "nix-command flakes",
            "build",
            "--no-link",
            "--print-out-paths",
            "github:NixOS/nixpkgs/revision#legacyPackages.aarch64-darwin.nodejs",
        ]
    ]


def test_verify_node_rejects_symlink_and_accepts_exact_digest(tmp_path: Path) -> None:
    target = tmp_path / "node"
    target.write_bytes(b"node")
    target.chmod(0o700)
    digest = hashlib.sha256(b"node").hexdigest()
    assert _verify_node(target, expected_sha256=digest) == target
    link = tmp_path / "node-link"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="direct executable"):
        _verify_node(link, expected_sha256=digest)


def test_secondary_archive_preserves_only_regular_binary(tmp_path: Path) -> None:
    tmp_path.chmod(0o700)
    payload = BytesIO()
    with tarfile.open(fileobj=payload, mode="w:gz") as archive:
        info = tarfile.TarInfo("node-v-test/bin/node")
        data = b"secondary-node"
        info.size = len(data)
        info.mode = 0o755
        archive.addfile(info, BytesIO(data))

    config = {
        "secondary_node": {
            "url": "https://example.invalid/node.tar.gz",
            "archive_sha256": hashlib.sha256(payload.getvalue()).hexdigest(),
            "binary_member": "node-v-test/bin/node",
            "sha256": hashlib.sha256(b"secondary-node").hexdigest(),
        }
    }

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return payload.getvalue()

    result = materialize_secondary_node(config, tmp_path, opener=lambda _url, timeout: Response())
    assert result.read_bytes() == b"secondary-node"
    assert result.stat().st_mode & 0o111


def test_npm_runtime_binds_exact_packages_and_private_browser_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_path.chmod(0o700)
    primary = tmp_path / "primary-node"
    primary.write_bytes(b"node")
    primary.chmod(0o700)
    config = {
        "npm_packages": {
            "typescript": "7.0.2",
            "npm": "12.0.2",
            "@playwright/test": "1.62.1",
            "vite": "8.2.2",
            "rolldown": "1.2.7",
        },
        "browsers": ["chromium", "firefox", "webkit"],
    }
    commands: list[list[str]] = []
    environments: list[dict[str, str]] = []

    def write_package(root: Path, name: str, version: str) -> Path:
        package = root / "node_modules" / name
        package.mkdir(parents=True)
        (package / "package.json").write_text(
            json.dumps({"name": name, "version": version}),
            encoding="utf-8",
        )
        return package

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        environments.append(environment)
        if command[1:3] == ["install", "--prefix"]:
            package_root = Path(command[3])
            npm_root = write_package(package_root, "npm", "12.0.2")
            (npm_root / "bin").mkdir()
            (npm_root / "bin" / "npm-cli.js").write_text("#!/usr/bin/env node\n", encoding="utf-8")
            typescript_root = write_package(package_root, "typescript", "7.0.2")
            tsc = typescript_root / "bin" / "tsc"
            tsc.parent.mkdir()
            tsc.write_text("#!/usr/bin/env node\n", encoding="utf-8")
            tsc.chmod(0o700)
            write_package(package_root, "@playwright/test", "1.62.1")
            write_package(package_root, "playwright", "1.62.1")
            write_package(package_root, "playwright-core", "1.62.1")
            write_package(package_root, "vite", "8.2.2")
            write_package(package_root, "rolldown", "1.2.7")
            write_package(package_root, "@rolldown/binding-darwin-arm64", "1.2.7")
        elif command[-1] == "--version" and command[1].endswith("npm-cli.js"):
            return subprocess.CompletedProcess(command, 0, stdout="12.0.2\n", stderr="")
        elif command[-1] == "--version" and command[1].endswith("tsc"):
            return subprocess.CompletedProcess(command, 0, stdout="Version 7.0.2\n", stderr="")
        elif command[-3:] == ["chromium", "firefox", "webkit"]:
            assert environment["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path / "browsers")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(bootstrap, "_run", runner)
    package_root, tsc = install_npm_runtime(tmp_path, config, primary)

    assert package_root == tmp_path / "npm"
    assert tsc == package_root / "node_modules" / "typescript" / "bin" / "tsc"
    assert commands[0][1:3] == ["install", "--prefix"]
    assert "--ignore-scripts" in commands[0]
    assert len(environments) == 4
    for environment in environments:
        assert Path(environment["HOME"]).is_relative_to(tmp_path)
        assert Path(environment["npm_config_cache"]).is_relative_to(tmp_path)
        assert Path(environment["TMPDIR"]).is_relative_to(tmp_path)
        assert "npm_config_prefix" not in environment


def test_external_root_and_environment_output_refuse_overlap_and_overwrite(tmp_path: Path) -> None:
    repository = tmp_path / "checkout"
    repository.mkdir()
    (repository / ".git").mkdir()
    with pytest.raises(ValueError, match="overlaps|active repository"):
        _ensure_task_root(repository / "runtime", repository)

    target = tmp_path / "existing.env"
    target.write_text("KEEP=1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fresh"):
        write_environment(target, {"KEEP": "2"}, repository=repository)
    assert target.read_text(encoding="utf-8") == "KEEP=1\n"

    outside = tmp_path / "outside"
    outside.mkdir()
    redirected = tmp_path / "redirected"
    redirected.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="direct directory|symlinked ancestor"):
        _ensure_task_root(redirected / "runtime", repository)


def test_environment_file_is_private_and_sorted(tmp_path: Path) -> None:
    path = tmp_path / "runtime.env"
    write_environment(path, {"B": "two", "A": "one"})
    assert path.read_text(encoding="utf-8") == "A=one\nB=two\n"
    assert path.stat().st_mode & 0o777 == 0o600
