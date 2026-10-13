"""Unit contracts for APGR declarative configuration precedence."""

from __future__ import annotations

from pathlib import Path
import hashlib
import sys

import pytest

from src.test.apg_test_support import repository_root


ROOT = repository_root(__file__)
sys.path.insert(0, str(ROOT / "src"))

from agentic_praxis_grimoire import config  # noqa: E402


def write_config(path: Path, outbox_root: Path) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(f'outbox_root = "{outbox_root}"\n', encoding="utf-8")


def test_outbox_root_precedence_is_explicit_project_global_default(
    tmp_path: Path,
) -> None:
    global_home = tmp_path / "global"
    project_root = tmp_path / "project"
    global_value = tmp_path / "global-outbox"
    project_value = tmp_path / "project-outbox"
    explicit_value = tmp_path / "explicit-outbox"
    write_config(global_home / "config.toml", global_value)
    write_config(project_root / ".apgr" / "config.toml", project_value)

    assert (
        config.resolve_outbox_root(
            apgr_home=global_home,
            project_root=project_root,
        )
        == project_value
    )
    assert (
        config.resolve_outbox_root(
            apgr_home=global_home,
            project_root=project_root,
            explicit=explicit_value,
        )
        == explicit_value
    )
    assert (
        config.resolve_outbox_root(apgr_home=global_home)
        == global_value
    )
    assert (
        config.resolve_outbox_root(
            apgr_home=tmp_path / "missing-global",
            home=tmp_path / "operator-home",
        )
        == tmp_path / "operator-home" / "Documents" / "agent" / "outbox"
    )


def test_project_root_discovery_stops_at_the_nearest_git_worktree(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    nested = repository / "src" / "nested"
    nested.mkdir(parents=True)
    (repository / ".git").mkdir()
    unrelated = tmp_path / ".git"
    unrelated.mkdir()
    assert config.discover_project_root(nested) == repository
    explicit = tmp_path / "synthetic"
    explicit.mkdir()
    assert config.discover_project_root(explicit=explicit) == explicit


def test_config_rejects_relative_or_unknown_outbox_values(tmp_path: Path) -> None:
    relative = tmp_path / "relative" / "config.toml"
    relative.parent.mkdir()
    relative.write_text('outbox_root = "reports"\n', encoding="utf-8")
    with pytest.raises(config.ConfigError, match="absolute"):
        config.load_config(relative)

    unknown = tmp_path / "unknown" / "config.toml"
    unknown.parent.mkdir()
    unknown.write_text('unexpected = "value"\n', encoding="utf-8")
    with pytest.raises(config.ConfigError, match="unsupported"):
        config.load_config(unknown)


@pytest.mark.parametrize("control", ("\\u0000", "\\u001f", "\\u007f"))
def test_config_rejects_control_bearing_outbox_paths(
    tmp_path: Path, control: str
) -> None:
    path = tmp_path / "control.toml"
    path.write_text(
        f'outbox_root = "{tmp_path}/unsafe{control}path"\n', encoding="utf-8"
    )

    with pytest.raises(config.ConfigError, match="control character"):
        config.load_config(path)


@pytest.mark.parametrize(
    "body,diagnostic",
    (
        ("outbox_root = 7\n", "non-empty string"),
        ("outbox_root = \"\"\n", "non-empty string"),
        ("outbox_root = [\n", "could not read"),
    ),
)
def test_config_rejects_invalid_toml_shapes(
    tmp_path: Path, body: str, diagnostic: str
) -> None:
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(config.ConfigError, match=diagnostic):
        config.load_config(path)


def test_config_absence_symlink_and_resolved_structure(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"
    assert config.load_config(missing) == {}
    target = tmp_path / "target.toml"
    target.write_text(f'outbox_root = "{tmp_path / "outbox"}"\n', encoding="utf-8")
    link = tmp_path / "link.toml"
    link.symlink_to(target)
    with pytest.raises(config.ConfigError, match="ordinary file"):
        config.load_config(link)
    dangling = tmp_path / "dangling.toml"
    dangling.symlink_to(tmp_path / "absent-target.toml")
    with pytest.raises(config.ConfigError, match="ordinary file"):
        config.load_config(dangling)
    assert config.resolved_configuration(
        explicit=tmp_path / "explicit", apgr_home=tmp_path / "home"
    ) == {"outbox_root": tmp_path / "explicit"}


def test_start_discovers_project_configuration(tmp_path: Path) -> None:
    project = tmp_path / "project"
    nested = project / "nested"
    nested.mkdir(parents=True)
    (project / ".git").mkdir()
    selected = tmp_path / "selected"
    write_config(project / ".apgr" / "config.toml", selected)
    assert config.resolve_outbox_root(
        start=nested, apgr_home=tmp_path / "missing-home"
    ) == selected


@pytest.mark.parametrize("body, diagnostic", (
    ('dispatcher = "command"', "dispatcher configuration must be a TOML table"),
    ('[dispatcher]\ncommand = "run"', "unsupported dispatcher configuration key"),
    ('[dispatcher]\nrouting = []', "dispatcher.routing configuration must be a TOML table"),
    ('[dispatcher.routing]\nprovider = "custom"', "unsupported routing configuration key"),
    ('[dispatcher.routing]\nexecution_mode = 7', "execution_mode must be a non-empty string"),
    ('[dispatcher.routing]\nexecution_mode = ""', "execution_mode must be a non-empty string"),
    ('[dispatcher.routing]\nexecution_mode = "unknown"', "unsupported execution_mode"),
))
def test_routing_schema_refuses_invalid_values(tmp_path, body, diagnostic):
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(config.ConfigError, match=diagnostic):
        config.load_config(path)


@pytest.mark.parametrize("body", ("", "[dispatcher]", "[dispatcher.routing]"))
def test_empty_optional_routing_tables_fall_through(tmp_path, body):
    project = tmp_path / "project"
    project_config = project / ".apgr/config.toml"
    project_config.parent.mkdir(parents=True)
    project_config.write_text(body, encoding="utf-8")
    global_home = tmp_path / "global"
    global_home.mkdir()
    global_config = global_home / "config.toml"
    global_config.write_text(body, encoding="utf-8")

    result = config.resolve_execution_mode(project_root=project, apgr_home=global_home)
    assert result.execution_mode == "dynamic"
    assert result.winner.source_type == "default"
    assert [item.source_type for item in result.provenance_chain] == [
        "project_config", "global_config", "default"
    ]
    assert [item.is_winner for item in result.provenance_chain] == [False, False, True]
    assert [item.precedence_rank for item in result.provenance_chain] == [2, 3, 4]
    for item, path in zip(result.provenance_chain, (project_config, global_config)):
        assert item.resolved_mode == ""
        assert item.source_path == str(path)
        assert item.content_digest == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("mode", config.ROUTING_MODES)
def test_supported_modes_have_explicit_and_file_provenance(tmp_path, mode):
    project = tmp_path / "project"
    path = project / ".apgr/config.toml"
    path.parent.mkdir(parents=True)
    path.write_text(f'[dispatcher.routing]\nexecution_mode = "{mode}"\n', encoding="utf-8")
    assert config.load_config(path) == {"dispatcher": {"routing": {"execution_mode": mode}}}
    # A project winner prevents a malformed lower-precedence config from being read.
    global_home = tmp_path / "global"
    global_home.mkdir()
    (global_home / "config.toml").write_text("malformed = [", encoding="utf-8")
    result = config.resolve_execution_mode(project_root=project, apgr_home=global_home)
    assert result.execution_mode == mode
    assert result.provenance_chain == (result.winner,)
    assert result.winner.as_dict() == {
        "source_type": "project_config", "source_path": str(path),
        "content_digest": hashlib.sha256(path.read_bytes()).hexdigest(),
        "resolved_mode": mode, "is_winner": True, "precedence_rank": 2,
    }
    path.write_text("also malformed = [", encoding="utf-8")
    explicit = config.resolve_execution_mode(mode, project_root=project, apgr_home=global_home)
    assert explicit.execution_mode == mode
    assert explicit.provenance_chain == (explicit.winner,)
    assert explicit.winner.as_dict() == {
        "source_type": "cli", "source_path": None, "content_digest": None,
        "resolved_mode": mode, "is_winner": True, "precedence_rank": 1,
    }


def test_routing_global_winner_discovery_and_home_aliases(tmp_path):
    project = tmp_path / "project"
    nested = project / "nested"
    nested.mkdir(parents=True)
    (project / ".git").mkdir()
    path = project / ".apgr/config.toml"
    path.parent.mkdir()
    path.write_text("[dispatcher.routing]\n", encoding="utf-8")
    global_home = tmp_path / "global"
    global_home.mkdir()
    global_config = global_home / "config.toml"
    global_config.write_text('[dispatcher.routing]\nexecution_mode = "codex_only"\n', encoding="utf-8")
    for alias in ("cli_home", "apgr_home", "global_home"):
        result = config.resolve_execution_mode(start=nested, **{alias: global_home})
        assert result.execution_mode == "codex_only"
        assert [item.is_winner for item in result.provenance_chain] == [False, True]
        assert result.winner.as_dict() == {
            "source_type": "global_config", "source_path": str(global_config),
            "content_digest": hashlib.sha256(global_config.read_bytes()).hexdigest(),
            "resolved_mode": "codex_only", "is_winner": True, "precedence_rank": 3,
        }
    path.unlink()
    assert config.resolve_execution_mode(project_root=project, cli_home=global_home,
        apgr_home=tmp_path / "ignored", global_home=tmp_path / "also-ignored").execution_mode == "codex_only"
    global_config.unlink()
    result = config.resolve_execution_mode(project_root=project, apgr_home=global_home)
    assert result.provenance_chain == (result.winner,)
    assert result.winner.source_type == "default"


def test_invalid_explicit_mode_and_malformed_project_do_not_fall_back(tmp_path):
    with pytest.raises(config.ConfigError, match="unsupported execution_mode"):
        config.resolve_execution_mode("unknown")
    path = tmp_path / ".apgr/config.toml"
    path.parent.mkdir()
    path.write_text('[dispatcher.routing]\nexecution_mode = "unknown"\n', encoding="utf-8")
    with pytest.raises(config.ConfigError, match="unsupported execution_mode"):
        config.resolve_execution_mode(project_root=tmp_path, apgr_home=tmp_path / "global")


def test_empty_project_config_preserves_global_outbox_and_binary_path_is_refused(tmp_path):
    project = tmp_path / "project"
    path = project / ".apgr/config.toml"
    path.parent.mkdir(parents=True)
    path.write_text("[dispatcher]\n", encoding="utf-8")
    global_home = tmp_path / "global"
    value = tmp_path / "outbox"
    write_config(global_home / "config.toml", value)
    assert config.resolve_outbox_root(project_root=project, global_home=global_home) == value
    with pytest.raises(config.ConfigError, match="not a valid path"):
        config.load_config(b"/binary-path")


def test_skill_overrides_closed_table(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[skills.overrides]\n"apgr:go-language-profile" = "project:go-language-profile"\n')
    assert config.load_config(path)["skills"]["overrides"] == {
        "apgr:go-language-profile": "project:go-language-profile"
    }
    for text in ('[skills]\ncontext = true\n', '[skills]\noverrides = 1\n', '[skills.overrides]\nx = 1\n'):
        path.write_text(text)
        with pytest.raises(config.ConfigError):
            config.load_config(path)


def _loaded(tmp_path, body):
    path = tmp_path / "config.toml"
    path.write_text(body, encoding="utf-8")
    return config.load_config(path)


def test_dispatcher_tables_round_trip_only_their_declared_values(tmp_path):
    body = """
[dispatcher.bundle]
required = true
[dispatcher.observations]
enabled = false
[dispatcher.review_mutation]
worktree = "warn"
index = "block"
head = "block"
[dispatcher.context]
mode = "adaptive"
instructions = "projected"
manifest_facts = true
max_initial_context_bytes = 0
max_initial_context_characters = 4096
skills = ["apgr:go-language-profile", {id = "project:local-skill", required = true, stages = ["plan", "work"]}]
[dispatcher.context.facts]
language = ["go", "python"]
test_framework = ["pytest"]
"""
    dispatcher = _loaded(tmp_path, body)["dispatcher"]
    assert dispatcher["bundle"] == {"required": True}
    assert dispatcher["observations"] == {"enabled": False}
    assert dispatcher["review_mutation"] == {"worktree": "warn", "index": "block", "head": "block"}
    assert dispatcher["context"]["skills"][1] == {"id": "project:local-skill", "required": True,
                                                  "stages": ["plan", "work"]}
    assert dispatcher["context"]["facts"] == {"language": ["go", "python"], "test_framework": ["pytest"]}
    assert _loaded(tmp_path, "[dispatcher.review_mutation]\n") == {"dispatcher": {"review_mutation": {}}}


@pytest.mark.parametrize("body, diagnostic", (
    ("[dispatcher]\nbundle = 1", "supports only required"),
    ("[dispatcher.bundle]\nrequired = 1", "bundle.required must be a boolean"),
    ("[dispatcher.bundle]\nother = true", "supports only required"),
    ("[dispatcher]\nobservations = 1", "supports only enabled"),
    ("[dispatcher.observations]\nenabled = \"yes\"", "observations.enabled must be a boolean"),
    ("[dispatcher]\ncontext = 1", "dispatcher.context must be a table"),
    ("[dispatcher.context]\nunknown = 1", "unsupported dispatcher.context key"),
    ("[dispatcher.context]\nmode = \"dynamic\"", "must be static or adaptive"),
    ("[dispatcher.context]\nmax_initial_context_bytes = -1", "non-negative integers"),
    ("[dispatcher.context]\nmax_initial_context_characters = true", "non-negative integers"),
    ("[dispatcher.context]\nmanifest_facts = 1", "manifest_facts must be a boolean"),
    ("[dispatcher.context]\ninstructions = \"inline\"", "projected or static"),
    ("[dispatcher.context]\nskills = \"apgr:x\"", "at most 64 entries"),
    ("[dispatcher.context]\nskills = [" + ", ".join(f'"apgr:s{i}"' for i in range(65)) + "]", "at most 64 entries"),
    ("[dispatcher.context]\nskills = [1]", "an ID or a table"),
    ("[dispatcher.context]\nskills = [{required = true}]", "an ID or a table"),
    ("[dispatcher.context]\nskills = [{id = \"apgr:x\", why = 1}]", "an ID or a table"),
    ("[dispatcher.context]\nskills = [{id = 7}]", "invalid qualified skill ID"),
    ("[dispatcher.context]\nskills = [\"vendor:x\"]", "invalid qualified skill ID"),
    ("[dispatcher.context]\nskills = [{id = \"apgr:x\", required = 1}]", "required must be a boolean"),
    ("[dispatcher.context]\nskills = [{id = \"apgr:x\", stages = []}]", "non-empty subset"),
    ("[dispatcher.context]\nskills = [{id = \"apgr:x\", stages = \"plan\"}]", "non-empty subset"),
    ("[dispatcher.context]\nskills = [{id = \"apgr:x\", stages = [\"plan\", \"plan\"]}]", "non-empty subset"),
    ("[dispatcher.context]\nskills = [{id = \"apgr:x\", stages = [\"deploy\"]}]", "non-empty subset"),
    ("[dispatcher.context]\nskills = [\"apgr:x\", {id = \"apgr:x\"}]", "duplicate dispatcher.context.skills"),
    ("[dispatcher.context]\nfacts = []", "facts must be a table"),
    ("[dispatcher.context.facts]\nwork_class = [\"x\"]", "dispatcher-owned"),
    ("[dispatcher.context.facts]\nmood = [\"x\"]", "unsupported dispatcher.context.facts kind"),
    ("[dispatcher.context.facts]\nlanguage = \"go\"", "distinct lowercase fact values"),
    ("[dispatcher.context.facts]\nlanguage = [\"Go\"]", "distinct lowercase fact values"),
    ("[dispatcher.context.facts]\nlanguage = [1]", "distinct lowercase fact values"),
    ("[dispatcher.context.facts]\nlanguage = [\"go\", \"go\"]", "distinct lowercase fact values"),
    ("[dispatcher.context.facts]\nlanguage = [" + ", ".join(f'"l{i}"' for i in range(33)) + "]",
     "distinct lowercase fact values"),
    ("[dispatcher]\nreview_mutation = 1", "review_mutation configuration must be a TOML table"),
    ("[dispatcher.review_mutation]\nstage = \"block\"", "unsupported review_mutation configuration key"),
    ("[dispatcher.review_mutation]\nworktree = \"ignore\"", "unsupported worktree review mutation policy"),
    ("[dispatcher.review_mutation]\nworktree = 1", "unsupported worktree review mutation policy"),
    ("[dispatcher.review_mutation]\nindex = \"warn\"", "index review mutation policy must be 'block'"),
    ("[dispatcher.review_mutation]\nindex = 1", "index review mutation policy must be 'block'"),
    ("[dispatcher.review_mutation]\nhead = \"allow\"", "head review mutation policy must be 'block'"),
    ("[dispatcher.review_mutation]\nhead = false", "head review mutation policy must be 'block'"),
))
def test_dispatcher_tables_refuse_unsupported_values(tmp_path, body, diagnostic):
    with pytest.raises(config.ConfigError, match=diagnostic):
        _loaded(tmp_path, body)


def test_rtk_integration_round_trips_the_declared_optional_contract(tmp_path):
    body = """
[integrations.rtk]
enabled = true
executable = "/opt/rtk/bin/rtk"
required = false
minimum_version = " 0.9.0 "
[integrations.rtk.providers]
claude = "hook"
codex = "instructions"
antigravity = "off"
"""
    assert _loaded(tmp_path, body) == {"integrations": {"rtk": {
        "enabled": True, "executable": Path("/opt/rtk/bin/rtk"), "required": False,
        "minimum_version": "0.9.0",
        "providers": {"claude": "hook", "codex": "instructions", "antigravity": "off"},
    }}}
    assert _loaded(tmp_path, "[integrations.rtk]\n") == {"integrations": {"rtk": {}}}
    assert _loaded(tmp_path, "[integrations]\n") == {}


@pytest.mark.parametrize("body, diagnostic", (
    ("integrations = 1", "integrations configuration must be a TOML table"),
    ("[integrations.other]\nx = 1", "unsupported integrations configuration key"),
    ("[integrations]\nrtk = 1", "integrations.rtk configuration must be a TOML table"),
    ("[integrations.rtk]\nmode = 1", "unsupported integrations.rtk configuration key"),
    ("[integrations.rtk]\nenabled = \"yes\"", "enabled must be a boolean"),
    ("[integrations.rtk]\nexecutable = \" \"", "executable must be a non-empty string"),
    ("[integrations.rtk]\nexecutable = 1", "executable must be a non-empty string"),
    ("[integrations.rtk]\nexecutable = \"~/bin/rtk\"", "cannot use ~ interpolation"),
    ("[integrations.rtk]\nexecutable = \"$HOME/bin/rtk\"", "cannot use variable interpolation"),
    ("[integrations.rtk]\nexecutable = \"/bin/rtk\\u0007\"", "contains a control character"),
    ("[integrations.rtk]\nexecutable = \"bin/rtk\"", "must be an absolute path"),
    ("[integrations.rtk]\nrequired = 1", "required must be a boolean"),
    ("[integrations.rtk]\nrequired = true", "required=true is deferred"),
    ("[integrations.rtk]\nminimum_version = \"\"", "minimum_version must be a non-empty string"),
    ("[integrations.rtk]\nminimum_version = 1", "minimum_version must be a non-empty string"),
    ("[integrations.rtk]\nproviders = 1", "providers configuration must be a TOML table"),
    ("[integrations.rtk.providers]\ngemini = \"hook\"", "unsupported integrations.rtk.providers key"),
    ("[integrations.rtk.providers]\nclaude = \"always\"", "providers.claude mode"),
    ("[integrations.rtk.providers]\ncodex = 1", "providers.codex mode"),
    ("[integrations.rtk.providers]\nantigravity = \"proxy\"", "providers.antigravity mode"),
))
def test_rtk_integration_refuses_unsupported_values(tmp_path, body, diagnostic):
    with pytest.raises(config.ConfigError, match=diagnostic):
        _loaded(tmp_path, body)


def test_load_config_decodes_supplied_bytes_and_reports_unreadable_paths(tmp_path, monkeypatch):
    path = tmp_path / "config.toml"
    path.write_text('outbox_root = "/ignored"\n', encoding="utf-8")
    assert config.load_config(path, raw_bytes=b'outbox_root = "/supplied"\n') == {"outbox_root": Path("/supplied")}
    with pytest.raises(config.ConfigError, match="could not read"):
        config.load_config(path, raw_bytes=b"\xff")
    with pytest.raises(config.ConfigError, match="not an ordinary file"):
        config.load_config(tmp_path)

    def refused(self):
        raise PermissionError(self)

    monkeypatch.setattr(Path, "lstat", refused)
    with pytest.raises(config.ConfigError, match="could not inspect configuration"):
        config.load_config(path)
