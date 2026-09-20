"""Portable managed roster documentation remains synchronized and link-complete."""
from pathlib import Path
import importlib.util
import re

ROOT = Path(__file__).resolve().parents[3]


def test_managed_directions_are_current_and_portable():
    spec = importlib.util.spec_from_file_location(
        "roster_directions", ROOT / "tools/add_dispatcher_roster_operator_directions.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.apply(ROOT, check=True) == []
    for body, parent in [(module.ROOT_BODY, ROOT),
                         (module.DISPATCHER_BODY, ROOT / "common/dispatcher")]:
        for target in re.findall(r"\]\(([^)]+)\)", body):
            assert (parent / target.split("#", 1)[0]).is_file(), target
        assert "dispatcher-operator-guide.md" not in body
        assert "guarded_active_checkout_update" not in body
        assert "not mandatory" in body or "Neither" in body
