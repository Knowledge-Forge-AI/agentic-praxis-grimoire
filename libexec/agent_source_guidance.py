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
import shlex
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
            print("apgr: skill deny settings unreadable; source skill unavailable",
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
        print("apgr: skill disable settings unreadable; source skill unavailable",
              file=sys.stderr)
        return None


class SourceGuidance(tuple):
    """Result of source_guidance preserving tuple[str, list[str]] compatibility."""
    prompt: str
    permissions: list[str]
    source_digest: str
    rendered_digest: str

    def __new__(
        cls,
        prompt: str,
        permissions: list[str],
        *,
        source_digest: str = "",
        rendered_digest: str = "",
        instruction_components: list[dict] | None = None,
        static_prompt: str | None = None,
    ) -> SourceGuidance:
        inst = super().__new__(cls, (prompt, permissions))
        inst.prompt = prompt
        inst.permissions = permissions
        inst.source_digest = source_digest
        inst.rendered_digest = rendered_digest
        inst.instruction_components = instruction_components or []
        # With a projection: the prompt the unchanged static path would have
        # produced from the same reads. A counterfactual, never transmitted.
        inst.static_prompt = prompt if static_prompt is None else static_prompt
        return inst


def render_rtk_slice(provider: str, mode: str, executable: str | None = None) -> str:
    """Render conditional RTK instruction slice for provider and effective mode.

    Modes:
    - 'off': Empty string (no RTK optimization slice).
    - 'instructions': Conditional guidance naming the configured executable.
    - 'hook': Ordinary command syntax, no double-prefix, advisory nature.
    """
    if mode == "off" or not mode:
        return ""

    if mode == "hook":
        return (
            "## RTK shell-output efficiency\n\n"
            "A matching RTK PreToolUse hook is registered and targeted for this session. Use ordinary\n"
            "command syntax without manual RTK prefixing. Output compaction is advisory and may be applied\n"
            "transparently if the hook runs for an eligible command. Raw, uncompressed commands\n"
            "must always be used for Git commit hashes, tree identities, candidate\n"
            "verification, machine JSON reports, manifests, and test receipts. If a command\n"
            "fails after execution, do not blindly re-run it raw."
        )

    if mode == "instructions":
        if not executable:
            return ""
        quoted = shlex.quote(str(executable))
        if provider == "antigravity":
            return (
                "## RTK shell-output efficiency\n\n"
                f"For supported shell and development commands, prefer the RTK-proxied form so\n"
                f"output is compacted before it reaches model context. Typical examples include\n"
                f"`{quoted} git status`, `{quoted} git diff`, `{quoted} git log`, `{quoted} pytest`, `{quoted} cargo test`,\n"
                f"`{quoted} cargo build`, `{quoted} npm test`, `{quoted} npm run build`, `{quoted} cat <file>`,\n"
                f"`{quoted} rg <pattern>`, and `{quoted} ls <path>`.\n\n"
                f"Task-authorized RTK meta commands may be run directly: `{quoted} gain`, `{quoted} gain --history`, and\n"
                f"`{quoted} discover`. When genuinely raw, unfiltered output is required, use\n"
                f"`{quoted} proxy <cmd>`. If RTK does not support a command or changes semantics the\n"
                f"task requires, run the raw command instead of forcing RTK.\n\n"
                f"This is prompt-based efficiency guidance, not a transparent Antigravity shell\n"
                f"hook and not a security boundary. A repository-local\n"
                f"`.agents/rules/antigravity-rtk-rules.md` may reinforce it, but agent-central\n"
                f"does not require or install that project-local file.\n\n"
                f"This integration imposes no additional sandbox restriction. Follow the task's\n"
                f"actual authority and stop boundaries.\n"
                f"Raw, uncompressed commands must always be used for Git commit hashes, tree identities,\n"
                f"candidate verification, machine JSON reports, manifests, and test receipts. If an RTK-wrapped\n"
                f"command fails after the underlying command may have executed, do not blindly re-run it raw;\n"
                f"preserve the observed result and underlying effects."
            )
        else:
            return (
                "## RTK shell-output efficiency\n\n"
                f"For supported shell and development commands, prefer running through `{quoted}` so\n"
                f"output is compacted before it reaches model context. Follow `$rtk-command-proxy`.\n"
                f"Do not prefix every shell command; use `{quoted}` for eligible human-facing reads and summaries.\n"
                f"Raw, uncompressed commands must always be used for Git commit hashes, tree identities,\n"
                f"candidate verification, machine JSON reports, manifests, and test receipts. If an RTK-wrapped\n"
                f"command fails after the underlying command may have executed, do not blindly re-run it raw;\n"
                f"preserve the observed result and underlying effects."
            )

    return ""


def _extract_rtk_mode_and_executable(
    rtk: Any,
    provider: str,
    executable: str | None = None,
    provider_mode: str | None = None,
) -> tuple[str, str | None]:
    if provider_mode is not None:
        if provider_mode == "instructions" and not executable:
            return "off", None
        return provider_mode, executable
    if rtk is None:
        return "off", None
    eff_exec = executable
    effective_mode = "off"
    if hasattr(rtk, "providers") and isinstance(rtk.providers, dict):
        pdata = rtk.providers.get(provider, {})
        if isinstance(pdata, dict):
            effective_mode = pdata.get("effective_mode", "off")
        elif isinstance(pdata, str):
            effective_mode = pdata
        eff_exec = (
            eff_exec
            or getattr(rtk, "configured_executable", None)
            or getattr(rtk, "resolved_executable", None)
        )
    elif isinstance(rtk, dict):
        if "providers" in rtk and isinstance(rtk["providers"], dict):
            pdata = rtk["providers"].get(provider, {})
            if isinstance(pdata, dict):
                effective_mode = pdata.get("effective_mode", "off")
            elif isinstance(pdata, str):
                effective_mode = pdata
        eff_exec = (
            eff_exec
            or rtk.get("configured_executable")
            or rtk.get("executable")
        )

    if effective_mode == "instructions" and not eff_exec:
        return "off", None

    return effective_mode, eff_exec


def codex_guidance_overrides(
    root: Path,
    *,
    workers: bool,
    rtk: Any = None,
    executable: str | None = None,
    provider_mode: str | None = None,
    instruction_records: list[dict] | None = None,
) -> list[str]:
    """Add standing source text and retain explicit per-skill disables."""
    disables = codex_skill_disables()
    disabled = disables is None or any("agent-worker" in Path(item["path"]).parts for item in disables)
    guidance = source_guidance(
        root / "codex",
        [],
        workers=workers and not disabled,
        instruction_file="AGENTS.md",
        rtk=rtk,
        provider="codex",
        executable=executable,
        provider_mode=provider_mode,
    )
    if instruction_records is not None:
        instruction_records.extend(guidance.instruction_components)
    result = []
    if disables:
        entries = ["{path=" + json.dumps(item["path"]) + ",enabled=false}"
                   for item in disables]
        result.append("skills.config=[" + ",".join(entries) + "]")
    if guidance[0]:
        result.append("developer_instructions=" + json.dumps(guidance[0]))
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
    root: Path,
    arguments: Sequence[str],
    *,
    workers: bool,
    instruction_file: str = "CLAUDE.md",
    rtk: Any = None,
    provider: str | None = None,
    executable: str | None = None,
    provider_mode: str | None = None,
    projection: dict | None = None,
) -> SourceGuidance:
    """Return additive text and exact Read permissions; never write runtime state.

    ``projection`` (Claude only) is a wrapper-validated stage projection whose
    body replaces the standing-instruction body; nothing else changes.
    """
    options = list(arguments)
    if "--" in options:
        options = options[:options.index("--")]
    if instruction_file == "CLAUDE.md" and (
        "--safe-mode" in options or os.environ.get("CLAUDE_CODE_SAFE_MODE") == "1"
    ):
        return SourceGuidance("", [], source_digest="", rendered_digest="")
    parts: list[str] = []
    permissions: list[str] = []

    eff_provider = provider
    if eff_provider is None:
        if instruction_file == "CLAUDE.md":
            eff_provider = "claude"
        elif instruction_file == "AGENTS.md":
            eff_provider = "codex"
        elif instruction_file == "GEMINI.md":
            eff_provider = "antigravity"
        else:
            eff_provider = "unknown"

    source_digest = ""
    rendered_digest = ""
    instruction_components = []
    static_part = None
    try:
        path = root / instruction_file
        # A projection carries the source bytes it was validated against; do
        # not re-read them, so the header and counterfactual match that check.
        source_body = (projection["source_text"] if projection is not None
                       else path.read_bytes().decode("utf-8"))
        source_digest = hashlib.sha256(source_body.encode("utf-8")).hexdigest()

        mode, eff_executable = _extract_rtk_mode_and_executable(
            rtk, eff_provider, executable=executable, provider_mode=provider_mode,
        )
        slice_text = render_rtk_slice(eff_provider, mode, eff_executable) if mode != "off" else ""

        def render(body: str) -> str:
            return body.rstrip() + "\n\n" + slice_text.strip() + "\n" if slice_text else body
        if projection is not None:
            static_rendered = render(source_body)
            static_part = (f"Source standing instructions ({path}; "
                           f"sha256={hashlib.sha256(static_rendered.encode('utf-8')).hexdigest()}):\n{static_rendered}")
        rendered_body = render(projection["body"] if projection is not None else source_body)
        rendered_digest = hashlib.sha256(rendered_body.encode("utf-8")).hexdigest()
        instruction_components.append({
            "kind": "standing-and-rtk", "source_path": str(path),
            "source_sha256": source_digest, "rendered_sha256": rendered_digest,
            "source_bytes": len(source_body.encode("utf-8")),
            "source_characters": len(source_body),
            "rendered_bytes": len(rendered_body.encode("utf-8")),
            "rendered_characters": len(rendered_body),
            "rtk_slice_sha256": hashlib.sha256(slice_text.encode("utf-8")).hexdigest(),
            "rtk_slice_bytes": len(slice_text.encode("utf-8")),
            "boundary": "component view, overlaps transport; do not add twice",
        })
        if projection is not None:
            instruction_components[-1]["projection"] = {
                "projection_id": projection["projection"]["projection_id"],
                "bytes": projection["projection"]["bytes"], "sha256": projection["projection"]["sha256"],
                "classes": list(projection["classes"]), "omitted": list(projection["omitted"])}
            label = (f"APGR stage projection for {'+'.join(projection['classes'])}; sha256={rendered_digest}; "
                     f"omitted as not applicable: {', '.join(projection['omitted']) or 'none'}")
        else:
            label = f"sha256={rendered_digest}"
        parts.append(f"Source standing instructions ({path}; {label}):\n{rendered_body}")
    except (OSError, UnicodeError):
        print("apgr: source standing instructions unavailable", file=sys.stderr)
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
            print("apgr: source worker guidance unavailable; direct work remains available",
                  file=sys.stderr)
    static_prompt = None
    if static_part is not None:
        static_prompt = "\n\n".join([static_part, *parts[1:]])
    return SourceGuidance(
        "\n\n".join(parts),
        permissions,
        source_digest=source_digest,
        rendered_digest=rendered_digest,
        instruction_components=instruction_components,
        static_prompt=static_prompt,
    )
