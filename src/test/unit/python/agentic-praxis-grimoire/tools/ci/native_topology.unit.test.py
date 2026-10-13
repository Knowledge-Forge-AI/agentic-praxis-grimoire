"""Unit tests for native-qualification workflow topology validation (source-only fixtures)."""

from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from libexec.apg_go_build import RELEASE_GO_VERSION
from release.ci.matrix_receipts import NATIVE_MEMBER_JOBS, NATIVE_PRESCRIBED_ARTIFACTS
from tools.ci.native_topology import (
    ACTION_PINS,
    ACTIONS_READ_JOBS,
    CONSUMERS,
    EXPECTED_NEEDS,
    EXPECTED_OUTPUTS,
    EXPECTED_RUNNERS,
    GATE,
    GO_SETUP_JOBS,
    GO_SHIM_JOBS,
    LANES,
    MEMBER_JOBS,
    NATIVE_DOWNLOAD_PIN,
    NIX_SETUP_JOBS,
    REQUIRED_NATIVE_JOBS,
    validate_native_qualification,
)

PATH = Path("native-qualification.yml")
REPO = "Knowledge-Forge-AI/agentic-praxis-grimoire"
BASE_IF = f"github.repository == '{REPO}' && github.repository_id == 1306002537"
TEMP = "${RUNNER_TEMP}"
Doc = dict[str, Any]
Mutation = Callable[[Doc], None]


def _use(action: str, /, **with_: Any) -> Doc:
    return {"uses": f"{action}@{next(iter(ACTION_PINS[action]))}", "with": with_}


def _upload(step_id: str, name: str, path: str) -> Doc:
    return {"id": step_id, "if": "${{ always() }}", **_use(
        "actions/upload-artifact", name=name, path="${{ runner.temp }}/" + path,
        **{"retention-days": 14, "if-no-files-found": "error"})}


def _main_steps(job: str) -> list[Doc]:
    out = f'--output "{TEMP}/out"'
    if job == "native-guard":
        return [{"id": "guard", "env": {"EXPECTED_REPO": REPO, "EXPECTED_REPO_ID": "1306002537",
                                        "HEAD_REF": "${{ github.head_ref }}"},
                 "run": f'[[ "$HEAD_REF" == "staging" ]] || exit 1\npython3 tools/ci/native_lane.py guard {out}\n'}]
    if job in LANES:
        return [{"id": "qualify", "run": f"python3 tools/ci/native_lane.py qualify --lane {job} {out}\n"},
                _upload("upload_lane", job, "out")]
    if job == "native-assemble":
        inputs = ",".join(f"needs.{lane}.outputs.seal_sha256" for lane in LANES)
        return [{"id": "assemble", "env": {"INPUTS": "${{ " + inputs.split(",")[0] + " }}",
                                           "COMMIT": "${{ needs.native-guard.outputs.source_commit }}"},
                 "run": f'python3 tools/ci/native_release_assembly.py assemble --lanes "{TEMP}/lanes" {out}\n'},
                {"id": "upload_bundle", **_use("actions/upload-artifact", name="bundle",
                                                 path="${{ runner.temp }}/out", **{"retention-days": 14,
                                                                                    "if-no-files-found": "error"})}]
    if job in CONSUMERS:
        env = {"BUNDLE": "${{ needs.native-assemble.outputs.artifact_id }}"}
        return [{"id": "consumer", "env": env, "run": f"python3 tools/ci/native_lane.py consumer --lane {job} "
                                                      f'--bundle "{TEMP}/bundle" {out}\n'}]
    if job == "native-release-scans":
        return [{"id": "check_scan", "run": "python3 tools/ci/native_release_assembly.py check-scan "
                                            f'--bundle "{TEMP}/bundle" --scans "{TEMP}/scans" {out}\n'}]
    return [{"id": "gate",
             "run": "python3 release/ci/matrix_receipts.py verify --workflow native-qualification "
                    f'--dir "{TEMP}/all-receipts" --sha "$COMMIT_SHA" --statuses-json "$MATRIX_NEEDS_RESULTS"'
                    f' > "{TEMP}/gate/matrix-aggregate.json"\n'
                    f'python3 tools/ci/native_gate.py --evidence "{TEMP}/gate" {out}\n'},
            _upload("upload_gate", "native-release-candidate-gate-result", "out")]


def _member_steps(job: str) -> list[Doc]:
    flags = "".join(f' --artifact "{TEMP}/out/{name}"' for name in NATIVE_PRESCRIBED_ARTIFACTS[job])
    return [{"id": "emit", "if": "${{ always() }}", "env": {"CI_JOB_STATUS": "${{ job.status }}"},
             "run": "python3 release/ci/matrix_receipts.py emit --workflow native-qualification "
                    f'--job {job} --status "$CI_JOB_STATUS" --dir "{TEMP}/receipts" --sha "$COMMIT_SHA"{flags}\n'},
            _upload("upload_receipt", f"{job}-receipt", "receipts")]


def _job(job: str) -> Doc:
    steps: list[Doc] = [_use("actions/checkout", **{"persist-credentials": False, "fetch-depth": 0})]
    if job in GO_SETUP_JOBS:
        steps.append(_use("actions/setup-go", **{"go-version": RELEASE_GO_VERSION.removeprefix("go"), "cache": False}))
    if job in NIX_SETUP_JOBS:
        steps.append(_use("cachix/install-nix-action", enable_kvm=False))
    if job in GO_SHIM_JOBS:
        steps.append({"run": f'printf \'#!/bin/sh\\nexit 1\\n\' > "{TEMP}/bin/go"\nexport PATH="{TEMP}/bin:$PATH"\n'})
    if job in {*CONSUMERS, "native-release-scans"}:
        steps.append({**_use("actions/download-artifact", **{"artifact-ids": "${{ needs.native-assemble.outputs.artifact_id }}",
                                                          "path": "${{ runner.temp }}/bundle-download", "merge-multiple": False}),
                      "uses": f"actions/download-artifact@{NATIVE_DOWNLOAD_PIN}"})
        steps.append({"id": "verify_bundle", "env": {"GITHUB_TOKEN": "${{ github.token }}", "NATIVE_BUNDLE_JSON": "fixture-binding"},
                      "run": f'python3 tools/ci/native_release_assembly.py verify-bundle --bundle "{TEMP}/bundle" --scratch "{TEMP}"\n'})
    steps += _main_steps(job)
    if job in MEMBER_JOBS:
        steps += _member_steps(job)
    if job == GATE:
        steps.insert(1, _use("actions/download-artifact", pattern="native-*-receipt",
                             path="${{ runner.temp }}/all-receipts"))
        steps[1]["uses"] = f"actions/download-artifact@{NATIVE_DOWNLOAD_PIN}"
    condition = "always() && " + BASE_IF if job == GATE else BASE_IF.replace("1306002537", "'1306002537'")
    if job not in ("native-guard", GATE):
        condition = ("needs.native-guard.result == 'success' && " + BASE_IF + " && github.base_ref == 'main'"
                     " && github.head_ref == 'staging'"
                     " && github.event.pull_request.head.repo.full_name == github.repository")
    doc: Doc = {"name": job, "if": "${{ " + condition + " }}", "runs-on": EXPECTED_RUNNERS[job],
                "timeout-minutes": 30, "steps": steps}
    if EXPECTED_NEEDS[job]:
        doc["needs"] = sorted(EXPECTED_NEEDS[job])
    if job == GATE:
        results = ",".join(f'"{m}":"${{{{ needs.{m}.result }}}}"' for m in MEMBER_JOBS)
        doc["env"] = {"MATRIX_NEEDS_RESULTS": "{" + results + "}",
                      "SOURCE_COMMIT": "${{ needs.native-guard.outputs.source_commit }}"}
    if job in ACTIONS_READ_JOBS:
        doc["permissions"] = {"contents": "read", "actions": "read"}
    if EXPECTED_OUTPUTS[job]:
        by_step = {"source_commit": "guard", "source_tree": "guard", "seal_sha256": "qualify",
                   "receipt_id": "upload_receipt", "receipt_digest": "upload_receipt",
                   "bundle_seal_sha256": "assemble", "artifact_id": "upload_lane", "artifact_digest": "upload_lane"}
        post = {"native-assemble": "upload_bundle", **{j: "upload_receipt" for j in (*CONSUMERS, "native-release-scans")}}
        doc["outputs"] = {
            key: "${{ steps." + (post.get(job) if key.startswith("artifact_") and job in post else by_step[key])
            + ".outputs." + key.replace("_id", "-id").replace("_digest", "-digest") + " }}"
            for key in EXPECTED_OUTPUTS[job]
        }
    return doc


def _native_doc() -> Doc:
    return {
        "name": "native-qualification",
        "permissions": {"contents": "read"},
        "concurrency": {"group": "native", "cancel-in-progress": True},
        "env": {"COMMIT_SHA": "${{ github.sha }}", "PR_HEAD_SHA": "${{ github.event.pull_request.head.sha }}"},
        "defaults": {"run": {"shell": "bash"}},
        "on": {"pull_request": {"branches": ["main"],
                                "types": ["opened", "synchronize", "reopened", "ready_for_review"]}},
        "jobs": {job: _job(job) for job in sorted(REQUIRED_NATIVE_JOBS)},
    }


def test_diagnostics_output_must_stay_under_runner_temp() -> None:
    doc = _native_doc()
    qualify = next(step for step in doc["jobs"][LANES[0]]["steps"] if step.get("id") == "qualify")
    qualify["run"] += 'python3 tools/ci/native_lane.py qualify --diagnostics "/tmp/escape"\n'
    errors = validate_native_qualification(doc, PATH)
    assert any("output path must be under RUNNER_TEMP" in error for error in errors), errors


def _step(doc: Doc, job: str, needle: str) -> Doc:
    return next(s for s in doc["jobs"][job]["steps"]
                if needle in s.get("run", "") or str(s.get("uses", "")).startswith(needle) or s.get("id") == needle)


def _edit_run(job: str, needle: str, old: str, new: str) -> Mutation:
    def mutate(doc: Doc) -> None:
        step = _step(doc, job, needle)
        assert old in step["run"], (old, step["run"])
        step["run"] = step["run"].replace(old, new)
    return mutate


def _set_step(job: str, needle: str, **values: Any) -> Mutation:
    return lambda doc: _step(doc, job, needle).update(values)


def _set_with(job: str, needle: str, **values: Any) -> Mutation:
    return lambda doc: _step(doc, job, needle)["with"].update(values)


def _set_job(job: str, **values: Any) -> Mutation:
    return lambda doc: doc["jobs"][job].update(values)


def _drop_step(job: str, needle: str) -> Mutation:
    return lambda doc: doc["jobs"][job]["steps"].remove(_step(doc, job, needle))


def _add_step(job: str, step: Doc) -> Mutation:
    return lambda doc: doc["jobs"][job]["steps"].append(copy.deepcopy(step))


def _dup_step(job: str, needle: str) -> Mutation:
    return lambda doc: doc["jobs"][job]["steps"].append(copy.deepcopy(_step(doc, job, needle)))


def _env(job: str, needle: str, key: str, value: str) -> Mutation:
    return lambda doc: _step(doc, job, needle).setdefault("env", {}).update({key: value})


def _del(path: tuple[str, ...]) -> Mutation:
    def mutate(doc: Doc) -> None:
        node: Any = doc
        for key in path[:-1]:
            node = node[key]
        del node[path[-1]]
    return mutate


def _pop_output(job: str) -> Mutation:
    return lambda doc: doc["jobs"][job]["outputs"].pop(next(iter(doc["jobs"][job]["outputs"])))


LANE, CONSUMER, ARM = LANES[0], CONSUMERS[0], "native-linux-arm64"
CASES: dict[str, tuple[Mutation, str]] = {
    "extra-job": (lambda d: d["jobs"].update({"extra": {"runs-on": "ubuntu-24.04"}}), "unexpected jobs"),
    "missing-job": (_del(("jobs", "native-release-scans")), "missing required jobs"),
    "arm-runner": (_set_job(ARM, **{"runs-on": "ubuntu-latest"}), "runs-on must be 'ubuntu-24.04-arm'"),
    "consumer-runner": (_set_job(CONSUMER, **{"runs-on": "macos-14"}), "runs-on must be 'macos-15'"),
    "assemble-needs": (lambda d: d["jobs"]["native-assemble"]["needs"].pop(), "needs must be"),
    "gate-needs": (lambda d: d["jobs"][GATE]["needs"].pop(), "needs must be"),
    "gate-not-always": (_set_job(GATE, **{"if": f"${{{{ {BASE_IF} }}}}"}), "missing job-level public guard"),
    "lane-if-bypass": (_set_job(LANE, **{"if": "${{ always() }}"}), "missing job-level public guard"),
    "lane-if-missing": (_del(("jobs", LANE, "if")), "missing job-level public guard"),
    "job-skip": (_set_job(LANE, **{"if": "${{ false }}"}), "cannot skip the job"),
    "step-skip": (_set_step(LANE, "qualify", **{"if": "false"}), "cannot skip the step"),
    "consumer-permissions": (_set_job(CONSUMER, permissions={"contents": "read"}), "permissions must be"),
    "lane-permissions": (_set_job(LANE, permissions={"contents": "write"}), "cannot increase permissions"),
    "id-token": (_set_job("native-assemble", permissions={"contents": "read", "actions": "read",
                                                           "id-token": "write"}), "id-token write forbidden"),
    "old-download-pin": (_set_step(GATE, "actions/download-artifact",
                                   uses="actions/download-artifact@fa0a91b85d4f404e444e00e005971372dc801d16"),
                         "download-artifact must use pin"),
    "unpinned-action": (_set_step("native-guard", "actions/checkout", uses="actions/checkout@v4"),
                        "not pinned to 40-char SHA"),
    "unapproved-action": (_add_step("native-guard", {"uses": "evil/publish@" + "a" * 40}),
                          "not an approved action pin"),
    "checkout-credentials": (_set_with("native-guard", "actions/checkout", **{"persist-credentials": True}),
                             "persist-credentials: false"),
    "download-option": (_set_with(GATE, "actions/download-artifact", **{"github-token": "x"}),
                        "download-artifact options not permitted"),
    "flatten-download": (_set_with(CONSUMER, "actions/download-artifact", **{"merge-multiple": True}), "download layout"),
    "consumer-job-token": (_set_job(CONSUMER, env={"GITHUB_TOKEN": "${{ github.token }}"}), "token must be scoped"),
    "consumer-runtime-token": (_env(CONSUMER, "consumer", "GITHUB_TOKEN", "${{ github.token }}"), "token forbidden"),
    "consumer-no-verifier": (_drop_step(CONSUMER, "verify_bundle"), "expected bundle verification step"),
    "consumer-conditional-verifier": (_set_step(CONSUMER, "verify_bundle", **{"if": "${{ success() }}"}), "expected bundle verification step"),
    "workflow-token": (lambda d: d["env"].update(GITHUB_TOKEN="${{ github.token }}"), "workflow-level GitHub token forbidden"),
    "consumer-late-verifier": (lambda d: d["jobs"][CONSUMER]["steps"].append(
        d["jobs"][CONSUMER]["steps"].pop(d["jobs"][CONSUMER]["steps"].index(_step(d, CONSUMER, "verify_bundle")))), "precede packaged execution"),
    "scan-no-verifier": (_drop_step("native-release-scans", "verify_bundle"), "expected bundle verification step"),
    "assemble-no-projection": (_edit_run("native-assemble", "matrix_receipts.py emit", "/public-projection-manifest.json", "/ignored.json"), "must bind artifact public-projection-manifest.json"),
    "lane-download": (_add_step(LANE, _use("actions/download-artifact", path="${{ runner.temp }}/x")),
                      "download-artifact forbidden outside post-lane jobs"),
    "retention": (_set_with(LANE, "upload_lane", **{"retention-days": 7}), "retention-days: 14"),
    "upload-outside-temp": (_set_with(LANE, "upload_lane", path="out"), "path must be under runner.temp"),
    "upload-warn": (_set_with(LANE, "upload_lane", **{"if-no-files-found": "warn"}), "if-no-files-found: error"),
    "expression-in-run": (_edit_run(LANE, "qualify", "qualify", "qualify ${{ github.head_ref }}"),
                          "run step contains expression"),
    "working-directory": (_set_step(LANE, "qualify", **{"working-directory": "."}), "working-directory is forbidden"),
    "step-continue-on-error": (_set_step(LANE, "qualify", **{"continue-on-error": True}),
                               "continue-on-error is forbidden"),
    "job-continue-on-error": (_set_job(LANE, **{"continue-on-error": True}), "unsupported job key"),
    "suppression": (_edit_run(LANE, "qualify", "\n", " || true\n"), "suppression token"),
    "wrong-caller-path": (_edit_run("native-guard", "guard", "tools/ci/native_lane.py", "release/ci/native_lane.py"),
                          "wrong helper path"),
    "missing-helper": (_edit_run(LANE, "qualify", "native_lane.py", "native_absent.py"),
                       "nonexistent or wrong helper path"),
    "output-outside-temp": (_edit_run(LANE, "qualify", f'--output "{TEMP}/out"', "--output out"),
                            "output path must be under RUNNER_TEMP"),
    "outputs-extra": (_set_job(LANE, outputs={**_job(LANE)["outputs"], "extra": "${{ steps.qualify.outputs.x }}"}),
                      "outputs must be"),
    "outputs-missing": (_pop_output(LANE), "outputs must be"),
    "output-bad-step": (lambda d: d["jobs"][LANE]["outputs"].update(
        seal_sha256="${{ steps.absent.outputs.seal_sha256 }}"), "must reference an existing step output"),
    "undeclared-output": (_env(CONSUMER, "consumer", "X", "${{ needs.native-assemble.outputs.nope }}"),
                          "undeclared output"),
    "undeclared-needs": (_env(LANE, "qualify", "X", "${{ needs.native-assemble.result }}"),
                         "without depending on it"),
    "no-go-shim": (_drop_step(CONSUMER, "bin/go"), "failing Go shim"),
    "go-in-assemble": (_add_step("native-assemble", _use("actions/setup-go", **{"go-version": "1.26.9"})),
                       "setup-go forbidden"),
    "go-missing": (_drop_step("native-release-scans", "actions/setup-go"), "missing required setup-go"),
    "go-version": (_set_with(LANE, "actions/setup-go", **{"go-version": "1.25.14"}), "setup-go must select"),
    "go-cache": (_set_with(LANE, "actions/setup-go", cache=True), "setup-go must set cache: false"),
    "nix-missing": (_drop_step(LANE, "cachix/install-nix-action"), "install-nix-action missing"),
    "nix-in-consumer": (_add_step(CONSUMER, _use("cachix/install-nix-action")), "install-nix-action forbidden"),
    "emit-literal-status": (_edit_run(LANE, "matrix_receipts.py emit", '"$CI_JOB_STATUS"', "success"),
                            "receipt emit must contain"),
    "emit-not-always": (lambda d: _step(d, LANE, "matrix_receipts.py emit").pop("if"), "must run with always()"),
    "emit-env": (_env(LANE, "matrix_receipts.py emit", "CI_JOB_STATUS", "success"), "must come from job.status"),
    "emit-artifact": (_edit_run("native-guard", "matrix_receipts.py emit", "/identity.json", "/other.json"),
                      "must bind artifact identity.json"),
    "emit-profile": (_edit_run(LANE, "matrix_receipts.py emit", "--workflow native-qualification ", ""),
                     "receipt emit must contain"),
    "emit-missing": (_drop_step(LANE, "matrix_receipts.py emit"), "exactly one receipt emit step"),
    "emit-duplicate": (_dup_step(LANE, "matrix_receipts.py emit"), "exactly one receipt emit step"),
    "receipt-upload-missing": (_drop_step(LANE, "upload_receipt"), "-receipt upload is required"),
    "receipt-upload-not-always": (lambda d: _step(d, LANE, "upload_receipt").pop("if"), "receipt upload must run"),
    "gate-missing-member": (lambda d: d["jobs"][GATE]["env"].update(MATRIX_NEEDS_RESULTS="{}"),
                            "must carry needs.native-guard.result"),
    "gate-without-native-gate": (_edit_run(GATE, "gate", "python3 tools/ci/native_gate.py", "echo"),
                                 "gate must run 'tools/ci/native_gate.py'"),
    "gate-without-statuses": (_edit_run(GATE, "gate", "--statuses-json", "--other"), "--statuses-json"),
    "gate-upload-missing": (_drop_step(GATE, "upload_gate"), "native-release-candidate-gate-result upload"),
    "secret": (_env("native-guard", "guard", "TOKEN", "${{ secrets.TOKEN }}"), "forbidden token 'secrets.'"),
    "dispatch": (lambda d: d["on"].update(workflow_dispatch={}), "only pull_request execution"),
    "target-branch": (lambda d: d["on"]["pull_request"].update(branches=["develop"]), "must target 'main'"),
    "path-filter": (lambda d: d["on"]["pull_request"].update(paths=["src/**"]), "cannot use event filters"),
    "pr-types": (_del(("on", "pull_request", "types")), "missing PR types"),
    "permissions": (lambda d: d.update(permissions={"contents": "write"}), "top-level permissions"),
    "concurrency": (lambda d: d["concurrency"].update({"cancel-in-progress": False}), "cancel-in-progress"),
    "top-level-key": (lambda d: d.update({"run-name": "x"}), "unsupported top-level key"),
    "guard-shallow": (_set_with("native-guard", "actions/checkout", **{"fetch-depth": 1}), "fetch-depth: 0"),
    "no-native-helper": (_edit_run(CONSUMER, "consumer", "tools/ci/native_lane.py", "true #"),
                         "precede packaged execution"),
}


@pytest.fixture
def native_doc() -> Doc:
    return _native_doc()


def test_synthetic_native_workflow_is_valid(native_doc: Doc) -> None:
    assert validate_native_qualification(native_doc, PATH) == []


def test_exact_native_job_inventory() -> None:
    assert len(REQUIRED_NATIVE_JOBS) == 10
    assert NATIVE_MEMBER_JOBS == set(MEMBER_JOBS) and GATE not in NATIVE_MEMBER_JOBS
    assert EXPECTED_NEEDS[GATE] == set(MEMBER_JOBS)
    assert {job: EXPECTED_RUNNERS[job] for job in LANES} == {
        "native-darwin-arm64": "macos-15", "native-linux-x64": "ubuntu-24.04", "native-linux-arm64": "ubuntu-24.04-arm"}


@pytest.mark.parametrize("name", sorted(CASES))
def test_native_topology_rejects_mutation(native_doc: Doc, name: str) -> None:
    mutate, expected = CASES[name]
    mutate(native_doc)
    errors = validate_native_qualification(native_doc, PATH)
    assert any(expected in error for error in errors), (expected, errors)


def test_validator_reports_malformed_documents_without_raising() -> None:
    assert any("missing jobs section" in e for e in validate_native_qualification({"jobs": []}, PATH))
    doc = _native_doc()
    doc["jobs"][LANE] = "not-an-object"
    assert any("job must be an object" in e for e in validate_native_qualification(doc, PATH))
    doc = _native_doc()
    doc["jobs"][LANE]["steps"] = []
    assert any("steps must be a non-empty list" in e for e in validate_native_qualification(doc, PATH))
