"""Shared pull-request workflow step policy and native-qualification topology validation."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPECTED_REPO = "Knowledge-Forge-AI/agentic-praxis-grimoire"
EXPECTED_REPO_ID = "1306002537"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
NATIVE_DOWNLOAD_PIN = "d3f86a106a0bac45b974a628896c90dbdf5c8093"
# This pin's src/download-artifact.ts nests ID downloads under the artifact name,
# even for one ID, unless merge-multiple is true. A pin upgrade must requalify it.
RUNNER_TEMP_PREFIX = "${{ runner.temp }}/"

ACTION_PINS: dict[str, frozenset[str]] = {
    "actions/checkout": frozenset({"3d3c42e5aac5ba805825da76410c181273ba90b1"}),
    "actions/setup-python": frozenset({"5fda3b95a4ea91299a34e894583c3862153e4b97"}),
    "actions/setup-go": frozenset({"b7ad1dad31e06c5925ef5d2fc7ad053ef454303e"}),
    "actions/setup-node": frozenset({"249970729cb0ef3589644e2896645e5dc5ba9c38"}),
    "actions/setup-java": frozenset({"b6effb05e454b25005698d916606bdc6ffcbf961"}),
    "actions/upload-artifact": frozenset({"b7c566a772e6b6bfb58ed0dc250532a479d7789f"}),
    "actions/download-artifact": frozenset({
        "fa0a91b85d4f404e444e00e005971372dc801d16",
        NATIVE_DOWNLOAD_PIN,
    }),
    "cachix/install-nix-action": frozenset({"13d8dd58da0234aa297dedd986986ccb8e7f3e24"}),
    "github/codeql-action/init": frozenset({"b96794f015dfd88f77b49b1c93e0fa7110f94c63"}),
    "github/codeql-action/analyze": frozenset({"b96794f015dfd88f77b49b1c93e0fa7110f94c63"}),
}
TOP_LEVEL_KEYS = {"name", "permissions", "concurrency", "env", "defaults", "jobs", "on"}
JOB_KEYS = {"name", "if", "needs", "runs-on", "timeout-minutes", "permissions", "outputs",
            "strategy", "env", "steps"}
DOWNLOAD_WITH_KEYS = {"name", "pattern", "path", "merge-multiple", "artifact-ids"}
FORBIDDEN_RUN_TOKENS = ("|| true", "|| :", "set +e", "exit 0", "continue-on-error")
FORBIDDEN_DOC_TOKENS = ("secrets.", "pull_request_target", "workflow_dispatch", "workflow_run")
SCRIPT_REF = re.compile(r"(?<![\w./-])((?:release|tools|libexec|bin)/[\w./-]*\.py)\b")
OUTPUT_FLAG = re.compile(r"--(?:output|dir|bundle|lanes|scans|evidence|artifact)\s+(\S+)")
OUTPUT_VALUE = re.compile(r"^(?:sha256:)?\$\{\{ steps\.([A-Za-z0-9_-]+)\.outputs\.[A-Za-z0-9_-]+ \}\}$")
NEEDS_REF = re.compile(r"needs\.([A-Za-z0-9_-]+)\.(result|outputs\.([A-Za-z0-9_-]+))")

LANES = ("native-darwin-arm64", "native-linux-x64", "native-linux-arm64")
CONSUMERS = tuple(lane.replace("native-", "native-consumer-") for lane in LANES)
GATE = "native-release-candidate-gate"
MEMBER_JOBS = ("native-guard", *LANES, "native-assemble", *CONSUMERS, "native-release-scans")
REQUIRED_NATIVE_JOBS = {*MEMBER_JOBS, GATE}
EXPECTED_RUNNERS = {
    "native-guard": "ubuntu-24.04", "native-assemble": "ubuntu-24.04",
    "native-release-scans": "ubuntu-24.04", GATE: "ubuntu-24.04",
    LANES[0]: "macos-15", LANES[1]: "ubuntu-24.04", LANES[2]: "ubuntu-24.04-arm",
    CONSUMERS[0]: "macos-15", CONSUMERS[1]: "ubuntu-24.04", CONSUMERS[2]: "ubuntu-24.04-arm",
}
LANE_NEEDS = {"native-guard"}
ASSEMBLE_NEEDS = {"native-guard", *LANES}
POST_NEEDS = {"native-guard", "native-assemble"}
EXPECTED_NEEDS: dict[str, set[str]] = {
    "native-guard": set(),
    **{lane: LANE_NEEDS for lane in LANES},
    "native-assemble": ASSEMBLE_NEEDS,
    **{consumer: POST_NEEDS for consumer in CONSUMERS},
    "native-release-scans": POST_NEEDS,
    GATE: set(MEMBER_JOBS),
}
RECEIPT_OUTPUTS = {"receipt_id", "receipt_digest"}
LANE_OUTPUTS = {"seal_sha256", "artifact_id", "artifact_digest", *RECEIPT_OUTPUTS}
POST_OUTPUTS = RECEIPT_OUTPUTS
EXPECTED_OUTPUTS: dict[str, set[str]] = {
    "native-guard": {"source_commit", "source_tree", *RECEIPT_OUTPUTS},
    **{lane: LANE_OUTPUTS for lane in LANES},
    "native-assemble": {"bundle_seal_sha256", "artifact_id", "artifact_digest", *RECEIPT_OUTPUTS},
    **{consumer: POST_OUTPUTS for consumer in CONSUMERS},
    "native-release-scans": {"artifact_id", "artifact_digest", *RECEIPT_OUTPUTS},
    GATE: set(),
}
ACTIONS_READ_JOBS = {"native-assemble", *CONSUMERS, "native-release-scans", GATE}
GO_SETUP_JOBS = {*LANES, "native-release-scans"}
NIX_SETUP_JOBS = set(LANES)
GO_SHIM_JOBS = {"native-assemble", *CONSUMERS}


def condition_clauses(value: Any) -> list[str]:
    text = str(value or "").strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2]
    return sorted(part.strip().replace(f"'{EXPECTED_REPO_ID}'", EXPECTED_REPO_ID)
                  for part in text.split("&&"))


def guard_clauses(need: str | None, *, always: bool = False) -> list[str]:
    clauses = [f"github.repository == '{EXPECTED_REPO}'", f"github.repository_id == {EXPECTED_REPO_ID}"]
    if always:
        clauses.append("always()")
    elif need is not None:
        clauses += [f"needs.{need}.result == 'success'", "github.base_ref == 'main'",
                    "github.head_ref == 'staging'",
                    "github.event.pull_request.head.repo.full_name == github.repository"]
    return sorted(clauses)


def check_pull_request_workflow(doc: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    name = path.name
    for key in sorted(set(doc) - TOP_LEVEL_KEYS):
        errors.append(f"{name}: unsupported top-level key {key!r}")
    text = json.dumps(doc)
    for token in FORBIDDEN_DOC_TOKENS:
        if token in text:
            errors.append(f"{name}: forbidden token {token!r}")
    on = doc.get("on")
    if not isinstance(on, dict) or set(on) != {"pull_request"}:
        errors.append(f"{name}: only pull_request execution is permitted")
    if not isinstance(on, dict) or not isinstance(on.get("pull_request"), dict):
        errors.append(f"{name}: missing pull_request trigger")
    else:
        pr = on["pull_request"]
        if pr.get("branches") != ["main"]:
            errors.append(f"{name}: pull_request must target 'main' branch")
        if any(key in pr for key in ("paths", "paths-ignore", "branches-ignore")):
            errors.append(f"{name}: required lanes cannot use event filters")
        types = pr.get("types", [])
        expected = {"opened", "synchronize", "reopened", "ready_for_review"}
        if not isinstance(types, list) or not expected.issubset(types):
            errors.append(f"{name}: missing PR types: {sorted(expected - set(types if isinstance(types, list) else []))}")
    perms = doc.get("permissions", {})
    if perms != {"contents": "read"}:
        errors.append(f"{name}: top-level permissions must be exactly {{contents: read}}, got {perms}")
    concurrency = doc.get("concurrency")
    if not isinstance(concurrency, dict) or concurrency.get("cancel-in-progress") is not True:
        errors.append(f"{name}: concurrency must specify cancel-in-progress: true")
    return errors


def _with(step: dict[str, Any]) -> dict[str, Any]:
    return step["with"] if isinstance(step.get("with"), dict) else {}


def steps_using(steps: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [s for s in steps if str(s.get("uses", "")).split("@")[0] == kind]


def check_go_setups(errors: list[str], label: str, steps: list[dict[str, Any]], *,
                    required: bool, forbidden: bool, no_cache: bool) -> None:
    from libexec.apg_go_build import RELEASE_GO_VERSION

    go_version = RELEASE_GO_VERSION.removeprefix("go")
    setups = steps_using(steps, "actions/setup-go")
    if required and not setups:
        errors.append(f"{label}: missing required setup-go")
    if forbidden and setups:
        errors.append(f"{label}: setup-go forbidden")
    for step in setups:
        with_ = step.get("with") if isinstance(step.get("with"), dict) else {}
        if with_.get("go-version") != go_version:
            errors.append(f"{label}: setup-go must select {go_version}")
        if no_cache and with_.get("cache") is not False:
            errors.append(f"{label}: setup-go must set cache: false")


def _check_action(errors: list[str], label: str, uses: str, native: bool) -> None:
    parts = uses.split("@")
    if len(parts) != 2 or not SHA_PATTERN.match(parts[1].strip()):
        errors.append(f"{label}: action {uses} not pinned to 40-char SHA")
    elif parts[0] not in ACTION_PINS or parts[1] not in ACTION_PINS[parts[0]]:
        errors.append(f"{label}: action {uses} is not an approved action pin")
    elif native and parts[0] == "actions/download-artifact" and parts[1] != NATIVE_DOWNLOAD_PIN:
        errors.append(f"{label}: download-artifact must use pin {NATIVE_DOWNLOAD_PIN}")


def _check_run(errors: list[str], label: str, run: Any) -> None:
    if not isinstance(run, str):
        errors.append(f"{label}: run must be a string")
        return
    if "${{" in run:
        errors.append(f"{label}: run step contains expression; pass env instead")
    for token in FORBIDDEN_RUN_TOKENS:
        if token in run:
            errors.append(f"{label}: run step contains suppression token {token!r}")
    for ref in SCRIPT_REF.findall(run):
        if ref.startswith("release/ci/native_") or not (ROOT / ref).is_file():
            errors.append(f"{label}: run step calls nonexistent or wrong helper path {ref}")
    for value in OUTPUT_FLAG.findall(run):
        if not value.strip("\"'").startswith(("${RUNNER_TEMP}/", "$RUNNER_TEMP/")):
            errors.append(f"{label}: output path must be under RUNNER_TEMP, got {value}")


def check_step_policy(errors: list[str], path: Path, job: str, job_doc: dict[str, Any], *,
                      native: bool) -> list[dict[str, Any]]:
    label = f"{path.name}:{job}"
    for key in sorted(set(job_doc) - JOB_KEYS):
        errors.append(f"{label}: unsupported job key {key!r}")
    if re.search(r"\bfalse\b", str(job_doc.get("if", ""))):
        errors.append(f"{label}: job condition cannot skip the job")
    raw_steps = job_doc.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        errors.append(f"{label}: steps must be a non-empty list")
        return []
    steps: list[dict[str, Any]] = []
    for step in raw_steps:
        if not isinstance(step, dict):
            errors.append(f"{label}: step must be an object")
            continue
        steps.append(step)
        for key in ("continue-on-error", "working-directory"):
            if key in step:
                errors.append(f"{label}: step key {key} is forbidden")
        if re.search(r"\bfalse\b", str(step.get("if", ""))):
            errors.append(f"{label}: step condition cannot skip the step")
        uses = step.get("uses")
        with_ = step.get("with") if isinstance(step.get("with"), dict) else {}
        if uses is not None:
            kind = str(uses).split("@")[0]
            _check_action(errors, label, str(uses), native)
            if "checkout" in str(uses).lower() and with_.get("persist-credentials") is not False:
                errors.append(f"{label}: checkout step must set persist-credentials: false")
            if kind in {"actions/upload-artifact", "actions/download-artifact"} \
                    and not str(with_.get("path", "")).startswith(RUNNER_TEMP_PREFIX):
                errors.append(f"{label}: {kind} path must be under runner.temp")
            if kind == "actions/upload-artifact" and native:
                if with_.get("retention-days") != 14:
                    errors.append(f"{label}: upload-artifact must specify retention-days: 14, "
                                  f"got {with_.get('retention-days')!r}")
                if with_.get("if-no-files-found") != "error":
                    errors.append(f"{label}: upload-artifact must set if-no-files-found: error")
            if kind == "actions/download-artifact" and set(with_) - DOWNLOAD_WITH_KEYS:
                errors.append(f"{label}: download-artifact options not permitted: "
                              f"{sorted(set(with_) - DOWNLOAD_WITH_KEYS)}")
            if kind == "actions/download-artifact" and native \
                    and (with_.get("merge-multiple", False) is not False or "name" in with_):
                errors.append(f"{label}: download layout must preserve artifact-name directories")
        if "run" in step:
            _check_run(errors, label, step["run"])
    return steps


def _runs(steps: list[dict[str, Any]]) -> str:
    return "\n".join(str(s.get("run", "")) for s in steps)


def _check_members(errors: list[str], label: str, job: str, steps: list[dict[str, Any]]) -> None:
    from release.ci.matrix_receipts import NATIVE_PRESCRIBED_ARTIFACTS

    emits = [s for s in steps if "matrix_receipts.py emit" in str(s.get("run", ""))]
    if len(emits) != 1:
        errors.append(f"{label}: exactly one receipt emit step is required, got {len(emits)}")
    else:
        emit = emits[0]
        run = str(emit["run"])
        env = emit.get("env") if isinstance(emit.get("env"), dict) else {}
        for fragment in ("--workflow native-qualification", f"--job {job} ", '--status "$CI_JOB_STATUS"'):
            if fragment not in run + " ":
                errors.append(f"{label}: receipt emit must contain {fragment.strip()!r}")
        if env.get("CI_JOB_STATUS") != "${{ job.status }}":
            errors.append(f"{label}: receipt status must come from job.status")
        if "always()" not in str(emit.get("if", "")):
            errors.append(f"{label}: receipt emit must run with always()")
        for artifact in NATIVE_PRESCRIBED_ARTIFACTS.get(job, ()):
            if f"/{artifact}" not in run:
                errors.append(f"{label}: receipt emit must bind artifact {artifact}")
    uploads = [s for s in steps_using(steps, "actions/upload-artifact")
               if isinstance(s.get("with"), dict) and s["with"].get("name") == f"{job}-receipt"]
    if len(uploads) != 1:
        errors.append(f"{label}: exactly one {job}-receipt upload is required, got {len(uploads)}")
    elif "always()" not in str(uploads[0].get("if", "")) \
            or uploads[0]["with"].get("path") != RUNNER_TEMP_PREFIX + "receipts":
        errors.append(f"{label}: receipt upload must run with always() from runner.temp/receipts")


def _check_job(errors: list[str], path: Path, job: str, job_doc: dict[str, Any]) -> None:
    label = f"{path.name}:{job}"
    steps = check_step_policy(errors, path, job, job_doc, native=True)
    runs = _runs(steps)
    if job_doc.get("runs-on") != EXPECTED_RUNNERS[job]:
        errors.append(f"{label}: runs-on must be {EXPECTED_RUNNERS[job]!r}, got {job_doc.get('runs-on')!r}")
    needs = job_doc.get("needs", [])
    if not isinstance(needs, list) or sorted(needs) != sorted(EXPECTED_NEEDS[job]):
        errors.append(f"{label}: needs must be {sorted(EXPECTED_NEEDS[job])}, got {needs!r}")
        needs = []
    if job == "native-guard":
        expected_if = guard_clauses(None)
    elif job == GATE:
        expected_if = guard_clauses(None, always=True)
    else:
        expected_if = guard_clauses("native-guard")
    if condition_clauses(job_doc.get("if")) != expected_if:
        errors.append(f"{label}: missing job-level public guard; condition must be exactly {expected_if}")
    perms = job_doc.get("permissions")
    if isinstance(perms, dict) and "id-token" in perms:
        errors.append(f"{label}: id-token write forbidden on native qualification")
    expected_perms = {"contents": "read", "actions": "read"} if job in ACTIONS_READ_JOBS else None
    if expected_perms is not None and perms != expected_perms:
        errors.append(f"{label}: permissions must be {expected_perms}, got {perms}")
    if expected_perms is None and perms not in (None, {"contents": "read"}):
        errors.append(f"{label}: job cannot increase permissions")
    outputs = job_doc.get("outputs", {})
    step_ids = {s.get("id") for s in steps}
    if not isinstance(outputs, dict) or set(outputs) != EXPECTED_OUTPUTS[job]:
        errors.append(f"{label}: outputs must be {sorted(EXPECTED_OUTPUTS[job])}, "
                      f"got {sorted(outputs) if isinstance(outputs, dict) else outputs!r}")
    else:
        for key, value in outputs.items():
            match = OUTPUT_VALUE.match(str(value))
            if match is None or match.group(1) not in step_ids:
                errors.append(f"{label}: output {key} must reference an existing step output")
    for need, _target, output in NEEDS_REF.findall(json.dumps(job_doc)):
        if need not in needs:
            errors.append(f"{label}: references needs.{need} without depending on it")
        elif output and output not in EXPECTED_OUTPUTS.get(need, set()):
            errors.append(f"{label}: references undeclared output needs.{need}.outputs.{output}")
    check_go_setups(errors, label, steps, required=job in GO_SETUP_JOBS,
                    forbidden=job not in GO_SETUP_JOBS, no_cache=True)
    nix = steps_using(steps, "cachix/install-nix-action")
    if (job in NIX_SETUP_JOBS) != bool(nix):
        errors.append(f"{label}: install-nix-action {'missing' if job in NIX_SETUP_JOBS else 'forbidden'}")
    if job not in ACTIONS_READ_JOBS and steps_using(steps, "actions/download-artifact"):
        errors.append(f"{label}: download-artifact forbidden outside post-lane jobs")
    if job in GO_SHIM_JOBS:
        shim = all(token in runs for token in ("/go", "exit 1", "RUNNER_TEMP"))
        if not shim or ("export PATH=" not in runs and "GITHUB_PATH" not in runs):
            errors.append(f"{label}: failing Go shim on PATH is required")
    if job in {*CONSUMERS, "native-release-scans"}:
        _check_bundle_verification(errors, label, job_doc, steps)
    if job in MEMBER_JOBS:
        _check_members(errors, label, job, steps)
    if job != GATE and "tools/ci/native_" not in runs:
        errors.append(f"{label}: must call a tools/ci/native_* helper")
    if job == "native-guard":
        checkout = steps_using(steps, "actions/checkout")
        if not checkout or any(_with(s).get("fetch-depth") != 0 for s in checkout):
            errors.append(f"{label}: guard checkout must use fetch-depth: 0")
        if "tools/ci/native_lane.py guard" not in runs:
            errors.append(f"{label}: must call native_lane.py guard")
        text = json.dumps(job_doc)
        for token, what in ((EXPECTED_REPO, "repository"), (EXPECTED_REPO_ID, "repository ID")):
            if token not in text:
                errors.append(f"{label}: guard job must check {what}")
    if job in LANES and f"native_lane.py qualify --lane {job}" not in runs:
        errors.append(f"{label}: must call native_lane.py qualify --lane {job}")
    if job == "native-assemble" and "native_release_assembly.py assemble" not in runs:
        errors.append(f"{label}: must call native_release_assembly.py assemble")
    if job == GATE:
        _check_gate(errors, label, job_doc, steps, runs)


def _check_bundle_verification(errors: list[str], label: str, job_doc: dict[str, Any],
                               steps: list[dict[str, Any]]) -> None:
    credentials = {"GITHUB_TOKEN", "GH_TOKEN"}
    if credentials & set(job_doc.get("env", {})):
        errors.append(f"{label}: GitHub token must be scoped to bundle verification")
    verifies = [s for s in steps if "native_release_assembly.py verify-bundle " in str(s.get("run", ""))]
    if len(verifies) != 1 or "if" in verifies[0] or verifies[0].get("env", {}).get("GITHUB_TOKEN") != "${{ github.token }}" \
            or not verifies[0].get("env", {}).get("NATIVE_BUNDLE_JSON"):
        errors.append(f"{label}: exactly one token-bearing expected bundle verification step is required")
    for step in steps:
        if credentials & set(step.get("env", {})) and step not in verifies:
            errors.append(f"{label}: GitHub token forbidden outside bundle verification")
    if len(verifies) == 1:
        verify_index = steps.index(verifies[0])
        execution = [i for i, s in enumerate(steps) if any(token in str(s.get("run", "")) for token in
                     ("native_lane.py consumer ", "native_release_assembly.py export-scan-input ", "native_release_assembly.py check-scan "))]
        downloads = [i for i, s in enumerate(steps) if str(s.get("uses", "")).startswith("actions/download-artifact@")]
        if not execution or not downloads or max(downloads) >= verify_index or min(execution) <= verify_index:
            errors.append(f"{label}: bundle verification must follow download and precede packaged execution")


def _check_gate(errors: list[str], label: str, job_doc: dict[str, Any],
                steps: list[dict[str, Any]], runs: str) -> None:
    env = job_doc.get("env") if isinstance(job_doc.get("env"), dict) else {}
    matrix = str(env.get("MATRIX_NEEDS_RESULTS", ""))
    for member in MEMBER_JOBS:
        if f'"{member}":"${{{{ needs.{member}.result }}}}"' not in matrix:
            errors.append(f"{label}: MATRIX_NEEDS_RESULTS must carry needs.{member}.result")
    for fragment in ("release/ci/matrix_receipts.py verify", "--workflow native-qualification",
                     '--statuses-json "$MATRIX_NEEDS_RESULTS"', "tools/ci/native_gate.py"):
        if fragment not in runs:
            errors.append(f"{label}: gate must run {fragment!r}")
    uploads = [s for s in steps_using(steps, "actions/upload-artifact")
               if isinstance(s.get("with"), dict) and s["with"].get("name") == "native-release-candidate-gate-result"]
    if len(uploads) != 1 or "always()" not in str(uploads[0].get("if", "")):
        errors.append(f"{label}: exactly one always() native-release-candidate-gate-result upload is required")


def validate_native_qualification(doc: dict[str, Any], path: Path) -> list[str]:
    errors = check_pull_request_workflow(doc, path)
    if {"GITHUB_TOKEN", "GH_TOKEN"} & set(doc.get("env", {})):
        errors.append(f"{path.name}: workflow-level GitHub token forbidden")
    jobs = doc.get("jobs")
    if not isinstance(jobs, dict):
        return [*errors, f"{path.name}: missing jobs section"]
    if REQUIRED_NATIVE_JOBS - set(jobs):
        errors.append(f"{path.name}: missing required jobs: {sorted(REQUIRED_NATIVE_JOBS - set(jobs))}")
    if set(jobs) - REQUIRED_NATIVE_JOBS:
        errors.append(f"{path.name}: unexpected jobs in native qualification: "
                      f"{sorted(set(jobs) - REQUIRED_NATIVE_JOBS)}")
    for job in sorted(REQUIRED_NATIVE_JOBS & set(jobs)):
        if isinstance(jobs[job], dict):
            _check_job(errors, path, job, jobs[job])
        else:
            errors.append(f"{path.name}:{job}: job must be an object")
    return errors
