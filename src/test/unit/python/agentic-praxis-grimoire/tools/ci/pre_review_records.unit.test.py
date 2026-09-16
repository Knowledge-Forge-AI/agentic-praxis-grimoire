"""Unit tests for pre_review_records data structures and sanitization."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.ci.pre_review_records import (
    ROOT,
    Check,
    Result,
    sanitize,
    sanitize_machine_result,
)


def test_check_dataclass_properties() -> None:
    c = Check(
        name="test-check",
        command=("python", "-m", "test"),
        cwd=ROOT,
        policy="exit-zero",
        python_owned=True,
    )
    assert c.name == "test-check"
    assert c.command == ("python", "-m", "test")
    assert c.python_owned is True
    assert c.policy == "exit-zero"
    with pytest.raises(AttributeError):
        c.name = "mutation"


def test_result_dataclass_properties() -> None:
    r = Result(
        name="test-check",
        status="passed",
        returncode=0,
        elapsed_seconds=1.23,
        detail="clean",
        classification="passed",
        interpreter="python3",
    )
    assert r.status == "passed"
    assert r.returncode == 0
    assert r.classification == "passed"


def test_sanitize_removes_root_and_private_paths() -> None:
    text = f"Error in {ROOT}/src/main.py with private /tmp/secret/data"
    sanitized = sanitize(text, Path("/tmp/secret/data"))
    assert str(ROOT) not in sanitized
    assert "<repo>" in sanitized
    assert "<private-path>" in sanitized


def test_sanitize_redacts_tokens_and_secrets() -> None:
    samples = [
        ("Authorization token: my-secret-token-12345", "token: <redacted>"),
        ("api_key = abcdef1234567890", "api_key = <redacted>"),
        ("password: supersecretpassword", "password: <redacted>"),
    ]
    for raw, expected in samples:
        sanitized = sanitize(raw)
        assert "<redacted>" in sanitized
        assert "my-secret-token-12345" not in sanitized
        assert "abcdef1234567890" not in sanitized
        assert "supersecretpassword" not in sanitized


def test_sanitize_machine_result_handles_nested_types() -> None:
    data = {
        "file": f"{ROOT}/src/config.py",
        "nested": ["token: secret123", {"path": f"{ROOT}/docs"}],
        "values": {1, 2},
        "tuple_val": (f"{ROOT}/bin",),
    }
    sanitized = sanitize_machine_result(data)
    assert isinstance(sanitized, dict)
    assert sanitized["file"] == "<repo>/src/config.py"
    assert sanitized["nested"][0] == "token: <redacted>"
    assert sanitized["nested"][1]["path"] == "<repo>/docs"
    assert isinstance(sanitized["values"], set)
    assert sanitized["tuple_val"] == ("<repo>/bin",)


def test_sanitize_machine_result_rejects_key_collision() -> None:
    p1 = Path("/tmp/dir-a/target")
    p2 = Path("/tmp/dir-b/target")
    # Both paths map to <private-path>
    data = {
        str(p1): 1,
        str(p2): 2,
    }
    with pytest.raises(ValueError, match="key collision"):
        sanitize_machine_result(data, p1, p2)
