"""v0.13.0 public-surface additions and historical-surface immutability."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[6]
LIBEXEC = ROOT / "libexec"
if str(LIBEXEC) not in sys.path:
    sys.path.insert(0, str(LIBEXEC))
release = importlib.import_module("apg_public_release")
v013 = importlib.import_module("apg_public_release_v013")


# Digests captured from the unmodified entry module before the v0.13 change:
# (audited surfaces, synthetic candidate filter, deselections, supplements,
# versioned-exclusion outcomes). A difference means history was rewritten.
HISTORICAL_GOLDENS = {
    "0.2.0": ("5e1950998461680ee238e1e3b71b28dc72b959c21197d901bea2077946de2a53", "8d29c231", "4f53cda1", "74234e98", "46e2b601"),
    "0.3.0": ("affa9cf7171ee40e3efdb8b4111c20e6c0cd93c55b0f87a120d44fee41539675", "8d29c231", "4f53cda1", "74234e98", "46e2b601"),
    "0.4.0": ("fa957397b031ff3c8109b0846c65a5bf8306f4d283afefa1045877bd891923ad", "8d29c231", "4f53cda1", "74234e98", "e90f92c5"),
    "0.5.0": ("8139adaec90dfe2477a3f3847b8eddd02dd845b128b066f5ab3be06c335c1c15", "8d29c231", "4f53cda1", "74234e98", "46e2b601"),
    "0.6.0": ("2f3bbfff906ee9c2672d392a1e282eef1129e06daf3a74a92ce05223cbf98958", "8d29c231", "4f53cda1", "74234e98", "46e2b601"),
    "0.7.0": ("c99391d94fc6ed7592822030d5b33154b31cdaec8cac67374b7a5157730142b9", "38b31e0d", "d752767e", "74234e98", "e667646a"),
    "0.8.0": ("ad253630aa6dd77cd0e5f90ecf2a549ebd011fa2dedcccabde6899f18047e062", "38b31e0d", "d752767e", "74234e98", "43b6312d"),
    "0.8.1": ("14979626bb083ac9e4dbbb1c277dea9b133e03dcacc087e45126c13c915f85d5", "38b31e0d", "d752767e", "74234e98", "fd9804f1"),
    "0.9.0": ("c3e9f70e227017a059d8999b74e926360815d70a124f45a55996d8ddb1683b02", "38b31e0d", "d752767e", "74234e98", "96698219"),
    "0.10.0": ("9355027300532fb63904b6221c4494b324d0e7d923fb19d4844d291ee8da4e5b", "166b9427", "d752767e", "b391cc05", "17a8912f"),
    "0.11.0": ("c937913e089755ff24f307cac9e9d02dc8373882ac2ca69a48225e3b4cb3fc1b", "166b9427", "8d61a473", "74234e98", "d9839093"),
    "0.12.0": ("fba77aa38bda33064e4e49ae8b36b07315d8eb543c72ad783ee6fa8c036ddb3a", "166b9427", "8d61a473", "74234e98", "4840730e"),
}


def _digest(value: object) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(rendered).hexdigest()


def _synthetic_paths() -> list[str]:
    paths = {"README.md", "libexec/x.py", "flake.nix", "nix/package.nix", "private",
             "private/x", "pkg/__pycache__/m.py", "a.egg-info/PKG-INFO"}
    paths |= set(release.V07_EXCLUDED_PATHS) | set(release.V07_GENERATED_PATHS)
    paths |= {prefix + "f" for prefix in (*release.V07_EXCLUDED_PREFIXES, *release.V07_GENERATED_PREFIXES)}
    paths |= {"x" + suffix for suffix in release.V07_GENERATED_SUFFIXES}
    return sorted(paths)


class _Entry:
    def __init__(self, path: str) -> None:
        self.path = path.encode()
        self.display_path = path


def _filtered(monkeypatch: pytest.MonkeyPatch, version: str) -> list[str]:
    entries = tuple(_Entry(path) for path in _synthetic_paths())
    monkeypatch.setattr(release, "tree_entries", lambda repository, excluded_prefix=b"": entries)
    return [entry.display_path for entry in release.public_candidate_entries(object(), version)]


def _exclusions(version: str) -> list[list[object]]:
    outcomes: list[list[object]] = []
    for path in _synthetic_paths():
        try:
            release.validate_versioned_policy_exclusions([_Entry(path)], version)
            outcomes.append([path, None])
        except release.ToolError as error:
            outcomes.append([path, str(error)])
    return outcomes


@pytest.mark.parametrize("version", sorted(HISTORICAL_GOLDENS))
def test_historical_release_semantics_are_unchanged(monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    surface, candidate, deselected, supplements, exclusions = HISTORICAL_GOLDENS[version]
    assert _digest([list(item.items()) for item in release.audited_policy_surfaces(version)]) == surface
    assert _digest(_filtered(monkeypatch, version)).startswith(candidate)
    assert _digest(list(release.PUBLIC_VALIDATION_DESELECTIONS_BY_VERSION[version])).startswith(deselected)
    assert _digest(release.PUBLIC_INVENTORY_SUPPLEMENTS_BY_VERSION[version]).startswith(supplements)
    assert _digest(_exclusions(version)).startswith(exclusions)


def test_v013_surface_is_v012_plus_exact_additions() -> None:
    old = release.audited_policy_surfaces("0.12.0")[0]
    new = release.audited_policy_surfaces("0.13.0")[0]
    additions = {
        "required_skills": set(v013.V013_SKILL_ADDITIONS),
        "required_projections": set(v013.V013_PROJECTION_ADDITIONS),
        "required_wrappers": set(v013.V013_WRAPPER_ADDITIONS),
        "required_helpers": set(v013.V013_HELPER_ADDITIONS),
        "required_test_entrypoints": set(v013.V013_TEST_ADDITIONS),
        "critical_files": set(v013.V013_CRITICAL_ADDITIONS) | set(v013.V013_WRAPPER_ADDITIONS)
        | set(v013.V013_HELPER_ADDITIONS) | set(v013.V013_TEST_ADDITIONS),
        "required_licensing_files": set(),
        "validation_categories": set(),
    }
    assert set(new) == set(old) == set(additions)
    for key, added in additions.items():
        assert new[key] == tuple(sorted(set(old[key]) | added)), key
        assert not added & set(old[key]), key


def test_v013_surface_binds_first_party_nix_owners() -> None:
    distribution = json.loads((ROOT / "nix/distribution.json").read_text(encoding="utf-8"))
    assert tuple(distribution["publication"]["critical_files"]) == v013.V013_NIX_CRITICAL_FILES
    assert distribution["publication"]["first_version"] == "0.13.0"
    surface = release.audited_policy_surfaces("0.13.0")[0]
    owned = {item for values in surface.values() for item in values}
    assert set(v013.V013_NIX_CRITICAL_FILES) <= set(surface["critical_files"])
    assert {"bin/apg-qualify-nix", "libexec/apg_nix_qualification.py", "libexec/apg_nix_smoke.py",
            "libexec/apg_nix_distribution.py"} <= owned
    exported = {f"bin/{name}" for name in distribution["commands"]} - {"bin/apgr"}
    assert exported <= set(surface["critical_files"])


def test_v013_audited_paths_exist_and_tests_are_public_mirrored() -> None:
    surface = release.audited_policy_surfaces("0.13.0")[0]
    for key, values in surface.items():
        if key == "validation_categories":
            continue
        for path in values:
            assert (ROOT / path).exists(), path
    for path in v013.V013_TEST_ADDITIONS:
        assert "/agentic-praxis-grimoire/" in path and path.endswith(".test.py")


def test_committed_public_surface_is_the_v013_surface() -> None:
    policy = json.loads((ROOT / "release/public-surface.json").read_text(encoding="utf-8"))
    for key, expected in release.audited_policy_surfaces("0.13.0")[0].items():
        assert tuple(policy[key]) == expected, key


def test_v013_release_gates_extend_v012_semantics() -> None:
    assert release.PUBLIC_VALIDATION_DESELECTIONS_BY_VERSION["0.13.0"] == (
        tuple(
            sorted(
                set(release.PUBLIC_VALIDATION_DESELECTIONS_BY_VERSION["0.12.0"])
                | {
                    "src/test/int/python/agentic-praxis-grimoire/bin/apg-test.int.test.py::test_standalone_unit_runner_executes_real_pytest_xdist_and_coverage_boundary"
                }
            )
        )
    )
    assert release.PUBLIC_INVENTORY_SUPPLEMENTS_BY_VERSION["0.13.0"] is None
    assert release.CANDIDATE_PATH_FILTERS["0.13.0"]("flake.nix")
    assert not release.CANDIDATE_PATH_FILTERS["0.13.0"]("private/x")
    assert v013.ADVANCED_HEAD_VERSIONS == {"0.12.0", "0.13.0"}
    assert v013.MERGED_CHECK_PREDECESSORS["0.13.0"] == "0.12.0"
    for version in ("0.13.1", "0.14.0", "1.0.0"):
        with pytest.raises(release.ToolError):
            release.audited_policy_surfaces(version)


def test_leaf_module_does_not_import_the_orchestrator() -> None:
    spec = importlib.util.find_spec("apg_public_release_v013")
    assert spec is not None and spec.origin is not None
    source = Path(spec.origin).read_text(encoding="utf-8")
    assert "import apg_public_release\n" not in source and "from apg_public_release " not in source


def _public_history(root: Path) -> "release.Repository":
    """Mirror public main: v0.11.0, untagged commit, v0.12.0, untagged repair."""
    release.run_git(root.parent, ["init", "-q", "-b", "main", str(root)])
    release.run_git(root, ["config", "user.name", "APG Test"])
    release.run_git(root, ["config", "user.email", "test@example.invalid"])
    (root / "README.md").write_text("bootstrap\n")
    release.run_git(root, ["add", "."])
    release.run_git(root, ["commit", "-qm", "Release v0.1.0"])
    release.run_git(root, ["tag", "v0.1.0"])
    for subject, tag in (("Release v0.11.0", "v0.11.0"), ("ci: advanced main", None),
                         ("Release v0.12.0", "v0.12.0"), ("APG160: repair", None)):
        release.run_git(root, ["commit", "--allow-empty", "-qm", subject])
        if tag:
            release.run_git(root, ["tag", "-a", tag, "-m", subject])
    return release.resolve_repository(root, "public history fixture")


def test_v013_lineage_accepts_untagged_commits_between_releases_only_for_v013(tmp_path, monkeypatch):
    repository = _public_history(tmp_path / "public")
    first = release.text_git(repository.root, ["rev-list", "--max-parents=0", "HEAD"])
    monkeypatch.setattr(release, "PUBLIC_V01_COMMIT", first)
    monkeypatch.setattr(release, "PUBLIC_V01_TREE", release.text_git(repository.root, ["rev-parse", f"{first}^{{tree}}"]))
    checked = []
    monkeypatch.setattr(release, "validate_public_release_surface", lambda repo, version: checked.append(version))
    options = {"accepted_commit": release.PUBLIC_V01_COMMIT, "accepted_tree": release.PUBLIC_V01_TREE}
    with pytest.raises(release.ToolError, match="cannot follow untagged commits"):
        release.verify_public_release_lineage(repository, allow_advanced_head=True, **options)
    identities = release.verify_public_release_lineage(
        repository, allow_advanced_head=True, allow_interleaved_untagged=True, **options)
    assert [identity.version for identity in identities] == ["0.1.0", "0.11.0", "0.12.0"]
    assert checked == ["0.12.0"]
    assert v013.INTERLEAVED_UNTAGGED_VERSIONS == {"0.13.0"}


@pytest.mark.parametrize("version, interleaved", [("0.12.0", False), ("0.13.0", True)])
def test_untagged_builder_selects_lineage_policy_by_release(tmp_path, monkeypatch, version, interleaved):
    import apg_staging_correction as staging

    seen = {}

    def lineage(*_args, **kwargs):
        seen.update(kwargs)
        raise release.ToolError("stop after lineage")

    monkeypatch.setattr(release, "validate_repository_separation", lambda *_a: None)
    monkeypatch.setattr(release, "verify_public_release_lineage", lineage)
    with pytest.raises(release.ToolError, match="stop after lineage"):
        staging.build_untagged_candidate(object(), object(), tmp_path / "out", version)
    assert seen["allow_advanced_head"] is True
    assert seen["allow_interleaved_untagged"] is interleaved


def test_intentional_fixture_links_are_excluded_but_documentation_links_are_checked(tmp_path):
    root = tmp_path / "links"
    release.run_git(tmp_path, ["init", "-q", "-b", "main", str(root)])
    fixture = root / "testing/fixtures/context-eval/subjects/scenario-03"
    (fixture / "docs").mkdir(parents=True)
    (fixture / "docs/keep.txt").write_text("kept\n")
    (fixture / "README.md").write_text("See [architecture](docs/missing.md).\n")
    (root / "docs").mkdir()
    (root / "docs/ok.md").write_text("See [fixture](../testing/fixtures/context-eval/subjects/scenario-03/README.md).\n")
    for arguments in (["add", "."], ["-c", "user.name=T", "-c", "user.email=t@example.invalid",
                                     "commit", "-qm", "fixture"]):
        release.run_git(root, arguments)
    repository = release.resolve_repository(root, "link fixture")
    release.validate_markdown_links(repository)
    (root / "docs/bad.md").write_text("See [gone](gone.md).\n")
    release.run_git(root, ["add", "."])
    release.run_git(root, ["-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-qm", "bad"])
    with pytest.raises(release.ToolError, match="broken public Markdown link in docs/bad.md"):
        release.validate_markdown_links(release.resolve_repository(root, "link fixture"))


def test_v013_surface_requires_every_nix_runtime_authority_file():
    import subprocess

    distribution = json.loads((ROOT / "nix/distribution.json").read_text(encoding="utf-8"))
    names = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", *distribution["runtime"]],
                           capture_output=True, text=True, check=True).stdout.split()
    surface = release.audited_policy_surfaces("0.13.0")[0]
    owned = {path for values in surface.values() for path in values}
    missing = [name for name in names
               if not name.startswith(("bin/", "libexec/", "src/agentic_praxis_grimoire/"))
               and "/profiles/" not in name and name not in owned]
    assert missing == []


def test_public_pr_ci_documentation_matches_v013_ruff_baseline_contract():
    docs_path = ROOT / "docs/public-pr-ci.md"
    assert docs_path.is_file(), "docs/public-pr-ci.md must exist"
    content = docs_path.read_text(encoding="utf-8")

    # Contradictory pre-ZH/ZI phrases must not be present
    assert "No automatic debt baseline is accepted by this lane" not in content
    assert "An observed baseline does not grandfather them" not in content

    # Exact v0.13 grandfathering policy contracts must be present
    assert "No automatic baseline refresh or growth and no count-only\ndebt waiver is accepted." in content or \
           "No automatic baseline refresh or growth and no count-only debt waiver is accepted." in content.replace("\n", " ")
    assert f"exactly {v013.V013_RUFF_BASELINE_COUNT} reviewed pre-existing Ruff findings" in content
    assert f"under schema `{v013.V013_RUFF_BASELINE_SCHEMA}`" in content
    assert "source-derived context hash" in content
    assert "pinned by cryptographic digest, count, and provenance in the v0.13 release\nauthority" in content or \
           "pinned by cryptographic digest, count, and provenance in the v0.13 release authority" in content.replace("\n", " ")
    assert "New, moved, or content-changed findings fail closed" in content
    assert "finding reductions\npass without baseline edits" in content or \
           "finding reductions pass without baseline edits" in content.replace("\n", " ")
    assert "grandfathering of visible debt, not a claim\nthat the debt is fixed" in content or \
           "grandfathering of visible debt, not a claim that the debt is fixed" in content.replace("\n", " ")

    # Suppression inventory wording must be qualified to prevent conflation
    assert "An observed suppression baseline does not grandfather them" in content


COMPATIBILITY = dict.fromkeys((
    "allow_v07_compatibility", "allow_v08_compatibility", "allow_v09_compatibility",
    "allow_v010_compatibility", "allow_v011_compatibility",
), True)


def _policy_repository(tmp_path, version="0.13.0", mutation=None):
    policy = json.loads((ROOT / "release/public-surface.json").read_bytes())
    if version != "0.13.0":
        policy.update(release.audited_policy_surfaces(version)[0])
    if mutation:
        mutation(policy)
    root = tmp_path / "policy"
    release.run_git(tmp_path, ["init", "-q", "-b", "main", str(root)])
    path = root / "release/public-surface.json"
    path.parent.mkdir()
    path.write_text(json.dumps(policy))
    release.run_git(root, ["add", "."])
    release.run_git(root, ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                           "commit", "-qm", "policy fixture"])
    return release.resolve_repository(root, "policy fixture")


@pytest.mark.parametrize("policy_version, intended", [
    ("0.13.0", "0.13.0"), ("0.13.0", "0.12.0"),
    ("0.12.0", "0.12.0"), ("0.12.0", "0.13.0"),
])
def test_policy_admission_is_version_explicit(tmp_path, policy_version, intended):
    repository = _policy_repository(tmp_path, policy_version)
    kwargs = dict(expected_surfaces=release.audited_policy_surfaces(intended), **COMPATIBILITY)
    if policy_version == intended:
        loaded = release.load_policy(repository, **kwargs)
        assert all(tuple(loaded[k]) == v for k, v in release.audited_policy_surfaces(intended)[0].items())
    else:
        with pytest.raises(release.ToolError, match="required_helpers differs from the audited schema-1 surface"):
            release.load_policy(repository, **kwargs)


@pytest.mark.parametrize("version, prefix, expected", [
    ("0.11.0", "V011", "59cd6cbb16451d5142ffeab80870ddf184a8e72e018ee05fa1dff82b53066deb"),
    ("0.12.0", "V012", "1246fbd71c24fa54bd6d9e905df8c09920dfe8979f63a7b25c89430adedf939d"),
])
def test_published_policy_digest_is_pinned_and_drift_fails(monkeypatch, version, prefix, expected):
    assert _digest(release.audited_policy_surfaces(version)[0]) == expected
    assert release.PUBLISHED_SURFACE_SHA256[version] == expected
    monkeypatch.setattr(release, prefix + "_HELPERS", ())
    with pytest.raises(release.ToolError, match="historical public v" + version.replace(".", r"\.") + " policy surface changed"):
        release.audited_policy_surfaces(version)


@pytest.mark.parametrize("version", ["0.13.1", "0.14.0", "1.0.0"])
def test_future_release_is_refused_at_surface_and_candidate_boundaries(tmp_path, version):
    import apg_staging_correction as staging

    with pytest.raises(release.ToolError, match="malformed or unsupported"):
        release.audited_policy_surfaces(version)
    with pytest.raises(release.InvocationError, match="untagged candidate mode is only available"):
        staging.build_untagged_candidate(object(), object(), tmp_path / "out", version)


@pytest.mark.parametrize("version", ["0.6.0", "0.7.0", "0.8.0", "0.8.1", "0.9.0", "0.10.0", "0.11.0", "0.12.0"])
def test_current_release_cannot_fall_back_to_historical_policy(tmp_path, version):
    repository = _policy_repository(tmp_path, version)
    with pytest.raises(release.ToolError, match="differs from the audited schema-1 surface"):
        release.load_policy(repository, expected_surfaces=release.audited_policy_surfaces("0.13.0"), **COMPATIBILITY)


@pytest.mark.parametrize("mutation, message", [
    (lambda p: p["required_helpers"].pop(), "required_helpers differs from the audited schema-1 surface"),
    (lambda p: p.update(required_helpers=list(release.audited_policy_surfaces("0.12.0")[0]["required_helpers"])),
     "required_helpers differs from the audited schema-1 surface"),
    (lambda p: p.update(schema_version=2), "schema version is unsupported"),
])
def test_current_policy_mutation_and_mixed_surface_fail_closed(tmp_path, mutation, message):
    repository = _policy_repository(tmp_path, mutation=mutation)
    with pytest.raises(release.ToolError, match=message):
        release.load_policy(repository, expected_surfaces=release.audited_policy_surfaces("0.13.0"), **COMPATIBILITY)


def test_compatibility_rejects_cross_version_surface_mixture(tmp_path):
    repository = _policy_repository(tmp_path, "0.9.0", lambda p: p.update(
        required_helpers=list(release.audited_policy_surfaces("0.10.0")[0]["required_helpers"])))
    with pytest.raises(release.ToolError, match="combines incompatible audited schema-1 surfaces"):
        release.load_policy(repository, expected_surfaces=release.audited_policy_surfaces("0.9.0"),
                            allow_v010_compatibility=True)
