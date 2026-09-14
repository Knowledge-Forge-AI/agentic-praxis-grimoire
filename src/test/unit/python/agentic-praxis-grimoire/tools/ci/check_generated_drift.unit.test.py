"""The drift adapter delegates exact-byte verification and propagates failure."""
from pathlib import Path
import subprocess
from tools.ci.check_generated_drift import evaluate


def test_uses_maintained_exact_corpus_owner(tmp_path: Path) -> None:
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")
    assert evaluate(tmp_path, run)[1] == 0
    assert commands[0][:3] == ["go", "build", "-o"]
    assert commands[1][1:] == ["skills", "verify-corpus", "--repository", str(tmp_path)]


def test_propagates_mismatch_and_tool_failure(tmp_path: Path) -> None:
    def mismatch(command, **kwargs):
        return subprocess.CompletedProcess(command, 0 if command[0] == "go" else 1, "", "")
    assert evaluate(tmp_path, mismatch)[1] == 1
    assert evaluate(tmp_path, lambda *a, **k: subprocess.CompletedProcess(a, 1, "", ""))[1] == 2
    def unavailable(*args, **kwargs):
        raise FileNotFoundError()
    assert evaluate(tmp_path, unavailable)[1] == 2
