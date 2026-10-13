"""Source-owned wrapper/native argv distinction for the bounded D1 route."""
from pathlib import Path


def expected_native_argv(root: Path, outer_argv: list[str], executable: str) -> list[str]:
    from claude_vc_profile import parse_wrapper_arguments, read_only_contract, resolve_profile, extract_read_only_tools
    from agent_source_guidance import source_guidance
    profile = outer_argv[1]
    source = root / 'claude'
    from agent_phase.runtime_models import source_defaults
    with source_defaults():
        resolved = resolve_profile(source, profile)
    arguments, tools = extract_read_only_tools(outer_argv[2:])
    overlay = read_only_contract(source, profile, headless=True, tools=tools)
    arguments = [arg for arg in arguments if arg != '--read-only']
    forwarded, _, _, _ = parse_wrapper_arguments(arguments)
    prompt, _ = source_guidance(source, arguments, workers=False, provider='claude')
    argv = [executable, '--model', resolved.resolved_model_id,
            '--effort', resolved.source_profile['effort'],
            '--permission-mode', overlay['permission_mode'], '--tools', ','.join(overlay['tools']),
            '--setting-sources', overlay['setting_sources'], '--mcp-config', '{"mcpServers":{}}',
            '--strict-mcp-config', '--disable-slash-commands', '--no-chrome']
    if prompt:
        argv.extend(['--append-system-prompt', prompt])
    return [*argv, *forwarded]


# Imported only when D1 readback calls this module; execution never starts a provider.
from .d1_qualification import (
    D1ReadbackError, INSTRUMENTED_AUTHORITY_SCHEMA, NATIVE_LAUNCH_FACTS_ARTIFACT, _sha256, _canonical_bytes,
    D1Error, build_d1_launch_environment, native_launch_custody, read_regular_nofollow,
    verify_d1_selected_executables,
)
import json
import shutil


def _expected_environment(edir, roots_data, is_instrumented, expected_argv, executable_selection=None, *, repo=None):
    from .d1_auth import AUTH_SCHEMA, validate_context
    auth = json.loads(read_regular_nofollow(edir / "auth-context.json"))
    if set(auth) != {"schema", "values"} or auth["schema"] != AUTH_SCHEMA:
        raise D1ReadbackError("invalid authentication context schema")
    blocked = () if is_instrumented else (repo, roots_data["custody_root"]["path"], edir)
    context = validate_context(auth["values"], forbidden_roots=blocked)
    home_dir = Path(context["HOME"])
    if is_instrumented and context != {"HOME": roots_data["isolated_home"]["path"]}:
        raise D1ReadbackError("instrumented authentication home mismatch")
    tmp_dir = Path(roots_data["isolated_tmp"]["path"] if "isolated_tmp" in roots_data else roots_data["tmp"]["path"])

    if is_instrumented:
        fake_exec = edir / "fake-bin" / "claude"
        cfg_path = edir / ".fake-claude-config.json"
        expected_env = build_d1_launch_environment(
            home_dir=home_dir,
            tmp_dir=tmp_dir,
            fake_executable=fake_exec,
            config_path=cfg_path,
            is_instrumented=True,
        )
    else:
        expected_env = build_d1_launch_environment(
            home_dir=home_dir,
            tmp_dir=tmp_dir,
            fake_executable=None,
            config_path=None,
            is_instrumented=False,
            executable_selection=executable_selection,
            auth_context=context,
        )
    # Reapply the maintained transport environment transform to retained plan inputs.
    from agent_phase.transmission import Transport
    plan_path = edir / "d1.context-plan.json"
    plan_bytes = plan_path.read_bytes()
    plan = json.loads(plan_bytes)
    prepared = {"path": plan_path, "record": plan, "evaluation_transport": True,
                "reference": {"schema": "apg.context-reference/v1", "path": plan_path.name,
                              "sha256": _sha256(plan_bytes), "bytes": len(plan_bytes)},
                "claude_read_stream": str(edir / "d1.context-plan.claude-stream.jsonl")}
    effective_env = Transport(prepared).environment(expected_argv, expected_env)
    return expected_env, effective_env


def _verify_executable(repo, edir, expected_env, is_instrumented, start_receipt, rec, expected_argv):
    repo_launcher = repo / "bin/claude-profile"
    repo_wrapper = repo / "libexec/claude_vc_profile.py"
    if not repo_launcher.is_file():
        raise D1ReadbackError("launcher bin/claude-profile missing")
    if not repo_wrapper.is_file():
        raise D1ReadbackError("wrapper libexec/claude_vc_profile.py missing")
    expected_launcher_sha = _sha256(repo_launcher.read_bytes())
    expected_wrapper_sha = _sha256(repo_wrapper.read_bytes())

    if is_instrumented:
        expected_phys_exec_path = edir / "fake-bin" / "claude"
        if not expected_phys_exec_path.is_file():
            raise D1ReadbackError("fake claude executable missing")
        expected_phys_exec = str(expected_phys_exec_path.resolve())
        expected_phys_sha = _sha256(expected_phys_exec_path.read_bytes())
    else:
        try:
            verify_d1_selected_executables(rec["executable_evidence"]["executable_selection"], expected_env)
        except (D1Error, KeyError, OSError) as error:
            raise D1ReadbackError("production executable selection mismatch") from error
        real_cli = shutil.which("claude", path=expected_env["PATH"])
        if not real_cli:
            raise D1ReadbackError("production claude executable missing from PATH")
        real_exec_path = Path(real_cli).resolve()
        if not real_exec_path.is_file():
            raise D1ReadbackError("resolved production claude executable is not a file")
        expected_phys_exec = str(real_exec_path)
        expected_phys_sha = _sha256(real_exec_path.read_bytes())

    if start_receipt.get("physical_executable") != expected_phys_exec:
        raise D1ReadbackError("physical executable mismatch in provider-start receipt")
    if start_receipt.get("physical_executable_sha256") != expected_phys_sha:
        raise D1ReadbackError("physical_executable_sha256 mismatch in provider-start receipt")

    # Check physical executable on disk currently has matching sha256
    phys_file = Path(expected_phys_exec)
    if not phys_file.is_file() or _sha256(phys_file.read_bytes()) != expected_phys_sha:
        raise D1ReadbackError("executable on disk digest mismatch with receipt physical_executable_sha256")

    ex_ev = rec.get("executable_evidence", {})
    if ex_ev.get("physical_executable") != expected_phys_exec:
        raise D1ReadbackError("record executable evidence physical_executable mismatch")
    if ex_ev.get("physical_executable_sha256") != expected_phys_sha:
        raise D1ReadbackError("record executable evidence physical_executable_sha256 mismatch")
    if ex_ev.get("launcher_sha256") != expected_launcher_sha:
        raise D1ReadbackError("record executable evidence launcher_sha256 mismatch")
    if ex_ev.get("wrapper_sha256") != expected_wrapper_sha:
        raise D1ReadbackError("record executable evidence wrapper_sha256 mismatch")

    if start_receipt.get("popen_executable") != str(Path(expected_argv[0]).resolve()):
        raise D1ReadbackError("Popen launcher executable mismatch")
    if start_receipt.get("popen_executable_sha256") != _sha256(Path(expected_argv[0]).read_bytes()):
        raise D1ReadbackError("Popen launcher digest mismatch")
    return expected_phys_exec, expected_phys_sha


def custodied_launch_facts(edir, rec):
    """Return native launch facts only after exact record-bound custody verifies."""
    try:
        data = read_regular_nofollow(edir / NATIVE_LAUNCH_FACTS_ARTIFACT)
    except OSError as error:
        raise D1ReadbackError(f"{NATIVE_LAUNCH_FACTS_ARTIFACT} missing, symlink or unreadable") from error
    custody = rec.get("post_provider", {}).get("native_launch_custody")
    if not isinstance(custody, dict):
        raise D1ReadbackError("native launch facts custody missing from record")
    if custody != native_launch_custody(data):
        raise D1ReadbackError("native launch facts digest mismatch with record custody")
    try:
        deliveries = json.loads(data)
    except ValueError as error:
        raise D1ReadbackError("native launch facts are not valid JSON") from error
    return deliveries.get("launch_facts") if isinstance(deliveries, dict) else None


def _verify_native(repo, edir, expected_argv, expected_phys_exec, expected_phys_sha, start_receipt, is_instrumented, rec):
    native = custodied_launch_facts(edir, rec)
    if not isinstance(native, dict):
        raise D1ReadbackError("native launch-owner observation missing")
    # Native environment evidence is diagnostic only: host launcher additions
    # are not source-derivable. Refuse any authoritative-looking native field;
    # environment custody is the verified outer start-receipt contract.
    from agent_phase.transmission import NATIVE_ENVIRONMENT_DIGEST_CLASSIFICATION
    if "environment_digest" in native:
        raise D1ReadbackError("native launch facts claim an unverifiable authoritative environment digest")
    if native.get("diagnostic_environment_digest_classification") != NATIVE_ENVIRONMENT_DIGEST_CLASSIFICATION:
        raise D1ReadbackError("native environment digest classification missing or not diagnostic")
    diagnostic = native.get("diagnostic_environment_digest")
    if not isinstance(diagnostic, str) or len(diagnostic) != 64 or diagnostic.strip("0123456789abcdef"):
        raise D1ReadbackError("native diagnostic environment digest malformed")
    if native.get("physical_executable") != expected_phys_exec or native.get("physical_executable_sha256") != expected_phys_sha:
        raise D1ReadbackError("native launch-owner executable mismatch")
    if native.get("parent_pid") != start_receipt.get("pid") or native.get("cwd") != str(edir):
        raise D1ReadbackError("native launch-owner parent/cwd mismatch")
    if native.get("argv") != expected_native_argv(repo, expected_argv, expected_phys_exec):
        raise D1ReadbackError("native argv differs from source-owned wrapper transformation")
    if is_instrumented:
        child = json.loads((edir / "child-startup-evidence.json").read_bytes())
        if child.get("pid") != native.get("pid") or child.get("argv") != native.get("argv"):
            raise D1ReadbackError("child full argv/PID differs from native launch-owner observation")


def verify_launch_facts(repo, edir, auth_data, roots_data, start_receipt, rec, expected_argv):
    is_instrumented = auth_data.get("schema") == INSTRUMENTED_AUTHORITY_SCHEMA
    try:
        expected_env, effective_env = _expected_environment(
            edir, roots_data, is_instrumented, expected_argv,
            rec.get("executable_evidence", {}).get("executable_selection"), repo=repo)
    except (D1Error, ValueError) as error:
        raise D1ReadbackError("invalid production executable selection or authentication context") from error
    if _sha256(read_regular_nofollow(edir / "auth-context.json")) != rec["pre_provider"].get("auth_context_sha256"):
        raise D1ReadbackError("authentication context digest mismatch")
    if start_receipt.get("environment_digest") != _sha256(_canonical_bytes(effective_env)):
        raise D1ReadbackError("environment_digest mismatch in provider-start receipt with source-derived digest")
    if start_receipt.get("allowlist_environment") != expected_env:
        raise D1ReadbackError("allowlist_environment mismatch in provider-start receipt with source-derived allowlist")
    physical, sha = _verify_executable(repo, edir, expected_env, is_instrumented, start_receipt, rec, expected_argv)
    _verify_native(repo, edir, expected_argv, physical, sha, start_receipt, is_instrumented, rec)
