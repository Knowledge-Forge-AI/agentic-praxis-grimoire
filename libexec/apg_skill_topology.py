"""Canonical topology and router-map validation for APG skills."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import json
from pathlib import Path
import re
import stat


CANONICAL_NAMESPACES = frozenset({"chatgpt"})
GENERAL_ROUTER_NAME = "agentic-praxis-grimoire-workflow"
CHATGPT_ROUTER_NAME = "chatgpt-manager-workflow"
CAPABILITY_MAP_PATH = Path("references/capability-map.json")

IssueReporter = Callable[[str, str, str, str, str], None]
NameValidator = Callable[[str], bool]


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
