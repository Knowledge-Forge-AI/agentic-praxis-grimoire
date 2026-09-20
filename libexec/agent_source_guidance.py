"""Optional source instructions, independent of vendor credential homes.

Advertise the one plain source skill through file reads instead of enabling
plugins or hooks. Claude uses its existing Read tool; Codex can read the file.
"""

from __future__ import annotations

import hashlib
from fnmatch import fnmatchcase
import json
import os
from pathlib import Path
import sys
from typing import Sequence


def worker_skill_disabled(root: Path, options: Sequence[str]) -> bool:
    """Honor targeted operator denies without restoring ambient settings grants."""
    home = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    from controller_generation import operator_root
    live_root = operator_root(root.parent) / root.name
    sources: list[Path | str] = [
        home / "settings.json", live_root / "settings.json",
        Path.cwd() / ".claude/settings.json", Path.cwd() / ".claude/settings.local.json",
    ]
    for index, option in enumerate(options):
        if option == "--settings" and index + 1 < len(options):
            sources.append(options[index + 1])
        elif option.startswith("--settings="):
            sources.append(option.split("=", 1)[1])
    for source in sources:
        try:
            raw = (source if isinstance(source, str) and source.lstrip().startswith("{")
                   else Path(source).expanduser().read_text(encoding="utf-8"))
            value = json.loads(raw)
            rules = value.get("permissions", {}).get("deny", [])
            if any(_denies_worker_skill(rule) for rule in rules):
                return True
        except FileNotFoundError:
            continue
        except (OSError, ValueError, AttributeError, TypeError):
            print("agent-central: skill deny settings unreadable; source skill unavailable",
                  file=sys.stderr)
            return True
    return False


def _denies_worker_skill(rule: str) -> bool:
    if rule == "Skill":
        return True
    if not isinstance(rule, str) or not rule.startswith("Skill(") or not rule.endswith(")"):
        return False
    pattern = rule[6:-1]
    return (fnmatchcase("agent-worker", pattern) or fnmatchcase("agent-worker ", pattern)
            or pattern.startswith("agent-worker:"))


def codex_skill_disables() -> list[dict[str, object]] | None:
    """Read only skill-disable policy from the existing non-secret config file."""
    import tomllib

    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    path = home / "config.toml"
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8"))
        return [{"path": item["path"], "enabled": False}
                for item in value.get("skills", {}).get("config", [])
                if item.get("enabled") is False and isinstance(item.get("path"), str)]
    except FileNotFoundError:
        return []
    except (OSError, ValueError, AttributeError, TypeError):
        print("agent-central: skill disable settings unreadable; source skill unavailable",
              file=sys.stderr)
        return None


def codex_guidance_overrides(root: Path, *, workers: bool) -> list[str]:
    """Add standing source text and retain explicit per-skill disables."""
    disables = codex_skill_disables()
    disabled = disables is None or any("agent-worker" in Path(item["path"]).parts for item in disables)
    guidance, _reads = source_guidance(
        root / "codex", [], workers=workers and not disabled,
        instruction_file="AGENTS.md",
    )
    result = []
    if disables:
        entries = ["{path=" + json.dumps(item["path"]) + ",enabled=false}"
                   for item in disables]
        result.append("skills.config=[" + ",".join(entries) + "]")
    if guidance:
        result.append("developer_instructions=" + json.dumps(guidance))
    return result


def _skill_description(body: str) -> str:
    """Read the source's plain scalar or indented description, not arbitrary YAML."""
    if not body.startswith("---\n") or "\n---" not in body:
        raise ValueError("skill frontmatter missing")
    lines = body.split("\n---", 1)[0].splitlines()[1:]
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        value = line.split(":", 1)[1].strip()
        if value in {">", ">-", "|", "|-"}:
            values = []
            for continuation in lines[index + 1:]:
                if continuation and not continuation[0].isspace():
                    break
                values.append(continuation.strip())
            value = " ".join(values).strip()
        if value:
            return value.strip("\"'")
    raise ValueError("skill description missing")


def source_guidance(
    root: Path, arguments: Sequence[str], *, workers: bool,
    instruction_file: str = "CLAUDE.md",
) -> tuple[str, list[str]]:
    """Return additive text and exact Read permissions; never write runtime state."""
    options = list(arguments)
    if "--" in options:
        options = options[:options.index("--")]
    if instruction_file == "CLAUDE.md" and (
        "--safe-mode" in options or os.environ.get("CLAUDE_CODE_SAFE_MODE") == "1"
    ):
        return "", []
    parts: list[str] = []
    permissions: list[str] = []
    try:
        path = root / instruction_file
        body = path.read_text(encoding="utf-8")
        parts.append(f"Source standing instructions ({path}; sha256="
                     f"{hashlib.sha256(body.encode()).hexdigest()}):\n{body}")
    except (OSError, UnicodeError):
        print("agent-central: source standing instructions unavailable", file=sys.stderr)
    disabled = instruction_file == "CLAUDE.md" and worker_skill_disabled(root, options)
    if workers and not disabled and "--disable-slash-commands" not in options:
        try:
            directory = root.parent / "common/skills/agent-worker"
            skill = directory / "SKILL.md"
            recovery = directory / "WORKER-RECOVERY.md"
            body = skill.read_text(encoding="utf-8")
            recovery.read_text(encoding="utf-8")
            description = _skill_description(body)
            if instruction_file == "CLAUDE.md" and any(
                char.isspace() or char in ",()[]*?" for char in str(directory)
            ):
                raise ValueError("source path cannot be represented as an exact Read rule")
            parts.append(
                "Launcher-advertised guidance (file read; not native Skill catalog "
                "registration). For agent-worker use this selected source reference "
                "instead of an ambient same-name skill.\n"
                f"Description: {description}\nSkill: {skill}\n"
                f"Recovery companion: {recovery}\n"
                f"Skill sha256: {hashlib.sha256(body.encode()).hexdigest()}\n"
                "Read the skill when useful; loading guidance does not start work."
            )
            permissions = [f"Read(/{path})" for path in (skill, recovery)]
        except (OSError, UnicodeError, ValueError):
            print("agent-central: source worker guidance unavailable; direct work remains available",
                  file=sys.stderr)
    return "\n\n".join(parts), permissions
