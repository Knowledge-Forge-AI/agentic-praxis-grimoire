"""Bind and drain workers around a V2 actor's complete launch preparation."""
from contextlib import contextmanager
import json
import os
from pathlib import Path


@contextmanager
def bound_workers(root, run_dir, workspace, parent_id, endpoint, authority, capability, argv, prefix, *, rtk=None):
    session = {"argv": argv, "stdout": b""}
    if not capability or not capability.get("allowed"):
        if capability and capability.get("requirement") == "required":
            raise RuntimeError("worker_unavailable: required worker capability absent")
        if endpoint is not None:
            from .runtime_models import apply_selection
            session["argv"] = apply_selection(argv, endpoint, root)
        yield session
        return
    from apgr_workers.ledger import ParentLedger
    from .worker_evidence import disposition
    state_dir = run_dir / "workers"
    ledger = ParentLedger(parent_id, state_dir)
    native = None
    parent_exit_observed = False
    keys = ("APGR_PARENT_ID", "APGR_WORKER_STATE_DIR", "APGR_WORKER_FACADE", "APGR_WORKERS_REQUIRED")
    prior = {key: os.environ.get(key) for key in keys}
    receipt = {"parent_id": parent_id, "status": "preparing", "uncertain_cleanup": True}
    receipt_path = run_dir / f"{prefix}.worker-custody.json"
    try:
        if endpoint.provider == "codex" and capability.get("parent_family") == "codex_parent":
            from apgr_workers.native_launch import prepare_native_binding, apply_native_binding, capability_with_native_binding, claim_fresh_launch
            native = prepare_native_binding(root, parent_id=parent_id, parent_profile=endpoint.profile,
                workspace=workspace, state_dir=state_dir, task_authority=authority,
                lifecycle_generation=parent_id, capability=capability)
            session["argv"] = apply_native_binding(argv, native, rtk=rtk)
            capability = capability_with_native_binding(capability, native, session["argv"])
        # Match V1: capability evidence binds native additions before parent
        # selection, while the fresh-launch record binds the actual selected argv.
        from .runtime_models import apply_selection
        session["argv"] = apply_selection(session["argv"], endpoint, root)
        if native is not None:
            claim_fresh_launch(native, argv=session["argv"], require_empty_ledger=True)
        policy_path = Path(os.environ["APGR_DISPATCH_WORKERS"])
        registered = ledger.initialize_parent(capability["parent_family"], workspace=workspace,
            task_authority=authority, policy_path=policy_path, worker_capability={
                **capability, "policy_source": str(policy_path), "source_root": str(root),
                "lifecycle_generation": parent_id, "parent_profile": endpoint.profile,
                "parent_provider": endpoint.provider})
        if registered["policy"]["policy_sha256"] != capability["policy_sha256"]:
            raise RuntimeError("worker_unavailable: policy identity mismatch")
        os.environ.update(APGR_PARENT_ID=parent_id, APGR_WORKER_STATE_DIR=str(state_dir),
                          APGR_WORKERS_REQUIRED="1" if capability.get("requirement") == "required" else "0")
        if endpoint.provider == "claude":
            os.environ["APGR_WORKER_FACADE"] = "1"
        else:
            os.environ.pop("APGR_WORKER_FACADE", None)
        receipt["status"] = "armed"
        receipt_path.write_text(json.dumps(receipt) + "\n")
        yield session
        parent_exit_observed = True
    finally:
        try:
            if ledger.data_path.exists():
                drain = ledger.drain_and_close(timeout_seconds=15.0, parent_exit_observed=parent_exit_observed)
                receipt.update(drain)
                receipt["worker_disposition"] = disposition(capability, json.loads(ledger.data_path.read_text()), session["stdout"])
                if native is not None:
                    from apgr_workers.native_launch import _update_launch_record
                    _update_launch_record(native, status="closed" if not drain.get("uncertain_cleanup") else "stopping", ledger_drain=drain)
                receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
                if drain.get("uncertain_cleanup"):
                    raise RuntimeError("worker_unavailable: worker cleanup uncertain")
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
