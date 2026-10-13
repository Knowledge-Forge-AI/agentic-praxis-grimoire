"""APG166V-H-COMPLETE1 host mechanical helper contract.

The complete provider-free transaction is never run here: the coding sandbox
denies the loopback socket that the known-GOOD Go cancellation fixture needs.
The transaction and its readback are injected; preflight, runtime capture and
the three simulated providers are real.
"""
from __future__ import annotations

import json
import os
import subprocess
import zipfile
from pathlib import Path

import pytest

from testing.h_eval import host_mechanical as hm

ROOT = Path(__file__).resolve().parents[3]
PASSING = {"complete_records": 15, "initial_trees_equal": 15, "subject_pairs_unchanged": 15,
           "promotion_oracle_fixtures": {"fixture_pairs": 25}, "provider_invocations": 0,
           "provider_guard": {"sentinels_observed": 0}}


def _go_module(tmp_path, monkeypatch):
    """A synthetic module-cache input whose h1 values are the pinned go.sum."""
    directory = tmp_path / "gomodcache/cache/download/example.com/fixture/!mod/@v"
    directory.mkdir(parents=True)
    gomod = b"module example.com/fixture/Mod\n"
    source = b"package mod\n"
    prefix = "example.com/fixture/Mod@v1.0.0/"
    with zipfile.ZipFile(directory / "v1.0.0.zip", "w") as archive:
        archive.writestr(prefix + "go.mod", gomod)
        archive.writestr(prefix + "mod.go", source)
    (directory / "v1.0.0.mod").write_bytes(gomod)
    go_sum = tmp_path / "go.sum"
    go_sum.write_text(
        f"example.com/fixture/Mod v1.0.0 {hm._h1([(prefix + 'go.mod', gomod), (prefix + 'mod.go', source)])}\n"
        f"example.com/fixture/Mod v1.0.0/go.mod {hm._h1([('go.mod', gomod)])}\n")
    monkeypatch.setattr(hm, "GO_SUM_SOURCES", (str(go_sum),))
    return directory


@pytest.fixture
def layout(tmp_path, monkeypatch):
    parent = tmp_path / "exclusive"
    parent.mkdir(mode=0o700)
    output = tmp_path / "output"
    output.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    module = _go_module(tmp_path, monkeypatch)
    inputs = tmp_path / "host-cache-inputs.json"
    inputs.write_text(json.dumps([str(cache), str(module)]))
    return {"runtime": parent / "runtime", "output": output, "cache_inputs": inputs, "tmp": tmp_path,
            "module": module}


def _transaction(calls, summary=PASSING, accepted=True, error=None):
    def run_transaction(qualification_dir, manifest, *, root):
        calls.append((Path(qualification_dir), Path(manifest), Path(root)))
        target = Path(qualification_dir) / "final-b8-test" / "transaction"
        target.mkdir(parents=True)
        (target / "dry-run.json").write_text(json.dumps(summary))
        (target.parent / "summary.json").write_text(json.dumps(summary))
        custody = target / "records/scenario-12/special/recovery-subtree/recovery-custody"
        custody.mkdir(parents=True)
        (custody / "preparation.stderr").write_text("usage: apgr skills acquire\n")
        (custody / "mcp.stdin").write_text("{}\n")
        skill = target / "records/scenario-12/special/midturn-recovery/recovery"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# skill\n")
        (target / "records/scenario-15/subject/frontend/node_modules/react").mkdir(parents=True)
        (target / "records/scenario-15/subject/frontend/node_modules/react/package.json").write_text("{}")
        (target / "records/scenario-15/home").mkdir(parents=True)
        (target / "records/scenario-15/home/credential.json").write_text("{}")
        (target / "records/scenario-15/x_test.go").write_text("package x\n")
        (target / "records/scenario-15/link.json").symlink_to(target / "dry-run.json")
        if error is not None:
            raise error
        return {"output": str(target.parent), "transaction": str(target), "accepted": accepted,
                "gates": {}, "seal": {}, "summary": summary}
    return run_transaction


def _readback(summary=PASSING, valid=True):
    def readback(repo, transaction, output):
        return {"summary": summary, "package_seal_valid": valid, "readback_valid": valid, "errors": []}
    return readback


def _run(layout, transaction, monkeypatch, readback=None):
    if readback is not None:
        monkeypatch.setattr(hm, "readback", readback)
    return hm.run(ROOT, layout["runtime"], layout["output"], cache_inputs=layout["cache_inputs"],
                  transaction=transaction)


def _result(layout):
    return json.loads((layout["output"] / hm.RESULT_NAME).read_text())


def test_single_passing_transaction_reads_counts_from_readback(layout, monkeypatch):
    calls = []
    code, result = _run(layout, _transaction(calls, summary={**PASSING, "complete_records": 0}),
                        monkeypatch, _readback())
    assert code == 0 and result["status"] == "passed"
    assert len(calls) == 1 and result["transactions_started"] == 1 and result["retries"] == 0
    assert result["checks"] == hm.EXPECTED_CHECKS
    assert result["live_provider_starts"] == 0 and result["source_unchanged"] is True
    assert _result(layout) == json.loads(json.dumps(result))
    manifest = json.loads(Path(result["runtime"]["manifest_path"]).read_text())
    assert manifest["lifecycle"]["state"] == "sealed"
    fakes = result["runtime"]["fakes"]
    assert set(fakes) == {"claude", "codex", "antigravity"}
    assert len({item["path"] for item in fakes.values()}) == 3
    assert all(item["mode"] == "0o700" for item in fakes.values())
    refusal = subprocess.run([fakes["antigravity"]["path"], "exec"], capture_output=True)
    assert refusal.returncode == 97


def test_failed_transaction_retains_actual_counts_without_retry(layout, monkeypatch):
    calls = []
    partial = {**PASSING, "complete_records": 11}
    code, result = _run(layout, _transaction(calls, summary=partial, error=RuntimeError("loopback")),
                        monkeypatch)
    assert code == 1 and result["status"] == "failed"
    assert len(calls) == 1
    assert result["checks"]["scenario_records"] == 11
    assert "loopback" in result["failure"]
    assert Path(result["traceback"]).is_file()


@pytest.mark.parametrize("readback", [
    _readback(summary={**PASSING, "provider_guard": {"sentinels_observed": 1}}),
    _readback(valid=False),
])
def test_readback_mismatch_fails_with_observed_values(layout, monkeypatch, readback):
    calls = []
    code, result = _run(layout, _transaction(calls), monkeypatch, readback)
    assert code == 1 and result["status"] == "failed" and len(calls) == 1
    assert result["checks"] != hm.EXPECTED_CHECKS


def test_unaccepted_transaction_is_not_passed(layout, monkeypatch):
    code, result = _run(layout, _transaction([], accepted=False), monkeypatch, _readback())
    assert code == 1 and result["status"] == "failed"


def _refused(layout, monkeypatch, message):
    calls = []
    code, result = _run(layout, _transaction(calls), monkeypatch)
    assert code == 2 and result["status"] == "refused"
    assert message in result["refusal"]
    assert calls == []


def test_refuses_runtime_root_inside_source(layout, monkeypatch):
    layout["runtime"] = ROOT / "apg166v-absent-runtime-root"
    _refused(layout, monkeypatch, "parent must be an exclusive" if (ROOT.stat().st_mode & 0o022) else "must not contain")


def test_refuses_existing_runtime_root(layout, monkeypatch):
    layout["runtime"].mkdir(mode=0o700)
    _refused(layout, monkeypatch, "must not exist")


def test_refuses_relative_paths(layout, monkeypatch):
    layout["runtime"] = Path("relative-runtime")
    _refused(layout, monkeypatch, "must be absolute")


def test_refuses_unavailable_loopback(layout, monkeypatch):
    monkeypatch.setattr(hm, "_loopback", lambda: {"127.0.0.1": False, "::1": False})
    _refused(layout, monkeypatch, "loopback")


def test_refuses_missing_local_command(layout, monkeypatch):
    real = hm.shutil.which
    monkeypatch.setattr(hm.shutil, "which", lambda name: None if name == "sqlite3" else real(name))
    _refused(layout, monkeypatch, "sqlite3")


def test_refuses_cache_inside_source_and_existing_result(layout, monkeypatch):
    layout["cache_inputs"].write_text(json.dumps([str(ROOT / "testing")]))
    _refused(layout, monkeypatch, "cache inputs")
    layout["cache_inputs"].write_text(json.dumps([str(layout["tmp"] / "cache")]))
    (layout["output"] / hm.RESULT_NAME).write_text("{}")
    _refused_existing = hm.run(ROOT, layout["runtime"], layout["output"],
                               cache_inputs=layout["cache_inputs"], transaction=_transaction([]))
    assert _refused_existing[0] == 2 and "already exists" in _refused_existing[1]["refusal"]
    assert (layout["output"] / hm.RESULT_NAME).read_text() == "{}"


def test_refuses_missing_go_module_input(layout, monkeypatch):
    layout["cache_inputs"].write_text(json.dumps([str(layout["tmp"] / "cache")]))
    _refused(layout, monkeypatch, "exactly one Go module input")


def test_refuses_go_module_input_that_differs_from_go_sum(layout, monkeypatch):
    (layout["module"] / "v1.0.0.mod").write_bytes(b"module changed\n")
    _refused(layout, monkeypatch, "does not match frozen go.sum")


def test_go_module_inputs_are_recorded_with_verified_h1(layout, monkeypatch):
    code, result = _run(layout, _transaction([]), monkeypatch, _readback())
    assert code == 0
    (module,) = result["host"]["go_module_inputs"]
    assert module["module"] == "example.com/fixture/Mod" and module["version"] == "v1.0.0"
    assert module["directory"] == str(layout["module"])
    assert {Path(item["path"]).name for item in module["files"]} == {"v1.0.0.zip", "v1.0.0.mod"}


def _assert_collected(layout, result):
    diagnostics = layout["output"] / hm.DIAGNOSTICS
    collection = json.loads((diagnostics / "COLLECTION.json").read_text())
    copied = set(collection["files"])
    assert {"runtime-manifest.json", "qualification/summary.json", "qualification/transaction/dry-run.json",
            "qualification/transaction/records/scenario-12/special/recovery-subtree/recovery-custody/preparation.stderr",
            "qualification/transaction/records/scenario-12/special/recovery-subtree/recovery-custody/mcp.stdin",
            "qualification/transaction/records/scenario-12/special/midturn-recovery/recovery/SKILL.md"} <= copied
    assert not any("node_modules" in name or "/home/" in name or name.endswith((".go", "link.json"))
                   for name in copied)
    omitted = {Path(item["path"]).name for item in collection["omissions"]}
    assert {"node_modules", "home", "x_test.go", "link.json"} <= omitted
    for name, item in collection["files"].items():
        data = (diagnostics / name).read_bytes()
        assert item["bytes"] == len(data)
        assert (os.stat(diagnostics / name).st_mode & 0o777) == 0o600
    index = json.loads((layout["output"] / "DIAGNOSTIC-INDEX.json").read_text())
    assert index["pointers"]["collection"] == str(diagnostics / "COLLECTION.json")
    assert result["diagnostics"]["selected_count"] == len(copied)
    assert result["collection_issues"] == []


def test_diagnostics_are_collected_on_passing_transaction(layout, monkeypatch):
    code, result = _run(layout, _transaction([]), monkeypatch, _readback())
    assert code == 0 and result["status"] == "passed"
    _assert_collected(layout, result)


def test_diagnostics_are_collected_on_failed_transaction(layout, monkeypatch):
    calls = []
    code, result = _run(layout, _transaction(calls, error=RuntimeError("boom")), monkeypatch)
    assert code == 1 and result["status"] == "failed" and len(calls) == 1
    _assert_collected(layout, result)
    assert json.loads((layout["output"] / "DIAGNOSTIC-INDEX.json").read_text())["pointers"]["traceback"]


def test_collection_failure_is_an_issue_not_a_status_change(layout, monkeypatch):
    def broken(*_args):
        raise OSError("disk full")
    monkeypatch.setattr(hm, "collect_diagnostics", broken)
    code, result = _run(layout, _transaction([]), monkeypatch, _readback())
    assert code == 0 and result["status"] == "passed"
    assert result["collection_issues"] == ["diagnostic collection failed: OSError: disk full"]
    written = json.loads((layout["output"] / hm.RESULT_NAME).read_text())
    assert written["collection_issues"] == result["collection_issues"]


def test_refuses_corrupt_go_module_zip(layout, monkeypatch):
    (layout["module"] / "v1.0.0.zip").write_bytes(b"not a zip")
    _refused(layout, monkeypatch, "Go module input verification failed: BadZipFile")
