"""Ratchet inventory changes, checker failures, and mypy identity failures cannot pass as presence checks."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv

sys.path.insert(0, str(Path(__file__).resolve().parents[7]))

from tools.ci.mypy_identity import get_expected_mypy_version
from tools.ci.pre_review_evaluation import evaluate
from tools.ci.pre_review_records import ROOT, Check
from tools.ci.retained_python_ratchets import evaluate_ratchets
from tools.ci.run_pre_review import execute_all


def fixture(root: Path) -> Path:
    owner = root / "src/agentic_praxis_grimoire/__init__.py"
    owner.parent.mkdir(parents=True, exist_ok=True)
    owner.write_text("", encoding="utf-8")
    baseline = root / "baseline.json"
    baseline.write_text(
        json.dumps({
            "schema": "apg-retained-python-ratchets-v1",
            "paths": [str(owner.relative_to(root))],
            "quality": {"ruff_f": 0, "mypy": 0},
        }),
        encoding="utf-8",
    )
    return baseline


def make_tool_root(root: Path) -> Path:
    tool_root = root / "tools"
    py_bin = tool_root / "python" / "bin"
    py_bin.mkdir(parents=True, exist_ok=True)
    python_exe = py_bin / "python"
    python_exe.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    python_exe.chmod(0o755)
    return tool_root


def make_synthetic_tool_root(root: Path, *, version: str | None = None) -> tuple[Path, Path]:
    tool_root = root / "tools"
    python_dir = tool_root / "python"
    venv.EnvBuilder(with_pip=False).create(python_dir)
    python = python_dir / "bin/python"
    sites = json.loads(
        subprocess.check_output(
            [str(python), "-I", "-c", "import json,site;print(json.dumps(site.getsitepackages()))"],
            text=True,
        )
    )
    site = next(Path(p) for p in sites if Path(p).is_relative_to(python_dir))
    package = site / "mypy"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("# Synthetic tool for identity contract only.\n", encoding="utf-8")
    pin = version or get_expected_mypy_version()
    metadata = site / f"mypy-{pin}.dist-info"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "METADATA").write_text(f"Metadata-Version: 2.1\nName: mypy\nVersion: {pin}\n", encoding="utf-8")
    (package / "__main__.py").write_text(
        f"import sys\nprint('mypy {pin}' if '--version' in sys.argv else 'owned synthetic check')\n",
        encoding="utf-8",
    )
    return tool_root, python


def test_independent_findings_are_not_waived(tmp_path: Path) -> None:
    baseline = fixture(tmp_path)
    tool_root = make_tool_root(tmp_path)
    python_dir = (tool_root / "python").resolve()
    calls = []

    def run(command, **kwargs):
        cmd = list(command)
        if "-c" in cmd:
            payload = {
                "prefix": str(python_dir),
                "mypy_file": str(python_dir / "lib/mypy/__init__.py"),
                "meta_version": "1.15.0",
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if "--version" in cmd:
            return subprocess.CompletedProcess(command, 0, "mypy 1.15.0", "")
        calls.append(command)
        return subprocess.CompletedProcess(command, 1, "findings", "")

    report, code = evaluate_ratchets(baseline, root=tmp_path, tool_root=tool_root, runner=run)
    assert code == 1 and len(calls) == 2
    assert set(report["checks"]) == {"ruff_f", "mypy"}
    assert report["checks"]["ruff_f"]["classification"] == "policy-finding"
    assert report["checks"]["mypy"]["classification"] == "policy-finding"


def test_missing_tool_is_not_a_policy_finding(tmp_path: Path) -> None:
    baseline = fixture(tmp_path)
    tool_root = make_tool_root(tmp_path)

    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 1, "", "No module named mypy")

    assert evaluate_ratchets(baseline, root=tmp_path, tool_root=tool_root, runner=run)[1] == 2


def test_owner_addition_and_baseline_inflation_refused(tmp_path: Path) -> None:
    baseline = fixture(tmp_path)
    (tmp_path / "src/agentic_praxis_grimoire/new.py").write_text("", encoding="utf-8")
    assert evaluate_ratchets(baseline, root=tmp_path)[1] == 1
    doc = json.loads(baseline.read_text(encoding="utf-8"))
    doc["quality"]["mypy"] = 7
    baseline.write_text(json.dumps(doc), encoding="utf-8")
    assert evaluate_ratchets(baseline, root=tmp_path)[1] == 2


def test_ratchet_identity_failure_rootless(tmp_path: Path) -> None:
    baseline = fixture(tmp_path)
    report, code = evaluate_ratchets(baseline, root=tmp_path, tool_root=None)
    assert code == 2
    assert report["status"] == "failed"
    assert report["classification"] == "tool-failure"
    assert report["checks"]["mypy"]["classification"] == "tool-failure"


def test_ratchet_identity_failure_wrong_version(tmp_path: Path) -> None:
    baseline = fixture(tmp_path)
    tool_root = make_tool_root(tmp_path)
    python_dir = (tool_root / "python").resolve()

    def run(command, **kwargs):
        cmd = list(command)
        if "-c" in cmd:
            payload = {
                "prefix": str(python_dir),
                "mypy_file": str(python_dir / "lib/mypy/__init__.py"),
                "meta_version": "1.14.0",
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if "--version" in cmd:
            return subprocess.CompletedProcess(command, 0, "mypy 1.14.0", "")
        return subprocess.CompletedProcess(command, 0, "", "")

    report, code = evaluate_ratchets(baseline, root=tmp_path, tool_root=tool_root, runner=run)
    assert code == 2
    assert report["status"] == "failed"
    assert report["classification"] == "tool-failure"
    assert report["checks"]["mypy"]["classification"] == "tool-failure"


def test_ratchet_identity_failure_wrong_root(tmp_path: Path) -> None:
    baseline = fixture(tmp_path)
    tool_root = make_tool_root(tmp_path)
    python_dir = (tool_root / "python").resolve()

    def run(command, **kwargs):
        cmd = list(command)
        if "-c" in cmd:
            payload = {
                "prefix": "/opt/ambient/python",
                "mypy_file": str(python_dir / "lib/mypy/__init__.py"),
                "meta_version": "1.15.0",
            }
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if "--version" in cmd:
            return subprocess.CompletedProcess(command, 0, "mypy 1.15.0", "")
        return subprocess.CompletedProcess(command, 0, "", "")

    report, code = evaluate_ratchets(baseline, root=tmp_path, tool_root=tool_root, runner=run)
    assert code == 2
    assert report["status"] == "failed"
    assert report["classification"] == "tool-failure"
    assert report["checks"]["mypy"]["classification"] == "tool-failure"


def test_real_subprocess_ratchet_owned_identity_stderr_and_ambient_shadow_ignored() -> None:
    """Exercise real retained_python_ratchets.py subprocess with synthetic owned mypy and ambient shadow.

    Verifies that:
    1. Entire stdout parses cleanly with json.loads (identity diagnostic is on stderr, not stdout).
    2. The owned mypy leg passes with returncode 0 and classification 'passed'.
    3. The verified identity diagnostic appears on stderr (exactly one line for identity).
    4. Ambient shadow executables and packages are ignored and never invoked.
    5. The real per-check run_pre_review executor (clean_env/capture) and evaluator classify
       without encountering invalid JSON.
    """
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = Path(raw_tmp).resolve()
        tool_root, _ = make_synthetic_tool_root(tmp_path)

        # Ambient shadow that must never be invoked
        ambient = tmp_path / "ambient"
        (ambient / "mypy").mkdir(parents=True, exist_ok=True)
        marker = tmp_path / "shadow-executed"
        (ambient / "mypy/__init__.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
            encoding="utf-8",
        )
        executable = ambient / "mypy-bin"
        executable.mkdir(parents=True, exist_ok=True)
        shadow_mypy = executable / "mypy"
        shadow_mypy.write_text(
            f"#!/bin/sh\n"
            f"touch '{marker}'\n"
            f"exit 99\n",
            encoding="utf-8",
        )
        shadow_mypy.chmod(0o755)

        env = dict(os.environ)
        env["PYTHONPATH"] = str(ambient)
        env["PATH"] = f"{executable}:{env.get('PATH', '')}"

        # 1. Run real retained_python_ratchets.py via subprocess
        ratchet_script = ROOT / "tools/ci/retained_python_ratchets.py"
        baseline_file = ROOT / "tools/ci/retained_python_ratchets.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(ratchet_script),
                "--baseline",
                str(baseline_file),
                "--tool-root",
                str(tool_root),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        # stdout must parse entirely with json.loads
        report = json.loads(proc.stdout)

        assert report.get("schema") == "apg-retained-python-ratchets-result-v1"
        assert "checks" in report
        assert "mypy" in report["checks"]

        # Owned mypy leg passes with returncode 0 and classification 'passed'
        assert report["checks"]["mypy"]["classification"] == "passed"
        assert report["checks"]["mypy"]["returncode"] == 0

        # Identity on stderr, not stdout
        expected_version = get_expected_mypy_version()
        assert "mypy identity verified:" not in proc.stdout
        assert "mypy identity verified:" in proc.stderr
        identity_lines = [
            line for line in proc.stderr.splitlines() if "mypy identity verified:" in line
        ]
        assert len(identity_lines) == 1
        assert f"mypy identity verified: version={expected_version};" in identity_lines[0]
        assert f"prefix={tool_root / 'python'}" in identity_lines[0]

        # Shadow executable/package not invoked
        assert not marker.exists()

        # 2. Exercise real per-check run_pre_review executor (clean_env/capture) and evaluator
        check = Check(
            "retained-python-ratchets",
            (
                sys.executable,
                str(ratchet_script),
                "--baseline",
                str(baseline_file),
                "--tool-root",
                str(tool_root),
            ),
            cwd=ROOT,
            policy="retained-python-ratchets",
            python_owned=True,
        )
        evidence_dir = tmp_path / "evidence"
        scratch_dir = tmp_path / "scratch"
        results = execute_all(
            (check,),
            evidence_dir,
            scratch_dir=scratch_dir,
            tool_root=tool_root,
        )
        assert len(results) == 1
        result = results[0]
        assert result.name == "retained-python-ratchets"
        # Must classify without invalid JSON error
        assert result.detail != "retained ratchet JSON was invalid"
        assert result.classification == report["classification"]

        # Directly exercise evaluator
        _, eval_detail, eval_class = evaluate(
            check,
            proc.returncode,
            proc.stdout,
            proc.stderr,
        )
        assert eval_detail != "retained ratchet JSON was invalid"
        assert eval_class == report["classification"]


def test_real_subprocess_ratchet_wrong_or_rootless_fails_closed() -> None:
    """Real retained_python_ratchets.py fails closed when tool-root is absent or wrong."""
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_path = Path(raw_tmp).resolve()
        ratchet_script = ROOT / "tools/ci/retained_python_ratchets.py"
        baseline_file = ROOT / "tools/ci/retained_python_ratchets.json"

        # 1. Rootless invocation fails closed with exit code 2
        proc_rootless = subprocess.run(
            [
                sys.executable,
                str(ratchet_script),
                "--baseline",
                str(baseline_file),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc_rootless.returncode == 2
        report_rootless = json.loads(proc_rootless.stdout)
        assert report_rootless["classification"] == "tool-failure"
        assert report_rootless["checks"]["mypy"]["classification"] == "tool-failure"
        assert "missing tool-root" in report_rootless["checks"]["mypy"]["detail"]

        # Evaluator also classifies rootless without invalid JSON
        check_rootless = Check(
            "retained-python-ratchets",
            (sys.executable, str(ratchet_script), "--baseline", str(baseline_file)),
            cwd=ROOT,
            policy="retained-python-ratchets",
            python_owned=True,
        )
        _, eval_detail, eval_class = evaluate(
            check_rootless,
            proc_rootless.returncode,
            proc_rootless.stdout,
            proc_rootless.stderr,
        )
        assert eval_detail != "retained ratchet JSON was invalid"
        assert eval_class == "tool-failure"

        # 2. Wrong version fails closed with exit code 2
        wrong_root, _ = make_synthetic_tool_root(tmp_path / "wrong", version="1.14.0")
        proc_wrong = subprocess.run(
            [
                sys.executable,
                str(ratchet_script),
                "--baseline",
                str(baseline_file),
                "--tool-root",
                str(wrong_root),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc_wrong.returncode == 2
        report_wrong = json.loads(proc_wrong.stdout)
        assert report_wrong["classification"] == "tool-failure"
        assert report_wrong["checks"]["mypy"]["classification"] == "tool-failure"
        assert "does not agree with CI_REQUIREMENTS" in report_wrong["checks"]["mypy"]["detail"]
