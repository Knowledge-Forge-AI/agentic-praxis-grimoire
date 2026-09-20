"""Source-owned D1 seam owner for probe APG166D-PROBE-D1.

Owns descriptor, probe fixture, authority, attempt state, raw evidence custody,
oracle, readback recomputation, provider-free fake subprocess lifecycle,
and production live entry point.
Converged onto one private internal execution owner: _execute_d1_attempt.
Zero real provider starts authorized in APG166P.
D1 does not qualify Codex/Antigravity/holdouts.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from agent_phase import context_adapter, provider
from . import claude_reads, importers, preregistration, readiness
from .execution import LIVE_ADMISSION_AVAILABLE
from .provider_free import ACTIVE_GUARD, LaunchGuard, ProviderInvocationError

PROBE_ID = "APG166D-PROBE-D1"
DESCRIPTOR_SCHEMA = "apg.d1-descriptor/v1"
AUTHORITY_SCHEMA = "apg.d1-authority/v1"
LIVE_AUTHORITY_SCHEMA = "apg.d1-live-authority/v1"
INSTRUMENTED_AUTHORITY_SCHEMA = "apg.d1-instrumented-authority/v1"
ATTEMPT_STATE_SCHEMA = "apg.d1-attempt-state/v1"
ATTEMPT_LEDGER_SCHEMA = "apg.d1-consumed-attempt-ledger/v1"
TRANSPORT_RECEIPT_SCHEMA = "apg.d1-transport-receipt/v1"
PROVIDER_START_RECEIPT_SCHEMA = "apg.d1-provider-start-receipt/v1"
CHILD_STARTUP_EVIDENCE_SCHEMA = "apg.d1-child-startup-evidence/v1"
LAUNCH_CONTRACT_SCHEMA = "apg.d1-launch-contract/v2"
OBSERVER_INPUTS_SCHEMA = "apg.d1-observer-inputs/v1"
RESPONSE_SCHEMA = "apg.d1-response/v1"
LIVE_EVIDENCE_SCHEMA = "apg.d1-live-record/v2"
INSTRUMENTED_EVIDENCE_SCHEMA = "apg.d1-instrumented-record/v2"
READINESS_CANDIDATE_SCHEMA = "apg.d1-readiness-candidate/v1"
NATIVE_LAUNCH_CUSTODY_SCHEMA = "apg.d1-native-launch-custody/v1"
NATIVE_LAUNCH_FACTS_ARTIFACT = "d1.context-launcher-deliveries.json"

PRODUCTION_TRANSPORT_KIND = "production-provider"
FAKE_TRANSPORT_KIND = "instrumented-provider-free"
D1_CLAUDE_CLI_VERSION = "2.1.281"
D1_SYSTEM_PATH = ("/usr/bin", "/bin", "/usr/local/bin")
EXECUTABLE_SELECTION_SCHEMA = "apg.d1-executable-selection/v1"

DESCRIPTOR_RELATIVE_PATH = "testing/h_eval/d1-descriptor.json"
FIXTURE_RELATIVE_PATH = "testing/h_eval/d1_probe_fixture.txt"
ORACLE_ID = "d1-nonce-oracle-v1"

ALLOWED_PROVIDER = "claude"
ALLOWED_PROFILE = "normal-final-review"
ALLOWED_ROLE = "Work Review"
ALLOWED_BINDING_ID = "binding-d1-work-review"
ALLOWED_PERMISSION_MODE = "plan"
ALLOWED_NATIVE_TOOLS = frozenset({"Read"})
FORBIDDEN_TOOLS = frozenset({"Bash", "Write", "Edit", "Agent"})
SURFACE_DISALLOWED_TOOLS = frozenset({
    "Bash", "Write", "Edit", "Agent", "Glob", "Grep",
    "WebFetch", "WebSearch", "NotebookEdit",
})

HEX_40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
AUTHORITY_ID_RE = re.compile(r"^[a-zA-Z0-9_\-\.]{3,128}$")
ATTEMPT_ID_RE = re.compile(r"^[a-zA-Z0-9_\-\.]{3,128}$")
SCENARIO_VARIANT_RE = re.compile(r"(?i)(?:\b|[a-z0-9_-]*_)scenario[-_\s]*0?([1-9]|1[0-5])(?=[^a-zA-Z0-9]|$)")


class D1Error(RuntimeError):
    """Base error for D1 qualification failures."""


class D1AuthorityError(D1Error):
    """Caller-supplied authority fails shape, binding, or replay invariants."""


class D1AttemptError(D1Error):
    """Attempt state violation, replay refusal, or duplicate execution."""


class D1ReadbackError(D1Error):
    """Evidence or custody verification failed during readback recomputation."""


class D1LiveAuthority(dict):
    """Authority record for manager-authorized live D1 attempts."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self["schema"] = LIVE_AUTHORITY_SCHEMA


class D1InstrumentedAuthority(dict):
    """Authority record for provider-free qualification attempts."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self["schema"] = INSTRUMENTED_AUTHORITY_SCHEMA


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def _write_private_bytes(path: Path, data: bytes) -> None:
    if path.parent.resolve() != path.parent:
        raise ValueError("artifact parent must be a physical directory")
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"destination exists; replay refused: {path}")
    parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        child_fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent_fd)
        with os.fdopen(child_fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def _write_private_json(path: Path, value: Any) -> None:
    _write_private_bytes(path, _json_bytes(value))


def read_regular_nofollow(path: Path) -> bytes:
    """Read one direct regular file; a symlink or non-regular entry raises OSError."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError(f"not a regular file: {path}")
        chunks = []
        while chunk := os.read(fd, 1 << 20):
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def native_launch_custody(data: bytes) -> dict[str, Any]:
    """Record-digest-bound custody for the exact native launch-facts bytes.

    The facts are observed once at the successful native Popen boundary.
    Readback checks the retained bytes against this custody and against
    source-derived expectations; it cannot re-observe a terminated child.
    """
    return {
        "schema": NATIVE_LAUNCH_CUSTODY_SCHEMA,
        "artifact": NATIVE_LAUNCH_FACTS_ARTIFACT,
        "bytes": len(data),
        "sha256": _sha256(data),
        "observation_scope": "native Popen success only; PID, process group and session are not re-observed after exit",
        "native_environment_digest": "diagnostic-non-authoritative; environment custody is the verified provider-start receipt",
    }


def _atomic_update_json(path: Path, value: Any) -> None:
    """Atomically update an existing private JSON file with fsync and directory fsync."""
    parent = path.parent
    if parent.resolve() != parent:
        raise ValueError("parent must be physical")
    temp_path = parent / f".tmp-{path.name}-{os.getpid()}-{int(time.time()*1000)}"
    if temp_path.exists():
        temp_path.unlink()
    _write_private_bytes(temp_path, _json_bytes(value))
    os.replace(temp_path, path)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def assert_structural_non_holdout(value: Any, root: Path | None = None) -> None:
    """Structurally reject any Scenario 01-15 reference, path, or binding."""
    repo = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    frozen_corpus = (repo / "testing/fixtures/context-eval").resolve()

    def _check(item: Any, path_prefix: str = "") -> None:
        if isinstance(item, str):
            if SCENARIO_VARIANT_RE.search(item):
                raise D1Error(f"structural holdout violation: '{item}' references frozen scenario at {path_prefix}")
            norm = os.path.normpath(item)
            if "testing/fixtures/context-eval" in norm or norm.startswith("testing/fixtures/context-eval"):
                raise D1Error(f"structural holdout violation: '{item}' references frozen context-eval at {path_prefix}")
            if "/" in item or item.endswith(".txt") or item.endswith(".json"):
                try:
                    resolved = (repo / item).resolve() if not Path(item).is_absolute() else Path(item).resolve()
                    if resolved == frozen_corpus or frozen_corpus in resolved.parents:
                        raise D1Error(f"structural holdout violation: path '{item}' resolves into frozen corpus at {path_prefix}")
                except D1Error:
                    raise
                except Exception:
                    pass
        elif isinstance(item, Mapping):
            for k, v in item.items():
                if isinstance(k, str) and SCENARIO_VARIANT_RE.search(k):
                    raise D1Error(f"structural holdout violation: key '{k}' references frozen scenario")
                _check(v, f"{path_prefix}.{k}" if path_prefix else str(k))
        elif isinstance(item, (list, tuple, set, frozenset)):
            for idx, elem in enumerate(item):
                _check(elem, f"{path_prefix}[{idx}]")

    _check(value)


def derive_policy_claude_model(root: Path | None = None) -> dict[str, str]:
    """Derive Claude model identity from current source policy:
    normal-final-review -> primary -> current model alias/catalog.
    """
    repo = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    profile_path = repo / "claude/profiles/normal-final-review.json"
    if not profile_path.is_file() or profile_path.is_symlink():
        raise D1Error(f"profile missing: {profile_path}")
    profile_data = json.loads(profile_path.read_bytes())
    role = profile_data.get("modelRole")
    if not role:
        raise D1Error("modelRole missing in normal-final-review profile")

    catalog_path = repo / "claude/model-catalog-v1.json"
    if not catalog_path.is_file() or catalog_path.is_symlink():
        raise D1Error(f"model catalog missing: {catalog_path}")
    catalog_data = json.loads(catalog_path.read_bytes())
    alias = catalog_data.get("roles", {}).get(role)
    if not alias:
        raise D1Error(f"role '{role}' not found in model catalog roles")
    model_entry = catalog_data.get("models", {}).get(alias, {})
    model_id = model_entry.get("id")
    if not model_id:
        raise D1Error(f"model id for alias '{alias}' not found in model catalog")

    import tomllib
    inventory = tomllib.loads((repo / "common/dispatcher/models.toml").read_text())
    selected = inventory["providers"]["claude"][ALLOWED_PROFILE]
    if selected["model"] != model_id or selected["effort"] != profile_data["effort"]:
        raise D1Error("source model inventory changed the accepted D1 route")
    return {
        "provider": ALLOWED_PROVIDER,
        "profile": ALLOWED_PROFILE,
        "model_role": role,
        "model_alias": alias,
        "model": model_id,
    }


def load_descriptor(root: Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    descriptor_path = repo_root / DESCRIPTOR_RELATIVE_PATH
    if not descriptor_path.is_file() or descriptor_path.is_symlink():
        raise D1Error(f"D1 descriptor missing or symlink: {descriptor_path}")
    data = json.loads(descriptor_path.read_bytes())
    validate_descriptor(data, root=repo_root)
    return data


def validate_descriptor(descriptor: Mapping[str, Any], root: Path | None = None) -> None:
    if not isinstance(descriptor, Mapping):
        raise D1Error("descriptor must be a mapping")
    if descriptor.get("schema") != DESCRIPTOR_SCHEMA:
        raise D1Error(f"invalid schema: {descriptor.get('schema')}")
    if descriptor.get("probe_id") != PROBE_ID:
        raise D1Error(f"invalid probe_id: {descriptor.get('probe_id')}")

    assert_structural_non_holdout(descriptor, root)

    route = descriptor.get("route", {})
    if not isinstance(route, Mapping):
        raise D1Error("descriptor route must be a mapping")
    if route.get("provider") != ALLOWED_PROVIDER:
        raise D1Error(f"provider must be {ALLOWED_PROVIDER}")
    if route.get("profile") != ALLOWED_PROFILE:
        raise D1Error(f"profile must be {ALLOWED_PROFILE}")
    if route.get("roles") != [ALLOWED_ROLE]:
        raise D1Error(f"roles must be [{ALLOWED_ROLE}]")
    if set(route.get("allowed_native_tools", [])) != ALLOWED_NATIVE_TOOLS:
        raise D1Error(f"native tools must be {sorted(ALLOWED_NATIVE_TOOLS)}")
    if set(route.get("forbidden_tools", [])) != FORBIDDEN_TOOLS:
        raise D1Error(f"forbidden tools must be {sorted(FORBIDDEN_TOOLS)}")
    if route.get("mcp_servers") != []:
        raise D1Error("route must require strict-empty MCP servers")

    isolation = route.get("settings_isolation", {})
    if (not isolation.get("isolated_settings") or isolation.get("isolated_home") is not False
            or not isolation.get("isolated_tmp") or isolation.get("provider_auth_home") != "operator"):
        raise D1Error("route must isolate settings/tmp while preserving operator authentication home")
    if isolation.get("global_settings_mutation_allowed") is not False:
        raise D1Error("route must prohibit global settings mutation")
    if isolation.get("safe_mode") is not True or isolation.get("session_persistence") is not False:
        raise D1Error("route must require safe mode and disabled session persistence")

    if root is not None:
        repo_root = Path(root).resolve()
        policy = derive_policy_claude_model(repo_root)
        if route.get("model") != policy["model"]:
            raise D1Error(f"descriptor model '{route.get('model')}' does not match source policy derived model '{policy['model']}'")

        identity_sources = descriptor.get("identity_sources", [])
        expected = descriptor.get("source_sha256", {})
        if set(identity_sources) != set(expected):
            raise D1Error("identity_sources must match source_sha256 keys")
        for rel in identity_sources:
            src = repo_root / rel
            if not src.is_file() or src.is_symlink():
                raise D1Error(f"identity source missing: {rel}")
            if _sha256(src.read_bytes()) != expected[rel]:
                raise D1Error(f"identity source {rel} digest mismatch")
        fixture_info = descriptor.get("fixture", {})
        fpath = repo_root / fixture_info.get("path", "")
        if not fpath.is_file() or fpath.is_symlink():
            raise D1Error("probe fixture missing")
        if _sha256(fpath.read_bytes()) != fixture_info.get("sha256"):
            raise D1Error("probe fixture digest mismatch")
    else:
        if not route.get("model"):
            raise D1Error("route model missing")


def derive_d1_route(descriptor: Mapping[str, Any], root: Path | None = None) -> dict[str, Any]:
    validate_descriptor(descriptor, root=root)
    r = copy.deepcopy(descriptor["route"])
    return {
        "provider": r["provider"],
        "profile": r["profile"],
        "model": r["model"],
        "binding_id": r.get("binding_id", ALLOWED_BINDING_ID),
        "roles": list(r["roles"]),
        "allowed_native_tools": list(r["allowed_native_tools"]),
        "forbidden_tools": list(r["forbidden_tools"]),
        "mcp_servers": list(r["mcp_servers"]),
        "settings_isolation": dict(r["settings_isolation"]),
        "probe_id": PROBE_ID,
    }


def extract_fixture_nonce(fixture_data: bytes) -> str:
    for line in fixture_data.splitlines():
        line_str = line.decode("utf-8", "replace").strip()
        if line_str.startswith("D1-PROBE-NONCE:"):
            parts = line_str.split(":", 1)
            nonce = parts[1].strip()
            if len(nonce) == 64 and HEX_64_RE.match(nonce):
                return nonce
    raise D1Error("D1-PROBE-NONCE marker not found in fixture bytes")


def materialize_probe(descriptor: Mapping[str, Any], destination_dir: Path, *, filename: str = "d1_probe_target.txt", root: Path | None = None) -> tuple[Path, str]:
    dest = Path(destination_dir)
    if not dest.is_absolute() or dest.resolve() != dest:
        raise ValueError("destination must be absolute physical path")
    dest.mkdir(parents=True, exist_ok=True, mode=0o700)
    repo_root = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    info = descriptor["fixture"]
    data = (repo_root / info["path"]).read_bytes()
    if _sha256(data) != info["sha256"]:
        raise D1Error("source fixture corrupted")
    target = dest / filename
    _write_private_bytes(target, data)

    nonce = extract_fixture_nonce(data)
    receipt = {
        "schema": "apg.d1-probe-receipt/v1",
        "probe_id": PROBE_ID,
        "path": str(target),
        "bytes": len(data),
        "sha256": _sha256(data),
        "nonce_sha256": _sha256(nonce.encode("utf-8")),
    }
    _write_private_json(dest / "probe-receipt.json", receipt)
    return target, nonce


def build_d1_prompt(fixture_path: Path, root: Path | None = None) -> bytes:
    """Build answer-neutral prompt for D1 probe.
    Does NOT include the expected nonce or answer in prompt bytes!
    """
    return (
        f"You are an independent Work Reviewer executing verification probe {PROBE_ID}.\n\n"
        f"Your task is to inspect the designated run-owned fixture file using the native Read tool.\n"
        f"Target file path: {os.fspath(fixture_path)}\n\n"
        f"Read the file using the native Read tool. Locate the exact D1-PROBE-NONCE marker value inside the file.\n"
        f"Then, emit a structured JSON response adhering to schema \"{RESPONSE_SCHEMA}\":\n\n"
        f"```json\n"
        f"{{\n  \"schema\": \"{RESPONSE_SCHEMA}\",\n  \"probe_id\": \"{PROBE_ID}\",\n  \"nonce\": \"<nonce-from-file>\",\n"
        f"  \"summary\": \"Verified native Read of probe fixture file.\"\n}}\n```\n\n"
        f"Do not modify any files. Do not invoke shell or mutation tools.\n"
    ).encode("utf-8")


def compute_authority_digest(authority: Mapping[str, Any]) -> str:
    """Compute canonical authority digest over all authority fields except authority_digest."""
    auth_copy = {k: v for k, v in authority.items() if k != "authority_digest"}
    return _sha256(_canonical_bytes(auth_copy))


def validate_d1_authority(authority: Mapping[str, Any], *, expected_commit: str | None = None,
                          expected_tree: str | None = None, expected_source_identity: str | None = None,
                          expected_descriptor_digest: str | None = None, expected_custody_root: str | None = None,
                          expected_evidence_root: str | None = None, root: Path | None = None) -> None:
    if not isinstance(authority, Mapping):
        raise D1AuthorityError("authority record must be a mapping")
    schema = authority.get("schema")
    if schema not in (AUTHORITY_SCHEMA, LIVE_AUTHORITY_SCHEMA, INSTRUMENTED_AUTHORITY_SCHEMA):
        raise D1AuthorityError(f"unsupported authority schema: {schema}")
    if authority.get("probe_id") != PROBE_ID:
        raise D1AuthorityError(f"authority probe_id must be {PROBE_ID}")
    if authority.get("max_starts") != 1:
        raise D1AuthorityError("authority max_starts must be 1")
    if authority.get("replay_prohibited") is not True:
        raise D1AuthorityError("replay_prohibited must be True")

    aid = authority.get("authority_id")
    if not isinstance(aid, str) or not aid.strip() or not AUTHORITY_ID_RE.match(aid):
        raise D1AuthorityError(f"authority authority_id invalid format: {aid!r}")

    attempt_id = authority.get("attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id.strip() or not ATTEMPT_ID_RE.match(attempt_id):
        raise D1AuthorityError(f"authority attempt_id invalid format: {attempt_id!r}")

    commit = authority.get("accepted_commit", "")
    tree = authority.get("accepted_tree", "")
    if not isinstance(commit, str) or not HEX_40_RE.match(commit):
        raise D1AuthorityError("accepted_commit must be exactly 40 lowercase hex")
    if not isinstance(tree, str) or not HEX_40_RE.match(tree):
        raise D1AuthorityError("accepted_tree must be exactly 40 lowercase hex")
    if expected_commit and commit != expected_commit:
        raise D1AuthorityError(f"commit mismatch: expected {expected_commit}, got {commit}")
    if expected_tree and tree != expected_tree:
        raise D1AuthorityError(f"tree mismatch: expected {expected_tree}, got {tree}")

    sid = authority.get("source_identity", "")
    dsha = authority.get("descriptor_sha256", "")
    if not isinstance(sid, str) or not HEX_64_RE.match(sid):
        raise D1AuthorityError("source_identity must be exactly 64 lowercase hex")
    if not isinstance(dsha, str) or not HEX_64_RE.match(dsha):
        raise D1AuthorityError("descriptor_sha256 must be exactly 64 lowercase hex")
    if expected_source_identity and sid != expected_source_identity:
        raise D1AuthorityError("source identity mismatch")
    if expected_descriptor_digest and dsha != expected_descriptor_digest:
        raise D1AuthorityError("descriptor digest mismatch")

    croot_str = authority.get("custody_root")
    eroot_str = authority.get("evidence_root")
    if not isinstance(croot_str, str) or not croot_str.strip():
        raise D1AuthorityError("authority custody_root must be specified")
    if not isinstance(eroot_str, str) or not eroot_str.strip():
        raise D1AuthorityError("authority evidence_root must be specified")

    croot = Path(croot_str)
    eroot = Path(eroot_str)
    if not croot.is_absolute() or croot.resolve() != croot or croot.is_symlink():
        raise D1AuthorityError(f"custody_root must be physical absolute non-symlink path: {croot_str}")
    if not eroot.is_absolute() or eroot.resolve() != eroot or eroot.is_symlink():
        raise D1AuthorityError(f"evidence_root must be physical absolute non-symlink path: {eroot_str}")

    try:
        eroot.resolve().relative_to(croot.resolve())
    except ValueError:
        raise D1AuthorityError("evidence_root must be located beneath custody_root with no escape")

    repo_root = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    for rpath, name in ((croot, "custody_root"), (eroot, "evidence_root")):
        if rpath == repo_root or rpath.is_relative_to(repo_root) or repo_root.is_relative_to(rpath):
            raise D1AuthorityError(f"{name} must not overlap with repository root: {rpath}")

    if expected_custody_root and str(croot.resolve()) != str(Path(expected_custody_root).resolve()):
        raise D1AuthorityError("custody root mismatch")
    if expected_evidence_root and str(eroot.resolve()) != str(Path(expected_evidence_root).resolve()):
        raise D1AuthorityError("evidence root mismatch")

    given_ad = authority.get("authority_digest")
    computed_ad = compute_authority_digest(authority)
    if given_ad is not None:
        if not isinstance(given_ad, str) or not HEX_64_RE.match(given_ad):
            raise D1AuthorityError("authority_digest must be exactly 64 lowercase hex")
        if given_ad != computed_ad:
            raise D1AuthorityError(f"authority_digest mismatch: expected {computed_ad}, got {given_ad}")

    assert_structural_non_holdout(authority, root=repo_root)


def derive_attempt_key(authority: Mapping[str, Any], source_identity: str) -> str:
    """Derive attempt key binding canonical custody-root path, authority_digest,
    PROBE_ID, source_identity, and attempt_id.
    """
    auth_digest = authority.get("authority_digest") or compute_authority_digest(authority)
    croot_str = str(Path(authority["custody_root"]).resolve())
    key_str = f"{croot_str}:{auth_digest}:{PROBE_ID}:{source_identity}:{authority['attempt_id']}"
    return _sha256(key_str.encode("utf-8"))


def record_attempt_consumption(
    custody_root: Path,
    evidence_root: Path,
    authority: Mapping[str, Any],
    source_identity: str,
    pre_provider_evidence: Mapping[str, Any],
    *,
    transport_kind: str = PRODUCTION_TRANSPORT_KIND,
    launch_contract_digest: str | None = None,
    provider_start_receipt_digest: str | None = None,
    guard_receipt_digest: str | None = None,
) -> tuple[Path, Path]:
    """Immediately before provider start, atomically create and fsync the consumed ledger record
    in the manager-bound custody root and the attempt state in the evidence root.
    """
    croot = Path(custody_root).resolve()
    edir = Path(evidence_root).resolve()

    ledger_dir = croot / "consumed-attempts"
    ledger_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    attempt_key = derive_attempt_key(authority, source_identity)
    ledger_file = ledger_dir / f"{attempt_key}.json"

    if ledger_file.exists() or ledger_file.is_symlink():
        raise D1AttemptError(f"attempt already consumed in manager-bound custody root; replay refused: {attempt_key}")

    auth_digest = authority.get("authority_digest") or compute_authority_digest(authority)
    transport_class = "production-provider" if transport_kind == PRODUCTION_TRANSPORT_KIND else "instrumented-provider-free"

    status = "start_finalized" if provider_start_receipt_digest else "prelaunch_consumed"
    ledger_record = {
        "schema": ATTEMPT_LEDGER_SCHEMA,
        "probe_id": PROBE_ID,
        "status": status,
        "authority_schema": authority.get("schema", AUTHORITY_SCHEMA),
        "authority_id": authority["authority_id"],
        "authority_digest": auth_digest,
        "attempt_id": authority["attempt_id"],
        "attempt_key": attempt_key,
        "source_identity": source_identity,
        "custody_root": str(croot),
        "evidence_root": str(edir),
        "transport_kind": transport_kind,
        "transport_class": transport_class,
        "launch_contract_digest": launch_contract_digest,
        "provider_start_receipt_digest": provider_start_receipt_digest,
        "guard_receipt_digest": guard_receipt_digest,
        "pid": None,
        "process_group": None,
        "session_id": None,
        "starts_consumed": 1,
        "consumed_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_private_json(ledger_file, ledger_record)
    ledger_sha256 = _sha256(_canonical_bytes(ledger_record))

    state_path = edir / "attempt-state.json"
    if state_path.exists() or state_path.is_symlink():
        raise D1AttemptError(f"attempt already started or consumed in evidence root; replay refused: {state_path}")

    state_record = {
        "schema": ATTEMPT_STATE_SCHEMA,
        "probe_id": PROBE_ID,
        "authority_id": authority["authority_id"],
        "authority_digest": auth_digest,
        "attempt_id": authority["attempt_id"],
        "attempt_key": attempt_key,
        "starts_consumed": 1,
        "status": "in_flight",
        "transport_kind": transport_kind,
        "transport_class": transport_class,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "custody_ledger_file": str(ledger_file),
        "custody_ledger_sha256": ledger_sha256,
        "pre_provider_evidence": dict(pre_provider_evidence),
    }
    _write_private_json(state_path, state_record)
    return ledger_file, state_path


def finalize_consumed_attempt(
    ledger_file: Path,
    state_path: Path,
    *,
    provider_start_receipt_digest: str,
    pid: int,
    process_group: int | None = None,
    session_id: int | None = None,
    guard_receipt_digest: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Durably transition the consumed-attempt ledger from prelaunch_consumed to start_finalized."""
    if not ledger_file.is_file() or ledger_file.is_symlink():
        raise D1AttemptError(f"custody ledger missing: {ledger_file}")
    ledger_record = json.loads(ledger_file.read_bytes())
    if ledger_record.get("schema") != ATTEMPT_LEDGER_SCHEMA:
        raise D1AttemptError("custody ledger schema mismatch")
    if ledger_record.get("status") != "prelaunch_consumed":
        raise D1AttemptError(f"cannot finalize attempt in status {ledger_record.get('status')}")
    ledger_record["status"] = "start_finalized"
    ledger_record["finalized_at"] = datetime.now(timezone.utc).isoformat()
    ledger_record["provider_start_receipt_digest"] = provider_start_receipt_digest
    ledger_record["pid"] = pid
    ledger_record["process_group"] = process_group
    ledger_record["session_id"] = session_id
    if guard_receipt_digest is not None:
        ledger_record["guard_receipt_digest"] = guard_receipt_digest
    _atomic_update_json(ledger_file, ledger_record)
    new_ledger_sha = _sha256(_canonical_bytes(ledger_record))

    if state_path.is_file() and not state_path.is_symlink():
        state_record = json.loads(state_path.read_bytes())
        if state_record.get("schema") == ATTEMPT_STATE_SCHEMA:
            state_record["custody_ledger_sha256"] = new_ledger_sha
            _atomic_update_json(state_path, state_record)
    return ledger_record, new_ledger_sha


def record_attempt_finish(evidence_root: Path, final_status: str, *, error: str | None = None) -> None:
    edir = Path(evidence_root).resolve()
    state_path = edir / "attempt-state.json"
    if not state_path.is_file() or state_path.is_symlink():
        raise D1AttemptError("attempt-state.json missing")
    data = json.loads(state_path.read_bytes())
    if data.get("schema") != ATTEMPT_STATE_SCHEMA or data.get("starts_consumed") != 1:
        raise D1AttemptError("corrupt attempt state")
    data["status"] = final_status
    data["finished_at"] = datetime.now(timezone.utc).isoformat()
    if error:
        data["error"] = error
    _atomic_update_json(state_path, data)


def capture_git_state(root: Path) -> dict[str, Any]:
    try:
        h = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, check=True, text=True).stdout.strip()
        t = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD^{tree}"], capture_output=True, check=True, text=True).stdout.strip()
        s = subprocess.run(["git", "-C", str(root), "status", "--porcelain=v1", "-z"], capture_output=True, check=True).stdout
        idx = root / ".git/index"
        return {
            "head": h,
            "tree": t,
            "index_sha256": _sha256(idx.read_bytes()) if idx.is_file() else None,
            "status_sha256": _sha256(s),
            "dirty": bool(s),
        }
    except Exception as exc:
        raise D1Error(f"git capture failed: {exc}") from exc


def capture_settings_state(settings_or_root: Any = None, *, root: Path | None = None,
                           isolated_settings: bool = True,
                           settings_file: Path | None = None,
                           isolated_home: Path | None = None,
                           auth_context: Mapping[str, str] | None = None) -> dict[str, Any]:
    if isinstance(settings_or_root, (str, Path)):
        if root is None:
            root = Path(settings_or_root)
    repo = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    sources: dict[str, Any] = {}

    try:
        from claude_vc_profile import canonical_settings_path
        canonical_path = settings_file or canonical_settings_path(repo)
    except Exception:
        canonical_path = settings_file or (repo / "claude/settings.json")

    if canonical_path.is_file() and not canonical_path.is_symlink():
        data = canonical_path.read_bytes()
        sources["canonical_settings"] = {
            "path": str(canonical_path.resolve()),
            "status": "present",
            "bytes": len(data),
            "sha256": _sha256(data),
        }
    else:
        sources["canonical_settings"] = {
            "path": str(canonical_path.resolve()),
            "status": "absent",
            "bytes": 0,
            "sha256": None,
        }

    try:
        from claude_vc_profile import read_only_contract
        contract = read_only_contract(repo, ALLOWED_PROFILE)
        sources["isolated_setting_sources"] = contract.get("setting_sources", "")
    except Exception:
        sources["isolated_setting_sources"] = ""
    sources["mode"] = "static"
    sources["isolation"] = {
        "isolated_settings": isolated_settings,
        "isolated_home": auth_context is None,
        "provider_auth_home": "operator" if auth_context else "disposable",
        "isolated_tmp": True,
        "global_settings_mutation_allowed": False,
    }

    if auth_context is not None:
        from .d1_auth import settings_snapshot
        sources["home_settings"] = settings_snapshot(auth_context)
    elif isolated_home is not None:
        home_path = Path(isolated_home).resolve()
        claude_home_settings = home_path / ".claude/settings.json"
        if claude_home_settings.is_file() and not claude_home_settings.is_symlink():
            d = claude_home_settings.read_bytes()
            sources["home_settings"] = {"path": str(claude_home_settings), "sha256": _sha256(d), "bytes": len(d)}
        else:
            sources["home_settings"] = {"path": str(claude_home_settings), "status": "absent"}

    sources_bytes = _canonical_bytes(sources)
    return {
        "schema": "apg.d1-settings-evidence/v1",
        "sha256": _sha256(sources_bytes),
        "sources": sources,
        "isolated": isolated_settings,
    }


def capture_runtime_state(manifest: Mapping[str, Any] | None) -> dict[str, Any]:
    if manifest is None:
        return {
            "status": "not-supplied",
            "runtime_manifest_file_sha256": None,
            "runtime_manifest_sealed_sha256": None,
            "lifecycle_state": "unsealed",
        }
    from .runtime_manifest import manifest_digest
    return {
        "status": "supplied",
        "runtime_manifest_file_sha256": _sha256(_json_bytes(manifest)),
        "runtime_manifest_sealed_sha256": manifest_digest(manifest),
        "lifecycle_state": manifest.get("lifecycle", {}).get("state", "unsealed"),
    }


def build_d1_runtime_manifest(
    root: Path,
    isolated_home: Path,
    isolated_tmp: Path,
    fake_executable: Path | None = None,
    *,
    is_instrumented: bool = False,
    executable_selection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Capture and seal a real complete v2 runtime manifest for D1 qualification."""
    from . import runtime_manifest
    repo = Path(root).resolve()

    real_claude = (executable_selection["executables"]["claude"]["physical"]
                   if executable_selection else shutil.which("claude"))
    if real_claude:
        prod_claude_exec = Path(real_claude).resolve()
    else:
        prod_claude_exec = (repo / "bin/claude-profile").resolve()

    target_claude = Path(fake_executable).resolve() if fake_executable else prod_claude_exec

    real_codex = shutil.which("codex")
    if real_codex:
        prod_codex_exec = Path(real_codex).resolve()
    else:
        prod_codex_exec = Path(sys.executable).resolve()

    git = Path(shutil.which("git") or "/usr/bin/git").resolve()
    py = Path(executable_selection["executables"]["python3"]["physical"]
              if executable_selection else shutil.which("python3") or sys.executable).resolve()

    def _find_cmd(name: str) -> tuple[Path, list[str]]:
        args = ["version"] if name == "go" else ["--version"]
        if executable_selection and name in executable_selection["executables"]:
            return Path(executable_selection["executables"][name]["physical"]), args
        if name in ("python", "python3"):
            return py, args
        if name == "apgr":
            apgr_bin = repo / "bin/apgr"
            if apgr_bin.is_file():
                return apgr_bin.resolve(), args
        w = shutil.which(name)
        if w:
            return Path(w).resolve(), args
        return git, ["--version"]

    commands = {
        name: _find_cmd(name)
        for name in runtime_manifest.REQUIRED_COMMANDS
    }
    real_agy = shutil.which("agy") or shutil.which("antigravity")
    if real_agy:
        prod_agy_exec = Path(real_agy).resolve()
        agy_decl = (prod_agy_exec, ["--version"])
    else:
        agy_decl = {"available": False}

    providers = {
        "claude": (target_claude, ["--version"]),
        "codex": (prod_codex_exec, ["--version"]),
        "antigravity": agy_decl,
    }
    source = repo / "README.md"
    groups = {g: [source] for g in runtime_manifest.REQUIRED_GROUPS}
    routes = {"normal-final-review": "claude-normal-final-review"}
    absent = [Path(isolated_tmp) / "absent-setting"]
    env = {
        "home": str(isolated_home),
        "temp_root": str(isolated_tmp),
        "values": {"CGO_ENABLED": "1"},
        "CGO_ENABLED": "1",
    }

    return runtime_manifest.capture_and_seal(
        providers=providers,
        commands=commands,
        groups=groups,
        routes=routes,
        absent_settings=absent,
        environment=env,
    )


def capture_executable_evidence(
    root: Path,
    *,
    runtime_manifest: Mapping[str, Any] | None = None,
    executable_path: Path | None = None,
    cli_version: str | None = None,
    is_instrumented: bool = False,
    executable_selection: Mapping[str, Any] | None = None,
    preflight: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    repo = Path(root).resolve()
    launcher = repo / "bin/claude-profile"
    wrapper = repo / "libexec/claude_vc_profile.py"

    real_cli = (executable_selection["executables"]["claude"]["physical"]
                if executable_selection else shutil.which("claude"))
    real_exec = Path(real_cli).resolve() if real_cli else None
    real_ver = preflight["claude_version"] if preflight else None
    if real_exec and not executable_selection:
        from claude_model_catalog import probe_claude_version
        v, st = probe_claude_version(real_exec)
        if st == "available":
            real_ver = v

    if executable_path is not None:
        executed = Path(executable_path).resolve()
    else:
        executed = real_exec or launcher.resolve()

    version = cli_version
    if version is None and is_instrumented:
        version = f"{D1_CLAUDE_CLI_VERSION} (fake-provider-free seam)"
    elif version is None:
        if real_ver is None:
            raise D1Error("production claude CLI version cannot be probed; fallback constants prohibited")
        version = real_ver

    return {
        "logical_launcher_path": str(launcher),
        "launcher_sha256": _sha256(launcher.read_bytes()) if launcher.is_file() else None,
        "wrapper_path": str(wrapper),
        "wrapper_sha256": _sha256(wrapper.read_bytes()) if wrapper.is_file() else None,
        "physical_executable": str(executed),
        "physical_executable_sha256": _sha256(executed.read_bytes()) if executed.is_file() else None,
        "cli_version": version,
        "production_executable": str(real_exec) if real_exec else None,
        "production_executable_sha256": _sha256(real_exec.read_bytes()) if real_exec and real_exec.is_file() else None,
        "production_cli_version": real_ver,
        "is_instrumented": is_instrumented,
        **({"executable_selection": dict(executable_selection), "preflight": dict(preflight or {})}
           if executable_selection else {}),
    }


def capture_isolation_roots(custody_root: Path, evidence_root: Path, run_dir: Path,
                            home_dir: Path | None, tmp_dir: Path, probe_dir: Path | None = None,
                            repo_root: Path | None = None,
                            disposable_root: Path | None = None) -> dict[str, Any]:
    repo = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    roots: dict[str, Any] = {}
    check_list = [
        ("custody_root", custody_root),
        ("evidence_root", evidence_root),
        ("run_dir", run_dir),
        ("isolated_tmp", tmp_dir),
    ]
    if home_dir is not None:
        check_list.append(("isolated_home", home_dir))
    if probe_dir is not None:
        check_list.append(("probe_dir", probe_dir))
    if disposable_root is not None:
        check_list.append(("disposable_root", disposable_root))
    for name, p in check_list:
        p_res = Path(p).resolve()
        if p_res == repo or p_res.is_relative_to(repo) or repo.is_relative_to(p_res):
            raise D1Error(f"isolation root overlaps with repository root: {name} at {p_res}")
        st = p_res.stat() if p_res.exists() else None
        roots[name] = {
            "path": str(p_res),
            "is_dir": p_res.is_dir() if p_res.exists() else False,
            "is_symlink": p.is_symlink(),
            "device": st.st_dev if st else None,
            "inode": st.st_ino if st else None,
            "mode": stat.S_IMODE(st.st_mode) if st else None,
        }
    return roots


def d1_outer_argv(root: Path) -> list[str]:
    from .d1_auth import FIXED_OPTIONS
    argv = provider.build_argv(provider.Endpoint("claude", "normal-final-review"), "reviewer", root)
    index = argv.index("--read-only") + 1
    return [*argv[:index], "--read-only-tools", "Read", *FIXED_OPTIONS, *argv[index:]]


def derive_expected_launch_contract(
    root: Path,
    *,
    descriptor: Mapping[str, Any],
    roots: Mapping[str, Any],
    settings_evidence: Mapping[str, Any],
    argv: Sequence[str] | None = None,
) -> dict[str, Any]:
    repo = Path(root).resolve()
    from claude_vc_profile import read_only_contract
    desc_route = descriptor["route"]
    model_info = derive_policy_claude_model(repo)
    try:
        ro_contract = read_only_contract(repo / "claude", desc_route["profile"])
    except Exception:
        ro_contract = read_only_contract(repo, desc_route["profile"])

    if argv is None:
        expected_argv = d1_outer_argv(repo)
    else:
        expected_argv = list(argv)

    return {
        "schema": LAUNCH_CONTRACT_SCHEMA,
        "probe_id": PROBE_ID,
        "provider": desc_route["provider"],
        "profile": desc_route["profile"],
        "model": model_info["model"],
        "roles": list(desc_route["roles"]),
        "binding_id": desc_route.get("binding_id", ALLOWED_BINDING_ID),
        "permission_mode": ro_contract["permission_mode"],
        "startup_tools": sorted(ALLOWED_NATIVE_TOOLS),
        "mcp_servers": list(desc_route.get("mcp_servers", [])),
        "argv": expected_argv,
        "settings_sources": dict(settings_evidence.get("sources", {})),
        "roots": {k: v["path"] for k, v in roots.items()},
    }


def build_expected_launch_contract(*, route: Mapping[str, Any], argv: Sequence[str],
                                   roots: Mapping[str, Any], settings_evidence: Mapping[str, Any],
                                   root: Path | None = None, descriptor: Mapping[str, Any] | None = None) -> dict[str, Any]:
    repo = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
    desc = descriptor or load_descriptor(root=repo)
    return derive_expected_launch_contract(repo, descriptor=desc, roots=roots, settings_evidence=settings_evidence, argv=argv)


def _launching_python() -> str:
    return sys.executable


def _executable_fact(lookup: str | None) -> dict[str, str]:
    if not lookup:
        raise D1Error("required D1 executable unavailable")
    path = Path(lookup).resolve()
    if not path.is_file() or not os.access(path, os.X_OK):
        raise D1Error("required D1 executable is not an executable file")
    return {"lookup": str(Path(lookup).absolute()), "physical": str(path),
            "sha256": _sha256(path.read_bytes())}


def select_d1_production_executables(*, python_executable: str | None = None,
                                     search_path: str | None = None) -> dict[str, Any]:
    """Bind existing launching-shell programs before closing the child environment."""
    search = os.environ.get("PATH", "") if search_path is None else search_path
    python = _executable_fact(python_executable or _launching_python())
    python_alias = Path(python["physical"]).parent / "python3"
    if not python_alias.is_file() or python_alias.resolve() != Path(python["physical"]):
        raise D1Error("launching interpreter has no matching python3 in its physical directory")
    claude = _executable_fact(shutil.which("claude", path=search))
    executables = {"python3": python, "claude": claude}
    with Path(claude["physical"]).open("rb") as stream:
        first = stream.readline(4096)
    if first.startswith(b"#!"):
        words = shlex.split(first[2:].decode("utf-8").strip())
        if not words or not Path(words[0]).is_absolute():
            raise D1Error("unsupported provider interpreter")
        _executable_fact(words[0])
        if words[0] == "/usr/bin/env":
            args = words[1:]
            if args[:1] == ["-S"]:
                args = args[1:]
            if not args or args[0].startswith("-") or "/" in args[0] or "=" in args[0]:
                raise D1Error("unsupported env provider interpreter")
            name = args[0]
            fact = _executable_fact(shutil.which(name, path=search))
            if name in executables and fact["physical"] != executables[name]["physical"]:
                raise D1Error("provider interpreter conflicts with selected executable")
            executables[name] = fact
    selection = {"schema": EXECUTABLE_SELECTION_SCHEMA, "executables": executables}
    selection["path_entries"] = list(dict.fromkeys(
        str(Path(fact["physical"]).parent) for fact in executables.values()))
    d1_production_path(selection)
    return selection


def d1_production_path(selection: Mapping[str, Any] | None) -> str:
    """Re-derive PATH from the retained selection, never from ambient readback state."""
    if not isinstance(selection, Mapping) or selection.get("schema") != EXECUTABLE_SELECTION_SCHEMA:
        raise D1Error("production executable selection missing or invalid")
    executables = selection.get("executables")
    if not isinstance(executables, dict) or not {"python3", "claude"} <= executables.keys():
        raise D1Error("production executable selection incomplete")
    # JSON custody sorts keys, so directory order must not depend on mapping order.
    names = ["python3", "claude", *sorted(set(executables) - {"python3", "claude"})]
    entries = []
    for name in names:
        fact = executables[name]
        if not isinstance(fact, dict):
            raise D1Error("invalid executable fact")
        for field in ("lookup", "physical"):
            value = fact.get(field)
            if not isinstance(value, str) or not Path(value).is_absolute() or os.pathsep in value:
                raise D1Error("invalid executable path")
        if not isinstance(fact.get("sha256"), str) or not HEX_64_RE.fullmatch(fact["sha256"]):
            raise D1Error("invalid executable digest")
        entries.append(str(Path(fact["physical"]).parent))
    entries = list(dict.fromkeys(entries))
    if selection.get("path_entries") != entries:
        raise D1Error("executable selection PATH entries differ from bound files")
    return os.pathsep.join(dict.fromkeys([*entries, *D1_SYSTEM_PATH]))


def verify_d1_selected_executables(selection: Mapping[str, Any], env: Mapping[str, str]) -> None:
    if env["PATH"] != d1_production_path(selection):
        raise D1Error("selected executable PATH mismatch")
    for name, fact in selection["executables"].items():
        lookup = shutil.which(name, path=env["PATH"])
        if not lookup or str(Path(lookup).resolve()) != fact["physical"]:
            raise D1Error("closed PATH executable differs from selection: " + name)
        if name == "claude" and lookup != fact["physical"]:
            raise D1Error("closed PATH claude must launch the physical executable")
        if _sha256(Path(lookup).read_bytes()) != fact["sha256"]:
            raise D1Error("selected executable digest changed: " + name)


def preflight_d1_production_executables(root: Path, selection: Mapping[str, Any],
                                       env: Mapping[str, str]) -> dict[str, Any]:
    """Bounded interpreter and wrapper doctor checks only; never inference or sign-in."""
    try:
        verify_d1_selected_executables(selection, env)
        if not shutil.which("bash", path=env["PATH"]):
            raise D1Error("wrapper bash unavailable")
        result = subprocess.run(
            ["/usr/bin/env", "python3", "-I", "-c",
             "import json,sys; print(json.dumps(list(sys.version_info[:3])))"],
            env=dict(env), capture_output=True, text=True, timeout=10, check=True)
        version = json.loads(result.stdout)
        if not isinstance(version, list) or len(version) != 3 or not all(type(v) is int for v in version):
            raise D1Error("invalid interpreter version response")
        if tuple(version) < (3, 10):
            raise D1Error("D1 interpreter below required Python 3.10")
        doctor = subprocess.run(
            [str(Path(root) / "bin/claude-profile"), "doctor", "normal-final-review"],
            env=dict(env), capture_output=True, text=True, timeout=30, check=True)
        report = json.loads(doctor.stdout)
        # The generic doctor's probe intentionally removes HOME. Some selected
        # launchers report a different version there than in D1's operator
        # context. Bind the exact pin to the same executable/environment D1
        # launches, while retaining the independent doctor compatibility gate.
        selected_version = subprocess.run(
            [selection["executables"]["claude"]["physical"], "--version"],
            env=dict(env), cwd=env["TMPDIR"], capture_output=True, text=True,
            timeout=15, check=True)
        version_match = re.fullmatch(
            r"([0-9]+\.[0-9]+\.[0-9]+)(?: \(Claude Code\))?\s*",
            selected_version.stdout)
        observed_version = version_match.group(1) if version_match else None
        if (observed_version != D1_CLAUDE_CLI_VERSION
                or not report.get("profiles")
                or any(p.get("compatibilityStatus") not in {"compatible", "not-required"}
                       for p in report["profiles"])):
            raise D1Error("D1 Claude version must match " + D1_CLAUDE_CLI_VERSION)
        from .d1_auth import check_status
        auth_status = check_status(selection["executables"]["claude"]["physical"], env)
        return {"python_version": version, "claude_version": observed_version,
                "doctor_claude_version": report.get("observedClaudeCodeVersion"),
                "auth_status": auth_status}
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise D1Error("D1 executable/auth preflight failed: " + str(error)) from error


def build_d1_launch_environment(
    *,
    home_dir: Path,
    tmp_dir: Path,
    fake_executable: Path | None = None,
    config_path: Path | None = None,
    is_instrumented: bool = False,
    executable_selection: Mapping[str, Any] | None = None,
    auth_context: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Construct closed allowlisted execution environment from scratch without ambient leakage."""
    home_resolved = str(Path(home_dir).resolve())
    tmp_resolved = str(Path(tmp_dir).resolve())

    if is_instrumented and fake_executable:
        fake_bin = str(Path(fake_executable).parent.resolve())
        safe_system = [p for p in ["/bin", "/usr/bin"] if not (Path(p) / "claude").exists()]
        closed_path = os.pathsep.join([fake_bin, *safe_system])
    else:
        closed_path = d1_production_path(executable_selection)

    env: dict[str, str] = {
        "PATH": closed_path,
        "HOME": home_resolved,
        "TMPDIR": tmp_resolved,
        "TMP": tmp_resolved,
        "TEMP": tmp_resolved,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "APGR_MODEL_AUTHORITY": "source-defaults",
        "CLAUDE_CODE_SAFE_MODE": "1",
    }
    if auth_context is not None:
        from .d1_auth import validate_context
        env.update(validate_context(dict(auth_context)))
    if is_instrumented and config_path:
        env["APG_D1_CONFIG"] = str(Path(config_path).resolve())
    return env


def create_provider_start_receipt(
    *,
    authority: Mapping[str, Any],
    attempt_key: str,
    physical_executable: str,
    physical_executable_sha256: str | None,
    argv: Sequence[str],
    environment: Mapping[str, str],
    cwd: Path | str,
    transport_class: str,
    transport_kind: str,
    guard_receipt: Mapping[str, Any] | None = None,
    pid: int | None = None,
    process_group: int | None = None,
    session_id: int | None = None,
    source_identity: str | None = None,
    allowlist_environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Create a local custody consistency receipt from the launch owner."""
    auth_digest = authority.get("authority_digest") or compute_authority_digest(authority)
    actual_cwd = str(Path(cwd).resolve())
    clean_env = dict(allowlist_environment) if allowlist_environment is not None else dict(environment)
    rec = {
        "schema": PROVIDER_START_RECEIPT_SCHEMA,
        "probe_id": PROBE_ID,
        "authority_schema": authority.get("schema", AUTHORITY_SCHEMA),
        "authority_id": authority["authority_id"],
        "authority_digest": auth_digest,
        "attempt_id": authority["attempt_id"],
        "attempt_key": attempt_key,
        "source_identity": source_identity or authority.get("source_identity"),
        "physical_executable": str(physical_executable),
        "physical_executable_sha256": physical_executable_sha256,
        "exact_argv": [str(a) for a in argv],
        "argv_sha256": _sha256(_canonical_bytes([str(a) for a in argv])),
        "environment_digest": _sha256(_canonical_bytes(dict(environment))),
        "allowlist_environment": clean_env,
        "cwd": actual_cwd,
        "pid": pid,
        "process_group": process_group,
        "session_id": session_id,
        "transport_kind": transport_kind,
        "transport_class": transport_class,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "provider_guard_identity": guard_receipt.get("root_identity") if guard_receipt else None,
        "guard_receipt_digest": _sha256(_canonical_bytes(guard_receipt)) if guard_receipt else None,
    }
    return rec


def inspect_observed_surface(raw_stream: bytes, expected_route: Mapping[str, Any],
                             expected_contract: Mapping[str, Any] | None = None,
                             expected_argv: Sequence[str] | None = None) -> dict[str, Any]:
    """Inspect raw provider stream for startup native tools, MCP servers, permissionMode, and contract."""
    init_event = None
    subagent_stats = []
    nested_envelope = False
    unexpected_calls = set()
    for line in raw_stream.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line.decode("utf-8", "replace"))
            if isinstance(ev, dict) and ev.get("type") == "result" and "subagent_stats" in ev:
                subagent_stats.append(ev["subagent_stats"])
            if isinstance(ev, dict) and ev.get("type") in ("assistant", "user"):
                nested_envelope |= ev.get("parent_tool_use_id") is not None
            if isinstance(ev, dict) and ev.get("type") == "assistant":
                for block in ev.get("message", {}).get("content", []):
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        if block.get("name") != "Read":
                            unexpected_calls.add(str(block.get("name")))
                        caller = block.get("caller")
                        if isinstance(caller, dict) and caller.get("type") != "direct":
                            nested_envelope = True
            if isinstance(ev, dict) and ev.get("type") == "system" and (ev.get("subtype") == "init" or ev.get("event") == "init"):
                if init_event is None:
                    init_event = ev
        except Exception:
            continue

    if init_event is None:
        return {
            "valid": False,
            "failure_codes": ["INIT_EVENT_MISSING"],
            "tools": [],
            "extra_tools": [],
            "missing_tools": ["Read"],
            "mcp_servers": [],
            "permission_mode": None,
            "model": None,
        }

    observed_tools = list(init_event.get("tools", []))
    tools_set = set(observed_tools)
    extra_tools = sorted(tools_set - {"Read"})
    missing_tools = sorted({"Read"} - tools_set)
    mcp_servers = list(init_event.get("mcp_servers", []))
    permission_mode = init_event.get("permissionMode")
    model = init_event.get("model")

    from .d1_auth import surface_failures
    failure_codes = surface_failures(init_event, expected_contract)
    if unexpected_calls:
        failure_codes.append("FORBIDDEN_TOOL_CALL_OBSERVED")
    if nested_envelope or any(
        isinstance(stats, dict) and any(
            isinstance(stats.get(key), (int, float)) and stats[key] > 0
            for key in ("spawned", "max_depth")
        ) for stats in subagent_stats
    ):
        failure_codes.append("SUBAGENTS_OBSERVED")
    if any(not isinstance(stats, dict) or any(
        key in stats and (type(stats[key]) is not int or stats[key] < 0)
        for key in ("spawned", "max_depth")
    ) for stats in subagent_stats):
        failure_codes.append("SUBAGENT_STATS_INVALID")
    if extra_tools:
        failure_codes.append("FORBIDDEN_TOOLS_OBSERVED")
    if missing_tools:
        failure_codes.append("READ_TOOL_MISSING")
    if mcp_servers != []:
        failure_codes.append("MCP_SERVERS_NON_EMPTY")
    if permission_mode != "plan":
        failure_codes.append("PERMISSION_MODE_MISMATCH")
    if model != expected_route.get("model"):
        failure_codes.append("MODEL_MISMATCH")

    if expected_contract is not None:
        if expected_contract.get("profile") != ALLOWED_PROFILE:
            failure_codes.append("PROFILE_MISMATCH")
        if expected_contract.get("roles") != [ALLOWED_ROLE]:
            failure_codes.append("ROLE_MISMATCH")
        if expected_contract.get("binding_id") != ALLOWED_BINDING_ID:
            failure_codes.append("BINDING_ID_MISMATCH")
        if expected_contract.get("permission_mode") != ALLOWED_PERMISSION_MODE:
            failure_codes.append("PERMISSION_MODE_MISMATCH")
        if expected_argv is not None and expected_contract.get("argv") != list(expected_argv):
            failure_codes.append("ARGV_MISMATCH")

    return {
        "valid": len(failure_codes) == 0,
        "failure_codes": failure_codes,
        "tools": observed_tools,
        "extra_tools": extra_tools,
        "missing_tools": missing_tools,
        "mcp_servers": mcp_servers,
        "permission_mode": permission_mode,
        "model": model,
        "cli_version": init_event.get("claude_code_version"),
        "startup_inventory": {key: init_event.get(key) for key in ("skills", "agents", "plugins")},
        "terminal_subagent_stats": subagent_stats,
        "unexpected_tool_calls": sorted(unexpected_calls),
        "expected_argv": list(expected_argv) if expected_argv else None,
    }


def evaluate_d1_response(output: bytes | str | Mapping[str, Any], expected_nonce: str, *,
                          observation: Mapping[str, Any] | None = None,
                          fixture_bytes: bytes | None = None,
                          fixture_path: Path | None = None) -> dict[str, Any]:
    if observation is None or not isinstance(observation, Mapping):
        return {"status": "fail", "oracle_id": ORACLE_ID, "reason": "native_read_observation_missing"}
    reads = observation.get("reads", [])
    if not reads:
        return {"status": "fail", "oracle_id": ORACLE_ID, "reason": "no_native_read_observed"}

    if fixture_path is not None:
        expected_str = str(Path(fixture_path).resolve())
        def _extract_path(rd: Mapping[str, Any]) -> str:
            return (
                rd.get("file_path")
                or rd.get("path")
                or rd.get("input", {}).get("file_path")
                or rd.get("result", {}).get("structured_file", {}).get("filePath")
                or ""
            )
        found_path = any(
            str(Path(_extract_path(r)).resolve()) == expected_str
            for r in reads if _extract_path(r)
        )
        if not found_path:
            return {"status": "fail", "oracle_id": ORACLE_ID, "reason": "fixture_path_not_observed_in_reads"}

    if fixture_bytes is not None:
        expected_digest = _sha256(fixture_bytes)
        def _match_digest(rd: Mapping[str, Any]) -> bool:
            if rd.get("sha256") == expected_digest:
                return True
            raw_id = rd.get("result", {}).get("raw_identity", {})
            if isinstance(raw_id, dict) and raw_id.get("sha256") == expected_digest:
                return True
            auth_rec = rd.get("result", {}).get("authorized_recovery", {})
            if isinstance(auth_rec, dict) and auth_rec.get("sha256") == expected_digest:
                return True
            content = rd.get("content") or rd.get("result", {}).get("structured_file", {}).get("content")
            if content and _sha256(content.encode("utf-8")) == expected_digest:
                return True
            return False

        if not any(_match_digest(r) for r in reads):
            return {"status": "fail", "oracle_id": ORACLE_ID, "reason": "observed_content_digest_mismatch"}

    from .d1_response import response_candidate
    cand, reason = response_candidate(output)
    if not isinstance(cand, Mapping):
        return {"status": "fail", "oracle_id": ORACLE_ID, "reason": reason or "non-JSON response"}
    if cand.get("schema") != RESPONSE_SCHEMA:
        return {"status": "fail", "oracle_id": ORACLE_ID, "reason": "schema mismatch"}
    if cand.get("probe_id") != PROBE_ID:
        return {"status": "fail", "oracle_id": ORACLE_ID, "reason": "probe_id mismatch"}
    if cand.get("nonce") != expected_nonce:
        return {"status": "fail", "oracle_id": ORACLE_ID, "reason": "nonce mismatch",
                "observed_nonce": cand.get("nonce"), "expected_nonce": expected_nonce}

    return {"status": "pass", "oracle_id": ORACLE_ID, "observed_nonce": cand.get("nonce"), "summary": cand.get("summary", "")}


def derive_d1_record(*, authority: Mapping[str, Any], descriptor: Mapping[str, Any], descriptor_sha256: str,
                     source_identity_str: str, route: Mapping[str, Any], pre_evidence: Mapping[str, Any],
                     terminal: Mapping[str, Any], stdout: bytes, stderr: bytes, raw_stream: bytes,
                     stream_receipt: Mapping[str, Any], observation: Mapping[str, Any], delivery_data: Mapping[str, Any],
                     imported: Mapping[str, Any], oracle_result: Mapping[str, Any], post_git: Mapping[str, Any],
                     post_settings: Mapping[str, Any], post_runtime: Mapping[str, Any],
                     surface_contract: Mapping[str, Any],
                     execution_kind: str = FAKE_TRANSPORT_KIND,
                     executable_evidence: Mapping[str, Any] | None = None,
                     native_launch: Mapping[str, Any] | None = None) -> dict[str, Any]:
    reads = observation.get("reads", [])
    read_count = len(reads)

    from .d1_failure import capture_status, failure_reasons
    capture = capture_status(stream_receipt, raw_stream, terminal)
    failures = failure_reasons(
        imported, terminal, capture, surface_contract, reads, oracle_result,
        native_launch=native_launch, git_preserved=post_git == pre_evidence["git"],
        settings_preserved=post_settings["sha256"] == pre_evidence["settings"]["sha256"],
    )
    passed_all = (
        capture["status"] == "complete" and imported.get("provider_outcome") == "success"
        and isinstance(native_launch, Mapping)
        and terminal.get("exit_code") == 0 and not terminal.get("truncated", False)
        and surface_contract.get("valid", False) is True
        and read_count >= 1
        and oracle_result.get("status") == "pass"
        and post_git == pre_evidence["git"]
        and post_settings["sha256"] == pre_evidence["settings"]["sha256"]
    )

    if execution_kind in (PRODUCTION_TRANSPORT_KIND, "live-provider"):
        effective_kind = "live-provider"
        schema = LIVE_EVIDENCE_SCHEMA
        d1_status = "qualified" if passed_all else "failed"
        provider_free_seam_qualified = False
    elif execution_kind in (FAKE_TRANSPORT_KIND, "instrumented-provider-free"):
        effective_kind = "instrumented-provider-free"
        schema = INSTRUMENTED_EVIDENCE_SCHEMA
        d1_status = "not-run"
        provider_free_seam_qualified = passed_all
    else:
        raise ValueError(f"invalid execution_kind: {execution_kind}")

    record = {
        "schema": schema,
        "probe_id": PROBE_ID,
        "execution_kind": effective_kind,
        "attempt_id": authority["attempt_id"],
        "d1_status": d1_status,
        "provider_free_d1_seam_qualified": provider_free_seam_qualified,
        "provider_free_seam_qualified": provider_free_seam_qualified,
        "source_identity": source_identity_str,
        "descriptor_sha256": descriptor_sha256,
        "route": dict(route),
        "surface_contract": dict(surface_contract),
        "executable_evidence": dict(executable_evidence or {}),
        "pre_provider": pre_evidence,
        "post_provider": {
            "git": post_git,
            "settings": post_settings,
            "runtime": post_runtime,
            "stdout": {"bytes": len(stdout), "sha256": _sha256(stdout)},
            "stderr": {"bytes": len(stderr), "sha256": _sha256(stderr)},
            "raw_stream": {"bytes": len(raw_stream), "sha256": _sha256(raw_stream)},
            "stream_receipt": stream_receipt,
            "terminal": dict(terminal),
            "capture": capture,
            "provider_outcome": imported.get("provider_outcome"),
            "failure_reasons": failures,
            "native_reads": {"read_count": read_count, "event_count": len(observation.get("events", [])), "reads": reads},
            "delivery": delivery_data,
            "native_launch_custody": dict(native_launch) if native_launch is not None else None,
            "importer": imported,
            "oracle": oracle_result,
        },
        "invariants": {
            "git_preserved": post_git == pre_evidence["git"],
            "settings_preserved": post_settings["sha256"] == pre_evidence["settings"]["sha256"],
            "one_use_consumed": True,
            "no_holdout_overlap": True,
            "live_admission_blocked": not LIVE_ADMISSION_AVAILABLE,
        },
    }
    guard = ACTIVE_GUARD.get()
    if guard is not None:
        try:
            record["provider_guard"] = guard.receipt()
        except Exception:
            pass
    record["record_digest"] = compute_record_digest(record)
    return record


def compute_record_digest(record: Mapping[str, Any]) -> str:
    """Compute canonical record digest omitting record_digest."""
    rec_copy = copy.deepcopy(dict(record))
    rec_copy.pop("record_digest", None)
    return _sha256(_canonical_bytes(rec_copy))


def corroborate_child_startup_evidence(
    child_st: Mapping[str, Any],
    *,
    start_receipt: Mapping[str, Any],
    route: Mapping[str, Any],
) -> None:
    """Corroborate child-observed startup evidence against launch-owner facts."""
    if child_st.get("schema") != CHILD_STARTUP_EVIDENCE_SCHEMA:
        raise D1ReadbackError("child startup evidence schema mismatch")

    child_pid = child_st.get("pid")
    child_ppid = child_st.get("ppid")
    if not isinstance(child_pid, int) or child_pid <= 0:
        raise D1ReadbackError("valid PID required in child startup evidence")
    sr_pid = start_receipt.get("pid")
    if child_pid != sr_pid and child_ppid != sr_pid:
        raise D1ReadbackError(f"child startup PID {child_pid} / PPID {child_ppid} does not corroborate start receipt PID {sr_pid}")

    if str(Path(child_st.get("cwd", "")).resolve()) != str(Path(start_receipt.get("cwd", "")).resolve()):
        raise D1ReadbackError(f"child startup cwd mismatch with start receipt: {child_st.get('cwd')} vs {start_receipt.get('cwd')}")

    child_argv = child_st.get("argv", [])
    if not child_argv or str(Path(child_argv[0]).resolve()) != str(Path(start_receipt.get("physical_executable", "")).resolve()):
        raise D1ReadbackError("child startup executable mismatch with start receipt physical executable")

    # Corroborate wrapper-transformed child-visible argv shape
    if "-p" not in child_argv and "--print" not in child_argv:
        raise D1ReadbackError("child startup argv missing print flag (-p)")
    if "--permission-mode" in child_argv:
        pm_idx = child_argv.index("--permission-mode")
        if pm_idx + 1 >= len(child_argv) or child_argv[pm_idx + 1] != "plan":
            raise D1ReadbackError("child startup permission-mode is not plan")
    if "--model" in child_argv:
        m_idx = child_argv.index("--model")
        if m_idx + 1 >= len(child_argv) or child_argv[m_idx + 1] != route.get("model"):
            raise D1ReadbackError("child startup model mismatch with expected route")

    sr_allowlist = start_receipt.get("allowlist_environment") or {}
    child_environ = child_st.get("environ", {})
    for ek, ev in sr_allowlist.items():
        cv = child_environ.get(ek)
        if ek == "PYTHONNOUSERSITE" and {ev, cv} <= {"1", "true"}:
            continue
        if cv != ev:
            raise D1ReadbackError(f"child startup environment mismatch for allowlisted key {ek}")
    system_runtime_keys = {
        "PWD", "SHLVL", "SDKROOT", "CPATH", "LIBRARY_PATH", "MANPATH",
        "__CF_USER_TEXT_ENCODING", "LC_CTYPE",
    }
    allowed_env_keys = {
        "PATH", "HOME", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL",
        "PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE", "APG_D1_CONFIG", "APGR_MODEL_AUTHORITY",
        "CLAUDE_CODE_SAFE_MODE",
    } | system_runtime_keys
    if child_environ.get("APGR_MODEL_AUTHORITY") != "source-defaults":
        raise D1ReadbackError("D1 model authority must remain source-defaults")
    leaked = set(child_st.get("environ", {}).keys()) - allowed_env_keys
    if leaked:
        raise D1ReadbackError(f"ambient environment leaked into child process: {leaked}")


def readback_d1_record(evidence_root: Path, root: Path, *, allow_failed: bool = False) -> dict[str, Any]:
    if root is None:
        raise ValueError("repository root is mandatory for qualification readback")
    repo = Path(root).resolve()
    edir = Path(evidence_root).resolve()
    if not edir.is_dir() or edir.is_symlink():
        raise D1ReadbackError(f"evidence root invalid: {edir}")

    required_artifacts = [
        "d1-record.json",
        "authority.json",
        "auth-context.json",
        "attempt-state.json",
        "transport-receipt.json",
        "provider-start-receipt.json",
        "launch-contract.json",
        "runtime-manifest.json",
        "production-expected-runtime.json",
        "settings-state.json",
        "isolation-roots.json",
        "observer-inputs.json",
        "stdout.bin",
        "stderr.bin",
        "prompt.bin",
        "d1.context-plan.claude-stream.jsonl",
        "d1.context-deliveries.json",
        NATIVE_LAUNCH_FACTS_ARTIFACT,
        "probe/d1_probe_target.txt",
        "probe/probe-receipt.json",
    ]
    for rel_art in required_artifacts:
        art_path = edir / rel_art
        if art_path.is_symlink():
            raise D1ReadbackError(f"{rel_art} symlink forbidden: {art_path}")
        if not art_path.is_file():
            raise D1ReadbackError(f"{rel_art} missing: {art_path}")

    rpath = edir / "d1-record.json"
    rec = json.loads(rpath.read_bytes())

    if rec.get("probe_id") != PROBE_ID:
        raise D1ReadbackError("probe_id mismatch")

    expected_digest = rec.get("record_digest")
    if not expected_digest:
        raise D1ReadbackError("record_digest missing from record")
    rec_copy = copy.deepcopy(rec)
    rec_copy.pop("record_digest", None)
    if _sha256(_canonical_bytes(rec_copy)) != expected_digest:
        raise D1ReadbackError("record digest mismatch; local custody record modified or inconsistent")

    auth_data = json.loads((edir / "authority.json").read_bytes())
    auth_digest = compute_authority_digest(auth_data)
    if auth_data.get("authority_digest") and auth_data["authority_digest"] != auth_digest:
        raise D1ReadbackError("authority_digest mismatch in authority.json")

    t_receipt = json.loads((edir / "transport-receipt.json").read_bytes())
    if t_receipt.get("probe_id") != PROBE_ID:
        raise D1ReadbackError("transport receipt probe_id mismatch")
    transport_kind = t_receipt.get("transport_kind")
    if transport_kind not in (PRODUCTION_TRANSPORT_KIND, FAKE_TRANSPORT_KIND):
        raise D1ReadbackError(f"invalid transport_kind in transport receipt: {transport_kind}")

    start_receipt_file = edir / "provider-start-receipt.json"
    if not start_receipt_file.is_file() or start_receipt_file.is_symlink():
        raise D1ReadbackError(f"provider-start-receipt.json missing: {start_receipt_file}")
    start_receipt = json.loads(start_receipt_file.read_bytes())
    if start_receipt.get("schema") != PROVIDER_START_RECEIPT_SCHEMA:
        raise D1ReadbackError("provider-start receipt schema mismatch")
    if start_receipt.get("probe_id") != PROBE_ID:
        raise D1ReadbackError("probe_id mismatch in provider-start receipt")
    if start_receipt.get("authority_id") != auth_data.get("authority_id"):
        raise D1ReadbackError("authority_id mismatch in provider-start receipt")
    if start_receipt.get("authority_digest") != auth_digest:
        raise D1ReadbackError("authority digest mismatch in provider-start receipt")
    if start_receipt.get("source_identity") and start_receipt["source_identity"] != rec["source_identity"]:
        raise D1ReadbackError("source identity mismatch in provider-start receipt")

    croot = Path(auth_data["custody_root"]).resolve()
    attempt_key = derive_attempt_key(auth_data, rec["source_identity"])
    if start_receipt.get("attempt_key") != attempt_key:
        raise D1ReadbackError("attempt_key mismatch in provider-start receipt")

    sr_pid = start_receipt.get("pid")
    if not isinstance(sr_pid, int) or sr_pid <= 0:
        raise D1ReadbackError("valid PID required in provider-start receipt")
    if start_receipt.get("cwd") != str(edir):
        raise D1ReadbackError("cwd mismatch in provider-start receipt")
    if start_receipt.get("physical_executable") != rec.get("executable_evidence", {}).get("physical_executable"):
        raise D1ReadbackError("physical executable mismatch in provider-start receipt")

    # 1. Independently rederive expected launch contract and argv from source
    strm = edir / "d1.context-plan.claude-stream.jsonl"
    roots_data = json.loads((edir / "isolation-roots.json").read_bytes())
    settings_data = json.loads((edir / "settings-state.json").read_bytes())
    repo_desc = load_descriptor(root=repo)
    validate_descriptor(repo_desc, root=repo)
    repo_route = derive_d1_route(repo_desc, root=repo)
    source_argv = d1_outer_argv(repo)
    source_argv = [*source_argv, "--live-log", str(strm.resolve()), "--live-display", "raw"]
    expected_argv = [str(a) for a in source_argv]
    expected_argv_sha256 = _sha256(_canonical_bytes(expected_argv))

    launch_contract = json.loads((edir / "launch-contract.json").read_bytes())
    rederived_contract = build_expected_launch_contract(
        route=repo_route,
        argv=source_argv,
        roots=roots_data,
        settings_evidence=settings_data,
        root=repo,
        descriptor=repo_desc,
    )
    if rederived_contract != launch_contract:
        raise D1ReadbackError("launch contract differs from source-rederived contract")
    if launch_contract.get("argv") != expected_argv:
        raise D1ReadbackError("launch contract argv mismatch with source-derived expected argv")
    if start_receipt.get("exact_argv") != expected_argv:
        raise D1ReadbackError("exact_argv mismatch between start receipt and source-derived expected argv")
    if start_receipt.get("argv_sha256") != expected_argv_sha256:
        raise D1ReadbackError("argv_sha256 mismatch in start receipt with source-derived expected argv digest")

    ledger_path = croot / "consumed-attempts" / f"{attempt_key}.json"
    if not ledger_path.is_file() or ledger_path.is_symlink():
        raise D1ReadbackError(f"custody ledger missing or symlink: {ledger_path}")
    ledger_data = json.loads(ledger_path.read_bytes())
    if ledger_data.get("schema") != ATTEMPT_LEDGER_SCHEMA:
        raise D1ReadbackError("custody ledger schema mismatch")
    if ledger_data.get("attempt_key") != attempt_key:
        raise D1ReadbackError("attempt_key mismatch in custody ledger")
    if ledger_data.get("authority_digest") != auth_digest:
        raise D1ReadbackError("authority_digest mismatch in custody ledger")
    if ledger_data.get("authority_schema") != auth_data.get("schema"):
        raise D1ReadbackError("authority_schema mismatch in custody ledger")
    if ledger_data.get("starts_consumed") != 1:
        raise D1ReadbackError("starts_consumed must be 1 in custody ledger")
    if ledger_data.get("transport_kind") != transport_kind:
        raise D1ReadbackError("transport_kind mismatch between ledger and transport receipt")
    if ledger_data.get("status") != "start_finalized":
        raise D1ReadbackError(f"custody ledger status must be start_finalized, got {ledger_data.get('status')}")
    if ledger_data.get("pid") != sr_pid:
        raise D1ReadbackError("PID mismatch between custody ledger and start receipt")

    if ledger_data.get("launch_contract_digest") != _sha256(_canonical_bytes(launch_contract)):
        raise D1ReadbackError("launch_contract_digest mismatch in custody ledger")
    if ledger_data.get("provider_start_receipt_digest") != _sha256(_canonical_bytes(start_receipt)):
        raise D1ReadbackError("provider_start_receipt_digest mismatch in custody ledger")

    guard_file = edir / "provider-guard-receipt.json"
    if guard_file.is_file():
        guard_receipt = json.loads(guard_file.read_bytes())
        if ledger_data.get("guard_receipt_digest") != _sha256(_canonical_bytes(guard_receipt)):
            raise D1ReadbackError("guard_receipt_digest mismatch in custody ledger")

    # Provenance / Authority check
    if auth_data.get("schema") == INSTRUMENTED_AUTHORITY_SCHEMA:
        if rec.get("execution_kind") != "instrumented-provider-free":
            raise D1ReadbackError("execution kind forgery: instrumented authority cannot produce live-provider record")
        if rec.get("schema") != INSTRUMENTED_EVIDENCE_SCHEMA:
            raise D1ReadbackError("instrumented record schema mismatch")
        if rec.get("d1_status") != "not-run":
            raise D1ReadbackError("instrumented evidence cannot claim qualified d1_status")
        if ledger_data.get("transport_kind") != FAKE_TRANSPORT_KIND:
            raise D1ReadbackError("instrumented authority cannot bind production transport in ledger")
        if not (edir / "provider-guard-receipt.json").is_file():
            raise D1ReadbackError("provider-guard-receipt.json missing for instrumented run")
        if not (edir / "instrumented-executed-runtime.json").is_file():
            raise D1ReadbackError("instrumented-executed-runtime.json missing for instrumented run")
        if start_receipt.get("transport_class") != "instrumented-provider-free":
            raise D1ReadbackError("start receipt transport class must be instrumented-provider-free")
        if t_receipt.get("transport_class") != "instrumented-provider-free":
            raise D1ReadbackError("transport receipt transport class must be instrumented-provider-free")
        child_st_path = edir / "child-startup-evidence.json"
        if not child_st_path.is_file():
            raise D1ReadbackError("child-startup-evidence.json missing for instrumented run")
        child_st = json.loads(child_st_path.read_bytes())
        corroborate_child_startup_evidence(child_st, start_receipt=start_receipt, route=repo_route)
    elif auth_data.get("schema") == LIVE_AUTHORITY_SCHEMA:
        if ledger_data.get("transport_kind") != PRODUCTION_TRANSPORT_KIND:
            raise D1ReadbackError("live authority requires production-provider transport ledger")
        if rec.get("execution_kind") != "live-provider":
            raise D1ReadbackError("live authority requires live-provider execution kind")
        if rec.get("schema") != LIVE_EVIDENCE_SCHEMA:
            raise D1ReadbackError("live record schema mismatch")
        if (edir / "provider-guard-receipt.json").exists():
            raise D1ReadbackError("provider-guard-receipt.json forbidden for live run")
        if (edir / "provider-guard").exists():
            raise D1ReadbackError("provider-guard directory forbidden for live run")
        if (edir / "instrumented-executed-runtime.json").exists():
            raise D1ReadbackError("instrumented-executed-runtime.json forbidden for live run")
        if start_receipt.get("transport_class") != "production-provider":
            raise D1ReadbackError("start receipt transport class must be production-provider")
        if t_receipt.get("transport_class") != "production-provider":
            raise D1ReadbackError("transport receipt transport class must be production-provider")
        if rec.get("executable_evidence", {}).get("is_instrumented") is True:
            raise D1ReadbackError("live execution cannot use instrumented executable")
        if "fake-bin" in str(rec.get("executable_evidence", {}).get("physical_executable", "")):
            raise D1ReadbackError("live execution cannot use fake-bin executable")
        if start_receipt.get("provider_guard_identity") is not None or start_receipt.get("guard_receipt_digest") is not None:
            raise D1ReadbackError("live provider-start receipt cannot bind provider guard")
    else:
        raise D1ReadbackError(f"unsupported authority schema: {auth_data.get('schema')}")

    if ledger_data.get("transport_kind") == PRODUCTION_TRANSPORT_KIND:
        if rec.get("execution_kind") != "live-provider":
            raise D1ReadbackError("execution kind mismatch with production ledger")
        if rec.get("schema") != LIVE_EVIDENCE_SCHEMA:
            raise D1ReadbackError("live record schema mismatch")
    elif ledger_data.get("transport_kind") == FAKE_TRANSPORT_KIND:
        if rec.get("execution_kind") != "instrumented-provider-free":
            raise D1ReadbackError("execution kind forgery detected: record claims live-provider but ledger transport is instrumented-provider-free")
        if rec.get("schema") != INSTRUMENTED_EVIDENCE_SCHEMA:
            raise D1ReadbackError("instrumented record schema mismatch")
        if rec.get("d1_status") == "qualified":
            raise D1ReadbackError("instrumented evidence cannot claim d1_status qualified")

    # Shared source-derived checks apply to both authority branches.
    from .d1_launch_contract import verify_launch_facts
    verify_launch_facts(repo, edir, auth_data, roots_data, start_receipt, rec, expected_argv)

    # Check attempt state
    st_data = json.loads((edir / "attempt-state.json").read_bytes())
    if st_data.get("starts_consumed") != 1:
        raise D1ReadbackError("starts_consumed must be 1 in attempt state")
    if st_data.get("attempt_key") != attempt_key:
        raise D1ReadbackError("attempt_key mismatch in attempt state")
    if st_data.get("custody_ledger_sha256") != _sha256(_canonical_bytes(ledger_data)):
        raise D1ReadbackError("custody ledger digest mismatch in attempt state")
    if str(Path(st_data.get("custody_ledger_file", "")).resolve()) != str(ledger_path.resolve()):
        raise D1ReadbackError("custody ledger path mismatch in attempt state")

    if st_data.get("status") == "in_flight":
        raise D1ReadbackError("attempt state is in_flight; incomplete runs are not terminal")
    if not allow_failed and st_data.get("status") != "completed":
        raise D1ReadbackError(f"terminal status must be completed, got {st_data.get('status')}: "
                              + ", ".join(rec["post_provider"].get("failure_reasons", [])))

    # Check stdout, stderr, raw stream
    post = rec["post_provider"]
    so = edir / "stdout.bin"
    if _sha256(so.read_bytes()) != post["stdout"]["sha256"]:
        raise D1ReadbackError("stdout mismatch")
    se = edir / "stderr.bin"
    if _sha256(se.read_bytes()) != post["stderr"]["sha256"]:
        raise D1ReadbackError("stderr mismatch")

    strm = edir / "d1.context-plan.claude-stream.jsonl"
    raw_stream = strm.read_bytes()
    if _sha256(raw_stream) != post["raw_stream"]["sha256"]:
        raise D1ReadbackError("stream log mismatch")

    comp = strm.with_suffix(".complete.json")
    if comp.is_symlink():
        raise D1ReadbackError("completion receipt symlink forbidden")
    comp_data = json.loads(comp.read_bytes()) if comp.is_file() else {}
    from .d1_failure import capture_receipt_valid, capture_status, failure_reasons
    capture = capture_status(comp_data, raw_stream, post["terminal"])
    if capture != post.get("capture") or comp_data != post["stream_receipt"]:
        raise D1ReadbackError("capture/complete receipt mismatch")
    if comp_data and not capture_receipt_valid(comp_data, raw_stream, post["terminal"]):
        raise D1ReadbackError("complete receipt unverifiable")
    if not allow_failed and capture["status"] != "complete":
        raise D1ReadbackError("capture incomplete")

    # Prompt and probe custody
    prompt_file = edir / "prompt.bin"
    prompt_bytes = prompt_file.read_bytes()
    if _sha256(prompt_bytes) != rec["pre_provider"].get("prompt_sha256"):
        raise D1ReadbackError("prompt digest mismatch")
    if len(prompt_bytes) != rec["pre_provider"].get("prompt_bytes"):
        raise D1ReadbackError("prompt bytes length mismatch")

    target_fixture = edir / "probe/d1_probe_target.txt"
    fixture_bytes = target_fixture.read_bytes()
    expected_nonce = extract_fixture_nonce(fixture_bytes)
    if expected_nonce.encode("utf-8") in prompt_bytes:
        raise D1ReadbackError("answer-neutral violation: prompt contains probe nonce")

    probe_receipt = json.loads((edir / "probe/probe-receipt.json").read_bytes())
    if probe_receipt.get("sha256") != _sha256(fixture_bytes):
        raise D1ReadbackError("probe receipt digest mismatch")
    if probe_receipt.get("nonce_sha256") != _sha256(expected_nonce.encode("utf-8")):
        raise D1ReadbackError("probe receipt nonce digest mismatch")

    # Launch contract and expected argv already independently verified above
    surface = inspect_observed_surface(raw_stream, rec["route"], expected_contract=launch_contract, expected_argv=launch_contract.get("argv"))
    if surface["failure_codes"] != rec["surface_contract"].get("failure_codes", []):
        raise D1ReadbackError("surface contract recomputation mismatch")
    if not allow_failed and not surface["valid"]:
        raise D1ReadbackError(f"surface contract invalid: {surface['failure_codes']}")

    # Recompute native Read observation from raw stream and retained observer inputs
    obs_inputs = json.loads((edir / "observer-inputs.json").read_bytes())
    if obs_inputs.get("raw_stream_sha256") != post["raw_stream"]["sha256"]:
        raise D1ReadbackError("observer inputs stream digest mismatch")

    rebuilt_captured = {}
    for path_str, cap_meta in obs_inputs.get("claude_read_capture", {}).items():
        p = Path(path_str)
        if not p.is_file():
            raise D1ReadbackError(f"captured recovery file missing: {path_str}")
        rebuilt_captured[path_str] = {
            "entry": cap_meta["entry"],
            "payload": p.read_bytes(),
            "scope": cap_meta["scope"],
        }

    recomputed_imp = importers.import_claude(so.read_bytes(), rec["route"], terminal=post["terminal"])
    from agent_phase.claude_read_observer import observe
    recomputed_obs = {"reads": [], "events": []}
    if capture["status"] == "complete" and recomputed_imp.get("provider_outcome") == "success":
        try:
            recomputed_obs = observe(raw_stream, expected_sha256=post["raw_stream"]["sha256"],
                                     captured=rebuilt_captured, scope=obs_inputs.get("scope", {}))
        except ValueError as error:
            if not allow_failed:
                raise D1ReadbackError(f"native Read observation recomputation failed: {error}") from error
    if comp_data and (comp_data.get("scope") != obs_inputs["scope"]
                      or comp_data.get("plan") != obs_inputs["reference"]):
        raise D1ReadbackError("completion scope/plan mismatch")

    recomputed_reads = recomputed_obs.get("reads", [])
    if len(recomputed_reads) != post["native_reads"].get("read_count"):
        raise D1ReadbackError("native reads count recomputation mismatch")
    if len(recomputed_reads) != len(post["native_reads"].get("reads", [])):
        raise D1ReadbackError("native reads recomputation mismatch")

    # Compare full recomputed read structures
    for r_obs, r_recomp in zip(post["native_reads"].get("reads", []), recomputed_reads):
        if r_obs.get("id") != r_recomp.get("id"):
            raise D1ReadbackError("read tool_use id mismatch")
        if r_obs.get("file_path") != r_recomp.get("file_path"):
            raise D1ReadbackError("read file path mismatch")
        if r_obs.get("record_sha256") != r_recomp.get("record_sha256"):
            raise D1ReadbackError("read record digest mismatch")

    # Recompute deliveries
    from agent_phase.acquisition_records import delivery_entries
    recomputed_read_deliveries = delivery_entries(
        recomputed_obs.get("events", []),
        run_id=obs_inputs.get("scope", {}).get("run_id", ""),
        binding_id=obs_inputs.get("scope", {}).get("binding_id", ""),
        attempt_id=obs_inputs.get("scope", {}).get("attempt_id", ""),
    )
    if not allow_failed:
        if not recomputed_read_deliveries.get("deliveries"):
            raise D1ReadbackError("no delivery entries derived from raw Read events")
        if recomputed_read_deliveries.get("coverage") != "complete":
            raise D1ReadbackError(f"read deliveries coverage incomplete: {recomputed_read_deliveries.get('diagnostics')}")

    retained_deliveries = json.loads((edir / "d1.context-deliveries.json").read_bytes())
    if retained_deliveries.get("schema") != "apg.controlled-transmissions/v1":
        raise D1ReadbackError("deliveries schema mismatch")
    if not allow_failed and retained_deliveries.get("coverage") != "complete":
        raise D1ReadbackError("deliveries coverage incomplete")
    if retained_deliveries != post["delivery"]:
        raise D1ReadbackError("deliveries mismatch with record summary")
    prompt_ev = next((e for e in retained_deliveries.get("events", []) if e.get("channel") == "prompt"), None)
    if prompt_ev is None:
        raise D1ReadbackError("prompt event missing from transmissions")
    if prompt_ev.get("payload_sha256") != rec["pre_provider"]["prompt_sha256"]:
        raise D1ReadbackError("transmission prompt digest mismatch")

    # Recompute importer
    recomputed_imp = importers.import_claude(so.read_bytes(), rec["route"], terminal=post["terminal"])
    if recomputed_imp != post["importer"]:
        raise D1ReadbackError("importer recomputation mismatch")

    # Recompute oracle from raw stdout + recomputed Read + probe fixture target
    recomputed_oracle = evaluate_d1_response(
        so.read_bytes(), expected_nonce,
        observation=recomputed_obs,
        fixture_bytes=fixture_bytes,
        fixture_path=target_fixture,
    )
    if (recomputed_imp.get("provider_outcome") != post.get("provider_outcome")
            or failure_reasons(
                recomputed_imp, post["terminal"], capture, rec["surface_contract"],
                recomputed_reads, recomputed_oracle,
                native_launch=post.get("native_launch_custody"),
                git_preserved=post["git"] == rec["pre_provider"]["git"],
                settings_preserved=post["settings"]["sha256"] == rec["pre_provider"]["settings"]["sha256"],
            ) != post.get("failure_reasons")):
        raise D1ReadbackError("provider failure disposition mismatch")
    if recomputed_oracle["status"] != post["oracle"]["status"]:
        raise D1ReadbackError("oracle recomputation status mismatch")
    if not allow_failed and recomputed_oracle["status"] != "pass":
        raise D1ReadbackError(f"oracle recomputation failed: {recomputed_oracle}")

    # Runtime manifest recomputation
    manifest_data = json.loads((edir / "runtime-manifest.json").read_bytes())
    from . import runtime_manifest as rm
    if post["runtime"]["runtime_manifest_sealed_sha256"] != rm.manifest_digest(manifest_data):
        raise D1ReadbackError("runtime manifest sealed digest mismatch")
    if post["runtime"]["runtime_manifest_file_sha256"] != _sha256(_json_bytes(manifest_data)):
        raise D1ReadbackError("runtime manifest file digest mismatch")
    rm.revalidate(manifest_data, probe_versions=False)
    prod_manifest_data = json.loads((edir / "production-expected-runtime.json").read_bytes())
    rm.revalidate(prod_manifest_data, probe_versions=False)

    # Settings & Git drift
    roots_data = json.loads((edir / "isolation-roots.json").read_bytes())
    git_target = Path(roots_data["disposable_root"]["path"]) if "disposable_root" in roots_data else repo
    if not allow_failed:
        if rec["pre_provider"]["settings"]["sha256"] != post["settings"]["sha256"]:
            raise D1ReadbackError("settings drift")
        if rec["pre_provider"]["git"] != post["git"]:
            raise D1ReadbackError("git drift")

        current_target_git = capture_git_state(git_target)
        if post["git"]["head"] != current_target_git["head"] or post["git"]["tree"] != current_target_git["tree"]:
            raise D1ReadbackError("git target state drifted after attempt")

        if "disposable_root" not in roots_data:
            current_git = capture_git_state(repo)
            if post["git"]["head"] != current_git["head"] or post["git"]["tree"] != current_git["tree"]:
                raise D1ReadbackError("git repository state drifted after attempt")

    sid = readiness.source_identity(readiness.make_seal(repo)["files"])
    if rec["source_identity"] != sid:
        raise D1ReadbackError("source identity mismatch")
    desc_bytes = (repo / DESCRIPTOR_RELATIVE_PATH).read_bytes()
    if _sha256(desc_bytes) != rec["descriptor_sha256"]:
        raise D1ReadbackError("descriptor mismatch")

    validate_descriptor(json.loads(desc_bytes), root=repo)
    return rec


def create_fake_claude_executable(bin_dir: Path, python_exe: str | None = None, repo_root: Path | None = None) -> Path:
    """Create private fake native claude executable underneath provider resolution."""
    bin_dir = Path(bin_dir).resolve()
    bin_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = bin_dir / "claude"
    py = python_exe or sys.executable
    # The source wrapper invokes python3 through this isolated PATH. Bind it
    # to the same qualified interpreter as the provider-free fixture.
    interpreter = bin_dir / "python3"
    if not interpreter.exists():
        interpreter.symlink_to(Path(py).resolve())
    elif interpreter.resolve() != Path(py).resolve():
        raise D1Error("instrumented interpreter binding changed")
    repo_repr = repr(str(repo_root.resolve())) if repo_root is not None else "None"

    script = f'''#!{py}
import json
import os
import sys
import time
from pathlib import Path

if "--version" in sys.argv[1:]:
    print({(D1_CLAUDE_CLI_VERSION + " (Claude Code)")!r})
    sys.exit(0)

if "--help" in sys.argv[1:]:
    print("auth status --json --safe-mode --no-session-persistence")
    sys.exit(0)
if sys.argv[1:3] == ["auth", "status"]:
    marker = Path(os.environ["HOME"]) / ".fake-authenticated"
    print(json.dumps({{"loggedIn": marker.is_file(), "authMethod": "claude.ai"}}))
    sys.exit(0 if marker.is_file() else 1)

prompt = sys.stdin.buffer.read()
cwd = Path.cwd()

config_path = cwd / ".fake-claude-config.json"
cfg = {{}}
if config_path.is_file():
    try:
        cfg = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        pass

scenario = cfg.get("scenario", "success")
attempt_id = cfg.get("attempt_id", "att-unknown")
edir = Path(cfg.get("evidence_root", str(cwd)))

# Startup evidence capture
startup_ev = {{
    "schema": "apg.d1-child-startup-evidence/v1",
    "pid": os.getpid(),
    "ppid": os.getppid(),
    "argv": sys.argv,
    "cwd": str(cwd),
    "environ": dict(os.environ),
    "timestamp": time.time(),
}}
st_file = edir / "child-startup-evidence.json"
with st_file.open("wb") as s:
    s.write((json.dumps(startup_ev, sort_keys=True, indent=2) + "\\n").encode("utf-8"))
    s.flush()
    os.fsync(s.fileno())
st_file.chmod(0o600)

if scenario == "timeout":
    time.sleep(2.0)
    sys.exit(124)

if scenario == "git_mutation":
    disp_str = cfg.get("disposable_root")
    if not disp_str:
        sys.stderr.write("fake error: git_mutation requires disposable_root\\n")
        sys.exit(98)
    disp = Path(disp_str).resolve()
    repo_cfg = {repo_repr}
    repo_resolved = Path(repo_cfg).resolve() if repo_cfg is not None else None
    if repo_resolved is not None and (disp == repo_resolved or repo_resolved.is_relative_to(disp) or disp.is_relative_to(repo_resolved)):
        sys.stderr.write("fake error: git_mutation cannot mutate real REPO_ROOT\\n")
        sys.exit(98)
    (disp / ".untracked_git_mutation_probe").write_text("git mutation")

if scenario == "settings_drift":
    cfg_file = edir / "home/.claude/settings.json"
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text('{{"mutated": true}}')

# Read probe fixture
fix_str = cfg.get("fixture_path")
fixture_path = Path(fix_str) if fix_str else (cwd / "probe/d1_probe_target.txt")
fbytes = fixture_path.read_bytes() if fixture_path.is_file() else b""
nonce = ""
for line in fbytes.splitlines():
    if line.startswith(b"D1-PROBE-NONCE:"):
        nonce = line.split(b":", 1)[1].strip().decode("utf-8", "replace")
        break

if scenario == "read_mismatch":
    ans_nonce = "0" * 64
else:
    ans_nonce = nonce

if scenario == "content_mismatch":
    content_text = "corrupted fixture content"
else:
    content_text = fbytes.decode("utf-8", "replace")

if scenario == "wrong_read_path":
    read_path_str = str(fixture_path.parent / "wrong_target.txt")
else:
    read_path_str = str(fixture_path)

tools = sys.argv[sys.argv.index("--tools") + 1].split(",") if "--tools" in sys.argv else []
if scenario == "extra_tool":
    tools.append("Bash")
elif scenario == "no_read_tool":
    tools = []
mcps = [{{"name": "bad", "status": "connected"}}] if scenario == "non_empty_mcp" else []
perm_mode = "default" if scenario == "permission_mismatch" else "plan"
model_name = "claude-sonnet-4" if scenario == "model_mismatch" else sys.argv[sys.argv.index("--model") + 1]

if scenario == "no_read":
    events = [
        {{"type": "system", "subtype": "init", "claude_code_version": {D1_CLAUDE_CLI_VERSION!r}, "model": model_name, "permissionMode": perm_mode, "tools": tools, "mcp_servers": mcps}},
        {{"type": "result", "subtype": "success", "session_id": "d1-s", "is_error": False,
          "result": json.dumps({{"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", "nonce": ans_nonce, "summary": "Read ok"}})}},
    ]
else:
    events = [
        {{"type": "system", "subtype": "init", "claude_code_version": {D1_CLAUDE_CLI_VERSION!r}, "model": model_name, "permissionMode": perm_mode, "tools": tools, "mcp_servers": mcps}},
        {{"type": "assistant", "session_id": "d1-s", "message": {{"content": [{{"type": "tool_use", "id": "read1", "name": "Read", "input": {{"file_path": read_path_str}}}}]}}}},
        {{"type": "user", "session_id": "d1-s", "message": {{"content": [{{"type": "tool_result", "tool_use_id": "read1", "content": f"1\\u2192{{content_text}}"}}]}},
          "tool_use_result": {{"type": "text", "file": {{"filePath": read_path_str, "content": content_text, "startLine": 1, "numLines": 6, "totalLines": 6}}}}}},
        {{"type": "result", "subtype": "success", "session_id": "d1-s", "is_error": False,
          "result": json.dumps({{"schema": "apg.d1-response/v1", "probe_id": "APG166D-PROBE-D1", "nonce": ans_nonce, "summary": "Read ok"}})}},
    ]

if scenario in ("auth_error", "nonzero"):
    events = [events[0],
        {{"type": "assistant", "session_id": "d1-s", "error": "authentication_failed",
          "is_api_error_message": True, "message": {{"content": [{{"type": "text", "text": "Not logged in · Please run /login"}}]}}}},
        {{"type": "result", "subtype": "success", "is_error": True, "session_id": "d1-s",
          "terminal_reason": "api_error", "api_error_status": 401, "duration_api_ms": 0,
          "total_cost_usd": 0, "usage": {{"input_tokens": 0, "output_tokens": 0}},
          "result": "Not logged in · Please run /login"}}]

strm_b = b'{{"type":"malformed"\\n' if scenario == "malformed" else b"".join((json.dumps(e, ensure_ascii=False) + "\\n").encode("utf-8") for e in events)

out_b = strm_b if scenario != "malformed" else b"malformed\\n"
sys.stdout.buffer.write(out_b)
sys.stdout.buffer.flush()
sys.exit(1 if scenario == "auth_error" else 7 if scenario == "nonzero" else 0)
'''
    target.write_text(script, encoding="utf-8")
    target.chmod(0o755)
    return target


def _execute_d1_attempt(
    root: Path,
    evidence_root: Path,
    authority: Mapping[str, Any],
    *,
    transport_kind: str,
    scenario: str = "success",
    tool_mutation: str | None = None,
    corrupt_log: bool = False,
    corrupt_stream_after: bool = False,
    runtime_manifest_override: Mapping[str, Any] | None = None,
    fake_executable: Path | None = None,
    timeout: float = 10.0,
    disposable_root: Path | None = None,
    guard_dir: Path | None = None,
) -> dict[str, Any]:
    """Single private internal attempt engine for both live production and fake qualifications.
    Executes all 19 lifecycle steps end-to-end through context_adapter.invoke(prep, provider.run, ...).
    """
    repo = Path(root).resolve()
    edir = Path(evidence_root).resolve()
    if edir.exists():
        non_guard_items = [p for p in edir.iterdir() if p.name != "provider-guard"]
        if non_guard_items:
            raise D1AttemptError("evidence directory must be empty")

    # 1. source/descriptor/model validation
    desc = load_descriptor(root=repo)
    dsha = _sha256((repo / DESCRIPTOR_RELATIVE_PATH).read_bytes())
    sid = readiness.source_identity(readiness.make_seal(repo)["files"])
    route = derive_d1_route(desc, root=repo)

    if scenario == "git_mutation":
        if disposable_root is None:
            raise D1Error("git_mutation scenario requires explicit disposable_root; mutating repository root is prohibited")
        disp_res = Path(disposable_root).resolve()
        if disp_res == repo or disp_res.is_relative_to(repo) or repo.is_relative_to(disp_res):
            raise D1Error(f"disposable_root cannot overlap with repository root: {disp_res}")
        if not (disp_res / ".git").exists():
            raise D1Error(f"disposable_root must be a valid git repository: {disp_res}")

    # 2. authority validation
    git_target = disposable_root if disposable_root is not None else repo
    gb = capture_git_state(git_target)
    pre_repo_git = capture_git_state(repo)
    validate_d1_authority(
        authority,
        expected_commit=gb["head"],
        expected_tree=gb["tree"],
        expected_source_identity=sid,
        expected_descriptor_digest=dsha,
        expected_custody_root=authority.get("custody_root"),
        expected_evidence_root=str(edir),
        root=repo,
    )
    # Refusals here leave the same grant/evidence root usable; no attempt writes.
    is_fake = transport_kind == FAKE_TRANSPORT_KIND
    selection = None
    preflight = None
    auth_context = None
    if not is_fake:
        from .d1_auth import capture_context, require_fresh_memory
        try:
            auth_context = capture_context(os.environ, forbidden_roots=(repo, edir, authority["custody_root"]))
            require_fresh_memory(auth_context, edir)
        except ValueError as error:
            raise D1Error(str(error)) from error
        selection = select_d1_production_executables()
        with tempfile.TemporaryDirectory(prefix="apg-d1-preflight-") as temporary:
            preflight_root = Path(temporary).resolve()
            if preflight_root.is_relative_to(repo) or preflight_root.is_relative_to(edir):
                raise D1Error("preflight temporary root must be outside repository and evidence")
            preflight_env = build_d1_launch_environment(
                home_dir=Path(auth_context["HOME"]), tmp_dir=preflight_root, executable_selection=selection,
                auth_context=auth_context)
            preflight = preflight_d1_production_executables(repo, selection, preflight_env)
            preflight["auto_memory_initially_fresh"] = True
    edir.mkdir(parents=True, exist_ok=True, mode=0o700)
    auth_digest = authority.get("authority_digest") or compute_authority_digest(authority)
    _write_private_json(edir / "authority.json", {**dict(authority), "authority_digest": auth_digest})

    # 3. probe materialization
    probe_dir = (edir / "probe").resolve()
    fpath, expected_nonce = materialize_probe(desc, probe_dir, root=repo)
    fb = fpath.read_bytes()

    # 4. answer-neutral prompt and prompt custody
    prompt_b = build_d1_prompt(fpath, root=repo)
    _write_private_bytes(edir / "prompt.bin", prompt_b)

    # 5. prepare context adapter and argv
    argv = d1_outer_argv(repo)
    argv, prompt_b, prep = context_adapter.prepare(
        capture={"settings": {"mode": "static"}, "provenance": []}, run_dir=edir, prefix="d1",
        run_id=f"d1-{authority['attempt_id']}", binding_id=ALLOWED_BINDING_ID,
        attempt_id=authority["attempt_id"], roles=[ALLOWED_ROLE], consumer="claude", argv=argv, prompt=prompt_b,
    )
    prep["record"]["acquisition"] = {"recovery": [{"id": "probe:d1", "path": str(fpath.relative_to(edir)), "bytes": len(fb), "sha256": _sha256(fb)}]}
    argv = claude_reads.prepare(prep, argv, qualification={"cli_version": D1_CLAUDE_CLI_VERSION, "model": route["model"]})
    strm_path = Path(prep["claude_read_stream"])

    # 6. capture isolation roots, settings, runtime, and executable
    home_dir = Path(auth_context["HOME"]) if auth_context else (edir / "home").resolve()
    if is_fake:
        home_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    _write_private_json(edir / "auth-context.json", {"schema": "apg.d1-auth-context/v1",
                        "values": dict(auth_context or {"HOME": str(home_dir)})})
    tmp_dir = (edir / "tmp").resolve()
    tmp_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    roots_ev = capture_isolation_roots(
        Path(authority["custody_root"]), edir, edir, home_dir if is_fake else None, tmp_dir, probe_dir, repo,
        disposable_root=disposable_root,
    )
    _write_private_json(edir / "isolation-roots.json", roots_ev)

    effective_fake_exec = fake_executable
    effective_scenario = scenario
    if tool_mutation == "Bash":
        effective_scenario = "extra_tool"
    elif tool_mutation == "mcp":
        effective_scenario = "non_empty_mcp"

    if is_fake and effective_fake_exec is None:
        fake_bin_dir = edir / "fake-bin"
        effective_fake_exec = create_fake_claude_executable(fake_bin_dir, repo_root=repo)

    prod_manifest = build_d1_runtime_manifest(
        repo, home_dir, tmp_dir, fake_executable=None, is_instrumented=False,
        executable_selection=selection,
    )
    _write_private_json(edir / "production-expected-runtime.json", prod_manifest)

    manifest = runtime_manifest_override or (
        build_d1_runtime_manifest(
            repo, home_dir, tmp_dir, fake_executable=effective_fake_exec, is_instrumented=True
        ) if is_fake else prod_manifest
    )
    _write_private_json(edir / "runtime-manifest.json", manifest)
    if is_fake:
        _write_private_json(edir / "instrumented-executed-runtime.json", manifest)
    rb = capture_runtime_state(manifest)

    sb = capture_settings_state(repo, isolated_settings=True, isolated_home=home_dir, auth_context=auth_context)
    _write_private_json(edir / "settings-state.json", sb)

    ex_ev = capture_executable_evidence(
        repo, runtime_manifest=manifest,
        executable_path=Path(selection["executables"]["claude"]["physical"]) if selection else effective_fake_exec,
        cli_version=preflight["claude_version"] if preflight else None, is_instrumented=is_fake,
        executable_selection=selection, preflight=preflight,
    )

    pre_ev = {
        "git": gb,
        "auth_context_sha256": _sha256((edir / "auth-context.json").read_bytes()),
        "settings": sb,
        "runtime": rb,
        "fixture": {"path": str(fpath.relative_to(edir)), "bytes": len(fb), "sha256": _sha256(fb)},
        "prompt_sha256": _sha256(prompt_b),
        "prompt_bytes": len(prompt_b),
    }

    # 7. bind expected launch contract
    launch_contract = build_expected_launch_contract(route=route, argv=argv, roots=roots_ev, settings_evidence=sb)
    _write_private_json(edir / "launch-contract.json", launch_contract)
    launch_contract_digest = _sha256(_canonical_bytes(launch_contract))

    # Environment setup
    if is_fake and effective_fake_exec:
        fake_cfg = {
            "scenario": effective_scenario,
            "fixture_path": str(fpath.resolve()),
            "attempt_id": authority["attempt_id"],
            "evidence_root": str(edir.resolve()),
            "disposable_root": str(disposable_root.resolve()) if disposable_root else None,
        }
        _write_private_json(edir / ".fake-claude-config.json", fake_cfg)

    clean_env = build_d1_launch_environment(
        home_dir=home_dir,
        tmp_dir=tmp_dir,
        fake_executable=effective_fake_exec if is_fake else None,
        config_path=(edir / ".fake-claude-config.json") if is_fake else None,
        is_instrumented=is_fake,
        executable_selection=selection,
        auth_context=auth_context,
    )

    # 8. write provider-guard receipt if present
    guard = ACTIVE_GUARD.get()
    gr = guard.receipt() if (is_fake and guard) else None
    guard_receipt_digest = _sha256(_canonical_bytes(gr)) if gr else None
    if gr:
        _write_private_json(edir / "provider-guard-receipt.json", gr)

    # 9. atomic attempt consumption immediately before process start
    # Attempt is burned in prelaunch_consumed status before Popen
    ledger_file, state_path = record_attempt_consumption(
        Path(authority["custody_root"]), edir, authority, sid, pre_ev,
        transport_kind=transport_kind,
        launch_contract_digest=launch_contract_digest,
        provider_start_receipt_digest=None,
        guard_receipt_digest=guard_receipt_digest,
    )

    # 10. invoke process runner through context_adapter.invoke(prep, provider.run, ...)
    hook_fired = [False]

    def _launch_owner_hook(proc: Any, executed_argv: Sequence[str], executed_cwd: str, executed_env: Mapping[str, str] | None) -> None:
        hook_fired[0] = True
        pid = proc.pid
        try:
            pgid = os.getpgid(pid)
        except OSError:
            pgid = None
        try:
            sid_session = os.getsid(pid)
        except OSError:
            sid_session = None

        effective_gr = gr
        effective_gr_digest = guard_receipt_digest
        if is_fake and guard is not None:
            guard.account_fake_process(effective_scenario, executed_argv, pid=pid)
            effective_gr = guard.receipt()
            pgr_file = edir / "provider-guard-receipt.json"
            if pgr_file.exists():
                _atomic_update_json(pgr_file, effective_gr)
            else:
                _write_private_json(pgr_file, effective_gr)
            effective_gr_digest = _sha256(_canonical_bytes(effective_gr))

        actual_env = executed_env if executed_env is not None else clean_env
        start_receipt = create_provider_start_receipt(
            authority=authority,
            attempt_key=derive_attempt_key(authority, sid),
            physical_executable=ex_ev["physical_executable"],
            physical_executable_sha256=ex_ev["physical_executable_sha256"],
            argv=executed_argv,
            environment=actual_env,
            cwd=executed_cwd,
            transport_class="production-provider" if transport_kind == PRODUCTION_TRANSPORT_KIND else "instrumented-provider-free",
            transport_kind=transport_kind,
            guard_receipt=effective_gr,
            pid=pid,
            process_group=pgid,
            session_id=sid_session,
            source_identity=sid,
            allowlist_environment=clean_env,
        )
        observed_launcher = Path(executed_argv[0]).resolve(strict=True)
        start_receipt["popen_executable"] = str(observed_launcher)
        start_receipt["popen_executable_sha256"] = _sha256(observed_launcher.read_bytes())
        _write_private_json(edir / "provider-start-receipt.json", start_receipt)
        start_receipt_digest = _sha256(_canonical_bytes(start_receipt))
        finalize_consumed_attempt(
            ledger_file,
            state_path,
            provider_start_receipt_digest=start_receipt_digest,
            pid=pid,
            process_group=pgid,
            session_id=sid_session,
            guard_receipt_digest=effective_gr_digest,
        )

    try:
        hook_token = provider.PROCESS_CREATION_HOOK.set(_launch_owner_hook)
        try:
            returned = context_adapter.invoke(prep, provider.run, argv, prompt_b, edir, environment=clean_env)
        finally:
            provider.PROCESS_CREATION_HOOK.reset(hook_token)

        if not hook_fired[0]:
            raise D1Error("launch-owner process creation hook did not observe child process")

        # Write transport receipt
        t_receipt = {
            "schema": TRANSPORT_RECEIPT_SCHEMA,
            "transport_kind": transport_kind,
            "transport_class": "production-provider" if transport_kind == PRODUCTION_TRANSPORT_KIND else "instrumented-provider-free",
            "probe_id": PROBE_ID,
            "authority_id": authority["authority_id"],
            "authority_digest": auth_digest,
            "attempt_id": authority["attempt_id"],
            "exit_code": getattr(returned, "exit_code", 0),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _write_private_json(edir / "transport-receipt.json", t_receipt)

        # 11. custody of stdout/stderr/raw stream/completion
        out_b = getattr(returned, "stdout", b"")
        err_b = getattr(returned, "stderr", b"")
        rc = getattr(returned, "exit_code", 0)

        if scenario != "missing_stdout":
            _write_private_bytes(edir / "stdout.bin", out_b)
        if scenario != "missing_stderr":
            _write_private_bytes(edir / "stderr.bin", err_b)

        if corrupt_log and strm_path.is_file():
            strm_path.unlink()
        if corrupt_stream_after and strm_path.is_file():
            strm_path.write_bytes(strm_path.read_bytes() + b'{"extra":true}\n')

        raw_stream = strm_path.read_bytes() if strm_path.is_file() else b""
        rcpt = json.loads(strm_path.with_suffix(".complete.json").read_bytes()) if strm_path.with_suffix(".complete.json").is_file() else {}

        # 12. native Read observation & retain observer inputs
        terminal = {
            "exit_code": rc,
            "signal": None,
            "timeout": scenario == "timeout",
            "truncated": getattr(returned, "truncated", False),
        }
        obs: dict[str, Any] = {"read_count": 0, "events": [], "reads": []}
        if rc == 0 and not corrupt_log and scenario not in ("malformed", "missing_raw_log") and strm_path.is_file():
            try:
                obs = claude_reads.collect(prep, returned)
            except Exception as e:
                obs = {"error": str(e), "read_count": 0, "events": [], "reads": []}

        serializable_capture = {}
        for k, v in prep.get("claude_read_capture", {}).items():
            serializable_capture[k] = {
                "entry": dict(v.get("entry", {})),
                "scope": dict(v.get("scope", {})),
            }
        obs_inputs = {
            "schema": OBSERVER_INPUTS_SCHEMA,
            "run_id": prep["record"]["run_id"],
            "binding_id": prep["record"]["binding_id"],
            "attempt_id": prep["record"]["attempt_id"],
            "scope": {k: prep["record"][k] for k in ("run_id", "binding_id", "attempt_id")},
            "reference": prep["reference"],
            "expected_probe_path": str(fpath.resolve()),
            "expected_probe_sha256": _sha256(fb),
            "expected_probe_bytes": len(fb),
            "profile": route["profile"],
            "model": route["model"],
            "raw_stream_path": str(strm_path.resolve()),
            "raw_stream_sha256": _sha256(raw_stream),
            "claude_read_capture": serializable_capture,
        }
        _write_private_json(edir / "observer-inputs.json", obs_inputs)

        # 13. importer (defined and executed on all paths!)
        imp = importers.import_claude(out_b, route, terminal=terminal)

        # 14. delivery derivation
        deliv_path = edir / "d1.context-deliveries.json"
        if deliv_path.is_file():
            deliveries = json.loads(deliv_path.read_bytes())
        else:
            from agent_phase.acquisition_records import delivery_entries
            deliveries = delivery_entries(
                obs.get("events", []),
                run_id=prep["record"]["run_id"],
                binding_id=prep["record"]["binding_id"],
                attempt_id=prep["record"]["attempt_id"],
            )
            _write_private_json(deliv_path, deliveries)
        try:
            native_launch = native_launch_custody(read_regular_nofollow(edir / NATIVE_LAUNCH_FACTS_ARTIFACT))
        except OSError:
            # Absent or unsafe native facts cannot qualify; readback refuses them.
            native_launch = None

        # 15. oracle evaluation
        oracle_res = evaluate_d1_response(out_b, expected_nonce, observation=obs, fixture_bytes=fb, fixture_path=fpath)

        # 16. post-state capture
        ga = capture_git_state(git_target)
        if disposable_root is not None:
            real_post_git = capture_git_state(repo)
            if (
                real_post_git["head"] != pre_repo_git["head"]
                or real_post_git["tree"] != pre_repo_git["tree"]
                or real_post_git["status_sha256"] != pre_repo_git["status_sha256"]
                or real_post_git["index_sha256"] != pre_repo_git["index_sha256"]
            ):
                raise D1Error("repository root was modified during attempt; disposable isolation violated")
        sa = capture_settings_state(repo, isolated_settings=True, isolated_home=home_dir, auth_context=auth_context)
        ra = capture_runtime_state(manifest)
        surface_contract = inspect_observed_surface(raw_stream, route, expected_contract=launch_contract, expected_argv=argv)

        # 17. derive D1 record
        d1_rec = derive_d1_record(
            authority=authority, descriptor=desc, descriptor_sha256=dsha, source_identity_str=sid, route=route,
            pre_evidence=pre_ev, terminal=terminal, stdout=out_b, stderr=err_b, raw_stream=raw_stream,
            stream_receipt=rcpt, observation=obs, delivery_data=deliveries, imported=imp, oracle_result=oracle_res,
            post_git=ga, post_settings=sa, post_runtime=ra, surface_contract=surface_contract,
            execution_kind=transport_kind, executable_evidence=ex_ev, native_launch=native_launch,
        )
        _write_private_json(edir / "d1-record.json", d1_rec)

        # 18. terminal attempt-state update
        is_qual = d1_rec.get("provider_free_d1_seam_qualified", False) if transport_kind == FAKE_TRANSPORT_KIND else (d1_rec.get("d1_status") == "qualified")
        st_fin = "completed" if is_qual else "failed"
        record_attempt_finish(edir, st_fin, error=None if is_qual else ", ".join(d1_rec["post_provider"]["failure_reasons"]) or "qualification failure")

        # 19. mandatory readback
        if is_qual:
            readback_d1_record(edir, root=repo)

        return d1_rec

    except Exception as exc:
        try:
            record_attempt_finish(edir, "failed", error=str(exc))
        except Exception:
            pass
        raise


def run_live_d1(root: Path, evidence_root: Path, authority: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
    """Production source-owned live D1 entry point.
    Callers may not override provider, profile, model, role, tools, MCP, prompt,
    fixture, oracle, transport, or execution kind.
    """
    if kwargs:
        raise D1AuthorityError(f"caller override prohibited: {list(kwargs.keys())}")
    if authority.get("schema") != LIVE_AUTHORITY_SCHEMA:
        raise D1AuthorityError(f"run_live_d1 requires live authority schema {LIVE_AUTHORITY_SCHEMA}, got {authority.get('schema')}")

    return _execute_d1_attempt(
        root,
        evidence_root,
        authority,
        transport_kind=PRODUCTION_TRANSPORT_KIND,
    )


def run_instrumented_d1_lifecycle(
    root: Path,
    evidence_root: Path,
    authority: Mapping[str, Any],
    *,
    scenario: str = "success",
    tool_mutation: str | None = None,
    corrupt_log: bool = False,
    corrupt_stream_after: bool = False,
    runtime_manifest_override: Mapping[str, Any] | None = None,
    fake_executable: Path | None = None,
    timeout: float = 10.0,
    disposable_root: Path | None = None,
) -> dict[str, Any]:
    """Provider-free D1 lifecycle executing a real fake child subprocess through the shared internal engine."""
    if authority.get("schema") != INSTRUMENTED_AUTHORITY_SCHEMA:
        raise D1AuthorityError(f"run_instrumented_d1_lifecycle requires instrumented authority schema {INSTRUMENTED_AUTHORITY_SCHEMA}, got {authority.get('schema')}")

    edir = Path(evidence_root).resolve()
    edir.mkdir(parents=True, exist_ok=True, mode=0o700)
    guard_dir = edir / "provider-guard"
    with LaunchGuard(guard_dir) as guard:
        guard.executable("claude", "normal-final-review")
        guard.executable("codex", "implementation-primary")
        guard.executable("antigravity", "gemini-3.8-flash-high")

        rec = _execute_d1_attempt(
            root,
            edir,
            authority,
            transport_kind=FAKE_TRANSPORT_KIND,
            scenario=scenario,
            tool_mutation=tool_mutation,
            corrupt_log=corrupt_log,
            corrupt_stream_after=corrupt_stream_after,
            runtime_manifest_override=runtime_manifest_override,
            fake_executable=fake_executable,
            timeout=timeout,
            disposable_root=disposable_root,
            guard_dir=guard_dir,
        )
        guard.assert_clean()
        return rec


def make_d1_readiness_candidate(root: Path, evidence_root: Path, *, independent_review: Any = None) -> dict[str, Any]:
    if independent_review is not None:
        raise ValueError("independent review custody belongs to dispatcher/manager")
    repo, edir = Path(root).resolve(), Path(evidence_root).resolve()
    if LIVE_ADMISSION_AVAILABLE:
        raise D1Error("general holdout live admission must remain disabled")

    rec = readback_d1_record(edir, root=repo)
    if rec.get("probe_id") != PROBE_ID:
        raise D1Error(f"readback probe_id mismatch: {rec.get('probe_id')}")
    sid = readiness.source_identity(readiness.make_seal(repo)["files"])
    if rec.get("source_identity") != sid:
        raise D1Error("record source identity differs from repository source")

    # Reject if ANY instrumented provenance is present
    auth_data = json.loads((edir / "authority.json").read_bytes())
    if auth_data.get("schema") != LIVE_AUTHORITY_SCHEMA:
        raise D1AuthorityError(f"readiness candidate requires live authority schema {LIVE_AUTHORITY_SCHEMA}, got {auth_data.get('schema')}")
    preregistration.verify_bindings(repo)
    preregistration.verify_promotions(repo)

    if (edir / "provider-guard-receipt.json").exists():
        raise D1Error("readiness candidate rejects provider-guard-receipt: instrumented provenance forbidden")
    if (edir / "provider-guard").exists():
        raise D1Error("readiness candidate rejects provider-guard directory: instrumented provenance forbidden")
    if (edir / "instrumented-executed-runtime.json").exists():
        raise D1Error("readiness candidate rejects instrumented-executed-runtime: instrumented provenance forbidden")
    if rec.get("execution_kind") != "live-provider":
        raise D1Error("readiness candidate requires live-provider evidence; instrumented evidence rejected as live D1")
    if rec.get("executable_evidence", {}).get("is_instrumented") is True:
        raise D1Error("readiness candidate rejects instrumented executable evidence")
    if "fake-bin" in str(rec.get("executable_evidence", {}).get("physical_executable", "")):
        raise D1Error("readiness candidate rejects fake-bin executable path")
    if rec.get("d1_status") != "qualified":
        raise D1Error(f"readiness candidate requires qualified D1 status, observed: {rec.get('d1_status')}")

    # Check external ledger transport kind and receipt digests
    croot = Path(auth_data["custody_root"]).resolve()
    attempt_key = derive_attempt_key(auth_data, sid)
    ledger_path = croot / "consumed-attempts" / f"{attempt_key}.json"
    if not ledger_path.is_file():
        raise D1Error("consumed attempt ledger missing in custody root")
    ledger_data = json.loads(ledger_path.read_bytes())
    if ledger_data.get("authority_schema") != LIVE_AUTHORITY_SCHEMA:
        raise D1AuthorityError("readiness candidate requires live authority schema in ledger")
    if ledger_data.get("transport_kind") != PRODUCTION_TRANSPORT_KIND:
        raise D1Error("readiness candidate requires production-provider transport ledger")
    if ledger_data.get("status") != "start_finalized":
        raise D1Error("readiness candidate requires start_finalized custody ledger")
    if not isinstance(ledger_data.get("pid"), int) or ledger_data["pid"] <= 0:
        raise D1Error("readiness candidate requires valid PID in custody ledger")

    launch_contract = json.loads((edir / "launch-contract.json").read_bytes())
    start_receipt = json.loads((edir / "provider-start-receipt.json").read_bytes())
    if start_receipt.get("transport_class") != "production-provider":
        raise D1Error("readiness candidate rejects non-production transport class in provider-start receipt")
    if start_receipt.get("provider_guard_identity") is not None or start_receipt.get("guard_receipt_digest") is not None:
        raise D1Error("readiness candidate rejects guard identity in provider-start receipt")
    if ledger_data.get("launch_contract_digest") != _sha256(_canonical_bytes(launch_contract)):
        raise D1Error("launch contract digest mismatch in custody ledger")
    if ledger_data.get("provider_start_receipt_digest") != _sha256(_canonical_bytes(start_receipt)):
        raise D1Error("provider start receipt digest mismatch in custody ledger")

    gates = {
        "d1_record_recomputed": True,
        "d1_probe_id_valid": rec.get("probe_id") == PROBE_ID,
        "source_identity_current": rec.get("source_identity") == sid,
        "holdout_admission_disabled": not LIVE_ADMISSION_AVAILABLE,
        "manager_review_required": True,
        "live_d1_qualified": True,
    }
    return {
        "schema": READINESS_CANDIDATE_SCHEMA,
        "phase": "APG166Q",
        "probe_id": PROBE_ID,
        "source_identity": sid,
        "gates": gates,
        "d1_mechanical_validation": "live-qualified",
        "provider_free_d1_seam_qualified": rec.get("provider_free_d1_seam_qualified", False),
        "d1_status": rec.get("d1_status", "not-run"),
        "execution_kind": rec.get("execution_kind"),
        "provider_free_package_inputs": "current",
        "manager_review_required": True,
        "prerequisites_ready": False,
        "live_holdout_authorized": False,
        "h_main_gate": False,
        "v0130_i_authorized": False,
        "blockers": ["manager_review_required", "independent_review_required", "live_d1_unauthorized"],
        "boundary": "Mechanical validation candidate only. External independent review and manager authorization required. No live holdout authorized.",
    }
