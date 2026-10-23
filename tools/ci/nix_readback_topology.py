"""Validate the attended, read-only Nix post-tag readback workflow."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from tools.ci.native_topology import ACTION_PINS, SHA_PATTERN

TOP_LEVEL_KEYS = {"name", "on", "permissions", "defaults", "concurrency", "jobs"}
JOB_KEYS = {"name", "strategy", "runs-on", "timeout-minutes", "env", "steps"}
EXPECTED_WORKFLOW_NAME = "APGR Nix post-tag readback"
EXPECTED_JOB_ID = "nix-readback"
EXPECTED_TAG = "v0.13.1"
EXPECTED_REV = "3223b8803d46edb54d2ea18dc4dea3910b6e3ad3"
EXPECTED_SYSTEMS = [
    {"lane": "darwin-arm64", "runner": "macos-15", "system": "aarch64-darwin"},
    {"lane": "linux-x64", "runner": "ubuntu-24.04", "system": "x86_64-linux"},
    {"lane": "linux-arm64", "runner": "ubuntu-24.04-arm", "system": "aarch64-linux"},
]
HELPER_PATHS = [
    "bin/apg-qualify-nix",
    "libexec/apg_nix_qualification.py",
    "libexec/apg_nix_smoke.py",
]
EXPECTED_STEP_NAMES = [
    "Check out workflow source",
    "Select Python for the release helper",
    "Install the pinned Nix toolchain",
    "Bind tag, revision, and readback helper",
    "Run the tag-pinned Nix readback",
    "Finalize bound receipt",
    "Retain readback receipt",
    "Require successful bound readback",
]
EXPECTED_RUN_SHA256 = {
    "bind": "104a10f0272ea5982e3fe1cb76558cedf9e0a4357445141d92a9fb3aec7ae16a",
    "readback": "353c200e92c98e8ff6748cade70981b1a41aba4b6794b50563067327fd17fc69",
    "finalize": "4f84928f743d6ff800d744d49ea07fbafdf40880d4192bafcd06dc09580cbcfc",
    "require": "db511209efa0b8a4eb1e4910e246a23902e74fe850e253018b4b42945d6259c8",
}
EXPECTED_UPLOAD_PATH = (
    "${{ runner.temp }}/apgr-nix-readback/receipt.json\n"
    "${{ runner.temp }}/apgr-nix-readback/readback.json\n"
    "${{ runner.temp }}/apgr-nix-readback/identity.json\n"
    "${{ runner.temp }}/apgr-nix-readback/helper-manifest.json\n"
    "${{ runner.temp }}/apgr-nix-readback/exit-status"
)
FORBIDDEN_AUTHORITY_MARKERS = (
    "id-token",
    "secrets.",
    "npm publish",
    "pnpm publish",
    "yarn publish",
    "twine",
    "pypi_",
    "registry-url",
    "gh release",
    "action-gh-release",
    "docker push",
    "cargo publish",
    "gem push",
)
def _label(path: Path) -> str:
    return path.name


def _check_action(errors: list[str], path: Path, step: str, uses: Any, action: str) -> None:
    label = f"{_label(path)}:{step}"
    if not isinstance(uses, str):
        errors.append(f"{label}: action must be pinned")
        return
    actual_action, separator, pin = uses.partition("@")
    if not separator or not SHA_PATTERN.fullmatch(pin):
        errors.append(f"{label}: action {uses!r} is not pinned to a 40-character SHA")
    elif actual_action != action or pin not in ACTION_PINS.get(action, frozenset()):
        errors.append(f"{label}: action {uses!r} is not an approved existing pin")


def _exact_keys(errors: list[str], path: Path, label: str, value: Any, expected: set[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{_label(path)}:{label}: expected mapping")
        return
    missing = sorted(expected - set(value))
    extra = sorted(set(value) - expected)
    if missing or extra:
        errors.append(f"{_label(path)}:{label}: keys must be exact (missing={missing}, extra={extra})")


def _require_fragments(errors: list[str], path: Path, label: str, text: Any, fragments: tuple[str, ...]) -> None:
    if not isinstance(text, str):
        errors.append(f"{_label(path)}:{label}: run must be a string")
        return
    for fragment in fragments:
        if fragment not in text:
            errors.append(f"{_label(path)}:{label}: missing required contract {fragment!r}")


def _check_run_hash(errors: list[str], path: Path, label: str, text: Any) -> None:
    if not isinstance(text, str):
        return
    expected = EXPECTED_RUN_SHA256[label]
    actual = hashlib.sha256(text.encode()).hexdigest()
    if actual != expected:
        errors.append(f"{_label(path)}:{label}: run body is not the pinned reviewed block")


def _check_bind_step(errors: list[str], path: Path, step: dict[str, Any]) -> None:
    label = "bind"
    _exact_keys(errors, path, label, step, {"name", "id", "env", "run"})
    if step.get("id") != "bind":
        errors.append(f"{_label(path)}:{label}: id must be bind")
    if step.get("env") != {"APGR_READBACK_DIR": "${{ runner.temp }}/apgr-nix-readback"}:
        errors.append(f"{_label(path)}:{label}: environment must use runner.temp readback directory")
    run = step.get("run", "")
    _check_run_hash(errors, path, label, run)
    _require_fragments(errors, path, label, run, (
        "set -euo pipefail",
        'mkdir -m 700 -p "$APGR_READBACK_DIR/scratch"',
        "python3 - \"$APGR_READBACK_DIR\" <<'PY'",
        "tag_pattern = re.compile",
        "rev_pattern = re.compile",
        "if not tag_pattern.fullmatch(tag):",
        "if not rev_pattern.fullmatch(expected):",
        '["git", "fetch", "--no-tags", "origin",',
        'f"+refs/tags/{tag}:refs/tags/{tag}"',
        'subprocess.run(["git", "checkout", "--detach", "--force", actual], check=True)',
        "helper_paths = (",
        '"bin/apg-qualify-nix"',
        '"libexec/apg_nix_qualification.py"',
        '"libexec/apg_nix_smoke.py"',
        '"helper_manifest_sha256": manifest["manifest_sha256"]',
        '"helper_files": list(helper_paths)',
        '"identity.json"',
        '"helper-manifest.json"',
    ))
    if isinstance(run, str):
        validation_positions = [
            run.find("if not tag_pattern.fullmatch(tag):"),
            run.find("if not rev_pattern.fullmatch(expected):"),
        ]
        git = run.find("subprocess.run(")
        if min(validation_positions, default=-1) < 0 or git < 0 or max(validation_positions) > git:
            errors.append(f"{_label(path)}:{label}: input validation must precede Git execution")
        if "${{" in run or re.search(r"(?:^|[\s;])eval(?:[\s(]|$)", run) or "git push" in run or "git commit" in run:
            errors.append(f"{_label(path)}:{label}: input must remain data-only and read-only")
        if tuple(fragment for fragment in HELPER_PATHS if fragment in run) != tuple(HELPER_PATHS):
            errors.append(f"{_label(path)}:{label}: helper paths must be the approved three-file set")


def _check_readback_step(errors: list[str], path: Path, step: dict[str, Any]) -> None:
    label = "readback"
    _exact_keys(errors, path, label, step, {"name", "id", "continue-on-error", "env", "run"})
    if step.get("id") != "readback" or step.get("continue-on-error") is not True:
        errors.append(f"{_label(path)}:{label}: only the helper step may continue to record its exit status")
    if step.get("env") != {"APGR_READBACK_DIR": "${{ runner.temp }}/apgr-nix-readback"}:
        errors.append(f"{_label(path)}:{label}: environment must use runner.temp readback directory")
    _check_run_hash(errors, path, label, step.get("run", ""))
    _require_fragments(errors, path, label, step.get("run", ""), (
        "set +e",
        "bin/apg-qualify-nix readback \\",
        '--tag "$APGR_TAG"',
        '--scratch "$APGR_READBACK_DIR/scratch"',
        '--system "$APGR_SYSTEM"',
        '--expect-rev "$APGR_EXPECTED_REV"',
        'printf \'%s\\n\' "$status" > "$APGR_READBACK_DIR/exit-status"',
        'exit "$status"',
    ))


def _check_finalize_step(errors: list[str], path: Path, step: dict[str, Any]) -> None:
    label = "finalize"
    _exact_keys(errors, path, label, step, {"name", "if", "env", "run"})
    if step.get("if") != "${{ always() }}":
        errors.append(f"{_label(path)}:{label}: finalization must always run")
    if step.get("env") != {"APGR_READBACK_DIR": "${{ runner.temp }}/apgr-nix-readback"}:
        errors.append(f"{_label(path)}:{label}: environment must use runner.temp readback directory")
    _check_run_hash(errors, path, label, step.get("run", ""))
    _require_fragments(errors, path, label, step.get("run", ""), (
        "set -euo pipefail",
        'identity = json.loads((root / "identity.json").read_text())',
        'manifest = json.loads((root / "helper-manifest.json").read_text())',
        '"schema": "apgr.nix-post-tag-readback-receipt/v1"',
        '"helper_manifest": manifest',
        'except (OSError, ValueError):',
        '"result_sha256"',
    ))


def _check_upload_step(errors: list[str], path: Path, step: dict[str, Any]) -> None:
    label = "upload"
    _exact_keys(errors, path, label, step, {"name", "if", "uses", "with"})
    if step.get("if") != "${{ always() }}":
        errors.append(f"{_label(path)}:{label}: receipt upload must always run")
    _check_action(errors, path, label, step.get("uses"), "actions/upload-artifact")
    if step.get("with") != {
        "name": "apgr-nix-readback-${{ matrix.lane }}",
        "path": EXPECTED_UPLOAD_PATH,
        "retention-days": 14,
        "if-no-files-found": "error",
    }:
        errors.append(f"{_label(path)}:{label}: receipt upload contract changed")


def _check_require_step(errors: list[str], path: Path, step: dict[str, Any]) -> None:
    label = "require"
    _exact_keys(errors, path, label, step, {"name", "if", "env", "run"})
    if step.get("if") != "${{ always() }}":
        errors.append(f"{_label(path)}:{label}: final gate must always run")
    if step.get("env") != {"APGR_READBACK_DIR": "${{ runner.temp }}/apgr-nix-readback"}:
        errors.append(f"{_label(path)}:{label}: environment must use runner.temp readback directory")
    _check_run_hash(errors, path, label, step.get("run", ""))
    _require_fragments(errors, path, label, step.get("run", ""), (
        "set -euo pipefail",
        'test "$(cat "$APGR_READBACK_DIR/exit-status")" = 0',
        'identity["tag"]',
        'identity["expected_rev"]',
        'identity["actual_rev"] != identity["expected_rev"]',
        'identity["system"]',
        'manifest.get("manifest_sha256") != identity.get("helper_manifest_sha256")',
        'receipt.get("status") != "passed"',
        'binding.get("tag")',
        'binding.get("locked_rev")',
        'binding.get("system")',
    ))


def validate_nix_readback(doc: dict[str, Any], path: Path) -> list[str]:
    """Return topology and authority violations for the Nix readback workflow."""

    errors: list[str] = []
    name = _label(path)
    _exact_keys(errors, path, "workflow", doc, TOP_LEVEL_KEYS)
    if doc.get("name") != EXPECTED_WORKFLOW_NAME:
        errors.append(f"{name}: workflow name must be {EXPECTED_WORKFLOW_NAME!r}")

    trigger = doc.get("on")
    expected_inputs = {
        "tag": {
            "description": "Exact release tag to read back",
            "required": True,
            "default": EXPECTED_TAG,
            "type": "string",
        },
        "expected_rev": {
            "description": "Exact 40-character release commit expected behind the tag",
            "required": True,
            "default": EXPECTED_REV,
            "type": "string",
        },
    }
    if not isinstance(trigger, dict) or set(trigger) != {"workflow_dispatch"}:
        errors.append(f"{name}: only workflow_dispatch execution is permitted")
    elif trigger.get("workflow_dispatch", {}).get("inputs") != expected_inputs:
        errors.append(f"{name}: dispatch inputs must be exact tag and expected_rev strings")

    if doc.get("permissions") != {"contents": "read"}:
        errors.append(f"{name}: permissions must be exactly contents: read")
    if doc.get("defaults") != {"run": {"shell": "bash"}}:
        errors.append(f"{name}: defaults must select bash")
    if doc.get("concurrency") != {
        "group": "apgr-nix-post-tag-${{ github.repository }}-${{ github.ref }}",
        "cancel-in-progress": False,
    }:
        errors.append(f"{name}: concurrency contract changed")

    jobs = doc.get("jobs")
    if not isinstance(jobs, dict) or set(jobs) != {EXPECTED_JOB_ID}:
        errors.append(f"{name}: job inventory must contain only {EXPECTED_JOB_ID!r}")
        return errors
    job = jobs[EXPECTED_JOB_ID]
    _exact_keys(errors, path, EXPECTED_JOB_ID, job, JOB_KEYS)
    if job.get("name") != "Nix readback (${{ matrix.system }})":
        errors.append(f"{name}:{EXPECTED_JOB_ID}: job name changed")
    if job.get("runs-on") != "${{ matrix.runner }}" or job.get("timeout-minutes") != 120:
        errors.append(f"{name}:{EXPECTED_JOB_ID}: runner or timeout changed")
    if job.get("env") != {
        "APGR_TAG": "${{ inputs.tag }}",
        "APGR_EXPECTED_REV": "${{ inputs.expected_rev }}",
        "APGR_SYSTEM": "${{ matrix.system }}",
        "APGR_LANE": "${{ matrix.lane }}",
    }:
        errors.append(f"{name}:{EXPECTED_JOB_ID}: environment binding changed")
    if job.get("strategy") != {"fail-fast": False, "matrix": {"include": EXPECTED_SYSTEMS}}:
        errors.append(f"{name}:{EXPECTED_JOB_ID}: native matrix must be the three approved systems")

    steps = job.get("steps")
    if not isinstance(steps, list) or [step.get("name") for step in steps if isinstance(step, dict)] != EXPECTED_STEP_NAMES:
        errors.append(f"{name}:{EXPECTED_JOB_ID}: steps must remain the exact bound sequence")
        return errors
    if not all(isinstance(step, dict) for step in steps):
        errors.append(f"{name}:{EXPECTED_JOB_ID}: every step must be a mapping")
        return errors

    checkout, python, nix, bind, readback, finalize, upload, require = steps
    _exact_keys(errors, path, "checkout", checkout, {"name", "uses", "with"})
    _check_action(errors, path, "checkout", checkout.get("uses"), "actions/checkout")
    if checkout.get("with") != {"persist-credentials": False, "fetch-depth": 0}:
        errors.append(f"{name}:checkout: credentials and fetch depth must be exact")
    _exact_keys(errors, path, "python", python, {"name", "uses", "with"})
    _check_action(errors, path, "python", python.get("uses"), "actions/setup-python")
    if python.get("with") != {"python-version": "3.13"}:
        errors.append(f"{name}:python: Python version must remain 3.13")
    _exact_keys(errors, path, "nix", nix, {"name", "uses", "with"})
    _check_action(errors, path, "nix", nix.get("uses"), "cachix/install-nix-action")
    if nix.get("with") != {
        "install_url": "https://releases.nixos.org/nix/nix-2.35.2/install",
        "extra_nix_config": "experimental-features = nix-command flakes",
        "enable_kvm": False,
    }:
        errors.append(f"{name}:nix: pinned installer contract changed")
    _check_bind_step(errors, path, bind)
    _check_readback_step(errors, path, readback)
    _check_finalize_step(errors, path, finalize)
    _check_upload_step(errors, path, upload)
    _check_require_step(errors, path, require)

    raw = json.dumps(doc, sort_keys=True).lower()
    for marker in FORBIDDEN_AUTHORITY_MARKERS:
        if marker in raw:
            errors.append(f"{name}: forbidden publication or OIDC authority marker {marker!r}")
    if "workflow_dispatch" not in raw:
        errors.append(f"{name}: dispatch trigger missing")
    return errors
