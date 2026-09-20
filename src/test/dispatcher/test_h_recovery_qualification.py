"""Provider-free recovery qualification against the real APGR acquisition engine."""
from __future__ import annotations

import copy
import hashlib
import os
import stat
import subprocess
from pathlib import Path

import pytest

from testing.h_eval import recovery_qualification as owner

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def apgr_binary(tmp_path_factory):
    configured = os.environ.get("APG_ACQUISITION_BINARY")
    if configured:
        path = Path(configured)
        assert path.is_file() and os.access(path, os.X_OK)
        return path
    target = tmp_path_factory.mktemp("h-recovery-apgr") / "apgr"
    result = subprocess.run(
        ["go", "build", "-o", str(target), "./cmd/apgr"],
        cwd=ROOT,
        capture_output=True,
        timeout=120,
        check=False,
        env={**os.environ, "GOPROXY": "off", "GOSUMDB": "off", "GOTOOLCHAIN": "local"},
    )
    assert result.returncode == 0, result.stderr.decode(errors="replace")
    return target


@pytest.fixture
def manifest_environment(tmp_path):
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    return {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "TMPDIR": str(tmp_path),
        "TMP": str(tmp_path),
        "TEMP": str(tmp_path),
        "LANG": "C",
        "LC_ALL": "C",
        "GOPROXY": "off",
        "GOSUMDB": "off",
        "GONOSUMDB": "*",
        "GOTOOLCHAIN": "local",
        "npm_config_offline": "true",
        "npm_config_prefer_offline": "true",
        "npm_config_audit": "false",
        "npm_config_fund": "false",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONNOUSERSITE": "1",
        "NO_PROXY": "*",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "ALL_PROXY": "",
    }


def qualify(apgr_binary, manifest_environment, destination):
    return owner.qualify_recovery(
        ROOT,
        destination,
        apgr_executable=apgr_binary,
        environment=manifest_environment,
        skill_id="apgr:go-language-profile",
    )


def test_real_mcp_recovery_is_idempotent_and_authority_bound(
    apgr_binary, manifest_environment, tmp_path
):
    destination = tmp_path / "recovery"
    result = qualify(apgr_binary, manifest_environment, destination)

    assert result["schema"] == owner.SCHEMA
    assert result["status"] == "complete"
    assert result["provider_free"] is True
    assert result["provider_invocations"] == 0
    assert result["model_invocations"] == 0
    assert result["network_policy"] == "configured_offline_not_os_enforced"
    assert result["network_disabled"] is False
    assert result["growth_policy"] == "immutable-pre-materialized"
    assert result["command"]["executable"] == str(apgr_binary.resolve())
    assert result["mcp"]["acquisition_repeats"] == [False, True]
    assert result["mcp"]["resource_read"] is True
    assert result["subtree"]["unchanged"] is True
    assert result["read_authority"]["status"] == "valid"
    assert result["stream_readback"]["status"] == "valid"
    assert {record["path"] for record in result["stream_custody"]} == {
        "recovery-custody/preparation.stdout",
        "recovery-custody/preparation.stderr",
        "recovery-custody/mcp.stdin",
        "recovery-custody/mcp.stdout",
        "recovery-custody/mcp.stderr",
    }
    for record in result["stream_custody"]:
        path = destination / record["path"]
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        raw = path.read_bytes()
        assert record["bytes"] == len(raw)
        assert record["sha256"] == hashlib.sha256(raw).hexdigest()
        assert "acquisitions" not in path.relative_to(destination).parts
    prelaunch = copy.deepcopy(result["prelaunch_authority"])
    assert result["recovery_authority"] == prelaunch
    assert result["postrun_readback"]["authority"] == prelaunch
    assert owner.verify_recovery_authority(destination, result)["status"] == "valid"
    assert owner.verify_stream_custody(destination, result)["status"] == "valid"


def test_source_launcher_prepare_only_recovery_matches_native_binary(
    apgr_binary, manifest_environment, tmp_path
):
    """The host binds the Python source launcher ``bin/apgr`` as ``apgr``.

    APG166V-H-COMPLETE1 scenario-12 failed with ``unrecognized arguments:
    --prepare-only`` because only the native binary accepted that shape.
    Both front ends must produce the same complete provider-free recovery.
    """
    launcher = ROOT / "bin/apgr"
    source = qualify(launcher, manifest_environment, tmp_path / "source-launcher")
    native = qualify(apgr_binary, manifest_environment, tmp_path / "native")

    assert source["status"] == "complete"
    assert source["command"]["executable"] == str(launcher.resolve())
    assert source["mcp"]["acquisition_repeats"] == [False, True]
    assert source["mcp"]["resource_read"] is True
    assert source["subtree"]["unchanged"] is True
    assert source["materialized_path"] == native["materialized_path"]
    assert owner.verify_recovery_authority(tmp_path / "source-launcher", source)["status"] == "valid"
    assert owner.verify_stream_custody(tmp_path / "source-launcher", source)["status"] == "valid"
    stderr = (tmp_path / "source-launcher/recovery-custody/preparation.stderr").read_bytes()
    assert b"unrecognized arguments" not in stderr


def test_stream_custody_tamper_fails_readback_without_mutating_prelaunch(
    apgr_binary, manifest_environment, tmp_path
):
    destination = tmp_path / "recovery"
    result = qualify(apgr_binary, manifest_environment, destination)
    prelaunch = copy.deepcopy(result["prelaunch_authority"])
    target = destination / "recovery-custody/mcp.stdin"
    target.write_bytes(target.read_bytes() + b"tamper")

    with pytest.raises(owner.RecoveryQualificationError):
        owner.verify_stream_custody(destination, result)
    assert result["prelaunch_authority"] == prelaunch
    assert result["postrun_readback"]["authority"] == prelaunch


@pytest.mark.parametrize("mutation", ["directory", "support", "bytes"])
def test_recovery_authority_rejects_subtree_growth_and_byte_drift(
    apgr_binary, manifest_environment, tmp_path, mutation
):
    destination = tmp_path / "recovery"
    result = qualify(apgr_binary, manifest_environment, destination)
    materialized = destination / result["materialized_path"]
    if mutation == "directory":
        (materialized / "unexpected").mkdir()
    elif mutation == "support":
        (materialized / "unexpected-support.txt").write_bytes(b"unexpected")
    else:
        body = materialized / "SKILL.md"
        body.write_bytes(body.read_bytes() + b"\nchanged")

    with pytest.raises(owner.RecoveryQualificationError):
        owner.verify_recovery_authority(destination, result)


def test_recovery_requires_explicit_manifest_environment(apgr_binary, tmp_path):
    with pytest.raises(owner.RecoveryQualificationError):
        owner.qualify_recovery(
            ROOT,
            tmp_path / "recovery",
            apgr_executable=apgr_binary,
            environment={},
        )


def test_recovery_rejects_ambient_network_policy(
    apgr_binary, manifest_environment, tmp_path
):
    manifest_environment["GOPROXY"] = "https://proxy.invalid"
    with pytest.raises(owner.RecoveryQualificationError):
        owner.qualify_recovery(
            ROOT,
            tmp_path / "recovery",
            apgr_executable=apgr_binary,
            environment=manifest_environment,
        )


def test_recovery_rejects_path_traversal_skill_identity(apgr_binary, manifest_environment, tmp_path):
    destination = tmp_path / "recovery"
    with pytest.raises(owner.RecoveryQualificationError):
        owner.qualify_recovery(
            ROOT,
            destination,
            apgr_executable=apgr_binary,
            environment=manifest_environment,
            skill_id="apgr:../../go-language-profile",
        )
    assert not destination.exists()
