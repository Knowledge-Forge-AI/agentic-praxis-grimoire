"""Drain optional owned children before final stage observations."""

from __future__ import annotations

import json
from typing import Any

from .stage_delta import _append_stage_observation_limitation


class WorkerCustody:
    """One idempotent drain shared by success, exception and finally paths."""

    def __init__(self, ledger: Any, directory: Any, prefix: str, state: dict | None):
        self.ledger = ledger
        self.directory = directory
        self.prefix = prefix
        self.state = state
        self.summary: dict[str, Any] | None = None
        self._armed = False

    @property
    def pending_artifact(self) -> str:
        return f"{self.prefix}.worker-drain.json"

    def _provisional_receipt(self) -> dict[str, Any]:
        return {
            "parent_id": getattr(self.ledger, "parent_id", None),
            "status": "armed",
            "uncertain_cleanup": True,
        }

    def arm(self) -> None:
        """Persist custody before an admitted provider can launch a child."""
        if self.ledger is None or self.state is None:
            return
        if self._armed:
            return
        pending = {
            "artifact": self.pending_artifact,
            "status": "incomplete",
        }
        current = self.state.get("worker_cleanup_pending")
        if (
            current is not None
            and (
                not isinstance(current, dict)
                or current.get("artifact") != pending["artifact"]
            )
        ):
            raise RuntimeError(
                "another stage owns the pending worker cleanup marker"
            )
        # The receipt carries the parent identity needed for post-crash
        # recovery. Write it first; only then publish the state marker that
        # allows provider execution to begin.
        self.directory.write_json(
            self.pending_artifact, self._provisional_receipt()
        )
        self.state["worker_cleanup_pending"] = pending
        self.directory.write_json("state.json", self.state)
        self._armed = True

    def drain(self) -> dict[str, Any] | None:
        if self.ledger is None or self.summary is not None:
            return self.summary
        pending = {
            "artifact": self.pending_artifact,
            "status": "incomplete",
        }
        if self.state is not None:
            current = self.state.get("worker_cleanup_pending")
            if current is None or (
                isinstance(current, dict)
                and current.get("artifact") == pending["artifact"]
            ):
                self.state["worker_cleanup_pending"] = pending
        receipt_path = self.directory.path / self.pending_artifact
        if not receipt_path.exists():
            self.directory.write_json(
                self.pending_artifact, self._provisional_receipt()
            )
        interruption: BaseException | None = None
        try:
            self.summary = self.ledger.drain_and_close(timeout_seconds=15.0)
            if not isinstance(self.summary, dict) or type(self.summary.get("uncertain_cleanup")) is not bool:
                raise ValueError("worker drain returned no cleanup decision")
        except BaseException as error:
            self.summary = {
                "parent_id": getattr(self.ledger, "parent_id", None),
                "uncertain_cleanup": True,
                "status": "stopping",
                "error": type(error).__name__,
            }
            if not isinstance(error, Exception):
                interruption = error
        if not self.summary.get("uncertain_cleanup") and self.state is not None:
            current = self.state.get("worker_cleanup_pending")
            if (
                isinstance(current, dict)
                and current.get("artifact") == self.pending_artifact
            ):
                self.state.pop("worker_cleanup_pending", None)
        self.directory.write_json(f"{self.prefix}.worker-drain.json", self.summary)
        meta_path = self.directory.path / f"{self.prefix}.meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["worker_drain"] = self.summary
                self.directory.write_json(f"{self.prefix}.meta.json", meta)
            except (OSError, ValueError, TypeError):
                pass
        if interruption is not None:
            raise interruption
        return self.summary

    def adopt_if_present(self, ledger: Any) -> None:
        """Retain a registration that may have completed before an error."""
        try:
            exists = bool(ledger.get_status().get("status"))
        except Exception:
            exists = True
        if exists:
            self.ledger = ledger

    def close_boundary(self, boundary: Any, **kwargs: Any) -> None:
        summary = self.drain()
        if boundary is None:
            return
        if summary and summary.get("uncertain_cleanup"):
            # No final tree/index capture while an owned child may mutate it.
            _append_stage_observation_limitation(
                boundary.state,
                boundary.stage_name,
                {
                    "kind": "worker_cleanup_pending",
                    "artifact": self.pending_artifact,
                },
            )
            return
        if boundary.state.get("worker_cleanup_pending"):
            # A marker belonging to another stage remains a global capture
            # fence even when this custody instance drained cleanly.
            _append_stage_observation_limitation(
                boundary.state,
                boundary.stage_name,
                {
                    "kind": "worker_cleanup_pending",
                    "artifact": boundary.state["worker_cleanup_pending"].get(
                        "artifact", self.pending_artifact
                    )
                    if isinstance(boundary.state["worker_cleanup_pending"], dict)
                    else self.pending_artifact,
                },
            )
            return
        boundary.close(**kwargs)
