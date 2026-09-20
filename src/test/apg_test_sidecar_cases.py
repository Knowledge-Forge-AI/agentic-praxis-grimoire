"""Bounded unit seams for core/dispatcher coverage report governance."""

import pytest


def _inventory(apg_test, tmp_path):
    core = "libexec/tool.py"
    sidecars = ("libexec/agent_phase/first.py", "libexec/agent_phase/second.py")
    files = {
        f"{apg_test.UNIT_ROOT.as_posix()}/libexec/tool.unit.test.py": (core, "unit"),
        f"{apg_test.UNIT_ROOT.as_posix()}/.github/hidden.unit.test.py": (".github/hidden", "unit"),
        f"{apg_test.INTEGRATION_ROOT.as_posix()}/libexec/tool.int.test.py": (core, "integration"),
    }
    for relative in (core, *sidecars, ".github/hidden", *files):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "bin").mkdir()
    return apg_test.Inventory(
        {core: ("unit", "integration", "combined")}, {}, files,
        {path: "governed dispatcher source" for path in sidecars},
    )


def _reports(inventory, variant):
    core, = inventory.coverage_sources
    sidecars = tuple(inventory.dispatcher_sources)
    core_measurement = {"summary": {
        "covered_lines": 9, "num_statements": 10,
        "covered_branches": 9, "num_branches": 10,
    }}
    sidecar_measurement = {"summary": {
        "covered_lines": 0, "num_statements": 1000,
        "covered_branches": 0, "num_branches": 1000,
    }}
    count = {"core-only": 0, "subset": 1}.get(variant, 2)
    report = {"files": {core: core_measurement, **{
        path: sidecar_measurement for path in sidecars[:count]
    }}}
    union = {"files": dict(report["files"])}
    if variant == "missing-core":
        del union["files"][core]
    elif variant == "foreign":
        union["files"]["libexec/undeclared.py"] = sidecar_measurement
    elif variant == "below-gate":
        union["files"][core] = {"summary": {
            "covered_lines": 8, "num_statements": 10,
            "covered_branches": 8, "num_branches": 10,
        }}
        # Fully covered dispatcher measurements cannot rescue an 80% core union.
        union["files"][sidecars[0]] = {"summary": {
            "covered_lines": 1000, "num_statements": 1000,
            "covered_branches": 1000, "num_branches": 1000,
        }}
    return report, union


def assert_combined_sidecar_contract(apg_test, tmp_path, monkeypatch, capsys, variant):
    """Replace test execution only; run actual census, counts and integer gates."""
    inventory = _inventory(apg_test, tmp_path)
    report, union = _reports(inventory, variant)
    monkeypatch.setattr(apg_test, "load_inventory", lambda _root: inventory)
    monkeypatch.setattr(apg_test, "dependency_versions", lambda: {})
    calls = []

    def execute(_root, suite, workers, artifacts, **kwargs):
        calls.append((suite, workers))
        assert kwargs["selected_files"] == tuple(sorted(
            path for path, (_owner, selected) in inventory.tests.items() if selected == suite
        ))
        return artifacts / f"{suite}.coverage", report

    def combine(_root, data_files, output):
        assert [path.name for path in data_files] == ["unit.coverage", "integration.coverage"]
        assert output.name == "combined.coverage"
        return union

    monkeypatch.setattr(apg_test, "_run_pytest", execute)
    monkeypatch.setattr(apg_test, "_combine_coverage", combine)
    diagnostic = {
        "missing-core": "combined:.*missing=.*tool.py",
        "foreign": "combined:.*foreign=.*undeclared.py",
        "below-gate": "combined: statement coverage gate failed: 8/10 < 85%",
    }.get(variant)
    if diagnostic:
        with pytest.raises(apg_test.ToolError, match=diagnostic):
            apg_test.run("combined", 8, tmp_path)
    else:
        apg_test.run("combined", 8, tmp_path)
    assert calls == [("unit", 8), ("integration", 8)]
    output = capsys.readouterr().out
    assert "PASS unit: statements 9/10; branches 9/10" in output
    assert "PASS integration: statements 9/10; branches 9/10" in output
    if diagnostic:
        assert "PASS combined union" not in output
    else:
        assert "PASS combined union: statements 9/10; branches 9/10" in output
    with pytest.raises(apg_test.ToolError, match="workers"):
        apg_test.run("unit", 0, tmp_path)
