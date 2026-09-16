"""Canonical machine and human result artifacts for a dispatcher run."""

from __future__ import annotations

import copy
import json
import re
import stat
from pathlib import Path
from typing import Any

from .lifecycle import get_lifecycle
from .stage_delta import MAX_STAGE_INLINE_DELTAS


RESULT_SCHEMA = "agent-phase-result-v4"
STAGE_ACCOUNTING_SCHEMA = "agent-phase-stage-accounting-v2"

_SAFE_ARTIFACT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_STORY_PATH_LIMIT = 10
_STORY_AUTHORITY_LIMIT = 10
_STORY_REASON_LIMIT = 20


def _count(value: Any, default: int = 0) -> int:
    """Inherited evidence may be incomplete or hand-repaired; never coerce it."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else default


def _mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _record_artifact_issue(
    issues: list[dict[str, str]], label: str, reason: str
) -> None:
    """Keep pointer-validation failures bounded and free of private values."""
    if any(
        item.get("pointer") == label and item.get("reason") == reason
        for item in issues
    ):
        return
    issues.append({"pointer": label, "reason": reason})


def _safe_artifact_name(value: Any) -> bool:
    """Accept only one run-relative, ASCII artifact name component."""
    return isinstance(value, str) and _SAFE_ARTIFACT_NAME.fullmatch(value) is not None


def _artifact_exists(directory: Any, name: str) -> bool:
    """Require a regular, non-symlink file directly in the run directory."""
    try:
        root = Path(directory.path).resolve()
        target = root / name
        info = target.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
            return False
        return target.resolve(strict=False).parent == root
    except (AttributeError, OSError, RuntimeError, ValueError):
        return False


def _validated_artifact_name(
    directory: Any,
    value: Any,
    *,
    label: str,
    issues: list[dict[str, str]],
) -> str | None:
    """Return a finalizable artifact pointer only when it is safe and present."""
    if not _safe_artifact_name(value):
        _record_artifact_issue(issues, label, "unsafe_name")
        return None
    if not _artifact_exists(directory, value):
        _record_artifact_issue(issues, label, "missing_or_unusable")
        return None
    return value


def _add_artifact_reference(
    references: dict[str, Any],
    group: str,
    name: str | None,
    **fields: Any,
) -> None:
    """Add a validated pointer to the human and machine handoff."""
    if name is None:
        return
    record = {"name": name, **fields}
    current = references.get(group)
    if isinstance(current, list):
        if not any(
            isinstance(item, dict) and item.get("name") == name for item in current
        ):
            current.append(record)
    else:
        references[group] = record


def _validated_binding(
    directory: Any,
    value: Any,
    *,
    label: str,
    issues: list[dict[str, str]],
) -> Any:
    """Copy a binding while validating its optional run-relative path."""
    if not isinstance(value, dict):
        return value
    binding = dict(value)
    if "relative_path" in binding:
        binding["relative_path"] = _validated_artifact_name(
            directory,
            binding.get("relative_path"),
            label=f"{label}.relative_path",
            issues=issues,
        )
    return binding


def _validated_stage_ledger(
    directory: Any,
    value: Any,
    *,
    issues: list[dict[str, str]],
) -> Any:
    """Copy ledger evidence and validate any bounded overflow artifact names."""
    if not isinstance(value, dict):
        return value
    ledger = copy.deepcopy(value)
    stages = ledger.get("stages")
    if not isinstance(stages, dict):
        return ledger
    for stage_name, stage_record in stages.items():
        if not isinstance(stage_record, dict):
            continue
        validated_names = {}
        for field in ("overflow", "overflow_artifact"):
            overflow = stage_record.get(field)
            if not isinstance(overflow, dict) or "name" not in overflow:
                continue
            overflow = dict(overflow)
            stage_record[field] = overflow
            key = repr(overflow.get("name"))
            if key not in validated_names:
                validated_names[key] = _validated_artifact_name(
                    directory, overflow.get("name"),
                    label=f"stage_delta_ledger.stages.{stage_name}.{field}", issues=issues,
                )
            overflow["name"] = validated_names[key]
        original_norms = stage_record.get("index_normalizations", [])
        stage_record["index_normalizations"] = _validated_index_normalizations(
            directory, original_norms, issues=issues
        )
        latest = stage_record.get("index_normalization")
        if isinstance(latest, dict):
            matching = next((i for i, norm in enumerate(original_norms)
                             if norm == latest), None) if isinstance(original_norms, list) else None
            stage_record["index_normalization"] = (
                stage_record["index_normalizations"][matching] if matching is not None else
                _validated_index_normalizations(directory, [latest], issues=issues)[0]
            )
    return ledger


def _validated_index_normalizations(
    directory: Any,
    value: Any,
    *,
    issues: list[dict[str, str]],
) -> Any:
    """Copy index normalizations and validate any bounded overflow artifact names."""
    if not isinstance(value, list):
        return value
    norms = copy.deepcopy(value)
    for index, norm in enumerate(norms):
        if not isinstance(norm, dict):
            continue
        validated_names: dict[str, Any] = {}
        for field in ("overflow", "overflow_artifact"):
            overflow = norm.get(field)
            if isinstance(overflow, dict) and "name" in overflow:
                overflow = dict(overflow)
                norm[field] = overflow
                original = overflow.get("name")
                key = repr(original)
                if key not in validated_names:
                    validated_names[key] = _validated_artifact_name(
                        directory, original,
                        label=f"index_normalizations[{index}].{field}", issues=issues,
                    )
                overflow["name"] = validated_names[key]
    return norms


def _validated_prompt_decisions(
    directory: Any,
    value: Any,
    *,
    issues: list[dict[str, str]],
) -> Any:
    """Copy prompt-capacity evidence without emitting stale artifact names."""
    if not isinstance(value, list):
        return value
    decisions: list[Any] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            decisions.append(item)
            continue
        decision = dict(item)
        if "artifact_basename" in decision:
            decision["artifact_basename"] = _validated_artifact_name(
                directory,
                decision.get("artifact_basename"),
                label=f"prompt_capacity_decisions[{index}].artifact_basename",
                issues=issues,
            )
        decisions.append(decision)
    return decisions


def _validated_revisor_input(
    directory: Any,
    value: Any,
    *,
    issues: list[dict[str, str]],
    references: dict[str, Any],
) -> Any:
    """Copy closer handoff metadata and validate its narrative pointers."""
    if not isinstance(value, dict):
        return value
    handoff = dict(value)
    producer = handoff.get("producer_narrative")
    if isinstance(producer, dict):
        producer_copy = dict(producer)
        if "artifact_basename" in producer_copy:
            producer_name = _validated_artifact_name(
                directory,
                producer_copy.get("artifact_basename"),
                label="revisor_input.producer_narrative.artifact_basename",
                issues=issues,
            )
            producer_copy["artifact_basename"] = producer_name
            _add_artifact_reference(
                references,
                "producer_narrative",
                producer_name,
                stage=producer_copy.get("stage"),
            )
        handoff["producer_narrative"] = producer_copy
    review = handoff.get("work_review")
    if isinstance(review, dict):
        review_copy = dict(review)
        if "artifact_name" in review_copy:
            review_name = _validated_artifact_name(
                directory,
                review_copy.get("artifact_name"),
                label="revisor_input.work_review.artifact_name",
                issues=issues,
            )
            review_copy["artifact_name"] = review_name
            _add_artifact_reference(
                references,
                "review_artifacts",
                review_name,
                stage=review_copy.get("stage"),
            )
        handoff["work_review"] = review_copy
    return handoff


def _review_artifacts(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return named review evidence, deriving compatibility records as needed."""
    recorded = state.get("review_artifacts")
    outcomes = state.get("review_outcomes", {})
    records = (
        [item for item in recorded if isinstance(item, dict)]
        if isinstance(recorded, list)
        else []
    )
    if not isinstance(outcomes, dict) or not outcomes:
        return records
    try:
        lifecycle = get_lifecycle(str(state.get("lifecycle", "standard")))
    except ValueError:
        return records
    recorded_stages = {
        item.get("stage") for item in records if isinstance(item.get("stage"), str)
    }
    for stage in lifecycle.stages:
        outcome = outcomes.get(stage.name)
        if (
            stage.role != "reviewer"
            or not isinstance(outcome, str)
            or stage.name in recorded_stages
        ):
            continue
        records.append({
            "schema": "agent-phase-review-artifact-v1",
            "name": f"{stage.prefix}.result.json",
            "stage": stage.name,
            "checkpoint": stage.checkpoint,
            "outcome": outcome,
            "independent": True,
        })
    return records


def _revision_record(state: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("authorized_revisor_revisions", "revisor_revisions"):
        value = state.get(key)
        if isinstance(value, dict):
            return value
    if state.get("lifecycle") != "work-reviewed":
        return None
    paths = state.get("revision_paths")
    if (not isinstance(paths, list) or not paths) and isinstance(
        state.get("post_review_revision_delta"), dict
    ):
        paths = state["post_review_revision_delta"].get("paths")
    if not isinstance(paths, list) or not paths:
        return None
    return {
        "schema": "agent-phase-revisor-revision-v1",
        "stage": state.get("terminal_result_stage"),
        "paths": list(paths),
        "authorized": True,
        "terminal_bytes_verified": bool(state.get("terminal_bytes_verified")),
        "independent_review_after_revision": False,
    }


def _terminal_narrative(directory: Any, state: dict[str, Any]) -> str | None:
    narrative = state.get("closer_narrative")
    if isinstance(narrative, str):
        return narrative
    stage_name = state.get("terminal_result_stage")
    if not isinstance(stage_name, str):
        return None
    try:
        lifecycle = get_lifecycle(str(state.get("lifecycle", "standard")))
        stage = lifecycle.stage(stage_name)
        artifact = directory.path / f"{stage.prefix}.result.json"
        value = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, AttributeError):
        return None
    body = value.get("body") if isinstance(value, dict) else None
    return body if isinstance(body, str) else None


def _closer_report(
    directory: Any, state: dict[str, Any]
) -> tuple[dict[str, str | None], str | None]:
    """Return explicit closer fields, deriving only from labelled narrative."""
    narrative = _terminal_narrative(directory, state)
    report = {
        key: state.get(key)
        for key in (
            "closer_disposition",
            "closer_rationale",
            "qualification_evidence",
            "unresolved_concerns",
        )
    }
    if isinstance(narrative, str):
        # Import lazily: lifecycle_dispatch imports result and result-repair
        # modules, while result artifacts are written from the dispatcher.
        from .lifecycle_dispatch import terminal_narrative_fields

        parsed = terminal_narrative_fields(narrative)
        for key, value in parsed.items():
            if report[key] is None:
                report[key] = value
    return report, narrative


def _bounded_paths(paths: Any) -> list[str]:
    if not isinstance(paths, list):
        return []
    return [str(path) for path in paths if isinstance(path, str)]


def _inline_deltas(info: dict[str, Any]) -> list[dict[str, Any]]:
    value = info.get("deltas", [])
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _paths_for(
    info: dict[str, Any], classification: str, statuses: tuple[str, ...] = ()
) -> list[str]:
    deltas = _inline_deltas(info)
    paths = [
        item.get("path")
        for item in deltas
        if item.get("classification") == classification
        and (not statuses or item.get("status") in statuses)
        and isinstance(item.get("path"), str)
    ]
    if paths:
        return [str(path) for path in paths]
    if not statuses:
        field = {
            "product": "product_paths",
            "operational_metadata": "operational_metadata_paths",
            "git_authority": "git_authority_paths",
        }.get(classification)
        return _bounded_paths(info.get(field)) if field else []
    return []


def _metadata_path_view(state: dict[str, Any]) -> dict[str, Any]:
    """Bound retained names; count stage path observations, not unique run paths."""
    explicit = state.get("operational_metadata_paths")
    if isinstance(explicit, list):
        paths = sorted(_bounded_paths(explicit))
        total = len(paths)
        basis = "supplied paths"
    else:
        ledger = _mapping(state.get("stage_delta_ledger"))
        stages = _mapping(ledger.get("stages"))
        paths = []
        total = 0
        for info in stages.values():
            if not isinstance(info, dict):
                continue
            observed = _paths_for(info, "operational_metadata")
            paths.extend(observed)
            total += max(len(observed), _count(info.get("operational_metadata_paths_total_count")),
                         _count(_mapping(info.get("classification_counts")).get("operational_metadata")))
        if not stages:
            paths = [d["path"] for d in _inline_deltas(ledger)
                     if d.get("classification") == "operational_metadata" and isinstance(d.get("path"), str)]
            total = max(len(paths), _count(_mapping(ledger.get("classification_counts")).get("operational_metadata")))
        paths.sort()
        basis = "stage path observations; repeated paths may occur"
    inline = paths[:MAX_STAGE_INLINE_DELTAS]
    return {"operational_metadata_paths": inline,
            "operational_metadata_paths_total_count": total,
            "operational_metadata_paths_inline_count": len(inline),
            "operational_metadata_paths_omitted_count": max(0, total - len(inline)),
            "operational_metadata_paths_count_basis": basis}


def _interstage_view(state: dict[str, Any]) -> list[dict[str, Any]]:
    observations = state.get("interstage_observations")
    if not isinstance(observations, list):
        return []
    records = []
    for item in observations[:MAX_STAGE_INLINE_DELTAS]:
        if not isinstance(item, dict):
            continue
        paths = _bounded_paths(item.get("paths"))[:MAX_STAGE_INLINE_DELTAS]
        total = max(len(paths), _count(item.get("paths_total_count")), _count(item.get("total_deltas_count")))
        records.append({"kind": "between_stages", "preceding_stage": item.get("preceding_stage"),
                        "following_stage": item.get("following_stage"), "paths": paths,
                        "paths_total_count": total, "paths_inline_count": len(paths),
                        "paths_omitted_count": total - len(paths)})
    return records


def _authority_text(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _authority_events(info: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for delta in _inline_deltas(info):
        if delta.get("classification") != "git_authority":
            continue
        event = delta.get("authority_event")
        if isinstance(event, dict):
            events.append(event)
    before = info.get("before_git_authority")
    after = info.get("after_git_authority")
    if isinstance(before, dict) and isinstance(after, dict):
        for field, kind in (
            ("branch", "branch_change"),
            ("head", "head_change"),
            ("active_operations", "active_operations_change"),
        ):
            if before.get(field) != after.get(field) and not any(
                item.get("kind") == kind for item in events
            ):
                events.append({
                    "kind": kind,
                    "before": before.get(field),
                    "after": after.get(field),
                })
    return events


def _stage_execution_story(
    state: dict[str, Any],
    invocations: list[dict[str, Any]],
) -> list[str]:
    story: list[str] = ["## Stage execution story", ""]
    ledger = state.get("stage_delta_ledger")
    stages_info = ledger.get("stages", {}) if isinstance(ledger, dict) else {}
    if not isinstance(stages_info, dict):
        stages_info = {}

    try:
        lifecycle = get_lifecycle(str(state.get("lifecycle", "standard")))
        stage_specs = {stage.name: stage for stage in lifecycle.stages}
        ordered_stages = list(lifecycle.stage_names)
    except ValueError:
        stage_specs = {}
        ordered_stages = []
    for candidate in list(stages_info) + [
        record.get("stage") for record in invocations if isinstance(record, dict)
    ]:
        if isinstance(candidate, str) and candidate not in ordered_stages:
            ordered_stages.append(candidate)

    invocations_by_stage: dict[str, list[dict[str, Any]]] = {}
    for record in invocations:
        if isinstance(record, dict) and isinstance(record.get("stage"), str):
            invocations_by_stage.setdefault(record["stage"], []).append(record)

    disposition_roles = {
        "plan": "planner",
        "plan_review": "plan reviewer",
        "work": "producer",
        "final_review": "work reviewer",
        "closeout": "closer",
        "produce": "producer",
        "work_review": "work reviewer",
        "revise_close": "closer",
        "produce_close": "producer / closer",
        "solo": "producer / closer",
    }

    # The invocation list is useful for transports; the stage list below is
    # the semantic story, including stages that had no provider result.
    story.extend(["### Stages invoked", ""])
    if invocations:
        for record in invocations:
            stage_name = record.get("stage", "unknown")
            role = record.get("role", "unknown")
            provider = record.get("provider", "unknown")
            profile = record.get("profile", "unknown")
            story.append(
                f"- stage `{stage_name}`: role=`{role}` endpoint=`{provider}/{profile}` "
                f"kind=`{record.get('invocation_kind', 'semantic')}` "
                f"exit={record.get('exit_code')}"
            )
    else:
        story.append("- No stage invocations recorded.")
    story.append("")

    story.extend(["### Stage changes and observations", ""])
    if not ordered_stages:
        story.append("- No stage delta records present.")
    for stage_name in ordered_stages:
        info = stages_info.get(stage_name)
        info = info if isinstance(info, dict) else {}
        stage_invocations = invocations_by_stage.get(stage_name, [])
        stage_spec = stage_specs.get(stage_name)
        role = (
            stage_invocations[0].get("role")
            if stage_invocations and isinstance(stage_invocations[0].get("role"), str)
            else stage_spec.role if stage_spec is not None else info.get("role", "unknown")
        )
        disposition = disposition_roles.get(stage_name, role)
        story.append(f"#### Stage `{stage_name}` (role: `{role}`; disposition: `{disposition}`)")
        if stage_invocations:
            exits = ", ".join(str(item.get("exit_code")) for item in stage_invocations)
            story.append(f"- invocation status: invoked ({len(stage_invocations)}), exit={exits}")
        else:
            story.append("- invocation status: no provider invocation recorded")

        adds = _paths_for(info, "product", ("added", "A"))
        mods = _paths_for(
            info,
            "product",
            ("modified", "M", "renamed", "R", "type_changed", "T"),
        )
        dels = _paths_for(info, "product", ("deleted", "D"))
        meta = _paths_for(info, "operational_metadata")
        product_paths = _bounded_paths(info.get("product_paths"))

        prod_counts = _mapping(info.get("classification_status_counts")).get("product")
        if isinstance(prod_counts, dict):
            add_count = _count(prod_counts.get("added")) + _count(prod_counts.get("A"))
            # Tree deltas use --no-renames and index renames are split into delete+add;
            # renamed statuses (R/renamed) and type/mode changes only appear in
            # legacy/foreign records and are rendered under modifications.
            mod_count = (
                _count(prod_counts.get("modified"))
                + _count(prod_counts.get("M"))
                + _count(prod_counts.get("renamed"))
                + _count(prod_counts.get("R"))
                + _count(prod_counts.get("type_changed"))
                + _count(prod_counts.get("T"))
            )
            del_count = _count(prod_counts.get("deleted")) + _count(prod_counts.get("D"))
        else:
            add_count = len(adds)
            mod_count = len(mods)
            del_count = len(dels)

        # Detailed evidence is a lower bound even if inherited counters are
        # missing, malformed, or smaller than the retained path records.
        add_count = max(add_count, len(adds))
        mod_count = max(mod_count, len(mods))
        del_count = max(del_count, len(dels))
        known_statuses = {"added", "A", "modified", "M", "renamed", "R", "type_changed", "T", "deleted", "D"}
        other_paths = [d["path"] for d in _inline_deltas(info)
                       if d.get("classification") == "product" and d.get("status") not in known_statuses
                       and isinstance(d.get("path"), str)]
        other_count = (sum(_count(v) for k, v in prod_counts.items() if k not in known_statuses)
                       if isinstance(prod_counts, dict) else len(other_paths))
        if other_count or other_paths:
            shown = other_paths[:_STORY_PATH_LIMIT]
            story.append(f"- product other/unclassified status ({max(other_count, len(other_paths))}; "
                         f"{len(shown)} shown, {max(other_count, len(other_paths)) - len(shown)} paths omitted/unavailable): "
                         + ", ".join(f"`{p}`" for p in shown))

        if add_count > 0:
            if adds:
                suffix = " ..." if len(adds) > _STORY_PATH_LIMIT else ""
                count_str = f"{add_count}"
                if add_count > len(adds):
                    count_str += f"; {len(adds)} inline, {add_count - len(adds)} omitted"
                story.append(
                    f"- product additions ({count_str}): "
                    f"{', '.join(f'`{path}`' for path in adds[:_STORY_PATH_LIMIT])}{suffix}"
                )
            else:
                story.append(
                    f"- product additions ({add_count}; detailed paths omitted by reporting bounds)"
                )

        if mod_count > 0:
            if mods:
                suffix = " ..." if len(mods) > _STORY_PATH_LIMIT else ""
                count_str = f"{mod_count}"
                if mod_count > len(mods):
                    count_str += f"; {len(mods)} inline, {mod_count - len(mods)} omitted"
                story.append(
                    f"- product modifications ({count_str}): "
                    f"{', '.join(f'`{path}`' for path in mods[:_STORY_PATH_LIMIT])}{suffix}"
                )
            else:
                story.append(
                    f"- product modifications ({mod_count}; detailed paths omitted by reporting bounds)"
                )

        if del_count > 0:
            if dels:
                suffix = " ..." if len(dels) > _STORY_PATH_LIMIT else ""
                count_str = f"{del_count}"
                if del_count > len(dels):
                    count_str += f"; {len(dels)} inline, {del_count - len(dels)} omitted"
                story.append(
                    f"- product deletions ({count_str}): "
                    f"{', '.join(f'`{path}`' for path in dels[:_STORY_PATH_LIMIT])}{suffix}"
                )
            else:
                story.append(
                    f"- product deletions ({del_count}; detailed paths omitted by reporting bounds)"
                )

        total_prod = max(len(product_paths), _count(info.get("product_paths_total_count")),
                         _count(_mapping(info.get("classification_counts")).get("product")))
        if total_prod and not (add_count or mod_count or del_count or other_count or adds or mods or dels):
            suffix = " ..." if len(product_paths) > _STORY_PATH_LIMIT else ""
            count_str = f"{total_prod}"
            if total_prod > len(product_paths):
                count_str += f"; {len(product_paths)} inline, {total_prod - len(product_paths)} omitted"
            story.append(
                f"- product paths ({count_str}; status unavailable in inline evidence): "
                f"{', '.join(f'`{path}`' for path in product_paths[:_STORY_PATH_LIMIT])}{suffix}"
            )

        meta_total = _count(info.get("operational_metadata_paths_total_count"), len(meta))
        if meta_total > 0 or meta:
            total_meta = max(meta_total, len(meta))
            if meta:
                suffix = " ..." if len(meta) > _STORY_PATH_LIMIT else ""
                count_str = f"{total_meta}"
                if total_meta > len(meta):
                    count_str += f"; {len(meta)} inline, {total_meta - len(meta)} omitted"
                story.append(
                    f"- operational metadata touched ({count_str}): "
                    f"{', '.join(f'`{path}`' for path in meta[:_STORY_PATH_LIMIT])}{suffix}"
                )
            else:
                story.append(
                    f"- operational metadata touched ({total_meta}; detailed paths omitted by reporting bounds)"
                )

        authority_events = _authority_events(info)
        if authority_events:
            story.append(f"- git authority events ({len(authority_events)}):")
            for event in authority_events[:_STORY_AUTHORITY_LIMIT]:
                story.append(
                    f"  - `{event.get('kind', 'authority_change')}`: "
                    f"{_authority_text(event.get('before'))} -> "
                    f"{_authority_text(event.get('after'))}"
                )
            if len(authority_events) > _STORY_AUTHORITY_LIMIT:
                story.append(
                    f"  - {len(authority_events) - _STORY_AUTHORITY_LIMIT} authority events omitted"
                )

        has_changes = bool(
            add_count
            or mod_count
            or del_count
            or adds
            or mods
            or dels
            or product_paths
            or total_prod
            or other_count
            or meta_total
            or meta
            or authority_events
        )
        if not has_changes:
            stage_norms = [
                n for n in state.get("index_normalizations", [])
                if isinstance(n, dict) and n.get("stage") == stage_name
            ]
            if not stage_norms and isinstance(info.get("index_normalizations"), list):
                stage_norms = [
                    n for n in info.get("index_normalizations")
                    if isinstance(n, dict)
                ]
            limitations = info.get("observation_limitations", {})
            boundary_limits = (
                limitations.get("boundary", [])
                if isinstance(limitations, dict)
                else []
            )
            overflow = _mapping(info.get("overflow") or info.get("overflow_artifact"))
            transport_failed = any(
                isinstance(inv, dict) and (inv.get("exit_code") not in (0, None) or inv.get("blocking_reason"))
                for inv in stage_invocations
            )

            if stage_norms:
                if any(n.get("safety") == "unsafe" for n in stage_norms):
                    story.append("- No product or metadata path delta observed; unsafe index observation recorded.")
                else:
                    story.append("- No product or metadata path delta observed; index anomaly recorded.")
            elif boundary_limits:
                story.append("- No product or metadata path delta observed; boundary capture limitation recorded.")
            elif transport_failed:
                story.append("- No product or metadata path delta observed; transport failure recorded.")
            elif overflow or _count(info.get("omitted_deltas_count")) > 0:
                story.append("- No product or metadata path delta observed; overflow record recorded.")
            else:
                story.append("- No changes observed.")

        total = info.get("total_deltas_count", len(_inline_deltas(info)))
        inline = info.get("inline_deltas_count", len(_inline_deltas(info)))
        omitted = info.get("omitted_deltas_count", 0)
        completeness = info.get("observation_completeness", "unknown")
        story.append(
            f"- observation completeness: `{completeness}` "
            f"(total={total}, inline={inline}, omitted={omitted})"
        )
        overflow = _mapping(info.get("overflow") or info.get("overflow_artifact"))
        if overflow:
            story.append(f"- overflow evidence: written={_count(overflow.get('written_count'))}, "
                         f"omitted={_count(overflow.get('omitted_overflow_count'))}")
        if overflow.get("name"):
            story.append(f"- overflow artifact: `{overflow['name']}`")
        limitations = info.get("observation_limitations")
        if isinstance(limitations, dict):
            limitation_labels: list[str] = []
            classification = limitations.get("classification")
            if isinstance(classification, str):
                limitation_labels.append(classification)
            metadata_scan = limitations.get("metadata_scan")
            omitted_roots = (
                metadata_scan.get("omitted_roots", [])
                if isinstance(metadata_scan, dict)
                else []
            )
            if isinstance(omitted_roots, list) and omitted_roots:
                limitation_labels.append(
                    "omitted metadata roots: "
                    + ", ".join(str(root) for root in omitted_roots[:_STORY_PATH_LIMIT])
                )
            if limitation_labels:
                story.append(f"- observation limitations: {'; '.join(limitation_labels)}")

        for norm in state.get("index_normalizations", []):
            if not isinstance(norm, dict) or norm.get("stage") != stage_name:
                continue
            safety = norm.get("safety", "unknown")
            staged = norm.get("staged_changes", [])
            staged_paths = [
                item.get("path") for item in staged
                if isinstance(item, dict) and isinstance(item.get("path"), str)
            ] if isinstance(staged, list) else []
            if not staged_paths and isinstance(norm.get("staged_paths"), list):
                staged_paths = [str(p) for p in norm["staged_paths"] if isinstance(p, str)]
            total_staged = _count(norm.get("staged_paths_total_count"), _count(norm.get("staged_changes_total_count"), len(staged_paths)))
            if total_staged > len(staged_paths):
                detail = f"{total_staged} staged path(s); {len(staged_paths)} inline, {total_staged - len(staged_paths)} omitted"
            else:
                detail = f"{len(staged_paths)} staged path(s)"
            if staged_paths:
                detail += ": " + ", ".join(
                    f"`{path}`" for path in staged_paths[:_STORY_PATH_LIMIT]
                )
            story.append(f"- index normalization/anomaly: `{safety}` ({detail})")
            intent = _bounded_paths(norm.get("intent_to_add_paths"))
            total_intent = _count(norm.get("intent_to_add_paths_total_count"), len(intent))
            if intent or total_intent > 0:
                prefix = f"  - intent-to-add ({total_intent} total): " if total_intent > len(intent) else "  - intent-to-add: "
                intent_line = prefix + ", ".join(
                    f"`{path}`" for path in intent[:_STORY_PATH_LIMIT]
                )
                if total_intent > len(intent):
                    intent_line += f" ... ({total_intent - len(intent)} omitted)"
                story.append(intent_line)
            unmerged = _bounded_paths(norm.get("unmerged_paths"))
            total_unmerged = _count(norm.get("unmerged_paths_total_count"), len(unmerged))
            if unmerged or total_unmerged > 0:
                prefix = f"  - unmerged/conflict paths ({total_unmerged} total): " if total_unmerged > len(unmerged) else "  - unmerged/conflict paths: "
                unmerged_line = prefix + ", ".join(
                    f"`{path}`" for path in unmerged[:_STORY_PATH_LIMIT]
                )
                if total_unmerged > len(unmerged):
                    unmerged_line += f" ... ({total_unmerged - len(unmerged)} omitted)"
                story.append(unmerged_line)
            if norm.get("reason"):
                story.append(f"  - normalization limitation: {norm['reason']}")
        story.append("")

    # A bounded global view retains normalization details even for a stage that
    # did not have a product delta.
    story.extend(["### Index normalization events", ""])
    norms = state.get("index_normalizations", [])
    if isinstance(norms, list) and norms:
        for norm in norms:
            if not isinstance(norm, dict):
                continue
            stage_name = norm.get("stage", "unknown")
            staged = norm.get("staged_changes", [])
            total_count = _count(norm.get("staged_changes_total_count"), len(staged) if isinstance(staged, list) else 0)
            inline_count = len(staged) if isinstance(staged, list) else 0
            safety = norm.get("safety", "unknown")
            count_info = f"{total_count} path(s)"
            if total_count > inline_count:
                count_info += f" ({inline_count} inline, {total_count - inline_count} omitted)"
            detail = f"{count_info}, safety=`{safety}`"
            overflow = _mapping(norm.get("overflow") or norm.get("overflow_artifact"))
            if overflow:
                detail += (f", overflow-written={_count(overflow.get('written_count'))}"
                           f", overflow-omitted={_count(overflow.get('omitted_overflow_count'))}")
            intent = _bounded_paths(norm.get("intent_to_add_paths"))
            if intent:
                detail += ", intent-to-add=" + ", ".join(
                    f"`{path}`" for path in intent[:_STORY_PATH_LIMIT]
                )
            if norm.get("reason"):
                detail += f", reason={norm['reason']}"
            story.append(f"- [{stage_name}] {detail}")
    else:
        story.append("- No index normalization required.")
    story.append("")

    story.extend(["### Git authority events", ""])
    all_authority_events: list[tuple[str, dict[str, Any]]] = []
    for stage_name in ordered_stages:
        info = stages_info.get(stage_name)
        if isinstance(info, dict):
            all_authority_events.extend(
                (stage_name, event) for event in _authority_events(info)
            )
    if all_authority_events:
        for stage_name, event in all_authority_events[:_STORY_AUTHORITY_LIMIT]:
            story.append(
                f"- [{stage_name}] `{event.get('kind', 'authority_change')}`: "
                f"{_authority_text(event.get('before'))} -> "
                f"{_authority_text(event.get('after'))}"
            )
        if len(all_authority_events) > _STORY_AUTHORITY_LIMIT:
            story.append(
                f"- {len(all_authority_events) - _STORY_AUTHORITY_LIMIT} authority events omitted"
            )
    else:
        branch_info = state.get("git_authority_branch")
        if isinstance(branch_info, dict) and not branch_info.get("matches", True):
            story.append(
                f"- Branch mismatch: entry branch `{branch_info.get('entry_branch')}`, "
                f"final branch `{branch_info.get('current_branch')}` (fail-closed)"
            )
        elif isinstance(branch_info, dict):
            story.append(
                f"- Entry branch `{branch_info.get('entry_branch')}` preserved at finalization."
            )
        else:
            story.append("- Normal Git authority maintained.")
    story.append("")

    story.extend(["### Cross-stage reversions and supersessions", ""])
    path_history: dict[str, list[tuple[str, str]]] = {}
    for stage_name in ordered_stages:
        info = stages_info.get(stage_name)
        if not isinstance(info, dict):
            continue
        for delta in _inline_deltas(info):
            if delta.get("classification") != "product":
                continue
            path = delta.get("path")
            status = delta.get("status")
            if isinstance(path, str) and isinstance(status, str):
                path_history.setdefault(path, []).append((stage_name, status))
    reversions: list[str] = []
    supersessions: list[str] = []
    for path, history in path_history.items():
        if len(history) < 2:
            continue
        stages_involved = [stage for stage, _status in history]
        if history[-1][1] in ("deleted", "D"):
            reversions.append(
                f"`{path}` (changed in {stages_involved[0]}, deleted in {stages_involved[-1]})"
            )
        else:
            supersessions.append(
                f"`{path}` (changed across {', '.join(stages_involved)})"
            )
    ledger = state.get("stage_delta_ledger", {})
    history_truncated = (
        (isinstance(ledger, dict) and (ledger.get("observation_completeness") == "truncated" or _count(ledger.get("omitted_deltas_count")) > 0))
        or any(
            isinstance(stages_info.get(st), dict)
            and (
                stages_info[st].get("observation_completeness") == "truncated"
                or _count(stages_info[st].get("omitted_deltas_count")) > 0
            )
            for st in ordered_stages
        )
    )

    if reversions:
        qualifier = " (observed in bounded inline evidence)" if history_truncated else ""
        story.append(
            f"- Reversions ({len(reversions)}){qualifier}: "
            + ", ".join(reversions[:_STORY_PATH_LIMIT])
        )
    if supersessions:
        qualifier = " (observed in bounded inline evidence)" if history_truncated else ""
        story.append(
            f"- Supersessions ({len(supersessions)}){qualifier}: "
            + ", ".join(supersessions[:_STORY_PATH_LIMIT])
        )
    if not (reversions or supersessions):
        if history_truncated:
            story.append("- Cross-stage reversions or supersessions: none detected in bounded inline evidence.")
        else:
            story.append("- No cross-stage path reversions or supersessions detected.")
    story.append("")

    story.extend(["### Observation completeness and limitations", ""])
    story.append("- Scope: Git product paths and bounded built-in operational metadata roots.")
    story.append("- External writes outside repository root are not tracked.")
    for stage_name in ordered_stages:
        info = stages_info.get(stage_name)
        if not isinstance(info, dict):
            continue
        limitations = info.get("observation_limitations")
        if not isinstance(limitations, dict):
            continue
        omitted = limitations.get("omitted_stage_deltas_count", 0)
        metadata_scan = limitations.get("metadata_scan")
        omitted_roots = (
            metadata_scan.get("omitted_roots", [])
            if isinstance(metadata_scan, dict)
            else []
        )
        completeness = info.get("observation_completeness", "unknown")
        if completeness != "bounded" or omitted or omitted_roots:
            detail = f"stage `{stage_name}`: completeness=`{completeness}`"
            if omitted:
                detail += f", omitted deltas={omitted}"
            if omitted_roots:
                detail += ", omitted roots=" + ", ".join(
                    str(root) for root in omitted_roots[:_STORY_PATH_LIMIT]
                )
            story.append(f"- {detail}")
    story.append("")

    story.extend(["### Review outcomes (advisory)", ""])
    review_outcomes = state.get("review_outcomes", {})
    if isinstance(review_outcomes, dict) and review_outcomes:
        for stage_name, outcome in review_outcomes.items():
            role = disposition_roles.get(stage_name, "reviewer")
            checkpoint = stage_specs.get(stage_name)
            checkpoint_name = checkpoint.checkpoint if checkpoint is not None else None
            checkpoint_text = f", checkpoint=`{checkpoint_name}`" if checkpoint_name else ""
            story.append(
                f"- `{stage_name}` role=`{role}`: **{outcome}** "
                f"(advisory{checkpoint_text})"
            )
    else:
        story.append("- No review outcomes recorded.")
    story.append("")

    story.extend(["### Closer disposition and revision delta", ""])
    disposition = state.get("closer_disposition") or "not explicitly reported"
    rationale = state.get("closer_rationale") or "none"
    story.append(f"- Closer disposition: **{disposition}**")
    story.append(f"- Closer rationale: {rationale}")
    qualification = state.get("qualification_evidence")
    story.append(
        "- Qualification evidence claimed by closer: "
        + (qualification if isinstance(qualification, str) and qualification else "none")
    )
    concerns = state.get("unresolved_concerns")
    story.append(
        "- Unresolved or deferred concerns: "
        + (concerns if isinstance(concerns, str) and concerns else "none reported")
    )
    closer_delta = state.get("closeout_delta") or state.get("post_review_revision_delta")
    if isinstance(closer_delta, dict):
        paths = _bounded_paths(closer_delta.get("paths"))
        story.append(
            f"- Closer delta changed: {closer_delta.get('changed', False)} "
            f"({len(paths)} path(s))"
        )
        if paths:
            story.append("  - " + ", ".join(f"`{path}`" for path in paths[:_STORY_PATH_LIMIT]))
    cumulative = state.get("cumulative_closeout_delta") or state.get("cumulative_post_review_delta")
    if isinstance(cumulative, dict):
        paths = _bounded_paths(cumulative.get("paths"))
        story.append(
            f"- Cumulative post-review delta changed: {cumulative.get('changed', False)} "
            f"({len(paths)} path(s))"
        )
    story.append(f"- Final candidate covered by review: **{state.get('final_candidate_reviewed')}**")
    story.append("")

    story.extend(["### Manager attention reasons", ""])
    reasons = state.get("manager_attention_reasons", [])
    if not isinstance(reasons, list):
        reasons = []
    reasons = [str(reason) for reason in reasons if isinstance(reason, str)]
    if reasons:
        for reason in reasons[:_STORY_REASON_LIMIT]:
            story.append(f"- attention reason: **{reason}**")
        if len(reasons) > _STORY_REASON_LIMIT:
            story.append(f"- {len(reasons) - _STORY_REASON_LIMIT} attention reasons omitted")
    elif state.get("manager_disposition_required"):
        disposition_record = state.get("manager_disposition")
        reason = (
            disposition_record.get("reason", "unknown")
            if isinstance(disposition_record, dict)
            else "unknown"
        )
        story.append(f"- disposition required: **{reason}**")
    else:
        story.append("- None (automatic completion / publication permitted).")
    story.append("")

    persistence_errors = (
        ("stage_delta_capture_error", "stage-delta capture"),
        ("index_normalization_error", "index normalization"),
        ("failure_boundary_error", "failure-boundary persistence"),
    )
    present_errors = [
        (key, label, state.get(key))
        for key, label in persistence_errors
        if state.get(key)
    ]
    if present_errors:
        story.extend(["### Boundary persistence observations", ""])
        for key, label, error in present_errors:
            if isinstance(error, dict):
                code = error.get("code") or error.get("reason") or "recorded"
            else:
                code = "recorded"
            story.append(
                f"- `{key}` ({label}): `{code}`; "
                "primary failure remains authoritative."
            )
        story.append("")
    return story


def _artifact_handoff_lines(result: dict[str, Any]) -> list[str]:
    """Render exact validated artifact names for the prompter."""
    lines = ["### Artifact handoff", ""]
    references = result.get("artifact_references")
    if not isinstance(references, dict):
        references = {}
    labels = (
        ("plan_material", "plan material"),
        ("producer_evidence", "producer evidence"),
        ("producer_narrative", "producer narrative"),
        ("terminal_result", "terminal stage result"),
        ("dispatcher_result", "aggregate dispatcher result"),
    )
    rendered = False
    for key, label in labels:
        reference = references.get(key)
        if isinstance(reference, dict) and isinstance(reference.get("name"), str):
            lines.append(f"- {label}: `{reference['name']}`")
            rendered = True
    reviews = references.get("review_artifacts")
    if isinstance(reviews, list):
        for reference in reviews:
            if not isinstance(reference, dict) or not isinstance(reference.get("name"), str):
                continue
            stage = reference.get("stage", "review")
            lines.append(f"- {stage} review: `{reference['name']}`")
            rendered = True
    issues = result.get("artifact_reference_issues")
    if isinstance(issues, list) and issues:
        lines.append(
            "- unavailable artifact pointers: "
            + ", ".join(
                str(item.get("pointer", "unknown"))
                for item in issues[:_STORY_REASON_LIMIT]
                if isinstance(item, dict)
            )
        )
        rendered = True
    if not rendered:
        lines.append("- No validated run-relative artifact pointers were available.")
    lines.append("")
    return lines


def write(directory: Any, state: dict[str, Any], invocations: list[dict[str, Any]]) -> None:
    blocking = state.get("blocking_reason")
    artifact_issues: list[dict[str, str]] = []
    artifact_references: dict[str, Any] = {"review_artifacts": []}
    closer_report, closer_narrative = _closer_report(directory, state)
    review_artifacts = []
    for index, item in enumerate(_review_artifacts(state)):
        if not isinstance(item, dict):
            continue
        record = dict(item)
        if "name" in record:
            name = _validated_artifact_name(
                directory,
                record.get("name"),
                label=f"review_artifacts[{index}].name",
                issues=artifact_issues,
            )
            record["name"] = name
            if name is None:
                record["artifact_reference_status"] = "unavailable"
            else:
                _add_artifact_reference(
                    artifact_references,
                    "review_artifacts",
                    name,
                    stage=record.get("stage"),
                )
        review_artifacts.append(record)
    review_artifact_names = [
        item["name"] for item in review_artifacts if isinstance(item.get("name"), str)
    ]
    review_artifact_outcomes = {
        item["stage"]: item["outcome"]
        for item in review_artifacts
        if isinstance(item.get("stage"), str)
        and isinstance(item.get("outcome"), str)
    }
    proposal_binding = state.get(
        "proposal_binding", state.get("plan_proposal_binding", state.get("plan_candidate"))
    )
    proposal_binding = _validated_binding(
        directory,
        proposal_binding,
        label="proposal_binding",
        issues=artifact_issues,
    )
    producer_binding = state.get(
        "producer_binding", state.get("work_product_binding", state.get("produced_candidate"))
    )
    revisor_binding = state.get(
        "revisor_binding",
        state.get(
            "revisor_candidate",
            state.get("revise_close_candidate", state.get("closeout_candidate")),
        ),
    )
    revisor_revisions = _revision_record(state)
    revisor_revision_paths = (
        list(revisor_revisions.get("paths", []))
        if isinstance(revisor_revisions, dict)
        and isinstance(revisor_revisions.get("paths"), list)
        else list(state.get("revision_paths", []))
        if isinstance(state.get("revision_paths"), list)
        else []
    )
    planner_proposal = state.get("planner_proposal")
    if not isinstance(planner_proposal, dict) and isinstance(proposal_binding, dict):
        planner_proposal = {
            "binding": proposal_binding,
            "artifact_name": "plan-material.md",
            "exact_bytes": True,
            "implementation_authority": False,
        }
    elif isinstance(planner_proposal, dict) and planner_proposal.get("artifact_name") == "plan.material.bin":
        planner_proposal = dict(planner_proposal)
        planner_proposal["artifact_name"] = "plan-material.md"
    if isinstance(planner_proposal, dict):
        planner_proposal = dict(planner_proposal)
        if isinstance(planner_proposal.get("binding"), dict):
            planner_proposal["binding"] = _validated_binding(
                directory,
                planner_proposal["binding"],
                label="planner_proposal.binding",
                issues=artifact_issues,
            )
        p_name = planner_proposal.get("artifact_name")
        if p_name and not _artifact_exists(directory, str(p_name)):
            # A historical producer may still carry the retired spelling. A
            # canonical plan file is the only compatible repair; never expose
            # the stale or missing pointer as a final artifact reference.
            if p_name == "plan.material.bin" and _artifact_exists(
                directory, "plan-material.md"
            ):
                p_name = "plan-material.md"
        if p_name is not None:
            p_name = _validated_artifact_name(
                directory,
                p_name,
                label="planner_proposal.artifact_name",
                issues=artifact_issues,
            )
            planner_proposal["artifact_name"] = p_name
            _add_artifact_reference(
                artifact_references, "plan_material", p_name, kind="planner_proposal"
            )
    if isinstance(state.get("plan_candidate"), dict):
        plan_candidate = _validated_binding(
            directory,
            state["plan_candidate"],
            label="candidates.plan",
            issues=artifact_issues,
        )
    else:
        plan_candidate = state.get("plan_candidate")

    producer_evidence = state.get("producer_evidence")
    if isinstance(producer_evidence, dict):
        producer_evidence = dict(producer_evidence)
        producer_name = producer_evidence.get("artifact_name")
        if producer_name is None:
            stage_name = producer_evidence.get("stage")
            try:
                producer_name = f"{get_lifecycle(str(state.get('lifecycle', 'standard'))).stage(str(stage_name)).prefix}.stdout.md"
            except (ValueError, TypeError):
                producer_name = None
        if producer_name is not None:
            producer_name = _validated_artifact_name(
                directory,
                producer_name,
                label="producer_evidence.artifact_name",
                issues=artifact_issues,
            )
            producer_evidence["artifact_name"] = producer_name
            _add_artifact_reference(
                artifact_references,
                "producer_evidence",
                producer_name,
                stage=producer_evidence.get("stage"),
            )
            _add_artifact_reference(
                artifact_references,
                "producer_narrative",
                producer_name,
                stage=producer_evidence.get("stage"),
            )

    revisor_input = _validated_revisor_input(
        directory,
        state.get("revisor_input"),
        issues=artifact_issues,
        references=artifact_references,
    )
    prompt_capacity_decisions = _validated_prompt_decisions(
        directory,
        state.get("prompt_capacity_decisions", []),
        issues=artifact_issues,
    )
    prompt_policy = state.get("prompt_policy")
    if isinstance(prompt_policy, dict):
        prompt_policy = dict(prompt_policy)
        if "evidence_artifact" in prompt_policy:
            prompt_policy["evidence_artifact"] = _validated_artifact_name(
                directory,
                prompt_policy.get("evidence_artifact"),
                label="prompt_policy.evidence_artifact",
                issues=artifact_issues,
            )

    stage_delta_ledger = _validated_stage_ledger(
        directory,
        state.get("stage_delta_ledger"),
        issues=artifact_issues,
    )
    index_normalizations = _validated_index_normalizations(
        directory,
        state.get("index_normalizations", []),
        issues=artifact_issues,
    )
    work_review = next(
        (
            item
            for item in review_artifacts
            if item.get("stage") in {"work_review", "final_review"}
        ),
        None,
    )
    post_revisor_review = state.get("post_revisor_review")
    if not isinstance(post_revisor_review, dict):
        post_revisor_review = {
            "performed": False,
            "automatic": False,
            "reason": "selected lifecycle has no post-revisor independent review",
        }
    current_worktree_product = (
        revisor_input.get("current_worktree_product")
        if isinstance(revisor_input, dict)
        else None
    )
    review_outcomes = state.get("review_outcomes", {})
    final_review = state.get("final_review")
    if final_review is None and isinstance(review_outcomes, dict):
        final_review = review_outcomes.get("final_review")
    terminal_result_name: str | None = None
    try:
        terminal_stage = get_lifecycle(
            str(state.get("lifecycle", "standard"))
        ).terminal_result_stage
        terminal_prefix = get_lifecycle(
            str(state.get("lifecycle", "standard"))
        ).stage(terminal_stage).prefix
        terminal_result_name = _validated_artifact_name(
            directory,
            f"{terminal_prefix}.result.json",
            label="terminal_result.artifact_name",
            issues=artifact_issues,
        )
    except (ValueError, TypeError):
        _record_artifact_issue(
            artifact_issues, "terminal_result.artifact_name", "unknown_lifecycle"
        )
    if terminal_result_name is not None:
        _add_artifact_reference(
            artifact_references,
            "terminal_result",
            terminal_result_name,
            stage=state.get("terminal_result_stage"),
        )

    # The dispatcher may have serialized state before entering this writer.
    # Keep every pointer-bearing state field aligned with the validated copies
    # used in result.json so resume and later disposition never see a stale or
    # private artifact name.  The caller owns the final state serialization.
    state["review_artifacts"] = copy.deepcopy(review_artifacts)
    state["review_artifact_names"] = list(review_artifact_names)
    state["review_artifact_outcomes"] = dict(review_artifact_outcomes)
    state["planner_proposal"] = copy.deepcopy(planner_proposal)
    if "proposal_binding" in state or "plan_proposal_binding" in state:
        state["proposal_binding"] = copy.deepcopy(proposal_binding)
        state["plan_proposal_binding"] = copy.deepcopy(proposal_binding)
    if "plan_candidate" in state:
        state["plan_candidate"] = copy.deepcopy(plan_candidate)
    if "producer_evidence" in state:
        state["producer_evidence"] = copy.deepcopy(producer_evidence)
    if "revisor_input" in state:
        state["revisor_input"] = copy.deepcopy(revisor_input)
    if "work_review" in state or work_review is not None:
        state["work_review"] = copy.deepcopy(work_review)
    if "prompt_capacity_decisions" in state:
        state["prompt_capacity_decisions"] = copy.deepcopy(prompt_capacity_decisions)
    if "prompt_policy" in state:
        state["prompt_policy"] = copy.deepcopy(prompt_policy)
    if "stage_delta_ledger" in state:
        state["stage_delta_ledger"] = copy.deepcopy(stage_delta_ledger)
    if "index_normalizations" in state:
        state["index_normalizations"] = copy.deepcopy(index_normalizations)
    state["artifact_reference_issues"] = copy.deepcopy(artifact_issues)
    state["terminal_result_artifact"] = terminal_result_name
    if state.get('ownership_challenges') is not None:
        from .ownership_challenge import statuses
        state['ownership_challenge_states'] = statuses(state)
    result = {
        "schema": RESULT_SCHEMA,
        **({"run_layout": copy.deepcopy(state["run_layout"])} if "run_layout" in state else {}),
        "run_id": state["run_id"],
        "project": state["project"],
        "phase_id": state["phase_id"],
        "run_directory": state["run_directory"],
        "outcome": state.get("outcome"),
        "semantic_outcome": state.get("semantic_outcome"),
        "finalization_outcome": state.get("finalization_outcome"),
        "finalization": state.get("finalization", state.get("finalization_outcome")),
        "complete": state.get("complete", False),
        "phase_type": state["phase_type"],
        "execution_mode": state["execution_mode"],
        "lifecycle": state.get("lifecycle", "standard"),
        "finalization_policy": state.get("finalization_policy", "publish"),
        "expected_stages": state.get("expected_stages", []),
        "expected_provider_invocations": state.get("expected_provider_invocations"),
        "expected_review_count": state.get("expected_review_count"),
        "terminal_result_stage": state.get("terminal_result_stage"),
        "stage_accounting_schema": state.get("stage_accounting_schema"),
        "stages_invoked": list(state.get("stages_invoked", [])),
        "stage_transports_completed": list(
            state.get("stage_transports_completed", [])
        ),
        "stage_transport_outcomes": state.get("stage_transport_outcomes", {}),
        "failure_stage_transport": state.get("failure_stage_transport"),
        "terminal_result_validated": state.get(
            "terminal_result_validated", False
        ),
        "manager_disposition_required": state.get(
            "manager_disposition_required", False
        ),
        "preserved_candidate": state.get("preserved_candidate"),
        "repository_finalized": state.get("repository_finalized"),
        "repository_binding": state.get("repository_binding"),
        "repository_state_validated": state.get("repository_state_validated"),
        "repository_mutation_attempted": state.get("repository_mutation_attempted"),
        "completion_kind": state.get("completion_kind"),
        "cwd": state["cwd"],
        "entry": state.get("entry"),
        "entry_head": (state.get("entry") or {}).get("head"),
        "final_head": state.get("final_head"),
        "phase_delta": state.get("phase_delta"),
        "phase_owned_paths": state.get("phase_owned_paths"),
        "mechanical_phase_delta": state.get("mechanical_phase_delta"),
        "path_ownership": state.get("path_ownership"),
        "ownership_challenges": state.get("ownership_challenges"),
        "ownership_challenge_states": state.get("ownership_challenge_states"),
        "ownership_candidate_evidence": state.get("ownership_candidate_evidence"),
        "mechanical_phase_owned_paths": state.get("mechanical_phase_owned_paths"),
        "ownership_type_transitions": state.get("ownership_type_transitions"),
        "path_dispositions": state.get("path_dispositions", []),
        "path_disposition_noops": state.get("path_disposition_noops", []),
        "excluded_paths": state.get("excluded_paths", []),
        "raw_terminal_candidate": state.get("raw_terminal_candidate"),
        "publication_candidate": state.get("publication_candidate"),
        "revision_paths": state.get("revision_paths"),
        "terminal_transport": state.get("terminal_transport"),
        "result_repair_transport": state.get("result_repair_transport"),
        "finalization_attempted": state.get("finalization_attempted", False),
        "commit": state.get("commit"),
        "push": state.get("push"),
        "archive_path": state.get("archive_path"),
        "archive": state.get("archive"),
        "prompt_policy": prompt_policy,
        "prompt_capacity_decisions": prompt_capacity_decisions,
        "review_count": len(
            state.get("effective_checkpoints", state.get("checkpoints_completed", []))
        ),
        "review_count_required": state.get("expected_review_count", 2),
        "stages_completed": list(state.get("stages_completed", [])),
        "candidates": {
            "plan": plan_candidate,
            "pre_final": state.get("pre_final_candidate"),
            "closeout": state.get("closeout_candidate"),
            "terminal": state.get("terminal_candidate"),
            "produced": state.get("produced_candidate"),
            "entry_tree": (state.get("entry") or {}).get("tree"),
            "final_tree": state.get("final_tree"),
        },
        "post_review_revision_delta": state.get("post_review_revision_delta"),
        "checkpoint_candidate": state.get("checkpoint_candidate"),
        "proposed_commit_message": state.get("proposed_commit_message"),
        "provider_exits": [
            {
                "stage": record["stage"],
                "exit_code": record.get("exit_code"),
                "invocation_kind": record.get("invocation_kind", "semantic"),
            }
            for record in invocations
        ],
        "provider_outcomes": state.get("provider_outcomes", {}),
        "review_outcomes": review_outcomes,
        # Keep the historical stage machine key alongside neutral aliases.
        "final_review": final_review,
        # Neutral additive aliases. Legacy fields above remain canonical for
        # compatibility with existing consumers.
        "review_artifacts": review_artifacts,
        "review_artifact_names": review_artifact_names,
        "review_artifact_outcomes": review_artifact_outcomes,
        "reviews": review_artifacts,
        "review_advisories": state.get("review_advisories", []),
        "planner_proposal": planner_proposal,
        "proposal_binding": proposal_binding,
        "plan_proposal_binding": proposal_binding,
        "producer_candidate": producer_binding,
        "producer_binding": producer_binding,
        "work_product_binding": producer_binding,
        "work_review": work_review,
        "current_worktree_product": current_worktree_product,
        "revisor_input": revisor_input,
        "revisor_candidate": revisor_binding,
        "revisor_binding": revisor_binding,
        "revisor_revision_paths": revisor_revision_paths,
        "authorized_revisor_revisions": revisor_revisions,
        "revisor_revisions": revisor_revisions,
        "post_revisor_review": post_revisor_review,
        "provider_evidence": state.get("provider_evidence", []),
        "provider_invocations_inherited": state.get(
            "provider_invocations_inherited", 0
        ),
        "provider_invocations_performed": state.get(
            "provider_invocations_performed", len(invocations)
        ),
        "provider_invocations_effective": state.get(
            "provider_invocations_effective"
        ),
        "semantic_provider_invocations_inherited": state.get(
            "semantic_provider_invocations_inherited"
        ),
        "semantic_provider_invocations_performed": state.get(
            "semantic_provider_invocations_performed"
        ),
        "auxiliary_provider_invocations": state.get(
            "auxiliary_provider_invocations",
            state.get("auxiliary_provider_invocations_performed", 0),
        ),
        "auxiliary_provider_invocations_performed": state.get(
            "auxiliary_provider_invocations_performed",
            state.get("auxiliary_provider_invocations", 0),
        ),
        "total_effective_provider_turns": state.get(
            "total_effective_provider_turns"
        ),
        "effective_stages": state.get("effective_stages"),
        "effective_checkpoints": state.get("effective_checkpoints"),
        "effective_stage_routes": state.get("effective_stage_routes"),
        "route_transition": state.get("route_transition"),
        "resume": state.get("resume"),
        "result_repair": state.get("result_repair"),
        "antigravity_output_recovery": state.get(
            "antigravity_output_recovery"
        ),
        "commit_message_origin": state.get("commit_message_origin"),
        "source_artifacts_verified": state.get("source_artifacts_verified"),
        "source_archive_verified": state.get("source_archive_verified"),
        "failure_candidate": state.get("failure_candidate"),
        "candidate_manifest": state.get("candidate_manifest"),
        "adoption": state.get("adoption"),
        "final_review_mutation": state.get("final_review_mutation"),
        "work_review_mutation": state.get("work_review_mutation"),
        "immutable_review_bindings": state.get("immutable_review_bindings", {}),
        "review_binding_invalidations": state.get("review_binding_invalidations", {}),
        "stage_delta_ledger": stage_delta_ledger,
        "stage_delta_record": stage_delta_ledger,
        "closer_disposition": closer_report["closer_disposition"],
        "closer_rationale": closer_report["closer_rationale"],
        "closer_narrative": closer_narrative,
        "qualification_evidence": closer_report["qualification_evidence"],
        "unresolved_concerns": closer_report["unresolved_concerns"],
        "closer_report": closer_report,
        "producer_evidence": producer_evidence,
        **_metadata_path_view(state),
        "interstage_observations": _interstage_view(state),
        "interstage_observations_total_count": len(state.get("interstage_observations", [])) if isinstance(state.get("interstage_observations"), list) else 0,
        "interstage_observations_inline_count": len(_interstage_view(state)),
        "interstage_observations_omitted_count": max(0, len(state.get("interstage_observations", [])) - len(_interstage_view(state))) if isinstance(state.get("interstage_observations"), list) else 0,
        "entry_dirt_overlap": state.get("entry_dirt_overlap"),
        "index_normalizations": index_normalizations,
        "terminal_fence_copies": state.get("terminal_fence_copies"),
        "closeout_fence_copies": state.get("closeout_fence_copies"),
        "shadow": state.get("shadow"),
        "blocking_reason": blocking,
        "stage_delta_capture_error": state.get("stage_delta_capture_error"),
        "index_normalization_error": state.get("index_normalization_error"),
        "failure_boundary_error": state.get("failure_boundary_error"),
        "terminal_result_artifact": terminal_result_name,
        "artifact_references": artifact_references,
        "artifact_reference_issues": artifact_issues,
        "task_artifacts_unverified": True,
    }
    directory.write_json("result.json", result)

    # result.json itself is a handoff artifact. Add that pointer only after the
    # first write proves that the run-relative regular file exists, then seal
    # the machine result with the complete reference set.
    dispatcher_result_name = _validated_artifact_name(
        directory,
        "result.json",
        label="dispatcher_result.artifact_name",
        issues=artifact_issues,
    )
    if dispatcher_result_name is not None:
        _add_artifact_reference(
            artifact_references,
            "dispatcher_result",
            dispatcher_result_name,
            kind="aggregate_result",
        )
    result["artifact_references"] = artifact_references
    result["artifact_reference_issues"] = artifact_issues
    directory.write_json("result.json", result)

    commit = result["commit"]
    commit_str = (
        f"- commit: `{commit['sha']}` {commit['subject']}"
        if commit else "- commit: none"
    )
    push = result["push"] or {}
    push_str = (
        f"- push: {push.get('status', 'unknown')} "
        f"(attempted={push.get('attempted', False)})"
    )
    delta = result["phase_delta"] or []
    owned = result["phase_owned_paths"] or []
    revisions = result["revisor_revision_paths"] or []
    metadata_paths = result["operational_metadata_paths"]

    lines = [
        f"# Phase dispatch result — {state['run_id']}",
        "",
        "## Phase and publication outcome",
        "",
        f"- project: `{result['project']}`",
        f"- phase id: `{result['phase_id']}`",
        f"- outcome: **{result['outcome']}**",
        f"- semantic outcome: **{result.get('semantic_outcome')}**",
        f"- finalization: **{result.get('finalization_outcome') or result.get('finalization')}**",
        f"- finalization repair class: `{(result.get('finalization') or {}).get('repair_class')}`",
        f"- local commit outcome: `{((result.get('finalization') or {}).get('local_commit') or {}).get('outcome')}`",
        f"- complete: **{result['complete']}**",
        f"- lifecycle: `{result['lifecycle']}`",
        f"- finalization policy: `{result['finalization_policy']}`",
        f"- completion kind: `{result['completion_kind']}`",
        commit_str,
        push_str,
        f"- finalization attempted: **{result['finalization_attempted']}**",
        "",
    ]
    lines.extend(_stage_execution_story(state, invocations))
    lines.extend(_artifact_handoff_lines(result))
    lines.extend([
        "## Closer disposition and rationale",
        "",
        f"- closer disposition: **{result.get('closer_disposition') or 'not explicitly reported'}**",
        f"- closer rationale: {result.get('closer_rationale') or 'not explicitly reported in terminal narrative'}",
    ])
    if result.get("closer_narrative"):
        lines.extend(["", result["closer_narrative"].strip(), ""])
    else:
        lines.append("")

    lines.extend([
        "## Changed product paths and retained metadata paths",
        "",
        f"- raw terminal observation: `{(result.get('raw_terminal_candidate') or {}).get('tree')}`",
        f"- publication candidate: `{(result.get('publication_candidate') or {}).get('tree')}`",
        f"- mechanical delta (observed, not necessarily published): {len(result.get('mechanical_phase_delta') or [])} path(s)",
    ])
    lines.extend(f"  - `{item['status']}` {item['path']}" for item in (result.get('mechanical_phase_delta') or [])[:_STORY_PATH_LIMIT])
    mechanical_owned = result.get('mechanical_phase_owned_paths') or []
    lines.append(f'- mechanically phase-owned paths: {len(mechanical_owned)}')
    lines.extend(f'  - `{path}`' for path in mechanical_owned[:_STORY_PATH_LIMIT])
    lines.extend(f"- path disposition: `{item['path']}` — `{item['disposition']}`" for item in result.get('path_dispositions', [])[:_STORY_PATH_LIMIT])
    lines.append(f"- ignored redundant metadata dispositions: {len(result.get('path_disposition_noops', []))}; proof retained in path_disposition_noops")
    lines.append(f"- excluded from publication: {len(result.get('excluded_paths') or [])} path(s)")
    lines.extend(f"  - `{path}`" for path in (result.get('excluded_paths') or [])[:_STORY_PATH_LIMIT])
    lines.extend([
        f"- phase delta: {len(delta)} path(s)",
    ])
    lines.extend(f"  - `{change['status']}` {change['path']}" for change in delta[:_STORY_PATH_LIMIT])
    if len(delta) > _STORY_PATH_LIMIT:
        lines.append(f"  - {len(delta) - _STORY_PATH_LIMIT} paths omitted from Markdown")
    lines.append(f"- phase-owned paths: {len(owned)}")
    lines.extend(f"  - `{path}`" for path in owned[:_STORY_PATH_LIMIT])
    if len(owned) > _STORY_PATH_LIMIT:
        lines.append(f"  - {len(owned) - _STORY_PATH_LIMIT} paths omitted from Markdown")
    shown_metadata = metadata_paths[:_STORY_PATH_LIMIT]
    lines.append(f"- retained operational metadata paths: total={result['operational_metadata_paths_total_count']}, "
                 f"inline={len(metadata_paths)}, omitted={result['operational_metadata_paths_omitted_count']}; "
                 f"{result['operational_metadata_paths_count_basis']}")
    lines.extend(f"  - `{path}`" for path in shown_metadata)
    lines.append(f"  - {max(0, result['operational_metadata_paths_total_count'] - len(shown_metadata))} paths omitted/unavailable in Markdown")
    lines.append(f"- between-stages metadata observations: total={result['interstage_observations_total_count']}, "
                 f"inline={result['interstage_observations_inline_count']}, omitted={result['interstage_observations_omitted_count']}")
    for observation in result['interstage_observations'][:_STORY_PATH_LIMIT]:
        lines.append(f"  - between `{observation['preceding_stage']}` and `{observation['following_stage']}`: "
                     f"total={observation['paths_total_count']}, inline={observation['paths_inline_count']}, "
                     f"omitted={observation['paths_omitted_count']}; unattributed to providers")
    if len(result['interstage_observations']) > _STORY_PATH_LIMIT:
        lines.append(f"  - {len(result['interstage_observations']) - _STORY_PATH_LIMIT} observations omitted from Markdown")
    lines.append("")

    lines.extend([
        "## Qualification performed and its outcomes",
        "",
    ])
    if result.get("qualification_evidence"):
        lines.extend([result["qualification_evidence"].strip(), ""])
    else:
        lines.extend(["- qualification evidence: not explicitly reported in terminal narrative", ""])

    lines.extend([
        "## Review outcomes and unresolved concerns",
        "",
        f"- reviews: {result['review_count']} of {result['review_count_required']}",
        f"- review artifacts: {len(review_artifacts)}",
    ])
    if review_artifacts:
        lines.append("- review artifact outcomes:")
        lines.extend(
            f"  - `{item['name']}`: {item['outcome']} ({item['stage']})"
            for item in review_artifacts
            if isinstance(item.get("name"), str)
            and isinstance(item.get("outcome"), str)
            and isinstance(item.get("stage"), str)
        )
    else:
        lines.append("- review artifact outcomes: none")

    if isinstance(revisor_revisions, dict):
        revision_paths = revisor_revisions.get("paths", [])
        lines.append(
            "- authorized revisor revisions: "
            f"{len(revision_paths) if isinstance(revision_paths, list) else 0} path(s)"
        )
        if isinstance(revision_paths, list):
            lines.extend(f"  - `{path}`" for path in revision_paths)
    else:
        lines.append("- authorized revisor revisions: none")

    if post_revisor_review.get("performed") or post_revisor_review.get("automatic"):
        lines.append(
            "- automatic post-revisor independent review: "
            f"performed={post_revisor_review.get('performed')} "
            f"automatic={post_revisor_review.get('automatic')}"
        )
    else:
        lines.append("- automatic post-revisor independent review: none")

    lines.append(
        "- unresolved concerns: "
        f"{result.get('unresolved_concerns') or 'not explicitly reported in terminal narrative'}"
    )
    if state.get("review_advisories"):
        lines.append("- review advisories:")
        lines.extend(f"  - {adv}" for adv in state["review_advisories"])
    lines.append("")

    lines.extend([
        "## Manager attention items",
        "",
        f"- manager disposition required: **{result['manager_disposition_required']}**",
    ])
    if state.get("entry_dirt_overlap"):
        lines.append(f"- entry dirt overlap: {', '.join(state['entry_dirt_overlap'])}")
    if state.get('ownership_challenges'):
        from .ownership_challenge import statuses
        challenge_status = statuses(state)
        lines.append('- Ownership challenges (entry dirt cannot be automatically restored):')
        records = state['ownership_challenges']['records']
        for challenge in records[:128]:
            path = challenge['path'].encode('utf-8')
            display = path[:1024].decode('utf-8', 'ignore')
            if len(path) > 1024:
                display += '… [path truncated]'
            lines.append(f"  - {challenge['challenge_id']}: {display} — {challenge['reason']} — {challenge_status[challenge['challenge_id']]}")
        if len(records) > 128:
            lines.append(f"  - {len(records) - 128} further challenges omitted; see result.json")

    if blocking:
        lines.extend(["", f"### Blocked — {blocking['code']}", "", blocking["detail"]])
    lines.append("")

    lines.extend([
        "## Supporting identities and mechanical evidence",
        "",
        f"- entry HEAD: `{result['entry_head']}`",
        f"- final HEAD: `{result['final_head']}`",
        f"- stages completed: {len(result['stages_completed'])} of {len(result['expected_stages'])}",
        f"- stages invoked: {len(result['stages_invoked'])} of {len(result['expected_stages'])}",
        f"- stage transports completed: {len(result['stage_transports_completed'])} of {len(result['expected_stages'])}",
        f"- terminal result validated: **{result['terminal_result_validated']}**",
        f"- semantic provider invocations: inherited={result['semantic_provider_invocations_inherited']} performed={result['semantic_provider_invocations_performed']}",
        f"- auxiliary provider invocations performed: {result['auxiliary_provider_invocations_performed']}",
        f"- authorized revisor revision paths: {len(revisions)}",
    ])
    lines.extend(f"  - `{path}`" for path in revisions[:_STORY_PATH_LIMIT])
    if len(revisions) > _STORY_PATH_LIMIT:
        lines.append(f"  - {len(revisions) - _STORY_PATH_LIMIT} paths omitted from Markdown")
    for name, candidate in result["candidates"].items():
        if isinstance(candidate, dict) and isinstance(candidate.get("tree"), str):
            lines.append(f"- {name} candidate tree: `{candidate['tree']}`")
    if result["archive_path"]:
        lines.append(f"- archive: `{result['archive_path']}`")
    transport = result["terminal_transport"]
    if isinstance(transport, dict):
        lines.append(
            "- terminal transport: "
            f"{transport.get('provider')} {transport.get('profile')} "
            f"exit={transport.get('exit_code')} "
            f"validated={transport.get('validated')} "
            f"stdout_bytes={transport.get('stdout_bytes')}"
        )
    repair_transport = result["result_repair_transport"]
    if isinstance(repair_transport, dict):
        lines.append(
            "- result-repair transport: "
            f"{repair_transport.get('provider')} {repair_transport.get('profile')} "
            f"exit={repair_transport.get('exit_code')} "
            f"validated={repair_transport.get('validated')} "
            f"stdout_bytes={repair_transport.get('stdout_bytes')}"
        )
    failure_transport = result["failure_stage_transport"]
    if isinstance(failure_transport, dict):
        lines.append(
            "- failure-stage transport: "
            f"{failure_transport.get('stage')} "
            f"status={failure_transport.get('status')} "
            f"exit={failure_transport.get('exit_code')}"
        )
    failure_candidate = result["failure_candidate"]
    if isinstance(failure_candidate, dict):
        lines.append(
            "- failure candidate: "
            f"stage={failure_candidate.get('stage')} "
            f"tree=`{failure_candidate.get('tree')}` "
            f"paths={len(failure_candidate.get('paths', []))}"
        )
    lines += [
        "",
        "Task-specific artifacts requested by the operator prompt are not "
        "mechanically verified by the dispatcher.",
        "",
    ]
    directory.write_text("result.md", "\n".join(lines))
