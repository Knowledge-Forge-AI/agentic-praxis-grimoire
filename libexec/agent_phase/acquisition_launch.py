"""Explicit caller-owned adaptive launch seam; no live provider qualification.

The ordinary dispatcher supplies no qualified projection and therefore never
probes or starts this optional server. Instrumented/native callers may attach
this seam only alongside independently qualified selective projection and read
authority. The provider attempt is invoked once by context_adapter.invoke.
"""
from __future__ import annotations

import json
import base64
import hashlib
import os
from pathlib import Path
import subprocess
import selectors
import time
from types import SimpleNamespace
import stat

PROTOCOL = "2025-11-25"
MAX_MESSAGE = 1 << 20


def _json(data):
    from .acquisition_records import _pairs
    return json.loads(data, object_pairs_hook=_pairs, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("invalid JSON constant")))


def _verify_recovery(run_dir, selected):
    """Verify the native materialization through direct run-owned descriptors."""
    location = selected["materialized_path"]
    if not isinstance(location, str) or not location.startswith("acquisitions/skills/"):
        raise ValueError("invalid recovery location")
    snapshot = selected["selection"]["snapshot"]
    body = base64.b64decode(snapshot["body"], validate=True)
    if hashlib.sha256(body).hexdigest() != selected["selection"]["source_sha256"]:
        raise ValueError("recovery body identity mismatch")
    files = {**(snapshot.get("support") or {}), "SKILL.md": snapshot["body"]}
    for name, encoded in files.items():
        relative = location + "/" + name
        parts = relative.split("/")
        if any(part in ("", ".", "..") or "\\" in part for part in parts):
            raise ValueError("unsafe recovery path")
        owner = os.open(run_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in parts[:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=owner)
                os.close(owner)
                owner = child
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=owner)
            with os.fdopen(fd, "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError("nonregular recovery snapshot")
                observed = stream.read(MAX_MESSAGE + 1)
            if len(observed) > MAX_MESSAGE or observed != base64.b64decode(encoded, validate=True):
                raise ValueError("recovery snapshot mismatch")
        finally:
            os.close(owner)


def _capture(argv, input_bytes=b""):
    """Bound both captured streams while enforcing one finite child deadline."""
    child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    output, errors = bytearray(), bytearray()
    try:
        child.stdin.write(input_bytes)
        child.stdin.close()
        selector.register(child.stdout, selectors.EVENT_READ, output)
        selector.register(child.stderr, selectors.EVENT_READ, errors)
        deadline = time.monotonic() + 10
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("MCP prelaunch timeout")
            for key, _ in selector.select(min(remaining, 0.1)):
                data = os.read(key.fileobj.fileno(), 8192)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                key.data.extend(data)
                if len(key.data) > MAX_MESSAGE:
                    raise ValueError("MCP prelaunch output bound")
        child.wait(timeout=max(0.01, deadline - time.monotonic()))
        return SimpleNamespace(returncode=child.returncode, stdout=bytes(output), stderr=bytes(errors))
    finally:
        selector.close()
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
        child.stdout.close()
        child.stderr.close()
        if not child.stdin.closed:
            child.stdin.close()


def _new(run_dir, name, value):
    # Bind the one installed-CLI retention owner in source and frozen controllers.
    # The owner has no import-time package/runtime dependency.
    import importlib.util
    source = Path(__file__).resolve().parents[2] / "src/agentic_praxis_grimoire/acquisition.py"
    spec = importlib.util.spec_from_file_location("_apgr_authority_retention", source)
    if spec is None or spec.loader is None:
        raise ValueError("acquisition retention owner unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    alias = name if name.startswith("acquisition-server-") else None
    retained = module.retain_authority(Path(run_dir), value, alias=alias)
    return str(Path(run_dir) / retained)


class AcquisitionLaunch:
    """Bounded adapter over an explicit native CLI and selected recovery IDs.

    `seam` names the actual argv contract, not a provider-name capability guess.
    These are native argv contracts; wrapper/profile argv is not interchangeable.
    This class does not attest selective projection or model consumption.
    """
    def __init__(self, *, binary, catalog, candidates, seam, native_read_authorized):
        self.binary = Path(binary)
        self.catalog = catalog
        self.candidates = list(candidates)
        self.seam = seam
        self.native_read_authorized = native_read_authorized

    def prepare(self, record, run_dir, argv):
        if self.seam == "claude-profile-readonly":
            from .claude_acquisition_argv import prepare_argv
            argv = prepare_argv(argv)  # Before any authority or one-use artifact.
        if not self.native_read_authorized or self.seam not in ("codex-native", "claude-native-readonly", "claude-profile-readonly"):
            raise ValueError("MCP independent read or native launch seam unavailable")
        if not self.binary.is_absolute() or not self.binary.is_file() or not os.access(self.binary, os.X_OK):
            raise ValueError("MCP executable unavailable")
        if not self.candidates or len(self.candidates) > 128 or len(set(self.candidates)) != len(self.candidates):
            raise ValueError("MCP recovery candidate bound")
        selected_ids = set(self.candidates)
        for relation in self.catalog.get("overrides") or []:
            if relation.get("requested") in selected_ids:
                selected_ids.add(relation.get("selected"))
        if any(snapshot.get("qualified_id") not in selected_ids for snapshot in self.catalog.get("snapshots") or []):
            raise ValueError("MCP authority includes unrelated source bodies")
        # Caller supplies captured source snapshots and override relationships.
        # No roots, environment, global settings or current catalog are read.
        authority = {"run_dir": str(run_dir), "run_id": record["run_id"],
                     "binding_id": record["binding_id"], "attempt_id": record["attempt_id"],
                     "consumer": "claude" if self.seam.startswith("claude-") else "codex",
                     "catalog": self.catalog, "allowed_ids": self.candidates}
        suffix = hashlib.sha256(json.dumps([record[k] for k in ("run_id", "binding_id", "attempt_id")]).encode()).hexdigest()
        initial = _new(run_dir, "acquisition-prelaunch-" + suffix + ".json", {**authority, "preparation": True})
        recovery = []
        recovery_files = {}
        for candidate in self.candidates:
            result = _capture([str(self.binary), "skills", "acquire", candidate, "--prepare-only", "--config", initial])
            if result.returncode or len(result.stdout) > MAX_MESSAGE:
                raise ValueError("MCP recovery preparation failed")
            selected = _json(result.stdout)
            _verify_recovery(run_dir, selected)
            snapshot = selected["selection"]["snapshot"]
            for name, encoded in {**(snapshot.get("support") or {}), "SKILL.md": snapshot["body"]}.items():
                data = base64.b64decode(encoded, validate=True)
                recovery_files[selected["materialized_path"] + "/" + name] = {
                    "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            recovery.append({"id": candidate, "path": selected["materialized_path"] + "/SKILL.md",
                             "sha256": selected["selection"]["source_sha256"],
                             "bytes": len(base64.b64decode(selected["selection"]["snapshot"]["body"], validate=True)),
                             "content_identity": selected["selection"]["content_identity"]})
        config_name = "acquisition-server-" + suffix + ".json"
        config = str(Path(run_dir) / config_name)
        self.pending = (run_dir, config_name, authority)
        command = [str(self.binary), "mcp", "serve", "--config", config]
        probe = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": PROTOCOL, "capabilities": {}, "clientInfo": {"name": "apgr-prelaunch", "version": "1"}}}
        result = _capture([str(self.binary), "mcp", "serve", "--config", initial], (json.dumps(probe) + "\n").encode())
        if result.returncode or len(result.stdout) > MAX_MESSAGE:
            raise ValueError("MCP prelaunch failed")
        response = _json(result.stdout)
        if response.get("jsonrpc") != "2.0" or response.get("id") != 1 or response.get("result", {}).get("protocolVersion") != PROTOCOL:
            raise ValueError("MCP protocol mismatch")
        if response["result"].get("capabilities") != {"tools": {}, "resources": {}}:
            raise ValueError("MCP capability mismatch")
        declaration = {"command": str(self.binary), "args": command[1:]}
        elected = list(argv)
        if self.seam == "codex-native":
            # Preserve every existing argv element; only the named run-owned
            # MCP server declaration is added before the stdin task marker.
            if not elected or elected[-1] != "-" or any("mcp_servers.apgr" in a for a in elected):
                raise ValueError("unsupported Codex argv seam")
            literal = "{command=" + json.dumps(declaration["command"]) + ",args=" + json.dumps(declaration["args"]) + "}"
            elected[-1:-1] = ["-c", "mcp_servers.apgr=" + literal]
        elif self.seam == "claude-profile-readonly":
            from .claude_acquisition_handoff import OPTION, split_option
            if (not elected or Path(elected[0]).name != "claude-profile"
                    or "--read-only" not in elected or "-p" not in elected
                    or split_option(elected)[1] is not None):
                raise ValueError("unsupported Claude profile seam")
            launch_config = _new(run_dir, "acquisition-mcp-" + suffix + ".json", {"mcpServers": {"apgr": declaration}})
            handoff = str(Path(run_dir) / ("acquisition-wrapper-" + suffix + ".json"))
            self.wrapper_handoff = (handoff, launch_config)
            elected.extend([OPTION, handoff])
        else:
            if elected.count("--tools") != 1 or any(a.startswith(("--mcp-config", "--tools=")) for a in elected):
                raise ValueError("unsupported Claude argv seam")
            at = elected.index("--tools") + 1
            if at >= len(elected) or elected[at] != "Read":
                raise ValueError("Claude native readonly tools must be exactly Read")
            elected[at] += ",mcp__apgr__skill_search,mcp__apgr__skill_acquire,mcp__apgr__context_explain"
            # Tool availability and noninteractive permission are separate.
            # Preserve caller-owned native Read scope; grant only these MCP calls.
            if any(a.startswith(("--allowed-tools", "--allowedTools")) for a in elected):
                raise ValueError("unsupported Claude permission seam")
            elected.extend(["--allowed-tools", "mcp__apgr__skill_search,mcp__apgr__skill_acquire,mcp__apgr__context_explain"])
            launch_config = _new(run_dir, "acquisition-mcp-" + suffix + ".json", {"mcpServers": {"apgr": declaration}})
            elected.extend(["--mcp-config", launch_config, "--strict-mcp-config"])
        details = {"protocol": PROTOCOL, "config": config, "recovery": recovery,
                         "status": "prelaunch_available", "model_observed": None,
                         "replay_authorized": False, "live_provider_qualified": False}
        if self.seam == "claude-profile-readonly":
            details["wrapper_handoff"] = handoff
            from .claude_recovery_authority import capture
            details["recovery_authority"] = capture(Path(run_dir), recovery_files)
        return elected, details

    def finalize(self, record):
        run_dir, name, authority = self.pending
        _new(run_dir, name, {**authority, "context_plan": record})
        if self.seam == "claude-profile-readonly":
            from .claude_acquisition_handoff import create
            path, config = self.wrapper_handoff
            create(path, record, config, self.binary)
