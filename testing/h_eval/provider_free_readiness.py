"""Read-only custody and bounded readiness for a provider-free H package."""
import hashlib
import json
import stat
from pathlib import Path

from agent_phase.transmission import direct_bytes

from .execution import _write_json
from .provider_free import verify_retained
from .readiness import make_seal, source_identity

TOKEN = "V0130_H_PROVIDER_FREE_PACKAGE_READY"
SCENARIOS = {f"scenario-{n:02d}" for n in range(1, 16)}
SKILLS = {"go-language-profile", "go-test-profile", "pytest-test-profile",
          "markdown-language-profile", "sqlite-database-profile"}
SPECIALS = {"scenario-12": {"midturn_recovery", "recovery_subtree"},
            "scenario-13": {"prelaunch_fallback"},
            "scenario-15": {"selective_projection"}}


def _inventory(directory):
    """Custody bound for retained qualification, separate from subject limits."""
    directory = Path(directory)
    if directory.resolve() != directory or not directory.is_dir():
        raise ValueError("provider-free custody root must be physical")
    files = {}
    total = 0
    for path in sorted(directory.rglob("*")):
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("provider-free custody entry must be regular")
        data = direct_bytes(path, utf8=False, max_bytes=256 << 20)
        total += len(data)
        if len(files) >= 100_000 or total > 2 << 30:
            raise ValueError("provider-free retained evidence exceeds custody bound")
        files[str(path.relative_to(directory))] = {
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "mode": stat.S_IMODE(info.st_mode)}
    return files


def retain_integrity(directory):
    directory = Path(directory)
    _write_json(directory / "integrity.json", {
        "schema": "apg.h-provider-free-integrity/v1", "files": _inventory(directory)})


def read_dry_run(directory):
    directory = Path(directory)
    integrity = json.loads((directory / "integrity.json").read_bytes())
    actual = _inventory(directory)
    actual.pop("integrity.json", None)
    if integrity != {"schema": "apg.h-provider-free-integrity/v1", "files": actual}:
        raise ValueError("provider-free retained evidence changed")
    result = json.loads((directory / "dry-run.json").read_bytes())
    verify_retained(directory / "provider-guard", result["provider_guard"])
    rows = result.get("records", [])
    if len(rows) != 15 or {row.get("scenario_id") for row in rows} != SCENARIOS:
        raise ValueError("provider-free scenario coverage incomplete")
    for row in rows:
        retained = json.loads((directory / "records" / row["scenario_id"] / "dry-run.json").read_bytes())
        if retained != row:
            raise ValueError("provider-free scenario summary differs from retained record")
    if result.get("aggregate_written") is not False:
        raise ValueError("provider-free evidence cannot be an H aggregate")
    if "promotion_oracle_fixtures" in result:
        retained = json.loads((directory / "promotion-oracle-fixtures/qualification.json").read_bytes())
        if result["promotion_oracle_fixtures"] != retained:
            raise ValueError("promotion fixture summary differs from retained qualification")
        from . import preregistration, starting_evidence
        root = Path(__file__).resolve().parents[2]
        cases = [case for skill in preregistration.verify_promotions(root)["skills"] for case in skill["cases"]]
        runtime = json.loads((directory / "runtime-manifest.json").read_bytes())
        starting_evidence.verify_all(retained, cases, runtime)
    return result


def _dry_run_complete(result):
    if (result.get("complete_records") != 15 or result.get("provider_invocations") != 0
            or result.get("runtime_transaction", {}).get("status") != "valid"
            or len(result.get("records", [])) != 15
            or {row.get("scenario_id") for row in result["records"]} != SCENARIOS):
        return False
    return all(row.get("status") == "complete" and row.get("initial_trees_equal") is True
               and all(row.get("subject_authority", {}).get(mode, {}).get("unchanged") is True
                       for mode in ("static", "adaptive"))
               and row.get("oracle", {}).get("fixture_exercise", {}).get("status") == "complete"
               and row.get("importer", {}).get("status") == "complete"
               and set(row.get("special", {})) == SPECIALS.get(row["scenario_id"], set())
               and all(value.get("status") == "complete" for value in row.get("special", {}).values())
               for row in result["records"])


def _promotion_fixtures_complete(result, root):
    """Require exact preregistered coverage, not just passing receipt counts."""
    from .preregistration import expected_oracle_inventory, verify_promotions
    from .promotion_oracles import source_sha256
    try:
        inventory = expected_oracle_inventory(verify_promotions(root))
    except (OSError, KeyError, TypeError, ValueError):
        return False
    expected = {row["case_id"]: row for row in inventory}
    evidence = result.get("promotion_oracle_fixtures", {})
    transaction = evidence.get("runtime_transaction", {})
    receipts = evidence.get("receipts", [])
    if (evidence.get("complete_qualification") is not True
            or evidence.get("qualification_mode") != "complete"
            or evidence.get("source_sha256") != source_sha256(root)
            or evidence.get("cases") != len(expected)
            or evidence.get("fixture_pairs") != len(expected)
            or len(receipts) != 2 * len(expected)):
        return False
    seen = set()
    for receipt in receipts:
        case_id, fixture = receipt.get("case_id"), receipt.get("fixture")
        binding = expected.get(case_id)
        key = (case_id, fixture)
        if (binding is None or fixture not in {"pass", "fail"} or key in seen
                or receipt.get("status") != fixture
                or any(receipt.get(field) != binding[field]
                       for field in ("oracle_id", "hidden_oracle_sha256"))):
            return False
        seen.add(key)
        if binding["kind"] == "non-trigger":
            if receipt.get("qualification_scope") != "structural-only; semantic-non-use-not-evaluated":
                return False
        elif binding["fixture_kind"] == "command":
            judged = receipt.get("model_evaluation", {})
            if judged.get("status") != fixture:
                return False
            if binding["skill_id"] in {"go-test-profile", "pytest-test-profile"}:
                authored = judged.get("model_authored_tests", {})
                if authored.get("status") != fixture:
                    return False
                if fixture == "pass" and (authored.get("good", {}).get("status") != "pass"
                                           or authored.get("bad", {}).get("status") != "fail"):
                    return False
    positive = {key for key, row in expected.items() if row["kind"] == "positive"}
    starts = evidence.get("starting_subjects", [])
    if (evidence.get("starting_subject_count") != len(positive)
            or len(starts) != len(positive)
            or {row.get("case_id") for row in starts} != positive
            or any(row.get("status") != "fail" or row.get("starting_failure_required") is not True
                   for row in starts)):
        return False
    from .starting_evidence import verify_all
    try:
        cases = [case for skill in verify_promotions(root)["skills"] for case in skill["cases"]]
        verify_all(evidence, cases)
    except (OSError, KeyError, TypeError, ValueError):
        return False
    return (transaction.get("before_revalidated") is True
            and transaction.get("after_revalidated") is True
            and transaction.get("manifest_sha256") == transaction.get("after_manifest_sha256")
            == result.get("runtime_transaction", {}).get("manifest_sha256"))


def make_package_seal(root, directory, *, independent_review=None):
    """Seal mechanical evidence only; independent acceptance is external.

    Even a well-formed review mapping cannot authenticate dispatcher custody.
    The legacy keyword is refused rather than silently granting authority.
    """
    if independent_review is not None:
        raise ValueError("independent review custody belongs to dispatcher/manager")
    root, directory = Path(root), Path(directory)
    result = read_dry_run(directory)
    source = make_seal(root)
    identity = source_identity(source["files"])
    promotion = hashlib.sha256((root / "testing/h_eval/promotion-preregistration.json").read_bytes()).hexdigest()
    gates = {
        "provider_free_transaction": _dry_run_complete(result),
        "promotion_oracle_fixtures": _promotion_fixtures_complete(result, root),
        "source_inventory": result.get("source_identity") == identity,
    }
    return {"schema": "apg.h-provider-free-package-seal/v2", "phase": "APG166E",
            "source_identity": identity, "files": source["files"], "gates": gates,
            "provider_free_mechanical_candidate": all(gates.values()),
            "provider_free_package_ready": False, "manager_review_required": True,
            "checkpoint": "V0130_H_PROVIDER_FREE_MANAGER_PENDING",
            "dry_run_sha256": hashlib.sha256((directory / "dry-run.json").read_bytes()).hexdigest(),
            "promotion_preregistration_sha256": promotion,
            "promotion_preregistration_acceptance": "pending-independent-review",
            "prerequisites_ready": False, "h_main_gate": False, "d1_authorized": False,
            "live_holdout_authorized": False, "qualified_promotions": 0,
            "scenario15": "contingent/unavailable", "v0130_i_authorized": False,
            "blockers": [name for name, passed in gates.items() if not passed] + ["manager_review_required"]}
