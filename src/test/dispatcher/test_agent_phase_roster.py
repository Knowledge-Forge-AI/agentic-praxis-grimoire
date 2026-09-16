from __future__ import annotations

import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import tomllib

import pytest

from agent_phase import roster as roster_module
from agent_phase.request import EXECUTION_MODES, PHASE_TYPES
from agent_phase.roster import (
    ENDPOINTS_SOURCE,
    MAX_ROSTER_BYTES,
    ROUTES_SOURCE,
    Endpoint,
    RosterError,
    load_roster,
    validate_profiles,
)
from agent_phase_roster_fixtures import (
    SYNTHETIC_ENDPOINTS,
    SYNTHETIC_GENERATION,
    build_synthetic_roster,
    replace_once,
    write_roster_sources,
)


ROOT = Path(__file__).resolve().parents[3]


def roster_root(tmp_path: Path) -> Path:
    return build_synthetic_roster(tmp_path).root


def rewrite(root: Path, relative: Path, transform) -> None:
    path = root / relative
    original = path.read_text(encoding="utf-8")
    changed = transform(original)
    if changed == original:
        raise AssertionError(f"fixture mutation was a no-op: {relative}")
    path.write_text(changed, encoding="utf-8")


def test_canonical_roster_is_complete_and_provenance_is_byte_exact() -> None:
    roster = load_roster(ROOT)

    assert set(roster.routes) == {
        (phase_type, execution_mode)
        for phase_type in PHASE_TYPES
        for execution_mode in EXECUTION_MODES
    }
    endpoints_document = tomllib.loads(roster.endpoints_source.raw.decode("utf-8"))
    routes_document = tomllib.loads(roster.routes_source.raw.decode("utf-8"))
    assert roster.generation == endpoints_document["generation"]
    assert roster.generation == routes_document["generation"]
    assert roster.provenance() == {
        "schema": "agent-phase-roster-provenance-v1",
        "generation": roster.generation,
        "sources": {
            "endpoints": {
                "path": ENDPOINTS_SOURCE.as_posix(),
                "sha256": hashlib.sha256(
                    (ROOT / ENDPOINTS_SOURCE).read_bytes()
                ).hexdigest(),
            },
            "routes": {
                "path": ROUTES_SOURCE.as_posix(),
                "sha256": hashlib.sha256(
                    (ROOT / ROUTES_SOURCE).read_bytes()
                ).hexdigest(),
            },
        },
    }


def test_profile_validation_visits_every_endpoint_alias() -> None:
    roster = load_roster(ROOT)
    visited: list[tuple[str, Endpoint]] = []

    validate_profiles(roster, lambda alias, endpoint: visited.append((alias, endpoint)))

    assert visited == sorted(roster.endpoints.items())


@pytest.mark.parametrize(
    ("relative", "transform", "message"),
    [
        (
            ENDPOINTS_SOURCE,
            lambda text: "unexpected = true\n" + text,
            "top-level fields",
        ),
        (
            ROUTES_SOURCE,
            lambda text: "unexpected = true\n" + text,
            "top-level fields",
        ),
        (
            ENDPOINTS_SOURCE,
            lambda text: replace_once(
                text,
                '[endpoints.fixture-gemini-blue]\nprovider = "antigravity"',
                '[endpoints.fixture-gemini-blue]\nprovider = "other"',
            ),
            "unknown provider",
        ),
        (
            ENDPOINTS_SOURCE,
            lambda text: replace_once(
                text,
                'profile = "fixture-gemini-blue"',
                'profile = "fixture-gemini-blue"\nmodel = "forbidden"',
            ),
            "fields must be provider and profile",
        ),
        (
            ROUTES_SOURCE,
            lambda text: replace_once(
                text,
                '[routes.implementation_testing.normal]\nplan = "fixture-gemini-blue"',
                '[routes.implementation_testing.normal]\nplan = "missing-alias"',
            ),
            "unknown endpoint alias",
        ),
        (
            ROUTES_SOURCE,
            lambda text: replace_once(
                text,
                '[routes.implementation_testing.normal]\n'
                'plan = "fixture-gemini-blue"\n'
                'plan_review = "fixture-claude-review"\n'
                'work = "fixture-codex-primary"\n'
                'final_review = "fixture-codex-review"\n'
                'closeout = "fixture-claude-primary"',
                '[routes.implementation_testing.normal]\n'
                'plan = "fixture-gemini-blue"\n'
                'plan_review = "fixture-claude-review"\n'
                'work = "fixture-codex-primary"\n'
                'final_review = "fixture-codex-review"',
            ),
            "must contain exactly",
        ),
        (
            ROUTES_SOURCE,
            lambda text: replace_once(
                text,
                '[routes.implementation_testing.normal]\n'
                'plan = "fixture-gemini-blue"\n'
                'plan_review = "fixture-claude-review"\n'
                'work = "fixture-codex-primary"\n'
                'final_review = "fixture-codex-review"\n'
                'closeout = "fixture-claude-primary"',
                '[routes.implementation_testing.normal]\n'
                'plan = "fixture-gemini-blue"\n'
                'plan_review = "fixture-claude-review"\n'
                'work = "fixture-codex-primary"\n'
                'final_review = "fixture-codex-review"\n'
                'closeout = "fixture-claude-primary"\n'
                'extra = "fixture-claude-primary"',
            ),
            "must contain exactly",
        ),
        (
            ROUTES_SOURCE,
            lambda text: replace_once(
                text, "[routes.sysadmin.normal]", "[routes.unsupported.normal]"
            ),
            "phase types",
        ),
        (
            ROUTES_SOURCE,
            lambda text: replace_once(
                text,
                "[routes.sysadmin.normal]",
                "[routes.sysadmin.unsupported]",
            ),
            "modes for sysadmin",
        ),
        (
            ROUTES_SOURCE,
            lambda text: replace_once(
                text,
                '[routes.implementation_testing.normal]\nplan = "fixture-gemini-blue"',
                "[routes.implementation_testing.normal]\nplan = 7",
            ),
            "unknown endpoint alias",
        ),
        (
            ENDPOINTS_SOURCE,
            lambda text: replace_once(
                text,
                'profile = "fixture-gemini-blue"',
                'profile = "invalid/profile"',
            ),
            "invalid profile",
        ),
    ],
)
def test_roster_mutations_fail_closed(
    tmp_path: Path, relative: Path, transform, message: str
) -> None:
    root = roster_root(tmp_path)
    rewrite(root, relative, transform)

    with pytest.raises(RosterError, match=message):
        load_roster(root)


@pytest.mark.parametrize("relative", [ENDPOINTS_SOURCE, ROUTES_SOURCE])
def test_missing_roster_file_fails_closed(tmp_path: Path, relative: Path) -> None:
    root = roster_root(tmp_path)
    (root / relative).unlink()

    with pytest.raises(RosterError, match="cannot read tracked roster"):
        load_roster(root)


@pytest.mark.parametrize("relative", [ENDPOINTS_SOURCE, ROUTES_SOURCE])
def test_malformed_roster_file_fails_closed(tmp_path: Path, relative: Path) -> None:
    root = roster_root(tmp_path)
    (root / relative).write_text("[unterminated\n", encoding="utf-8")

    with pytest.raises(RosterError, match="not valid TOML"):
        load_roster(root)


def test_generation_must_match_across_both_sources(tmp_path: Path) -> None:
    fixture = build_synthetic_roster(tmp_path)
    root = fixture.root
    rewrite(
        root,
        ROUTES_SOURCE,
        lambda text: replace_once(
            text,
            f"generation = {fixture.generation}",
            f"generation = {fixture.generation + 1}",
        ),
    )

    with pytest.raises(RosterError, match="generation.*match"):
        load_roster(root)


@pytest.mark.parametrize(
    "replacement",
    ["generation = 0", "generation = -1", "generation = true", 'generation = "1"'],
)
def test_generation_is_a_positive_bounded_integer(
    tmp_path: Path, replacement: str
) -> None:
    root = roster_root(tmp_path)
    rewrite(
        root,
        ENDPOINTS_SOURCE,
        lambda text: replace_once(
            text, f"generation = {SYNTHETIC_GENERATION}", replacement
        ),
    )

    with pytest.raises(RosterError, match="generation"):
        load_roster(root)


def test_oversized_regular_file_is_rejected_without_path_read_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = roster_root(tmp_path)
    path = root / ENDPOINTS_SOURCE
    with path.open("wb") as handle:
        handle.truncate(MAX_ROSTER_BYTES + 1)

    def forbidden_read_bytes(_path: Path) -> bytes:
        raise AssertionError("oversized roster was read before its size was checked")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read_bytes)
    with pytest.raises(RosterError, match="exceeds"):
        load_roster(root)


def _load_roster_subprocess(root: Path) -> subprocess.CompletedProcess[str]:
    program = """
from pathlib import Path
from agent_phase.roster import RosterError, load_roster
import sys
try:
    load_roster(Path(sys.argv[1]))
except RosterError as error:
    print(error, file=sys.stderr)
    raise SystemExit(0)
raise SystemExit(3)
"""
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.fspath(ROOT / "libexec")
    return subprocess.run(
        [sys.executable, "-c", program, os.fspath(root)],
        capture_output=True,
        text=True,
        timeout=2,
        env=environment,
        check=False,
    )


@pytest.mark.parametrize("kind", ["fifo", "socket"])
def test_non_regular_roster_nodes_are_rejected_without_blocking(
    kind: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix="roster-", dir="/tmp") as temporary:
        root = roster_root(Path(temporary))
        path = root / ENDPOINTS_SOURCE
        path.unlink()
        bound_socket = None
        if kind == "fifo":
            os.mkfifo(path)
        else:
            bound_socket = socket.socket(socket.AF_UNIX)
            bound_socket.bind(os.fspath(path))
        try:
            completed = _load_roster_subprocess(root)
        finally:
            if bound_socket is not None:
                bound_socket.close()

    assert completed.returncode == 0
    assert "regular file" in completed.stderr


def test_symlinked_roster_leaf_is_rejected(tmp_path: Path) -> None:
    root = roster_root(tmp_path)
    path = root / ENDPOINTS_SOURCE
    target = path.with_name("real-endpoints.toml")
    path.rename(target)
    path.symlink_to(target.name)

    with pytest.raises(RosterError, match="symlink"):
        load_roster(root)


def test_symlinked_roster_ancestor_is_rejected(tmp_path: Path) -> None:
    root = roster_root(tmp_path)
    common = root / "common"
    target = root / "real-common"
    common.rename(target)
    common.symlink_to(target.name, target_is_directory=True)

    with pytest.raises(RosterError, match="symlink"):
        load_roster(root)


def test_hard_linked_roster_is_rejected(tmp_path: Path) -> None:
    root = roster_root(tmp_path)
    path = root / ENDPOINTS_SOURCE
    original = path.with_name("original-endpoints.toml")
    path.rename(original)
    os.link(original, path)

    with pytest.raises(RosterError, match="single-link"):
        load_roster(root)


def test_file_replacement_during_set_capture_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = roster_root(tmp_path)
    path = root / ENDPOINTS_SOURCE
    replacement = path.with_name("replacement-endpoints.toml")
    replacement.write_bytes(path.read_bytes())
    real_read = roster_module.os.read
    replaced = False

    def replacing_read(descriptor: int, size: int) -> bytes:
        nonlocal replaced
        chunk = real_read(descriptor, size)
        if chunk and not replaced:
            replaced = True
            os.replace(replacement, path)
        return chunk

    monkeypatch.setattr(roster_module.os, "read", replacing_read)

    with pytest.raises(RosterError, match="changed during capture"):
        load_roster(root)


def test_roster_snapshot_is_deeply_immutable() -> None:
    roster = load_roster(ROOT)
    key = ("implementation_testing", "normal")

    with pytest.raises(TypeError):
        roster.endpoints["changed"] = Endpoint("codex", "sysadmin-primary")
    with pytest.raises(TypeError):
        roster.routes[key]["work"] = "changed"

    aliases = roster.route_aliases(*key)
    aliases["work"] = "caller-local-change"
    assert roster.route_aliases(*key)["work"] != "caller-local-change"


@pytest.mark.parametrize(
    ("execution_mode", "wrong_alias", "required_provider"),
    [
        ("claude_only", "fixture-codex-primary", "claude"),
        ("codex_only", "fixture-gemini-blue", "codex"),
        ("gemini_only", "fixture-claude-primary", "antigravity"),
    ],
)
def test_named_only_modes_enforce_provider_family_in_product_validation(
    tmp_path: Path,
    execution_mode: str,
    wrong_alias: str,
    required_provider: str,
) -> None:
    fixture = build_synthetic_roster(tmp_path)
    routes = {key: dict(value) for key, value in fixture.routes.items()}
    routes[("implementation_testing", execution_mode)]["work"] = wrong_alias
    write_roster_sources(
        fixture.root,
        SYNTHETIC_ENDPOINTS,
        routes,
        generation=fixture.generation,
    )

    with pytest.raises(RosterError, match=f"must use only {required_provider}"):
        load_roster(fixture.root)
