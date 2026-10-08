"""Atomic, bounded phase canary budget management.

Enforces:
- Canonical budget path under normal provider HOME (not caller resettable):
  Documents/agent/outbox/agentic-praxis-grimoire_dev/APG166S-R1/canary-budget.json
- Stable phase and case keys
- Atomic flock, fsync, and rename reservations before provider invocation
- Maximum 2 attempts per case
- In-flight and duplicate refusal
- Interruption consumes an attempt; reconciliation occurs only when process group is proven gone
- Second attempt requires predecessor terminal disposition, predecessor proven cleanup, and a changed cause
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import pwd
import re
import secrets
import stat
import subprocess
import time
from pathlib import Path
from typing import Any, Iterator

SCHEMA = "apgr.canary-budget/v1"
DEFAULT_PHASE = "APG166S-R1"
SONNET_PHASE = "APG166ZQ"
ALLOWED_PHASES = frozenset({DEFAULT_PHASE, SONNET_PHASE})

LEGACY_SOURCE_PERMIT = (SONNET_PHASE, "gemini-sonnet", 1)
LEGACY_CLASSIFICATION = "legacy_no_worker_admission_parent_cleanup_proven"
LEGACY_EVALUATE_APPLY_REFUSED = "legacy evaluation is read-only; apply is not accepted"
PINNED_CANARY_SHA256 = "8565bcbb8b7b0d7c70edfeee8e6d11617e045b89380e92efa8ba7aad9e2f0c2a"
PINNED_AUTHORITY_SHA256 = "efb61da9401ed67f10ff76bcbd5beaeac5c11b51950017b866b90b3b26e3ebca"
LEGACY_AUTHORITY_SCHEMA = "apg166zx-legacy-gemini-custody-authority-v1"
LEGACY_APPROVAL_SCHEMA = "apgr.legacy-custody-application-approval/v1"
LEGACY_ENTRY_KEYS = frozenset({
    "attempt", "status", "pid", "pgid", "process_start_identity",
    "cause", "created_at", "updated_at", "cleanup_proven", "details",
})
LEGACY_DETAILS_KEYS = frozenset({
    "receipt", "source_identity", "bundle_sha256", "parent_cleanup", "worker_drain",
})
LEGACY_FORBIDDEN_ACTIONS = [
    "reset_budget",
    "new_campaign_to_bypass_attempt_limit",
    "forge_worker_drain",
    "forge_receipt_sha256",
    "forge_classification_inputs",
    "rewrite_historical_canary",
    "launch_gemini_attempt_2_in_APG166ZX",
]

LEGACY_OPERATION = "legacy_evidence_reconciliation_v1"
LEGACY_NEWER_KEYS = frozenset({"classification_inputs", "cleanup_classification", "outcome_layers",
                               "provider_invocations", "parent_identity", "receipt_sha256",
                               "worker_drain", "cleanup_reconciliation", "registration_observation"})
LEGACY_EXPECTED_FACTS = {
    "provider_stage_ok": True, "parent_process_cleanup_proven": True,
    "parent_verified_absence": True, "worker_registration_failed_before_admission": True,
    "worker_admissions": 0, "worker_result_records": 0, "native_admissions": 0,
    "sonnet_child_admitted": False, "maintained_worker_drain_record_present": False,
}

LEGACY_CASES = frozenset({
    "claude-gemini",
    "claude-luna",
    "codex-gemini",
    "codex-luna",
})

SONNET_CASES = frozenset({
    "claude-sonnet-native",
    "claude-sonnet-native-reuse",
    "codex-sonnet",
    "gemini-sonnet",
})

ALL_CASES = LEGACY_CASES | SONNET_CASES


class CanaryBudgetError(Exception):
    """Base error for canary budget operations."""


class BudgetExhaustedError(CanaryBudgetError):
    """Raised when the 2-attempt budget for a case is exhausted."""


class InFlightCanaryError(CanaryBudgetError):
    """Raised when an attempt is already active or in-flight for a case."""


class PredecessorCleanupError(CanaryBudgetError):
    """Raised when predecessor cleanup is not proven before second attempt."""


class UnchangedCauseError(CanaryBudgetError):
    """Raised when attempt 2 is requested without a changed remediation cause."""


def canonical_budget_path(home: Path | None = None, phase: str = DEFAULT_PHASE) -> Path:
    """Return canonical phase budget path derived from normal provider HOME.

    The relative path is fixed to prevent caller tampering or budget bypass:
    Documents/agent/outbox/agentic-praxis-grimoire_dev/<phase>/canary-budget.json
    """
    if phase not in ALLOWED_PHASES:
        raise CanaryBudgetError("phase budget identity cannot be changed")
    if home is None:
        base = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    else:
        base = Path(home).resolve()
    return base / "Documents" / "agent" / "outbox" / "agentic-praxis-grimoire_dev" / phase / "canary-budget.json"


def process_group_is_present(pgid: int | None) -> bool:
    """Return true unless the kernel proves that a process group is absent."""
    if not isinstance(pgid, int) or pgid <= 0:
        return True
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


class CanaryBudget:
    """Atomic, process-safe manager for phase canary attempt reservations."""

    def __init__(self, home: Path | None = None, phase: str = DEFAULT_PHASE) -> None:
        self.phase = phase
        self.path = canonical_budget_path(home=home, phase=phase)
        self.lock_path = self.path.parent / (self.path.name + ".lock")

    @contextlib.contextmanager
    def _locked(self) -> Iterator[dict[str, Any]]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = os.open(os.fspath(self.lock_path), os.O_RDWR | os.O_CREAT, 0o600)
        try:
            try:
                os.fchmod(lock_fd, 0o600)
            except OSError:
                pass
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            data = self._read()
            self._reconcile(data)
            try:
                yield data
            finally:
                self._write(data)
        finally:
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(lock_fd)

    def _read(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {
                "schema": SCHEMA,
                "phase": self.phase,
                "cases": {},
            }
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise CanaryBudgetError(f"budget file is not an object: {self.path}")
            if data.get("schema") != SCHEMA or data.get("phase") != self.phase or not isinstance(data.get("cases"), dict):
                raise CanaryBudgetError("invalid budget identity or cases; refusing reset")
            return data
        except (json.JSONDecodeError, OSError) as err:
            raise CanaryBudgetError(f"unreadable canary budget at {self.path}: {err}") from err

    def _write(self, data: dict[str, Any]) -> None:
        tmp_path = self.path.with_name(f"{self.path.name}.tmp.{secrets.token_hex(8)}")
        content = (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")
        fd = os.open(os.fspath(tmp_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(os.dup(fd), "wb") as stream:
                stream.write(content)
                stream.flush()
            os.fsync(fd)
        finally:
            os.close(fd)
        tmp_path.replace(self.path)
        directory_fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _reconcile(self, data: dict[str, Any]) -> None:
        """Reconcile in-flight attempts whose process group is proven gone.

        Interruption consumes the attempt; it remains recorded in the budget.
        """
        cases = data.get("cases", {})
        now = time.time()
        for case_name, case_data in cases.items():
            attempts = case_data.get("attempts", [])
            for att in attempts:
                if att.get("status") in {"reserved", "in_flight"}:
                    pgid = att.get("pgid")
                    if not process_group_is_present(pgid):
                        att["status"] = "interrupted"
                        att["cleanup_proven"] = False
                        att["reconciled_at"] = now
                        att["interrupted_reason"] = "process_group_proven_absent"

    def reserve(self, case: str, *, cause: str | None = None) -> dict[str, Any]:
        """Atomically reserve an attempt for a canary case.

        Enforces:
        - 2 attempts max per case
        - In-flight duplicate refusal
        - Attempt 2 requires predecessor disposition, proven cleanup, and changed cause
        """
        if case not in ALL_CASES:
            raise CanaryBudgetError("unknown canary case")
        if self.phase == DEFAULT_PHASE and case in SONNET_CASES:
            raise CanaryBudgetError(f"case '{case}' requires Sonnet budget phase ('{SONNET_PHASE}')")
        if self.phase == SONNET_PHASE and case in LEGACY_CASES:
            raise CanaryBudgetError(f"case '{case}' requires legacy budget phase ('{DEFAULT_PHASE}')")
        with self._locked() as data:
            cases = data.setdefault("cases", {})
            case_data = cases.setdefault(case, {"attempts": []})
            attempts = case_data.setdefault("attempts", [])

            # Check if any attempt is currently in-flight
            for att in attempts:
                if att.get("status") in {"reserved", "in_flight"}:
                    pgid = att.get("pgid")
                    if process_group_is_present(pgid):
                        raise InFlightCanaryError(
                            f"Case '{case}' already has active in-flight attempt {att.get('attempt')} (pgid {pgid})"
                        )

            # Check maximum 2 attempts limit
            if len(attempts) >= 2:
                raise BudgetExhaustedError(
                    f"Case '{case}' budget exhausted (maximum 2 attempts allowed; {len(attempts)} recorded)"
                )

            # Rules for attempt 2
            if len(attempts) == 1:
                predecessor = attempts[0]
                pred_status = predecessor.get("status")
                if pred_status in {"reserved", "in_flight"}:
                    raise InFlightCanaryError(
                        f"Case '{case}' predecessor attempt 1 is still in-flight"
                    )
                if not predecessor.get("cleanup_proven"):
                    raise PredecessorCleanupError(
                        f"Case '{case}' second attempt refused: predecessor attempt 1 cleanup not proven (status: {pred_status})"
                    )
                pred_cause = predecessor.get("cause")
                if not cause or cause == pred_cause:
                    raise UnchangedCauseError(
                        f"Case '{case}' second attempt refused: requires changed remediation cause (predecessor: {pred_cause!r}, got: {cause!r})"
                    )

            attempt_num = len(attempts) + 1
            now = time.time()
            entry = {
                "attempt": attempt_num,
                "status": "reserved",
                "pid": os.getpid(),
                "pgid": os.getpgrp(),
                "process_start_identity": subprocess.run(
                    ["ps", "-p", str(os.getpid()), "-o", "lstart="],
                    capture_output=True, text=True, check=True,
                ).stdout.strip(),
                "cause": cause or "initial_run",
                "created_at": now,
                "updated_at": now,
                "cleanup_proven": False,
            }
            attempts.append(entry)
            return dict(entry)

    def record_disposition(
        self,
        case: str,
        attempt: int,
        *,
        status: str,
        cleanup_proven: bool,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Atomically record the terminal disposition of a reserved attempt."""
        with self._locked() as data:
            cases = data.get("cases", {})
            if case not in cases:
                raise CanaryBudgetError(f"Case '{case}' not found in budget")
            attempts = cases[case].get("attempts", [])
            matching = [a for a in attempts if a.get("attempt") == attempt]
            if not matching:
                raise CanaryBudgetError(f"Attempt {attempt} for case '{case}' not found in budget")
            entry = matching[0]
            entry["status"] = status
            entry["cleanup_proven"] = bool(cleanup_proven)
            entry["updated_at"] = time.time()
            if details:
                entry["details"] = details
            return dict(entry)

    def get_case(self, case: str) -> dict[str, Any]:
        """Return a copy of the budget entry for a case."""
        with self._locked() as data:
            return dict(data.get("cases", {}).get(case, {"attempts": []}))

    def reconcile_attempt_cleanup(self, case: str, attempt: int, *, receipt_path: Path) -> dict:
        """Correct one terminal observation without reconciling or rewriting on refusal."""
        try:
            original = _stable_bytes(self.path)
            data = json.loads(original)
            if data.get("schema") != SCHEMA or data.get("phase") != self.phase:
                raise CanaryBudgetError("invalid budget identity")
            matches = [a for a in data["cases"][case]["attempts"] if a.get("attempt") == attempt]
            if len(matches) != 1:
                raise CanaryBudgetError("attempt is not unique")
            entry = matches[0]
            decision = evaluate_cleanup_reconciliation(entry, receipt_path, case=case, phase=self.phase)
            if not decision["ok"]:
                raise CanaryBudgetError("cleanup reconciliation refused: " + ", ".join(decision["missing"]))
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise CanaryBudgetError("unreadable reconciliation evidence") from error
        # Unlike _locked, this path never runs _reconcile or writes in finally.
        fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            if _stable_bytes(self.path) != original:
                raise CanaryBudgetError("budget changed during evidence evaluation")
            again = evaluate_cleanup_reconciliation(entry, receipt_path, case=case, phase=self.phase)
            if again != decision:
                raise CanaryBudgetError("evidence changed during evaluation")
            entry["cleanup_reconciliation"] = {
                "operation": "evidence_reconciliation_v1", "at": time.time(),
                "original_cleanup_proven": False, "original_status": entry["status"],
                "receipt_sha256": decision["receipt_sha256"],
                "classification": decision["classification"],
                "artifact_digests": decision["artifact_digests"],
                "raw_budget_sha256_before": hashlib.sha256(original).hexdigest(),
                "reconciler_source_identity": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            }
            entry["cleanup_proven"] = True
            self._write(data)
            return dict(entry)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


    def evaluate_legacy_attempt_cleanup(self, case: str, attempt: int, **evidence) -> dict:
        """Evaluate pinned legacy evidence without opening a lock or writing."""
        if "apply" in evidence:
            raise CanaryBudgetError(LEGACY_EVALUATE_APPLY_REFUSED)
        return self.reconcile_legacy_attempt_cleanup(case, attempt, **evidence, apply=False)

    def reconcile_legacy_attempt_cleanup(
        self, case: str, attempt: int, *, canary_path: Path,
        authority_path: Path, authority_sha256: str,
        approval_path: Path | None = None, approval_sha256: str | None = None,
        apply: bool = False,
    ) -> dict:
        """Reconcile only the pinned old attempt; current reconciliation is separate."""
        evidence = {"canary_path": canary_path, "authority_path": authority_path,
                        "authority_sha256": authority_sha256, "approval_path": approval_path,
                        "approval_sha256": approval_sha256, "case": case, "attempt": attempt,
                        "phase": self.phase}
        try:
            original = _stable_bytes(self.path)
            data, entry, decision = _legacy_budget_decision(original, **evidence)
            if apply and approval_path is None:
                raise ValueError("application approval required")
            if not apply or decision["already_reconciled"]:
                return decision
            # Deliberately avoid _locked: no automatic reconciliation/finally write.
            fd = os.open(self.lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                if _stable_bytes(self.path) != original:
                    raise ValueError("budget changed during evidence evaluation")
                _, _, again = _legacy_budget_decision(original, **evidence)
                if again != decision:
                    raise ValueError("evidence changed during evaluation")
                entry["cleanup_reconciliation"] = {
                    "operation": LEGACY_OPERATION, "at": time.time(),
                    "original_cleanup_proven": False, "original_status": entry["status"],
                    "original_attempt_sha256": decision["original_attempt_sha256"],
                    "raw_budget_sha256_before": hashlib.sha256(original).hexdigest(),
                    "classification": LEGACY_CLASSIFICATION,
                    "canary_sha256": decision["canary_sha256"],
                    "authority_sha256": decision["authority_sha256"],
                    "approval_sha256": decision["approval_sha256"],
                    "recomputed_historical_facts": decision["recomputed_facts"],
                    "reconciler_source_identity": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                }
                entry["cleanup_proven"] = True
                self._write(data)
                return {**decision, "status": "reconciled"}
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise CanaryBudgetError("legacy reconciliation refused: " + str(error)[:160]) from error


STAGE_REGISTRATION_SCHEMA = "apgr.stage-worker-registration/v1"


def _stable_bytes(path: Path) -> bytes:
    """Read a bounded direct regular evidence file with entry/descriptor stability."""
    path = Path(path).absolute()
    if path.resolve() != path:
        raise ValueError("indirect evidence path")
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > 32 * 1024 * 1024:
        raise ValueError("invalid evidence file")

    def identity(s):
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if identity(before) != identity(opened):
            raise ValueError("evidence entry changed")
        with os.fdopen(os.dup(fd), "rb") as stream:
            raw = stream.read(32 * 1024 * 1024 + 1)
        if len(raw) != opened.st_size or identity(opened) != identity(os.fstat(fd)) or identity(opened) != identity(path.lstat()):
            raise ValueError("evidence changed during read")
        return raw
    finally:
        os.close(fd)


def cleanup_inputs(record: dict, run_dir: Path) -> dict:
    """Snapshot maintained stage evidence before terminal budget disposition."""
    inputs = {"provider_invocations": record.get("provider_invocations"),
              "actual_argv": record.get("actual_argv"), "run_dir": str(run_dir.resolve()),
              "parent_id": record.get("parent_id"), "artifact_digests": {}}
    names = ["01-work.registration.json", "01-work.meta.json", "01-work.worker-drain.json",
             "01-work.provider-launch.json"]
    parent = inputs["parent_id"]
    if isinstance(parent, str) and parent and Path(parent).name == parent:
        names.append(f"workers/{parent}/ledger.json")
    for name in names:
        try:
            inputs["artifact_digests"][name] = hashlib.sha256(_stable_bytes(run_dir / name)).hexdigest()
        except (OSError, ValueError):
            pass  # Missing evidence stays missing; absence is never a release proof.
    return inputs


def classify_cleanup(record: dict, run_dir: Path) -> dict:
    """Separate proven drain/no-provider admission from uncertain custody."""
    decision = {"classification": "uncertain", "cleanup_proven": False, "missing": [], "evidence": {}}
    inputs = record.get("classification_inputs")
    if not isinstance(inputs, dict):
        decision["missing"] = ["budget_bound_classification_inputs", "01-work.worker-drain.json", "affirmative_no_admission_record"]
        return decision
    try:
        run_dir = Path(run_dir)
        if str(run_dir.resolve()) != inputs.get("run_dir"):
            raise ValueError("run_dir binding")
        if inputs.get("parent_id") != record.get("parent_id"):
            raise ValueError("parent binding")
        if any(inputs.get(k) != record.get(k) for k in ("provider_invocations", "actual_argv")):
            raise ValueError("invocation binding")
        artifacts = inputs.get("artifact_digests")
        if not isinstance(artifacts, dict) or not artifacts:
            raise ValueError("artifact digests")
        loaded = {}
        parent_id = record.get("parent_id")
        allowed = {"01-work.registration.json", "01-work.meta.json", "01-work.worker-drain.json",
                   "01-work.provider-launch.json", f"workers/{parent_id}/ledger.json"}
        for name, digest in artifacts.items():
            if name not in allowed:
                raise ValueError("unexpected evidence path")
            raw = _stable_bytes(run_dir / name)
            if hashlib.sha256(raw).hexdigest() != digest:
                raise ValueError("artifact digest mismatch")
            loaded[name] = json.loads(raw)
        reg = loaded.get("01-work.registration.json") or {}
        registration_bound = (reg.get("schema") == STAGE_REGISTRATION_SCHEMA
            and reg.get("parent_id") == parent_id and reg.get("prefix") == "01-work"
            and reg.get("stage") == "work" and reg.get("index") == 1
            and isinstance(reg.get("run_id"), str)
            and reg.get("lifecycle_generation") == f"{reg.get('run_id')}:work:1"
            and reg.get("complete") is True)
        if (registration_bound and reg.get("registration_status") == "refused_before_register"
            and reg.get("register_entered") is False and reg.get("provider_entered") is False
            and reg.get("custody_status") == "not_acquired" and reg.get("process_state") == "not_started"
            and type(inputs.get("provider_invocations")) is int and inputs["provider_invocations"] == 0
            and inputs.get("actual_argv") == [] and not record.get("admission")
            and not record.get("native_admission") and not record.get("worker_results")
            and record.get("error_code") == "worker_unavailable"):
            decision.update(classification="proven_no_child_before_provider", cleanup_proven=True,
                            evidence={"artifact_digests": artifacts})
            return decision
        meta = loaded.get("01-work.meta.json") or {}
        drain = loaded.get("01-work.worker-drain.json") or {}
        ledger = loaded.get(f"workers/{parent_id}/ledger.json") or {}
        cleanup = record.get("parent_cleanup") or {}
        parent_proven = (cleanup == meta.get("cleanup")
            and all(cleanup.get(k) is True for k in ("cleanup_proven", "outer_group_absent",
                "nested_groups_absent", "verified_absence", "reaped"))
            and not cleanup.get("failure_reasons"))
        drained = (drain == (record.get("stage_meta") or {}).get("worker_drain")
            and drain.get("parent_id") == parent_id and drain.get("status") == "closed"
            and drain.get("uncertain_cleanup") is False and ledger.get("status") == "closed"
            and ledger.get("parent_id") == parent_id)
        if parent_proven and drained:
            decision.update(classification="proven_drained", cleanup_proven=True,
                            evidence={"artifact_digests": artifacts})
            return decision
        if not parent_proven:
            decision["missing"].append("complete_parent_process_cleanup")
        if not drained:
            decision["missing"].append("01-work.worker-drain.json_and_closed_ledger")
        if not registration_bound or reg.get("registration_status") != "refused_before_register":
            decision["missing"].append("affirmative_no_admission_record")
    except (OSError, ValueError, TypeError, AttributeError) as error:
        decision["missing"].append("stable_bound_evidence: " + str(error)[:120])
    return decision


def evaluate_cleanup_reconciliation(entry: dict, receipt_path: Path, *, run_dir: Path | None = None,
                                    case: str | None = None, phase: str | None = None) -> dict:
    """Evaluate only original disposition-bound receipts; old missing proof refuses."""
    refusal = {"ok": False, "cleanup_proven": False, "classification": "uncertain", "missing": []}
    try:
        if entry.get("status") not in {"passed", "partial", "blocked", "failed", "interrupted", "invalidated"}:
            raise ValueError("terminal_attempt_required")
        if entry.get("cleanup_proven") is not False or entry.get("cleanup_reconciliation"):
            raise ValueError("unreconciled_false_cleanup_required")
        details = entry["details"]
        path = Path(receipt_path)
        if path.absolute() != Path(details["receipt"]).absolute():
            raise ValueError("exact_receipt_path_binding")
        raw = _stable_bytes(path)
        if not details.get("receipt_sha256") or hashlib.sha256(raw).hexdigest() != details["receipt_sha256"]:
            raise ValueError("original_budget_bound_receipt_digest")
        record = json.loads(raw)
        if record.get("schema") != "apgr.worker-canary/v1" or record.get("case") != (case or details.get("case")) or record.get("phase") != (phase or details.get("phase")):
            raise ValueError("case_phase_schema_binding")
        reservation = record["budget_reservation"]
        if any(k not in entry or reservation.get(k) != entry[k] for k in (
            "attempt", "pid", "pgid", "process_start_identity", "created_at")):
            raise ValueError("exact_attempt_reservation_binding")
        if record.get("candidate_source_identity") != details.get("source_identity") or not details.get("source_identity"):
            raise ValueError("source_identity_binding")
        if (record.get("bundle") or {}).get("manifest_sha256") != details.get("bundle_sha256") or not details.get("bundle_sha256"):
            raise ValueError("bundle_binding")
        if record.get("parent_cleanup") != details.get("parent_cleanup") or (record.get("stage_meta") or {}).get("worker_drain") != details.get("worker_drain"):
            raise ValueError("original_cleanup_observation_binding")
        if not details.get("classification_inputs") or record.get("classification_inputs") != details["classification_inputs"]:
            raise ValueError("original_budget_bound_classification_inputs")
        bound_run = Path(details["classification_inputs"]["run_dir"])
        if run_dir is not None and Path(run_dir).absolute() != bound_run.absolute():
            raise ValueError("exact_run_dir_binding")
        decision = classify_cleanup(record, bound_run)
        return {**decision, "ok": decision["cleanup_proven"],
                "receipt_sha256": hashlib.sha256(raw).hexdigest(),
                "artifact_digests": details["classification_inputs"]["artifact_digests"]}
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        refusal["missing"] = [str(error)[:160]]
        return refusal


def canonical_attempt_sha256(entry: dict) -> str:
    """Digest sorted compact Python JSON, including unchanged historical values."""
    raw = json.dumps(entry, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _legacy_require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _legacy_equal(actual, expected) -> bool:
    """JSON equality with strict bool/int distinctions, including nested fields."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_legacy_equal(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(_legacy_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def _legacy_json(raw: bytes) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            _legacy_require(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    def invalid_constant(_):
        raise ValueError("nonfinite JSON number")
    result = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    _legacy_require(isinstance(result, dict), "JSON object required")
    return result


def _legacy_document(path: Path, digest: str) -> dict:
    raw = _stable_bytes(path)
    _legacy_require(hashlib.sha256(raw).hexdigest() == digest, "immutable evidence hash mismatch")
    return _legacy_json(raw)


def _legacy_authority(authority: dict) -> None:
    expected = {"schema": LEGACY_AUTHORITY_SCHEMA, "phase": "APG166ZX",
                    "decision": "authorize_implementation_and_provider_free_testing_only",
                    "case": "gemini-sonnet", "historical_campaign_phase": SONNET_PHASE, "attempt": 1,
                    "classification": LEGACY_CLASSIFICATION, "real_budget_application_authorized_now": False,
                    "forbidden": LEGACY_FORBIDDEN_ACTIONS, "verified_historical_facts": LEGACY_EXPECTED_FACTS}
    _legacy_require(all(_legacy_equal(authority[k], v) for k, v in expected.items()), "authority contract mismatch")
    historical = authority["historical_canary"]
    _legacy_require(historical["filename"] == "APG166ZS-GEMINI-CANARY.json"
                    and historical["sha256"] == PINNED_CANARY_SHA256, "authority canary binding")
    _legacy_require(all(isinstance(historical[k], str) and historical[k]
                    for k in ("candidate_source_identity", "bundle_sha256", "parent_id")), "authority identity missing")
    budget = authority["budget_evidence"]
    _legacy_require(budget["attempt_record_cleanup_proven"] is False
                    and budget["attempt_status"] == "partial", "authority historical budget observation")
    _legacy_require(all(isinstance(budget[k], str) and re.fullmatch(r"[0-9a-f]{64}", budget[k])
                    for k in ("zv_packet_sha256", "budget_actions_sha256")), "authority evidence reference")


def _legacy_parent_cleanup(canary: dict, entry: dict) -> None:
    pc, meta = canary["parent_cleanup"], canary["stage_meta"]
    flags = ("cleanup_proven", "outer_group_absent", "nested_groups_absent",
             "verified_absence", "reaped", "wrapper_reaped", "parent_reaped")
    _legacy_require(all(pc[k] is True for k in flags), "parent cleanup proof incomplete")
    _legacy_require(_legacy_equal(pc, meta["cleanup"]) and _legacy_equal(pc, entry["details"]["parent_cleanup"]), "cleanup observation binding")
    _legacy_require(pc["failure_reasons"] == [] and pc["outer_group_status"] == "absent"
                    and pc["termination"]["reason"] == "normal_completion", "parent cleanup uncertainty")
    nested, count = pc["nested_group_status"], pc["nested_groups_registered"]
    _legacy_require(isinstance(nested, dict) and type(count) is int and count >= 0
                    and len(nested) == count and all(v == "absent" for v in nested.values()), "nested group absence")
    groups = pc["termination"]["nested_pgids"]
    _legacy_require(isinstance(groups, list) and len(groups) == count
                    and all(type(p) is int and p > 0 for p in groups)
                    and set(nested) == {str(p) for p in groups}, "nested group identity")
    _legacy_require(type(pc["termination"]["outer_pgid"]) is int
                    and pc["termination"]["outer_pgid"] > 0, "outer process group identity")


def recompute_legacy_historical_facts(canary: dict, entry: dict) -> dict:
    _legacy_require(not (LEGACY_NEWER_KEYS & canary.keys()), "current receipt through legacy path")
    meta = canary["stage_meta"]
    _legacy_require(not (LEGACY_NEWER_KEYS & meta.keys()), "current stage through legacy path")
    ag = meta["antigravity_evidence"]
    _legacy_require(canary["stage_ok"] is True and type(meta["exit_code"]) is int
                    and meta["exit_code"] == 0 and meta["stage"] == "work", "provider stage incomplete")
    _legacy_require(ag["validation"] == "validated" and ag["provider_status"] == "success"
                    and ag["transport_success"] is True, "provider completion evidence")
    for name in ("process_group_cleanup", "version_probe_cleanup"):
        _legacy_require(ag[name]["cleanup_complete"] is True
                        and ag[name]["group_absent"] is True, "provider process group absence")
    _legacy_parent_cleanup(canary, entry)
    cap, disposition = meta["worker_capability"], meta["worker_disposition"]
    reason = cap["reason"]
    _legacy_require(cap["available"] is False and cap["allowed"] is False
                    and isinstance(reason, str) and re.fullmatch(r"parent registration unavailable \([A-Za-z_][A-Za-z0-9_]*\)", reason)
                    and disposition == {"status": "unavailable", "reason": reason}, "registration timing not proven")
    for name, empty in (("admission", {}), ("worker_results", []), ("native_admission", [])):
        _legacy_require(_legacy_equal(canary[name], empty), "child admission or result present")
    _legacy_require(canary["native_sonnet_count"] is None
                    and cap["native_worker"]["enabled"] is False, "native admission possible")
    _legacy_require(_legacy_equal(canary["capacity_receipt"], dict.fromkeys(("max_gemini", "max_luna", "max_sonnet", "borrowing"))), "capacity admission observation")
    return {"provider_stage_ok": canary["stage_ok"], "parent_process_cleanup_proven": canary["parent_cleanup"]["cleanup_proven"],
            "parent_verified_absence": canary["parent_cleanup"]["verified_absence"],
            "worker_registration_failed_before_admission": True,
            "worker_admissions": len(canary["admission"]), "worker_result_records": len(canary["worker_results"]),
            "native_admissions": len(canary["native_admission"]), "sonnet_child_admitted": False,
            "maintained_worker_drain_record_present": "worker_drain" in meta}


def _legacy_entry(entry: dict, canary: dict) -> tuple[dict, dict | None]:
    audit = entry.get("cleanup_reconciliation")
    original = dict(entry)
    if "cleanup_reconciliation" in original:
        _legacy_require(isinstance(audit, dict) and entry["cleanup_proven"] is True, "invalid legacy readback")
        original.pop("cleanup_reconciliation")
        original["cleanup_proven"] = False
    _legacy_require(original.keys() == LEGACY_ENTRY_KEYS and original["cleanup_proven"] is False
                    and original["status"] == "partial" and type(original["attempt"]) is int
                    and original["attempt"] == 1, "legacy attempt shape or disposition")
    details = original["details"]
    _legacy_require(isinstance(details, dict) and details.keys() == LEGACY_DETAILS_KEYS
                    and details["worker_drain"] is None, "current or incomplete budget details")
    receipt = Path(details["receipt"])
    _legacy_require(receipt.name == "canary.json" and receipt.parent.name == "gemini-sonnet", "historical receipt identity")
    _legacy_require(details["source_identity"] == canary["candidate_source_identity"]
                    and details["bundle_sha256"] == canary["bundle"]["manifest_sha256"], "budget source or bundle mismatch")
    for key in ("attempt", "pid", "pgid", "process_start_identity", "created_at", "cause"):
        _legacy_require(_legacy_equal(original[key], canary["budget_reservation"][key]), "reservation identity mismatch")
    return original, audit


def _legacy_approval(path: Path | None, digest: str | None, decision: dict) -> None:
    if path is None:
        _legacy_require(digest is None, "approval path required with digest")
        return
    approval = _legacy_document(path, digest)
    expected = {"schema": LEGACY_APPROVAL_SCHEMA, "decision": "authorize_legacy_cleanup_application",
                    "reviewed_authority_sha256": PINNED_AUTHORITY_SHA256, "canary_sha256": PINNED_CANARY_SHA256,
                    "case": "gemini-sonnet", "attempt": 1, "historical_campaign_phase": SONNET_PHASE,
                    "classification": LEGACY_CLASSIFICATION, "original_attempt_sha256": decision["original_attempt_sha256"]}
    _legacy_require(_legacy_equal(approval, expected), "application approval binding mismatch")


def _legacy_readback(audit: dict, decision: dict) -> None:
    expected = {"operation": LEGACY_OPERATION, "original_cleanup_proven": False, "original_status": "partial",
                    "original_attempt_sha256": decision["original_attempt_sha256"], "classification": LEGACY_CLASSIFICATION,
                    "canary_sha256": decision["canary_sha256"], "authority_sha256": decision["authority_sha256"],
                    "approval_sha256": decision["approval_sha256"], "recomputed_historical_facts": decision["recomputed_facts"]}
    _legacy_require(decision["approval_sha256"] is not None, "readback application approval required")
    _legacy_require(audit.keys() == expected.keys() | {"at", "raw_budget_sha256_before", "reconciler_source_identity"}
                    and all(_legacy_equal(audit[k], v) for k, v in expected.items()), "contradictory legacy reconciliation")
    _legacy_require(type(audit["at"]) in (float, int) and audit["at"] > 0
                    and all(isinstance(audit[k], str) and re.fullmatch(r"[0-9a-f]{64}", audit[k])
                            for k in ("raw_budget_sha256_before", "reconciler_source_identity")), "malformed legacy audit")


def evaluate_legacy_cleanup_reconciliation(
    entry: dict, *, canary_path: Path, authority_path: Path, authority_sha256: str,
    case: str, attempt: int, phase: str,
    approval_path: Path | None = None, approval_sha256: str | None = None,
) -> dict:
    """Evaluate the one source-pinned legacy shape; no caller permit overrides."""
    try:
        _legacy_require(type(attempt) is int and (phase, case, attempt) == LEGACY_SOURCE_PERMIT, "legacy permit identity")
        _legacy_require(authority_sha256 == PINNED_AUTHORITY_SHA256, "reviewed authority digest required")
        authority = _legacy_document(authority_path, PINNED_AUTHORITY_SHA256)
        _legacy_authority(authority)
        canary = _legacy_document(canary_path, PINNED_CANARY_SHA256)
        _legacy_require(canary["schema"] == "apgr.worker-canary/v1" and canary["case"] == case
                        and canary["phase"] == phase and canary["status"] == "partial"
                        and canary["cleanup_proven"] is False, "archived canary identity or state")
        historical = authority["historical_canary"]
        _legacy_require(canary["candidate_source_identity"] == historical["candidate_source_identity"]
                        and canary["bundle"]["manifest_sha256"] == historical["bundle_sha256"]
                        and canary["parent_id"] == historical["parent_id"], "authority source, bundle or parent mismatch")
        original, audit = _legacy_entry(entry, canary)
        facts = recompute_legacy_historical_facts(canary, original)
        _legacy_require(_legacy_equal(facts, authority["verified_historical_facts"]), "recomputed historical facts mismatch")
        decision = {"ok": True, "status": "already_reconciled" if audit else "eligible",
                        "classification": LEGACY_CLASSIFICATION, "cleanup_proven": True,
                        "canary_sha256": PINNED_CANARY_SHA256, "authority_sha256": PINNED_AUTHORITY_SHA256,
                        "approval_sha256": approval_sha256, "original_attempt_sha256": canonical_attempt_sha256(original),
                        "recomputed_facts": facts, "already_reconciled": audit is not None, "missing": []}
        _legacy_approval(approval_path, approval_sha256, decision)
        if audit is not None:
            _legacy_readback(audit, decision)
        return decision
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return {"ok": False, "cleanup_proven": False, "classification": "uncertain", "missing": [str(error)[:160]]}


def _legacy_budget_decision(raw: bytes, **evidence) -> tuple[dict, dict, dict]:
    data = _legacy_json(raw)
    _legacy_require(data.keys() == {"schema", "phase", "cases"} and data["schema"] == SCHEMA
                    and data["phase"] == evidence["phase"], "budget identity; refusing reset")
    case_data = data["cases"][evidence["case"]]
    _legacy_require(case_data.keys() == {"attempts"}, "conflicting case disposition")
    attempts = case_data["attempts"]
    _legacy_require(isinstance(attempts, list) and len(attempts) == 1, "unique attempt 1 required; later attempt refused")
    entry = attempts[0]
    decision = evaluate_legacy_cleanup_reconciliation(entry, **evidence)
    _legacy_require(decision["ok"], ", ".join(decision["missing"]))
    return data, entry, decision


def main(argv: list[str] | None = None) -> int:
    """Explicit-home legacy operator; default is read-only evaluation."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    legacy = commands.add_parser("legacy-reconcile", help="Evaluate pinned legacy custody; apply requires separate approval")
    legacy.add_argument("--home", required=True, type=Path)
    legacy.add_argument("--phase", choices=sorted(ALLOWED_PHASES), default=SONNET_PHASE)
    legacy.add_argument("--case", choices=["gemini-sonnet"], default="gemini-sonnet")
    legacy.add_argument("--attempt", type=int, choices=[1], default=1)
    for name in ("canary", "authority", "approval"):
        legacy.add_argument("--" + name, required=name != "approval", type=Path)
    legacy.add_argument("--authority-sha256", required=True)
    legacy.add_argument("--approval-sha256")
    legacy.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = CanaryBudget(home=args.home, phase=args.phase).reconcile_legacy_attempt_cleanup(
            args.case, args.attempt, canary_path=args.canary, authority_path=args.authority,
            authority_sha256=args.authority_sha256, approval_path=args.approval,
            approval_sha256=args.approval_sha256, apply=args.apply)
    except CanaryBudgetError as error:
        print(json.dumps({"ok": False, "reason": str(error)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
