"""Provider-free qualification of the APGR acquisition recovery subtree.

This owner exercises the real APGR CLI and MCP acquisition engine with a
synthetic client.  It deliberately has no provider or model execution seam:
the only child process it may start is the manifest-bound APGR executable.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import stat
import subprocess
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "apg.h-recovery-qualification/v1"
MCP_PROTOCOL = "2025-11-25"
MAX_OUTPUT = 1 << 20
DEFAULT_SKILL = "apgr:go-language-profile"
READBACK_SCHEMA = "apg.h-recovery-readback/v1"
_SKILL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_REQUIRED_NETWORK_POLICY = {
    "GOPROXY": "off",
    "GOSUMDB": "off",
    "GONOSUMDB": "*",
    "GOTOOLCHAIN": "local",
    "npm_config_offline": "true",
    "npm_config_prefer_offline": "true",
    "npm_config_audit": "false",
    "npm_config_fund": "false",
    "PIP_NO_INDEX": "1",
    "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    "PYTHONNOUSERSITE": "1",
    "NO_PROXY": "*",
    "HTTP_PROXY": "",
    "HTTPS_PROXY": "",
    "ALL_PROXY": "",
}
_FORBIDDEN_AMBIENT_NETWORK_KEYS = frozenset({
    "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    "ftp_proxy", "rsync_proxy",
})
_STREAM_PATHS = frozenset({
    "recovery-custody/preparation.stdout",
    "recovery-custody/preparation.stderr",
    "recovery-custody/mcp.stdin",
    "recovery-custody/mcp.stdout",
    "recovery-custody/mcp.stderr",
})


class RecoveryQualificationError(ValueError):
    """The provider-free recovery contract was not satisfied."""


def _fail(message: str) -> None:
    raise RecoveryQualificationError(message)


def _physical(path: Path, *, directory: bool = False) -> Path:
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        _fail("recovery path must be an absolute physical path")
    value = path.lstat()
    if directory:
        valid = stat.S_ISDIR(value.st_mode) and not stat.S_ISLNK(value.st_mode)
    else:
        valid = stat.S_ISREG(value.st_mode) and not stat.S_ISLNK(value.st_mode)
    if not valid:
        _fail("recovery path is not a direct regular path")
    return path


def _destination(path: str | Path) -> Path:
    value = Path(path)
    if not value.is_absolute() or value.resolve() != value:
        _fail("recovery destination must be an absolute physical path")
    if value.exists() or value.is_symlink():
        _physical(value, directory=True)
        if any(value.iterdir()):
            _fail("recovery destination must be empty")
    else:
        value.mkdir(mode=0o700, parents=False)
    _physical(value, directory=True)
    if stat.S_IMODE(value.stat().st_mode) & 0o077:
        _fail("recovery destination must be private")
    return value


def _source(path: str | Path) -> Path:
    value = Path(path)
    return _physical(value, directory=True)


def _executable(path: str | Path) -> Path:
    value = _physical(Path(path))
    if not os.access(value, os.X_OK):
        _fail("manifest-bound APGR executable is not executable")
    return value


def _executable_identity(path: Path) -> dict[str, Any]:
    value = _physical(path)
    metadata = value.stat()
    data = value.read_bytes()
    return {
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "mode": stat.S_IMODE(metadata.st_mode),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _environment(value: Mapping[str, str] | None) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        _fail("explicit manifest-bound environment is required")
    result = dict(value)
    if any(not isinstance(key, str) or not isinstance(item, str) for key, item in result.items()):
        _fail("manifest-bound environment must contain only strings")
    forbidden = ("TOKEN", "SECRET", "PASSWORD", "COOKIE", "PRIVATE_KEY", "API_KEY")
    if any(any(part in key.upper() for part in forbidden) for key in result):
        _fail("manifest-bound environment must not carry credentials")
    if _FORBIDDEN_AMBIENT_NETWORK_KEYS.intersection(result):
        _fail("manifest-bound environment must not carry lowercase ambient proxy variables")
    if not result.get("PATH"):
        _fail("manifest-bound environment must bind PATH")
    if any(result.get(key) != expected for key, expected in _REQUIRED_NETWORK_POLICY.items()):
        _fail("manifest-bound environment must declare configured offline policy")
    if any(not Path(part).is_absolute() for part in result["PATH"].split(os.pathsep)):
        _fail("manifest-bound PATH must contain absolute directories")
    for key in ("HOME", "TMPDIR", "TMP", "TEMP"):
        if key not in result:
            _fail(f"manifest-bound environment must bind {key}")
        try:
            _physical(Path(result[key]), directory=True)
        except (OSError, RecoveryQualificationError):
            _fail(f"manifest-bound environment {key} is not physical")
    return result


def _qualified_skill(value: str) -> str:
    if not isinstance(value, str) or value.count(":") != 1:
        _fail("provider-free recovery requires one qualified APGR skill")
    namespace, name = value.split(":", 1)
    if namespace != "apgr" or _SKILL_NAME.fullmatch(name) is None:
        _fail("provider-free recovery skill identity is unsafe")
    return value


def _safe_relative(value: str, *, prefix: str | None = None) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        _fail("unsafe acquisition relative path")
    path = PurePosixPath(value)
    if value != path.as_posix() or path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        _fail("unsafe acquisition relative path")
    if prefix is not None and (not path.parts or path.parts[0] != prefix):
        _fail("acquisition path outside the run-owned subtree")
    return path


def _scope_args(
    destination: Path,
    *,
    run_id: str,
    binding_id: str,
    attempt_id: str,
    consumer: str = "claude",
) -> list[str]:
    return [
        "--run-dir", str(destination),
        "--run-id", run_id,
        "--binding-id", binding_id,
        "--attempt-id", attempt_id,
        "--consumer", consumer,
    ]


def _run(
    argv: list[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    input_bytes: bytes = b"",
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            argv,
            cwd=str(cwd),
            env=dict(environment),
            input=input_bytes,
            capture_output=True,
            timeout=20,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        _fail(f"APGR acquisition process failed: {type(error).__name__}")
    if len(result.stdout) > MAX_OUTPUT or len(result.stderr) > MAX_OUTPUT:
        _fail("APGR acquisition output exceeded the bounded capture")
    return result


def _require_success(result: subprocess.CompletedProcess[bytes], label: str) -> None:
    if result.returncode != 0:
        _fail(f"{label} returned {result.returncode}")


def _custody_root(destination: Path) -> Path:
    root = destination / "recovery-custody"
    root.mkdir(mode=0o700, exist_ok=False)
    _physical(root, directory=True)
    if stat.S_IMODE(root.stat().st_mode) & 0o077:
        _fail("recovery custody root must be private")
    return root


def _retain_stream(destination: Path, custody_root: Path, relative: str, data: bytes) -> dict[str, Any]:
    path = destination / _safe_relative(relative)
    if path.parent != custody_root:
        _fail("recovery stream custody path escaped its private root")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as error:
        _fail(f"recovery stream custody could not be created: {type(error).__name__}")
    try:
        os.fchmod(descriptor, 0o600)
        offset = 0
        while offset < len(data):
            written = os.write(descriptor, data[offset:])
            if written <= 0:
                _fail("recovery stream custody write made no progress")
            offset += written
        os.fsync(descriptor)
    except OSError as error:
        _fail(f"recovery stream custody write failed: {type(error).__name__}")
    finally:
        os.close(descriptor)
    _physical(path)
    try:
        directory_descriptor = os.open(
            custody_root,
            os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except OSError as error:
        _fail(f"recovery stream custody directory sync failed: {type(error).__name__}")
    metadata = path.stat()
    if stat.S_IMODE(metadata.st_mode) != 0o600 or path.read_bytes() != data:
        _fail("recovery stream custody readback changed")
    return {
        "path": str(path.relative_to(destination)),
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "mode": 0o600,
    }


def _json_clone(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, sort_keys=True))


def verify_stream_custody(destination: str | Path, qualification: Mapping[str, Any]) -> dict[str, Any]:
    """Verify retained APGR streams without entering the acquisition subtree."""
    root = _physical(Path(destination), directory=True)
    records = qualification.get("stream_custody")
    if not isinstance(records, list) or len(records) != len(_STREAM_PATHS):
        _fail("recovery stream custody is incomplete")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            _fail("recovery stream custody record is malformed")
        relative = record.get("path")
        if not isinstance(relative, str) or relative not in _STREAM_PATHS or relative in seen:
            _fail("recovery stream custody path is invalid")
        seen.add(relative)
        if any(part == "acquisitions" for part in _safe_relative(relative).parts):
            _fail("recovery stream custody entered acquisitions")
        path = root / _safe_relative(relative)
        try:
            _physical(path)
        except (OSError, RecoveryQualificationError):
            _fail("recovery stream custody file is unavailable")
        metadata = path.stat()
        if stat.S_IMODE(metadata.st_mode) != 0o600:
            _fail("recovery stream custody mode changed")
        if record.get("device") != metadata.st_dev or record.get("inode") != metadata.st_ino:
            _fail("recovery stream custody identity changed")
        data = path.read_bytes()
        if record.get("bytes") != len(data) or record.get("sha256") != hashlib.sha256(data).hexdigest():
            _fail("recovery stream custody bytes changed")
    if seen != _STREAM_PATHS:
        _fail("recovery stream custody inventory is incomplete")
    return {"status": "valid", "paths": sorted(seen), "streams": len(seen)}


def _json_output(result: subprocess.CompletedProcess[bytes], label: str) -> dict[str, Any]:
    if result.stderr:
        _fail(f"{label} wrote unexpected diagnostics")
    try:
        value = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(f"{label} did not return one JSON object: {type(error).__name__}")
    if not isinstance(value, dict):
        _fail(f"{label} returned a non-object")
    return value


def _source_files(source_root: Path, selected_identity: str, support: Mapping[str, bytes]) -> dict[str, bytes]:
    selected_identity = _qualified_skill(selected_identity)
    _, skill_name = selected_identity.split(":", 1)
    skill_root = source_root / "skills" / skill_name
    _physical(skill_root, directory=True)
    source = _physical(skill_root / "SKILL.md")
    expected = {"SKILL.md": source.read_bytes()}
    if expected["SKILL.md"] != support.get("SKILL.md", expected["SKILL.md"]):
        _fail("APGR body does not match the repository-owned skill")
    for name, data in support.items():
        if name == "SKILL.md":
            continue
        relative = _safe_relative(name)
        path = _physical(skill_root.joinpath(*relative.parts))
        if path.read_bytes() != data:
            _fail("APGR support snapshot does not match the repository-owned skill")
        expected[name] = data
    return expected


def _selection_files(source_root: Path, value: Mapping[str, Any], requested_id: str) -> tuple[str, dict[str, bytes], dict[str, dict[str, Any]]]:
    requested_id = _qualified_skill(requested_id)
    selection = value.get("selection")
    if not isinstance(selection, Mapping):
        _fail("APGR acquisition response lacks selection")
    selected = selection.get("selected_identity")
    if not isinstance(selected, str):
        _fail("APGR acquisition response lacks selected identity")
    selected = _qualified_skill(selected)
    if selection.get("requested_identity") != requested_id:
        _fail("APGR acquisition response changed the requested identity")
    snapshot = selection.get("snapshot")
    if not isinstance(snapshot, Mapping) or not isinstance(snapshot.get("body"), str):
        _fail("APGR acquisition response lacks a body snapshot")
    try:
        body = base64.b64decode(snapshot["body"], validate=True)
    except (ValueError, TypeError):
        _fail("APGR body snapshot is not valid base64")
    support_value = snapshot.get("support") or {}
    if not isinstance(support_value, Mapping):
        _fail("APGR support snapshot is not an object")
    support: dict[str, bytes] = {}
    for name, encoded in support_value.items():
        if not isinstance(name, str) or not isinstance(encoded, str):
            _fail("APGR support snapshot is malformed")
        _safe_relative(name)
        try:
            support[name] = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError):
            _fail("APGR support snapshot is not valid base64")
    source_files = _source_files(source_root, selected, {**support, "SKILL.md": body})
    source_sha = selection.get("source_sha256")
    if source_sha != hashlib.sha256(body).hexdigest():
        _fail("APGR body source identity is inconsistent")
    materialized = value.get("materialized_path")
    materialized_path = _safe_relative(materialized, prefix="acquisitions")
    if len(materialized_path.parts) < 4 or materialized_path.parts[1] != "skills":
        _fail("APGR materialized path is outside acquisitions/skills")
    expected: dict[str, dict[str, Any]] = {}
    for name, data in source_files.items():
        relative = f"{materialized_path.as_posix()}/{name}"
        _safe_relative(relative, prefix="acquisitions")
        expected[relative] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return materialized_path.as_posix(), source_files, expected


def _mcp_message(number: int, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"jsonrpc": "2.0", "id": number, "method": method}
    if params is not None:
        value["params"] = dict(params)
    return value


def _mcp_wire(skill_id: str) -> bytes:
    messages: list[dict[str, Any]] = [
        _mcp_message(1, "initialize", {
            "protocolVersion": MCP_PROTOCOL,
            "capabilities": {},
            "clientInfo": {"name": "apg-provider-free-recovery", "version": "1"},
        }),
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        _mcp_message(2, "tools/list"),
    ]
    for number in (3, 4):
        messages.append(_mcp_message(number, "tools/call", {
            "name": "skill_acquire", "arguments": {"id": skill_id},
        }))
    messages.append(_mcp_message(5, "resources/read", {"uri": f"apgr://skills/{skill_id}"}))
    return b"".join(json.dumps(message, sort_keys=True).encode() + b"\n" for message in messages)


def _mcp_responses(result: subprocess.CompletedProcess[bytes]) -> list[dict[str, Any]]:
    if result.stderr:
        _fail("APGR MCP wrote unexpected diagnostics")
    responses: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        try:
            value = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            _fail(f"APGR MCP returned malformed JSON: {type(error).__name__}")
        if not isinstance(value, dict):
            _fail("APGR MCP returned a non-object response")
        responses.append(value)
    if len(responses) != 5:
        _fail("APGR MCP did not return the complete synthetic-client response set")
    if any("error" in response for response in responses):
        _fail("APGR MCP synthetic client received an error")
    return responses


def _verify_mcp_responses(
    responses: list[Mapping[str, Any]],
    *,
    requested_id: str,
    materialized_path: str,
    source_files: Mapping[str, bytes],
    expected_files: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    expected_ids = [1, 2, 3, 4, 5]
    if [response.get("id") for response in responses] != expected_ids:
        _fail("APGR MCP response IDs are incomplete or reordered")
    if responses[0].get("result", {}).get("protocolVersion") != MCP_PROTOCOL:
        _fail("APGR MCP protocol negotiation did not complete")
    tools = responses[1].get("result", {}).get("tools")
    if not isinstance(tools, list) or [tool.get("name") for tool in tools] != ["skill_search", "skill_acquire", "context_explain"]:
        _fail("APGR MCP discovery did not expose the frozen tool set")
    repeats: list[bool] = []
    for response in responses[2:4]:
        content = response.get("result", {}).get("content")
        if not isinstance(content, list) or len(content) != 2:
            _fail("APGR MCP acquisition response lacks the body/support envelope")
        if content[0].get("type") != "text" or content[0].get("text", "").encode() != source_files["SKILL.md"]:
            _fail("APGR MCP body differs from the source-owned skill")
        try:
            envelope = json.loads(content[1]["text"])
        except (KeyError, TypeError, json.JSONDecodeError):
            _fail("APGR MCP support envelope is malformed")
        if envelope.get("requested_identity") != requested_id or envelope.get("materialized_path") != materialized_path:
            _fail("APGR MCP support envelope changed the bound identity")
        if envelope.get("is_repeat_delivery") not in (False, True):
            _fail("APGR MCP repeat status is missing")
        repeats.append(envelope["is_repeat_delivery"])
        support = envelope.get("support") or {}
        if set(support) != set(source_files) - {"SKILL.md"}:
            _fail("APGR MCP support inventory differs from the source snapshot")
        for name, encoded in support.items():
            try:
                decoded = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError):
                _fail("APGR MCP support envelope is not valid base64")
            if decoded != source_files[name]:
                _fail("APGR MCP support bytes changed")
    if repeats != [False, True]:
        _fail("APGR MCP did not demonstrate one pre-materialized repeat")
    resource = responses[4].get("result", {}).get("contents")
    if not isinstance(resource, list) or len(resource) != 1:
        _fail("APGR MCP resource read is incomplete")
    try:
        resource_value = json.loads(resource[0]["text"])
    except (KeyError, TypeError, json.JSONDecodeError):
        _fail("APGR MCP resource read is malformed")
    if resource_value.get("materialized_path") != materialized_path:
        _fail("APGR MCP resource path differs from the retained authority")
    body = resource_value.get("selection", {}).get("snapshot", {}).get("body")
    if not isinstance(body, str) or base64.b64decode(body, validate=True) != source_files["SKILL.md"]:
        _fail("APGR MCP resource body differs from the source-owned skill")
    return {
        "status": "complete",
        "acquisition_repeats": repeats,
        "resource_read": True,
        "expected_files": sorted(expected_files),
    }


def _authority_summary(authority: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "valid",
        "file_paths": sorted(authority["files"]),
        "directory_paths": sorted(authority["directories"]),
        "file_count": len(authority["files"]),
        "directory_count": len(authority["directories"]),
    }


def verify_recovery_authority(destination: str | Path, qualification: Mapping[str, Any]) -> dict[str, Any]:
    """Re-read a retained authority and fail if any subtree identity changed."""
    from agent_phase.claude_recovery_authority import verify

    authority = qualification.get("prelaunch_authority") or qualification.get("recovery_authority")
    if not isinstance(authority, Mapping):
        _fail("retained recovery authority is missing")
    try:
        verify(Path(destination), authority)
    except (OSError, ValueError, KeyError, TypeError) as error:
        _fail(f"recovery authority changed: {type(error).__name__}")
    return _authority_summary(authority)


def qualify_recovery(
    source_root: str | Path,
    destination: str | Path,
    *,
    apgr_executable: str | Path,
    environment: Mapping[str, str],
    skill_id: str = DEFAULT_SKILL,
    run_id: str = "h-recovery",
    binding_id: str = "provider-free-recovery",
    attempt_id: str = "one",
) -> dict[str, Any]:
    """Qualify one immutable, pre-materialized APGR recovery subtree.

    ``environment`` is mandatory and is passed verbatim to every APGR child;
    no ambient environment or provider executable is consulted.
    """
    root = _source(source_root)
    requested_skill = _qualified_skill(skill_id)
    executable = _executable(apgr_executable)
    executable_identity = _executable_identity(executable)
    env = _environment(environment)
    environment_digest = hashlib.sha256(
        json.dumps(sorted(env.items()), separators=(",", ":")).encode()
    ).hexdigest()
    if not all(isinstance(value, str) and value for value in (run_id, binding_id, attempt_id)):
        _fail("recovery scope identifiers are required")
    destination_path = _destination(destination)
    custody_root = _custody_root(destination_path)

    scope = _scope_args(destination_path, run_id=run_id, binding_id=binding_id, attempt_id=attempt_id)
    command_identity = {
        "executable": str(executable),
        **executable_identity,
        "operations": ["skills acquire --prepare-only", "mcp serve"],
    }
    from agent_phase.claude_recovery_authority import capture

    prepare = _run(
        [str(executable), "skills", "acquire", requested_skill, "--prepare-only", *scope, "--project-root", str(root)],
        cwd=root,
        environment=env,
    )
    stream_custody = [
        _retain_stream(destination_path, custody_root, "recovery-custody/preparation.stdout", prepare.stdout),
        _retain_stream(destination_path, custody_root, "recovery-custody/preparation.stderr", prepare.stderr),
    ]
    _require_success(prepare, "APGR preparation")
    prepared = _json_output(prepare, "APGR preparation")
    if _executable_identity(executable) != executable_identity:
        _fail("manifest-bound APGR executable changed during preparation")
    materialized_path, source_files, expected_files = _selection_files(root, prepared, requested_skill)
    try:
        authority = capture(destination_path, expected_files)
    except (OSError, ValueError, KeyError, TypeError) as error:
        _fail(f"pre-materialized recovery subtree is not exact: {type(error).__name__}")
    before_summary = _authority_summary(authority)

    mcp_input = _mcp_wire(requested_skill)
    mcp = _run(
        [str(executable), "mcp", "serve", *scope, "--project-root", str(root)],
        cwd=root,
        environment=env,
        input_bytes=mcp_input,
    )
    stream_custody.extend([
        _retain_stream(destination_path, custody_root, "recovery-custody/mcp.stdin", mcp_input),
        _retain_stream(destination_path, custody_root, "recovery-custody/mcp.stdout", mcp.stdout),
        _retain_stream(destination_path, custody_root, "recovery-custody/mcp.stderr", mcp.stderr),
    ])
    _require_success(mcp, "APGR MCP")
    responses = _mcp_responses(mcp)
    if _executable_identity(executable) != executable_identity:
        _fail("manifest-bound APGR executable changed during MCP qualification")
    mcp_evidence = _verify_mcp_responses(
        responses,
        requested_id=requested_skill,
        materialized_path=materialized_path,
        source_files=source_files,
        expected_files=expected_files,
    )
    try:
        from agent_phase.claude_recovery_authority import verify

        postrun_authority = verify(destination_path, authority)
    except (OSError, ValueError, KeyError, TypeError) as error:
        _fail(f"recovery subtree changed during MCP qualification: {type(error).__name__}")
    after_summary = _authority_summary(postrun_authority)
    if before_summary != after_summary:
        _fail("recovery authority summary changed")
    custody_readback = verify_stream_custody(destination_path, {"stream_custody": stream_custody})
    prelaunch_authority = _json_clone(authority)
    postrun_readback = {
        "schema": READBACK_SCHEMA,
        "status": "valid",
        "authority": _json_clone(postrun_authority),
        "summary": after_summary,
    }
    return {
        "schema": SCHEMA,
        "status": "complete",
        "provider_free": True,
        "network_policy": "configured_offline_not_os_enforced",
        "network_disabled": False,
        "provider_invocations": 0,
        "model_invocations": 0,
        "skill_id": requested_skill,
        "materialized_path": materialized_path,
        "growth_policy": "immutable-pre-materialized",
        "command": command_identity,
        "environment_digest": environment_digest,
        "preparation": {"returncode": prepare.returncode, "stdout_bytes": len(prepare.stdout), "stderr_bytes": len(prepare.stderr)},
        "mcp": {"returncode": mcp.returncode, "stdout_bytes": len(mcp.stdout), "stderr_bytes": len(mcp.stderr), **mcp_evidence},
        "subtree": {"unchanged": True, "files": before_summary["file_paths"], "directories": before_summary["directory_paths"]},
        "stream_custody": stream_custody,
        "stream_readback": custody_readback,
        "prelaunch_authority": prelaunch_authority,
        "postrun_readback": postrun_readback,
        # Retain the historical key for callers that already consume it; it is
        # a separate copy and never becomes the post-run readback record.
        "recovery_authority": _json_clone(prelaunch_authority),
        "read_authority": after_summary,
    }


__all__ = [
    "DEFAULT_SKILL",
    "RecoveryQualificationError",
    "qualify_recovery",
    "verify_recovery_authority",
    "verify_stream_custody",
]
