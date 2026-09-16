#!/usr/bin/env python3
"""Install or verify managed dispatcher-roster operator directions."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import secrets
import stat
import sys


sys.path.insert(0, os.fspath(Path(__file__).resolve().parents[1] / "libexec"))

from agent_phase.roster import (
    RosterError,
    load_roster,
)


SOURCE_ROOT = Path(__file__).resolve().parents[1]
ROOT_README = Path("README.md")
DISPATCHER_README = Path("common/dispatcher/README.md")
ROOT_ANCHOR = "## Dispatcher roster\n"
DISPATCHER_ANCHOR = "## Operator roster workflow\n"
ROOT_BEGIN = "<!-- BEGIN MANAGED DISPATCHER ROSTER QUICK START -->"
ROOT_END = "<!-- END MANAGED DISPATCHER ROSTER QUICK START -->"
DISPATCHER_BEGIN = "<!-- BEGIN MANAGED DISPATCHER ROSTER OPERATIONS -->"
DISPATCHER_END = "<!-- END MANAGED DISPATCHER ROSTER OPERATIONS -->"

ROOT_BODY = """## Dispatcher roster quick start

Edit `common/dispatcher/endpoints.toml` for provider/profile aliases and
`common/dispatcher/routes.toml` for stage-slot assignments. Advance their shared
positive `generation` together. Provider profiles own model, effort, and runtime
semantics; roster files do not own security-sensitive launch controls.
Select `execution_mode` from the current operator instruction, not a durable
default. Follow the self-contained
[operator roster workflow](common/dispatcher/README.md#operator-roster-workflow)
for provider-free validation, evidence inspection, and result-repair boundaries.
APGR owns single-phase execution; JACA owns cross-phase orchestration. Neither
JACA nor Agent-Security is a mandatory local prototype runtime dependency."""

DISPATCHER_BODY = """Edit `endpoints.toml` when adding or renaming a stable endpoint alias. Each
alias contains only `provider` and `profile`. Edit `routes.toml` when changing a
stage roster; every supported phase/mode table must contain exactly the five
standard slots. Provider profiles own model, effort, and runtime semantics;
endpoints alias provider plus profile; routes alias phase, mode, and stage.
Do not copy model or reasoning-effort values into either roster file.

Both files carry one positive `generation`. Advance it in both files as one
operator edit; a mismatch is unusable roster state and dispatch fails closed.
Select `execution_mode` from the explicit current operator instruction for each
run. These directions define no active default and do not change routing policy.

APGR owns the portable single-phase runtime and its provider/profile catalogs.
Agent-Central owns workstation composition; its checkout and link-installation
procedures are not APGR runtime prerequisites. See
[ADR 0058](../../docs/adr/2026/09/0058-apgr-jaca-product-boundary-and-runtime-ownership.md)
for the APGR/JACA ownership boundary. Permanent cross-phase orchestration,
capacity selection, and fail-closed brokerage remain JACA concerns.

Keep security-sensitive controls outside the roster. Never add executables,
arbitrary paths, environment variables, permissions, approval or sandbox
settings, hooks, credentials, or other launch/security controls to these files.
Agent-Security retains its security-control ownership when integrated, but
Agent-Security and JACA are not mandatory dependencies of the availability-first
local prototype. Their absence, staleness, or failure does not block local
prototype launch; optional hardening may observe, warn, or enhance.

Before dispatch, run from the APGR repository root using its qualified Python:

```bash
python3 tools/add_dispatcher_roster_operator_directions.py --check
python3 -m pytest -q src/test/dispatcher/test_agent_phase_roster.py src/test/dispatcher/test_agent_phase_routing.py
bin/agent-phase-resolve path/to/request.json
bin/agent-phase-dispatch --help
```

The first command closed-validates both canonical TOML files and checks these
managed directions. The tests cover completeness, referential integrity,
provider-profile validation, and behavioral routing. Resolution is provider-free
and exposes selected aliases, profile-derived intelligence, the shared
generation, repository-relative source paths, and SHA-256 source digests.
Inspect that evidence before using a changed roster. A passing local check does
not authorize dispatch, publication, or workstation installation.

For explicit result repair, use the APGR runtime binary with the working
directory set to the source phase's target repository. Retain the source run as
immutable evidence. An operator commit message supplies explicit finalization
authority; `--result-repair-commit-subject` is restricted to explicit
`--from-stage result-repair` with commit-local or publish finalization. It is
unavailable to ordinary dispatch, automatic repair, other resume modes, and
checkpoint finalization. Inspect the runtime's `--help` for supported options;
do not rewrite retained evidence or infer permission to finalize from a repair.

Phase resume routes unperformed suffix stages from the current validated roster
snapshot while preserving historical execution evidence for completed prefix
stages in an immutable per-stage ledger. Historical V4 and V5 source runs are
adapted upon resume. Finalization-only operations require no fabricated current
provider route and do not load the current roster.

Producer requests remain strict JSON. Nonce-fenced provider review and terminal
result objects accept a JSONC-compatible subset: strict JSON plus `//` comments,
`/* ... */` comments, and trailing commas. Duplicate keys, prose, YAML, a second
object, malformed comments, unknown fields, and identity/domain violations remain
rejected. This is not a general JSON5 contract."""


class DirectionError(RuntimeError):
    """The documentation cannot be safely reconciled."""


def _managed_text(begin: str, body: str, end: str) -> str:
    return f"{begin}\n{body.rstrip()}\n{end}\n"


def _updated_document(
    text: str,
    *,
    anchor: str,
    begin: str,
    body: str,
    end: str,
) -> str:
    begin_count = text.count(begin)
    end_count = text.count(end)
    replacement = _managed_text(begin, body, end)
    if begin_count == end_count == 0:
        if text.count(anchor) != 1:
            raise DirectionError(f"documentation anchor is missing or ambiguous: {anchor!r}")
        before, after = text.split(anchor, 1)
        tail = after.lstrip("\n")
        separator = "\n" if tail else ""
        return before + anchor + "\n" + replacement + separator + tail
    if begin_count != 1 or end_count != 1:
        raise DirectionError("managed documentation markers are missing or ambiguous")
    start = text.index(begin)
    end_at = text.index(end)
    if end_at < start:
        raise DirectionError("managed documentation markers are out of order")
    finish = end_at + len(end)
    while finish < len(text) and text[finish] == "\n":
        finish += 1
    tail = text[finish:]
    separator = "\n" if tail else ""
    return text[:start] + replacement + separator + tail


def _validate_document_path(root: Path, relative: Path) -> os.stat_result:
    try:
        root_stat = os.lstat(root)
    except OSError as error:
        raise DirectionError(f"cannot inspect documentation root: {error}") from error
    if stat.S_ISLNK(root_stat.st_mode):
        raise DirectionError("documentation root is a symlink")
    if not stat.S_ISDIR(root_stat.st_mode):
        raise DirectionError("documentation root is not a directory")
    current = root
    for index, component in enumerate(relative.parts):
        current = current / component
        try:
            value = os.lstat(current)
        except OSError as error:
            raise DirectionError(
                f"cannot inspect documentation target {relative}: {error}"
            ) from error
        if stat.S_ISLNK(value.st_mode):
            traversed = Path(*relative.parts[: index + 1]).as_posix()
            raise DirectionError(f"documentation path contains a symlink: {traversed}")
        if index < len(relative.parts) - 1 and not stat.S_ISDIR(value.st_mode):
            raise DirectionError(
                f"documentation ancestor is not a directory: {current}"
            )
    if not stat.S_ISREG(value.st_mode):
        raise DirectionError(f"documentation target is not a regular file: {relative}")
    return value


def _identity(value: os.stat_result) -> tuple[int, ...]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_document(root: Path, relative: Path) -> tuple[str, int, tuple[int, ...]]:
    path = root / relative
    named = _validate_document_path(root, relative)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise DirectionError(f"cannot read documentation target {relative}: {error}") from error
    try:
        opened = os.fstat(descriptor)
        if _identity(opened) != _identity(named):
            raise DirectionError(f"documentation target moved while opening: {relative}")
        with os.fdopen(descriptor, "r", encoding="utf-8", newline="") as handle:
            descriptor = -1
            text = handle.read()
        return text, opened.st_mode, _identity(opened)
    except UnicodeDecodeError as error:
        raise DirectionError(f"cannot read documentation target {relative}: {error}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _atomic_replace(
    root: Path,
    relative: Path,
    text: str,
    mode: int,
    expected_identity: tuple[int, ...],
) -> None:
    path = root / relative
    parent = path.parent
    current = _validate_document_path(root, relative)
    if _identity(current) != expected_identity:
        raise DirectionError(f"documentation target changed before replacement: {relative}")
    parent_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        parent_descriptor = os.open(parent, parent_flags)
    except OSError as error:
        raise DirectionError(f"cannot open documentation parent {parent}: {error}") from error
    descriptor = -1
    temporary_name = ""
    try:
        named_parent = os.lstat(parent)
        opened_parent = os.fstat(parent_descriptor)
        if (named_parent.st_dev, named_parent.st_ino) != (
            opened_parent.st_dev,
            opened_parent.st_ino,
        ):
            raise DirectionError(
                f"documentation parent moved before replacement: {relative}"
            )
        temporary_flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        for _attempt in range(32):
            temporary_name = f".{path.name}.{secrets.token_hex(8)}"
            try:
                descriptor = os.open(
                    temporary_name,
                    temporary_flags,
                    0o600,
                    dir_fd=parent_descriptor,
                )
                break
            except FileExistsError:
                continue
        else:
            raise DirectionError(
                f"cannot allocate temporary documentation target: {relative}"
            )
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            descriptor = -1
            handle.write(text)
            handle.flush()
            os.fchmod(handle.fileno(), stat.S_IMODE(mode))
            os.fsync(handle.fileno())
        if _identity(_validate_document_path(root, relative)) != expected_identity:
            raise DirectionError(
                f"documentation target changed before replacement: {relative}"
            )
        os.replace(
            temporary_name,
            path.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
        temporary_name = ""
        os.fsync(parent_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_name:
            try:
                os.unlink(temporary_name, dir_fd=parent_descriptor)
            except FileNotFoundError:
                pass
        os.close(parent_descriptor)


def _plan_update(
    root: Path,
    relative: Path,
    *,
    anchor: str,
    begin: str,
    body: str,
    end: str,
) -> tuple[str, int, tuple[int, ...]] | None:
    if relative == ROOT_README and not (root / relative).exists():
        return None
    text, mode, identity = _read_document(root, relative)
    if relative == ROOT_README and anchor not in text and begin not in text:
        return None
    updated = _updated_document(
        text, anchor=anchor, begin=begin, body=body, end=end
    )
    if updated == text:
        return None
    return updated, mode, identity


def apply(root: Path, *, check: bool) -> list[Path]:
    try:
        load_roster(root)
    except RosterError as error:
        raise DirectionError(f"refusing to document unusable roster: {error}") from error
    planned: list[tuple[Path, str, int, tuple[int, ...]]] = []
    specifications = (
        (ROOT_README, ROOT_ANCHOR, ROOT_BEGIN, ROOT_BODY, ROOT_END),
        (
            DISPATCHER_README,
            DISPATCHER_ANCHOR,
            DISPATCHER_BEGIN,
            DISPATCHER_BODY,
            DISPATCHER_END,
        ),
    )
    for relative, anchor, begin, body, end in specifications:
        update = _plan_update(
            root,
            relative,
            anchor=anchor,
            begin=begin,
            body=body,
            end=end,
        )
        if update is not None:
            planned.append((relative, *update))
    if not check:
        for relative, text, mode, identity in planned:
            _atomic_replace(root, relative, text, mode, identity)
    return [relative for relative, _text, _mode, _identity_value in planned]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=SOURCE_ROOT)
    arguments = parser.parse_args(argv)
    root = Path(os.path.abspath(os.fspath(arguments.root)))
    try:
        changed = apply(root, check=arguments.check)
    except DirectionError as error:
        print(f"add-dispatcher-roster-directions: {error}", file=sys.stderr)
        return 2
    if arguments.check and changed:
        paths = ", ".join(path.as_posix() for path in changed)
        print(f"add-dispatcher-roster-directions: managed documentation drift: {paths}", file=sys.stderr)
        return 1
    if changed:
        print("updated " + ", ".join(path.as_posix() for path in changed))
    else:
        print("dispatcher roster operator directions are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
