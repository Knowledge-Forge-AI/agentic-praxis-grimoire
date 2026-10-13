"""A qualified environment survives provider transport enrichment."""
import json
import os
from pathlib import Path
import sys

import pytest

from agent_phase import context_adapter, provider


@pytest.mark.parametrize("managed", [False, True])
def test_explicit_environment_never_merges_ambient_values(tmp_path, monkeypatch, managed):
    monkeypatch.setenv("APG_TEST_AMBIENT", "must-not-leak")
    monkeypatch.setattr(provider, "_is_managed_antigravity_launcher", lambda *_: managed)
    fake = tmp_path / "instrumented-environment"
    fake.write_text(f"#!{sys.executable}\nimport json,os,sys\n"
                    "sys.stdin.buffer.read()\n"
                    "print(json.dumps({k:v for k,v in os.environ.items() if k.startswith('APG_TEST_')}))\n")
    fake.chmod(0o700)

    class Transport:
        def environment(self, argv, environment):
            assert "APG_TEST_AMBIENT" not in environment
            return {**environment, "APG_TEST_TRANSPORT": "retained"}

        def process_started(self, argv):
            assert argv == [str(fake)]

        def wrote_stdin(self, payload):
            assert payload == b"fixture"

    token = context_adapter.ACTIVE_TRANSPORT.set(Transport())
    try:
        result = provider.run([str(fake)], b"fixture", tmp_path,
                              environment={"APG_TEST_BOUND": "retained"})
    finally:
        context_adapter.ACTIVE_TRANSPORT.reset(token)
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "APG_TEST_BOUND": "retained", "APG_TEST_TRANSPORT": "retained"}


def test_invalid_environment_is_rejected_before_process_start(tmp_path):
    with pytest.raises(TypeError, match="environment"):
        provider.run([str(tmp_path / "never-created")], b"", tmp_path,
                     environment={"BAD": object()})


def test_transport_environment_failure_closes_owned_activity_descriptors(monkeypatch):
    from agent_phase import provider_environment
    descriptors = os.pipe()
    monkeypatch.setattr(provider_environment.os, "pipe", lambda: descriptors)

    class BrokenTransport:
        def environment(self, argv, environment):
            raise ValueError("instrumented transport failure")

    with pytest.raises(ValueError, match="instrumented transport failure"):
        provider_environment.process_options([], {}, BrokenTransport(), managed=True,
                                             activity_key="APG_TEST_ACTIVITY")
    for descriptor in descriptors:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def test_managed_launcher_keeps_single_source_constant(monkeypatch):
    monkeypatch.setattr(provider, "ANTIGRAVITY_LAUNCHER", "bin/fixture-profile")
    root = Path(provider.__file__).resolve().parents[2]
    assert provider._is_managed_antigravity_launcher(["bin/fixture-profile"], root)
    assert not provider._is_managed_antigravity_launcher(["bin/antigravity-profile"], root)
