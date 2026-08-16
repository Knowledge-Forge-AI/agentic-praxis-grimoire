"""APG60D source-binding integrity controls."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
SUPPORT = ROOT / "src/test/support"
sys.path.insert(0, str(SUPPORT))

import apg_python_source_binding_contract as binding  # noqa: E402
from apg_candidate_surface_contract import SurfaceContractError  # noqa: E402


CANDIDATE = "css-language-profile"
OWNER = {"owner_id": "source-binding-owner", "path": "owner.py"}


def _write(root: Path, tail: str = "") -> None:
    (root / "owner.py").write_text(
        f"EXPECTED_SKILLS = ({CANDIDATE!r},)\n{tail}",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "tail",
    (
        "def trigger(callback):\n    callback.write()\n",
        "def trigger(callback):\n    callback.run()\n",
        "def trigger(callback):\n    callback.get()\n",
        "def trigger(callback):\n    return sorted((1,), key=callback)\n",
        'def trigger(callback):\n    print("x", file=callback)\n',
        'def trigger(callback):\n    return f"{callback}"\n',
        "def trigger(callback):\n    return tuple(callback)\n",
    ),
    ids=(
        "callback-write",
        "callback-run",
        "callback-get",
        "sorted-key",
        "print-file",
        "format-protocol",
        "iteration-protocol",
    ),
)
def test_callback_bearing_source_is_only_a_source_binding_claim(
    tmp_path: Path, tail: str
) -> None:
    _write(tmp_path, tail)

    assert binding.read_bound_strings(
        tmp_path / "owner.py", "EXPECTED_SKILLS", OWNER["owner_id"]
    ) == [CANDIDATE]


def test_proof_scope_excludes_runtime_and_callback_finality() -> None:
    assert binding.SOURCE_BINDING_PROOF_SCOPE == (
        "exact static owner declaration and mechanically identifiable "
        "protected-name write refusal"
    )
    assert binding.RUNTIME_VALUE_AUTHORITY == "not-used"
    assert binding.ARBITRARY_CALLER_MUTATION_SCOPE == (
        "outside-static-source-proof"
    )
    assert binding.REFLECTIVE_CALL_EFFECT_SCOPE == (
        "outside-static-syntactic-proof"
    )


def test_static_extraction_never_executes_owner_module(tmp_path: Path) -> None:
    sentinel = tmp_path / "executed"
    _write(
        tmp_path,
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('executed')\n",
    )

    assert binding.read_bound_strings(
        tmp_path / "owner.py", "EXPECTED_SKILLS", OWNER["owner_id"]
    ) == [CANDIDATE]
    assert not sentinel.exists()


@pytest.mark.parametrize(
    "tail",
    (
        "EXPECTED_SKILLS = ()\n",
        "if True:\n    EXPECTED_SKILLS = ()\n",
        "EXPECTED_SKILLS += ()\n",
        "del EXPECTED_SKILLS\n",
        "(EXPECTED_SKILLS := ())\n",
        (
            "def replace():\n"
            "    global EXPECTED_SKILLS\n"
            "    EXPECTED_SKILLS = ()\n"
        ),
        (
            "def outer():\n"
            "    EXPECTED_SKILLS = ()\n"
            "    def replace():\n"
            "        nonlocal EXPECTED_SKILLS\n"
            "        EXPECTED_SKILLS = ()\n"
        ),
        'globals()["EXPECTED_SKILLS"] = ()\n',
        'vars()["EXPECTED_" + "SKILLS"] = ()\n',
        (
            "import sys\n"
            "setattr(sys.modules[__name__], "
            '"EXPECTED_SKILLS", ())\n'
        ),
        'exec("EXPECTED_SKILLS = ()")\n',
        "def EXPECTED_SKILLS():\n    return ()\n",
        "async def EXPECTED_SKILLS():\n    return ()\n",
        "class EXPECTED_SKILLS:\n    pass\n",
        "import os as EXPECTED_SKILLS\n",
        "from os import path as EXPECTED_SKILLS\n",
        "from os import *\n",
        (
            "try:\n"
            "    raise RuntimeError\n"
            "except RuntimeError as EXPECTED_SKILLS:\n"
            "    pass\n"
        ),
        (
            "def replace(EXPECTED_SKILLS):\n"
            "    return EXPECTED_SKILLS\n"
        ),
        (
            'key = "EXPECTED_" + "SKILLS"\n'
            '__import__("builtins").globals().update({key: ()})\n'
        ),
        (
            "from builtins import globals as namespace\n"
            'namespace().update({"EXPECTED_" + "SKILLS": ()})\n'
        ),
        (
            'key = "EXPECTED_" + "SKILLS"\n'
            '__builtins__["globals"]().update({key: ()})\n'
        ),
        (
            "import sys\n"
            'sys.modules[__name__].__setattr__("EXPECTED_SKILLS", ())\n'
        ),
        (
            "import builtins\n"
            'key = "EXPECTED_" + "SKILLS"\n'
            'getattr(builtins, "globals")().update({key: ()})\n'
        ),
        (
            "from builtins import getattr as accessor\n"
            'key = "EXPECTED_" + "SKILLS"\n'
            'accessor(__import__("builtins"), "globals")().update({key: ()})\n'
        ),
        "def replace[EXPECTED_SKILLS]():\n    pass\n",
        "def replace[*EXPECTED_SKILLS]():\n    pass\n",
        "def replace[**EXPECTED_SKILLS]():\n    pass\n",
        (
            "import builtins\n"
            "import operator\n"
            'key = "EXPECTED_" + "SKILLS"\n'
            'namespace = operator.attrgetter("globals")(builtins)()\n'
            "namespace.update({key: ()})\n"
        ),
        (
            "import builtins\n"
            "from operator import attrgetter as accessor\n"
            'key = "EXPECTED_" + "SKILLS"\n'
            'namespace = accessor("globals")(builtins)()\n'
            "namespace.update({key: ()})\n"
        ),
    ),
    ids=(
        "duplicate",
        "conditional",
        "augmented",
        "delete",
        "named-expression",
        "global-write",
        "nonlocal-write",
        "globals-write",
        "vars-write",
        "setattr-module-write",
        "exec-write",
        "function-binding",
        "async-function-binding",
        "class-binding",
        "import-binding",
        "from-import-binding",
        "wildcard-import",
        "exception-binding",
        "argument-binding",
        "imported-globals-update",
        "from-import-globals-update",
        "builtins-dict-globals-update",
        "dunder-setattr-write",
        "getattr-globals-update",
        "imported-getattr-globals-update",
        "type-var-binding",
        "type-var-tuple-binding",
        "param-spec-binding",
        "operator-attrgetter-globals-update",
        "imported-attrgetter-globals-update",
    ),
)
def test_source_authored_protected_name_writes_fail(
    tmp_path: Path, tail: str
) -> None:
    _write(tmp_path, tail)

    with pytest.raises(SurfaceContractError, match="EXPECTED_SKILLS"):
        binding.assert_bound_assignment(
            tmp_path,
            OWNER,
            CANDIDATE,
            [CANDIDATE],
            "EXPECTED_SKILLS",
        )


def test_exact_frozenset_binding_is_supported(tmp_path: Path) -> None:
    (tmp_path / "owner.py").write_text(
        f"EXPECTED_SKILLS = frozenset(({CANDIDATE!r},))\n",
        encoding="utf-8",
    )

    assert binding.read_bound_strings(
        tmp_path / "owner.py", "EXPECTED_SKILLS", OWNER["owner_id"]
    ) == [CANDIDATE]


@pytest.mark.parametrize("expression", ("[]", "{'css-language-profile'}"))
def test_mutable_final_collection_is_rejected(
    tmp_path: Path, expression: str
) -> None:
    (tmp_path / "owner.py").write_text(
        f"EXPECTED_SKILLS = {expression}\n",
        encoding="utf-8",
    )

    with pytest.raises(SurfaceContractError, match="immutable"):
        binding.read_bound_strings(
            tmp_path / "owner.py", "EXPECTED_SKILLS", OWNER["owner_id"]
        )
