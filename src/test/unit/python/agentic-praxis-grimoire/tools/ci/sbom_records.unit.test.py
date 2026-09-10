"""Unit tests for SBOM generation policy and Grype vulnerability controls."""

from __future__ import annotations

import json
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import subprocess
import tarfile
import zipfile

import pytest

from tools.ci.sbom_records import (
    ScanError,
    _coverage_union,
    _grype_document,
    _conditional_policy,
    _scan_conditional_dependency,
    _database_identity,
    _ecosystems,
    _install_sdist,
    _scan_record,
    _parse_checksums,
    _scan_status,
    _verify_conditional_receipt,
    validate_grype_report,
)
from tools.ci.workflow_model import parse_yaml_or_json

ROOT = Path(__file__).resolve().parents[7]


def _database_policy() -> dict[str, object]:
    return {
        "scan": {
            "scanner": {
                "database": {
                    "relative_path": "db/6/vulnerability.db",
                    "identity_file": "database-identity.json",
                    "last_update_check": "db/6/last_update_check",
                    "max_age_hours": 120,
                    "require_update_check": True,
                }
            }
        }
    }


def _database_runner(
    scanner_root: Path,
    now: datetime,
    *,
    built: datetime | None = None,
    update_returncode: int = 0,
) -> tuple[list[list[str]], object]:
    calls: list[list[str]] = []
    database = scanner_root / "db/6/vulnerability.db"
    built = built or now

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        if command[1:3] == ["db", "update"]:
            if update_returncode == 0:
                database.parent.mkdir(parents=True, exist_ok=True)
                database.write_bytes(b"fresh database")
            return subprocess.CompletedProcess(
                command, update_returncode, b"database updated\n", b""
            )
        status = {
            "schemaVersion": "v6.1.9",
            "built": built.isoformat(),
            "path": str(database),
            "valid": True,
        }
        return subprocess.CompletedProcess(
            command, 0, json.dumps(status).encode("utf-8"), b""
        )

    return calls, runner


def _conditional_runner(
    output: Path,
    *,
    sbom_artifacts: list[dict[str, object]] | None = None,
    metadata_name: str = "tomli",
    metadata_version: str = "2.0.1",
) -> tuple[list[list[str]], object]:
    calls: list[list[str]] = []
    if sbom_artifacts is None:
        sbom_artifacts = [
            {
                "type": "python",
                "name": "tomli",
                "version": "2.0.1",
                "purl": "pkg:pypi/tomli@2.0.1",
                "foundBy": "python-installed-package-cataloger",
            }
        ]

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        if command[1:4] == ["-m", "pip", "download"]:
            download = Path(command[command.index("--dest") + 1])
            wheel = download / "tomli-2.0.1-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("tomli/__init__.py", "__version__ = '2.0.1'\n")
                archive.writestr(
                    "tomli-2.0.1.dist-info/METADATA",
                    "Metadata-Version: 2.1\nName: tomli\nVersion: 2.0.1\n",
                )
                archive.writestr(
                    "tomli-2.0.1.dist-info/WHEEL",
                    "Wheel-Version: 1.0\nTag: py3-none-any\n",
                )
            return subprocess.CompletedProcess(command, 0, b"downloaded", b"")
        if command[1:4] == ["-m", "pip", "install"]:
            site = Path(command[command.index("--target") + 1])
            wheel = next(Path(command[command.index("--find-links") + 1]).glob("*.whl"))
            with zipfile.ZipFile(wheel) as archive:
                archive.extractall(site)
            metadata = site / "tomli-2.0.1.dist-info/METADATA"
            metadata.write_text(
                f"Metadata-Version: 2.1\nName: {metadata_name}\nVersion: {metadata_version}\n",
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, b"installed", b"")
        if command[1] == "scan":
            sbom_path = Path(
                next(item[10:] for item in command if item.startswith("syft-json="))
            )
            sbom_path.write_text(
                json.dumps({"artifacts": sbom_artifacts, "files": []}),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, b"scanned", b"")
        if command[1].startswith("sbom:"):
            grype_path = Path(command[command.index("--file") + 1])
            grype_path.write_text(
                json.dumps(
                    {
                        "descriptor": {"version": "0.118.0"},
                        "matches": [],
                    }
                ),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, b"scanned", b"")
        raise AssertionError(command)

    return calls, runner


def test_sbom_policy_targets_and_ecosystems() -> None:
    policy_path = ROOT / "release/ci/sbom_policy.json"
    assert policy_path.is_file()

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    assert policy.get("schema") == "apg-sbom-policy-v1"

    targets = policy["targets"]
    assert "source" in targets
    assert targets["source"]["output_format"] == "spdx-json"

    deliverables = targets["deliverables"]
    assert "python" in deliverables
    assert "native_binaries" in deliverables

    # Native binaries cover darwin/arm64, linux/amd64, linux/arm64
    bin_targets = deliverables["native_binaries"]["targets"]
    platforms = {(t["os"], t["arch"]) for t in bin_targets}
    assert ("darwin", "arm64") in platforms
    assert ("linux", "amd64") in platforms
    assert ("linux", "arm64") in platforms

    # The scanner consumes one coverage policy; Python has a separate receipt.
    assert "coverage" not in policy
    coverage = policy["scan"]["coverage"]
    assert set(coverage["required_source_types"]) == {"go-module", "npm"}
    assert coverage["conditional_dependency_inventory"]["required_types"] == ["python"]
    assert coverage["record_digests"] is True
    assert "**/__pycache__/**" in policy["scan"]["source"]["exclude"]


def test_conditional_dependency_policy_is_a_separate_python310_receipt() -> None:
    policy = json.loads(
        (ROOT / "release/ci/sbom_policy.json").read_text(encoding="utf-8")
    )
    conditional = policy["scan"]["coverage"]["conditional_dependency_inventory"]
    assert conditional == {
        "path": "tools/ci/dependency_inventory.py",
        "inventory": "runtime",
        "source": "pyproject.toml",
        "target_python": "3.10",
        "required_package": "tomli",
        "required_types": ["python"],
    }
    assert _conditional_policy(policy) == conditional


def _scan_conditional_fixture(
    tmp_path: Path,
    *,
    sbom_artifacts: list[dict[str, object]] | None = None,
    metadata_name: str = "tomli",
    metadata_version: str = "2.0.1",
) -> tuple[dict[str, object], list[list[str]]]:
    output = tmp_path / "sbom-output"
    output.mkdir()
    installer = tmp_path / "python"
    installer.write_bytes(b"python")
    installer.chmod(0o755)
    syft = tmp_path / "syft"
    syft.write_bytes(b"syft")
    grype = tmp_path / "grype"
    grype.write_bytes(b"grype")
    policy = json.loads(
        (ROOT / "release/ci/sbom_policy.json").read_text(encoding="utf-8")
    )
    calls, runner = _conditional_runner(
        output,
        sbom_artifacts=sbom_artifacts,
        metadata_name=metadata_name,
        metadata_version=metadata_version,
    )
    result = _scan_conditional_dependency(
        ROOT,
        output,
        syft=syft,
        syft_config=None,
        grype=grype,
        grype_config=None,
        environment={},
        policy=policy,
        redact=(),
        installer_python=installer,
        runner=runner,
    )
    return result, calls


def test_conditional_dependency_scan_binds_view_and_exact_grype_input(
    tmp_path: Path,
) -> None:
    result, calls = _scan_conditional_fixture(tmp_path)

    assert result["status"] == "passed"
    assert result["target"] == "conditional-runtime/python-3.10"
    assert result["source"]["requirement"] == "tomli==2.0.1"
    assert result["source"]["marker"] == "python_version < '3.11'"
    assert len(result["source"]["source_sha256"]) == 64
    assert len(result["view"]["wheel"]["sha256"]) == 64
    assert len(result["view"]["metadata"]["sha256"]) == 64
    assert result["sbom"]["package"]["name"] == "tomli"
    assert result["grype"]["input_sbom_sha256"] == result["sbom"]["sha256"]
    assert result["receipt"]["path"].endswith("receipt.json")
    receipt = _verify_conditional_receipt(
        tmp_path / "sbom-output" / result["receipt"]["path"],
        result["receipt"]["sha256"],
    )
    assert receipt["schema"] == "apg-conditional-sbom-receipt-v1"
    assert calls[0][1:4] == ["-m", "pip", "download"]
    assert calls[1][1:4] == ["-m", "pip", "install"]
    assert "--no-deps" in calls[0] and "--no-deps" in calls[1]
    assert any(command[1] == "scan" for command in calls)
    assert any(command[1].startswith("sbom:") for command in calls)


def test_conditional_dependency_missing_receipt_is_blocking(tmp_path: Path) -> None:
    with pytest.raises(ScanError, match="conditional dependency receipt is unavailable"):
        _verify_conditional_receipt(tmp_path / "missing-receipt.json")


def test_conditional_dependency_metadata_substitution_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ScanError, match="metadata was substituted"):
        _scan_conditional_fixture(tmp_path, metadata_name="other-package")


def test_conditional_dependency_absent_from_sbom_is_a_coverage_gap(tmp_path: Path) -> None:
    with pytest.raises(ScanError, match="conditional dependency is absent"):
        _scan_conditional_fixture(
            tmp_path,
            sbom_artifacts=[
                {
                    "type": "python",
                    "name": "other-package",
                    "version": "1.0.0",
                    "purl": "pkg:pypi/other-package@1.0.0",
                }
            ],
        )


def test_grype_vulnerability_configuration() -> None:
    grype_path = ROOT / "release/ci/grype.yaml"
    assert grype_path.is_file()

    cfg = parse_yaml_or_json(grype_path.read_text(encoding="utf-8"))
    # High and critical must fail
    assert cfg.get("fail-on-severity") == "high"

    # Only-fixed must be false (no ignore-unfixed)
    assert cfg.get("only-fixed") is False
    assert cfg["db"]["require-update-check"] is True
    assert cfg["db"]["validate-by-hash-on-start"] is True
    assert cfg["db"]["max-allowed-built-age"] == "120h0m0s"

    # Ignore list must exist (narrow expiring exceptions)
    ignore = cfg.get("ignore", [])
    assert isinstance(ignore, list)

    # Any exception must have valid future expiration date
    now = datetime.now(timezone.utc)
    for entry in ignore:
        assert "vulnerability" in entry
        assert "expires" in entry
        exp_dt = datetime.fromisoformat(entry["expires"].replace("Z", "+00:00"))
        assert exp_dt > now, f"Expired waiver detected for {entry['vulnerability']}"


def test_database_update_provisions_cache_and_ignores_stale_sidecar(
    tmp_path: Path,
) -> None:
    scanner_root = tmp_path / "scanners"
    scanner_root.mkdir()
    grype = scanner_root / "grype"
    grype.write_bytes(b"grype")
    now = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)
    (scanner_root / "database-identity.json").write_text(
        json.dumps(
            {
                "database_sha256": "old-digest",
                "valid": True,
                "update_receipt": {"exit_code": 0},
            }
        ),
        encoding="utf-8",
    )
    calls, runner = _database_runner(scanner_root, now)
    environment: dict[str, str] = {}

    result = _database_identity(
        scanner_root,
        grype,
        scanner_root / "grype-task.yaml",
        {},
        _database_policy(),
        environment,
        now=now,
        runner=runner,
    )

    assert (scanner_root / "db").is_dir()
    assert environment["GRYPE_DB_CACHE_DIR"] == str(scanner_root / "db")
    assert [command[1:3] for command in calls] == [["db", "update"], ["db", "status"]]
    assert all("--config" in command for command in calls)
    assert result["update"] == {
        "command": ["db", "update"],
        "returncode": 0,
        "status": "passed",
        "stdout_present": True,
        "stderr_present": False,
    }
    assert result["update_check"] == "command-observed"
    assert result["identity_validated"] is False
    assert result["database_sha256"] == hashlib.sha256(b"fresh database").hexdigest()


def test_database_update_failure_stops_before_status(tmp_path: Path) -> None:
    scanner_root = tmp_path / "scanners"
    scanner_root.mkdir()
    grype = scanner_root / "grype"
    grype.write_bytes(b"grype")
    now = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)
    calls, runner = _database_runner(
        scanner_root,
        now,
        update_returncode=7,
    )

    with pytest.raises(ScanError, match="database update command failed"):
        _database_identity(
            scanner_root,
            grype,
            None,
            {},
            _database_policy(),
            {},
            now=now,
            runner=runner,
        )

    assert calls == [[str(grype), "db", "update"]]
    assert (scanner_root / "db").is_dir()


@pytest.mark.parametrize(
    ("status_path", "built", "message"),
    (
        ("other.db", datetime(2026, 9, 12, 12, tzinfo=timezone.utc), "different database"),
        (
            "vulnerability.db",
            datetime(2026, 9, 7, 11, tzinfo=timezone.utc),
            "database is stale",
        ),
    ),
)
def test_database_status_path_and_freshness_remain_blocking(
    tmp_path: Path,
    status_path: str,
    built: datetime,
    message: str,
) -> None:
    scanner_root = tmp_path / "scanners"
    scanner_root.mkdir()
    grype = scanner_root / "grype"
    grype.write_bytes(b"grype")
    now = datetime(2026, 9, 12, 12, tzinfo=timezone.utc)
    calls, base_runner = _database_runner(scanner_root, now, built=built)
    expected_database = scanner_root / "db/6/vulnerability.db"
    alternate_database = scanner_root / "db/6/other.db"

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        completed = base_runner(command, **kwargs)
        if command[1:3] == ["db", "status"]:
            status = json.loads(completed.stdout.decode("utf-8"))
            if status_path == "other.db":
                alternate_database.write_bytes(b"other database")
                status["path"] = str(alternate_database)
            else:
                status["path"] = str(expected_database)
            completed = subprocess.CompletedProcess(
                command, 0, json.dumps(status).encode("utf-8"), b""
            )
        return completed

    with pytest.raises(ScanError, match=message):
        _database_identity(
            scanner_root,
            grype,
            None,
            {},
            _database_policy(),
            {},
            now=now,
            runner=runner,
        )
    assert [command[1:3] for command in calls] == [["db", "update"], ["db", "status"]]


def test_sdist_derived_install_is_offline_and_digest_bound(tmp_path: Path) -> None:
    output = tmp_path / "scan-output"
    output.mkdir()
    archive = tmp_path / "apgr-0.11.0.tar.gz"
    archive.write_bytes(b"exact sdist")
    installer = tmp_path / "python"
    installer.write_bytes(b"python")
    installer.chmod(0o755)
    record = {
        "id": "python-sdist",
        "path": archive,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        target = Path(command[command.index("--target") + 1])
        metadata = target / "agentic_praxis_grimoire-0.11.0.dist-info/METADATA"
        metadata.parent.mkdir(parents=True)
        metadata.write_text("Name: agentic-praxis-grimoire\nVersion: 0.11.0\n", encoding="utf-8")
        binary = target / "agentic_praxis_grimoire/bin/apgr"
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b"native apgr")
        binary.chmod(0o755)
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        assert environment["PIP_CACHE_DIR"] == str(output / "pip-cache")
        assert environment["TMPDIR"] == str(output / "pip-tmp")
        assert environment["PIP_NO_INPUT"] == "1"
        return subprocess.CompletedProcess(command, 0, b"installed\n", b"")

    install_root, evidence = _install_sdist(
        record,
        output,
        installer,
        {},
        runner=runner,
    )

    assert install_root == output / "installed/python-sdist"
    assert calls[0][1:4] == ["-m", "pip", "install"]
    assert {"--no-index", "--no-deps", "--no-build-isolation"}.issubset(calls[0])
    assert evidence["target"] == "installed/python-sdist"
    assert evidence["archive_sha256"] == record["sha256"]
    assert len(evidence["installed_tree_sha256"]) == 64
    assert evidence["metadata"]["path"].endswith(".dist-info/METADATA")
    assert evidence["binary"]["path"] == "agentic_praxis_grimoire/bin/apgr"
    assert evidence["installer"]["status"] == "passed"


def test_sdist_install_failure_and_archive_mutation_are_blocking(tmp_path: Path) -> None:
    output = tmp_path / "scan-output"
    output.mkdir()
    archive = tmp_path / "apgr-0.11.0.tar.gz"
    archive.write_bytes(b"exact sdist")
    installer = tmp_path / "python"
    installer.write_bytes(b"python")
    installer.chmod(0o755)
    record = {
        "id": "python-sdist",
        "path": archive,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    }

    def failed(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(command, 9, b"", b"pip failed")

    with pytest.raises(ScanError, match="offline sdist installation failed"):
        _install_sdist(record, output, installer, {}, runner=failed)

    output = tmp_path / "scan-output-mutated"
    output.mkdir()

    def mutating(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        archive.write_bytes(b"mutated sdist")
        return subprocess.CompletedProcess(command, 0, b"installed", b"")

    with pytest.raises(ScanError, match="changed during derived installation"):
        _install_sdist(record, output, installer, {}, runner=mutating)


def test_sdist_coverage_union_requires_declared_raw_or_derived_type() -> None:
    covered = _coverage_union(
        {"types": {"go-module": 1}},
        {"types": {"python": 1}},
        ["python"],
    )
    assert covered == {
        "required_types": ["python"],
        "covered_types": ["go-module", "python"],
        "missing_types": [],
        "status": "passed",
    }
    missing = _coverage_union({"types": {}}, {"types": {}}, ["python"])
    assert missing["status"] == "coverage-gap"
    assert missing["missing_types"] == ["python"]


def test_sdist_scan_preserves_raw_gap_and_qualifies_from_derived_sbom(
    tmp_path: Path,
) -> None:
    output = tmp_path / "scan-output"
    output.mkdir()
    (output / "extracted").mkdir()
    archive = tmp_path / "apgr-0.11.0.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        payload = b"source payload"
        info = tarfile.TarInfo("README.md")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    installer = tmp_path / "python"
    installer.write_bytes(b"python")
    installer.chmod(0o755)
    syft = tmp_path / "syft"
    syft.write_bytes(b"syft")
    grype = tmp_path / "grype"
    grype.write_bytes(b"grype")
    record = {
        "id": "python-sdist",
        "kind": "python-sdist",
        "relative": "python/apgr-0.11.0.tar.gz",
        "path": archive,
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "required_types": ["python"],
    }

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if command[1:4] == ["-m", "pip", "install"]:
            target = Path(command[command.index("--target") + 1])
            metadata = target / "agentic_praxis_grimoire-0.11.0.dist-info/METADATA"
            metadata.parent.mkdir(parents=True)
            metadata.write_text("Name: apgr\nVersion: 0.11.0\n", encoding="utf-8")
            binary = target / "agentic_praxis_grimoire/bin/apgr"
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b"native apgr")
            binary.chmod(0o755)
            return subprocess.CompletedProcess(command, 0, b"installed", b"")
        if command[1] == "scan":
            output_path = Path(next(item.removeprefix("syft-json=") for item in command if item.startswith("syft-json=")))
            derived = "derived-install" in output_path.as_posix()
            artifacts = (
                [{"type": "python", "name": "apgr", "foundBy": "python-installed-package-cataloger"}]
                if derived
                else [{"type": "file", "name": "README.md", "foundBy": "directory-cataloger"}]
            )
            output_path.write_text(json.dumps({"artifacts": artifacts, "files": []}), encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, b"", b"")
        if command[1].startswith("sbom:"):
            output_path = Path(command[command.index("--file") + 1])
            output_path.write_text(
                json.dumps({"descriptor": {"version": "0.118.0"}, "matches": []}),
                encoding="utf-8",
            )
            return subprocess.CompletedProcess(command, 0, b"", b"")
        raise AssertionError(command)

    result = _scan_record(
        record,
        source=tmp_path,
        output=output,
        syft=syft,
        syft_config=None,
        grype=grype,
        grype_config=None,
        environment={},
        policy={},
        redact=(),
        installer_python=installer,
        runner=runner,
    )

    assert result["sbom"]["coverage_status"] == "coverage-gap"
    assert result["derived_install"]["sbom"]["coverage_status"] == "passed"
    assert result["derived_install"]["source_archive_sha256"] == record["sha256"]
    assert result["derived_install"]["sbom"]["source_archive_sha256"] == record["sha256"]
    assert result["derived_install"]["grype"]["source_archive_sha256"] == record["sha256"]
    assert result["coverage_union"]["status"] == "passed"
    assert result["status"] == "passed"


def test_grype_report_requires_database_identity_and_blocks_high(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    report = {
        "descriptor": {"name": "grype", "version": "0.118.0"},
        "db": {"status": "loaded", "built": now.isoformat()},
        "matches": [],
    }
    path = tmp_path / "clean.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    result = validate_grype_report(path, now=now)
    assert result["status"] == "passed"

    report["matches"] = [{"vulnerability": {"id": "CVE-test", "severity": "High"}, "artifact": {"name": "demo"}}]
    path.write_text(json.dumps(report), encoding="utf-8")
    result = validate_grype_report(path, now=now)
    assert result["status"] == "failed"
    assert result["blocking_findings"][0]["id"] == "CVE-test"


def test_sbom_ecosystem_detection_uses_package_urls() -> None:
    document = {
        "packages": [
            {"externalRefs": [{"referenceLocator": "pkg:golang/example.org/x"}]},
            {"externalRefs": [{"referenceLocator": "pkg:pypi/demo"}]},
            {"externalRefs": [{"referenceLocator": "pkg:npm/demo"}]},
        ]
    }
    assert _ecosystems(document) == {"go-module", "python-package", "npm-package"}


def test_scan_policy_records_cataloger_and_artifact_contract() -> None:
    policy = json.loads(
        (ROOT / "release/ci/sbom_policy.json").read_text(encoding="utf-8")
    )
    scan = policy["scan"]
    assert scan["source"]["catalogers"] == "all"
    assert "javascript-package-cataloger" in scan["source"]["required_catalogers"]
    assert scan["bundle"]["go"]["darwin-arm64"]["binary"] == "go/darwin-arm64/apgr"
    assert scan["bundle"]["python"]["wheel_count"] == 3
    assert scan["bundle"]["npm"]["count"] == 4
    assert scan["scanner"]["grype"]["custom_ignores"] == []


def test_empty_or_missing_sbom_coverage_is_blocking() -> None:
    status, missing = _scan_status(
        {"package_count": 0, "types": {}, "catalogers": {}},
        ["python"],
    )
    assert status == "coverage-gap"
    assert missing == ["python"]

    status, missing = _scan_status(
        {
            "package_count": 2,
            "types": {"go-module": 2},
            "catalogers": {"go-module-binary-cataloger": 2},
        },
        ["go-module"],
        ["javascript-package-cataloger"],
    )
    assert status == "coverage-gap"
    assert missing == ["cataloger:javascript-package-cataloger"]


def test_checksum_substitution_is_refused(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"original")
    checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (tmp_path / "SHA256SUMS").write_text(
        f"{checksum}  artifact.bin\n", encoding="ascii"
    )
    assert _parse_checksums(tmp_path, "SHA256SUMS") == {"artifact.bin": checksum}

    artifact.write_bytes(b"substituted")
    with pytest.raises(ScanError, match="checksum mismatch"):
        _parse_checksums(tmp_path, "SHA256SUMS")


def test_grype_database_failure_and_malformed_report_are_blocking(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    report = {
        "descriptor": {"name": "grype", "version": "0.118.0"},
        "db": {"status": "failed", "built": now.isoformat()},
        "matches": [],
    }
    path = tmp_path / "failed-db.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(TypeError, match="database reports failure"):
        validate_grype_report(path, now=now)

    path.write_text(json.dumps({"descriptor": {"version": "0.118.0"}}), encoding="utf-8")
    with pytest.raises(TypeError, match="no match collection"):
        validate_grype_report(path, now=now)


def test_grype_severity_boundary_blocks_high_but_retains_medium(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    report = {
        "descriptor": {"name": "grype", "version": "0.118.0"},
        "db": {"status": "loaded", "built": now.isoformat()},
        "matches": [
            {
                "vulnerability": {"id": "CVE-medium", "severity": "Medium"},
                "artifact": {"name": "demo"},
            }
        ],
    }
    path = tmp_path / "medium.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    result = validate_grype_report(path, now=now)
    assert result["status"] == "passed"
    assert result["severity_counts"] == {"medium": 1}

    report["matches"].append(
        {
            "vulnerability": {"id": "CVE-high", "severity": "High"},
            "artifact": {"name": "demo"},
        }
    )
    path.write_text(json.dumps(report), encoding="utf-8")
    result = validate_grype_report(path, now=now)
    assert result["status"] == "failed"
    assert result["blocking_findings"] == [
        {"id": "CVE-high", "severity": "high", "artifact": "demo"}
    ]


@pytest.mark.parametrize("returncode", [0, 2, 1])
def test_pinned_grype_threshold_exit_is_distinct_from_operational_failure(
    tmp_path: Path, returncode: int,
) -> None:
    output = tmp_path / "grype.json"
    report = {"matches": []}

    def runner(command, **kwargs):
        output.write_text(json.dumps(report), encoding="utf-8")
        return subprocess.CompletedProcess(command, returncode, b"", b"")

    arguments = dict(scanner=tmp_path / "grype", config=None,
                     sbom=tmp_path / "source.json", output=output,
                     environment={}, runner=runner)
    if returncode == 1:
        with pytest.raises(ScanError, match="failed operationally"):
            _grype_document(**arguments)
    else:
        observed, completed = _grype_document(**arguments)
        assert observed == report
        assert completed.returncode == returncode
