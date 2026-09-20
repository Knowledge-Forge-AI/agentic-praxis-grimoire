"""Provider-free manager resolutions for dispatcher ownership challenges.

The resolution receipt is a bounded owner record.  It binds one immutable
challenge observation to one closed decision and to the exact archived source
run.  Creating the record never rewrites the source run or the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

_LIBEXEC_DIR = str(Path(__file__).resolve().parents[1])
if _LIBEXEC_DIR not in sys.path:
    sys.path.insert(0, _LIBEXEC_DIR)

if __name__ == "__main__":
    from controller_generation_bootstrap import enter
    if len(sys.argv) < 2 or sys.argv[1] != "ownership":
        sys.argv.insert(1, "ownership")
    try:
        enter(Path(__file__).resolve().parents[2])
    except (OSError, ValueError, RuntimeError) as error:
        sys.exit(f"agent-phase-ownership: generation binding failed ({type(error).__name__})")

from agent_phase import archive_verify, gitstate, ownership_challenge  # noqa: E402
from agent_phase.request import load_request  # noqa: E402
from agent_phase.resume_validation import load_core, load_json, require_source  # noqa: E402


SCHEMA = "agent-phase-ownership-resolution-v1"
MAX_BYTES = 256 * 1024
MAX_REASON_BYTES = 4096

_HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class OwnershipResolutionError(ValueError):
    """A source, challenge, or manager receipt failed closed validation."""

    code = "OWNERSHIP_RESOLUTION_INVALID"

    def __init__(self, detail: str, code: str | None = None) -> None:
        self.code = code or self.code
        self.detail = detail
        super().__init__(f"{self.code}: {detail}")


def encoded(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as error:
        raise OwnershipResolutionError("receipt is not bounded UTF-8 JSON") from error


def digest(value: Any) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def _invalid(detail: str) -> None:
    raise OwnershipResolutionError(detail)


def _safe_hex(value: Any, pattern: re.Pattern[str], label: str) -> None:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        _invalid(f"{label} identity is invalid")


def _read_json(path: Path) -> dict[str, Any]:
    """Read one exact regular JSON file while rejecting duplicate keys."""
    if path.is_symlink() or not path.is_file():
        _invalid("ownership resolution must be an exact regular file")
    try:
        info = path.stat()
        if info.st_size > MAX_BYTES or info.st_mode & 0o077:
            _invalid("ownership resolution file is unsafe or oversized")
        raw = path.read_bytes()
    except OSError as error:
        raise OwnershipResolutionError("cannot read ownership resolution") from error
    if len(raw) > MAX_BYTES:
        _invalid("ownership resolution exceeds its size bound")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                _invalid("ownership resolution repeats a JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (UnicodeError, TypeError, json.JSONDecodeError) as error:
        raise OwnershipResolutionError("invalid ownership resolution JSON") from error
    if not isinstance(value, dict):
        _invalid("ownership resolution must be a JSON object")
    return value


def _manager_generation() -> dict[str, Any] | None:
    try:
        from controller_generation import provenance

        return provenance()
    except (ImportError, OSError, RuntimeError, ValueError, TypeError):
        return None


def _candidate_record(record: dict[str, Any], raw_tree: str | None = None) -> dict[str, Any]:
    """Return the exact candidate binding for a challenge observation.

    A challenge may be observed after the producer boundary and retained while
    later terminal work changes unrelated paths.  Its immutable ``raw_tree``
    remains the creation observation; the receipt separately binds the sealed
    terminal tree while carrying the challenged path's exact object identity.
    """
    return {
        "entry_tree": record["entry_tree"],
        "raw_tree": record["raw_tree"] if raw_tree is None else raw_tree,
        "base_head": record["base_head"],
        "path": record["path"],
        "status": record["status"],
        "entry_object": record["entry_object"],
        "current_object": record["current_object"],
        "base_object": record["base_object"],
    }


def _load_source(source_path: Path, root: Path) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load and archive-verify a source without inspecting the live boundary."""
    try:
        source = require_source(source_path)
        state = load_json(source, "state.json")
        request = load_request(source / "request.json")
        source, state, _result, _resolved, _entry, _completed = load_core(
            source,
            state.get("phase_id"),
            request,
            None,
            None,
        )
        archive_verify.verify_source_archive(source)
        source_manifest = archive_verify.source_manifest(source)
    except (OSError, TypeError, KeyError, ValueError, RuntimeError) as error:
        if isinstance(error, OwnershipResolutionError):
            raise
        raise OwnershipResolutionError(
            f"source evidence cannot be loaded: {error}", "OWNERSHIP_SOURCE_INVALID"
        ) from error

    # The source is historical evidence.  Its repository identity is still
    # checked against the live product root by the caller before any receipt
    # is accepted, but no current worktree boundary is captured here.
    try:
        ownership_challenge.validate(root, state)
    except (TypeError, KeyError, ValueError, RuntimeError) as error:
        raise OwnershipResolutionError(
            f"ownership challenge ledger is invalid: {error}",
            "OWNERSHIP_CHALLENGE_INVALID",
        ) from error
    return source, state, source_manifest, request.as_dict()


def _state_raw_tree(state: dict[str, Any]) -> str:
    for key in ("raw_terminal_candidate", "terminal_candidate", "closeout_candidate"):
        value = state.get(key)
        if isinstance(value, dict) and isinstance(value.get("tree"), str):
            ownership_challenge.validate_tree(value["tree"])
            return value["tree"]
    _invalid("source has no sealed terminal candidate tree")
    raise AssertionError("unreachable")


def _identity_matches_state(
    record: dict[str, Any],
    state: dict[str, Any],
    root: Path,
    source: Path | None = None,
) -> None:
    """Accept an origin only through an exact, archived resume chain."""
    expected = {
        "repository": str(root.resolve()),
        "project": state.get("project"),
        "phase_id": state.get("phase_id"),
        "lifecycle": state.get("lifecycle", "standard"),
    }
    for key, value in expected.items():
        if record.get(key) != value:
            _invalid(f"challenge {key} differs from source state")
    cursor = state
    seen: set[Path] = {source.resolve()} if source is not None else set()
    for _depth in range(16):
        if (record.get("run_id") == cursor.get("run_id")
                and record.get("controller_generation") == cursor.get("controller_generation")):
            return
        resume = cursor.get("resume")
        if source is None or cursor.get("resumed") is not True or not isinstance(resume, dict):
            _invalid("challenge origin differs from source state")
        source_info = resume.get("source")
        if not isinstance(source_info, dict):
            _invalid("resumed challenge lacks exact source provenance")
        source_name = source_info.get("path")
        if not isinstance(source_name, str) or not Path(source_name).is_absolute():
            _invalid("resumed challenge source path is invalid")
        try:
            predecessor = require_source(Path(source_name))
            if predecessor in seen:
                _invalid("resumed challenge source provenance cycles")
            archive_verify.verify_source_archive(predecessor)
            manifest = archive_verify.source_manifest(predecessor)
            hashes = resume.get("source_hashes")
            if (not isinstance(hashes, dict) or "state.json" not in hashes
                    or any(manifest["files"].get(name) != value for name, value in hashes.items())):
                _invalid("resumed challenge source hashes differ")
            archived = source_info.get("archive")
            if (not isinstance(archived, dict)
                    or archived.get("sha256") != manifest["archive_sha256"]):
                _invalid("resumed challenge source archive differs")
            predecessor_state = load_json(predecessor, "state.json")
            if predecessor_state.get("run_id") != resume.get("source_run_id"):
                _invalid("resumed challenge source run identity differs")
            if any(predecessor_state.get(key) != expected[key]
                   for key in ("project", "phase_id", "lifecycle")):
                _invalid("resumed challenge source phase identity differs")
            ownership_challenge.validate(root, predecessor_state)
            records = (predecessor_state.get("ownership_challenges") or {}).get("records", [])
            if record not in records:
                _invalid("resumed challenge is absent from its archived predecessor")
        except (OSError, TypeError, KeyError, ValueError, RuntimeError) as error:
            if isinstance(error, OwnershipResolutionError):
                raise
            raise OwnershipResolutionError("resumed challenge source evidence is invalid") from error
        seen.add(predecessor)
        cursor = predecessor_state
    _invalid("resumed challenge source provenance exceeds its depth bound")


def _open_challenge(
    root: Path,
    state: dict[str, Any],
    challenge_id: str,
    source: Path | None = None,
) -> dict[str, Any]:
    records = [
        record
        for record in ownership_challenge.open_records(state)
        if record.get("challenge_id") == challenge_id
    ]
    if len(records) != 1:
        _invalid("challenge is missing, already resolved, or superseded")
    record = records[0]
    _identity_matches_state(record, state, root, source)
    raw_tree = _state_raw_tree(state)
    try:
        current = ownership_challenge.object_at(root, raw_tree, record["path"])
    except (OSError, TypeError, KeyError, ValueError, RuntimeError) as error:
        raise OwnershipResolutionError(
            f"challenge terminal candidate cannot be read: {error}",
            "OWNERSHIP_CHALLENGE_INVALID",
        ) from error
    if current != record["current_object"]:
        _invalid("challenge candidate object differs from source terminal candidate")
    return record


def _manager_authority(generation: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "kind": "owner",
        "surface": "agent-phase-ownership",
        "operation": "resolve",
        "controller_generation": generation,
    }


def _record_without_digest(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "sha256"}


def _receipt(
    root: Path,
    source: Path,
    state: dict[str, Any],
    source_manifest: dict[str, Any],
    challenge: dict[str, Any],
    decision: str,
    reason: str,
) -> dict[str, Any]:
    candidate = _candidate_record(challenge, raw_tree=_state_raw_tree(state))
    generation = _manager_generation()
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "source_run": str(source),
        "source_run_id": state["run_id"],
        "repository": str(root.resolve()),
        "project": state["project"],
        "phase_id": state["phase_id"],
        "lifecycle": state.get("lifecycle", "standard"),
        "source_controller_generation": state.get("controller_generation"),
        "controller_generation": generation,
        "source_manifest": source_manifest,
        "source_manifest_sha256": digest(source_manifest),
        "challenge_id": challenge["challenge_id"],
        "challenge": challenge,
        "challenge_sha256": digest(challenge),
        "decision": decision,
        "reason": reason,
        "candidate_tree": candidate["raw_tree"],
        "candidate_tree_sha256": digest(candidate),
        "candidate": candidate,
        "manager_authority": _manager_authority(generation),
        "provider_invocations": 0,
        "product_test_invocations": 0,
        "git_mutation_performed": False,
        "source_rewritten": False,
    }
    receipt["sha256"] = digest(receipt)
    return receipt


def validate_receipt(value: dict[str, Any]) -> dict[str, Any]:
    """Validate receipt structure and its self-checksum without Git access."""
    if not isinstance(value, dict) or value.get("schema") != SCHEMA:
        _invalid("unsupported ownership resolution schema")
    required = {
        "schema", "source_run", "source_run_id", "repository", "project", "phase_id",
        "lifecycle", "source_controller_generation", "controller_generation",
        "source_manifest", "source_manifest_sha256", "challenge_id", "challenge",
        "challenge_sha256", "decision", "reason", "candidate_tree",
        "candidate_tree_sha256", "candidate", "manager_authority",
        "provider_invocations", "product_test_invocations", "git_mutation_performed",
        "source_rewritten", "sha256",
    }
    if set(value) != required:
        _invalid("ownership resolution fields are not exact")
    if len(encoded(value)) > MAX_BYTES:
        _invalid("ownership resolution exceeds its size bound")
    _safe_hex(value.get("sha256"), _HEX64, "receipt checksum")
    if value["sha256"] != digest(_record_without_digest(value)):
        _invalid("ownership resolution checksum differs")
    _safe_hex(value["source_manifest_sha256"], _HEX64, "source manifest")
    _safe_hex(value["challenge_sha256"], _HEX64, "challenge")
    _safe_hex(value["candidate_tree_sha256"], _HEX64, "candidate")
    if not isinstance(value["source_run"], str) or not value["source_run"]:
        _invalid("source run identity is invalid")
    for key in ("source_run_id", "repository", "project", "phase_id", "lifecycle", "candidate_tree"):
        if not isinstance(value[key], str) or not value[key]:
            _invalid(f"{key} identity is invalid")
    if not isinstance(value["source_manifest"], dict):
        _invalid("source manifest is invalid")
    if value["source_manifest_sha256"] != digest(value["source_manifest"]):
        _invalid("source manifest checksum differs")
    if not isinstance(value["challenge"], dict):
        _invalid("challenge record is invalid")
    if value["challenge_id"] != value["challenge"].get("challenge_id"):
        _invalid("challenge ID differs from its record")
    if value["challenge_sha256"] != digest(value["challenge"]):
        _invalid("challenge record checksum differs")
    if not re.fullmatch(r"ownch1-[0-9a-f]{64}\Z", value["challenge_id"]):
        _invalid("challenge ID is invalid")
    if value["decision"] not in ("phase_owned", "exclude_unrelated"):
        _invalid("unsupported ownership decision")
    if (not isinstance(value["reason"], str) or not value["reason"].strip()
            or len(value["reason"].encode("utf-8")) > MAX_REASON_BYTES):
        _invalid("manager reason is empty or oversized")
    if not isinstance(value["candidate"], dict):
        _invalid("candidate binding is invalid")
    if value["candidate_tree_sha256"] != digest(value["candidate"]):
        _invalid("candidate binding checksum differs")
    if value["candidate_tree"] != value["candidate"].get("raw_tree"):
        _invalid("candidate tree differs from candidate binding")
    if (type(value["provider_invocations"]) is not int
            or value["provider_invocations"] != 0
            or type(value["product_test_invocations"]) is not int
            or value["product_test_invocations"] != 0
            or value["git_mutation_performed"] is not False
            or value["source_rewritten"] is not False):
        _invalid("manager resolution records an unsupported side effect")
    authority = value["manager_authority"]
    if authority != _manager_authority(value["controller_generation"]):
        _invalid("manager authority binding is invalid")
    return value


def read(path: Path) -> dict[str, Any]:
    return validate_receipt(_read_json(path))


def validate_for_source(
    path: Path,
    root: Path,
    source: Path,
    state: dict[str, Any],
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Bind a receipt to one exact source and its current challenge bytes."""
    receipt = read(path)
    # The receipt carries both the canonical path and the archived source
    # identity.  Keep the path binding exact so a symlink/alias cannot be
    # substituted while preserving the same resolved directory.
    if receipt["source_run"] != str(source.resolve()):
        _invalid("receipt names a different source run")
    try:
        receipt_source = Path(receipt["source_run"]).resolve(strict=True)
    except OSError as error:
        raise OwnershipResolutionError("receipt source run is unavailable") from error
    if receipt_source != source.resolve():
        _invalid("receipt names a different source run")
    if receipt["repository"] != str(root.resolve()):
        _invalid("receipt names a different repository")
    expected_source = {
        "source_run_id": state.get("run_id"),
        "project": state.get("project"),
        "phase_id": state.get("phase_id"),
        "lifecycle": state.get("lifecycle", "standard"),
    }
    for key, expected in expected_source.items():
        if receipt[key] != expected:
            _invalid(f"receipt {key} differs from source")
    if receipt["source_controller_generation"] != state.get("controller_generation"):
        _invalid("receipt controller generation differs from source")
    if receipt["source_manifest"] != source_manifest:
        _invalid("source manifest differs from receipt")
    challenge = receipt["challenge"]
    try:
        ownership_challenge.validate_record(root, challenge)
        ownership_challenge.validate(root, state)
    except (TypeError, KeyError, ValueError, RuntimeError) as error:
        raise OwnershipResolutionError(
            f"receipt challenge is invalid: {error}", "OWNERSHIP_CHALLENGE_INVALID"
        ) from error
    ledger = state.get("ownership_challenges")
    if not isinstance(ledger, dict) or not isinstance(ledger.get("records"), list):
        _invalid("source has no ownership challenge ledger")
    current = next(
        (record for record in ledger["records"]
         if record.get("challenge_id") == receipt["challenge_id"]),
        None,
    )
    if current != challenge:
        _invalid("receipt challenge differs from source ledger")
    _identity_matches_state(challenge, state, root, source)
    if receipt["candidate"] != _candidate_record(challenge, raw_tree=_state_raw_tree(state)):
        _invalid("receipt candidate differs from challenge evidence")
    if receipt["candidate_tree"] != _state_raw_tree(state):
        _invalid("receipt candidate differs from source terminal candidate")
    if receipt["decision"] not in challenge["allowed_decisions"]:
        _invalid("receipt decision is not allowed for this challenge")
    if receipt["candidate"].get("path") != challenge["path"]:
        _invalid("receipt candidate path differs from challenge")
    return receipt


def apply_receipts(
    root: Path,
    source: Path,
    state: dict[str, Any],
    source_manifest: dict[str, Any],
    paths: list[Path] | tuple[Path, ...] | None,
) -> list[dict[str, Any]]:
    """Validate and apply manager receipts to a caller-owned state copy."""
    if paths is not None and not isinstance(paths, (list, tuple)):
        _invalid("ownership resolution inputs must be a list")
    receipts: list[dict[str, Any]] = []
    seen: set[str] = set()
    seen_paths: set[str] = set()
    for path in paths or ():
        try:
            if Path(path).resolve().is_relative_to(root.resolve()):
                _invalid("ownership resolution must be outside the product repository")
        except OSError as error:
            raise OwnershipResolutionError(
                "ownership resolution path is unavailable"
            ) from error
        receipt = validate_for_source(path, root, source, state, source_manifest)
        challenge_id = receipt["challenge_id"]
        if challenge_id in seen:
            _invalid("duplicate ownership resolution receipt")
        candidate_path = receipt["challenge"]["path"]
        if candidate_path in seen_paths:
            _invalid("contradictory ownership resolution receipts")
        seen.add(challenge_id)
        seen_paths.add(candidate_path)
        try:
            ownership_challenge.resolve_manager(
                root,
                state,
                challenge_id,
                receipt["decision"],
                receipt["sha256"],
            )
        except (TypeError, KeyError, ValueError, RuntimeError) as error:
            raise OwnershipResolutionError(
                f"manager resolution is stale or unsupported: {error}",
                "OWNERSHIP_CHALLENGE_INVALID",
            ) from error
        receipts.append(receipt)
    return receipts


def create(
    source_path: Path,
    root: Path,
    challenge_id: str,
    decision: str,
    reason: str,
) -> dict[str, Any]:
    """Create one manager receipt without mutating source or repository state."""
    if not isinstance(challenge_id, str) or not re.fullmatch(r"ownch1-[0-9a-f]{64}\Z", challenge_id):
        _invalid("challenge ID is invalid")
    if decision not in ("phase_owned", "exclude_unrelated"):
        _invalid("unsupported ownership decision")
    if (not isinstance(reason, str) or not reason.strip()
            or len(reason.encode("utf-8")) > MAX_REASON_BYTES):
        _invalid("manager reason is empty or oversized")
    from agent_phase.finalization_proof import require_standard_environment, _repository_guard
    require_standard_environment()
    root = gitstate.repository_root(root).resolve()
    _repository_guard(root)
    source, state, source_manifest, _request = _load_source(source_path, root)
    if source.is_relative_to(root):
        _invalid("source evidence must be outside the product repository")
    challenge = _open_challenge(root, state, challenge_id, source)
    if decision not in challenge["allowed_decisions"]:
        _invalid("decision is not allowed for the challenge")
    receipt = _receipt(root, source, state, source_manifest, challenge, decision, reason)
    validate_receipt(receipt)
    return receipt


def _write_create_only(path: Path, value: dict[str, Any]) -> None:
    target = path.absolute()
    resolved = target.resolve()
    if any(resolved.is_relative_to(Path(value[key]).resolve())
           for key in ('repository', 'source_run')):
        _invalid('ownership resolution output must be outside the repository and historical source run')
    if target.is_symlink() or target.exists():
        _invalid("ownership resolution output already exists")
    data = encoded(value) + b"\n"
    if len(data) > MAX_BYTES:
        _invalid("ownership resolution output exceeds its size bound")
    try:
        fd = os.open(
            target,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
    except OSError as error:
        raise OwnershipResolutionError("cannot create ownership resolution output") from error
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        target.chmod(0o600)
    except OSError as error:
        raise OwnershipResolutionError("cannot write ownership resolution output") from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase-ownership", allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)
    resolve_parser = subparsers.add_parser("resolve", allow_abbrev=False)
    resolve_parser.add_argument("--run", type=Path, required=True,
                                help="exact historical run directory")
    resolve_parser.add_argument("--challenge", required=True,
                                help="exact immutable ownership challenge ID")
    resolve_parser.add_argument("--decision", required=True,
                                choices=("phase_owned", "exclude_unrelated"))
    resolve_parser.add_argument("--reason", required=True,
                                help="bounded manager rationale")
    resolve_parser.add_argument("--output", type=Path, required=True,
                                help="new owner-private receipt outside the product repository")
    resolve_parser.add_argument("--dry-run", action="store_true",
                                help="validate and print without creating the receipt")
    args = parser.parse_args(argv)
    try:
        from agent_phase.finalization_proof import require_standard_environment
        require_standard_environment()
        root = gitstate.repository_root(Path.cwd()).resolve()
        output = args.output.resolve()
        if output.is_relative_to(root):
            raise OwnershipResolutionError(
                "ownership resolution output must be outside the product repository"
            )
        receipt = create(args.run, root, args.challenge, args.decision, args.reason)
        if not args.dry_run:
            _write_create_only(args.output, receipt)
        json.dump(receipt, sys.stdout, sort_keys=True, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    except (OwnershipResolutionError, OSError, TypeError, KeyError, ValueError, RuntimeError) as error:
        payload = {
            "schema": SCHEMA,
            "action": "refused",
            "provider_invocations": 0,
            "product_test_invocations": 0,
            "git_mutation_performed": False,
            "source_rewritten": False,
            "code": getattr(error, "code", "OWNERSHIP_RESOLUTION_INVALID"),
            "detail": str(error),
        }
        json.dump(payload, sys.stdout, sort_keys=True, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[2:]))
