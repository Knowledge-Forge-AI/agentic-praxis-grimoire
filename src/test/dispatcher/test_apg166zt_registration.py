"""Provider-free tests for stage registration provenance and re-resolution validation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
from typing import Any

import pytest

from agent_phase.dispatch import DispatchError, Dispatcher
from agent_phase.envelope import RenderedPrompt
from agent_phase.provider import Result
from agent_phase.routing import Endpoint
from agent_phase.run import RunDirectory, stage_parent_id
from agent_phase.worker_capability import resolve_worker_capability
from apgr_workers.ledger import ParentLedger
from test_agent_phase_antigravity import repository, write_fake_evidence

ROOT = Path(__file__).resolve().parents[3]

AGY_MOCK = r"""#!""" + sys.executable + r"""
import sys
if '--version' in sys.argv:
    print('agy 1.0')
    sys.exit(0)
print('agy ok')
sys.exit(0)
"""


@pytest.fixture
def clean_leaf_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APGR_WORKER_LEAF", raising=False)
    monkeypatch.delenv("APGR_PARENT_ID", raising=False)
    monkeypatch.delenv("APGR_WORKER_STATE_DIR", raising=False)
    monkeypatch.delenv("APGR_WORKERS_REQUIRED", raising=False)


@pytest.fixture
def agy_bin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    agy_path = bin_dir / "agy"
    agy_path.write_text(AGY_MOCK, encoding="utf-8")
    agy_path.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    return bin_dir


def _make_prompt(text: bytes = b"Inspect task") -> RenderedPrompt:
    return RenderedPrompt(text, [{"kind": "task_prompt", "start": 0, "end": len(text)}])


def _make_runner(invocations: list[dict[str, Any]]):
    def runner(argv: list[str], prompt: bytes, cwd: Path, max_output: int, on_output=None) -> Result:
        write_fake_evidence(list(argv), 0)
        now = time.time()
        parent_id = os.environ.get("APGR_PARENT_ID")
        state_dir = os.environ.get("APGR_WORKER_STATE_DIR")
        invocations.append({
            "argv": list(argv),
            "prompt": prompt,
            "parent_id": parent_id,
            "state_dir": state_dir,
        })
        return Result(0, b'{"type":"result","status":"SUCCESS"}', b"", False, now, now)
    return runner


def test_what_actually_registers_with_absent_accounting_state(
    tmp_path: Path, clean_leaf_env: None, agy_bin: Path
) -> None:
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "reg-test-run", "test-stage")
    invocations: list[dict[str, Any]] = []
    runner = _make_runner(invocations)

    dispatcher = Dispatcher(ROOT, repo, runner=runner, resolve_scanner=False)
    assert dispatcher._stage_accounting_state is None

    cap = resolve_worker_capability(
        ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
        bundle=dispatcher.roster.bundle,
    )
    assert cap is not None and cap.get("allowed") is True

    endpoint = Endpoint("antigravity", "gemini-3.8-flash-high")
    rendered = _make_prompt()

    result, meta = dispatcher._stage(
        directory,
        1,
        "work",
        "01-work",
        "reviewer",
        endpoint,
        rendered,
        None,
        read_only=True,
        worker_capability=cap,
    )

    assert result.ok is True
    assert len(invocations) == 1
    parent_id = invocations[0]["parent_id"]
    state_dir = invocations[0]["state_dir"]
    assert parent_id == stage_parent_id(directory.run_id, "work", 1)
    assert state_dir == str(directory.path / "workers")

    ledger = ParentLedger(parent_id, Path(state_dir))
    status = ledger.get_status()
    assert status["registered"] is False or status.get("status") == "closed"
    data = json.loads(ledger.data_path.read_text(encoding="utf-8"))
    reg_cap = data["worker_capability"]
    assert reg_cap["execution_mode"] == "gemini_flash_sub"
    assert reg_cap["parent_family"] == "gemini_flash"
    assert reg_cap["parent_provider"] == "antigravity"
    assert reg_cap["parent_profile"] == "gemini-3.8-flash-high"
    assert reg_cap["limits"]["max_gemini"] == 4
    assert meta["worker_capability"]["execution_mode"] == "gemini_flash_sub"


def test_what_actually_registers_canary_scenario_required_override(
    tmp_path: Path, clean_leaf_env: None, agy_bin: Path
) -> None:
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "reg-test-run", "test-stage")
    invocations: list[dict[str, Any]] = []
    runner = _make_runner(invocations)

    dispatcher = Dispatcher(ROOT, repo, runner=runner, resolve_scanner=False)
    assert dispatcher._stage_accounting_state is None

    cap = resolve_worker_capability(
        ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
        bundle=dispatcher.roster.bundle,
    )
    assert cap is not None
    # Canary supplies locally required override
    cap["requirement"] = "required"

    endpoint = Endpoint("antigravity", "gemini-3.8-flash-high")
    rendered = _make_prompt()

    result, meta = dispatcher._stage(
        directory,
        1,
        "work",
        "01-work",
        "worker",
        endpoint,
        rendered,
        None,
        read_only=True,
        worker_capability=cap,
    )

    assert result.ok is True
    assert len(invocations) == 1
    parent_id = invocations[0]["parent_id"]
    state_dir = invocations[0]["state_dir"]
    ledger = ParentLedger(parent_id, Path(state_dir))
    data = json.loads(ledger.data_path.read_text(encoding="utf-8"))
    reg_cap = data["worker_capability"]
    assert reg_cap["execution_mode"] == "gemini_flash_sub"
    assert reg_cap["parent_family"] == "gemini_flash"
    assert reg_cap["requirement"] == "required"
    assert meta["worker_capability"]["execution_mode"] == "gemini_flash_sub"


@pytest.mark.parametrize("missing_field", [
    "execution_mode",
    "source_root",
    "parent_family",
    "parent_provider",
    "parent_profile",
    "parent_model",
    "parent_effort",
])
def test_missing_provenance_fields_rejected(
    tmp_path: Path, clean_leaf_env: None, agy_bin: Path, missing_field: str
) -> None:
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "reg-test-run", "test-stage")
    invocations: list[dict[str, Any]] = []
    runner = _make_runner(invocations)

    dispatcher = Dispatcher(ROOT, repo, runner=runner, resolve_scanner=False)
    cap = resolve_worker_capability(
        ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
        bundle=dispatcher.roster.bundle,
    )
    assert cap is not None
    cap["requirement"] = "required"
    del cap[missing_field]

    endpoint = Endpoint("antigravity", "gemini-3.8-flash-high")
    with pytest.raises(DispatchError, match=rf"parent registration unavailable \(ValueError:.*{missing_field}"):
        dispatcher._stage(
            directory,
            1,
            "work",
            "01-work",
            "primary",
            endpoint,
            _make_prompt(),
            None,
            read_only=False,
            worker_capability=cap,
        )
    assert len(invocations) == 0


@pytest.mark.parametrize("field,altered_value", [
    ("limits", {"max_gemini": 99, "max_luna": 4, "max_sonnet": 4, "max_aggregate": 12, "max_gemini_workers_per_parent": 99, "max_aggregate_workers_per_codex_parent": 12}),
    ("policy_sha256", "0" * 64),
    ("policy_selection", "triple_pool_2x2"),
    ("parent_model", "wrong-model"),
    ("parent_effort", "low"),
    ("source_root", "/wrong/path"),
])
def test_altered_provenance_fields_rejected(
    tmp_path: Path, clean_leaf_env: None, agy_bin: Path, field: str, altered_value: Any
) -> None:
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "reg-test-run", "test-stage")
    invocations: list[dict[str, Any]] = []
    runner = _make_runner(invocations)

    dispatcher = Dispatcher(ROOT, repo, runner=runner, resolve_scanner=False)
    cap = resolve_worker_capability(
        ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
        bundle=dispatcher.roster.bundle,
    )
    assert cap is not None
    cap["requirement"] = "required"
    cap[field] = altered_value

    endpoint = Endpoint("antigravity", "gemini-3.8-flash-high")
    with pytest.raises(DispatchError, match=rf"parent registration unavailable \(ValueError:.*{field}"):
        dispatcher._stage(
            directory,
            1,
            "work",
            "01-work",
            "primary",
            endpoint,
            _make_prompt(),
            None,
            read_only=False,
            worker_capability=cap,
        )
    assert len(invocations) == 0


@pytest.mark.parametrize("worker_block,sub_key,altered_val", [
    ("gemini_worker", "maximum_concurrency", 99),
    ("luna_worker", "maximum_concurrency", 99),
    ("sonnet_worker", "maximum_concurrency", 99),
    ("native_worker", "enabled", True),
])
def test_altered_worker_blocks_rejected(
    tmp_path: Path, clean_leaf_env: None, agy_bin: Path, worker_block: str, sub_key: str, altered_val: Any
) -> None:
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "reg-test-run", "test-stage")
    invocations: list[dict[str, Any]] = []
    runner = _make_runner(invocations)

    dispatcher = Dispatcher(ROOT, repo, runner=runner, resolve_scanner=False)
    cap = resolve_worker_capability(
        ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
        bundle=dispatcher.roster.bundle,
    )
    assert cap is not None
    cap["requirement"] = "required"
    cap[worker_block] = {**cap[worker_block], sub_key: altered_val}

    endpoint = Endpoint("antigravity", "gemini-3.8-flash-high")
    with pytest.raises(DispatchError, match=rf"parent registration unavailable \(ValueError:.*{worker_block}"):
        dispatcher._stage(
            directory,
            1,
            "work",
            "01-work",
            "primary",
            endpoint,
            _make_prompt(),
            None,
            read_only=False,
            worker_capability=cap,
        )
    assert len(invocations) == 0


def test_mismatched_family_rejected(
    tmp_path: Path, clean_leaf_env: None, agy_bin: Path
) -> None:
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "reg-test-run", "test-stage")
    invocations: list[dict[str, Any]] = []
    runner = _make_runner(invocations)

    dispatcher = Dispatcher(ROOT, repo, runner=runner, resolve_scanner=False)
    cap = resolve_worker_capability(
        ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
        bundle=dispatcher.roster.bundle,
    )
    assert cap is not None
    cap["requirement"] = "required"
    cap["parent_family"] = "codex_parent"

    endpoint = Endpoint("antigravity", "gemini-3.8-flash-high")
    with pytest.raises(DispatchError, match=r"parent registration unavailable \(ValueError:.*parent_family"):
        dispatcher._stage(
            directory,
            1,
            "work",
            "01-work",
            "primary",
            endpoint,
            _make_prompt(),
            None,
            read_only=False,
            worker_capability=cap,
        )
    assert len(invocations) == 0


def test_mismatched_endpoint_rejected(
    tmp_path: Path, clean_leaf_env: None, agy_bin: Path
) -> None:
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "reg-test-run", "test-stage")
    invocations: list[dict[str, Any]] = []
    runner = _make_runner(invocations)

    codex_mock = agy_bin / "codex"
    codex_mock.write_text(AGY_MOCK, encoding="utf-8")
    codex_mock.chmod(0o755)
    dispatcher = Dispatcher(
        ROOT, repo, runner=runner, resolve_scanner=False, codex_executable=str(codex_mock),
    )
    cap = resolve_worker_capability(
        ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
        bundle=dispatcher.roster.bundle,
    )
    assert cap is not None
    cap["requirement"] = "required"

    endpoint = Endpoint("codex", "implementation-testing")
    with pytest.raises(DispatchError, match=r"parent registration unavailable \(ValueError:.*provenance mismatch"):
        dispatcher._stage(
            directory,
            1,
            "work",
            "01-work",
            "primary",
            endpoint,
            _make_prompt(),
            None,
            read_only=False,
            worker_capability=cap,
        )
    assert len(invocations) == 0


def test_mismatched_accounting_mode_refuses(
    tmp_path: Path, clean_leaf_env: None, agy_bin: Path
) -> None:
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "reg-test-run", "test-stage")
    invocations: list[dict[str, Any]] = []
    runner = _make_runner(invocations)

    dispatcher = Dispatcher(ROOT, repo, runner=runner, resolve_scanner=False)
    dispatcher._stage_accounting_state = {"execution_mode": "gemini_flash_opus_sub"}

    cap = resolve_worker_capability(
        ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
        bundle=dispatcher.roster.bundle,
    )
    assert cap is not None
    cap["requirement"] = "required"
    cap["execution_mode"] = "gemini_flash_sub"

    endpoint = Endpoint("antigravity", "gemini-3.8-flash-high")
    with pytest.raises(DispatchError, match=r"parent registration unavailable \(ValueError:.*explicit execution mode.*authoritative accounting state"):
        dispatcher._stage(
            directory,
            1,
            "work",
            "01-work",
            "primary",
            endpoint,
            _make_prompt(),
            None,
            read_only=False,
            worker_capability=cap,
        )
    assert len(invocations) == 0


@pytest.mark.parametrize("required", [False, True])
def test_absent_fixture_respects_local_requirement(tmp_path, monkeypatch, clean_leaf_env, agy_bin, required):
    import shutil
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "reg-test-run", "test-stage")
    invocations = []
    dispatcher = Dispatcher(ROOT, repo, runner=_make_runner(invocations), resolve_scanner=False)
    cap = resolve_worker_capability(ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
                                    bundle=dispatcher.roster.bundle)
    cap["requirement"] = "required" if required else "optional"
    real_which = shutil.which
    monkeypatch.setattr(shutil, "which",
                        lambda name: None if name in {"agy", "antigravity"} else real_which(name))
    args = (directory, 1, "work", "01-work", "worker",
            Endpoint("antigravity", "gemini-3.8-flash-high"), _make_prompt(), None)
    if required:
        with pytest.raises(DispatchError, match="re-resolution not allowed"):
            dispatcher._stage(*args, read_only=True, worker_capability=cap)
        assert not invocations
    else:
        _, meta = dispatcher._stage(*args, read_only=True, worker_capability=cap)
        assert meta["worker_capability"]["allowed"] is False
        assert len(invocations) == 1
    receipt = json.loads((directory.path / "01-work.registration.json").read_bytes())
    assert receipt["register_entered"] is False
    assert receipt["registration_status"] == "refused_before_register"


@pytest.mark.parametrize("stage_kind", ["explicit", "ordinary"])
def test_f5_optional_stage_registration_failure_diagnostics_generic_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_leaf_env: None, agy_bin: Path, stage_kind: str
) -> None:
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", f"f5-{stage_kind}-run", "test-stage")
    invocations: list[dict[str, Any]] = []
    runner = _make_runner(invocations)

    dispatcher = Dispatcher(ROOT, repo, runner=runner, resolve_scanner=False)
    endpoint = Endpoint("antigravity", "gemini-3.8-flash-high")

    synthetic_secret = "synthetic-secret-token-xyz9876543210"
    synthetic_path = "/private/synthetic/tokens/sensitive-path.pem"
    synthetic_raw = f"{synthetic_secret}\n{synthetic_path}\nextra-padding-" + "X" * 250
    expected_detail = synthetic_raw.replace("\n", " ").strip()[:240]

    def failing_register(*args: Any, **kwargs: Any) -> Any:
        raise ValueError(synthetic_raw)

    monkeypatch.setattr(ParentLedger, "register", failing_register)

    if stage_kind == "explicit":
        cap = resolve_worker_capability(
            ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
            bundle=dispatcher.roster.bundle,
        )
        assert cap is not None
        cap["requirement"] = "optional"
        result, meta = dispatcher._stage(
            directory,
            1,
            "work",
            "01-work",
            "worker",
            endpoint,
            _make_prompt(),
            None,
            read_only=True,
            worker_capability=cap,
        )
    else:
        dispatcher._stage_accounting_state = {"execution_mode": "gemini_flash_sub"}
        result, meta = dispatcher._stage(
            directory,
            1,
            "work",
            "01-work",
            "worker",
            endpoint,
            _make_prompt(),
            None,
            read_only=True,
            worker_capability=None,
        )

    # 1. Runner launched exactly once without synthetic details in prompt/argv
    assert result.ok is True
    assert len(invocations) == 1
    inv_prompt = invocations[0].get("prompt", b"").decode("utf-8", errors="replace")
    assert synthetic_secret not in inv_prompt
    assert synthetic_path not in inv_prompt
    assert "parent registration unavailable (ValueError)" in inv_prompt
    assert all(synthetic_secret not in arg for arg in invocations[0]["argv"])

    # 2. On-disk prompt excludes synthetic details and retains generic reason
    prompt_file = directory.path / "01-work.prompt.md"
    assert prompt_file.exists()
    on_disk_prompt = prompt_file.read_text(encoding="utf-8")
    assert synthetic_secret not in on_disk_prompt
    assert synthetic_path not in on_disk_prompt
    assert "parent registration unavailable (ValueError)" in on_disk_prompt

    # 3. meta.worker_capability retains generic reason and excludes synthetic details
    assert meta["worker_capability"]["allowed"] is False
    assert meta["worker_capability"]["reason"] == "parent registration unavailable (ValueError)"
    assert synthetic_secret not in meta["worker_capability"]["reason"]
    assert synthetic_path not in meta["worker_capability"]["reason"]

    # 4. meta.json safe diagnostic contains bounded detail
    meta_path = directory.path / "01-work.meta.json"
    assert meta_path.exists()
    meta_json = json.loads(meta_path.read_text(encoding="utf-8"))
    assert "registration_observation" in meta_json
    reg_obs = meta_json["registration_observation"]
    assert "failure" in reg_obs
    failure = reg_obs["failure"]
    assert failure["category"] == "parent registration unavailable"
    assert failure["error_type"] == "ValueError"
    assert failure["detail"] == expected_detail
    assert len(failure["detail"]) <= 240
    assert "\n" not in failure["detail"]

    # 5. Registration artifact behavior: written ONLY for explicit cap
    registration_file = directory.path / "01-work.registration.json"
    if stage_kind == "explicit":
        assert registration_file.exists()
        reg_json = json.loads(registration_file.read_text(encoding="utf-8"))
        assert reg_json["failure"]["category"] == "parent registration unavailable"
        assert reg_json["failure"]["error_type"] == "ValueError"
        assert reg_json["failure"]["detail"] == expected_detail
    else:
        assert not registration_file.exists()


def test_f5_required_mode_registration_failure_raises_detailed_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clean_leaf_env: None, agy_bin: Path
) -> None:
    repo = repository.__wrapped__(tmp_path)
    directory = RunDirectory(tmp_path / "runs", "f5-req-test-run", "test-stage")
    invocations: list[dict[str, Any]] = []
    runner = _make_runner(invocations)

    dispatcher = Dispatcher(ROOT, repo, runner=runner, resolve_scanner=False)
    endpoint = Endpoint("antigravity", "gemini-3.8-flash-high")

    synthetic_secret = "synthetic-secret-token-req-12345"
    synthetic_path = "/private/synthetic/tokens/req-sensitive.pem"
    synthetic_raw = f"{synthetic_secret} {synthetic_path}"

    def failing_register(*args: Any, **kwargs: Any) -> Any:
        raise ValueError(synthetic_raw)

    monkeypatch.setattr(ParentLedger, "register", failing_register)

    cap = resolve_worker_capability(
        ROOT, "antigravity", "gemini-3.8-flash-high", "gemini_flash_sub",
        bundle=dispatcher.roster.bundle,
    )
    assert cap is not None
    cap["requirement"] = "required"

    with pytest.raises(DispatchError, match=rf"parent registration unavailable \(ValueError:.*{synthetic_secret}"):
        dispatcher._stage(
            directory,
            1,
            "work",
            "01-work",
            "worker",
            endpoint,
            _make_prompt(),
            None,
            read_only=True,
            worker_capability=cap,
        )

    assert len(invocations) == 0
