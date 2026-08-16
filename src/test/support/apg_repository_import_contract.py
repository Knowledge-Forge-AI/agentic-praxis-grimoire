"""Closed repository-source execution for three retained-state derivations.

This module verifies repository-owned Python source and executes it in a fresh
isolated interpreter.  It closes import provenance and result transport for
trusted APG test consumers; it is not a Python sandbox.  Standard-library
imports are allowed only when their top-level name is in
``sys.stdlib_module_names`` and their isolated-child origin is built in,
frozen, or lexically beneath ``sysconfig``'s stdlib roots.  Repository source
cannot shadow that allowance.
"""

from __future__ import annotations

import ast
from contextlib import redirect_stderr, redirect_stdout
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import sysconfig
from typing import Any, NoReturn

REQUEST_SCHEMA_VERSION = 3
MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_RESULT_BYTES = 64 * 1024
MAX_RESULT_ITEMS = 10_000
WORKER_TIMEOUT_SECONDS = 10
WORKER_HARNESS_MODULES = (
    "apg_exact_read_contract",
    "apg_worker_temp_root_binding_contract",
    "apg_worker_temp_cleanup_contract",
    "apg_worker_temp_contract",
    "apg_repository_snapshot_contract",
)
OPERATION_PATHS = {
    "topology": "libexec/apg_skill_topology.py",
    "library": "libexec/apg_skill_library_check.py",
    "installer": "libexec/install_global_skills.py",
}
OPERATIONS = set(OPERATION_PATHS)
FORBIDDEN_IMPORT_ROOTS = {
    "builtins",
    "importlib",
    "pkgutil",
    "runpy",
    "site",
    "zipimport",
}
FORBIDDEN_CALLS = {"__import__", "compile", "eval", "exec"}
SAFE_SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class RepositoryImportError(ValueError):
    """Repository source or isolated execution violates the closed contract."""


def _fail(message: str) -> NoReturn:
    raise RepositoryImportError(message)


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            _fail(f"JSON protocol contains duplicate key: {key}")
        value[key] = item
    return value


def _imports(source: str, relative: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    try:
        tree = ast.parse(source, filename=relative)
    except (SyntaxError, ValueError) as error:
        raise RepositoryImportError(
            f"repository Python source is invalid: {relative}"
        ) from error
    imports: list[tuple[str, tuple[str, ...]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            called = node.func.id if isinstance(node.func, ast.Name) else None
            if called in FORBIDDEN_CALLS:
                _fail(f"unsupported dynamic execution in {relative}")
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "importlib"
            ):
                _fail(f"unsupported dynamic import in {relative}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                    _fail(f"unsupported import mechanism in {relative}")
                imports.append((alias.name, ()))
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module is None:
                _fail(f"relative imports are unsupported in {relative}")
            if node.module.split(".", 1)[0] in FORBIDDEN_IMPORT_ROOTS:
                _fail(f"unsupported import mechanism in {relative}")
            members = tuple(alias.name for alias in node.names)
            if "*" in members:
                _fail(f"star imports are unsupported in {relative}")
            imports.append((node.module, members))
    return tuple(imports)


def _joined(parent: PurePosixPath, *parts: str) -> str:
    return parent.joinpath(*parts).as_posix()


def _kind(repository: Any, relative: str) -> str | None:
    return repository.entry_kind(relative)


def _local_chain(
    repository: Any,
    import_root: PurePosixPath,
    module_name: str,
    *,
    optional: bool = False,
) -> tuple[tuple[str, str, bool], ...] | None:
    parts = module_name.split(".")
    resolved: list[tuple[str, str, bool]] = []
    for index, part in enumerate(parts):
        parent = import_root.joinpath(*parts[:index])
        file_relative = _joined(parent, f"{part}.py")
        package_relative = _joined(parent, part)
        file_kind = _kind(repository, file_relative)
        package_kind = _kind(repository, package_relative)
        if file_kind not in {None, "regular"}:
            _fail("repository imported module must be a direct regular file")
        if package_kind not in {None, "directory"}:
            _fail("repository imported package must be a direct directory")
        if file_kind is not None and package_kind is not None:
            _fail("repository import is ambiguous between module and package")
        if file_kind is None and package_kind is None:
            if optional and index == len(parts) - 1:
                return None
            if index == 0:
                return None
            _fail("repository package submodule is missing")
        prefix = ".".join(parts[: index + 1])
        final = index == len(parts) - 1
        if file_kind == "regular":
            if not final:
                _fail("repository module cannot contain a submodule")
            resolved.append((prefix, file_relative, False))
            continue
        init_relative = _joined(PurePosixPath(package_relative), "__init__.py")
        init_kind = _kind(repository, init_relative)
        if init_kind != "regular":
            _fail("repository namespace or non-direct package is unsupported")
        resolved.append((prefix, init_relative, True))
    return tuple(resolved)


def _append_source(
    pending: list[tuple[str, str, bool]],
    known: dict[str, tuple[str, bool]],
    entry: tuple[str, str, bool],
) -> None:
    name, relative, is_package = entry
    previous = known.get(name)
    if previous is not None:
        if previous != (relative, is_package):
            _fail("repository module name resolves inconsistently")
        return
    known[name] = (relative, is_package)
    pending.append(entry)


def _consumer_identity(relative: str) -> tuple[PurePosixPath, str]:
    main_path = PurePosixPath(relative)
    if (
        main_path.suffix != ".py"
        or main_path.name == "__init__.py"
        or not main_path.stem.isidentifier()
        or main_path.parent == PurePosixPath(".")
    ):
        _fail("dynamic consumer must be a named Python module beneath one directory")
    if main_path.stem in sys.stdlib_module_names:
        _fail("dynamic consumer cannot shadow a standard-library module")
    return main_path.parent, main_path.stem


def _read_import_source(
    repository: Any,
    source_relative: str,
    total_bytes: int,
) -> tuple[str, int]:
    try:
        source = repository.read_text(source_relative)
    except Exception as error:
        if error.__class__.__name__ == "RepositoryPathError":
            raise RepositoryImportError(
                "repository imported source is not a direct regular file"
            ) from error
        raise
    total_bytes += len(source.encode("utf-8"))
    if total_bytes > MAX_REQUEST_BYTES // 2:
        _fail("repository import source closure exceeds the bounded ceiling")
    return source, total_bytes


def _append_chain(
    pending: list[tuple[str, str, bool]],
    known: dict[str, tuple[str, bool]],
    chain: tuple[tuple[str, str, bool], ...],
) -> None:
    for entry in chain:
        _append_source(pending, known, entry)


def _expand_import(
    repository: Any,
    import_root: PurePosixPath,
    imported: str,
    members: tuple[str, ...],
    pending: list[tuple[str, str, bool]],
    known: dict[str, tuple[str, bool]],
) -> None:
    top = imported.split(".", 1)[0]
    chain = _local_chain(repository, import_root, imported)
    if chain is None:
        if top not in sys.stdlib_module_names:
            _fail("non-standard-library external import is unsupported")
        return
    if top in sys.stdlib_module_names:
        _fail("repository source cannot shadow the standard library")
    _append_chain(pending, known, chain)
    if not chain[-1][2]:
        return
    for member in members:
        child = _local_chain(
            repository,
            import_root,
            f"{imported}.{member}",
            optional=True,
        )
        if child is not None:
            _append_chain(pending, known, child)


def _collect_sources(
    repository: Any,
    relative: str,
) -> tuple[str, dict[str, dict[str, Any]]]:
    import_root, main_module = _consumer_identity(relative)
    pending = [(main_module, relative, False)]
    known = {main_module: (relative, False)}
    sources: dict[str, dict[str, Any]] = {}
    total_bytes = 0
    while pending:
        name, source_relative, is_package = pending.pop()
        source, total_bytes = _read_import_source(
            repository,
            source_relative,
            total_bytes,
        )
        sources[name] = {
            "is_package": is_package,
            "relative": source_relative,
            "source": source,
        }
        for imported, members in _imports(source, source_relative):
            _expand_import(
                repository,
                import_root,
                imported,
                members,
                pending,
                known,
            )
    return main_module, sources


def _valid_result(operation: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("isolated result must be an object")
    expected = {
        "topology": {"diagnostics", "names"},
        "library": {
            "canonical_skills",
            "catalog_rows",
            "names",
            "passed",
            "projections",
        },
        "installer": {"names"},
    }[operation]
    if set(value) != expected:
        _fail("isolated result has an unsupported shape")
    if operation == "library":
        if type(value["passed"]) is not bool or any(
            type(value[key]) is not int or value[key] < 0
            for key in ("canonical_skills", "catalog_rows", "projections")
        ):
            _fail("isolated library result has invalid values")
        names = value["names"]
        if (
            not isinstance(names, list)
            or len(names) > MAX_RESULT_ITEMS
            or any(
                not isinstance(name, str)
                or not SAFE_SKILL_NAME.fullmatch(name)
                or len(name) > 64
                for name in names
            )
            or names != sorted(names)
            or len(names) != len(set(names))
        ):
            _fail("isolated library names are not sorted and unique")
    else:
        names = value["names"]
        if (
            not isinstance(names, list)
            or len(names) > MAX_RESULT_ITEMS
            or any(
                not isinstance(name, str)
                or not SAFE_SKILL_NAME.fullmatch(name)
                or len(name) > 64
                for name in names
            )
        ):
            _fail("isolated result names are invalid")
        if names != sorted(names) or len(names) != len(set(names)):
            _fail("isolated result names are not sorted and unique")
        if operation == "topology" and (
            type(value["diagnostics"]) is not int
            or value["diagnostics"] < 0
        ):
            _fail("isolated topology diagnostics are invalid")
    return value


def _encode_worker_request(request: dict[str, Any], temp_fd: int) -> bytes:
    request["temp_fd"] = temp_fd
    encoded = json.dumps(
        request,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(encoded) > MAX_REQUEST_BYTES:
        _fail("isolated request exceeds the bounded ceiling")
    return encoded


def _launch_repository_worker(
    request: dict[str, Any],
    repository_root: Path,
    root_descriptor: int,
    root_parent_descriptor: int,
    worker_temp_environment: Any,
    worker_temp_error: type[BaseException],
) -> subprocess.CompletedProcess[bytes]:
    try:
        with worker_temp_environment(repository_root) as temp:
            encoded = _encode_worker_request(request, temp.descriptor)
            return subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    str(Path(__file__).resolve()),
                    "--worker",
                ],
                input=encoded,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=WORKER_TIMEOUT_SECONDS,
                check=False,
                pass_fds=(
                    root_descriptor,
                    root_parent_descriptor,
                    temp.descriptor,
                ),
                env={
                    "LC_ALL": "C",
                    "PATH": os.defpath,
                    **temp.environment,
                },
            )
    except (
        OSError,
        TypeError,
        ValueError,
        subprocess.TimeoutExpired,
        worker_temp_error,
    ) as error:
        raise RepositoryImportError(
            "isolated repository consumer failed"
        ) from error


def execute_repository_consumer(
    root: Path,
    relative: str,
    operation: str,
) -> dict[str, Any]:
    """Execute one fixed retained-state operation over verified source bytes."""

    if operation not in OPERATIONS:
        _fail("unsupported repository consumer operation")
    if relative != OPERATION_PATHS[operation]:
        _fail("repository consumer path does not match its fixed operation")
    from apg_repository_path_contract import (  # local harness dependency
        RepositoryPathContract,
        RepositoryPathError,
    )
    from apg_worker_temp_contract import (  # parent-only harness dependency
        WorkerTempError,
        worker_temp_environment,
    )
    from apg_repository_import_descriptor_contract import (  # parent-only
        repository_worker_descriptors,
    )

    completed: subprocess.CompletedProcess[bytes] | None = None
    try:
        with RepositoryPathContract(root) as repository:
            repository.assert_root_binding()
            main_module, sources = _collect_sources(repository, relative)
            for harness_module in WORKER_HARNESS_MODULES:
                harness_relative = f"src/test/support/{harness_module}.py"
                try:
                    harness_source, _ = _read_import_source(
                        repository, harness_relative, 0
                    )
                except RepositoryImportError:
                    harness_source = Path(__file__).with_name(
                        f"{harness_module}.py"
                    ).read_text(encoding="utf-8")
                sources[harness_module] = {
                    "is_package": False,
                    "relative": harness_relative,
                    "source": harness_source,
                }
            repository.assert_root_binding()
            with repository_worker_descriptors(repository) as (
                root_descriptor,
                root_parent_descriptor,
            ):
                request = {
                    "main_module": main_module,
                    "operation": operation,
                    "root_fd": root_descriptor,
                    "root_identity": list(repository.root_identity),
                    "root_name": repository.root_name,
                    "root_parent_fd": root_parent_descriptor,
                    "requested_root_identity": list(
                        repository.requested_root_identity
                    ),
                    "schema_version": REQUEST_SCHEMA_VERSION,
                    "sources": sources,
                }
                completed = _launch_repository_worker(
                    request,
                    repository.root,
                    root_descriptor,
                    root_parent_descriptor,
                    worker_temp_environment,
                    WorkerTempError,
                )
            repository.assert_root_binding()
    except RepositoryPathError as error:
        raise RepositoryImportError(
            "repository import violates the physical path contract"
        ) from error
    assert completed is not None
    if (
        completed.returncode != 0
        or completed.stderr
        or len(completed.stdout) > MAX_RESULT_BYTES
    ):
        _fail("isolated repository consumer failed")
    try:
        envelope = json.loads(
            completed.stdout.decode("utf-8"),
            object_pairs_hook=_strict_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RepositoryImportError(
            "isolated repository consumer returned invalid data"
        ) from error
    if (
        not isinstance(envelope, dict)
        or set(envelope) != {"ok", "result", "schema_version"}
        or envelope["schema_version"] != REQUEST_SCHEMA_VERSION
        or envelope["ok"] is not True
    ):
        _fail("isolated repository consumer rejected the request")
    return _valid_result(operation, envelope["result"])


def _within(path: str, roots: tuple[str, ...]) -> bool:
    physical = os.path.abspath(path)
    return any(
        os.path.commonpath((physical, root)) == root
        for root in roots
    )


class _ManifestLoader(importlib.abc.Loader):
    def __init__(self, entry: dict[str, Any]) -> None:
        self.entry = entry

    def create_module(self, spec: Any) -> None:
        return None

    def exec_module(self, module: Any) -> None:
        source = self.entry["source"]
        relative = self.entry["relative"]
        module.__file__ = f"<repository>/{relative}"
        exec(compile(source, module.__file__, "exec"), module.__dict__)


class _ClosedFinder(importlib.abc.MetaPathFinder):
    def __init__(
        self,
        sources: dict[str, dict[str, Any]],
        stdlib_paths: tuple[str, ...],
        stdlib_roots: tuple[str, ...],
    ) -> None:
        self.sources = sources
        self.local_roots = {name.split(".", 1)[0] for name in sources}
        self.stdlib_paths = stdlib_paths
        self.stdlib_roots = stdlib_roots

    def find_spec(
        self,
        fullname: str,
        path: Any = None,
        target: Any = None,
    ) -> Any:
        entry = self.sources.get(fullname)
        if entry is not None:
            return importlib.util.spec_from_loader(
                fullname,
                _ManifestLoader(entry),
                origin=f"<repository>/{entry['relative']}",
                is_package=entry["is_package"],
            )
        top = fullname.split(".", 1)[0]
        if top in self.local_roots or top not in sys.stdlib_module_names:
            raise ImportError("import is outside the closed source set")
        search = self.stdlib_paths if path is None else tuple(path)
        if any(not _within(item, self.stdlib_roots) for item in search):
            raise ImportError("standard-library package path is outside its root")
        spec = importlib.machinery.PathFinder.find_spec(fullname, list(search))
        if spec is None:
            raise ImportError("standard-library module is unavailable")
        if spec.origin not in {"built-in", "frozen", None} and not _within(
            spec.origin,
            self.stdlib_roots,
        ):
            raise ImportError("standard-library module origin is outside its root")
        locations = spec.submodule_search_locations or ()
        if any(not _within(item, self.stdlib_roots) for item in locations):
            raise ImportError("standard-library package is outside its root")
        return spec


def _validate_worker_request_identity(request: Any) -> dict[str, Any]:
    if (
        not isinstance(request, dict)
        or set(request)
        != {
            "main_module",
            "operation",
            "requested_root_identity",
            "root_fd",
            "root_identity",
            "root_name",
            "root_parent_fd",
            "schema_version",
            "sources",
            "temp_fd",
        }
        or request["schema_version"] != REQUEST_SCHEMA_VERSION
        or request["operation"] not in OPERATIONS
        or request["main_module"]
        != PurePosixPath(OPERATION_PATHS[request["operation"]]).stem
    ):
        _fail("worker request shape is invalid")
    return request


def _validate_worker_request_values(request: dict[str, Any]) -> None:
    for key in ("root_fd", "root_parent_fd", "temp_fd"):
        if type(request[key]) is not int or request[key] < 0:
            _fail("worker repository descriptor is invalid")
    if (
        not isinstance(request["root_name"], str)
        or not request["root_name"]
        or request["root_name"] in {".", ".."}
        or "/" in request["root_name"]
        or "\\" in request["root_name"]
    ):
        _fail("worker repository root name is invalid")
    for key in ("root_identity", "requested_root_identity"):
        value = request[key]
        if (
            not isinstance(value, list)
            or len(value) != 7
            or any(type(item) is not int or item < 0 for item in value)
        ):
            _fail("worker repository identity is invalid")
    if not isinstance(request["main_module"], str):
        _fail("worker main module is invalid")
    if (
        not isinstance(request["sources"], dict)
        or request["main_module"] not in request["sources"]
    ):
        _fail("worker source closure is invalid")


def _validate_worker_source(name: Any, entry: Any) -> None:
    if not isinstance(name, str) or not isinstance(entry, dict):
        _fail("worker source manifest is invalid")
    if set(entry) != {"is_package", "relative", "source"}:
        _fail("worker source manifest is invalid")
    if (
        type(entry["is_package"]) is not bool
        or not isinstance(entry["relative"], str)
        or not isinstance(entry["source"], str)
    ):
        _fail("worker source manifest is invalid")


def _worker_request(raw: bytes) -> dict[str, Any]:
    if not raw or len(raw) > MAX_REQUEST_BYTES:
        _fail("worker request exceeds the bounded ceiling")
    try:
        decoded = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RepositoryImportError("worker request is invalid") from error
    request = _validate_worker_request_identity(decoded)
    _validate_worker_request_values(request)
    for name, entry in request["sources"].items():
        _validate_worker_source(name, entry)
    return request


def _worker_root_binding(request: dict[str, Any]) -> Path:
    try:
        root_stat = os.fstat(request["root_fd"])
        root_entry = os.stat(
            request["root_name"],
            dir_fd=request["root_parent_fd"],
            follow_symlinks=False,
        )
    except OSError as error:
        raise RepositoryImportError(
            "worker repository root is unavailable"
        ) from error
    expected = tuple(request["root_identity"])
    if (
        _stat_identity(root_stat) != expected
        or _stat_identity(root_entry) != expected
    ):
        _fail("worker repository root entry changed")
    try:
        os.fchdir(request["root_fd"])
    except OSError as error:
        raise RepositoryImportError(
            "worker cannot enter the pinned repository root"
        ) from error
    return Path(".")


def _stat_identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _worker_assert_root_binding(request: dict[str, Any]) -> None:
    """Recheck the pinned descriptor and its parent entry without chdir."""

    try:
        root_stat = os.fstat(request["root_fd"])
        root_entry = os.stat(
            request["root_name"],
            dir_fd=request["root_parent_fd"],
            follow_symlinks=False,
        )
    except OSError as error:
        raise RepositoryImportError(
            "worker repository root disappeared during evaluation"
        ) from error
    expected = tuple(request["root_identity"])
    if (
        _stat_identity(root_stat) != expected
        or _stat_identity(root_entry) != expected
    ):
        _fail("worker repository root entry changed during evaluation")


def _worker_canonical_names(root: Path) -> list[str]:
    """Derive a sorted safe name set from direct canonical repository leaves."""

    try:
        namespaces = sorted((root / "skills").iterdir(), key=lambda item: item.name)
    except OSError as error:
        raise RepositoryImportError("worker skill root cannot be enumerated") from error
    names: list[str] = []
    for namespace in namespaces:
        if namespace.name == "README.md":
            continue
        if namespace.name == "chatgpt":
            if namespace.is_symlink() or not namespace.is_dir():
                _fail("worker canonical namespace is not direct")
            candidates = sorted(namespace.iterdir(), key=lambda item: item.name)
        else:
            candidates = [namespace]
        for candidate in candidates:
            if (
                candidate.is_symlink()
                or not candidate.is_dir()
                or not SAFE_SKILL_NAME.fullmatch(candidate.name)
                or not (candidate / "SKILL.md").is_file()
                or (candidate / "SKILL.md").is_symlink()
            ):
                _fail("worker canonical skill leaf is invalid")
            names.append(candidate.name)
    if len(names) != len(set(names)):
        _fail("worker canonical skill names are duplicated")
    return sorted(names)


def _stdlib_boundary() -> tuple[tuple[str, ...], tuple[str, ...]]:
    roots = tuple(
        sorted(
            {
                os.path.abspath(value)
                for key in ("stdlib", "platstdlib")
                if (value := sysconfig.get_path(key))
            }
        )
    )
    paths = tuple(
        item
        for item in sys.path
        if os.path.isdir(item) and _within(item, roots)
    )
    if not roots or not paths:
        _fail("standard-library boundary is unavailable")
    return paths, roots


def _worker_result(request: dict[str, Any]) -> dict[str, Any]:
    _worker_root_binding(request)
    stdlib_paths, stdlib_roots = _stdlib_boundary()
    finder = _ClosedFinder(request["sources"], stdlib_paths, stdlib_roots)
    sys.path[:] = list(stdlib_paths)
    sys.meta_path[:] = [
        importlib.machinery.BuiltinImporter,
        importlib.machinery.FrozenImporter,
        finder,
    ]
    snapshot_module = importlib.import_module("apg_repository_snapshot_contract")
    with snapshot_module.worker_snapshot(
        request["root_fd"], request["temp_fd"]
    ) as root:
        os.chdir(root)
        with open(os.devnull, "w", encoding="utf-8") as sink:
            with redirect_stdout(sink), redirect_stderr(sink):
                module = importlib.import_module(request["main_module"])
                operation = request["operation"]
                if operation == "topology":
                    diagnostics: list[tuple[Any, ...]] = []
                    leaves = module.discover_canonical_leaves(
                        root,
                        root / "skills",
                        lambda *items: diagnostics.append(items),
                    )
                    result = {
                        "diagnostics": len(diagnostics),
                        "names": sorted(Path(path).name for path in leaves),
                    }
                elif operation == "library":
                    result = module.check_library(root)
                    result = {
                        "canonical_skills": result.canonical_skills,
                        "catalog_rows": result.catalog_rows,
                        "names": _worker_canonical_names(root),
                        "passed": result.passed,
                        "projections": result.projections,
                    }
                else:
                    destination = (
                        Path("..")
                        / f".{request['root_name']}-actual-retained-destination"
                    )
                    inventory = module.build_inventory((root,), destination)
                    result = {"names": sorted(skill.name for skill in inventory.skills)}
                _worker_assert_root_binding(request)
                return result


def _worker_main() -> int:
    request: dict[str, Any] | None = None
    try:
        request = _worker_request(sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1))
        result = _valid_result(request["operation"], _worker_result(request))
        envelope = {
            "ok": True,
            "result": result,
            "schema_version": REQUEST_SCHEMA_VERSION,
        }
    except Exception:
        envelope = {
            "ok": False,
            "result": None,
            "schema_version": REQUEST_SCHEMA_VERSION,
        }
    finally:
        if request is not None:
            for key in ("root_fd", "root_parent_fd", "temp_fd"):
                try:
                    os.close(request[key])
                except OSError:
                    pass
    encoded = json.dumps(
        envelope,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if len(encoded) > MAX_RESULT_BYTES:
        encoded = (
            b'{"ok":false,"result":null,"schema_version":'
            + str(REQUEST_SCHEMA_VERSION).encode("ascii")
            + b"}"
        )
    sys.stdout.buffer.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(_worker_main() if sys.argv[1:] == ["--worker"] else 2)
