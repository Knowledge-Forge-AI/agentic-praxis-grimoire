"""One fresh independent review after a successful but invalid review transport."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import review_result
from .envelope import RenderedPrompt


def retry_review(dispatcher, directory, state, stage, nonce, error):
    from .dispatch import DispatchError
    from .lifecycle_dispatch import require_unchanged

    context = getattr(dispatcher, "_review_attempt_context", None)
    recoveries = state.setdefault("review_recoveries", {})
    if context is None or stage.name in recoveries:
        raise DispatchError(str(error), error.code) from error
    endpoint = context["endpoint"]
    record = {
        "schema": "agent-phase-review-recovery-v1", "stage": stage.name,
        "reason": "successful_transport_invalid_review_result",
        "candidate": context["binding"],
        "endpoint": {"provider": endpoint.provider, "profile": endpoint.profile},
        "attempt_count": 1, "second_provider_invocation": False,
        "attempts": [], "status": "pending",
    }
    recoveries[stage.name] = record

    def save():
        directory.write_json(f"{stage.prefix}.recovery.json", record)
        directory.write_json("state.json", state)

    def retain(prefix, number, attempt_nonce, diagnostic):
        files = []
        destination = directory.path / "review-attempts" / stage.name / str(number)
        destination.mkdir(parents=True, exist_ok=False)
        for source in sorted(directory.path.glob(prefix + ".*")):
            if source.name.endswith(".recovery.json"):
                continue
            data = source.read_bytes()
            target = destination / source.name
            with target.open("xb") as handle:
                handle.write(data)
            target.chmod(0o400)
            files.append({"name": str(target.relative_to(directory.path)),
                          "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        meta = json.loads((directory.path / f"{prefix}.meta.json").read_bytes())
        attempt = {"number": number, "nonce": attempt_nonce,
                   "prefix": prefix, "artifacts": files,
                   "transport_status": "completed" if meta.get("exit_code") == 0 and not meta.get("truncated") else "failed",
                   "exit_code": meta.get("exit_code"), "truncated": meta.get("truncated"),
                   "parser_error": diagnostic}
        record["attempts"].append(attempt)
        save()

    def require_retry_boundary():
        if state.get("worker_cleanup_pending"):
            record["status"] = "worker_cleanup_blocked"
            save()
            raise DispatchError("review retry blocked by pending worker cleanup", "WORKER_CLEANUP_FAILED")
        try:
            from . import review_binding, stage_delta
            stage_delta.normalize_index_if_needed(
                dispatcher.cwd, context["index_identity"], state, stage_name=stage.name
            )
            review_binding.verify(dispatcher.cwd, state, stage.name)
            require_unchanged(dispatcher, state, context["candidate"], stage.name,
                              context["index_identity"], strict=True)
        except DispatchError:
            record["status"] = "candidate_or_index_changed"
            save()
            raise

    retain(stage.prefix, 1, nonce, {"code": error.code, "detail": error.detail})
    require_retry_boundary()
    fresh_nonce = review_result.new_nonce()
    # Equal-length nonce substitution keeps the original scope/authority and
    # segment offsets byte-identical. Never forward the malformed response.
    rendered = context["rendered"]
    data = rendered.data
    for old, new in zip(review_result.markers(nonce), review_result.markers(fresh_nonce)):
        if data.count(old.encode()) != 1:
            record["status"] = "prompt_contract_invalid"
            save()
            raise DispatchError("review retry prompt contract is ambiguous", "REVIEW_RESULT_INVALID")
        data = data.replace(old.encode(), new.encode(), 1)
    retry_prefix = stage.prefix + ".review-retry"

    def invoked():
        record["second_provider_invocation"] = True
        record["attempt_count"] = 2
        save()

    try:
        result, meta = dispatcher._stage(
            directory, context["index"] + dispatcher.lifecycle.expected_provider_invocations,
            stage.name, retry_prefix, stage.role, endpoint,
            RenderedPrompt(data, rendered.segments), context["binding"],
            read_only=True, invocation_kind="auxiliary_review_retry",
            on_provider_invoke=invoked,
        )
    except BaseException:
        record["status"] = (
            "candidate_or_index_changed" if stage.name in state.get("review_binding_invalidations", {})
            else "transport_failed"
        )
        if (directory.path / f"{retry_prefix}.meta.json").is_file():
            retain(retry_prefix, 2, fresh_nonce, None)
        save()
        raise
    try:
        parsed = review_result.parse(result.stdout, stage.name, fresh_nonce)
    except review_result.ReviewResultError as second:
        record["status"] = "invalid"
        retain(retry_prefix, 2, fresh_nonce, {"code": second.code, "detail": second.detail})
        require_retry_boundary()
        state["blocking_reason"] = {"code": second.code, "detail": second.detail}
        state["outcome"] = "blocked"
        save()
        raise DispatchError(str(second), second.code) from second
    retain(retry_prefix, 2, fresh_nonce, None)
    require_retry_boundary()
    # Publish completed-stage artifacts only after ordinary strict validation.
    for source in sorted(directory.path.glob(retry_prefix + ".*")):
        name = stage.prefix + source.name[len(retry_prefix):]
        if source.name.endswith(".meta.json"):
            def canonical(value):
                if isinstance(value, str):
                    return value.replace(retry_prefix, stage.prefix)
                if isinstance(value, list):
                    return [canonical(item) for item in value]
                if isinstance(value, dict):
                    return {key: canonical(item) for key, item in value.items()}
                return value
            directory.write_json(name, canonical(meta))
        else:
            directory.write_bytes(name, source.read_bytes())
    record["status"] = "recovered"
    record["validated_nonce"] = fresh_nonce
    save()
    return parsed


def validate_recovery(source: Path, stage, canonical_result: dict) -> list[dict]:
    """Bind auxiliary attempts without counting them as extra checkpoints."""
    name = f"{stage.prefix}.recovery.json"
    path = source / name
    if not path.exists():
        return []
    record = json.loads(path.read_bytes())
    if not isinstance(record, dict):
        raise ValueError("review recovery is not an object")
    attempts = record.get("attempts")
    if (record.get("schema") != "agent-phase-review-recovery-v1"
            or record.get("stage") != stage.name or record.get("status") != "recovered"
            or record.get("attempt_count") != 2 or record.get("second_provider_invocation") is not True
            or not isinstance(attempts, list) or len(attempts) != 2):
        raise ValueError("invalid review recovery record")
    records = [{"stage": stage.name, "name": name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}]
    nonces = []
    for number, attempt in enumerate(attempts, 1):
        if not isinstance(attempt, dict) or attempt.get("number") != number:
            raise ValueError("review attempt identity mismatch")
        prefix = stage.prefix if number == 1 else stage.prefix + ".review-retry"
        base = Path("review-attempts") / stage.name / str(number)
        files = {}
        for item in attempt["artifacts"]:
            relative = Path(item["name"])
            if relative.parent != base or relative.name in files:
                raise ValueError("invalid review attempt artifact path")
            data = (source / relative).read_bytes()
            if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("review attempt artifact drift")
            files[relative.name] = data
            records.append({**item, "stage": stage.name})
        meta = json.loads(files[f"{prefix}.meta.json"])
        stdout = files[f"{prefix}.stdout.md"]
        prompt = files[f"{prefix}.prompt.md"]
        if (meta.get("candidate") != record["candidate"]
                or any(meta.get(key) != record["endpoint"].get(key) for key in ("provider", "profile"))
                or meta.get("exit_code") != 0 or meta.get("truncated")
                or meta.get("stdout_sha256") != hashlib.sha256(stdout).hexdigest()
                or meta.get("prompt_sha256") != hashlib.sha256(prompt).hexdigest()):
            raise ValueError("review recovery transport binding mismatch")
        drain = meta.get("worker_drain")
        if drain is not None and (
            not isinstance(drain, dict) or drain.get("uncertain_cleanup") is not False
            or json.loads(files[f"{prefix}.worker-drain.json"]) != drain
        ):
            raise ValueError("review attempt worker cleanup is unproven")
        nonce = attempt["nonce"]
        if not isinstance(nonce, str) or len(nonce) != 32 or any(c not in "0123456789abcdef" for c in nonce):
            raise ValueError("review attempt nonce is invalid")
        nonces.append(nonce)
        try:
            parsed = review_result.parse(stdout, stage.name, nonce)
        except review_result.ReviewResultError as error:
            if number != 1 or attempt["parser_error"] != {"code": error.code, "detail": error.detail}:
                raise ValueError("review attempt diagnostic mismatch") from error
        else:
            if number != 2 or parsed.as_dict() != canonical_result or attempt["parser_error"] is not None:
                raise ValueError("review attempt result mismatch")
        if number == 2:
            canonical_meta = json.loads((source / f"{stage.prefix}.meta.json").read_bytes())
            if (canonical_meta.get("candidate") != record["candidate"]
                    or stdout != (source / f"{stage.prefix}.stdout.md").read_bytes()
                    or prompt != (source / f"{stage.prefix}.prompt.md").read_bytes()):
                raise ValueError("canonical review differs from recovered attempt")
    if nonces[0] == nonces[1] or record.get("validated_nonce") != nonces[1]:
        raise ValueError("review recovery nonce mismatch")
    return records
