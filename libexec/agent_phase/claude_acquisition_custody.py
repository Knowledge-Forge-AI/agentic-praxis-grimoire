"""Before/after custody for one consumed internal acquisition attempt."""
from pathlib import Path

from .claude_recovery_authority import file_identity, physical, verify
from .claude_acquisition_handoff import decode, identity, KEYS
from .transmission import direct_bytes


def snapshot(path, value, plan_path, server):
    files = {"handoff": path, "plan": plan_path, "config": value["config"]["path"],
             "server": server, "binary": value["binary"]["path"]}
    verify(Path(path).parent, value["recovery_authority"])
    return {"scope": value["scope"], "recovery": value["recovery_authority"],
            "files": {key: {"path": str(p), **file_identity(p)} for key, p in files.items()}}


def capture_prepared(prepared):
    plan = prepared["record"]
    name = plan.get("acquisition", {}).get("wrapper_handoff")
    if name is None:
        return None
    path = Path(name)
    value = decode(direct_bytes(path))
    if value["scope"] != {k: plan[k] for k in KEYS}:
        raise ValueError("acquisition custody scope mismatch")
    return snapshot(path, value, prepared["path"], plan["acquisition"]["config"])


def retain_before(path, value, plan_path, server):
    from .context_adapter import _write_new
    path = Path(path)
    marker = Path(str(path) + ".consumed")
    if direct_bytes(marker) != identity(direct_bytes(path))["sha256"].encode():
        raise ValueError("consumed marker mismatch")
    _write_new(Path(str(path) + ".custody-before.json"),
               {**snapshot(path, value, plan_path, server), "marker": file_identity(marker)})


def verify_after(prepared, expected):
    """Called after child termination; no repair, retry or mutable receipt."""
    from .context_adapter import _write_new
    if expected is None:
        return None
    path = Path(prepared["record"]["acquisition"]["wrapper_handoff"])
    marker = Path(str(path) + ".consumed")
    def observe(operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except (OSError, ValueError) as error:
            return {"unavailable": type(error).__name__}
    # Observe only originally authorized paths, even if child-side bytes drift.
    observed = {"scope": {k: prepared["record"].get(k) for k in KEYS},
                "files": {key: observe(file_identity, row["path"]) for key, row in expected["files"].items()},
                "marker": observe(file_identity, marker),
                "recovery_root": observe(physical, expected["recovery"]["path"], directory=True),
                "recovery_files": {name: observe(file_identity, path.parent / name)
                                   for name in expected["recovery"]["files"]}}
    try:
        before = decode(direct_bytes(Path(str(path) + ".custody-before.json")))
        if ({k: v for k, v in before.items() if k != "marker"} != expected
                or observed["files"] != {key: {k: v for k, v in row.items() if k != "path"}
                                         for key, row in expected["files"].items()}):
            raise ValueError("post-run acquisition authority drift")
        after = capture_prepared(prepared)
        if after != expected:
            raise ValueError("post-run acquisition authority drift")
        if (observed["marker"] != before["marker"]
                or direct_bytes(marker) != identity(direct_bytes(path))["sha256"].encode()):
            raise ValueError("post-run consumed marker drift")
    except (OSError, ValueError) as error:
        _write_new(Path(str(path) + ".custody-after.json"),
                   {"status": "invalid", "observed": observed, "error_type": type(error).__name__})
        raise
    receipt = {**after, "marker": observed["marker"]}
    _write_new(Path(str(path) + ".custody-after.json"), {"status": "valid", "observed": observed, **receipt})
    return {"before": before, "after": receipt}
