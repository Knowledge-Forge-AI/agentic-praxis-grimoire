"""Reproducible prerequisite source inventory; live-probe receipts require separate custody verification."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SCHEMA = "apg.h-readiness-seal/v1"
PATTERNS = (
    "libexec/**/*.py", "src/agentic_praxis_grimoire/**/*.py",
    "skills/**/*.go", "skills/**/*.json", "skills/**/SKILL.md",
    "internal/**/*.go", "cmd/**/*.go", "testing/h_eval/*.py", "testing/h_eval/*.json",
    "candidate/**/*.go", "envsnap/**/*.go", "evidence/**/*.go", "footprint/**/*.go",
    "hotspot/**/*.go", "phase/**/*.go", "provider/**/*.go", "report/**/*.go",
    "routing/**/*.go", "schema/**/*.go",
    "testing/fixtures/context-eval/*.json", "testing/fixtures/context-eval/measure_f.py",
    "testing/fixtures/context-eval/subjects/**/*",
    "src/test/dispatcher/test_h_*.py", "src/test/dispatcher/test_agent_phase_context.py",
    "src/test/dispatcher/test_agent_phase_acquisition.py", "common/dispatcher/**/*",
    "src/test/dispatcher/test_apg166_records.py",
    "codex/profiles/**/*", "claude/profiles/**/*", "antigravity/profiles/**/*",
    "codex/AGENTS.md", "claude/CLAUDE.md", "antigravity/GEMINI.md",
    "claude/settings.json", "claude/model-catalog-v1.json", "docs/governance/skill-maturity-ledger.json",
    "docs/governance/language-profile-known-debt.json", "bin/claude-profile",
    "bin/antigravity-profile", "go.mod", "go.sum", "testing/apg-test-inventory.json",
    "bin/agent-worker", "bin/agent-worker-mcp", "bin/apgr-worker-canary",
    "bin/apgr-dispatcher-bundle", "codex/config.d/170-subagents.toml",
    "common/skills/agent-worker/*.md", "src/test/dispatcher/test_apg166s*.py",
    "src/agentic_praxis_grimoire/VERSION", "src/agentic_praxis_grimoire/resources/*.json",
)


def _qualification(value):
    fields = {"probe_id", "evidence_sha256", "raw_stream_sha256", "cli_version", "profile", "model", "effort"}
    if not isinstance(value, dict) or set(value) != fields or not all(isinstance(v, str) and v for v in value.values()):
        raise ValueError("complete native Read probe qualification required")
    if value["probe_id"] != "APG166B-PROBE-1" or value["profile"] != "normal-final-review":
        raise ValueError("unqualified native Read route")
    for field in ("evidence_sha256", "raw_stream_sha256"):
        if len(value[field]) != 64 or any(c not in "0123456789abcdef" for c in value[field]):
            raise ValueError("invalid probe evidence identity")
    return value


def make_seal(root, qualification=None):
    root = Path(root)
    paths = set()
    for pattern in PATTERNS:
        paths.update(p for p in root.glob(pattern) if p.is_file())
    if any(p.is_symlink() for p in paths):
        raise ValueError("sealed input must be a regular source owner")
    value = {"schema": SCHEMA, "phase": "APG166A", "purpose": "pre-live infrastructure source inventory",
            "files": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)},
            "prerequisites_ready": False, "blockers": ["complete live native recovery observation unavailable"],
            "live_pairs": 0, "qualified_promotions": 0, "h_gate_established": False,
            "scenario15": "contingent/unavailable", "default": "static",
            "policy": "Verify accepted source and this inventory before live holdout; any sealed input change after results invalidates the complete live set."}

    if qualification is not None:
        value.update(phase="APG166B", qualification=_qualification(qualification),
                     prerequisites_ready=False, blockers=[
                         "Claude adaptive MCP acquisition cannot use the qualified read-only profile observer route",
                         "Concrete holdout subjects, routes, result importers and substantive oracles remain unbound",
                         "Current CLI repeated-Read structured-result semantics remain unqualified",
                     ],
                     qualification_boundary="Single full-file native Read observation only; source recomputation does not authenticate private probe receipts or qualify adaptive acquisition.")
    return value


def verify_seal(root, seal):
    current = (make_ready1_seal(root, seal.get("evidence")) if seal.get("phase") == "APG166V"
               else make_qual5_seal(root, seal.get("evidence"), seal.get("independent_review")) if seal.get("phase") == "APG166D"
               else make_qual4_seal(root, seal.get("probe_evidence")) if seal.get("phase") == "APG166C"
               else make_seal(root, seal.get("qualification")))
    if current != seal:
        raise ValueError("readiness inputs changed; live holdout must not proceed")


def source_identity(files):
    return hashlib.sha256((json.dumps(files, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()


def verify_d1_carry_forward(root):
    """Validate a historical representation, never authenticate external acceptance."""
    path = Path(root) / "testing/h_eval/d1-carry-forward.json"
    value = json.loads(path.read_bytes())
    expected_attempts = {
        "D1-01": {"recorded_status": "failed", "consumed": True},
        "D1-02": {"recorded_status": "failed", "readback_status": "unqualified_with_readback", "consumed": True},
    }
    if (set(value) != {"schema", "phase", "attempts", "observation", "replay", "manager_decision", "historical_custody", "scope"}
            or value["schema"] != "apg.h-d1-carry-forward/v1" or value["phase"] != "APG166V"
            or value["attempts"] != expected_attempts
            or value["observation"] != {"attempt": "D1-02", "classification": "inherited-observation",
                "native_read_and_exact_nonce": True, "profile": "normal-final-review"}
            or value["replay"] != {"reference": "APG166T-REPAIR2 finalized offline interpretation",
                "status": "passing", "classification": "corrected-offline-replay", "live_provider_run": False}
            or value["manager_decision"] != {
                "reference": "APG166V-H-READY1 manager disposition dated 2026-09-28",
                "custody": "external", "self_certified": False}
            or value["historical_custody"] != "Original identities, failed records and consumed ledgers retained externally; not rewritten or re-read here"
            or value["scope"] != "Native Read capability and separate corrected replay only; not selective projection, adaptive acquisition, H benefit or a live grant"):
        raise ValueError("D1 carry-forward historical boundary changed")
    return value


def make_ready1_seal(root, evidence=None, *, independent_review=None, manager_grant=None):
    """Recompute current mechanical facts; external decisions cannot be supplied here."""
    if independent_review is not None or manager_grant is not None:
        raise ValueError("review and grant custody belongs to dispatcher/manager")
    from .preregistration import verify_bindings, verify_promotions
    from .execution import LIVE_ADMISSION_AVAILABLE
    from .provider_free_readiness import make_package_seal
    from . import runtime_manifest
    evidence = {} if evidence is None else evidence
    if not isinstance(evidence, dict) or set(evidence) - {"transaction_directory"}:
        raise ValueError("only retained mechanical transaction evidence is accepted")
    verify_bindings(root)
    verify_promotions(root)
    carry = verify_d1_carry_forward(root)
    value = make_seal(root)
    package = None
    runtime_digest = None
    if evidence:
        directory = Path(evidence["transaction_directory"])
        package = make_package_seal(root, directory)
        manifest = json.loads((directory / "runtime-manifest.json").read_bytes())
        runtime_manifest.verify(manifest)
        runtime_digest = runtime_manifest.manifest_digest(manifest)
    gates = {
        "bindings_current": True, "promotion_preregistration_current": True,
        "d1_carry_forward_recorded": True,
        "provider_free_transaction": package is not None and package["provider_free_mechanical_candidate"],
        "runtime_manifest": runtime_digest is not None,
        "live_admission_available": LIVE_ADMISSION_AVAILABLE,
        "independent_preregistration_dispositions": False, "manager_live_grant": False,
    }
    value.update(phase="APG166V", continuation="H-READY1", evidence=evidence,
                 source_identity=source_identity(value["files"]), prerequisite_gates=gates,
                 d1_carry_forward=carry, d1_carry_forward_validation="structural-only; external acceptance not authenticated",
                 final_source_d1="historical exact-source boolean not applicable to manager carry-forward",
                 mechanical_package=package, runtime_manifest_sha256=runtime_digest,
                 prerequisites_ready=False, h_main_gate=False, live_holdout_authorized=False,
                 manager_review_required=True, v0130_i_authorized=False,
                 blockers=[name for name, passed in gates.items() if not passed],
                 qualification_boundary="Preparation only; instrumented mechanics, inherited observation, corrected replay, independent review and later manager grant remain distinct")
    return value


def make_qual5_seal(root, evidence=None, independent_review=None):
    """Historical mechanical summary; independent review is manager-owned."""
    if independent_review is not None:
        raise ValueError("independent review custody belongs to dispatcher/manager")
    from .preregistration import verify_bindings, verify_promotions
    from .execution import LIVE_ADMISSION_AVAILABLE
    verify_bindings(root)
    verify_promotions(root)
    value = make_seal(root)
    evidence = evidence or {}
    source = source_identity(value["files"])
    promotion = hashlib.sha256((Path(root) / "testing/h_eval/promotion-preregistration.json").read_bytes()).hexdigest()
    gates = {
        "complete_execution_package": evidence.get("complete_execution_package") is True and LIVE_ADMISSION_AVAILABLE,
        "all_subject_dry_run": evidence.get("dry_run") == {"complete_records": 15, "provider_invocations": 0},
        "complete_runtime_manifest": evidence.get("runtime_manifest_complete") is True,
        "final_source_d1": evidence.get("d1", {}).get("status") == "qualified"
            and evidence.get("d1", {}).get("probe_id") == "APG166D-PROBE-D1"
            and evidence.get("d1", {}).get("source_identity") == source,
        "manager_review_required": False,
    }
    for key in ("runtime_manifest_sha256", "dry_run_sha256", "d1_evidence_sha256"):
        digest = evidence.get(key, "")
        gates[key] = isinstance(digest, str) and len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
    value.update(phase="APG166D", evidence=evidence, manager_review_required=True,
                 source_identity=source, prerequisite_gates=gates,
                 promotion_preregistration_sha256=promotion,
                 prerequisites_ready=False, complete_execution_package=gates["complete_execution_package"],
                 runtime_manifest_schema="apg.h-runtime-inputs/v2", v0130_i_authorized=False,
                 checkpoint="V0130_H_PREREQUISITES_BLOCKED",
                 blockers=[name for name, passed in gates.items() if not passed],
                 live_holdout_authorized=False,
                 qualification_boundary="Prerequisites only; private packet custody and independent review are external authority. No H or promotion execution.")
    return value


def make_qual4_seal(root, probes=None):
    """Keep partial execution bindings explicit; never mint a readiness token."""
    from .preregistration import verify_bindings, verify_promotions
    verify_bindings(root)
    verify_promotions(root)
    value = make_seal(root)
    value.update(phase="APG166C", probe_evidence=probes or {},
                 runtime_manifest_schema="apg.h-runtime-inputs/v1",
                 prerequisites_ready=False, v0130_i_authorized=False,
                 checkpoint="V0130_H_PREREQUISITES_BLOCKED",
                 complete_execution_package=False,
                 blockers=["Concrete clean subject factories, result importers and substantive oracle implementations remain unfrozen",
                           "Complete 15-subject dry-run unavailable; preflight inventory is not an execution package",
                           "Full H provider/runtime/projection inputs remain unqualified and unbound",
                           "Dispatcher-owned independent work review pending"],
                 qualification_boundary="Bounded Claude wrapper/native-Read mechanism only; no H execution or positive skill use")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("write", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seal", type=Path, required=True)
    parser.add_argument("--qualification", type=Path, help="Digest-bound private probe receipt summary (write only)")
    args = parser.parse_args()
    if args.action == "verify":
        verify_seal(args.root, json.loads(args.seal.read_bytes()))
    else:
        with args.seal.open("xb") as stream:
            stream.write((json.dumps(make_seal(args.root, json.loads(args.qualification.read_bytes()) if args.qualification else None), indent=2, sort_keys=True)+"\n").encode())


if __name__ == "__main__":
    main()
