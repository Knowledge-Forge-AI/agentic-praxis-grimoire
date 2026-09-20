"""APG166ZB-CONTEXT-PROJECTION1 pure instruction projection over the real tracked source."""
from __future__ import annotations

import hashlib
import itertools
import json
from pathlib import Path

import pytest

from agent_phase import instruction_projection as ip

ROOT = Path(__file__).resolve().parents[3]
SOURCE = (ROOT / "claude/CLAUDE.md").read_bytes()
MANIFEST = (ROOT / "claude" / ip.MANIFEST_NAME).read_bytes()
# Authority, Git/worktree, artifact, worker, cleanup and host boundaries that
# every projected stage must keep. Listed here, not derived from the manifest.
INVARIANT = ["preamble", "role-split", "permissions-enforced-elsewhere", "environment", "stack-notes",
             "claude-profile-authority", "dispatcher-profile-authority", "git-and-hook-policy",
             "agent-scratch", "subagent-workers", "worker-runtime-authority"]
CLASS_SETS = [[c] for c in ip.CLASSES] + [list(p) for p in itertools.combinations(ip.CLASSES, 2)] + [list(ip.CLASSES)]


def manifest_value():
    return json.loads(MANIFEST)


def raw(value) -> bytes:
    return json.dumps(value).encode()


def test_manifest_tiles_the_tracked_source_byte_for_byte():
    manifest = ip.load_manifest(MANIFEST)
    assert manifest["source"] == {"path": "CLAUDE.md", **ip.identity(SOURCE)}, "re-review the classification"
    sections = ip.split(SOURCE.decode(), manifest)
    rebuilt = "".join(s["lead"] + "".join(f["text"] for f in s["fragments"]) for s in sections)
    assert rebuilt.encode() == SOURCE
    assert [f["id"] for s in sections for f in s["fragments"]] == [f["id"] for f in manifest["fragments"]]


def test_manifest_invariant_flags_match_the_independent_core_list():
    manifest = ip.load_manifest(MANIFEST)
    assert [f["id"] for f in manifest["fragments"] if f["invariant"]] == INVARIANT


@pytest.mark.parametrize("classes", CLASS_SETS, ids=lambda c: "+".join(c))
@pytest.mark.parametrize("ambient", [True, False])
def test_every_projection_keeps_the_invariant_core_verbatim(classes, ambient):
    result = ip.project(SOURCE, MANIFEST, classes, {"ambient_tools": ambient})
    body = result["body"].decode()
    rows = {r["id"]: r for r in result["fragments"]}
    sections = ip.split(SOURCE.decode(), ip.load_manifest(MANIFEST))
    texts = {f["id"]: f["text"] for s in sections for f in s["fragments"]}
    for ident in INVARIANT:
        assert rows[ident]["selected"] is True and texts[ident] in body, ident
    # No projection can include a fragment outside its declared classification.
    for row in result["fragments"]:
        applicable = bool(set(row["stages"]) & set(classes)) and (ambient or not row["requires"])
        assert row["selected"] is applicable, row["id"]
        if not applicable:
            assert texts[row["id"]] not in body, row["id"]
    assert set(result["selected"]) | set(result["omitted"]) == set(rows)


def test_stage_overlays_appear_only_where_declared():
    plan = ip.project(SOURCE, MANIFEST, ["planning"], {"ambient_tools": False})
    review = ip.project(SOURCE, MANIFEST, ["review_verification"], {"ambient_tools": False})
    work = ip.project(SOURCE, MANIFEST, ["implementation"], {"ambient_tools": True})
    closeout = ip.project(SOURCE, MANIFEST, ["closeout"], {"ambient_tools": True})
    assert "review-adversarial-posture" in plan["selected"] and "review-adversarial-posture" in review["selected"]
    # The single-example abstraction rule in that paragraph binds implementers too.
    assert "review-adversarial-posture" in work["selected"]
    assert {"phase-owner-codex-review", "claude-profile-operations", "server-memory", "repomap",
            "curated-shell-environment"} <= set(plan["omitted"])
    assert "phase-owner-codex-review" in work["selected"] and closeout["omitted"] == []
    for result in (plan, review):
        assert result["comparison"]["projected_bytes"] < result["comparison"]["static_bytes"]
        assert result["comparison"]["static_bytes"] == len(SOURCE)
    for result in (work, closeout):
        assert result["omitted"] == [] and result["body"] == SOURCE and result["comparison"]["delta_bytes"] == 0
    # An omitted leading fragment keeps its heading when a later one is selected.
    assert "## Review posture\n\nWhen doing adversarial review" in plan["body"].decode()
    assert "## Claude fallback profiles\n\n- `claude/settings.json`" in plan["body"].decode()


def test_projection_is_deterministic_and_identity_tracks_inputs():
    first = ip.project(SOURCE, MANIFEST, ["planning"], {"ambient_tools": False})
    again = ip.project(SOURCE, MANIFEST, ["planning"], {"ambient_tools": False})
    assert first == again and first["projection"] == ip.identity(first["body"])
    assert first["projection"]["sha256"] == hashlib.sha256(first["body"]).hexdigest()
    other = ip.project(SOURCE, MANIFEST, ["review_verification"], {"ambient_tools": False})
    assert other["projection_id"] != first["projection_id"]
    # Reclassifying one fragment changes identity even when bytes stay equal.
    value = manifest_value()
    row = next(f for f in value["fragments"] if f["id"] == "documentation-defaults")
    row["why"] = "changed rationale"
    changed = ip.project(SOURCE, raw(value), ["planning"], {"ambient_tools": False})
    assert changed["body"] == first["body"] and changed["projection_id"] != first["projection_id"]
    # A source change is refused rather than silently reclassified.
    edited = SOURCE.replace(b"standing defaults", b"standing default!")
    with pytest.raises(ip.ProjectionError) as caught:
        ip.project(edited, MANIFEST, ["planning"], {"ambient_tools": False})
    assert caught.value.code == "instruction_source_changed"
    value = manifest_value()
    value["source"].update(ip.identity(edited))
    reclassified = ip.project(edited, raw(value), ["planning"], {"ambient_tools": False})
    assert reclassified["projection_id"] != first["projection_id"]


def mutate(kind):
    value = manifest_value()
    fragments = value["fragments"]
    if kind == "duplicate_id":
        fragments[1]["id"] = fragments[0]["id"]
    elif kind == "unknown_key":
        fragments[4]["tools"] = ["Bash"]
    elif kind == "authority_top_level":
        value["permissions"] = {"allow": ["Bash"]}
    elif kind == "unknown_stage":
        fragments[4]["stages"] = ["deploy"]
    elif kind == "unknown_capability":
        fragments[8]["requires"] = ["root"]
    elif kind == "narrowed_invariant":
        fragments[1]["stages"] = ["planning"]
    elif kind == "uncovered_section":
        del fragments[5]
    elif kind == "reordered":
        fragments[3], fragments[4] = fragments[4], fragments[3]
    elif kind == "interleaved":
        fragments.insert(9, dict(fragments[6], id="late-review"))
    elif kind == "ambiguous_anchor":
        fragments[7]["anchor"] = ""
    elif kind == "missing_anchor":
        fragments[7]["anchor"] = "No such line in the source."
    elif kind == "leading_anchor":
        fragments[6]["anchor"] = "When doing adversarial review, prioritize missing invariants, unstated"
    elif kind == "wrong_schema":
        value["schema"] = "apg.other/v1"
    elif kind == "duplicate_json_key":
        return MANIFEST.replace(b'"schema": "apg.claude', b'"schema": "x", "schema": "apg.claude', 1)
    elif kind == "not_json":
        return b"{"
    return raw(value)


@pytest.mark.parametrize("kind", ["duplicate_id", "unknown_key", "authority_top_level", "unknown_stage",
                                  "unknown_capability", "narrowed_invariant", "uncovered_section", "reordered",
                                  "interleaved", "ambiguous_anchor", "missing_anchor", "leading_anchor",
                                  "wrong_schema", "duplicate_json_key", "not_json"])
def test_malformed_manifest_is_refused_with_a_stable_code(kind):
    with pytest.raises(ip.ProjectionError) as caught:
        ip.project(SOURCE, mutate(kind), ["planning"], {"ambient_tools": False})
    assert caught.value.code == "instruction_manifest_invalid", caught.value


@pytest.mark.parametrize("classes,capabilities", [([], {"ambient_tools": False}), (["deploy"], {"ambient_tools": False}),
                                                  (["planning"], {}), (["planning"], {"ambient_tools": 1}),
                                                  (["planning", "planning"], {"ambient_tools": True})])
def test_selection_inputs_are_closed(classes, capabilities):
    with pytest.raises(ip.ProjectionError) as caught:
        ip.project(SOURCE, MANIFEST, classes, capabilities)
    assert caught.value.code == "instruction_selection_unavailable"


def test_generation_allowlist_carries_the_manifest():
    from controller_generation_store import ALLOWLIST
    assert "claude/" + ip.MANIFEST_NAME in ALLOWLIST and "claude/CLAUDE.md" in ALLOWLIST
