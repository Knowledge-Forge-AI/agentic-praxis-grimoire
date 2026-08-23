"""Exact-argv launcher for the portable APGR Go runtime.

The bridge is deliberately only a process boundary.  It locates an explicitly
authorised development binary, a package-owned binary, or a deterministic
source-checkout build, and then hands the complete argument vector to Go.  It
does not search ``PATH`` for an unrelated ``apgr`` and it never downloads a
runtime binary.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from typing import Mapping, Sequence


MODULE_PATH = "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire"
BINARY_NAME = "apgr"
BINARY_MANIFEST_SCHEMA = "apg.binary-manifest/v1"
BUILD_INFO_SCHEMA = "apg.build-info/v1"
BUILD_FLAGS = ("CGO_ENABLED=0", "-trimpath", "-buildvcs=false", "-buildid=")
CORPUS_RESOURCE = "resources/skill-metadata.json"
SUPPORTED_TARGETS = frozenset({"darwin/arm64", "linux/amd64", "linux/arm64"})


class GoBridgeError(RuntimeError):
    """The portable Go runtime cannot be located or launched safely."""


@dataclass(frozen=True, slots=True)
class Invocation:
    argv: tuple[str, ...]
    cwd: Path
    source_root: Path | None = None
    kind: str = "override"


@dataclass(frozen=True, slots=True)
class CapturedResult:
    """The bounded result of a bridge call whose streams were captured."""

    returncode: int
    stdout: bytes
    stderr: bytes


def _direct_file_bytes(value: Path, label: str) -> bytes:
    """Read one direct regular file without following a package symlink."""

    try:
        metadata = value.lstat()
    except OSError as error:
        raise GoBridgeError(f"{label} is unavailable") from error
    if value.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise GoBridgeError(f"{label} must be a direct regular file")
    try:
        return value.read_bytes()
    except OSError as error:
        raise GoBridgeError(f"{label} cannot be read") from error


def _direct_executable(value: Path, label: str) -> Path:
    if not value.is_absolute() or value != Path(os.path.normpath(value)):
        raise GoBridgeError(f"{label} must be an absolute clean path")
    try:
        metadata = value.lstat()
    except OSError as error:
        raise GoBridgeError(f"{label} is unavailable") from error
    if value.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise GoBridgeError(f"{label} must be a direct regular file")
    if not os.access(value, os.X_OK):
        raise GoBridgeError(f"{label} is not executable")
    return value


def _source_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[2]
    module = candidate / "go.mod"
    command = candidate / "cmd" / "apgr" / "main.go"
    version = candidate / "src" / "agentic_praxis_grimoire" / "VERSION"
    try:
        module_text = module.read_text(encoding="utf-8")
    except OSError:
        return None
    if (
        not module.is_file()
        or module.is_symlink()
        or not command.is_file()
        or command.is_symlink()
        or not version.is_file()
        or version.is_symlink()
        or not module_text.startswith(f"module {MODULE_PATH}\n")
    ):
        return None
    return candidate


def _identities(root: Path) -> tuple[str, str]:
    version_path = root / "src" / "agentic_praxis_grimoire" / "VERSION"
    corpus_path = root / "src" / "agentic_praxis_grimoire" / CORPUS_RESOURCE
    try:
        version = _direct_file_bytes(version_path, "version authority").decode("ascii").strip()
    except UnicodeDecodeError as error:
        raise GoBridgeError("version authority is not ASCII") from error
    if not version or any(character.isspace() for character in version):
        raise GoBridgeError("version authority is malformed")
    corpus = hashlib.sha256(
        _direct_file_bytes(corpus_path, "canonical corpus identity")
    ).hexdigest()
    return version, corpus


def _package_identities() -> tuple[str, str]:
    package_root = Path(__file__).resolve().parent
    try:
        version = _direct_file_bytes(package_root / "VERSION", "version resource").decode(
            "ascii"
        ).strip()
    except UnicodeDecodeError as error:
        raise GoBridgeError("version resource is not ASCII") from error
    if not version or any(character.isspace() for character in version):
        raise GoBridgeError("version resource is malformed")
    corpus = hashlib.sha256(
        _direct_file_bytes(package_root / CORPUS_RESOURCE, "canonical corpus identity")
    ).hexdigest()
    return version, corpus


def _host_target() -> str:
    machine = platform.machine().lower()
    architecture = {
        "aarch64": "arm64",
        "arm64": "arm64",
        "amd64": "amd64",
        "x86_64": "amd64",
    }.get(machine)
    operating_system = {
        "darwin": "darwin",
        "linux": "linux",
    }.get(sys.platform)
    if operating_system is None or architecture is None:
        raise GoBridgeError(
            f"unsupported APGR runtime target: {sys.platform}/{machine}"
        )
    target = f"{operating_system}/{architecture}"
    if target not in SUPPORTED_TARGETS:
        raise GoBridgeError(f"unsupported APGR runtime target: {target}")
    return target


def _canonical_json(value: object) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise GoBridgeError("binary manifest is not canonical JSON") from error
    return rendered.encode("utf-8") + b"\n"


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate manifest key: {key}")
        result[key] = value
    return result


def _manifest_target(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        goos = value.get("goos")
        goarch = value.get("goarch")
        if isinstance(goos, str) and isinstance(goarch, str):
            return f"{goos}/{goarch}"
    return None


def _read_manifest(path: Path) -> dict[str, object]:
    raw = _direct_file_bytes(path, "bundled Go binary manifest")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise GoBridgeError("bundled Go binary manifest is malformed") from error
    if not isinstance(value, dict):
        raise GoBridgeError("bundled Go binary manifest must be a JSON object")
    canonical = _canonical_json(value)
    if raw != canonical:
        raise GoBridgeError("bundled Go binary manifest is not canonical JSON")
    return value


def _validate_manifest(binary: Path, manifest_path: Path) -> None:
    manifest = _read_manifest(manifest_path)
    expected_keys = {
        "binary_name",
        "build_flags",
        "build_identity",
        "build_info_schema",
        "corpus_fingerprint",
        "module_path",
        "schema_version",
        "sha256",
        "size_bytes",
        "target",
        "version",
    }
    if set(manifest) != expected_keys:
        raise GoBridgeError("bundled Go binary manifest fields are unsupported")
    if manifest["schema_version"] != BINARY_MANIFEST_SCHEMA:
        raise GoBridgeError("bundled Go binary manifest schema is unsupported")
    try:
        version, corpus = _package_identities()
        target = _host_target()
    except GoBridgeError:
        raise
    if manifest.get("version") != version:
        raise GoBridgeError("bundled Go binary manifest version disagrees with VERSION")
    if manifest.get("module_path") != MODULE_PATH:
        raise GoBridgeError("bundled Go binary manifest module identity is wrong")
    if manifest.get("build_info_schema") != BUILD_INFO_SCHEMA:
        raise GoBridgeError("bundled Go binary manifest build-info schema is wrong")
    if manifest.get("build_flags") != list(BUILD_FLAGS):
        raise GoBridgeError("bundled Go binary manifest build flags are wrong")
    identity = manifest["build_identity"]
    if not isinstance(identity, dict) or identity != {
        "corpus_fingerprint": corpus,
        "schema_version": BUILD_INFO_SCHEMA,
        "target": target,
        "version": version,
    }:
        raise GoBridgeError("bundled Go binary manifest build identity is wrong")
    if _manifest_target(manifest.get("target")) != target:
        raise GoBridgeError("bundled Go binary manifest target is not this host")
    binary_name = manifest.get("binary_name", manifest.get("binary"))
    if binary_name != BINARY_NAME:
        raise GoBridgeError("bundled Go binary manifest names the wrong executable")
    if manifest.get("corpus_fingerprint") != corpus:
        raise GoBridgeError("bundled Go binary manifest corpus identity is wrong")
    size = manifest.get("size_bytes")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise GoBridgeError("bundled Go binary manifest size is invalid")
    digest = manifest.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(
        character not in "0123456789abcdef" for character in digest
    ):
        raise GoBridgeError("bundled Go binary manifest hash is invalid")
    try:
        metadata = binary.lstat()
        content = binary.read_bytes()
    except OSError as error:
        raise GoBridgeError("bundled Go APGR binary cannot be read") from error
    if binary.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise GoBridgeError("bundled Go APGR binary must be a direct regular file")
    if len(content) != size:
        raise GoBridgeError("bundled Go APGR binary size does not match its manifest")
    if hashlib.sha256(content).hexdigest() != digest:
        raise GoBridgeError("bundled Go APGR binary hash does not match its manifest")


def locate(environment: Mapping[str, str] | None = None) -> Invocation:
    """Locate an explicit, package-bundled, or source-checkout Go command."""

    values = os.environ if environment is None else environment
    override = values.get("APGR_GO_BINARY")
    if override is not None:
        executable = _direct_executable(Path(override), "APGR_GO_BINARY")
        return Invocation((os.fspath(executable),), Path.cwd(), kind="override")

    package_root = Path(__file__).resolve().parent
    bundled = package_root / "bin" / BINARY_NAME
    manifest = package_root / "bin" / f"{BINARY_NAME}.binary-manifest.json"
    if bundled.exists() or bundled.is_symlink() or manifest.exists() or manifest.is_symlink():
        executable = _direct_executable(bundled, "bundled Go APGR binary")
        _validate_manifest(executable, manifest)
        return Invocation((os.fspath(executable),), Path.cwd(), kind="bundled")

    root = _source_root()
    if root is None:
        raise GoBridgeError("portable Go APGR runtime is unavailable")
    go_value = shutil.which("go")
    if go_value is None:
        raise GoBridgeError("Go toolchain is required for the source-checkout bridge")
    go = Path(go_value).resolve(strict=True)
    _direct_executable(go, "Go toolchain")
    return Invocation((os.fspath(go),), root, source_root=root, kind="source")


def _build_info(executable: Path, *, environment: Mapping[str, str] | None) -> dict[str, object]:
    try:
        completed = subprocess.run(
            [os.fspath(executable), "build-info"],
            cwd=Path.cwd(),
            env=None if environment is None else dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            shell=False,
        )
    except OSError as error:
        raise GoBridgeError("Go APGR build-info could not be executed") from error
    if completed.returncode != 0:
        raise GoBridgeError("Go APGR build-info verification failed")
    try:
        value = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GoBridgeError("Go APGR build-info is not valid JSON") from error
    if not isinstance(value, dict):
        raise GoBridgeError("Go APGR build-info must be a JSON object")
    return value


def _verify_build_info(
    executable: Path,
    *,
    environment: Mapping[str, str] | None,
    release_required: bool,
) -> None:
    expected_version, expected_corpus = _package_identities()
    info = _build_info(executable, environment=environment)
    if info.get("module_path") != MODULE_PATH:
        raise GoBridgeError("Go APGR build-info module identity is wrong")
    if info.get("schema_version") != BUILD_INFO_SCHEMA:
        raise GoBridgeError("Go APGR build-info schema identity is wrong")
    if info.get("target") != _host_target():
        raise GoBridgeError("Go APGR binary target does not match this host")
    version = info.get("version")
    corpus = info.get("corpus_fingerprint")
    allowed_versions = {expected_version} if release_required else {expected_version, "devel"}
    allowed_corpus = {expected_corpus} if release_required else {expected_corpus, "devel"}
    if version not in allowed_versions:
        raise GoBridgeError("Go APGR build-info version is not authorized")
    if corpus not in allowed_corpus:
        raise GoBridgeError("Go APGR build-info corpus identity is not authorized")
    if version == expected_version:
        if info.get("embedded_corpus_fingerprint") != expected_corpus:
            raise GoBridgeError("Go APGR embedded corpus identity is wrong")
        if info.get("corpus_fingerprint_verified") is not True:
            raise GoBridgeError("Go APGR build-info corpus identity is unverified")
    schemas = info.get("report_schema_versions")
    if not isinstance(schemas, dict):
        raise GoBridgeError("Go APGR build-info schema identity is unavailable")


def _child_environment(environment: Mapping[str, str] | None) -> dict[str, str] | None:
    if environment is not None:
        child = dict(environment)
    elif os.environ.get("AGENT_REPORT_TESTING") == "1":
        child = dict(os.environ)
    else:
        return None
    if child.get("AGENT_REPORT_TESTING") == "1":
        child["APG_REPORT_GO_TESTING"] = "1"
        for legacy, current in (
            ("AGENT_REPORT_TEST_PAUSE_STEP", "APG_REPORT_GO_TEST_PAUSE_STEP"),
            ("AGENT_REPORT_TEST_SIGNAL_DIR", "APG_REPORT_GO_TEST_SIGNAL_DIR"),
        ):
            if legacy in child:
                child[current] = child[legacy]
    return child


@contextmanager
def _build_source(invocation: Invocation, environment: Mapping[str, str] | None):
    if invocation.source_root is None:
        raise GoBridgeError("source-checkout bridge has no source root")
    version, corpus = _identities(invocation.source_root)
    ldflags = " ".join(
        (
            "-buildid=",
            f"-X={MODULE_PATH}/internal/buildinfo.Version={version}",
            f"-X={MODULE_PATH}/internal/buildinfo.CorpusFingerprint={corpus}",
        )
    )
    build_environment = dict(os.environ) if environment is None else dict(environment)
    build_environment["CGO_ENABLED"] = "0"
    try:
        with tempfile.TemporaryDirectory(prefix="apgr-go-bridge.") as temporary:
            binary = Path(temporary) / BINARY_NAME
            built = subprocess.run(
                [
                    invocation.argv[0],
                    "build",
                    "-trimpath",
                    "-buildvcs=false",
                    "-ldflags",
                    ldflags,
                    "-o",
                    os.fspath(binary),
                    "./cmd/apgr",
                ],
                cwd=invocation.source_root,
                env=build_environment,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
            )
            if built.returncode != 0:
                detail = built.stderr.strip()
                if detail:
                    raise GoBridgeError(f"source-checkout Go bridge build failed: {detail}")
                raise GoBridgeError("source-checkout Go bridge build failed")
            _direct_executable(binary, "source-checkout Go APGR binary")
            _verify_build_info(binary, environment=build_environment, release_required=True)
            yield binary
    except OSError as error:
        raise GoBridgeError("source-checkout Go bridge build failed") from error


def _execute(
    arguments: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str] | None,
) -> int:
    """Run one bridge process with inherited streams and signal forwarding."""

    process = subprocess.Popen(
        list(arguments), cwd=cwd, env=environment, shell=False
    )
    return _wait_with_forwarding(process)


def _execute_capture(
    arguments: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str] | None,
    input_bytes: bytes | None,
) -> CapturedResult:
    process = subprocess.Popen(
        list(arguments),
        cwd=cwd,
        env=environment,
        stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    try:
        stdout, stderr = _communicate_with_forwarding(process, input_bytes)
    except OSError as error:
        raise GoBridgeError("Go APGR bridge launch failed") from error
    return CapturedResult(process.returncode, stdout, stderr)


def _wait_with_forwarding(process: subprocess.Popen[bytes]) -> int:
    handled = [signal.SIGINT, signal.SIGTERM]
    if hasattr(signal, "SIGHUP"):
        handled.append(signal.SIGHUP)
    previous: dict[signal.Signals, object] = {}

    def forward(signum: int, _frame: object) -> None:
        try:
            process.send_signal(signum)
        except OSError:
            pass

    try:
        for value in handled:
            previous[value] = signal.getsignal(value)
            signal.signal(value, forward)
        return process.wait()
    finally:
        for value, handler in previous.items():
            signal.signal(value, handler)


def _communicate_with_forwarding(
    process: subprocess.Popen[bytes], input_bytes: bytes | None
) -> tuple[bytes, bytes]:
    handled = [signal.SIGINT, signal.SIGTERM]
    if hasattr(signal, "SIGHUP"):
        handled.append(signal.SIGHUP)
    previous: dict[signal.Signals, object] = {}

    def forward(signum: int, _frame: object) -> None:
        try:
            process.send_signal(signum)
        except OSError:
            pass

    try:
        for value in handled:
            previous[value] = signal.getsignal(value)
            signal.signal(value, forward)
        stdout, stderr = process.communicate(input_bytes)
        return stdout, stderr
    finally:
        for value, handler in previous.items():
            signal.signal(value, handler)


def _verify_invocation(invocation: Invocation, environment: Mapping[str, str] | None) -> None:
    _verify_build_info(
        Path(invocation.argv[0]),
        environment=environment,
        release_required=invocation.kind == "bundled",
    )


def _normalise_returncode(returncode: int) -> int:
    if returncode >= 0:
        return returncode
    if returncode == -signal.SIGINT:
        return 130
    return 1


def run(
    arguments: Sequence[str],
    *,
    repository_root: Path | None,
    environment: Mapping[str, str] | None = None,
) -> int:
    """Run the located bridge with exact argv, inherited streams, and no shell."""

    invocation = locate(environment)
    child_environment = _child_environment(environment)
    try:
        if invocation.source_root is None:
            _verify_invocation(invocation, child_environment)
            returncode = _execute(
                [*invocation.argv, *arguments],
                cwd=repository_root or Path.cwd(),
                environment=child_environment,
            )
        else:
            with _build_source(invocation, child_environment) as binary:
                returncode = _execute(
                    [os.fspath(binary), *arguments],
                    cwd=repository_root or Path.cwd(),
                    environment=child_environment,
                )
    except OSError as error:
        raise GoBridgeError("Go APGR bridge launch failed") from error
    return _normalise_returncode(returncode)


def run_capture(
    arguments: Sequence[str],
    *,
    repository_root: Path | None,
    input_bytes: bytes | None = None,
    environment: Mapping[str, str] | None = None,
) -> CapturedResult:
    """Run the bridge while capturing streams for compatibility callables."""

    invocation = locate(environment)
    child_environment = _child_environment(environment)
    try:
        if invocation.source_root is None:
            _verify_invocation(invocation, child_environment)
            captured = _execute_capture(
                [*invocation.argv, *arguments],
                cwd=repository_root or Path.cwd(),
                environment=child_environment,
                input_bytes=input_bytes,
            )
            return CapturedResult(
                _normalise_returncode(captured.returncode),
                captured.stdout,
                captured.stderr,
            )
        with _build_source(invocation, child_environment) as binary:
            captured = _execute_capture(
                [os.fspath(binary), *arguments],
                cwd=repository_root or Path.cwd(),
                environment=child_environment,
                input_bytes=input_bytes,
            )
            return CapturedResult(
                _normalise_returncode(captured.returncode),
                captured.stdout,
                captured.stderr,
            )
    except OSError as error:
        raise GoBridgeError("Go APGR bridge launch failed") from error


def canonical_arguments(
    *,
    repository_root: Path | None,
    outbox_root: Path,
    project: str,
    action: str,
    arguments: Sequence[str],
) -> list[str]:
    """Build the explicit configuration handoff for a canonical Go route."""

    result: list[str] = [
        "--outbox-root",
        os.fspath(outbox_root),
        "--project",
        project,
    ]
    if repository_root is not None:
        result[0:0] = ["--repository", os.fspath(repository_root)]
    result.extend(("report", action, *arguments))
    return result


def response_arguments(
    *,
    repository_root: Path | None,
    outbox_root: Path,
    project: str,
    phase: str,
    source: Path | None,
) -> list[str]:
    """Build the exact argv for the Go-owned response capture route."""

    result: list[str] = [
        "--outbox-root",
        os.fspath(outbox_root),
        "--project",
        project,
    ]
    if repository_root is not None:
        result[0:0] = ["--repository", os.fspath(repository_root)]
    result.extend(("response", "capture", "--phase", phase))
    if source is not None:
        result.extend(("--input", os.fspath(source)))
    return result


def legacy_arguments(
    command: str, repository_root: Path, arguments: Sequence[str]
) -> list[str]:
    """Build the exact compatibility-name handoff."""

    return [
        "--repository",
        os.fspath(repository_root),
        "legacy",
        command,
        *arguments,
    ]
