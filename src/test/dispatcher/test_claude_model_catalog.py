import json

import pytest

from claude_model_catalog import CatalogError, load_catalog, resolve_role
from test_agent_phase_rtk import _REPO_ROOT


@pytest.mark.parametrize('case', ['valid-unused', 'malformed-unused', 'missing-reference'])
def test_catalog_validates_entries_and_references_without_inventory_equality(tmp_path, case):
    data = json.loads((_REPO_ROOT / 'claude/model-catalog-v1.json').read_text())
    data['models']['fixture-unused'] = {'id': 'claude-sonnet-999-1'}
    if case == 'malformed-unused':
        data['models']['fixture-unused']['adaptiveThinking'] = 'not a boolean'
    elif case == 'missing-reference':
        data['roles'][next(iter(data['roles']))] = 'fixture-absent'
    path = tmp_path / 'catalog.json'
    path.write_text(json.dumps(data))
    if case == 'valid-unused':
        catalog = load_catalog(path)
        assert catalog.models['fixture-unused'].id == 'claude-sonnet-999-1'
        for role in data['roles']:
            assert resolve_role(catalog, role)['model_key'] == data['roles'][role]
    else:
        with pytest.raises(CatalogError):
            load_catalog(path)


@pytest.mark.parametrize('version, compatibility, exit_code', [
    ('2.1.249', 'incompatible', 1), ('2.1.250', 'compatible', 0),
])
def test_doctor_matches_effective_parent_and_explicit_fable_models(monkeypatch, version, compatibility, exit_code):
    import claude_model_catalog as catalog
    from claude_vc_profile import resolve_profile

    monkeypatch.setattr(catalog, 'probe_claude_version', lambda executable: (version, 'available'))
    profiles = ['implementation-primary', 'implementation-review', 'normal-final-review',
                'normal-plan-review', 'fable-architecture-docs-primary']
    report, actual_exit = catalog.run_doctor(_REPO_ROOT / 'claude', profiles)
    assert actual_exit == exit_code
    for row in report['profiles']:
        selected = resolve_profile(_REPO_ROOT / 'claude', row['profile'])
        assert row['resolvedModelId'] == selected.resolved_model_id
        assert row['requiredClaudeCodeVersion'] == selected.minimum_version
        if row['profile'] == 'fable-architecture-docs-primary':
            assert row['resolvedModelId'] == 'claude-fable-5-1'
            assert row['requiredClaudeCodeVersion'] == '2.1.250'
            assert row['compatibilityStatus'] == compatibility
        else:
            assert row['resolvedModelId'] == 'claude-opus-5-5'
            assert row['compatibilityStatus'] == 'not-required'
