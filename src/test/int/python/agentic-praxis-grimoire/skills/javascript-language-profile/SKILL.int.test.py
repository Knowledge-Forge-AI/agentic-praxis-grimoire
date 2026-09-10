#!/usr/bin/env python3
"""Exact-engine qualification and provisional-boundary integration for JavaScript."""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "libexec"))
sys.path.insert(0, str(ROOT / "src/test/support"))

import apg_test  # noqa: E402
from apg_javascript_candidate_contract import (  # noqa: E402
    ContractError,
    load_scenario_fixture,
    validate_candidate,
)
from apg_javascript_fixture_contract import (  # noqa: E402
    load_manifest,
    validate_commonjs_seam_invariant,
    validate_commonjs_node_owner,
    validate_fixture_projection,
)


FIXTURE = ROOT / "src/test/fixtures/apg78-javascript-core"
SCENARIOS = ROOT / "src/test/fixtures/apg79-javascript-language-profile-scenarios.json"


def _evaluate(output_contract_id: str, source: str) -> object:
    observation = apg_test.invoke_javascript_engine(
        ROOT,
        ["--input-type=module", "--eval", source],
        cwd=ROOT,
        timeout=20,
        environment={**os.environ, "NO_COLOR": "1"},
        output_contract_id=output_contract_id,
    )
    return observation.result


def _import(output_contract_id: str, path: Path, body: str) -> object:
    return _evaluate(
        output_contract_id,
        f"import * as subject from {json.dumps(path.as_uri())}; {body}",
    )


def test_candidate_manifest_and_independent_projection_are_coherent() -> None:
    scenarios = load_scenario_fixture(SCENARIOS)
    manifest = load_manifest(FIXTURE / "fixture-manifest.json")
    validate_fixture_projection(manifest, scenarios)
    validate_candidate(
        (ROOT / "skills/javascript-language-profile/SKILL.md").read_text(encoding="utf-8"),
        (ROOT / "docs/specs/javascript-language-profile.md").read_text(encoding="utf-8"),
        (ROOT / "docs/specs/javascript-language-profile-scenario-coverage.md").read_text(encoding="utf-8"),
        integrated=True,
    )


def test_script_module_strictness_declarations_tdz_and_closure() -> None:
    script = _evaluate(
        "script-module-strictness",
        "const sloppy=Function('return this!==undefined')();"
        "const strict=Function(\"'use strict'; return this===undefined\")();"
        "console.log(JSON.stringify({sloppy,strict,moduleThis:this===undefined}));"
    )
    assert script == {"sloppy": True, "strict": True, "moduleThis": True}
    sloppy_source = (FIXTURE / "unbound/sloppy-script.js.txt").read_text(encoding="utf-8")
    strict_source = (FIXTURE / "unbound/strict-script.js.txt").read_text(encoding="utf-8")
    scripts = _evaluate(
        "script-goal-strictness",
        "const vm=await import('node:vm');"
        f"const sources={{sloppy:{json.dumps(sloppy_source)},strict:{json.dumps(strict_source)}}};"
        "const run=(source)=>{const context={};try{new vm.Script(source).runInNewContext(context);return {error:null,result:context.result}}catch(error){return {error:error.constructor.name}}};"
        "console.log(JSON.stringify({sloppy:run(sources.sloppy),strict:run(sources.strict)}));"
    )
    assert scripts == {
        "sloppy": {"error": None, "result": 1},
        "strict": {"error": "ReferenceError"},
    }
    result = _import(
        "scope-declarations",
        FIXTURE / "src/scope.mjs",
        "const t=subject.touchBeforeDeclaration(); const h=subject.hoistingBoundary(); const p=subject.perIterationBindings(); console.log(JSON.stringify({tdzError:t.observed.threw,varBefore:h.varBefore,fnBefore:h.fnBefore,perIteration:p}));",
    )
    assert result["tdzError"] == "ReferenceError"
    assert result["varBefore"] == "undefined"
    assert result["fnBefore"] == "function"
    assert result["perIteration"] == {"fromLet": [0, 1, 2], "fromVar": [3, 3, 3]}
    functions = _import(
        "functions-boundaries",
        FIXTURE / "src/functions.mjs",
        "const trace=[]; console.log(JSON.stringify({binding:subject.bindingPair.call({label:'lexical'}), defaults:subject.defaults(trace), spread:subject.restSpreadAndCapture(1,2,3), abrupt:subject.abruptArguments(trace), trace}));",
    )
    assert functions == {
        "binding": {"called": "holder", "arrow": "lexical"},
        "defaults": {"first": 1, "second": 2},
        "spread": {
            "head": 1,
            "tail": [2, 3],
            "widened": [1, 2, 3],
            "called": [1, 2, 3],
            "copied": {"head": 1, "own": "included"},
            "captured": 1,
        },
        "abrupt": "TypeError",
        "trace": ["first", "throw"],
    }


def test_optional_chain_coercion_equality_objects_and_classes() -> None:
    evaluation = _import(
        "optional-chain",
        FIXTURE / "src/evaluation.mjs",
        "const trace=[]; console.log(JSON.stringify({result:subject.shortCircuit(trace,{flag:false,absent:null,nested:null}),trace}));",
    )
    assert evaluation == {
        "result": {
            "conjunction": False,
            "disjunction": "r",
            "coalesced": "r",
            "grouped": "TypeError",
            "optionalCall": 6,
        },
        "trace": ["or-right", "coalesce-right", "optional-argument"],
    }
    objects = _import(
        "objects-classes",
        FIXTURE / "src/objects.mjs",
        "const trace=[]; const d=new subject.Derived(trace); const chain=subject.chain(); const fixed=subject.fixedProperty(); console.log(JSON.stringify({chain:{ownKind:chain.ownKind,ownShared:chain.ownShared,shared:chain.derived.shared},fixed:subject.writeAndDelete(fixed),setter:subject.inheritedSetter(),nonWritable:subject.inheritedNonWritable(),trace,field:d.field,staticTrace:subject.Derived.trace,secret:d.secret,brand:subject.Base.holds(d)}));",
    )
    assert objects["chain"] == {"ownKind": True, "ownShared": False, "shared": "from-base"}
    assert objects["fixed"] == {
        "assign": {"threw": "TypeError"},
        "remove": {"threw": "TypeError"},
        "value": "original",
    }
    assert objects["setter"] == {"observed": 7, "ownsValue": False}
    assert objects["nonWritable"] == {"threw": "TypeError", "value": "base", "owns": False}
    assert objects["trace"] == ["base-constructor", "derived-field", "derived-after-super"]
    assert objects["field"] == "derived-field"
    assert objects["staticTrace"] == ["static-field", "static-block"]
    assert objects["secret"] == "derived-private"
    assert objects["brand"] is True
    equality = _evaluate(
        "equality",
        "console.log(JSON.stringify({nanStrict:NaN===NaN,nanSame:Object.is(NaN,NaN),zeroSame:Object.is(0,-0),set:[...new Set([NaN,NaN,0,-0])].length,bigintError:(()=>{try{return 1n+1}catch(e){return e.constructor.name}})()}));"
    )
    assert equality == {
        "nanStrict": False,
        "nanSame": True,
        "zeroSame": False,
        "set": 2,
        "bigintError": "TypeError",
    }
    coercion = _import(
        "coercion",
        FIXTURE / "src/coercion.mjs",
        "const trace=[]; const value=subject.convertible(trace); const result=subject.conversions(value); console.log(JSON.stringify({trace,result}));",
    )
    assert coercion["trace"] == ["number", "string", "default"]
    assert coercion["result"] == {"number": 42, "string": "forty-two", "loose": True}


def test_iterator_close_and_finally_completion_boundaries() -> None:
    result = _import(
        "iterator-close",
        FIXTURE / "src/iteration.mjs",
        "const a=[]; subject.continueThenBreak(subject.observableIterator(a,3)); const b=[]; const body=subject.throwingBody(subject.returnVariant(b,'throwing')); const missingTrace=[]; const missing=subject.partialDestructure(subject.returnVariant(missingTrace,'missing')); let noncall; try{subject.partialDestructure(subject.returnVariant([], 'non-callable'))}catch(e){noncall=e.constructor.name}; let nonobject; try{subject.partialDestructure(subject.returnVariant([], 'non-object'))}catch(e){nonobject=e.constructor.name}; console.log(JSON.stringify({a,b,body,missingTrace,missing,noncall,nonobject}));",
    )
    assert result["a"] == ["next:1", "next:2", "return"]
    assert result["b"] == ["next:1"]
    assert result["body"] == "TypeError:body"
    assert result["noncall"] == "TypeError"
    assert result["missing"] == {"first": 1, "second": 2}
    assert result["missingTrace"] == ["next:1", "next:2"]
    assert result["nonobject"] == "TypeError"
    errors = _import(
        "finally-completion",
        FIXTURE / "src/errors.mjs",
        "let normal; const trace=[]; try{subject.finallyPreservesThrow(trace)}catch(e){normal={name:e.constructor.name,message:e.message,trace}}; console.log(JSON.stringify({throwing:subject.finallyReplacesThrow(), returning:subject.finallyOverridesReturn(), normal}));",
    )
    assert errors["throwing"] == "from-finally"
    assert errors["returning"] == "from-finally"
    assert errors["normal"] == {
        "name": "TypeError",
        "message": "preserved",
        "trace": ["finally"],
    }


def test_promise_module_dynamic_import_and_host_stops() -> None:
    async_result = _import(
        "promise-async",
        FIXTURE / "src/async.mjs",
        "const promiseTrace=[]; const pending=subject.reactionOrder(promiseTrace); promiseTrace.push('after-call'); await pending; await Promise.resolve(); const awaitTrace=[]; await subject.awaitBoundary(awaitTrace); const rejected=await subject.catchPropagation(); console.log(JSON.stringify({promiseTrace,awaitTrace,rejected}));",
    )
    assert async_result["promiseTrace"] == ["synchronous", "after-call", "then-1", "then-2"]
    assert async_result["awaitTrace"] == ["before-await", "after-await"]
    assert async_result["rejected"] == {"caught": "async-origin"}
    modules = _import(
        "module-live-bindings",
        FIXTURE / "src/modules/consumer.mjs",
        "const live=subject.observeLiveBinding(); const namespace=subject.observeNamespace(); const write=subject.attemptNamespaceWrite(); console.log(JSON.stringify({live,namespace,write}));",
    )
    assert modules["live"] == {"before": 0, "after": 1}
    assert modules["namespace"] == {
        "label": "counter",
        "count": 1,
        "keys": ["count", "increment", "label"],
        "tag": "[object Module]",
    }
    assert modules["write"] == {"threw": "TypeError"}
    cycle = _evaluate(
        "module-cycle",
        f"try{{await import({json.dumps((FIXTURE / 'src/modules/cycle-a.mjs').as_uri())}); console.log(JSON.stringify('unexpected'))}}catch(e){{console.log(JSON.stringify(e.constructor.name))}}"
    )
    assert cycle == "ReferenceError"
    top_level_await = _import(
        "top-level-await",
        FIXTURE / "src/modules/top-level-await.mjs",
        "console.log(JSON.stringify(subject.value));",
    )
    assert top_level_await == 1
    dynamic_failure = _import(
        "dynamic-import-failure",
        FIXTURE / "src/dynamic-import-boundary.mjs",
        "let result; try{await subject.load('./absent.mjs'); result='unexpected'}catch(e){result=e.constructor.name}; console.log(JSON.stringify(result));",
    )
    assert dynamic_failure == "Error"
    boundary = _import(
        "module-strictness",
        FIXTURE / "src/module-boundary.mjs",
        "console.log(JSON.stringify({topLevelThisIsUndefined:subject.topLevelThis===undefined,strict:subject.strictnessIsIntrinsic()}));",
    )
    assert boundary == {
        "topLevelThisIsUndefined": True,
        "strict": {"threw": "ReferenceError"},
    }
    selected = _import(
        "module-goal-evidence",
        FIXTURE / "src/mode-selected.js",
        "console.log(JSON.stringify(subject.goalEvidence));",
    )
    assert selected == 'nearest package.json "type" field'


def test_checked_javascript_effect_free_core_and_commonjs_boundary() -> None:
    checked = _import(
        "checked-javascript",
        FIXTURE / "src/checked.js",
        "console.log(JSON.stringify(subject.summarize([1,2,3])));",
    )
    assert checked == {"total": 6, "count": 3}
    core = _import(
        "cli-core",
        FIXTURE / "src/cli-core.mjs",
        "const input=['--verbose','2','3']; const env={VERBOSE:'0'}; const first=subject.run(input,env); const second=subject.run(input,env); console.log(JSON.stringify({first,stable:JSON.stringify(first)===JSON.stringify(second)}));",
    )
    assert core == {
        "first": {
            "total": 5,
            "operandCount": 2,
            "verbose": True,
            "messages": ["operands:2"],
            "status": "computed",
        },
        "stable": True,
    }
    observations = {}
    for commonjs, output_contract_id in (
        (FIXTURE / "src/commonjs-boundary.cjs", "commonjs-boundary-syntax"),
        (FIXTURE / "src/cli-node-adapter-boundary.cjs", "cli-commonjs-adapter-syntax"),
    ):
        observation = apg_test.invoke_javascript_engine(
            ROOT,
            ["--check", str(commonjs)],
            cwd=ROOT,
            timeout=20,
            output_contract_id=output_contract_id,
        )
        assert observation.return_code == 0
        assert observation.stdout_empty
        assert observation.stderr_empty
        observations[output_contract_id] = observation
    manifest = load_manifest(FIXTURE / "fixture-manifest.json")
    scenarios = load_scenario_fixture(SCENARIOS)
    validate_commonjs_seam_invariant(manifest, scenarios, observations)
    from apg_nodejs_candidate_contract import load_scenarios, validate_candidate as validate_node
    validate_commonjs_node_owner(load_scenarios(
        ROOT / "src/test/fixtures/apg81-nodejs-runtime-profile-scenarios.json"
    ))
    validate_node(
        (ROOT / "skills/nodejs-runtime-profile/SKILL.md").read_text(),
        (ROOT / "docs/specs/nodejs-runtime-profile.md").read_text(),
        (ROOT / "docs/specs/nodejs-runtime-profile-scenario-coverage.md").read_text(),
    )

    # Node availability does not satisfy missing CommonJS artifact facts
    mutated_manifest = deepcopy(manifest)
    mutated_manifest["cases"][10]["required_evidence"] = []
    with pytest.raises(ContractError, match="required_evidence mismatch"):
        validate_commonjs_seam_invariant(mutated_manifest, scenarios, observations)


def test_closed_output_contract_rejects_each_observable_violation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = "APG79D-NONSECRET-OUTPUT-SENTINEL"

    def reject(
        contract_id: str,
        return_code: int,
        stdout: str,
        stderr: str,
    ) -> None:
        with pytest.raises(apg_test.JavascriptQualificationError) as captured:
            apg_test._validate_javascript_output(
                contract_id,
                return_code,
                stdout,
                stderr,
            )
        assert sentinel not in str(captured.value)
        assert contract_id in str(captured.value)

    reject("absent-contract", 0, sentinel, sentinel)
    reject("top-level-await", 7, "1", "")
    reject("top-level-await", 0, "1", sentinel)
    reject("commonjs-boundary-syntax", 0, sentinel, "")
    reject("top-level-await", 0, sentinel, "")
    reject("top-level-await", 0, json.dumps("1"), "")
    reject(
        "script-module-strictness",
        0,
        json.dumps({"sloppy": True, "strict": True}),
        "",
    )

    promise = deepcopy(
        apg_test.JAVASCRIPT_OUTPUT_CONTRACTS["promise-async"].expected_result
    )
    promise["promiseTrace"].pop()
    reject("promise-async", 0, json.dumps(promise), "")
    reject("top-level-await", 0, "2", "")
    reject("top-level-await", 0, '{"value":1,"value":1}', "")
    monkeypatch.setitem(
        apg_test.JAVASCRIPT_OUTPUT_CONTRACTS,
        "invalid-policy",
        apg_test.JavascriptOutputContract(0, "invalid", "empty"),
    )
    reject("invalid-policy", 0, "", "")


def test_engine_binding_rejects_missing_relative_and_symlink_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    exact_engine = os.environ["APG_JAVASCRIPT_NODE"]
    monkeypatch.delenv("APG_JAVASCRIPT_NODE")
    with pytest.raises(apg_test.ToolError, match="test prerequisite is unavailable"):
        apg_test.validate_javascript_engine(ROOT)

    monkeypatch.setenv("APG_JAVASCRIPT_NODE", "relative-node")
    with pytest.raises(apg_test.ToolError, match="absolute regular executable"):
        apg_test.validate_javascript_engine(ROOT)

    linked = tmp_path / "linked-node"
    linked.symlink_to(exact_engine)
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(linked))
    with pytest.raises(apg_test.ToolError, match="absolute regular executable"):
        apg_test.validate_javascript_engine(ROOT)

    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(ROOT / "bin/apg-test"))
    with pytest.raises(apg_test.ToolError, match="outside the repository"):
        apg_test.validate_javascript_engine(ROOT)

    local_engine = tmp_path / "local-node"
    local_engine.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    local_engine.chmod(0o755)
    monkeypatch.setenv("APG_JAVASCRIPT_NODE", str(local_engine))
    with pytest.raises(apg_test.ToolError, match="approved immutable Nix-store"):
        apg_test.validate_javascript_engine(ROOT)

    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(Path(exact_engine).parent, target_is_directory=True)
    monkeypatch.setenv(
        "APG_JAVASCRIPT_NODE",
        str(linked_parent / Path(exact_engine).name),
    )
    with pytest.raises(apg_test.ToolError, match="symlinked path components"):
        apg_test.validate_javascript_engine(ROOT)


def test_target_metadata_remains_static_and_nonexecuted() -> None:
    rows = load_scenario_fixture(SCENARIOS)["rows"][-3:]
    assert [row["id"] for row in rows] == [
        "APG79-TARGET-001", "APG79-TARGET-002", "APG79-TARGET-003"
    ]
    assert rows[0]["response"] == "stop-and-escalate"
    assert rows[0]["whole_file_owner"] == "project-configuration-owner"
    assert rows[0]["javascript_selection"] == "selected"
    assert all(row["response"] == "stop-and-escalate" for row in rows[1:])
    assert all("execution" in row["nonowned_conclusion_note"] for row in rows[1:])


def test_module_cycle_root_scalar_contract_rejects_same_type_wrong_value() -> None:
    """QD004: module-cycle root scalar contract positive observation and same-type wrong value rejection."""
    # Retained positive observation bound to cycle-a.mjs / cycle-b.mjs source
    positive = _evaluate(
        "module-cycle",
        f"try{{await import({json.dumps((FIXTURE / 'src/modules/cycle-a.mjs').as_uri())}); console.log(JSON.stringify('unexpected'))}}catch(e){{console.log(JSON.stringify(e.constructor.name))}}",
    )
    assert positive == "ReferenceError"
    assert isinstance(positive, str)
    assert apg_test.JAVASCRIPT_OUTPUT_CONTRACTS["module-cycle"].expected_result == "ReferenceError"

    # Same-type wrong value rejection: ReferenceError -> TypeError (root only, str -> str)
    with pytest.raises(apg_test.JavascriptQualificationError) as captured:
        apg_test._validate_javascript_output("module-cycle", 0, json.dumps("TypeError"), "")
    assert "result value mismatch at result" in str(captured.value)
    assert "module-cycle" in str(captured.value)


def test_top_level_await_root_scalar_contract_rejects_same_type_wrong_value() -> None:
    """QD004: top-level-await root scalar contract positive observation, wrong2 rejection, and partial supersession proof."""
    # Retained positive observation bound to top-level-await.mjs source
    positive = _import(
        "top-level-await",
        FIXTURE / "src/modules/top-level-await.mjs",
        "console.log(JSON.stringify(subject.value));",
    )
    assert positive == 1
    assert isinstance(positive, int)
    assert apg_test.JAVASCRIPT_OUTPUT_CONTRACTS["top-level-await"].expected_result == 1

    # Same-type wrong value rejection: integer 1 -> 2 (root only, int -> int)
    # Proves partial supersession: wrong value 2 was historically rejected in bulk test,
    # and this dedicated root test isolates value-mismatch qualification without asserting an invalid validator.
    with pytest.raises(apg_test.JavascriptQualificationError) as captured:
        apg_test._validate_javascript_output("top-level-await", 0, json.dumps(2), "")
    assert "result value mismatch at result" in str(captured.value)
    assert "top-level-await" in str(captured.value)


def test_dynamic_import_failure_root_scalar_contract_rejects_same_type_wrong_value() -> None:
    """QD004: dynamic-import-failure root scalar contract positive observation and same-type wrong value rejection."""
    # Retained positive observation bound to dynamic-import-boundary.mjs source
    positive = _import(
        "dynamic-import-failure",
        FIXTURE / "src/dynamic-import-boundary.mjs",
        "let result; try{await subject.load('./absent.mjs'); result='unexpected'}catch(e){result=e.constructor.name}; console.log(JSON.stringify(result));",
    )
    assert positive == "Error"
    assert isinstance(positive, str)
    assert apg_test.JAVASCRIPT_OUTPUT_CONTRACTS["dynamic-import-failure"].expected_result == "Error"

    # Same-type wrong value rejection: Error -> TypeError (root only, str -> str)
    with pytest.raises(apg_test.JavascriptQualificationError) as captured:
        apg_test._validate_javascript_output("dynamic-import-failure", 0, json.dumps("TypeError"), "")
    assert "result value mismatch at result" in str(captured.value)
    assert "dynamic-import-failure" in str(captured.value)


def test_module_goal_evidence_root_scalar_contract_rejects_same_type_wrong_value() -> None:
    """QD004: module-goal-evidence root scalar contract positive observation and same-type wrong value rejection."""
    # Retained positive observation bound to mode-selected.js source
    positive = _import(
        "module-goal-evidence",
        FIXTURE / "src/mode-selected.js",
        "console.log(JSON.stringify(subject.goalEvidence));",
    )
    expected = 'nearest package.json "type" field'
    assert positive == expected
    assert isinstance(positive, str)
    assert apg_test.JAVASCRIPT_OUTPUT_CONTRACTS["module-goal-evidence"].expected_result == expected

    # Same-type wrong value rejection: 'nearest package.json "type" field' -> 'file extension alone' (root only, str -> str)
    with pytest.raises(apg_test.JavascriptQualificationError) as captured:
        apg_test._validate_javascript_output("module-goal-evidence", 0, json.dumps("file extension alone"), "")
    assert "result value mismatch at result" in str(captured.value)
    assert "module-goal-evidence" in str(captured.value)


def test_root_scalar_contracts_detect_lost_scalar_enforcement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each named negative must fail if root equality enforcement is removed."""
    original = apg_test._check_exact_json
    def omit_root_equality(actual, expected, context):
        if context == "result" and type(actual) is type(expected) and not isinstance(expected, (dict, list)):
            return None
        return original(actual, expected, context)
    monkeypatch.setattr(apg_test, "_check_exact_json", omit_root_equality)
    for control in (
        test_module_cycle_root_scalar_contract_rejects_same_type_wrong_value,
        test_top_level_await_root_scalar_contract_rejects_same_type_wrong_value,
        test_dynamic_import_failure_root_scalar_contract_rejects_same_type_wrong_value,
        test_module_goal_evidence_root_scalar_contract_rejects_same_type_wrong_value,
    ):
        with pytest.raises(pytest.fail.Exception, match="DID NOT RAISE"):
            control()


@pytest.mark.parametrize("source,reason", (
    ("process.stdout.write(Buffer.from('4150473132382d5245414c2d53545245414d','hex'));process.exitCode=2", "unexpected status"),
    ("process.stderr.write(Buffer.from('4150473132382d5245414c2d53545245414d','hex'))", "unexpected stderr"),
    ("process.stdout.write(Buffer.from('4150473132382d5245414c2d53545245414d','hex'))", "invalid structured output"),
    ("console.log(JSON.stringify({raw:Buffer.from('4150473132382d5245414c2d53545245414d','hex').toString()}))", "type mismatch"),
    ("process.stdout.write(Buffer.concat([Buffer.from('4150473132382d5245414c2d53545245414d','hex'),Buffer.from([255])]))", "UnicodeError"),
    ("process.stdout.write('['.repeat(4000)+JSON.stringify(Buffer.from('4150473132382d5245414c2d53545245414d','hex').toString())+']'.repeat(4000))", "invalid structured output|type mismatch"),
    ("process.stdout.write(Buffer.from('4150473132382d5245414c2d53545245414d','hex'));setInterval(()=>{},1000)", "TimeoutExpired"),
))
def test_real_engine_stream_failure_custody(source: str, reason: str) -> None:
    with pytest.raises(apg_test.JavascriptQualificationError, match=reason) as caught:
        apg_test.invoke_javascript_engine(ROOT, ["--input-type=module", "--eval", source],
                                        cwd=ROOT, timeout=1, output_contract_id="top-level-await")
    _assert_real_engine_failure_clean(caught.value)


def _assert_real_engine_failure_clean(error: BaseException) -> None:
    import traceback
    needle = bytes.fromhex("4150473132382d5245414c2d53545245414d").decode()
    assert needle not in str(error) and needle not in repr(error)
    assert error.__cause__ is None and error.__context__ is None
    rendered = "".join(traceback.TracebackException.from_exception(error, capture_locals=True).format())
    assert needle not in rendered
