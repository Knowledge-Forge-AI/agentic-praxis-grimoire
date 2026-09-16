"""Read-only resume qualification for previously uncertain owned cleanup."""

import json
from pathlib import Path
from typing import Any

from .run import worker_parent_prefix


def verify_pending_cleanup(source: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    pending = state.get("worker_cleanup_pending")
    if not pending:
        return None
    try:
        artifact = pending["artifact"]
        if not isinstance(artifact, str) or Path(artifact).name != artifact:
            raise ValueError("invalid cleanup artifact")
        source = source.resolve()
        receipt_path = source / artifact
        if receipt_path.is_symlink():
            raise ValueError("cleanup artifact is not an owned regular file")
        receipt = json.loads(receipt_path.read_text())
        parent_id = receipt["parent_id"]
        run_prefixes = (str(state["run_id"]) + "--", worker_parent_prefix(state["run_id"]))
        if not isinstance(parent_id, str) or not parent_id.startswith(run_prefixes):
            raise ValueError("cleanup parent does not belong to the source run")
        # Optional worker imports remain confined to runs that actually used
        # the facility. Read an atomic snapshot without starting a provider,
        # registering a parent, or rewriting the historical run.
        from agent_workers.ledger import sanitize_parent_id

        ledger_path = source / "workers" / sanitize_parent_id(parent_id) / "ledger.json"
        workers_path = source / "workers"
        if workers_path.is_symlink() or workers_path.resolve() != workers_path:
            raise ValueError("owned worker ledger directory is not local")
        if not workers_path.is_dir():
            raise ValueError("owned cleanup ledger is unavailable")

        def verify_ledger(path: Path, expected_parent: str | None = None) -> str:
            if path.is_symlink() or path.resolve() != path or not path.is_file():
                raise ValueError("owned cleanup ledger is unavailable")
            ledger = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(ledger, dict):
                raise ValueError("owned worker ledger is incomplete")
            ledger_parent = ledger.get("parent_id")
            if (
                not isinstance(ledger_parent, str)
                or not ledger_parent.startswith(run_prefixes)
                or expected_parent is not None and ledger_parent != expected_parent
                or path.parent.name != sanitize_parent_id(ledger_parent)
            ):
                raise ValueError("owned worker parent identity is invalid")
            if ledger.get("status") != "closed":
                raise ValueError("owned worker parent has not closed")
            jobs = ledger.get("gemini_jobs")
            natives = ledger.get("native_agents")
            if not isinstance(jobs, dict) or not isinstance(natives, dict):
                raise ValueError("owned worker ledger is incomplete")
            if any(
                not isinstance(job, dict)
                or job.get("status") not in {"completed", "failed", "cancelled"}
                or job.get("cleanup_proven") is not True
                for job in jobs.values()
            ):
                raise ValueError("owned Gemini cleanup remains unproven")
            if any(
                not isinstance(child, dict) or child.get("status") != "closed"
                for child in natives.values()
            ):
                raise ValueError("owned native closure remains unproven")
            return ledger_parent

        verify_ledger(ledger_path, parent_id)
        ledger_paths = sorted(workers_path.glob("*/ledger.json"))
        if ledger_path not in ledger_paths:
            ledger_paths.append(ledger_path)
        for owned_path in ledger_paths:
            verify_ledger(owned_path)
        return {"parent_id": parent_id, "source_artifact": artifact, "cleanup_proven": True}
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        raise ValueError(f"source run still has unresolved worker custody: {error}") from error


def verify_retained_cleanup(source: Path, state: dict[str, Any]) -> None:
    """Validate recorded stage and auxiliary drains; no-worker history needs none."""
    # Keep the existing durable ledger reconciliation for a crashed parent.
    reconciled = verify_pending_cleanup(source, state)
    for receipt_path in source.glob("*.worker-drain.json"):
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            reconciled_receipt = bool(reconciled and reconciled["source_artifact"] == receipt_path.name)
            if not isinstance(receipt, dict) or (
                receipt.get("uncertain_cleanup") is not False and not reconciled_receipt
            ):
                raise ValueError("retained drain does not prove cleanup")
            prefix = receipt_path.name.removesuffix(".worker-drain.json")
            meta_path = source / f"{prefix}.meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                if not isinstance(meta, dict):
                    raise ValueError("stage metadata is not an object")
                recorded = meta.get("worker_drain")
                if recorded is not None and recorded != receipt:
                    raise ValueError("stage metadata and drain disagree")
        except (OSError, ValueError, TypeError) as error:
            raise ValueError(f"unresolved retained worker custody: {receipt_path.name}: {error}") from error
    for meta_path in source.glob("*.meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if not isinstance(meta, dict):
                raise ValueError("stage metadata is not an object")
            drain = meta.get("worker_drain")
            if drain is not None:
                receipt_path = meta_path.with_name(meta_path.name.removesuffix(".meta.json") + ".worker-drain.json")
                if not receipt_path.is_file():
                    raise ValueError("stage worker drain receipt is missing")
        except (OSError, ValueError, TypeError) as error:
            raise ValueError(f"unresolved retained worker custody: {meta_path.name}: {error}") from error
