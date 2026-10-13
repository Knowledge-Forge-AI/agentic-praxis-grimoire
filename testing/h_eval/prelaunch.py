"""Non-consuming prelaunch check of the H arm settings/discovery observation.

A live arm consumes its unit before context preparation, then observes the
manifest-bound operator settings and the provider's global skill root.  That
root is not a runtime-manifest input, so a manifest check cannot predict an
observation refusal.  This module runs the arm's own observation owner for
every provider routed by the requested scenario units and reports whether it
would open.

It reads only the sealed runtime manifest, the frozen routes of the source
tree, the manifest-bound settings files and the provider global discovery
roots.  An existing root receives the arm's bounded content inventory.  An
absent root is observed as absent: only the named root and the identity
metadata of its lexical path components are examined, so no ancestor such as
HOME or a vendor store is listed or hashed and no opt-in is needed.  A missing
parent (``missing_parent``) is reported because its later appearance would
refuse the arm after its provider start.  It never reads decision, grant or
custody records, never touches a ledger, never creates an arm, run or skill
directory, never probes a version or spawns a process, and applies no
promotion-only absence rule.

``ready`` is necessary, not sufficient: it is not admission and does not
authorize, consume or replay any unit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

from . import execution, live_admission, runtime_manifest

SCHEMA = "apg.h-prelaunch-observation-check/v2"
MAX_REPORTED_LINKS = 20
_NOTE = "ready is necessary, not sufficient; this check is not admission and consumes nothing"
_ERRORS = (OSError, TypeError, ValueError, KeyError)


class UsageError(ValueError):
    """A request outside the preregistered scenario inventory."""


def units_for(scenario_ids: Iterable[str]) -> list[str]:
    """Return the scenario units named by ``scenario_ids`` in frozen order."""
    requested = list(scenario_ids)
    known = (*live_admission.CALIBRATION, *live_admission.ACCEPTANCE)
    if not requested or len(set(requested)) != len(requested):
        raise UsageError("scenario list must be non-empty and unique")
    unknown = [sid for sid in requested if sid not in known]
    if unknown:
        raise UsageError("scenario is not a preregistered live scenario")
    return [live_admission.scenario_unit(sid, mode)
            for sid in known if sid in requested for mode in live_admission.MODES]


def providers_for(source_root: Path, scenario_ids: Iterable[str]) -> list[str]:
    """Derive the provider set from the frozen routes of both modes."""
    providers = set()
    for scenario_id in scenario_ids:
        for mode in live_admission.MODES:
            _scenario, _row, route, _source = execution._frozen_inputs(source_root, scenario_id, mode)
            providers.add(route["provider"])
    return sorted(providers)


def _unresolved(entries: Sequence[Mapping[str, Any]], prefix: str = "") -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for entry in entries:
        relative = f"{prefix}{entry.get('relative_path')}"
        if entry.get("target_kind") == "unresolved":
            found.append({"relative_path": relative, "errno": str(entry.get("unresolved_errno"))})
        nested = entry.get("target_identity")
        if isinstance(nested, Mapping):
            found.extend(_unresolved(nested.get("entries", []), f"{relative}/"))
    return found


def _identity_view(state: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "settings_before": state["settings_before"],
        "global_candidate": str(state["global_candidate"]),
        "global_scope": state["global_scope"],
        "global_absent": list(state["global_absent"]),
        "global_path": str(state["global_path"]),
        "global_before": state["global_before"],
    }


def _provider_check(manifest: Mapping[str, Any], provider_name: str) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "status": "refused", "global_candidate": None, "global_path": None, "global_scope": None,
        "absent": None, "missing_parent": None, "settings_inputs": None,
        "unresolved_link_count": None, "unresolved_links": None, "identity_sha256": None,
        "failure_detail": None,
    }
    step = "discovery_root"
    try:
        # Classify the named root first.  An absent root is never replaced by
        # an ancestor; only its lexical path components are examined.
        candidate = execution._global_discovery_candidate(manifest, provider_name)
        state, absence = execution._discovery_root_state(candidate)
        present = state == "present"
        missing = [] if present else list(absence["missing"])
        entry.update(global_candidate=str(candidate), global_path=str(candidate),
                     global_scope="existing-root" if present else "absent-root",
                     absent=len(missing), missing_parent=len(missing) > 1)
        step = "settings_observation"
        settings_paths = execution._operator_settings_paths(manifest)
        settings = [execution._observation_identity(path) for path in settings_paths]
        entry["settings_inputs"] = len(settings)
        step = "global_observation"
        if present:
            walk = runtime_manifest._input(candidate, unresolved_links=True)
            unresolved = _unresolved(walk.get("entries", []))
            entry["unresolved_link_count"] = len(unresolved)
            entry["unresolved_links"] = unresolved[:MAX_REPORTED_LINKS]
            expected = walk["sha256"]
        else:
            expected = absence["sha256"]
        step = "operator_observation"
        first = _identity_view(execution._operator_observation(manifest, provider_name=provider_name))
        step = "stability"
        second = _identity_view(execution._operator_observation(manifest, provider_name=provider_name))
        if (first != second or first["settings_before"] != settings
                or first["global_scope"] != entry["global_scope"]
                or first["global_before"]["sha256"] != expected):
            raise ValueError("prelaunch observation is not stable")
        entry["identity_sha256"] = hashlib.sha256(runtime_manifest._canonical(first)).hexdigest()
        entry["status"] = "ready"
    except _ERRORS as error:
        entry["failure_detail"] = execution._failure_detail(error, step)
    return entry


def check_observation(
    runtime_inputs: Mapping[str, Any],
    *,
    source_root: str | Path,
    scenario_ids: Iterable[str] = live_admission.CALIBRATION,
) -> dict[str, Any]:
    """Run the arm observation owner for each routed provider; consume nothing.

    An absent provider root is reported with ``global_scope: absent-root`` and
    observed without any ancestor walk.
    """
    source_root = Path(source_root)
    scenario_ids = list(scenario_ids)
    report: dict[str, Any] = {
        "schema": SCHEMA, "status": "refused", "admission": False, "note": _NOTE,
        "units": units_for(scenario_ids), "providers": {}, "failure_detail": None,
    }
    try:
        manifest = runtime_manifest.verify_complete(runtime_inputs, probe_versions=False)
        if manifest["lifecycle"]["state"] != "sealed":
            raise ValueError("prelaunch check requires a sealed runtime manifest")
    except _ERRORS as error:
        report["failure_detail"] = execution._failure_detail(error, "runtime_manifest")
        return report
    try:
        providers = providers_for(source_root, scenario_ids)
    except _ERRORS as error:
        report["failure_detail"] = execution._failure_detail(error, "frozen_routes")
        return report
    report["providers"] = {
        name: _provider_check(manifest, name)
        for name in providers
    }
    if all(value["status"] == "ready" for value in report["providers"].values()):
        report["status"] = "ready"
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: exit 0 when ready, 1 when refused, 2 on a usage or input error."""
    parser = argparse.ArgumentParser(
        prog="python -m testing.h_eval.prelaunch",
        description="Non-consuming check of the H arm settings/discovery observation.",
    )
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--runtime-inputs", required=True)
    parser.add_argument("--scenario", action="append", dest="scenarios",
                        help="repeatable; defaults to the calibration scenarios")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_:
        return 2 if exit_.code not in (0, None) else 0
    try:
        runtime_inputs = json.loads(Path(args.runtime_inputs).read_text(encoding="utf-8"))
        report = check_observation(
            runtime_inputs,
            source_root=Path(args.source_root).resolve(),
            scenario_ids=args.scenarios or live_admission.CALIBRATION,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, UsageError) as error:
        print(f"prelaunch: {type(error).__name__}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
