from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import pytest

from agent_phase.bundle import publish_bundle

_SRC_DIR = str(Path(__file__).resolve().parents[3] / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from agentic_praxis_grimoire.home import (
    LAYOUT_VERSION,
    home_layout_paths,
    inspect_home,
    resolve_home_with_provenance,
)
from agentic_praxis_grimoire.paths import PathContractError
from agentic_praxis_grimoire import cli


def test_resolve_home_precedence(tmp_path: Path) -> None:
    cli_h = tmp_path / "cli_home"
    env_h = tmp_path / "env_home"
    def_h = tmp_path / "user"

    # Tier 1: CLI
    path, source = resolve_home_with_provenance(
        cli_home=cli_h,
        environment={"APGR_HOME": str(env_h)},
        home=def_h,
    )
    assert path == cli_h
    assert source == "cli"

    # Tier 2: Environment
    path, source = resolve_home_with_provenance(
        cli_home=None,
        environment={"APGR_HOME": str(env_h)},
        home=def_h,
    )
    assert path == env_h
    assert source == "environment"

    # Tier 3: Default
    path, source = resolve_home_with_provenance(
        cli_home=None,
        environment={},
        home=def_h,
    )
    assert path == def_h / ".apgr"
    assert source == "default"


def test_resolve_home_rejects_relative_path() -> None:
    with pytest.raises(PathContractError, match="must be an absolute path"):
        resolve_home_with_provenance(cli_home="relative/path")

    with pytest.raises(PathContractError, match="must be an absolute path"):
        resolve_home_with_provenance(environment={"APGR_HOME": "relative/path"})


def test_resolve_home_no_jaca_home_coupling(tmp_path: Path) -> None:
    jaca_dir = tmp_path / "jaca"
    def_h = tmp_path / "user"
    path, source = resolve_home_with_provenance(
        cli_home=None,
        environment={"JACA_HOME": str(jaca_dir)},
        home=def_h,
    )
    assert path == def_h / ".apgr"
    assert source == "default"
    assert path != jaca_dir
    assert not path.is_relative_to(jaca_dir)


def test_home_layout_paths_structure(tmp_path: Path) -> None:
    home_dir = tmp_path / "my_home"
    outbox = tmp_path / "my_outbox"
    paths = home_layout_paths(home_dir, outbox_root=outbox)

    assert paths["home"] == home_dir
    assert paths["config"] == home_dir / "config.toml"
    assert paths["dispatcher"] == home_dir / "dispatcher"
    assert paths["claude_settings"] == home_dir / "claude" / "settings.json"
    assert paths["database"] == home_dir / "state" / "dispatcher.sqlite3"
    assert paths["state"] == home_dir / "state"
    assert paths["state_runs"] == home_dir / "state" / "runs"
    assert paths["generations"] == home_dir / "generations"
    assert paths["scratch"] == home_dir / "scratch"
    assert paths["skills"] == home_dir / "skills"
    assert paths["outbox_root"] == outbox

    # State and outbox roots are strictly decoupled
    assert not paths["database"].is_relative_to(outbox)
    assert not paths["state_runs"].is_relative_to(outbox)


def test_inspect_home_nonexistent_clean(tmp_path: Path) -> None:
    nonexistent = tmp_path / "nonexistent_home"
    report = inspect_home(cli_home=nonexistent)

    assert report["layout_version"] == LAYOUT_VERSION
    assert report["precedence_source"] == "cli"
    assert report["effective_home"] == str(nonexistent)
    assert any("does not exist" in d for d in report["diagnostics"])
    # Absolutely zero side effects: nonexistent directory was not created
    assert not nonexistent.exists()


def test_inspect_home_dispatcher_partial_bundle(tmp_path: Path) -> None:
    home_dir = tmp_path / "op_home"
    home_dir.mkdir()
    disp = home_dir / "dispatcher"
    disp.mkdir()
    (disp / "routes.toml").write_text("generation = 1\n")
    (disp / "endpoints.toml").write_text("generation = 1\n")
    # missing capabilities.toml and policy.toml

    report = inspect_home(cli_home=home_dir)
    assert any("partial operator dispatcher roster" in d for d in report["diagnostics"])


def test_inspect_home_dispatcher_generation_mismatch(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    home_dir = tmp_path / "op_home"
    home_dir.mkdir()
    disp = home_dir / "dispatcher"
    source = tmp_path / "source"
    shutil.copytree(repo_root / "common/dispatcher", source)

    publish_bundle(source, disp, expected_generation=9)

    policy_file = disp / "policy.toml"
    policy_file.write_text(
        re.sub(r"generation = \d+", "generation = 6", policy_file.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    manifest_path = disp / "bundle.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest_data.get("files") or manifest_data.get("members")
    files["policy.toml"]["sha256"] = hashlib.sha256(policy_file.read_bytes()).hexdigest()
    files["policy.toml"]["bytes"] = policy_file.stat().st_size
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    report = inspect_home(cli_home=home_dir)
    assert any("operator dispatcher roster generation mismatch" in d for d in report["diagnostics"])


def test_cli_home_show_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    home_dir = tmp_path / "test_cli_home"
    home_dir.mkdir()

    exit_code = cli.main(["--apgr-home", str(home_dir), "home", "show", "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["layout_version"] == LAYOUT_VERSION
    assert data["precedence_source"] == "cli"
    assert data["effective_home"] == str(home_dir)
    assert "database" in data["paths"]


def test_cli_home_show_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home_dir = tmp_path / "test_cli_home"
    home_dir.mkdir()

    exit_code = cli.main(["--apgr-home", str(home_dir), "home", "show"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert f"layout_version: {LAYOUT_VERSION}" in captured.out
    assert "precedence_source: cli" in captured.out
    assert f"effective_home: {home_dir}" in captured.out


def test_cli_home_show_relative_fails(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["--apgr-home", "relative/path", "home", "show", "--json"])
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "must be an absolute path" in captured.err


def test_go_python_home_show_parity(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import subprocess
    home_dir = tmp_path / "parity_home"
    home_dir.mkdir()

    # Python CLI owns full configuration resolution (scope: resolved_config)
    exit_code = cli.main(["--apgr-home", str(home_dir), "home", "show", "--json"])
    assert exit_code == 0
    py_raw = capsys.readouterr().out
    py_out = json.loads(py_raw)
    assert py_out["scope"] == "resolved_config"

    repo_root = Path(__file__).resolve().parents[3]

    # Standalone Go CLI is scoped to paths_only
    proc = subprocess.run(
        ["go", "run", "./cmd/apgr", "--apgr-home", str(home_dir), "home", "show", "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    go_standalone = json.loads(proc.stdout)
    assert go_standalone["layout_version"] == LAYOUT_VERSION
    assert go_standalone["scope"] == "paths_only"
    assert go_standalone["precedence_source"] == "cli"
    assert go_standalone["effective_home"] == str(home_dir)
    assert any("paths_only scope" in d for d in go_standalone["diagnostics"])

    # Pure Go consumes and renders the canonical Python-produced resolved_config view
    py_json_path = tmp_path / "py_view.json"
    py_json_path.write_text(py_raw)

    proc_consumed = subprocess.run(
        ["go", "run", "./cmd/apgr", "home", "show", "--from-json", str(py_json_path), "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    go_consumed = json.loads(proc_consumed.stdout)
    assert go_consumed == py_out


def test_inspect_home_with_review_mutation_config(tmp_path: Path) -> None:
    home_dir = tmp_path / "configured_home"
    home_dir.mkdir()
    cfg = home_dir / "config.toml"
    cfg.write_text("""
outbox_root = "/tmp/outbox"

[dispatcher.routing]
execution_mode = "conserve_claude"

[dispatcher.review_mutation]
worktree = "warn"
index = "block"
head = "block"
""")
    report = inspect_home(cli_home=home_dir)
    assert report["layout_version"] == LAYOUT_VERSION
    assert report["scope"] == "resolved_config"
    assert report["paths"]["outbox_root"] == "/tmp/outbox"
    # Verify no diagnostic complaining about unsupported key review_mutation
    assert not any("review_mutation" in d for d in report["diagnostics"])
    assert not any("config file error" in d for d in report["diagnostics"])


def test_inspect_home_flags_symlinked_roster_file_and_invalid_policy(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    home_dir = tmp_path / "op_home"
    home_dir.mkdir()
    disp = home_dir / "dispatcher"
    source = tmp_path / "source"
    shutil.copytree(repo_root / "common/dispatcher", source)

    publish_bundle(source, disp, expected_generation=9)

    # Symlinked roster file
    real_file = tmp_path / "real_routes.toml"
    routes_file = disp / "routes.toml"
    real_file.write_text(routes_file.read_text(encoding="utf-8"), encoding="utf-8")
    routes_file.unlink()
    routes_file.symlink_to(real_file)

    report = inspect_home(cli_home=home_dir)
    assert any("must be a regular non-symlink file" in d for d in report["diagnostics"])

    # Fix symlink, check invalid policy axis detection
    routes_file.unlink()
    routes_file.write_text(real_file.read_text(encoding="utf-8"), encoding="utf-8")
    policy_file = disp / "policy.toml"
    policy_file.write_text(
        re.sub(r'worktree = "[^"]+"', 'worktree = "invalid_axis"', policy_file.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    manifest_path = disp / "bundle.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    files = manifest_data.get("files") or manifest_data.get("members")
    files["policy.toml"]["sha256"] = hashlib.sha256(policy_file.read_bytes()).hexdigest()
    files["policy.toml"]["bytes"] = policy_file.stat().st_size
    manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

    report2 = inspect_home(cli_home=home_dir)
    assert any("unsupported worktree in [review_mutation]" in d for d in report2["diagnostics"])


def test_go_python_home_show_parity_configured(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import subprocess
    repo_root = Path(__file__).resolve().parents[3]
    home_dir = tmp_path / "full_configured_home"
    home_dir.mkdir()

    # config.toml with review_mutation
    (home_dir / "config.toml").write_text("""
outbox_root = "/tmp/outbox_configured"

[dispatcher.routing]
execution_mode = "normal"

[dispatcher.review_mutation]
worktree = "allow"
index = "block"
head = "block"
""")

    # Populated operator dispatcher bundle with generation 42
    disp = home_dir / "dispatcher"
    disp.mkdir()
    gen = 42
    for name in ("routes.toml", "endpoints.toml", "capabilities.toml", "policy.toml"):
        src = repo_root / "common" / "dispatcher" / name
        content = src.read_text(encoding="utf-8")
        import re
        content = re.sub(r"generation = \d+", f"generation = {gen}", content)
        (disp / name).write_text(content, encoding="utf-8")

    # Python CLI emits resolved_config view
    exit_code = cli.main(["--apgr-home", str(home_dir), "home", "show", "--json"])
    assert exit_code == 0
    py_raw = capsys.readouterr().out
    py_out = json.loads(py_raw)
    assert py_out["scope"] == "resolved_config"
    assert py_out["paths"]["outbox_root"] == "/tmp/outbox_configured"

    # Go --from-json parses and renders identical view
    py_json_path = tmp_path / "py_view_configured.json"
    py_json_path.write_text(py_raw)

    proc_consumed = subprocess.run(
        ["go", "run", "./cmd/apgr", "home", "show", "--from-json", str(py_json_path), "--json"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    go_consumed = json.loads(proc_consumed.stdout)
    assert go_consumed == py_out
