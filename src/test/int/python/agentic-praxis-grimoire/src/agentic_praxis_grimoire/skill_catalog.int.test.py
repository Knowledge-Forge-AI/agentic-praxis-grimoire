"""Installed-wheel catalog entrypoints, isolated from the development import tree."""
from __future__ import annotations

import json
import base64
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
from src.test.apg_test_support import repository_root

ROOT = repository_root(__file__)


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    root = tmp_path_factory.mktemp("catalog-wheel")
    build = subprocess.run(
        [sys.executable, "-c", "import apg_python_build_backend as b; print(b.build_wheel(__import__('sys').argv[1]))", str(root)],
        cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "libexec")},
        capture_output=True, text=True, timeout=120,
    )
    assert build.returncode == 0, build.stderr
    wheel = root / build.stdout.strip().splitlines()[-1]
    package = root / "installed"
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(package)
    binary = package / "agentic_praxis_grimoire/bin/apgr"
    binary.chmod(0o755)
    return package


def invoke(installed, cwd, *args, home=None):
    env = dict(os.environ, PYTHONPATH=str(installed), APGR_HOME=str(home or cwd / "missing-home"))
    env.pop("APGR_GO_BINARY", None)
    result = subprocess.run([sys.executable, "-m", "agentic_praxis_grimoire", *args],
                            cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
    return result


def leaf(root, source="project", name="go-language-profile", body="local"):
    directory = root / (".apgr/skills" if source == "project" else "skills") / name
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text(f"---\nname: {name}\ndescription: café\n---\n{body}\n")


def test_installed_embedded_and_no_write(installed, tmp_path):
    before = list(tmp_path.iterdir())
    result = invoke(installed, tmp_path, "skills", "list", "--all-sources", "--json")
    assert result.returncode == 0, result.stderr
    catalog = json.loads(result.stdout)
    assert all(row["qualified_id"].startswith("apgr:") for row in catalog["skills"])
    assert list(tmp_path.iterdir()) == before
    legacy = invoke(installed, tmp_path, "skills", "list", "--json")
    assert legacy.returncode == 0, legacy.stderr
    assert {row["name"] for row in json.loads(legacy.stdout)} == {row["id"] for row in catalog["skills"]}
    context = invoke(installed, tmp_path, "skills", "context-report")
    assert context.returncode == 0, context.stderr
    assert json.loads(context.stdout)["skill_count"] == len(catalog["skills"])


def test_installed_acquisition_selected_source_and_mcp(installed, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    run = tmp_path / "run"; run.mkdir()
    leaf(project, body="selected exact body")
    leaf(home, "user", body="unselected body")
    (project / ".apgr/config.toml").write_text('[skills.overrides]\n"apgr:go-language-profile" = "project:go-language-profile"\n')
    args = ("--project-root", str(project), "--apgr-home", str(home), "skills", "acquire", "apgr:go-language-profile",
            "--run-dir", str(run), "--run-id", "run", "--binding-id", "review", "--attempt-id", "attempt", "--consumer", "claude")
    result = invoke(installed, tmp_path, *args)
    assert result.returncode == 0, result.stderr
    acquired = json.loads(result.stdout)
    source = project / ".apgr/skills/go-language-profile/SKILL.md"
    assert acquired["selection"]["selected_identity"] == "project:go-language-profile"
    assert base64.b64decode(acquired["selection"]["snapshot"]["body"]) == source.read_bytes()
    assert (run / acquired["materialized_path"] / "SKILL.md").read_bytes() == source.read_bytes()
    config = next(run.glob("acquisition-authority-*.json"))
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "installed-fixture", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "skill_acquire", "arguments": {"id": "apgr:go-language-profile"}}},
    ]
    env = dict(os.environ, PYTHONPATH=str(installed)); env.pop("APGR_GO_BINARY", None)
    mcp = subprocess.run([sys.executable, "-m", "agentic_praxis_grimoire", "mcp", "serve", "--config", str(config)],
                         cwd=tmp_path, env=env, input="".join(json.dumps(m) + "\n" for m in messages), capture_output=True, text=True, timeout=30)
    assert mcp.returncode == 0, mcp.stderr
    assert json.loads(mcp.stdout.splitlines()[1])["result"]["content"][0]["text"] == source.read_text()


def test_installed_sources_overrides_and_invalid_target(installed, tmp_path):
    project = tmp_path / "project"
    home = tmp_path / "home"
    leaf(project)
    leaf(home, "user")
    config = project / ".apgr/config.toml"
    config.write_text('[skills.overrides]\n"apgr:go-language-profile" = "project:go-language-profile"\n')
    args = ("--project-root", str(project), "--apgr-home", str(home), "skills", "list", "--all-sources", "--json")
    result = invoke(installed, tmp_path, *args)
    assert result.returncode == 0, result.stderr
    catalog = json.loads(result.stdout)
    assert len([row for row in catalog["skills"] if row["id"] == "go-language-profile"]) == 3
    assert catalog["overrides"][0]["selected"] == "project:go-language-profile"
    assert catalog["overrides"][0]["config_sha256"]
    (project / ".apgr/skills/go-language-profile/SKILL.md").write_bytes(b"\xff")
    result = invoke(installed, tmp_path, *args)
    assert result.returncode == 0, result.stderr
    assert any("override replacement unavailable" in row["message"] for row in json.loads(result.stdout)["diagnostics"])
    config.write_text('[skills.overrides]\n"apgr:go-language-profile" = "apgr:go-language-profile"\n')
    assert invoke(installed, tmp_path, *args).returncode != 0
    # Canonical-only remains usable despite local configuration/source defects.
    assert invoke(installed, tmp_path, "--project-root", str(project), "skills", "list").returncode == 0


def test_installed_project_isolation_and_home_precedence(installed, tmp_path):
    outer = tmp_path / "outer"
    leaf(outer, name="outer")
    (outer / ".git").mkdir()
    inner = outer / "inner"
    inner.mkdir()
    (inner / ".git").write_text("gitdir: fixture\n")
    nested = inner / "nested"
    nested.mkdir()
    explicit = tmp_path / "config-free"
    explicit.mkdir()
    home = tmp_path / "selected-home"
    leaf(home, "user", "user-rule")
    hidden = tmp_path / "environment-home"
    leaf(hidden, "user", "hidden")
    result = invoke(installed, nested, "skills", "list", "--all-sources", "--apgr-home", str(home), "--json", home=hidden)
    assert result.returncode == 0, result.stderr
    ids = {r["qualified_id"] for r in json.loads(result.stdout)["skills"]}
    assert "project:outer" not in ids and "user:hidden" not in ids and "user:user-rule" in ids
    result = invoke(installed, outer, "skills", "list", "--all-sources", "--project-root", str(explicit), "--json")
    assert result.returncode == 0, result.stderr
    assert "project:outer" not in {r["qualified_id"] for r in json.loads(result.stdout)["skills"]}


def test_installed_text_provenance_relative_start_and_global_notice(installed, tmp_path):
    import hashlib
    project = tmp_path / "project"
    leaf(project)
    (project / ".git").mkdir()
    config = project / ".apgr/config.toml"
    config.write_text('[skills.overrides]\n"apgr:go-language-profile" = "project:go-language-profile"\n')
    home = tmp_path / "home"
    leaf(home, "user", "configuration")
    (home / "config.toml").write_text(config.read_text())
    args = ("skills", "list", "--all-sources", "--start", "project")
    result = invoke(installed, tmp_path, *args, home=home)
    assert result.returncode == 0, result.stderr
    assert "[available]" in result.stdout
    assert f"config={config}" in result.stdout
    assert f"sha256={hashlib.sha256(config.read_bytes()).hexdigest()}" in result.stdout
    assert "global configuration not consulted" in result.stdout
    (project / ".apgr/skills/go-language-profile/SKILL.md").write_bytes(b"\xff")
    result = invoke(installed, tmp_path, *args, home=home)
    assert result.returncode == 0, result.stderr
    assert "[unavailable]" in result.stdout
    # An invalid global configuration cannot gate listing or become authority.
    (home / "config.toml").write_bytes(b"\xff")
    result = invoke(installed, tmp_path, *args, "--json", home=home)
    assert result.returncode == 0, result.stderr
    catalog = json.loads(result.stdout)
    assert len(catalog["overrides"]) == 1
    assert all(d["identity"] != "user:configuration" for d in catalog["diagnostics"])


def test_installed_context_plan(installed, tmp_path):
    request = {"schema_version": "apg.context-plan/v1", "run_id": "installed", "binding_id": "work", "attempt_id": "1",
               "roles": ["producer"], "consumer": "go_library", "requested_mode": "adaptive",
               "catalog": {"schema_version": "apg.skill-catalog/v1"},
               "facts": [{"kind": "language", "value": "go"}, {"kind": "test_framework", "value": "go-native"}],
               "mandatory": [{"id": "task", "text": "doctrine é"}], "qualification": {}}
    env = dict(os.environ, PYTHONPATH=str(installed), APGR_HOME=str(tmp_path / "absent-home"))
    env.pop("APGR_GO_BINARY", None)
    result = subprocess.run([sys.executable, "-m", "agentic_praxis_grimoire", "skills", "plan", "--stdin"],
                            cwd=tmp_path, env=env, input=json.dumps(request), capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    plan = json.loads(result.stdout)
    assert plan["effective_mode"] == "static" and plan["required_satisfied"]
    assert len(plan["selected_snapshots"]) == 2
    assert plan["tokens"] is None and not (tmp_path / "absent-home").exists()
