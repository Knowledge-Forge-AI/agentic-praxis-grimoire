"""Closed repository-import execution for retained dynamic consumers."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import sys
import subprocess
import threading
import time
from types import ModuleType
import zipfile

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

from apg_candidate_lifecycle_fixture import materialize_actual_retained  # noqa: E402
from apg_candidate_surface_contract import (  # noqa: E402
    derive_skill_surface_counts,
    load_removal_plan,
)
from apg_repository_import_contract import (  # noqa: E402
    RepositoryImportError,
    execute_repository_consumer,
)
from apg_repository_import_cache_contract import (  # noqa: E402
    snapshot_repository_import_state,
)


CANDIDATE = "css-language-profile"
PLAN = load_removal_plan(
    ROOT / "src/test/fixtures/apg60-css-removal-plan.json", root=ROOT
)


def _contract_module():
    return importlib.import_module("apg_actual_retained_surface_contract")


def _materialize_lifecycle(root: Path) -> None:
    materialize_actual_retained(root, ROOT, PLAN)


def _materialize(root: Path) -> None:
    _write(
        root / f"skills/{CANDIDATE}/SKILL.md",
        f"---\nname: {CANDIDATE}\ndescription: Test.\n---\n",
    )
    (root / "libexec").mkdir()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _consumer(imports: str, body: str = "") -> str:
    return (
        imports
        + body
        + "\ndef discover_canonical_leaves(root, skills, report):\n"
        "    return tuple(sorted(\n"
        "        path for path in skills.iterdir()\n"
        "        if path.is_dir() and (path / 'SKILL.md').is_file()\n"
        "    ))\n"
    )


def _operation_consumer(operation: str, marker: Path) -> str:
    prefix = (
        "from pathlib import Path\n"
        "import time\n"
        f"MARKER = Path({str(marker)!r})\n"
    )
    if operation == "topology":
        return prefix + (
            "def discover_canonical_leaves(root, skills, report):\n"
            "    MARKER.write_text('ready', encoding='utf-8')\n"
            "    time.sleep(0.15)\n"
            "    return tuple(path for path in skills.iterdir()\n"
            "                 if path.is_dir() and (path / 'SKILL.md').is_file())\n"
        )
    if operation == "library":
        return prefix + (
            "class Result:\n"
            "    canonical_skills = 1\n"
            "    catalog_rows = 1\n"
            "    passed = True\n"
            "    projections = 1\n"
            "\n"
            "def check_library(root):\n"
            "    MARKER.write_text('ready', encoding='utf-8')\n"
            "    time.sleep(0.15)\n"
            "    return Result()\n"
        )
    return prefix + (
        "class Skill:\n"
        "    def __init__(self, name):\n"
        "        self.name = name\n"
        "\n"
        "class Inventory:\n"
        "    def __init__(self, skills):\n"
        "        self.skills = skills\n"
        "\n"
        "def build_inventory(roots, destination):\n"
        "    MARKER.write_text('ready', encoding='utf-8')\n"
        "    time.sleep(0.15)\n"
        "    return Inventory([Skill('css-language-profile')])\n"
    )


def _assert_rejected(root: Path) -> None:
    with pytest.raises(RepositoryImportError):
        execute_repository_consumer(
            root,
            "libexec/apg_skill_topology.py",
            "topology",
        )


def test_external_symlinked_helper_fails_without_parent_cache(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    name = "apg60f_external_helper"
    _materialize(root)
    _write(tmp_path / "outside.py", "VALUE = 1\n")
    (root / f"libexec/{name}.py").symlink_to(tmp_path / "outside.py")
    _write(root / "libexec/apg_skill_topology.py", _consumer(f"import {name}\n"))
    state = snapshot_repository_import_state(
        root,
        {name, "apg_skill_topology"},
    )
    sys.modules.pop(name, None)
    try:
        _assert_rejected(root)
        assert name not in sys.modules
        state.assert_restored()
    finally:
        sys.modules.pop(name, None)


def test_first_root_helper_cannot_satisfy_second_root(
    tmp_path: Path,
) -> None:
    name = "apg60f_cross_root_helper"
    first, second = tmp_path / "first", tmp_path / "second"
    _materialize(first)
    _materialize(second)
    _write(tmp_path / "outside.py", "VALUE = 1\n")
    (first / f"libexec/{name}.py").symlink_to(tmp_path / "outside.py")
    for root in (first, second):
        _write(
            root / "libexec/apg_skill_topology.py",
            _consumer(f"import {name}\n"),
        )
    sys.modules.pop(name, None)
    try:
        _assert_rejected(first)
        _assert_rejected(second)
        assert name not in sys.modules
    finally:
        sys.modules.pop(name, None)


@pytest.mark.parametrize(
    "shape",
    (
        "symlink-package",
        "symlink-ancestor",
        "dangling",
        "namespace",
    ),
)
def test_non_direct_repository_import_shapes_fail(
    tmp_path: Path,
    shape: str,
) -> None:
    root = tmp_path / "repository"
    name = f"apg60f_{shape.replace('-', '_')}"
    _materialize(root)
    if shape == "symlink-package":
        outside = tmp_path / name
        _write(outside / "__init__.py", "VALUE = 1\n")
        (root / f"libexec/{name}").symlink_to(
            outside,
            target_is_directory=True,
        )
        imports = f"import {name}\n"
    elif shape == "symlink-ancestor":
        outside = tmp_path / name
        _write(outside / "__init__.py", "")
        _write(outside / "helper.py", "VALUE = 1\n")
        (root / f"libexec/{name}").symlink_to(
            outside,
            target_is_directory=True,
        )
        imports = f"from {name} import helper\n"
    elif shape == "dangling":
        (root / f"libexec/{name}.py").symlink_to(tmp_path / "missing.py")
        imports = f"import {name}\n"
    else:
        (root / f"libexec/{name}").mkdir()
        _write(root / f"libexec/{name}/helper.py", "VALUE = 1\n")
        imports = f"from {name} import helper\n"
    _write(root / "libexec/apg_skill_topology.py", _consumer(imports))
    _assert_rejected(root)


@pytest.mark.parametrize("shape", ("sys-path", "pth", "zip"))
def test_external_import_fallbacks_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shape: str,
) -> None:
    root = tmp_path / "repository"
    name = f"apg60f_{shape.replace('-', '_')}"
    _materialize(root)
    injected = tmp_path / "injected"
    if shape == "zip":
        archive = injected / "helpers.zip"
        archive.parent.mkdir(parents=True)
        with zipfile.ZipFile(archive, "w") as stream:
            stream.writestr(f"{name}.py", "VALUE = 1\n")
        monkeypatch.syspath_prepend(archive)
    elif shape == "sys-path":
        _write(injected / f"{name}.py", "VALUE = 1\n")
        monkeypatch.syspath_prepend(injected)
    else:
        site = tmp_path / "site"
        _write(injected / f"{name}.py", "VALUE = 1\n")
        _write(site / "external.pth", str(injected) + "\n")
        monkeypatch.setenv("PYTHONPATH", str(site))
    _write(root / "libexec/apg_skill_topology.py", _consumer(f"import {name}\n"))
    _assert_rejected(root)


@pytest.mark.parametrize("shape", ("importlib", "dunder-import"))
def test_dynamic_import_shapes_fail_with_resolvable_target(
    tmp_path: Path,
    shape: str,
) -> None:
    root = tmp_path / "repository"
    name = f"apg60f_{shape.replace('-', '_')}"
    _materialize(root)
    _write(root / f"libexec/{name}.py", "VALUE = 1\n")
    imports = (
        f"import importlib\nVALUE = importlib.import_module({name!r})\n"
        if shape == "importlib"
        else f"VALUE = __import__({name!r})\n"
    )
    _write(root / "libexec/apg_skill_topology.py", _consumer(imports))
    _assert_rejected(root)


def test_direct_recursive_module_package_and_stdlib_imports_pass(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    _materialize(root)
    _write(
        root / "libexec/apg60f_package/__init__.py",
        "from apg60f_package.helper import select\n",
    )
    _write(
        root / "libexec/apg60f_package/helper.py",
        "from pathlib import Path\n"
        "def select(paths):\n"
        "    values = tuple(paths)\n"
        "    assert all(isinstance(path, Path) for path in values)\n"
        "    return tuple(sorted(values))\n",
    )
    _write(
        root / "libexec/apg60f_direct.py",
        "from apg60f_package import select\n",
    )
    _write(
        root / "libexec/apg_skill_topology.py",
        "from apg60f_direct import select\n\n"
        "def discover_canonical_leaves(root, skills, report):\n"
        "    return select(\n"
        "        path for path in skills.iterdir()\n"
        "        if path.is_dir() and (path / 'SKILL.md').is_file()\n"
        "    )\n",
    )
    result = execute_repository_consumer(
        root,
        "libexec/apg_skill_topology.py",
        "topology",
    )
    assert result == {"diagnostics": 0, "names": [CANDIDATE]}


def test_repository_module_cannot_shadow_allowed_stdlib(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    _materialize(root)
    _write(root / "libexec/json.py", "SHADOWED = True\n")
    _write(root / "libexec/apg_skill_topology.py", _consumer("import json\n"))
    _assert_rejected(root)


@pytest.mark.parametrize("shape", ("source-closure", "result", "wrong-path"))
def test_protocol_bounds_and_fixed_operation_path_fail_closed(
    tmp_path: Path,
    shape: str,
) -> None:
    root = tmp_path / "repository"
    _materialize(root)
    if shape == "wrong-path":
        _write(root / "libexec/arbitrary.py", _consumer(""))
        with pytest.raises(RepositoryImportError):
            execute_repository_consumer(
                root,
                "libexec/arbitrary.py",
                "topology",
            )
        return
    if shape == "source-closure":
        _write(
            root / "libexec/apg60f_oversized.py",
            "VALUE = " + repr("x" * (1024 * 1024 + 1)) + "\n",
        )
        source = _consumer("import apg60f_oversized\n")
    else:
        source = (
            "def discover_canonical_leaves(root, skills, report):\n"
            "    return [skills] * 10001\n"
        )
    _write(root / "libexec/apg_skill_topology.py", source)
    _assert_rejected(root)


@pytest.mark.parametrize("repeat", (1, 2), ids=("once", "twice"))
def test_parent_path_and_module_cache_are_exactly_restored(
    tmp_path: Path,
    repeat: int,
) -> None:
    root = tmp_path / "repository"
    name = "apg60f_isolated_helper"
    _materialize(root)
    _write(root / f"libexec/{name}.py", "VALUE = 1\n")
    _write(root / "libexec/apg_skill_topology.py", _consumer(f"import {name}\n"))
    assert name not in sys.modules
    existing = ModuleType(name)
    sys.modules[name] = existing
    try:
        state = snapshot_repository_import_state(
            root,
            {name, "apg_skill_topology"},
        )
        for _ in range(repeat):
            execute_repository_consumer(
                root,
                "libexec/apg_skill_topology.py",
                "topology",
            )
            state.assert_restored()
            assert sys.modules[name] is existing
    finally:
        sys.modules.pop(name, None)


def test_two_valid_roots_load_their_own_helpers(
    tmp_path: Path,
) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    for root, marker in ((first, "first"), (second, "second")):
        _materialize(root)
        _write(
            root / "libexec/apg60f_local.py",
            f"MARKER = {marker!r}\n",
        )
        _write(
            root / "libexec/apg_skill_topology.py",
            _consumer(
                "import apg60f_local\n",
                f"assert apg60f_local.MARKER == {marker!r}\n",
            ),
        )
        result = execute_repository_consumer(
            root,
            "libexec/apg_skill_topology.py",
            "topology",
        )
        assert result["names"] == [CANDIDATE]
    assert "apg60f_local" not in sys.modules


def test_worker_cannot_follow_replaced_root_path_after_source_collection(
    monkeypatch, tmp_path: Path
) -> None:
    root = tmp_path / "repository"
    replacement = tmp_path / "replacement"
    _materialize(root)
    _write(
        root / "libexec/apg_skill_topology.py",
        _consumer(""),
    )
    _materialize(replacement)
    _write(
        replacement / "skills/replacement-only/SKILL.md",
        "---\nname: replacement-only\ndescription: Replacement.\n---\n",
    )
    _write(
        replacement / "libexec/apg_skill_topology.py",
        _consumer(""),
    )
    module = importlib.import_module("apg_repository_import_contract")
    original_run = module.subprocess.run

    def replace_before_launch(*args, **kwargs):
        root.rename(tmp_path / "original")
        replacement.rename(root)
        return original_run(*args, **kwargs)

    monkeypatch.setattr(module.subprocess, "run", replace_before_launch)
    with pytest.raises(RepositoryImportError):
        execute_repository_consumer(
            root,
            "libexec/apg_skill_topology.py",
            "topology",
        )


@pytest.mark.parametrize(
    ("operation", "relative"),
    (
        ("topology", "libexec/apg_skill_topology.py"),
        ("library", "libexec/apg_skill_library_check.py"),
        ("installer", "libexec/install_global_skills.py"),
    ),
)
def test_each_dynamic_consumer_rejects_physical_root_replacement_during_evaluation(
    tmp_path: Path,
    operation: str,
    relative: str,
) -> None:
    root = tmp_path / "repository"
    replacement = tmp_path / "replacement"
    marker = tmp_path / "worker-started"
    _materialize(root)
    _materialize(replacement)
    _write(
        root / relative,
        _operation_consumer(operation, marker),
    )
    _write(
        replacement / relative,
        _operation_consumer(operation, marker),
    )
    original_run = importlib.import_module(
        "apg_repository_import_contract"
    ).subprocess.run

    def swap_when_worker_starts() -> None:
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        root.rename(tmp_path / "original")
        replacement.rename(root)

    module = importlib.import_module("apg_repository_import_contract")

    def run_with_swap(*args, **kwargs):
        thread = threading.Thread(target=swap_when_worker_starts)
        thread.start()
        try:
            return original_run(*args, **kwargs)
        finally:
            thread.join(timeout=3)

    module.subprocess.run = run_with_swap
    try:
        with pytest.raises(RepositoryImportError):
            execute_repository_consumer(
                root,
                relative,
                operation,
            )
    finally:
        module.subprocess.run = original_run


@pytest.mark.parametrize(
    ("operation", "relative"),
    (
        ("topology", "libexec/apg_skill_topology.py"),
        ("library", "libexec/apg_skill_library_check.py"),
        ("installer", "libexec/install_global_skills.py"),
    ),
)
def test_dynamic_consumers_are_repeatable_across_two_roots(
    tmp_path: Path,
    operation: str,
    relative: str,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _materialize_lifecycle(first)
    _materialize_lifecycle(second)
    results = []
    for root in (first, second):
        results.extend(
            execute_repository_consumer(root, relative, operation)
            for _ in range(2)
        )
    assert results[0] == results[1]
    assert results[2] == results[3]
    assert results[0] == results[2]


def test_worker_snapshot_does_not_follow_replaced_descendant_path(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    outside = tmp_path / "outside"
    marker = tmp_path / "worker-started"
    _materialize(root)
    _materialize(outside)
    _write(
        root / "libexec/apg_skill_topology.py",
        "from pathlib import Path\n"
        "import time\n"
        f"MARKER = Path({str(marker)!r})\n"
        "def discover_canonical_leaves(root, skills, report):\n"
        "    MARKER.write_text('ready', encoding='utf-8')\n"
        "    time.sleep(0.15)\n"
        "    return tuple(path for path in skills.iterdir()\n"
        "                 if path.is_dir() and (path / 'SKILL.md').is_file())\n",
    )
    _write(
        outside / "skills/external-only/SKILL.md",
        "---\nname: external-only\ndescription: Outside.\n---\n",
    )
    original_run = importlib.import_module(
        "apg_repository_import_contract"
    ).subprocess.run
    module = importlib.import_module("apg_repository_import_contract")

    def replace_descendant() -> None:
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        original = root / "skills/css-language-profile"
        original.rename(root / "skills/css-language-profile-original")
        (root / "skills/css-language-profile").symlink_to(
            outside / "skills/external-only",
            target_is_directory=True,
        )

    def run_with_swap(*args, **kwargs):
        thread = threading.Thread(target=replace_descendant)
        thread.start()
        try:
            return original_run(*args, **kwargs)
        finally:
            thread.join(timeout=3)

    module.subprocess.run = run_with_swap
    try:
        result = execute_repository_consumer(
            root,
            "libexec/apg_skill_topology.py",
            "topology",
        )
    finally:
        module.subprocess.run = original_run
    assert result == {"diagnostics": 0, "names": [CANDIDATE]}


def test_current_three_dynamic_consumers_pass_disposable_derivations(
    tmp_path: Path,
) -> None:
    _materialize_lifecycle(tmp_path)
    counts = derive_skill_surface_counts(tmp_path)
    _contract_module()._assert_live_dynamic_consumers(
        tmp_path,
        PLAN["owners"],
        CANDIDATE,
        counts,
    )
