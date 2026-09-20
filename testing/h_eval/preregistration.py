"""Provider-free verification of preregistered cases and unavailable bindings.

This inventory is deliberately not a live execution driver. Null subject,
importer and substantive-oracle owners remain blocking; receipt import is not an
oracle and a caller-supplied projection is not an isolation qualification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
from pathlib import Path

from .evaluate import load
from . import promotion_oracles

TARGETS = {"go-language-profile", "go-test-profile", "pytest-test-profile",
           "markdown-language-profile", "sqlite-database-profile"}

_ATTRIBUTION_INSUFFICIENT = [
    "skill delivery", "native Read", "skill acquisition", "prompt compliance"
]
_PROMPT_CHECKLIST_MARKERS = (
    "add tests", "use subtests", "cleanup", "race-test", "race test",
    "pytest-xdist", "xdist", "worker count", "wal mode", "sqlite3",
    "commonmark", "parser dialect", "renderer/version", "rendered evidence",
    "driver/library", "filesystem facts", "integrity verification",
    "transactional failure", "runner selection", "capture race",
)

_REQUIRED_NON_TRIGGERS = {
    "go-language-profile": {"go-test-only", "non-go"},
    "go-test-profile": {"production-go", "foreign-tests"},
    "pytest-test-profile": {"bats", "unittest"},
    "markdown-language-profile": {"mdx", "frontmatter"},
    "sqlite-database-profile": {"postgresql", "generic-sql"},
}
_REQUIRED_GO_LANGUAGE_CATEGORIES = {"cancellation", "concurrency", "api-resources"}
_REVIEW_SKILLS = tuple(sorted(TARGETS))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def case_identity(case):
    value = {k: v for k, v in case.items() if k != "case_sha256"}
    # The oracle records the digest that binds this case, but that field must
    # not recursively hash itself.  All other oracle bytes remain part of the
    # case identity.
    if isinstance(value.get("oracle"), dict):
        value["oracle"] = {k: v for k, v in value["oracle"].items() if k != "case_sha256"}
    return sha((json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode())


def expected_oracle_inventory(value):
    """Derive the expected registry inventory from the preregistration only."""
    inventory = []
    for row in value["skills"]:
        for case in row["cases"]:
            oracle = case["oracle"]
            inventory.append({
                "case_id": case["case_id"],
                "skill_id": row["skill_id"],
                "kind": case["kind"],
                "oracle_id": oracle.get("oracle_id"),
                "hidden_oracle_sha256": oracle.get("hidden_oracle_sha256"),
                "fixture_kind": oracle.get("fixture_kind"),
                "fixture_contract": oracle.get("fixture_contract"),
                "case_sha256": case.get("case_sha256"),
            })
    return inventory


def _verify_case_attribution(case):
    kind = case["kind"]
    expected = {
        "material_decision_required": True,
        "decision_not_dictated_by": ["prompt", "oracle"],
        "exact_guidance_link_required": kind == "positive",
        "resulting_work_link_required": True,
        "insufficient_evidence": _ATTRIBUTION_INSUFFICIENT,
        "mode": "positive_use" if kind == "positive" else "semantic_non_use",
    }
    if kind == "non-trigger":
        expected["neighboring_domain_non_use_required"] = True
        expected["semantic_non_use_link_required"] = True
    if case.get("attribution_rubric") != expected:
        raise ValueError("attribution rubric changed")
    if kind == "positive":
        if not any("not dictated by the prompt or oracle" in item.lower()
                   for item in case["required_evidence"]):
            raise ValueError("positive attribution evidence changed")
        prompt = case["prompt"].lower()
        if any(marker in prompt for marker in _PROMPT_CHECKLIST_MARKERS):
            raise ValueError("checklist-leading prompt")
        oracle = case["oracle"]["independent_rubric"].lower()
        if any(marker in oracle for marker in _PROMPT_CHECKLIST_MARKERS):
            raise ValueError("checklist-leading oracle")
    else:
        if not any("semantic non-use decision" in item.lower()
                   for item in case["required_evidence"]):
            raise ValueError("non-trigger attribution evidence changed")


def _verify_case_oracle(case, skill_id):
    """Bind every case to an independent, source-owned fixture contract."""
    oracle = case.get("oracle")
    if not isinstance(oracle, dict):
        raise ValueError("promotion oracle missing")
    try:
        spec = promotion_oracles.spec_for(case["case_id"])
    except (KeyError, promotion_oracles.PromotionOracleError) as exc:
        raise ValueError("promotion oracle fixture missing") from exc
    expected_command = list(spec.command) if spec.command is not None else None
    if (oracle.get("schema") != promotion_oracles.SCHEMA
            or oracle.get("fixture_id") != case["case_id"]
            or oracle.get("fixture_source") != promotion_oracles.SOURCE_PATH
            or oracle.get("oracle_id") != spec.oracle_id
            or oracle.get("hidden_oracle_sha256") != spec.hidden_oracle_sha256
            or oracle.get("case_sha256") != case.get("case_sha256")
            or oracle.get("fixture_kind") != spec.fixture_kind
            or oracle.get("fixture_contract") != spec.check_name
            or oracle.get("command") != expected_command
            or oracle.get("runtime_requirements") != list(spec.runtime_requirements)
            or oracle.get("expected_status") != {"good": "pass", "bad": "fail"}
            or oracle.get("hidden_fact_digests") != [sha(fact.encode()) for fact in spec.hidden_facts]
            or oracle.get("assertion_owner") != "source-owned"):
        raise ValueError("promotion oracle binding changed")
    if case["kind"] != spec.kind:
        raise ValueError("promotion oracle kind changed")
    if not oracle.get("independent_rubric") or "source-owned" not in oracle["independent_rubric"].lower():
        raise ValueError("promotion oracle rubric is not independent")
    if case["case_id"] == "pytest-test-profile/positive/fixture-lifecycle":
        if oracle.get("decision_axis") != "failure-path observation and state-isolation test design":
            raise ValueError("fixture-lifecycle test-design decision axis changed")
        if not any("copying source-owned hidden tests" in item for item in case["required_evidence"]):
            raise ValueError("fixture-lifecycle material attribution requirement missing")
    if not oracle.get("decision_axis") or oracle["decision_axis"].lower() in case["prompt"].lower():
        raise ValueError("promotion decision is dictated")
    visible = case["prompt"] + "\n" + "\n".join(case["subject_files"].values())
    if any(fact.lower() in visible.lower() for fact in spec.hidden_facts):
        raise ValueError("promotion oracle leaks hidden fact")
    if skill_id == "pytest-test-profile" and any(
            marker in visible.lower() for marker in ("pytest-xdist", "xdist", "-n 2", "worker count")):
        if oracle.get("xdist_binding") != {
                "bound": True,
                "source": "runtime-manifest",
                "justification": "worker-shared isolation is the selected substantive concern",
        }:
            raise ValueError("unbound xdist in promotion subject")
    if oracle.get("case_sha256") != case.get("case_sha256"):
        raise ValueError("stale case digest in promotion oracle")
    if case["kind"] == "positive":
        if spec.fixture_kind != "command" and case["relevance_category"] not in {
            "nested-blocks", "links", "code-literals"
        }:
            raise ValueError("positive oracle is not executable or structural")
        if oracle.get("test_ownership") != "fixture-owned" or not spec.good_files or not spec.bad_files:
            raise ValueError("positive fixture ownership is incomplete")
        if skill_id not in TARGETS:
            raise ValueError("case skill identity is outside promotion scope")
    else:
        if spec.fixture_kind != "source_fact" or oracle.get("test_ownership") != "fixture-owned":
            raise ValueError("non-trigger oracle is not source-owned")


def _verify_non_trigger_contract(case, skill_id):
    """Validate the preregistration contract without claiming semantic proof."""
    contract = case.get("non_trigger_contract")
    required = {
        "selection/delivery/acquisition/read traces",
        "actual task result",
        "absence of material target-skill guidance use",
        "reviewer disposition of semantic non-use",
    }
    if not isinstance(contract, dict):
        raise ValueError("non-trigger semantic evidence contract missing")
    spec = promotion_oracles.spec_for(case["case_id"])
    expected_oracle = {
        "owner": "source-owned-later-result-and-independent-review",
        "result_api": "testing.h_eval.promotion_oracles.evaluate_model_output",
        "contract": "requested replacement; preserve other files and content; line endings and trailing whitespace immaterial",
        "required": True,
        "observable_facts": list(spec.hidden_facts),
        "task_result_required": True,
    }
    if (contract.get("target_skill") != skill_id
            or contract.get("neighboring_domain") != case.get("relevance_category")
            or contract.get("external_correctness_oracle") != expected_oracle
            or set(contract.get("required_evidence", ())) != required
            or contract.get("provider_free_claim") != "structure-only"):
        raise ValueError("non-trigger semantic evidence contract changed")


def _verify_review_contract(value):
    review = value.get("independent_review")
    expected = {
        "status": "pending",
        "source_disposition": "pending",
        "provider_free_package_disposition": "pending",
        "overall_inventory_disposition": "pending",
        "per_skill_disposition": {skill: "pending" for skill in _REVIEW_SKILLS},
        "acceptance_owner": "dispatcher_work_review",
        "acceptance_required": True,
    }
    if review != expected:
        raise ValueError("independent review contract changed")


def verify_promotions(root):
    root = Path(root)
    value = load(root / "testing/h_eval/promotion-preregistration.json")
    if (value["schema"] != "apg.h-promotion-preregistration/v1" or value["live_observations"] != 0
            or value["reserve_substitution"] is not False
            or {r["skill_id"] for r in value["skills"]} != TARGETS or len(value["skills"]) != 5):
        raise ValueError("promotion scope changed")
    oracle_source = value.get("oracle_source")
    if (not isinstance(oracle_source, dict)
            or oracle_source.get("path") != promotion_oracles.SOURCE_PATH
            or oracle_source.get("paths") != list(promotion_oracles.SOURCE_PATHS)
            or oracle_source.get("schema") != promotion_oracles.SCHEMA
            or len(oracle_source.get("sha256", "")) != 64):
        raise ValueError("promotion oracle source changed")
    if (root / promotion_oracles.SOURCE_PATH).exists() and (
            promotion_oracles.source_sha256(root) != oracle_source["sha256"]):
        raise ValueError("promotion oracle source drift")
    _verify_review_contract(value)
    expected_inventory = []
    ledger = {r["skill_id"]: r for r in load(root / "docs/governance/skill-maturity-ledger.json")["skills"]}
    for row in value["skills"]:
        raw = (root / row["source_path"]).read_bytes()
        refusal_path = root / f'docs/evaluations/apg166/promotions/{row["skill_id"]}.json'
        refusal = load(refusal_path)
        if (sha(raw) != row["whole_sha256"] or row["body_identity"] != refusal["body_only"]
                or row["prior_refusal_sha256"] != sha(refusal_path.read_bytes())
                or row["maturity_entry"] != ledger[row["skill_id"]]):
            raise ValueError("skill body or maturity authority changed")
        if (row["review_rubric"]["promotion_authorized"] is not False
                or row["review_rubric"]["required_categories"] != ledger[row["skill_id"]]["required_evidence_categories"]):
            raise ValueError("promotion rubric changed")
        if row.get("planning_case_count") != 3:
            raise ValueError("positive planning inventory changed")
        positive = [c for c in row["cases"] if c["kind"] == "positive"]
        negative = [c for c in row["cases"] if c["kind"] == "non-trigger"]
        if len(positive) != 3 or len(negative) != 2 or len({c["case_id"] for c in row["cases"]}) != len(row["cases"]):
            raise ValueError("insufficient preregistered distinct cases")
        if {c["relevance_category"] for c in negative} != _REQUIRED_NON_TRIGGERS[row["skill_id"]]:
            raise ValueError("required neighboring non-triggers missing")
        if row["skill_id"] == "go-language-profile" and {c["relevance_category"] for c in positive} != _REQUIRED_GO_LANGUAGE_CATEGORIES:
            raise ValueError("go-language positive concerns incomplete")
        for case in row["cases"]:
            if not case["case_id"].startswith(row["skill_id"] + "/"):
                raise ValueError("case skill binding changed")
            if case_identity(case) != case["case_sha256"] or not case["required_evidence"] or not case["oracle"]["independent_rubric"]:
                raise ValueError("case identity or rubric changed")
            _verify_case_attribution(case)
            _verify_case_oracle(case, row["skill_id"])
            if case["kind"] == "non-trigger":
                _verify_non_trigger_contract(case, row["skill_id"])
            oracle = case["oracle"]
            expected_inventory.append({
                "case_id": case["case_id"],
                "skill_id": row["skill_id"],
                "kind": case["kind"],
                "oracle_id": oracle.get("oracle_id"),
                "hidden_oracle_sha256": oracle.get("hidden_oracle_sha256"),
                "fixture_kind": oracle.get("fixture_kind"),
                "fixture_contract": oracle.get("fixture_contract"),
                "case_sha256": case["case_sha256"],
            })
            if sha((root / case["route"]["model_source"]).read_bytes()) != case["route"]["model_source_sha256"]:
                raise ValueError("case route changed")
            for name, text in case["subject_files"].items():
                if (Path(name).is_absolute() or any(p in ("", ".", "..") for p in name.split("/"))
                        or "\\" in name or not isinstance(text, str)):
                    raise ValueError("unsafe subject input")
            if any(key in case for key in ("expected_answer", "target_answer", "golden_solution")):
                raise ValueError("answer-leading case")
    try:
        promotion_oracles.validate_registry(expected_inventory)
    except promotion_oracles.PromotionOracleError as exc:
        raise ValueError("promotion oracle inventory changed") from exc
    return value


def verify_bindings(root):
    root = Path(root)
    value = load(root / "testing/h_eval/scenario-bindings.json")
    if value.get("phase") in ("APG166D", "APG166E"):
        from .subjects import verify_manifest
        manifest = root / "testing/fixtures/context-eval/subjects/manifest.json"
        if value.get("subject_manifest") != {"path": "testing/fixtures/context-eval/subjects/manifest.json",
                                              "sha256": sha(manifest.read_bytes())}:
            raise ValueError("subject factory manifest binding changed")
        verify_manifest(corpus_root=root / "testing/fixtures/context-eval")
    corpus = {p.name: p for p in (root / "testing/fixtures/context-eval").glob("scenario-*.json")}
    metrics = root / "testing/fixtures/context-eval/context-eval-metrics-and-oracles.json"
    definitions = load(metrics)
    if sha(metrics.read_bytes()) != value["metrics_sha256"] or len(value["scenarios"]) != 15:
        raise ValueError("frozen corpus/metrics changed")
    expected_ids = {f"scenario-{i:02}" for i in range(1, 16)}
    if {r["scenario_id"] for r in value["scenarios"]} != expected_ids:
        raise ValueError("missing or duplicate scenario")
    for row in value["scenarios"]:
        path = corpus[Path(row["scenario_path"]).name]
        scenario = load(path)
        if (sha(path.read_bytes()) != row["scenario_sha256"] or scenario["scenario_id"] != row["scenario_id"]
                or scenario["expected_outcome"]["quality_oracle"] != row["frozen_oracle"]
                or scenario["task_input"] != row["authority"]):
            raise ValueError("frozen scenario changed")
        routes = row["routes"]
        if set(routes) != {"static", "adaptive"}:
            raise ValueError("missing arm")
        if any(routes[m]["requested_mode"] != m for m in routes):
            raise ValueError("requested mode changed")
        if ({k: v for k, v in routes["static"].items() if k != "requested_mode"}
                != {k: v for k, v in routes["adaptive"].items() if k != "requested_mode"}):
            raise ValueError("asymmetric route")
        if (routes["static"]["provider"] != scenario["provider"]
                or routes["static"]["role_binding"] != scenario.get("role_binding", scenario.get("role_bindings"))):
            raise ValueError("scenario route changed")
        sid = row["scenario_id"]
        cohorts = definitions["cohorts"]
        expected_flags = {"savings": sid in cohorts["savings_eligible_cohort"],
                          "non_synthetic_savings": sid in cohorts["savings_eligible_cohort"] and sid not in ("scenario-08", "scenario-09"),
                          "correctness_only": sid in cohorts["correctness_failure_only_cohort"],
                          "fallback": sid in cohorts["fallback_cohort"],
                          "exact_recovery": sid in ("scenario-10", "scenario-11", "scenario-12", "scenario-14"),
                          "synthetic": sid in ("scenario-08", "scenario-09")}
        if row["cohorts"] != expected_flags or row["contingency"] != ("contingent/unavailable" if sid == "scenario-15" else None):
            raise ValueError("cohort or contingency changed")
        route = routes["static"]
        sources = route["identity_sources"]
        if (len(sources) != len(set(sources)) or set(sources) != set(route["source_sha256"])
                or "common/dispatcher/models.toml" not in sources):
            raise ValueError("route identity source inventory changed")
        models = tomllib.loads((root / "common/dispatcher/models.toml").read_text())
        selected = models["providers"][route["provider"]][route["profile"]]
        if route.get("model") != selected["model"] or route.get("effort") != selected["effort"]:
            raise ValueError("route model or effort changed")
        if route["provider"] == "codex":
            native = tomllib.loads((root / f"codex/profiles/{route['profile']}.config.toml").read_text())
            if (native["model"], native["model_reasoning_effort"]) != (selected["model"], selected["effort"]):
                raise ValueError("native Codex route changed")
        elif route["provider"] == "claude":
            native = load(root / f"claude/profiles/{route['profile']}.json")
            catalog = load(root / "claude/model-catalog-v1.json")
            model = catalog["models"][catalog["roles"][native["modelRole"]]]["id"]
            if (model, native["effort"]) != (selected["model"], selected["effort"]):
                raise ValueError("native Claude route changed")
        for name, digest in route["source_sha256"].items():
            if sha((root / name).read_bytes()) != digest:
                raise ValueError("route source changed")
    return value


def qualify_promotion_oracles(root, runtime_value, fixture_root=None):
    """Run source-owned fixtures with a sealed runtime and durable evidence.

    The one-argument executable mapping remains an explicit diagnostic
    compatibility path for focused tests.  It cannot establish complete
    qualification because it has no sealed manifest transaction or durable
    fixture root.
    """
    value = verify_promotions(root)
    source = value["oracle_source"]
    source_path = Path(root) / source["path"]
    if (not source_path.is_file()
            or promotion_oracles.source_sha256(root) != source["sha256"]):
        raise ValueError("promotion oracle source unavailable or changed")
    inventory = expected_oracle_inventory(value)
    promotion_oracles.validate_registry(inventory)
    starting_subject_cases = []
    for row in value["skills"]:
        for case in row["cases"]:
            if case["kind"] != "positive":
                continue
            starting_subject_cases.append(
                {"case_id": case["case_id"], "subject_files": case["subject_files"]}
            )
    if fixture_root is None:
        executable_paths = promotion_oracles.executable_paths_for_value(runtime_value)
        starting_subjects = [
                promotion_oracles.qualify_starting_subject(
                    entry["case_id"], entry["subject_files"], executable_paths
                )
                for entry in starting_subject_cases
        ]
        result = promotion_oracles.qualify_all_diagnostic(
            executable_paths, expected_inventory=inventory
        )
        result["starting_subjects"] = starting_subjects
        result["starting_subject_count"] = len(starting_subjects)
    else:
        result = promotion_oracles.qualify_all(
            runtime_value, fixture_root, expected_inventory=inventory,
            starting_subject_cases=starting_subject_cases,
        )
    return result


def preflight(root, output):
    """Exclusive-create unavailable records; never instantiate a model/provider."""
    bindings = verify_bindings(root)
    verify_promotions(root)
    output = Path(output)
    if output.parent.resolve() != output.parent:
        raise ValueError("physical preflight parent required")
    output.mkdir(mode=0o700, exist_ok=False)
    for row in bindings["scenarios"]:
        result = {"phase": "APG166C", "scenario_id": row["scenario_id"],
                  "status": "unavailable", "provider_invocations": 0,
                  "subject_materialized": False, "oracle_executed": False,
                  "scenario_sha256": row["scenario_sha256"], "blockers": row["blockers"],
                  "arms": {m: {"status": "unavailable", "route": row["routes"][m]} for m in ("static", "adaptive")}}
        with (output / (row["scenario_id"] + ".json")).open("x") as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write("\n")
    return {"records": 15, "live_results": 0, "complete_execution_package": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(preflight(args.root.resolve(), args.output.absolute()), sort_keys=True))


if __name__ == "__main__":
    main()
