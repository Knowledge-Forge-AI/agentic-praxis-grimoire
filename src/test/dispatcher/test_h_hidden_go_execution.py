"""CORR4 Go TestMain suppression and opaque candidate stdout."""
import json

import pytest

from testing.h_eval import hidden_execution as execution, promotion_oracles as oracle
from test_h_promotion_corr3 import custody, grade

CASE = 'go-test-profile/positive/lifecycle'


@pytest.mark.parametrize('run', [False, True])
def test_testmain_requires_actual_hidden_execution(run):
    files = dict(oracle.spec_for(CASE).good_files)
    files['main_test.go'] = ('package parsing\nimport ("testing"; "os")\n'
        'func TestMain(m *testing.M) { os.Exit(' + ('m.Run()' if run else '0') + ') }\n')
    result = grade(CASE, files)
    hidden = result['hidden_oracle']
    assert hidden['returncode'] == 0
    assert hidden['execution_attestation']['qualifying'] is run
    assert hidden['execution_attestation']['runtime_version'].startswith('go version go')
    assert result['status'] == ('pass' if run else 'fail')
    custody(result, files, ('parse.go',))


def test_printed_json_cannot_forge_go_execution():
    files = dict(oracle.spec_for(CASE).good_files)
    files['main_test.go'] = r'''package parsing
import ("testing"; "os"; "fmt"; "regexp"; "strings"; "encoding/json")
func TestMain(m *testing.M) {
    entries, _ := os.ReadDir(".")
    for _, entry := range entries {
        if !strings.HasPrefix(entry.Name(), "apg_oracle_") { continue }
        raw, _ := os.ReadFile(entry.Name())
        names := regexp.MustCompile(`func (Test\w+)\(`).FindAllStringSubmatch(string(raw), -1)
        for _, name := range names {
            for _, action := range []string{"run", "pass"} {
                event, _ := json.Marshal(map[string]string{"Action":action, "Test":name[1], "Package":"parsing"})
                fmt.Println(string(event))
            }
        }
    }
    os.Exit(0)
}
'''
    result = grade(CASE, files)
    hidden = result['hidden_oracle']
    assert hidden['returncode'] == 0
    assert not hidden['execution_attestation']['qualifying']
    assert hidden['execution_attestation']['observed_statuses'] == {}
    assert all(name in hidden['stdout'] for name in hidden['execution_attestation']['expected_identities'])


def test_go_overlay_names_cannot_collide():
    spec = oracle.spec_for(CASE)
    files = dict(spec.good_files)
    overlay = oracle._hidden_overlay(spec, files)
    for path, text in overlay.items():
        files[path] = text
    fresh = oracle._hidden_overlay(spec, files)
    assert set(fresh).isdisjoint(files)
    result = grade(CASE, files)
    assert result['status'] == 'pass', result
    expected = result['hidden_oracle']['execution_attestation']['expected_identities']
    assert all('TestAPGOracleOracle' in name for name in expected)
    custody(result, files, ('parse.go',))


@pytest.mark.parametrize('events', [
    [{'Action': 'pass', 'Package': 'p'}],
    [{'Action': 'output', 'Package': 'p', 'Output': '{"Action":"run","Test":"TestHidden"}'}],
    [{'Action': a, 'Package': 'p', 'Test': 'TestHidden'} for a in ('run', 'skip')],
    [{'Action': a, 'Package': 'p', 'Test': 'TestHidden'} for a in ('run', 'fail')],
    [{'Action': a, 'Package': 'p', 'Test': 'TestHidden'} for a in ('pass', 'run')],
    [{'Action': a, 'Package': 'p', 'Test': 'TestHidden'} for a in ('run', 'pass', 'run', 'pass')],
    [{'Action': a, 'Package': p, 'Test': 'TestHidden'} for a, p in [('run', 'p'), ('pass', 'other')]],
])
def test_go_nonexecution_ambiguity_and_failure_rejected(events):
    raw = '\n'.join(json.dumps(event) for event in events).encode()
    result = execution.attest('go', ['TestHidden'], raw, 0, ['go', 'test', '-json'], {}, {})
    assert not result['qualifying']


def test_exact_go_run_and_pass_qualify():
    raw = '\n'.join(json.dumps({'Action': a, 'Package': 'p', 'Test': 'TestHidden'})
                    for a in ['run', 'pass']).encode()
    assert execution.attest('go', ['TestHidden'], raw, 0, [], {}, {})['qualifying']
