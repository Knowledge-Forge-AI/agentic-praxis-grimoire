"""D1 capture and outcome derivation shared by execution and readback."""
import hashlib
from collections.abc import Mapping


def capture_receipt_valid(receipt, raw, terminal):
    """Verify the wrapper receipt independently of runner output completeness."""
    return (
        receipt.get("schema") == "apg.claude-stream-completion/v2"
        and receipt.get("raw_stream") == {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        and receipt.get("durable") is True
        and receipt.get("stream_enabled_before_start") is True
        and type(receipt.get("process_status")) is int
        and receipt["process_status"] == terminal.get("exit_code")
    )


def capture_status(receipt, raw, terminal):
    complete = capture_receipt_valid(receipt, raw, terminal) and not any(
        terminal.get(k) for k in ("truncated", "timeout", "signal")
    )
    return {"status": "complete" if complete else "incomplete",
            "receipt_present": bool(receipt), "process_status": receipt.get("process_status")}


def failure_reasons(imported, terminal, capture, surface, reads, oracle, *,
                    native_launch, git_preserved, settings_preserved):
    reasons = []
    if imported.get("provider_outcome") != "success":
        error = "PROVIDER_ERROR" if imported.get("provider_outcome") == "error" else "PROVIDER_OUTCOME_UNVERIFIED"
        if "authentication_failed" in imported.get("provider_error", {}).get("assistant_errors", []):
            error += ":authentication_failed"
        reasons.append(error)
    if terminal.get("exit_code") != 0:
        reasons.append("NONZERO_EXIT:" + str(terminal.get("exit_code")))
    reasons.extend(surface.get("failure_codes", []))
    if surface.get("valid") is not True and not surface.get("failure_codes"):
        reasons.append("SURFACE_UNVERIFIED")
    if not reads:
        reasons.append("NO_NATIVE_READ")
    if capture["status"] != "complete":
        reasons.append("CAPTURE_INCOMPLETE")
    if oracle.get("status") != "pass":
        reasons.append("ORACLE_FAILED:" + str(oracle.get("reason") or "unverified"))
    if not isinstance(native_launch, Mapping):
        reasons.append("NATIVE_LAUNCH_CUSTODY_MISSING")
    if not git_preserved:
        reasons.append("GIT_DRIFT")
    if not settings_preserved:
        reasons.append("SETTINGS_DRIFT")
    return reasons
