"""Leaf authority prompt and bounded workspace change observation."""
from pathlib import Path
import subprocess

def build_leaf_prompt(
    task: str,
    task_authority: str,
    mutation_scope: list[str] | None = None,
    acceptance_criteria: str | None = None,
    worker_kind: str = "gemini",
) -> str:
    if worker_kind == "luna":
        worker_label = "Codex Luna"
    elif worker_kind == "sonnet":
        worker_label = "Claude Sonnet"
    else:
        worker_label = "Gemini"
    lines = [
        f"# {worker_label} Worker Leaf Job",
        "",
        f"You are an isolated {worker_label} leaf worker executing a delegated task for a parent agent.",
        "You must NOT attempt to register as a root agent or recursively invoke agent phases.",
        "Do not create further workers, spawn subagents, or stage, commit, or push Git changes.",
        f"Task Authority: {task_authority.upper()}",
    ]
    if task_authority == "read_only":
        lines.append(
            "READ-ONLY RESTRICTION: You may inspect files and reason, but you must NOT create or edit files, "
            "run any tests, builds, installers, formatters, or Git mutation commands."
        )
    elif mutation_scope:
        lines.append(
            f"MUTATION SCOPE: You are permitted to modify only these paths: {', '.join(mutation_scope)}. "
            "Do not modify files outside this designated scope."
        )

    if acceptance_criteria:
        lines.extend(["", "## Acceptance Criteria", acceptance_criteria])

    lines.extend(["", "## Task Instructions", task])
    return "\n".join(lines)


def get_changed_paths(workspace: Path) -> list[str] | None:
    """Inspect workspace for uncommitted git changes."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if res.returncode == 0:
            paths = []
            entries = iter(res.stdout.split("\0"))
            for entry in entries:
                if len(entry) < 4:
                    continue
                paths.append(entry[3:])
                if "R" in entry[:2] or "C" in entry[:2]:
                    next(entries, None)  # The source path follows a rename/copy.
            return sorted(set(paths))
    except Exception:
        pass
    return None
