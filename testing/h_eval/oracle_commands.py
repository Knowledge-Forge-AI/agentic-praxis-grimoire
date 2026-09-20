"""Retained command receipts using the shared sealed-runtime owner."""
import hashlib
import os
import shutil
import stat
from collections.abc import Mapping
from pathlib import Path

from .execution import _write_bytes, _write_json
from .runtime_execution import begin
from .runtime_manifest import manifest_digest

MAX_STREAM_BYTES = 64 << 20
# Download-cache files a GOPROXY=off build reads.  ``.ziphash`` is omitted so
# Go recomputes the zip hash and checks it against the subject's go.sum.
GO_MODULE_SUFFIXES = (".mod", ".zip", ".info")


def _go_escape(value: str) -> str:
    """Go module-cache case encoding: each upper-case letter becomes ``!lower``."""
    return "".join("!" + character.lower() if "A" <= character <= "Z" else character
                   for character in value)


def _go_sum_versions(go_sum: Path) -> list[tuple[str, str]]:
    versions = set()
    for line in go_sum.read_text().splitlines():
        fields = line.split()
        if len(fields) != 3 or not fields[2].startswith("h1:"):
            raise ValueError("subject go.sum line is malformed")
        versions.add((fields[0], fields[1].removesuffix("/go.mod")))
    return sorted(versions)


def _bound_module_directories(runtime: Mapping) -> dict[str, tuple[Path, dict[str, Mapping]]]:
    """Map escaped module paths to sealed ``cache/download/<module>/@v`` inputs."""
    groups, files = runtime.get("groups"), runtime.get("files")
    if not isinstance(groups, Mapping) or not isinstance(files, Mapping):
        return {}
    bound = {}
    for declared in groups.get("cache_inputs", []):
        identity = files.get(declared)
        if not isinstance(identity, Mapping) or identity.get("kind") != "directory":
            continue
        physical = Path(identity["physical_path"])
        parts = physical.parts
        starts = [index for index in range(len(parts) - 1) if parts[index:index + 2] == ("cache", "download")]
        if parts[-1] != "@v" or not starts or starts[-1] + 3 > len(parts) - 1:
            continue
        module = "/".join(parts[starts[-1] + 2:-1])
        entries = {entry["relative_path"]: entry for entry in identity.get("entries", [])
                   if isinstance(entry, Mapping) and entry.get("kind") == "file"}
        bound[module] = (physical, entries)
    return bound


def seed_go_modules(runtime: Mapping, subject: Path, modules: Path) -> list[dict]:
    """Copy only go.sum-named module files from sealed cache inputs.

    The copy is a no-op without a subject go.sum or a matching bound input, so
    ``go`` still fails honestly when a module is unavailable.  Every copied file
    must equal its sealed inventory entry; nothing is downloaded or defaulted.
    """
    go_sum = Path(subject) / "go.sum"
    if not go_sum.is_file():
        return []
    bound = _bound_module_directories(runtime)
    seeded = []
    for module, version in _go_sum_versions(go_sum):
        escaped = _go_escape(module)
        if escaped not in bound:
            continue
        physical, entries = bound[escaped]
        target = modules / "cache" / "download" / escaped / "@v"
        for suffix in GO_MODULE_SUFFIXES:
            name = _go_escape(version) + suffix
            entry = entries.get(name)
            if entry is None:
                continue
            source = physical / name
            if source.is_symlink() or not source.is_file():
                raise ValueError("bound Go module input is not a regular file")
            data = source.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if entry.get("bytes") != len(data) or entry.get("sha256") != digest:
                raise ValueError("bound Go module input differs from the sealed inventory")
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
            _write_bytes(target / name, data)
            seeded.append({"module": module, "version": version, "name": name, "source": str(source),
                           "bytes": len(data), "sha256": digest})
    return seeded


def _remove_run_owned(path: Path) -> None:
    """Remove a run-owned tree, restoring owner write on Go's read-only module dirs."""
    for directory, names, _files in os.walk(path):
        for name in names:
            child = Path(directory) / name
            if not child.is_symlink():
                child.chmod(stat.S_IMODE(child.lstat().st_mode) | stat.S_IRWXU)
    shutil.rmtree(path)


class ManifestRunner:
    """One immutable command invocation in an oracle-owned directory."""

    def __init__(self, runtime, subject, directory):
        self.runtime = runtime
        self.subject = Path(subject)
        self.directory = Path(directory)
        if self.directory.exists() or self.directory.resolve() != self.directory:
            raise ValueError("oracle command receipt directory must be new and physical")
        self.directory.mkdir(mode=0o700)
        self.used = False

    def run(self, argv, *, cwd):
        if self.used:
            raise ValueError("oracle command replay refused")
        self.used = True
        cwd = Path(cwd)
        if cwd != self.subject:
            raise ValueError("oracle command subject changed")
        home, temporary, cache = [self.directory / name for name in ("home", "tmp", "cache")]
        for path in (home, temporary, cache, cache / "go", cache / "npm"):
            path.mkdir(mode=0o700)
        transaction = begin(self.runtime, work_dir=self.directory, home=home)
        try:
            executable = transaction.resolve(argv[0])
            extra = {"PYTHONPATH": str(cwd)}
            go_modules = []
            if argv[0] == "go":
                extra["GOCACHE"] = str(cache / "go")
                (cache / "gomod").mkdir(mode=0o700)
                go_modules = seed_go_modules(self.runtime, cwd, cache / "gomod")
                extra["GOMODCACHE"] = str(cache / "gomod")
            if argv[0] == "npm":
                extra["npm_config_cache"] = str(cache / "npm")
            completed = transaction.run(argv[0], argv[1:], cwd=cwd, temp_root=temporary,
                                        extra_environment=extra, timeout=120)
            for name, data in (("stdout", completed.stdout), ("stderr", completed.stderr)):
                if len(data) > MAX_STREAM_BYTES:
                    raise ValueError("oracle command stream exceeds declared retention bound")
                _write_bytes(self.directory / name, data)
            receipt = {
                "schema": "apg.h-oracle-command/v1", "argv": list(argv),
                "physical_executable": executable, "exit_code": completed.returncode,
                "runtime_sha256": manifest_digest(self.runtime),
                "stdout": {"bytes": len(completed.stdout), "sha256": hashlib.sha256(completed.stdout).hexdigest()},
                "stderr": {"bytes": len(completed.stderr), "sha256": hashlib.sha256(completed.stderr).hexdigest()},
                "truncated": False, "network_policy": "configured_offline_not_os_enforced"}
            if go_modules:
                receipt["go_module_inputs"] = go_modules
            _write_json(self.directory / "command.json", receipt)
            return completed
        finally:
            transaction.close()
            for path in (home, temporary, cache):
                _remove_run_owned(path)
