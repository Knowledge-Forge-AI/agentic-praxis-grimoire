"""Real CLI boundary tests for bin/apg-test."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile

import pytest

from src.test.apg_test_support import repository_root


REPOSITORY_ROOT = repository_root(__file__)
COMMAND = REPOSITORY_ROOT / "bin" / "apg-test"
sys.path.insert(0, str(REPOSITORY_ROOT / "libexec"))

import apg_test  # noqa: E402


def run_command(
    *arguments: str, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy() if environment is None else environment.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get(
        "PATH", ""
    )
    worker_root = Path(environment["TMPDIR"]).resolve(strict=True)
    with tempfile.TemporaryDirectory(
        prefix="apg-nested-pytest-", dir=worker_root.parent
    ) as pytest_root:
        environment["PYTEST_ADDOPTS"] = f"--basetemp={shlex.quote(pytest_root)}"
        return subprocess.run(
            [str(COMMAND), *arguments],
            cwd=REPOSITORY_ROOT,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )


@pytest.fixture
def repo_state_snapshot():
    """Verify repository source, ref, and index state remain strictly unchanged."""
    head_before = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    status_before = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    yield
    head_after = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    status_after = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    assert head_before == head_after, f"git HEAD drifted: {head_before} != {head_after}"
    assert status_before == status_after, f"git working tree/index changed:\n{status_after}"


def test_help_exposes_supported_suites_and_worker_override() -> None:
    result = run_command("--help")
    assert result.returncode == 0
    assert "{unit,integration,unit-integration,policy}" in result.stdout
    assert "--workers WORKERS" in result.stdout
    assert "--summary-file" in result.stdout


def test_invalid_worker_count_fails_before_test_execution() -> None:
    result = run_command("unit", "--workers", "0")
    assert result.returncode == 1
    assert "workers must be between 1 and 64" in result.stderr


def test_typescript_preflight_and_cli_reject_missing_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert apg_test.validate_typescript_compiler(REPOSITORY_ROOT) == "Version 7.0.2"
    monkeypatch.delenv("APG_TYPESCRIPT_TSC")
    with pytest.raises(apg_test.ToolError, match="test prerequisite is unavailable"):
        apg_test.validate_typescript_compiler(REPOSITORY_ROOT)
    environment = os.environ.copy()
    result = run_command("unit", environment=environment)
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == (
        "apg-test: TypeScript test prerequisite is unavailable: set "
        "APG_TYPESCRIPT_TSC to an absolute executable typescript@7.0.2 tsc "
        "installed outside the repository checkout\n"
    )


def test_typescript_preflight_rejects_unsafe_or_wrong_compiler_bindings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compiler = Path(os.environ["APG_TYPESCRIPT_TSC"])
    link = tmp_path / "tsc-link"
    link.symlink_to(compiler)
    monkeypatch.setenv("APG_TYPESCRIPT_TSC", str(link))
    with pytest.raises(apg_test.ToolError, match="absolute regular executable"):
        apg_test.validate_typescript_compiler(REPOSITORY_ROOT)

    monkeypatch.setenv("APG_TYPESCRIPT_TSC", str(COMMAND))
    with pytest.raises(apg_test.ToolError, match="outside the repository checkout"):
        apg_test.validate_typescript_compiler(REPOSITORY_ROOT)

    wrong = tmp_path / "wrong-tsc"
    wrong.write_text("#!/bin/sh\nprintf 'Version 7.0.1\\n'\n", encoding="utf-8")
    wrong.chmod(0o700)
    monkeypatch.setenv("APG_TYPESCRIPT_TSC", str(wrong))
    with pytest.raises(apg_test.ToolError, match="version mismatch"):
        apg_test.validate_typescript_compiler(REPOSITORY_ROOT)


def test_standalone_unit_runner_executes_real_pytest_xdist_and_coverage_boundary() -> None:
    result = run_command("unit", "--workers", "2")
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"
    assert "passed" in result.stdout
    assert "PASS unit: statements" in result.stdout
    assert "branches" in result.stdout


def test_missing_child_contribution_fixture_fails_the_real_runner() -> None:
    result = run_command(
        "unit",
        "--workers",
        "2",
        "--verify-failure-mode",
        "missing-child",
    )
    assert result.returncode == 1
    assert "required Python child has no observable coverage contribution" in result.stderr, (
        f"{result.stderr}\n{result.stdout}"
    )
    assert "injected-missing-child" in result.stderr


def test_real_worker_crash_fixture_fails_without_restart() -> None:
    result = run_command(
        "unit",
        "--workers",
        "2",
        "--verify-failure-mode",
        "worker-crash",
    )
    assert result.returncode == 1
    assert "worker" in result.stderr.lower()
    assert "worker-complete set is incomplete" in result.stderr


def test_policy_suite_executes_real_validation_and_writes_summary_file(
    tmp_path: Path,
) -> None:
    summary_file = tmp_path / "ci" / "policy-summary.json"
    result = run_command("policy", "--summary-file", str(summary_file))
    assert result.returncode == 0, f"{result.stderr}\n{result.stdout}"
    assert (
        "PASS policy: inventory, skill-library, and record-identity checks passed"
        in result.stdout
    )
    assert summary_file.is_file()
    assert oct(stat.S_IMODE(summary_file.stat().st_mode)) == "0o600"
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["subproject"] == "apg"
    assert payload["suite"] == "policy"
    assert payload["test_status"] == "pass"
    assert payload["gate_status"] == "pass"
    assert len(payload["source_commit"]) == 40
    assert all(c in "0123456789abcdef" for c in payload["source_commit"].lower())


def test_intentional_invocation_error_writes_error_summary_file(
    tmp_path: Path,
) -> None:
    summary_file = tmp_path / "ci" / "invocation-error-summary.json"
    result = run_command("unit", "--workers", "0", "--summary-file", str(summary_file))
    assert result.returncode == 1
    assert "workers must be between 1 and 64" in result.stderr
    assert summary_file.is_file()
    assert oct(stat.S_IMODE(summary_file.stat().st_mode)) == "0o600"
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["subproject"] == "apg"
    assert payload["suite"] == "unit"
    assert payload["test_status"] == "error"
    assert payload["gate_status"] == "error"
    assert len(payload["source_commit"]) == 40

    # Also verify unit-integration role with --summary-file=<path> syntax
    combined_summary = tmp_path / "ci" / "combined-invocation-error.json"
    res_comb = run_command(
        "unit-integration",
        "--workers",
        "0",
        f"--summary-file={combined_summary}",
    )
    assert res_comb.returncode == 1
    assert "workers must be between 1 and 64" in res_comb.stderr
    assert combined_summary.is_file()
    assert oct(stat.S_IMODE(combined_summary.stat().st_mode)) == "0o600"
    payload_comb = json.loads(combined_summary.read_text(encoding="utf-8"))
    assert payload_comb["version"] == 1
    assert payload_comb["subproject"] == "apg"
    assert payload_comb["suite"] == "combined"
    assert payload_comb["test_status"] == "error"
    assert payload_comb["gate_status"] == "error"
    assert len(payload_comb["source_commit"]) == 40

    # Missing summary file argument fails with error (exit 2)
    res_missing = run_command("policy", "--summary-file")
    assert res_missing.returncode == 2


def test_intentional_worker_crash_writes_error_summary_file(
    tmp_path: Path,
) -> None:
    summary_file = tmp_path / "ci" / "crash-failure-summary.json"
    result = run_command(
        "unit",
        "--workers",
        "2",
        "--verify-failure-mode",
        "worker-crash",
        "--summary-file",
        str(summary_file),
    )
    assert result.returncode == 1
    assert "worker-complete set is incomplete" in result.stderr
    assert summary_file.is_file()
    assert oct(stat.S_IMODE(summary_file.stat().st_mode)) == "0o600"
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["subproject"] == "apg"
    assert payload["suite"] == "unit"
    assert payload["test_status"] == "error"
    assert payload["gate_status"] == "error"
    assert len(payload["source_commit"]) == 40


def test_invalid_role_writes_error_summary_file(
    tmp_path: Path,
) -> None:
    summary_file = tmp_path / "ci" / "invalid-role-summary.json"
    result = run_command("invalid-role", "--summary-file", str(summary_file))
    assert result.returncode == 2
    assert summary_file.is_file()
    assert oct(stat.S_IMODE(summary_file.stat().st_mode)) == "0o600"
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["subproject"] == "apg"
    assert payload["suite"] == "unknown"
    assert payload["test_status"] == "error"
    assert payload["gate_status"] == "error"
    assert len(payload["source_commit"]) == 40

    # Also verify early arg parsing with unit-integration and --summary-file=<path>
    invalid_summary = tmp_path / "ci" / "invalid-args-combined-summary.json"
    res_inv = run_command("unit-integration", "--invalid-flag", f"--summary-file={invalid_summary}")
    assert res_inv.returncode == 2
    assert invalid_summary.is_file()
    assert oct(stat.S_IMODE(invalid_summary.stat().st_mode)) == "0o600"
    payload_inv = json.loads(invalid_summary.read_text(encoding="utf-8"))
    assert payload_inv["version"] == 1
    assert payload_inv["subproject"] == "apg"
    assert payload_inv["suite"] == "combined"
    assert payload_inv["test_status"] == "error"
    assert payload_inv["gate_status"] == "error"
    assert len(payload_inv["source_commit"]) == 40

    # A malformed final output option must not reuse an earlier receipt target.
    previous_summary = tmp_path / "ci" / "previous-summary.json"
    previous_payload = dict(payload, suite="policy", test_status="pass", gate_status="pass")
    previous_bytes = json.dumps(previous_payload).encode("utf-8")
    previous_summary.write_bytes(previous_bytes)
    previous_summary.chmod(0o600)
    for malformed_tail in (("--summary-file=",), ("--summary-file", "--invalid-flag")):
        malformed = run_command(
            "invalid-role", "--summary-file", str(previous_summary), *malformed_tail
        )
        assert malformed.returncode == 2
        assert previous_summary.read_bytes() == previous_bytes
        assert stat.S_IMODE(previous_summary.stat().st_mode) == 0o600


def test_missing_prerequisite_typescript_tsc_with_summary_file_writes_error_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary_file = tmp_path / "ci" / "missing-tsc-summary.json"
    monkeypatch.delenv("APG_TYPESCRIPT_TSC", raising=False)
    environment = os.environ.copy()
    result = run_command("unit", "--summary-file", str(summary_file), environment=environment)
    assert result.returncode == 1
    assert "TypeScript test prerequisite is unavailable" in result.stderr
    assert summary_file.is_file()
    assert oct(stat.S_IMODE(summary_file.stat().st_mode)) == "0o600"
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["subproject"] == "apg"
    assert payload["suite"] == "unit"
    assert payload["test_status"] == "error"
    assert payload["gate_status"] == "error"
    assert len(payload["source_commit"]) == 40


def test_reused_summary_path_overwrites_prior_summary(
    tmp_path: Path,
) -> None:
    summary_file = tmp_path / "ci" / "reused-summary.json"
    # First invocation: policy passes
    res1 = run_command("policy", "--summary-file", str(summary_file))
    assert res1.returncode == 0
    p1 = json.loads(summary_file.read_text(encoding="utf-8"))
    assert p1["test_status"] == "pass"
    assert p1["gate_status"] == "pass"

    # Second invocation: invalid worker count fails with error/error
    res2 = run_command("unit", "--workers", "0", "--summary-file", str(summary_file))
    assert res2.returncode == 1
    p2 = json.loads(summary_file.read_text(encoding="utf-8"))
    assert p2["test_status"] == "error"
    assert p2["gate_status"] == "error"
    assert p2["suite"] == "unit"


def test_missing_prerequisite_javascript_node_with_summary_file_writes_error_summary(
    tmp_path: Path,
) -> None:
    fake_tsc = tmp_path / "bin" / "tsc"
    fake_tsc.parent.mkdir(parents=True, exist_ok=True)
    fake_tsc.write_text("#!/bin/sh\necho 'Version 7.0.2'\n", encoding="utf-8")
    fake_tsc.chmod(0o755)

    summary_file = tmp_path / "ci" / "missing-node-summary.json"
    environment = os.environ.copy()
    environment["APG_TYPESCRIPT_TSC"] = str(fake_tsc)
    environment.pop("APG_JAVASCRIPT_NODE", None)
    result = run_command("unit", "--summary-file", str(summary_file), environment=environment)
    assert result.returncode == 1
    assert "JavaScript test prerequisite is unavailable" in result.stderr
    assert summary_file.is_file()
    assert oct(stat.S_IMODE(summary_file.stat().st_mode)) == "0o600"
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["subproject"] == "apg"
    assert payload["suite"] == "unit"
    assert payload["test_status"] == "error"
    assert payload["gate_status"] == "error"
    assert len(payload["source_commit"]) == 40


def _clone_disposable_repo(target_dir: Path) -> Path:
    """Clone a disposable checkout of REPOSITORY_ROOT into target_dir."""
    subprocess.run(
        ["git", "clone", "-s", str(REPOSITORY_ROOT), str(target_dir)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    import shutil
    candidate_apg_test = REPOSITORY_ROOT / "libexec" / "apg_test.py"
    if candidate_apg_test.is_file():
        shutil.copy2(candidate_apg_test, target_dir / "libexec" / "apg_test.py")
    return target_dir


def test_policy_inventory_failure_writes_fail_summary(
    tmp_path: Path,
    repo_state_snapshot: None,
) -> None:
    repo = _clone_disposable_repo(tmp_path / "disposable-repo")
    probe = repo / "libexec" / "apg_temp_uninventoried_probe.py"
    probe.write_text("# temporary uninventoried probe\n", encoding="utf-8")
    summary_file = tmp_path / "ci" / "policy-inv-fail-summary.json"

    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
    result = subprocess.run(
        [str(repo / "bin" / "apg-test"), "policy", "--summary-file", str(summary_file)],
        cwd=repo,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.returncode == 1
    assert "coverage source inventory differs" in result.stderr
    assert summary_file.is_file()
    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload["test_status"] == "fail"
    assert payload["gate_status"] == "fail"
    assert payload["suite"] == "policy"
    assert len(payload["source_commit"]) == 40


def test_concurrent_invocation_isolation_for_disposable_fixture(
    tmp_path: Path,
    repo_state_snapshot: None,
) -> None:
    import concurrent.futures

    def run_isolated_probe(worker_id: int) -> dict[str, object]:
        repo = _clone_disposable_repo(tmp_path / f"repo-{worker_id}")
        probe = repo / "libexec" / f"probe_{worker_id}.py"
        probe.write_text(f"# probe {worker_id}\n", encoding="utf-8")
        summary_file = tmp_path / f"summary-{worker_id}.json"
        environment = os.environ.copy()
        environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
        result = subprocess.run(
            [str(repo / "bin" / "apg-test"), "policy", "--summary-file", str(summary_file)],
            cwd=repo,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert result.returncode == 1
        assert "coverage source inventory differs" in result.stderr
        assert summary_file.is_file()
        return json.loads(summary_file.read_text(encoding="utf-8"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_isolated_probe, i) for i in (1, 2)]
        results = [f.result() for f in futures]

    for p in results:
        assert p["test_status"] == "fail"
        assert p["gate_status"] == "fail"
        assert p["suite"] == "policy"


def test_maintained_jaca_ci_fixtures_conform_to_schema() -> None:
    fixtures_dir = REPOSITORY_ROOT / "testing" / "fixtures" / "jaca_ci"
    assert fixtures_dir.is_dir()

    # 1. sample-summary-pass.json
    pass_file = fixtures_dir / "sample-summary-pass.json"
    assert pass_file.is_file()
    pass_data = json.loads(pass_file.read_text(encoding="utf-8"))
    assert set(pass_data.keys()) == {"version", "subproject", "suite", "test_status", "gate_status", "source_commit"}
    assert pass_data["version"] == 1
    assert pass_data["subproject"] == "apg"
    assert pass_data["suite"] == "policy"
    assert pass_data["test_status"] == "pass"
    assert pass_data["gate_status"] == "pass"
    assert len(pass_data["source_commit"]) == 40

    # 2. sample-summary-fail.json
    fail_file = fixtures_dir / "sample-summary-fail.json"
    assert fail_file.is_file()
    fail_data = json.loads(fail_file.read_text(encoding="utf-8"))
    assert set(fail_data.keys()) == {"version", "subproject", "suite", "test_status", "gate_status", "source_commit"}
    assert fail_data["version"] == 1
    assert fail_data["subproject"] == "apg"
    assert fail_data["suite"] == "unit"
    assert fail_data["test_status"] == "fail"
    assert fail_data["gate_status"] == "fail"
    assert len(fail_data["source_commit"]) == 40

    # 3. illustrative PR fixtures
    for pr_fixture_name in ("valid-apg-pr.json", "invalid-role-pr.json", "drift-pr.json"):
        pr_path = fixtures_dir / pr_fixture_name
        assert pr_path.is_file()
        pr_data = json.loads(pr_path.read_text(encoding="utf-8"))
        assert pr_data["schema"] == "apgr-ci-illustrative-fixture-v1"
        assert pr_data["repository"] == "example/apgr-fixture"
        assert pr_data["head_repository"] == pr_data["repository"]
        assert pr_data["base_object"] == "2" * 40
        assert pr_data["head_object"] == "1" * 40
        assert len(pr_data["head_object"]) == 40
        assert len(pr_data["base_object"]) == 40


def test_jaca_ci_conformance_model_accepts_valid_summary_and_rejects_malformed(
    tmp_path: Path,
) -> None:
    """Executable JACA CI Conformance Model pinned to lair001/joint-agentic-command-aegis_dev@4fcc610f0b9ae8142e0ab9f7d29f75b43f187b90 (proposed contract enforcing strict key set validation following ci-policy branch, stricter than current rnr-unit unmarshal path)."""
    def jaca_consume_role_evidence(
        repo_root: Path, role_id: str, commit: str
    ) -> dict[str, object]:
        role_map = {
            "apg-policy": ("policy", ".test-reports/apg/policy/summary.json"),
            "apg-unit": ("unit", ".test-reports/apg/unit/summary.json"),
            "apg-integration": ("integration", ".test-reports/apg/integration/summary.json"),
            "apg-dev-gate": ("combined", ".test-reports/apg/combined/summary.json"),
        }
        if role_id not in role_map:
            raise ValueError("unknown role evidence owner")
        expected_suite, relative = role_map[role_id]
        absolute = repo_root / relative

        # requirePathBeneath
        resolved_root = repo_root.resolve(strict=True)
        resolved_target = absolute.resolve()
        if resolved_target != resolved_root and resolved_root not in resolved_target.parents:
            raise ValueError("evidence path escapes root")

        # requireNoSymlinkComponents
        rel = absolute.relative_to(repo_root)
        current = repo_root
        for part in rel.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("evidence path contains a symlink")

        try:
            st = os.lstat(absolute)
        except OSError as err:
            raise ValueError(f"inspect project evidence {relative!r}: {err}") from err
        if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or st.st_size > 1024 * 1024:
            raise ValueError(f"project evidence {relative!r} is unsafe or oversized")

        content = absolute.read_bytes()
        digest = hashlib.sha256(content).hexdigest()

        summary = json.loads(content.decode("utf-8"))
        allowed_keys = {"version", "subproject", "suite", "test_status", "gate_status", "source_commit"}
        if set(summary.keys()) != allowed_keys:
            raise ValueError("evidence summary keys mismatch")

        if (
            summary.get("version") != 1
            or summary.get("subproject") != "apg"
            or summary.get("suite") != expected_suite
            or summary.get("test_status") != "pass"
            or summary.get("gate_status") != "pass"
            or summary.get("source_commit") != commit
        ):
            raise ValueError("APG summary identity or terminal status mismatch")

        return {
            "digest": {"path": relative, "sha256": digest, "bytes": st.st_size},
            "summary": summary,
        }

    # Verify against real policy summary generated under mock root
    mock_root = tmp_path / "mock-repo"
    reports_dir = mock_root / ".test-reports/apg/policy"
    reports_dir.mkdir(parents=True)
    summary_file = reports_dir / "summary.json"

    # Generate real summary
    commit = apg_test.resolve_source_commit(REPOSITORY_ROOT)
    apg_test.write_summary(
        summary_file,
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit=commit,
    )

    # Acceptance check
    result = jaca_consume_role_evidence(mock_root, "apg-policy", commit)
    assert result["summary"]["test_status"] == "pass"
    assert result["digest"]["path"] == ".test-reports/apg/policy/summary.json"

    # Negative 1: wrong commit
    with pytest.raises(ValueError, match="terminal status mismatch"):
        jaca_consume_role_evidence(mock_root, "apg-policy", "0" * 40)

    # Negative 2: wrong role / suite mismatch
    unit_reports = mock_root / ".test-reports/apg/unit"
    unit_reports.mkdir(parents=True)
    unit_summary = unit_reports / "summary.json"
    apg_test.write_summary(
        unit_summary,
        suite="policy",  # Mismatched suite for apg-unit
        test_status="pass",
        gate_status="pass",
        source_commit=commit,
    )
    with pytest.raises(ValueError, match="terminal status mismatch"):
        jaca_consume_role_evidence(mock_root, "apg-unit", commit)

    # Negative 3: missing evidence file
    with pytest.raises(ValueError, match="inspect project evidence"):
        jaca_consume_role_evidence(mock_root, "apg-integration", commit)

    # Negative 4: unknown role
    with pytest.raises(ValueError, match="unknown role evidence owner"):
        jaca_consume_role_evidence(mock_root, "apg-unknown", commit)

    # Negative 5: unknown fields (strict decoder)
    summary_file.write_text(
        json.dumps({
            "version": 1, "subproject": "apg", "suite": "policy",
            "test_status": "pass", "gate_status": "pass",
            "source_commit": commit, "extra_field": "disallowed",
        }),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="keys mismatch"):
        jaca_consume_role_evidence(mock_root, "apg-policy", commit)

    # Negative 6: symlink in path
    summary_file.unlink()
    real_target = mock_root / "internal-target.json"
    real_target.write_text(
        json.dumps({
            "version": 1, "subproject": "apg", "suite": "policy",
            "test_status": "pass", "gate_status": "pass",
            "source_commit": commit,
        }),
        encoding="utf-8",
    )
    summary_file.symlink_to(real_target)
    with pytest.raises(ValueError, match="symlink"):
        jaca_consume_role_evidence(mock_root, "apg-policy", commit)


def test_refused_summary_paths_are_strictly_preserved(
    tmp_path: Path,
    repo_state_snapshot: None,
) -> None:
    # 1. Tracked valid receipt
    sample_file = REPOSITORY_ROOT / "testing" / "fixtures" / "jaca_ci" / "sample-summary-pass.json"
    assert sample_file.is_file()
    sample_sha = hashlib.sha256(sample_file.read_bytes()).hexdigest()
    res1 = run_command("policy", "--summary-file", str(sample_file))
    assert res1.returncode == 1
    assert "cannot target tracked file" in res1.stderr
    assert hashlib.sha256(sample_file.read_bytes()).hexdigest() == sample_sha

    # 2. Tracked code file
    code_file = REPOSITORY_ROOT / "libexec" / "apg_test.py"
    code_sha = hashlib.sha256(code_file.read_bytes()).hexdigest()
    res2 = run_command("policy", "--summary-file", str(code_file))
    assert res2.returncode == 1
    assert "cannot target tracked file" in res2.stderr
    assert hashlib.sha256(code_file.read_bytes()).hexdigest() == code_sha

    # 3. Receipt-shaped file inside .git (in a disposable clone to protect live repo)
    disposable_repo = _clone_disposable_repo(tmp_path / "git-meta-disposable")
    git_dir = disposable_repo / ".git"
    git_receipt = git_dir / "temp-test-receipt.json"
    git_receipt.write_text(
        json.dumps({
            "version": 1, "subproject": "apg", "suite": "policy",
            "test_status": "pass", "gate_status": "pass", "source_commit": "0" * 40,
        }),
        encoding="utf-8",
    )
    git_receipt_sha = hashlib.sha256(git_receipt.read_bytes()).hexdigest()
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
    res3 = subprocess.run(
        [str(disposable_repo / "bin" / "apg-test"), "policy", "--summary-file", str(git_receipt)],
        cwd=disposable_repo,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert res3.returncode == 1
    assert "cannot target Git metadata" in res3.stderr
    assert git_receipt.is_file()
    assert hashlib.sha256(git_receipt.read_bytes()).hexdigest() == git_receipt_sha

    # 4. Output symlink pointing to protected content
    symlink_target = tmp_path / "link-to-tracked.json"
    symlink_target.symlink_to(sample_file)
    res4 = run_command("policy", "--summary-file", str(symlink_target))
    assert res4.returncode == 1
    assert "cannot target a symlink" in res4.stderr
    assert symlink_target.is_symlink()
    assert hashlib.sha256(sample_file.read_bytes()).hexdigest() == sample_sha

    # 5. Invalid argv with refused path preserves refused path
    res5 = run_command("invalid-role", "--summary-file", str(sample_file))
    assert res5.returncode == 2
    assert hashlib.sha256(sample_file.read_bytes()).hexdigest() == sample_sha

    # 6. Error path with refused path preserves refused path
    res6 = run_command("unit", "--workers", "0", "--summary-file", str(sample_file))
    assert res6.returncode == 1
    assert hashlib.sha256(sample_file.read_bytes()).hexdigest() == sample_sha


def test_inverse_alias_refused_and_preserved_in_disposable_repo(
    tmp_path: Path,
    repo_state_snapshot: None,
) -> None:
    disposable_repo = _clone_disposable_repo(tmp_path / "inverse-alias-repo")
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")

    # Create valid external receipt
    outside_receipt = tmp_path / "outside-valid-receipt.json"
    commit = apg_test.resolve_source_commit(REPOSITORY_ROOT)
    apg_test.write_summary(
        outside_receipt,
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit=commit,
    )
    outside_sha = hashlib.sha256(outside_receipt.read_bytes()).hexdigest()

    # Create tracked symlink inside repo pointing to the outside receipt
    tracked_symlink = disposable_repo / "tracked-symlink.json"
    tracked_symlink.symlink_to(outside_receipt)
    subprocess.run(["git", "add", "tracked-symlink.json"], cwd=disposable_repo, check=True)
    subprocess.run(["git", "commit", "-m", "add tracked symlink"], cwd=disposable_repo, check=True)

    head_before = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=disposable_repo, text=True).strip()
    status_before = subprocess.check_output(["git", "status", "--porcelain"], cwd=disposable_repo, text=True).strip()

    # 1. Normal validation invocation (policy) targeting the tracked symlink
    res_policy = subprocess.run(
        [str(disposable_repo / "bin" / "apg-test"), "policy", "--summary-file", str(tracked_symlink)],
        cwd=disposable_repo,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert res_policy.returncode == 1
    assert "cannot target a symlink" in res_policy.stderr
    assert tracked_symlink.is_symlink()
    assert hashlib.sha256(outside_receipt.read_bytes()).hexdigest() == outside_sha
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=disposable_repo, text=True).strip() == head_before
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=disposable_repo, text=True).strip() == status_before

    # 2. Invalid argv targeting the tracked symlink
    res_invalid = subprocess.run(
        [str(disposable_repo / "bin" / "apg-test"), "invalid-role", "--summary-file", str(tracked_symlink)],
        cwd=disposable_repo,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert res_invalid.returncode == 2
    assert tracked_symlink.is_symlink()
    assert hashlib.sha256(outside_receipt.read_bytes()).hexdigest() == outside_sha
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=disposable_repo, text=True).strip() == head_before
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=disposable_repo, text=True).strip() == status_before

    # 3. Positive case: ordinary fresh ignored output under repository succeeds
    ignored_summary = disposable_repo / ".test-reports" / "apg" / "policy" / "fresh-summary.json"
    res_ignored = subprocess.run(
        [str(disposable_repo / "bin" / "apg-test"), "policy", "--summary-file", str(ignored_summary)],
        cwd=disposable_repo,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert res_ignored.returncode == 0, f"{res_ignored.stderr}\n{res_ignored.stdout}"
    assert ignored_summary.is_file()
    assert apg_test._is_apgr_receipt(ignored_summary)

    # 4. Positive case: ordinary fresh scratch output outside repository succeeds
    scratch_summary = tmp_path / "scratch-summary.json"
    res_scratch = subprocess.run(
        [str(disposable_repo / "bin" / "apg-test"), "policy", "--summary-file", str(scratch_summary)],
        cwd=disposable_repo,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert res_scratch.returncode == 0, f"{res_scratch.stderr}\n{res_scratch.stdout}"
    assert scratch_summary.is_file()
    assert apg_test._is_apgr_receipt(scratch_summary)


def test_real_pytest_empty_collection_exit_status_5_handling(
    tmp_path: Path,
) -> None:
    empty_test_dir = tmp_path / "empty_tests"
    empty_test_dir.mkdir()
    res = subprocess.run(
        [sys.executable, "-m", "pytest", str(empty_test_dir)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 5
    empty_repo = _clone_disposable_repo(tmp_path / "empty-repo")
    empty_unit = empty_repo / "src" / "test" / "unit" / "python" / "agentic-praxis-grimoire"
    import shutil
    shutil.rmtree(empty_unit)
    empty_unit.mkdir(parents=True)
    art = tmp_path / "artifacts"
    art.mkdir()
    with pytest.raises(apg_test.InvocationError, match="collected no tests"):
        apg_test._run_pytest(empty_repo, "unit", 1, art)


def test_real_bounded_sigint_process_cancellation(
    tmp_path: Path,
    repo_state_snapshot: None,
) -> None:
    import signal, time
    sigint_repo = _clone_disposable_repo(tmp_path / "sigint-repo")
    summary_file = tmp_path / "sigint-summary.json"
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
    worker_root = Path(environment.get("TMPDIR", "/tmp")).resolve(strict=True)
    with tempfile.TemporaryDirectory(
        prefix="apg-sigint-pytest-", dir=worker_root.parent
    ) as pytest_root:
        environment["PYTEST_ADDOPTS"] = f"--basetemp={shlex.quote(pytest_root)}"
        proc = subprocess.Popen(
            [str(sigint_repo / "bin" / "apg-test"), "unit", "--workers", "1", "--summary-file", str(summary_file)],
            cwd=sigint_repo,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(1.0)
        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=15)
        assert proc.returncode == 130
        assert "interrupted" in stderr
        assert summary_file.is_file()
        payload = json.loads(summary_file.read_text(encoding="utf-8"))
        assert payload["test_status"] == "error"
        assert payload["gate_status"] == "error"
        assert payload["suite"] == "unit"
        assert len(payload["source_commit"]) == 40


def test_head_drift_in_disposable_repo(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = _clone_disposable_repo(tmp_path / "drift-repo")
    summary_file = tmp_path / "drift-summary.json"
    apg_test.write_summary(
        summary_file,
        suite="policy",
        test_status="pass",
        gate_status="pass",
        source_commit="0" * 40,
    )
    assert summary_file.is_file()

    commits = iter(["0" * 40, "1" * 40])
    from unittest.mock import patch
    with patch("apg_test.resolve_source_commit", lambda _r: next(commits)):
        saved_cwd = os.getcwd()
        try:
            os.chdir(repo)
            exit_code = apg_test.main(["policy", "--summary-file", str(summary_file)])
        finally:
            os.chdir(saved_cwd)
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "git HEAD drifted during execution" in captured.err
        assert not summary_file.exists()
