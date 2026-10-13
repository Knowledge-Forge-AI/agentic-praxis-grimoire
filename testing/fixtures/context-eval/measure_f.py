"""F-CONTEXT1 measurement correction. Explicit binary; no builds or providers.

The fixed envelope is synthetic. Standing/skill bytes are exact current source.
This is a prospective packing fixture, not a live delivery or H benefit study.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def measure(root, binary):
    directory = root / "testing/fixtures/context-eval"
    rows = []
    for source in sorted(directory.glob("scenario-*.json")):
        scenario = json.loads(source.read_bytes())
        number = int(scenario["scenario_id"].split("-")[1])
        if number not in {*range(1, 10), 13, 15}:
            continue
        instruction = scenario["mandatory_instructions"]["provider_file"]
        standing = (root / instruction).read_bytes()
        task = "\n<fixture-task>\n" + json.dumps(scenario["task_input"], sort_keys=True, ensure_ascii=False) + "\n</fixture-task>\n"
        role = "\n<fixture-roles>\n" + json.dumps(scenario["role_binding"], sort_keys=True, ensure_ascii=False) + "\n</fixture-roles>\n"
        canonical = [k for k in scenario.get("f_accounting_correction", {}).get("required_skill_requests", scenario.get("expected_outcome", {}).get("selected_skills", [])) if k.startswith("apgr:")]
        request = {"schema_version": "apg.context-plan/v1", "run_id": "f-fixture", "binding_id": scenario["role_binding"]["binding_id"],
                   "attempt_id": "fixture-attempt-1", "roles": scenario["role_binding"]["roles"], "consumer": "go_library",
                   "requested_mode": "adaptive", "catalog": {"schema_version": "apg.skill-catalog/v1"},
                   "requests": [{"id": k, "required": True} for k in sorted(canonical)],
                   "mandatory": [{"id": "standing", "kind": "standing", "text": standing.decode(), "source_path": instruction, "source_sha256": hashlib.sha256(standing).hexdigest()},
                                 {"id": "task", "kind": "synthetic-fixture-envelope", "text": task},
                                 {"id": "roles", "kind": "synthetic-fixture-envelope", "text": role}],
                   "budget": {"max_initial_context_bytes": scenario.get("budget", {}).get("max_initial_controlled_bytes")},
                   "qualification": {}}
        result = subprocess.run([str(binary), "skills", "plan", "--stdin"], input=json.dumps(request).encode(), capture_output=True, check=True)
        plan = json.loads(result.stdout)
        rows.append({"scenario_id": scenario["scenario_id"], "cohort": scenario["cohort"], "subset": scenario["subset"],
                     "budget": scenario.get("budget"), "standing_source": {"path": instruction, "bytes": len(standing), "sha256": hashlib.sha256(standing).hexdigest()},
                     "mandatory_cost": plan["mandatory_cost"], "payload_cost": plan["payload_cost"],
                     "selected": [{"id": s["qualified_id"], "sha256": hashlib.sha256(__import__('base64').b64decode(s["body"])).hexdigest()} for s in plan["selected_snapshots"]],
                     "decisions": [d for d in plan["decisions"] if d["required"]], "effective_mode": plan["effective_mode"],
                     "reasons": plan["reasons"], "catalog_fingerprint": plan["catalog_fingerprint"],
                     "content_identity": plan["content_identity"], "rule_version": plan["rule_version"]})
    return {"revision": "F-CONTEXT1", "phase": "APG164", "basis": "current exact source; synthetic fixed task/role envelope; no live provider",
            "boundary": "prospective UTF-8 stdin including serialized selected payload; native discovery, argv, provider overhead and tokens not measured here",
            "historical_scenario_03": {"components_bytes": 31544, "limit_bytes": 30000, "adaptive_fit": False},
            "collision_cases": "E-CATALOG1 scenarios 08/09 retained; this canonical accounting view does not replace their synthetic collision tests",
            "rows": rows}


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--root",type=Path,required=True);parser.add_argument("--binary",type=Path,required=True)
    args=parser.parse_args();print(json.dumps(measure(args.root.resolve(),args.binary.resolve()),indent=2,sort_keys=True))
