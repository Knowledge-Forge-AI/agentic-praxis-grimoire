"""Canonical topology and router-map validation for APG skills."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re
import stat


CANONICAL_NAMESPACES = frozenset({"chatgpt"})
GENERAL_ROUTER_NAME = "agentic-praxis-grimoire-workflow"
CHATGPT_ROUTER_NAME = "chatgpt-manager-workflow"
CAPABILITY_MAP_PATH = Path("references/capability-map.json")
EXACT_TRANSITION_SURFACES = frozenset(
    {
        "canonical",
        "catalog",
        "projections",
        "stable_maturity",
        "provisional_maturity",
        "general_routes",
        "chatgpt_local_routes",
        "checked_routes",
        "project_selections",
        "current_release",
        "test_inventory",
        "profile_lifecycle",
    }
)
PROFILE_LIFECYCLE_STATES = frozenset(
    {
        "not-applicable",
        "repair-required",
        "retained-provisional",
        "retained-stable",
        "provisionally-integrated",
        "provisionally-integrated-with-known-debt",
        "accepted-integration-rolled-back",
    }
)
PROFILE_ADR_STATES = frozenset(
    {"not-applicable", "Proposed", "Accepted with amendment"}
)
PROFILE_INTEGRATION_STATES = frozenset({"integrated", "unintegrated"})
ROOT_GO_SOURCE_NAME = re.compile(r"[a-z][a-z0-9_]*\.go")

IssueReporter = Callable[[str, str, str, str, str], None]
NameValidator = Callable[[str], bool]


@dataclass(frozen=True, order=True)
class ProfileLifecycleRow:
    """One current canonical profile's independently owned lifecycle facts."""

    profile: str
    lifecycle: str
    adr_status: str
    integration: str
    lifecycle_owners: tuple[str, ...] = ()

    def text(self) -> str:
        owners = ",".join(self.lifecycle_owners) or "none"
        return "|".join(
            (self.profile, self.lifecycle, self.adr_status, self.integration, owners)
        )


_LIFECYCLE_FIELD = re.compile(r"Lifecycle: `([a-z][a-z0-9-]*)`\.")
_LIFECYCLE_ADR_FIELD = re.compile(
    r"Lifecycle ADR: `(not-applicable|Proposed|Accepted with amendment)`\."
)


def _exact_lifecycle_owner(path: Path) -> tuple[str, str] | None:
    """Parse one optional lifecycle owner using exact anchored fields."""

    text = path.read_text(encoding="utf-8")
    lifecycle_lines = [line for line in text.splitlines() if line.startswith("Lifecycle:")]
    adr_lines = [line for line in text.splitlines() if line.startswith("Lifecycle ADR:")]
    if not lifecycle_lines and not adr_lines:
        return None
    if len(lifecycle_lines) != 1 or len(adr_lines) != 1:
        raise ValueError(f"lifecycle owner fields are incomplete or duplicated: {path}")
    lifecycle = _LIFECYCLE_FIELD.fullmatch(lifecycle_lines[0])
    adr_status = _LIFECYCLE_ADR_FIELD.fullmatch(adr_lines[0])
    if lifecycle is None or adr_status is None:
        raise ValueError(f"lifecycle owner fields are not exact and anchored: {path}")
    if lifecycle.group(1) not in PROFILE_LIFECYCLE_STATES - {"not-applicable"}:
        raise ValueError(f"lifecycle owner has an unknown lifecycle value: {path}")
    return lifecycle.group(1), adr_status.group(1)


def observe_profile_lifecycle_rows(
    root: Path,
    canonical_paths: Mapping[str, Path],
    integrated_names: Sequence[str],
) -> tuple[ProfileLifecycleRow, ...]:
    """Observe lifecycle owners independently from integration membership."""

    profile_paths = {
        name: path for name, path in canonical_paths.items() if name.endswith("-profile")
    }
    integrated = tuple(integrated_names)
    if len(integrated) != len(set(integrated)) or not set(integrated).issubset(
        profile_paths
    ):
        raise ValueError("integrated profile names are duplicated or unknown")
    rows: list[ProfileLifecycleRow] = []
    for name in sorted(profile_paths):
        candidates = (
            root / profile_paths[name] / "SKILL.md",
            root / "docs" / "specs" / f"{name}.md",
        )
        owners: list[tuple[str, str, str]] = []
        for path in candidates:
            if not path.is_file():
                continue
            value = _exact_lifecycle_owner(path)
            if value is not None:
                owners.append((*value, path.relative_to(root).as_posix()))
        if owners and len({owner[:2] for owner in owners}) != 1:
            raise ValueError(f"lifecycle owners disagree for {name}")
        lifecycle, adr_status = owners[0][:2] if owners else (
            "not-applicable",
            "not-applicable",
        )
        rows.append(
            ProfileLifecycleRow(
                name,
                lifecycle,
                adr_status,
                "integrated" if name in integrated else "unintegrated",
                tuple(sorted(owner[2] for owner in owners)),
            )
        )
    return tuple(rows)


def complete_profile_lifecycle_rows(
    canonical_names: Sequence[str],
    rows: Sequence[ProfileLifecycleRow],
    *,
    required_node_row: ProfileLifecycleRow,
) -> tuple[str, ...]:
    """Bind one lifecycle row to every canonical profile leaf.

    Canonical discovery owns the domain.  Catalog membership and maturity are
    deliberately not accepted as substitutes for this complete map.
    """

    names = tuple(canonical_names)
    if (
        names != tuple(sorted(set(names)))
        or not names
        or any(not name.endswith("-profile") for name in names)
    ):
        raise ValueError("canonical profile names are not exact sorted leaves")
    if len(rows) != len(set(rows)):
        raise ValueError("profile lifecycle rows contain a duplicate")
    by_name: dict[str, ProfileLifecycleRow] = {}
    for row in rows:
        if (
            not row.profile
            or not row.lifecycle
            or not row.adr_status
            or not row.integration
            or row.lifecycle not in PROFILE_LIFECYCLE_STATES
            or row.adr_status not in PROFILE_ADR_STATES
            or row.integration not in PROFILE_INTEGRATION_STATES
            or row.lifecycle_owners != tuple(sorted(set(row.lifecycle_owners)))
            or (
                row.lifecycle == "not-applicable"
                and (row.adr_status != "not-applicable" or row.lifecycle_owners)
            )
            or (
                row.lifecycle != "not-applicable"
                and (row.adr_status == "not-applicable" or not row.lifecycle_owners)
            )
            or any(
                "|" in value
                for value in (
                    row.profile,
                    row.lifecycle,
                    row.adr_status,
                    row.integration,
                    *row.lifecycle_owners,
                )
            )
        ):
            raise ValueError("profile lifecycle row is malformed")
        if row.profile in by_name:
            raise ValueError("profile lifecycle map contains a duplicate profile")
        by_name[row.profile] = row
    if tuple(sorted(by_name)) != names:
        raise ValueError("profile lifecycle map is incomplete or has an unknown profile")
    if by_name.get(required_node_row.profile) != required_node_row:
        raise ValueError("Node lifecycle row does not match the current owner")
    return tuple(by_name[name].text() for name in names)


def exact_topology_transition(
    baseline: Mapping[str, Sequence[str]],
    observed: Mapping[str, Sequence[str]],
    deltas: Mapping[str, tuple[Sequence[str], Sequence[str]]],
) -> dict[str, tuple[str, ...]]:
    """Require an exact member-for-member transition on every owned surface."""

    if set(baseline) != EXACT_TRANSITION_SURFACES:
        raise ValueError("baseline topology surfaces are incomplete")
    if set(observed) != EXACT_TRANSITION_SURFACES:
        raise ValueError("observed topology surfaces are incomplete")
    if not set(deltas).issubset(EXACT_TRANSITION_SURFACES):
        raise ValueError("transition delta names an unknown topology surface")

    normalized: dict[str, tuple[str, ...]] = {}
    for surface in sorted(EXACT_TRANSITION_SURFACES):
        before = tuple(baseline[surface])
        after = tuple(observed[surface])
        if (
            before != tuple(sorted(set(before)))
            or after != tuple(sorted(set(after)))
        ):
            raise ValueError(f"{surface} rows are not exact sorted unique sets")
        removed_values, added_values = deltas.get(surface, ((), ()))
        removed = tuple(removed_values)
        added = tuple(added_values)
        if (
            removed != tuple(sorted(set(removed)))
            or added != tuple(sorted(set(added)))
            or set(removed) & set(added)
            or not set(removed).issubset(before)
        ):
            raise ValueError(f"{surface} delta is malformed")
        expected = tuple(sorted((set(before) - set(removed)) | set(added)))
        if after != expected:
            raise ValueError(f"{surface} transition is not the exact baseline delta")
        normalized[surface] = after
    return normalized


def frontmatter_name(path: Path) -> str:
    """Return the exact leaf name declared by a canonical SKILL.md."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ValueError(f"skill is unreadable: {path.parent.name}") from error
    if not lines or lines[0] != "---":
        raise ValueError(f"skill frontmatter is malformed: {path.parent.name}")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError(
            f"skill frontmatter is unterminated: {path.parent.name}"
        ) from error
    names = [
        line.removeprefix("name:").strip()
        for line in lines[1:end]
        if line.startswith("name:")
    ]
    if names != [path.parent.name]:
        raise ValueError(
            f"skill name is malformed or mismatched: {path.parent.name}"
        )
    return names[0]


def policy_skill_paths(policy: Mapping[str, object]) -> dict[str, Path]:
    """Return exact direct or ChatGPT-nested paths from release policy."""
    skill_values = policy.get("required_skills")
    projection_values = policy.get("required_projections")
    if (
        not isinstance(skill_values, list)
        or not skill_values
        or skill_values != sorted(set(skill_values))
        or not isinstance(projection_values, list)
        or not projection_values
        or projection_values != sorted(set(projection_values))
    ):
        raise ValueError("skill paths are malformed")

    paths: dict[str, Path] = {}
    pattern = re.compile(
        r"skills/(?:(?:chatgpt)/)?"
        r"([a-z0-9]+(?:-[a-z0-9]+)*)/SKILL\.md"
    )
    for value in skill_values:
        match = pattern.fullmatch(value) if isinstance(value, str) else None
        if match is None or match.group(1) in paths:
            raise ValueError("required_skills is malformed")
        paths[match.group(1)] = Path(value).parent

    projection_names: list[str] = []
    projection_pattern = re.compile(
        r"\.agents/skills/([a-z0-9]+(?:-[a-z0-9]+)*)"
    )
    for value in projection_values:
        match = (
            projection_pattern.fullmatch(value)
            if isinstance(value, str)
            else None
        )
        if match is None:
            raise ValueError("required_projections is malformed")
        projection_names.append(match.group(1))
    if tuple(sorted(paths)) != tuple(projection_names):
        raise ValueError("skill and projection sets disagree")
    return {name: paths[name] for name in sorted(paths)}


def _relative(path: Path, root: Path) -> str:
    try:
        value = path.relative_to(root).as_posix()
    except ValueError:
        return "."
    return value or "."


def _ordinary_directory(path: Path) -> bool:
    try:
        return path.is_dir() and not path.is_symlink()
    except OSError:
        return False


def _ordinary_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode) and not path.is_symlink()
    except OSError:
        return False


def discover_canonical_leaves(
    root: Path,
    skills: Path,
    report: IssueReporter,
) -> tuple[Path, ...]:
    """Discover direct and accepted namespace leaves without counting owners."""
    try:
        entries = sorted(skills.iterdir(), key=lambda item: item.name)
    except OSError:
        entries = []
    leaves: list[Path] = []
    for entry in entries:
        if entry.name == "README.md":
            continue
        if entry.name not in CANONICAL_NAMESPACES:
            if ROOT_GO_SOURCE_NAME.fullmatch(entry.name) and _ordinary_file(entry):
                continue
            if entry.is_dir():
                leaves.append(entry)
                if entry.is_symlink():
                    report(
                        "APG004",
                        _relative(entry, root),
                        "canonical-directory-real",
                        "canonical skill directory is a symbolic link",
                        "restore an ordinary direct-child canonical directory",
                    )
                continue
            report(
                "APG003",
                _relative(entry, root),
                "skills-root-entry",
                "unexpected non-directory entry exists under skills",
                "remove it or move its content into an authorized owner",
            )
            continue

        leaves.extend(_discover_namespace_leaves(root, entry, report))
    return tuple(leaves)


def canonical_skill_paths(root: Path, skills: Path) -> dict[str, Path]:
    """Return the exact named direct and accepted nested canonical paths."""
    diagnostic_codes: list[str] = []
    leaves = discover_canonical_leaves(
        root,
        skills,
        lambda code, *_details: diagnostic_codes.append(code),
    )
    if diagnostic_codes:
        raise ValueError(
            f"canonical skill topology is invalid: {diagnostic_codes[0]}"
        )
    paths: dict[str, Path] = {}
    for leaf in leaves:
        name = frontmatter_name(leaf / "SKILL.md")
        if name in paths:
            raise ValueError("canonical skill set contains a duplicate name")
        try:
            paths[name] = leaf.relative_to(root)
        except ValueError as error:
            raise ValueError(
                "canonical skill path escapes its public release"
            ) from error
    return {name: paths[name] for name in sorted(paths)}


def _discover_namespace_leaves(
    root: Path,
    namespace: Path,
    report: IssueReporter,
) -> tuple[Path, ...]:
    if not _ordinary_directory(namespace):
        report(
            "APG036",
            _relative(namespace, root),
            "canonical-namespace-shape",
            "canonical namespace is missing, a symlink, or not an ordinary directory",
            "restore the declared ordinary namespace directory",
        )
        return ()
    try:
        entries = sorted(namespace.iterdir(), key=lambda item: item.name)
    except OSError:
        entries = []
    leaves: list[Path] = []
    for leaf in entries:
        relative = _relative(leaf, root)
        if leaf.name == "SKILL.md":
            report(
                "APG036",
                relative,
                "canonical-namespace-shape",
                "namespace directory may not declare a SKILL.md",
                "remove the namespace-level SKILL.md",
            )
            continue
        if not leaf.is_dir():
            report(
                "APG036",
                relative,
                "canonical-namespace-shape",
                "namespace contains an unsupported non-directory entry",
                "remove it or move it below one canonical nested leaf",
            )
            continue
        leaves.append(leaf)
        if leaf.is_symlink():
            report(
                "APG004",
                relative,
                "canonical-directory-real",
                "canonical skill directory is a symbolic link",
                "restore an ordinary nested canonical directory",
            )
            continue
        if not _ordinary_file(leaf / "SKILL.md") and _has_nested_directory(leaf):
            report(
                "APG037",
                relative,
                "canonical-leaf-depth",
                "unsupported namespace depth exists below a canonical leaf owner",
                "retain only skills/<name> and skills/chatgpt/<name> leaves",
            )
    return tuple(leaves)


def _has_nested_directory(leaf: Path) -> bool:
    try:
        return any(child.is_dir() for child in leaf.iterdir())
    except OSError:
        return False


def _load_capability_map(
    root: Path,
    leaf: Path,
    router_name: str,
    valid_name: NameValidator,
    report: IssueReporter,
) -> tuple[str, ...] | None:
    map_path = leaf / CAPABILITY_MAP_PATH
    relative = _relative(map_path, root)
    if not _ordinary_file(map_path):
        report(
            "APG038",
            relative,
            "router-map-contract",
            f"required capability map is missing for {router_name!r}",
            "restore the router-owned capability map",
        )
        return None
    try:
        value = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        value = None
    if (
        not isinstance(value, dict)
        or set(value) != {"capabilities", "router_name", "schema_version"}
        or value.get("schema_version") != 1
        or value.get("router_name") != router_name
        or not isinstance(value.get("capabilities"), list)
    ):
        report(
            "APG038",
            relative,
            "router-map-contract",
            f"capability map metadata is invalid for {router_name!r}",
            "restore the exact schema-version-1 router map",
        )
        return None
    capabilities = value["capabilities"]
    names: list[str] = []
    valid = True
    for capability in capabilities:
        if (
            not isinstance(capability, dict)
            or set(capability) != {"capability_class", "name", "trigger"}
            or not isinstance(capability.get("name"), str)
            or not valid_name(capability["name"])
            or not isinstance(capability.get("capability_class"), str)
            or not capability["capability_class"].strip()
            or not isinstance(capability.get("trigger"), str)
            or not capability["trigger"].strip()
        ):
            valid = False
            continue
        names.append(capability["name"])
    if not valid or names != sorted(names) or len(names) != len(set(names)):
        report(
            "APG038",
            relative,
            "router-map-contract",
            f"capability entries are invalid for {router_name!r}",
            "retain sorted unique complete capability entries",
        )
        return None
    return tuple(names)


def check_router_maps(
    root: Path,
    canonical: Mapping[str, Path],
    valid_name: NameValidator,
    report: IssueReporter,
) -> None:
    """Validate historical general-only and current general/subrouter maps."""
    general_leaf = canonical.get(GENERAL_ROUTER_NAME)
    if general_leaf is None:
        return
    skills = root / "skills"
    if _relative(general_leaf, skills) != GENERAL_ROUTER_NAME:
        report(
            "APG038",
            _relative(general_leaf, root),
            "router-map-contract",
            "general router is not owned by its direct canonical path",
            "restore the general router as a direct canonical leaf",
        )
        return
    general_names = _load_capability_map(
        root,
        general_leaf,
        GENERAL_ROUTER_NAME,
        valid_name,
        report,
    )
    if general_names is None:
        return

    chatgpt_leaf = canonical.get(CHATGPT_ROUTER_NAME)
    nested_names = {
        name
        for name, path in canonical.items()
        if _relative(path, skills).startswith("chatgpt/")
    }
    if chatgpt_leaf is None:
        if nested_names:
            report(
                "APG038",
                _relative(general_leaf / CAPABILITY_MAP_PATH, root),
                "router-map-contract",
                "ChatGPT-nested leaves exist without the required subrouter",
                "restore the ChatGPT subrouter and its local capability map",
            )
            return
        expected_general = set(canonical) - {GENERAL_ROUTER_NAME}
        if set(general_names) != expected_general:
            report(
                "APG038",
                _relative(general_leaf / CAPABILITY_MAP_PATH, root),
                "router-map-contract",
                "general router entries do not equal the routable canonical leaves",
                "restore one exact entry per non-router canonical leaf",
            )
        return

    if (
        _relative(chatgpt_leaf, skills)
        != f"chatgpt/{CHATGPT_ROUTER_NAME}"
    ):
        report(
            "APG038",
            _relative(chatgpt_leaf, root),
            "router-map-contract",
            "ChatGPT router is not owned by its accepted nested canonical path",
            "restore the ChatGPT router below skills/chatgpt",
        )
        return
    expected_general = (
        set(canonical)
        - {GENERAL_ROUTER_NAME}
        - (nested_names - {CHATGPT_ROUTER_NAME})
    )
    expected_chatgpt = nested_names - {CHATGPT_ROUTER_NAME}
    chatgpt_names = _load_capability_map(
        root,
        chatgpt_leaf,
        CHATGPT_ROUTER_NAME,
        valid_name,
        report,
    )
    if (
        CHATGPT_ROUTER_NAME not in nested_names
        or set(general_names) != expected_general
        or chatgpt_names is None
        or set(chatgpt_names) != expected_chatgpt
        or set(general_names).intersection(expected_chatgpt)
    ):
        report(
            "APG038",
            _relative(chatgpt_leaf / CAPABILITY_MAP_PATH, root),
            "router-map-contract",
            "general and ChatGPT router maps are incomplete, cyclic, or cross-domain",
            "restore disjoint general-subrouter and ChatGPT-leaf ownership",
        )
