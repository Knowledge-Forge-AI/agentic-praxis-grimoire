"""Check definitions and execution attestation for APGR pre-review suite."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ci.pre_review_records import ROOT, Check


def checks(scratch_dir: Path, tool_root: Path | None = None) -> tuple[Check, ...]:
    """Assemble the configured inventory of pre-review checks adapted for APGR."""
    python = sys.executable
    native = tool_root / "bin" if tool_root is not None else None
    python_tools = tool_root / "python" / "bin" if tool_root is not None else None
    node = (
        tool_root / "node" / "node_modules" / ".bin"
        if tool_root is not None else None
    )

    def executable(name: str, owner: Path | None = native) -> str:
        if owner is not None:
            return str(owner / name)
        which_path = shutil.which(name)
        if which_path is not None:
            return which_path
        return str(owner / name) if owner is not None else name

    workflows_dir = ROOT / ".github/workflows"
    workflows = tuple(str(path) for path in sorted(workflows_dir.iterdir())
                      if path.is_file() and path.suffix in {".yml", ".yaml"}) \
        if workflows_dir.is_dir() else ()

    def missing_targets(name: str, target: str) -> tuple[str, ...]:
        # Execute a failing lane so independent checks still reach aggregation.
        return (python, "-c", "import sys; sys.stderr.write("
                + repr(f"{name}: required {target} targets absent\n") + "); sys.exit(2)")

    try:
        dockerfiles = tuple(
            path
            for path in subprocess.run(
                ["git", "ls-files", "*Dockerfile", "Dockerfile*"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            if path
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        dockerfiles = tuple(
            p.relative_to(ROOT).as_posix()
            for p in ROOT.rglob("*Dockerfile*")
            if p.is_file()
        )

    ruff_roots = (
        "src/agentic_praxis_grimoire",
        "libexec",
        "tools",
        "bin",
        "release/ci",
        "src/test",
    )

    return (
        Check("ruff", (python, "-m", "ruff", "check", "--output-format=json", *ruff_roots), policy="ruff", python_owned=True),
        Check(
            "pyflakes",
            (
                python,
                "-m",
                "ruff",
                "check",
                "--select",
                "F",
                "src/agentic_praxis_grimoire",
                "libexec",
            ),
            python_owned=True,
        ),
        Check(
            "mypy",
            (
                python,
                "tools/ci/python_type_check.py",
                "--manifest",
                "tools/ci/python_type_ownership.json",
            ),
            python_owned=True,
        ),
        Check(
            "retained-python-ratchets",
            (
                python,
                "tools/ci/retained_python_ratchets.py",
                "--baseline",
                "tools/ci/retained_python_ratchets.json",
            ),
            policy="retained-python-ratchets",
            python_owned=True,
        ),
        Check(
            "python-retention-inventory",
            (python, "tools/ci/python_retention_inventory.py", "--check", "--json"),
            python_owned=True,
        ),
        Check("ci-topology", (python, "tools/ci/ci_topology.py"), python_owned=True),
        Check(
            "file-length",
            (python, "tools/ci/file_length_policy.py", "--format", "json"),
            policy="file-length",
            python_owned=True,
        ),
        Check(
            "python-compile",
            (
                python,
                "-m",
                "compileall",
                "-q",
                "src/agentic_praxis_grimoire",
                "libexec",
                "tools",
                "release/ci",
                "src/test",
            ),
            python_owned=True,
        ),
        Check("actionlint", (executable("actionlint"), "-format", "{{json .}}", *workflows)
              if workflows else missing_targets("actionlint", "workflow")),
        Check(
            "zizmor",
            (
                executable("zizmor"),
                "--offline",
                "--strict-collection",
                "--no-exit-codes",
                "--format",
                "json",
                ".github/workflows",
            ),
            policy="zizmor",
        ),
        Check(
            "pip-audit",
            (
                python,
                "tools/ci/dependency_inventory.py",
                "--auditor",
                executable("pip-audit", python_tools),
                "--scratch-dir",
                str(scratch_dir / "dependency-audit"),
            ),
            policy="pip-audit",
            python_owned=True,
        ),
        Check("govulncheck", (executable("govulncheck"), "-json", "./..."), cwd=ROOT),
        Check(
            "semgrep",
            (
                executable("semgrep", python_tools),
                "scan",
                "--config",
                "tools/ci/semgrep.yml",
                "--json",
                "--error",
                "--metrics",
                "off",
                "src/agentic_praxis_grimoire",
                "libexec",
                "tools",
            ),
            python_owned=False,
        ),
        Check(
            "betterleaks",
            (
                executable("betterleaks"),
                "dir",
                ".",
                "--no-banner",
                "--redact=100",
                "--report-format=json",
                "--report-path=-",
            ),
            policy="betterleaks",
        ),
        Check("malskanner", (executable("malskanner", node), ".", "--json"), policy="malskanner"),
        Check("prompt-defense-audit", (python, "tools/ci/prompt_defense_check.py"), python_owned=True),
        Check("scanner-suppressions", (python, "tools/ci/scanner_suppressions.py"), policy="suppressions", python_owned=True),
        Check("liquibase", (python, "tools/ci/liquibase_check.py"), python_owned=True),
        # The tracked Dockerfile is a maintained hotspot test fixture. Keep its
        # concrete path in the receipt and retain Hadolint's finding exit code;
        # the fixture is not an operational-image claim or a waived lane.
        Check(
            "hadolint",
            (executable("hadolint"), "--format", "json", *dockerfiles)
            if dockerfiles
            else missing_targets("hadolint", "Dockerfile"),
            policy="hadolint",
        ),
        Check(
            "generated-code-drift",
            (
                python,
                "tools/ci/check_generated_drift.py",
                "--evidence-dir",
                str(scratch_dir / "generated-code-drift"),
            ),
            python_owned=True,
        ),
        Check(
            "release-matrix",
            (python, "testing/release/check_release_matrix.py"),
            python_owned=True,
        ),
    )


def _interpreter(check: Check) -> str | None:
    return "<tool-python>" if check.python_owned else None


def _attest_check_owner(check: Check, tool_root: Path | None) -> None:
    if not check.python_owned:
        return
    actual = Path(check.command[0]).resolve()
    if check.python_entry == "interpreter" and actual != Path(sys.executable).resolve():
        raise RuntimeError(f"interpreter mismatch for {check.name}: {actual} != {sys.executable}")


def _attest_python_owner(tool_root: Path | None) -> None:
    interpreter = Path(sys.executable)
    if (
        not interpreter.is_absolute()
        or not interpreter.is_file()
        or not os.access(interpreter, os.X_OK)
    ):
        raise RuntimeError("pre-review Python interpreter is not an executable")
    try:
        resolved = interpreter.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise RuntimeError("pre-review Python interpreter cannot be resolved") from error
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise RuntimeError("pre-review Python interpreter target is not executable")
    repository = ROOT.resolve(strict=True)
    if resolved == repository or repository in resolved.parents:
        raise RuntimeError("pre-review Python interpreter is inside the repository")
    if tool_root is not None:
        if not tool_root.is_absolute() or tool_root.is_symlink() or not tool_root.is_dir():
            raise RuntimeError("pre-review tool root is not a direct external directory")
        tool_resolved = tool_root.resolve(strict=True)
        if tool_resolved == repository or repository in tool_resolved.parents:
            raise RuntimeError("pre-review tool root is inside the repository")


def _command_attestation(check: Check, tool_root: Path | None) -> str:
    values: list[str] = []
    interpreter = Path(sys.executable).resolve()
    repository = ROOT.resolve(strict=True)
    tool_resolved = tool_root.resolve(strict=True) if tool_root is not None else None
    for value in check.command:
        candidate = Path(value)
        if candidate.is_absolute():
            try:
                resolved = candidate.resolve(strict=False)
            except OSError:
                resolved = candidate
            if resolved == interpreter:
                values.append("<python>")
                continue
            if tool_resolved is not None and resolved == tool_resolved:
                values.append("<tool-root>")
                continue
            if tool_resolved is not None and tool_resolved in resolved.parents:
                values.append(f"<tool-root>/{resolved.relative_to(tool_resolved)}")
                continue
            if repository in resolved.parents:
                values.append(f"<repo>/{resolved.relative_to(repository)}")
                continue
            values.append(f"<external>/{candidate.name}")
            continue
        values.append(value)
    return " ".join(values)
