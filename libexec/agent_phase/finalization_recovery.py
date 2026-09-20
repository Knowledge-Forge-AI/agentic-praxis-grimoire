"""Provider-free finalization, with new receipts and immutable source runs."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import uuid

from . import archive_verify, finalization, gitstate, outcomes
from . import finalization_proof as proof_module
from .display import Display
from .lifecycle import FINALIZATION_POLICIES, get_lifecycle


SCHEMA = "agent-phase-finalization-recovery-v1"


class ReceiptDirectory:
    def __init__(self, source: Path) -> None:
        self.path = source.parent / f"{source.name}.finalization-{uuid.uuid4().hex}"
        self.path.mkdir(mode=0o700)

    def write_bytes(self, name: str, data: bytes) -> Path:
        path = self.path / name
        with path.open("xb") as stream:
            stream.write(data)
        path.chmod(0o600)
        return path

    def write_json(self, name: str, value: object) -> Path:
        return self.write_bytes(name, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())


def _receipt(proof: proof_module.Proof, policy: str, dry_run: bool) -> dict:
    from controller_generation import provenance
    from . import ownership_challenge
    repair_code = {
        "recognize_materialization": "CANDIDATE_MATERIALIZATION_VERIFIED",
        "verify_existing": "RECORDED_FINALIZATION_VERIFIED",
    }.get(proof.action)
    if (proof.action == "finalize"
            and (proof.state.get("blocking_reason") or {}).get("code") == "PATH_DISPOSITION_INVALID"):
        repair_code = "METADATA_NORMALIZATION_VERIFIED"
    ownership_evidence = []
    for index, resolution in enumerate(proof.ownership_resolutions, 1):
        ownership_evidence.append({
            "challenge_id": resolution["challenge_id"],
            "decision": resolution["decision"],
            "receipt_sha256": resolution["sha256"],
            "reason": resolution["reason"],
            "filename": (
                None if dry_run else f"ownership-resolution-{index}.json"
            ),
        })
    return {
        "controller_generation": provenance(),
        "source_controller_generation": proof.state.get("controller_generation"),
        "schema": SCHEMA, "source_run_id": proof.state["run_id"],
        "source_manifest": proof.source_manifest,
        "source_entry_head": proof.entry.head, "observed_head": proof.current.head,
        "source_semantic_outcome": proof.state.get("semantic_outcome"),
        "validated_terminal_outcome": proof.terminal.outcome,
        "candidate_manifest": proof.manifest, "path_ownership": proof.state["path_ownership"],
        "adoption": proof.state.get("adoption"),
        "phase_owned_paths": sorted(proof.manifest["paths"]),
        "mechanical_phase_owned_paths": proof.state.get("mechanical_phase_owned_paths") or [],
        "excluded_paths": proof.state.get("excluded_paths") or [],
        "path_disposition_noops": proof.state.get("path_disposition_noops") or [],
        "unrelated_committed_paths_not_adopted": proof.extras,
        "branch": proof.current.branch, "finalization_policy": policy,
        "dry_run": dry_run, "action": proof.action,
        "repair": {"code": repair_code,
                   "repair_class": outcomes.classify_failure(repair_code) if repair_code else None},
        "provider_invocations": 0, "product_test_invocations": 0,
        "git_mutation_performed": False, "publication_attempted": False,
        "source_rewritten": False, "finalization": {"outcome": "not_attempted"},
        "ownership_resolutions": ownership_evidence,
        # Preserve the complete validated manager receipts in the new
        # provider-free evidence.  The source run remains immutable; this
        # copy lets a later adoption/materialization proof rebind the exact
        # challenge, candidate, and decision without trusting a path summary.
        "ownership_resolution_records": deepcopy(proof.ownership_resolutions),
        "ownership_challenges": proof.state.get("ownership_challenges"),
        "ownership_challenge_states": ownership_challenge.statuses(proof.state),
    }


def _write_ownership_resolution_copies(
    directory: ReceiptDirectory, proof: proof_module.Proof
) -> None:
    """Retain validated manager receipts beside the new recovery receipt."""
    for index, resolution in enumerate(proof.ownership_resolutions, 1):
        directory.write_json(f"ownership-resolution-{index}.json", resolution)


def _execute(proof: proof_module.Proof, directory: ReceiptDirectory, policy: str) -> dict:
    from controller_generation import provenance
    from . import ownership_challenge
    state = deepcopy(proof.state)
    lifecycle = get_lifecycle(state["lifecycle"])
    resolved_paths = sorted({
        receipt["challenge"]["path"] for receipt in proof.ownership_resolutions
    })
    # Only a proved checkpoint or redundant metadata stop reaches here.
    # No ownership decision is changed: proof already rejected ambiguities.
    state.update({
        "controller_generation": provenance(directory.path.name),
        "source_controller_generation": proof.state.get("controller_generation"),
        "finalization_policy": policy, "resumed": True,
        "manager_disposition_required": False, "manager_attention_reasons": [],
        "manager_attention_records": [],
        "manager_disposition": {
            "required": False,
            "reason": "ownership_challenges_resolved" if resolved_paths else None,
            "paths": resolved_paths,
            "candidate_tree": proof.manifest.get("candidate_tree"),
            "automatic_publication": "permitted",
        },
        "blocking_reason": None, "commit": None,
        "effective_stages": {stage: "inherited" for stage in lifecycle.stage_names},
        "provider_invocations_inherited": len(lifecycle.stage_names),
        "provider_invocations_performed": 0,
        "source_run_id": proof.state["run_id"],
        "run_id": directory.path.name,
        "run_directory": str(directory.path),
        "complete": False, "outcome": None,
        "resume": {"finalization_replayed": True,
                   "source_entry_head": proof.entry.head,
                   "source_entry_tree": proof.state["path_ownership"]["entry_tree"]},
        "ownership_resolution_receipts": [
            {"challenge_id": item["challenge_id"],
             "decision": item["decision"],
             "receipt_sha256": item["sha256"],
             "filename": f"ownership-resolution-{index}.json"}
            for index, item in enumerate(proof.ownership_resolutions, 1)
        ],
        "ownership_resolution_records": deepcopy(proof.ownership_resolutions),
        # The ledger is immutable evidence; this derived view reflects the
        # manager events applied to the recovery copy rather than the source's
        # still-open statuses.
        "ownership_challenge_states": ownership_challenge.statuses(proof.state),
    })
    display = Display(sys.stderr, enabled=False)
    try:
        finalization.finalize_repository(state, proof.current, proof.terminal, display,
                                        resumed=True, directory=directory)
    except (finalization.FinalizationError, gitstate.GitStateError) as error:
        state["blocking_reason"] = {"code": error.code, "detail": error.detail}
    finally:
        display.close()
    state["ownership_challenge_states"] = ownership_challenge.statuses(state)
    state["complete"] = not state.get("blocking_reason")
    state["outcome"] = "completed" if state["complete"] else "blocked"
    state["semantic_outcome"] = proof.terminal.outcome
    outcomes.finish(state)
    return state


def _human_receipt(receipt: dict) -> bytes:
    """Bounded human readback; authority remains in the exact JSON records."""
    records = (receipt.get('ownership_challenges') or {}).get('records', [])
    statuses = receipt.get('ownership_challenge_states') or {}
    lines = ['# Finalization recovery', '',
        f"- Semantic outcome: {receipt['validated_terminal_outcome']}",
        f"- Finalization outcome: {receipt['finalization']['outcome']}",
        f"- Repair class: {receipt['finalization'].get('repair_class')}",
        '- Provider invocations: 0; product test invocations: 0',
        f"- Mechanical ownership: {len(receipt['mechanical_phase_owned_paths'])} path(s)",
        f"- Exclusions: {len(receipt['excluded_paths'])} path(s)",
        f"- Metadata no-ops: {len(receipt['path_disposition_noops'])}", '']
    for status in ('open', 'resolved_by_provider', 'resolved_by_manager', 'superseded'):
        lines.append(f'- {status}: {sum(value == status for value in statuses.values())}')
    lines.extend(['', 'Entry dirt is not automatically restored. Exclusions affect only the private publication tree.',
                  'Exact objects, complete path sets and authority records are retained in receipt.json.', ''])
    for record in records[:128]:
        view = {key: record[key] for key in ('challenge_id', 'path', 'reason')}
        if len(view['path']) > 1024:
            view['path'] = view['path'][:1024] + ' [display truncated; see receipt.json]'
        view['state'] = statuses[record['challenge_id']]
        lines.extend(['```json', json.dumps(view, ensure_ascii=False, indent=2), '```', ''])
    if len(records) > 128:
        lines.append(f'{len(records) - 128} challenge records omitted from Markdown; retained in receipt.json.')
    return ('\n'.join(lines) + '\n').encode('utf-8')


def _deliver(directory: ReceiptDirectory, receipt: dict, state: dict | None) -> None:
    """Receipt delivery cannot erase a completed local commit or push."""
    receipt["delivery"] = {"outcome": "completed", "receipt_written": True}
    receipt["receipt_path"] = str(directory.path / "receipt.json")
    try:
        if state is not None:
            directory.write_json("finalization-state.json",
                                 {key: value for key, value in state.items()
                                  if key != "_ownership_recovery"})
        directory.write_bytes("receipt.md", _human_receipt(receipt))
        directory.write_json("receipt.json", receipt)
    except OSError:
        receipt["delivery"] = {"outcome": "blocked", "receipt_written": False,
                               "code": "RECOVERY_RECEIPT_DELIVERY_FAILED"}


def _verify_source_after(proof: proof_module.Proof, receipt: dict) -> None:
    try:
        unchanged = archive_verify.source_manifest(proof.source) == proof.source_manifest
    except (OSError, archive_verify.VerificationError):
        unchanged = False
    receipt["source_verification"] = {"outcome": "completed" if unchanged else "blocked"}
    if not unchanged:
        receipt["source_rewritten"] = None
        receipt["source_verification"]["code"] = "RECOVERY_SOURCE_CHANGED_OR_UNAVAILABLE"


def recover(source: Path, root: Path, *, dry_run: bool = False,
            policy: str | None = None, authorize_policy_upgrade: bool = False,
            ownership_resolutions: list[Path] | tuple[Path, ...] | None = None,
            ownership_resolution: Path | None = None) -> dict:
    """Name one source; never discover latest or execute a semantic lifecycle."""
    proof_module.require_standard_environment()
    root = gitstate.repository_root(root).resolve()
    if source.resolve().is_relative_to(root):
        proof_module.refuse("RECOVERY_SOURCE_LOCATION", "run evidence must be outside the product repository")
    if ownership_resolution is not None:
        if ownership_resolutions:
            proof_module.refuse(
                "OWNERSHIP_RESOLUTION_INVALID",
                "singular and repeated resolution inputs cannot be combined",
                "requires_manager_ownership",
            )
        ownership_resolutions = [ownership_resolution]
    proof = proof_module.inspect(source, root, ownership_resolutions)
    policy = policy or proof.state["finalization_policy"]
    finalization.validate_transition(proof.state["finalization_policy"], policy)
    if policy != proof.state["finalization_policy"] and not authorize_policy_upgrade:
        proof_module.refuse("RECOVERY_POLICY_AUTHORITY_REQUIRED",
                            "policy upgrade requires --authorize-policy-upgrade",
                            "requires_manager_ownership")
    receipt = _receipt(proof, policy, dry_run)
    receipt["policy_upgrade_authorized"] = authorize_policy_upgrade
    if proof.action == "finalize" and policy != "checkpoint":
        proof_module.require_no_execution_hooks(root)
    proof_module.revalidate(proof)
    if dry_run:
        receipt["finalization"] = {"outcome": "planned"}
        return receipt
    directory = ReceiptDirectory(proof.source)
    _write_ownership_resolution_copies(directory, proof)
    state = None
    if proof.action != "finalize":
        receipt["finalization"] = {
            "outcome": "materialized" if proof.action == "recognize_materialization" else "reused",
            "commit": proof.current.head,
            "repair_class": receipt["repair"]["repair_class"],
        }
        # Recognition proves local objects only. It never upgrades publication.
        receipt["publication"] = {"status": "not_attempted_materialized"}
        proof_module.revalidate(proof)
    else:
        proof_module.revalidate(proof)
        if policy != "checkpoint":
            proof_module.require_no_execution_hooks(root)
        state = _execute(proof, directory, policy)
        receipt["final_head"] = gitstate.current_head(root)
        receipt["git_mutation_performed"] = receipt["final_head"] != proof.current.head
        receipt["publication"] = state.get("push")
        receipt["publication_attempted"] = bool((state.get("push") or {}).get("attempted"))
        failure = state.get("blocking_reason")
        receipt["finalization"] = {
            "outcome": "blocked" if failure else "completed",
            "commit": state.get("commit"), "blocking_reason": failure,
            "repair_class": outcomes.classify_failure(failure["code"], state) if failure else None,
        }
        receipt["finalization"]["local_commit"] = state["finalization"]["local_commit"]
        _verify_source_after(proof, receipt)
    _deliver(directory, receipt, state)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent-phase-finalize", allow_abbrev=False)
    parser.add_argument("--run", type=Path, required=True, help="exact historical run directory")
    parser.add_argument("--dry-run", action="store_true", help="prove and print plan; write no receipt or Git refs")
    parser.add_argument("--finalization", choices=FINALIZATION_POLICIES)
    parser.add_argument("--authorize-policy-upgrade", action="store_true",
                        help="explicit operator authority for a stronger finalization policy")
    parser.add_argument("--ownership-resolution", type=Path, action="append", default=[],
                        metavar="RECEIPT",
                        help="exact manager ownership receipt; repeat for multiple challenges")
    args = parser.parse_args(argv)
    try:
        receipt = recover(args.run, Path.cwd(), dry_run=args.dry_run, policy=args.finalization,
                          authorize_policy_upgrade=args.authorize_policy_upgrade,
                          ownership_resolutions=args.ownership_resolution)
    except (proof_module.RecoveryError, finalization.FinalizationError,
            gitstate.GitStateError, ValueError, RuntimeError, OSError, TypeError, KeyError) as error:
        code = getattr(error, "code", "RECOVERY_EVIDENCE_INVALID")
        receipt = {"schema": SCHEMA, "action": "refused", "provider_invocations": 0,
                   "finalization": {"outcome": "blocked", "code": code,
                       "repair_class": getattr(error, "repair_class", outcomes.classify_failure(code, {}))}}
        json.dump(receipt, sys.stdout, sort_keys=True, indent=2)
        sys.stdout.write("\n")
        return 2
    json.dump(receipt, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 2 if (receipt["finalization"]["outcome"] == "blocked"
                 or receipt.get("delivery", {}).get("outcome") == "blocked"
                 or receipt.get("source_verification", {}).get("outcome") == "blocked") else 0
