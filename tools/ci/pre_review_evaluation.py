"""Evaluation and policy classification for APGR pre-review check results."""

from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path
from typing import Any, NamedTuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ci.betterleaks_dispositions import load_records, reconcile
from tools.ci.pre_review_records import (
    CI_ROOT,
    FINDING_RETURN_CODES,
    INTERNAL_FAILURE,
    MODULE_FAILURE,
    POLICY_CHECKS,
    Check,
)


class RuffBaselineError(RuntimeError):
    """Raised when the Ruff baseline file is missing, tampered, or violates policy."""




def claim_historical_ruff_findings(root: Path, findings: list) -> tuple[int, set[int]]:
    """Classify two immutable APG140 fixture observations, returning count and matched indices."""
    relative = "src/test/support/apg_external_compatibility_fixture.py"
    path = root / relative
    expected = {(31, 8, "`stat` imported but unused"),
                (32, 44, "`typing.Sequence` imported but unused")}
    if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != (
        "40b7e98fd862977d83a5e6a01113435bc1b6c47a710668c82faf5d45ff10369e"
    ):
        return 0, set()
    accepted = 0
    claimed: set[int] = set()
    for idx, row in enumerate(findings):
        location = row.get("location", {})
        identity = (location.get("row"), location.get("column"), row.get("message"))
        reported = Path(row["filename"])
        if not reported.is_absolute():
            reported = root / reported
        if row.get("code") == "F401" and reported == path and identity in expected:
            expected.remove(identity)
            accepted += 1
            claimed.add(idx)
    return accepted, claimed


def historical_ruff_findings(root: Path, findings: list) -> int:
    """Classify two immutable APG140 fixture observations, never a lint baseline.

    APGR-V0110-READINESS4 pre_final review under Decision B preserves accepted historical fixture bytes. The public
    APG140 support binding owns this exact source; independent pre-final review
    must disposition this classification with the rest of the candidate.
    """
    return claim_historical_ruff_findings(root, findings)[0]


def load_ruff_baseline(
    baseline_path: Path | None = None,
    *,
    expected_digest: str | None = None,
) -> set[tuple[str, str, int, int, str, str]]:
    """Load grandfathered Ruff baseline findings mapped as exact identities.

    Returns a set of tuples: (path, code, row, col, context_hash, message).
    Raises RuffBaselineError on any missing file, corrupted JSON, schema mismatch,
    unexpected keys, provenance tampering, count mismatch, or digest mismatch.
    """
    libexec_dir = Path(__file__).resolve().parents[2] / "libexec"
    if str(libexec_dir) not in sys.path:
        sys.path.insert(0, str(libexec_dir))
    from apg_public_release_v013 import (
        V013_RUFF_BASELINE_COUNT,
        V013_RUFF_BASELINE_DIGEST,
        V013_RUFF_BASELINE_ORIGIN_COMMIT,
        V013_RUFF_BASELINE_ORIGIN_TREE,
        V013_RUFF_BASELINE_SCHEMA,
    )

    is_default_path = baseline_path is None
    if baseline_path is None:
        baseline_path = CI_ROOT / "ruff_baseline.json"
        if expected_digest is None:
            expected_digest = V013_RUFF_BASELINE_DIGEST

    if not baseline_path.is_file():
        raise RuffBaselineError(f"ruff baseline file does not exist: {baseline_path}")

    raw_bytes = baseline_path.read_bytes()
    computed_digest = hashlib.sha256(raw_bytes).hexdigest()
    if expected_digest is not None and computed_digest != expected_digest:
        raise RuffBaselineError(
            f"ruff baseline digest mismatch: computed {computed_digest} != expected {expected_digest}"
        )

    try:
        data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as error:
        raise RuffBaselineError(f"ruff baseline JSON malformed: {error}") from error

    if not isinstance(data, dict):
        raise RuffBaselineError("ruff baseline must be a JSON object")

    expected_keys = {
        "schema",
        "origin_commit",
        "origin_tree",
        "carry_forward_commit",
        "carry_forward_tree",
        "description",
        "findings",
    }
    if set(data.keys()) != expected_keys:
        raise RuffBaselineError(
            f"ruff baseline keys differ from closed contract: {set(data.keys()) ^ expected_keys}"
        )

    if data.get("schema") != V013_RUFF_BASELINE_SCHEMA:
        raise RuffBaselineError(f"unsupported ruff baseline schema: {data.get('schema')}")

    if data.get("origin_commit") != V013_RUFF_BASELINE_ORIGIN_COMMIT:
        raise RuffBaselineError(f"ruff baseline origin_commit mismatch: {data.get('origin_commit')}")

    if data.get("origin_tree") != V013_RUFF_BASELINE_ORIGIN_TREE:
        raise RuffBaselineError(f"ruff baseline origin_tree mismatch: {data.get('origin_tree')}")

    findings = data.get("findings")
    if not isinstance(findings, list):
        raise RuffBaselineError("ruff baseline findings must be a list")

    if is_default_path and expected_digest == V013_RUFF_BASELINE_DIGEST and len(findings) != V013_RUFF_BASELINE_COUNT:
        raise RuffBaselineError(
            f"ruff baseline finding count mismatch: {len(findings)} != {V013_RUFF_BASELINE_COUNT}"
        )

    finding_keys = {"path", "code", "message", "row", "col", "context_hash"}
    identities: set[tuple[str, str, int, int, str, str]] = set()

    for idx, item in enumerate(findings):
        if not isinstance(item, dict) or set(item.keys()) != finding_keys:
            raise RuffBaselineError(f"ruff baseline finding at index {idx} violates closed schema")
        path = item["path"]
        code = item["code"]
        message = item["message"]
        row = item["row"]
        col = item["col"]
        context_hash = item["context_hash"]

        if not isinstance(path, str) or not path.strip():
            raise RuffBaselineError(f"invalid path in baseline finding {idx}")
        if not isinstance(code, str) or not code.strip():
            raise RuffBaselineError(f"invalid code in baseline finding {idx}")
        if not isinstance(message, str) or not message.strip():
            raise RuffBaselineError(f"invalid message in baseline finding {idx}")
        if not isinstance(row, int) or row <= 0:
            raise RuffBaselineError(f"invalid row in baseline finding {idx}")
        if not isinstance(col, int) or col <= 0:
            raise RuffBaselineError(f"invalid col in baseline finding {idx}")
        if (
            not isinstance(context_hash, str)
            or len(context_hash) != 64
            or not all(c in "0123456789abcdef" for c in context_hash.lower())
        ):
            raise RuffBaselineError(f"invalid context_hash in baseline finding {idx}")

        ident = (path, code, row, col, context_hash.lower(), message)
        if ident in identities:
            raise RuffBaselineError(f"duplicate finding identity in baseline: {ident}")
        identities.add(ident)

    return identities



def baseline() -> dict:
    """Load the pre-review ratchets from the baseline JSON file."""
    return json.loads((CI_ROOT / "pre_review_baseline.json").read_text(encoding="utf-8"))[
        "ratchets"
    ]


def finding_count(policy: str, output: str) -> int:
    """Count findings in machine-readable checker output."""
    document = json.loads(output or "null")
    if policy == "hadolint":
        if not isinstance(document, list) or not all(isinstance(item, dict) for item in document):
            raise ValueError("hadolint JSON has no valid finding collection")
        return len(document)
    if policy == "pip-audit":
        dependencies = document.get("dependencies", document) if isinstance(document, dict) else document
        if isinstance(dependencies, list):
            return sum(len(item.get("vulns", [])) for item in dependencies if isinstance(item, dict))
        return 0
    if policy == "zizmor":
        if isinstance(document, list) and all(isinstance(item, dict) for item in document):
            return len(document)
        for key in ("findings", "results", "audits"):
            if isinstance(document, dict) and isinstance(document.get(key), list):
                if not all(isinstance(item, dict) for item in document[key]):
                    raise ValueError("zizmor finding collection is malformed")
                return len(document[key])
        raise ValueError("zizmor JSON has no finding collection")
    if policy == "betterleaks":
        if isinstance(document, list) and all(isinstance(item, dict) for item in document):
            return len(document)
        raise ValueError("BetterLeaks JSON has no valid finding collection")
    raise ValueError(f"unknown finding policy {policy}")


class GovulncheckSummary(NamedTuple):
    findings: int
    reachable: int
    errors: int
    total_osvs: int
    reachable_osvs: int
    module_package_osvs: int
    module_package_records: int
    unique_osv_ids: tuple[str, ...]
    reachable_osv_ids: tuple[str, ...]
    module_package_osv_ids: tuple[str, ...]


def _govulncheck_records(output: str) -> GovulncheckSummary:
    """Classify govulncheck JSONL output according to pinned v1.1.4 producer semantics."""
    decoder = json.JSONDecoder()
    position = 0
    records: list[dict[str, Any]] = []
    while position < len(output):
        while position < len(output) and output[position].isspace():
            position += 1
        if position >= len(output):
            break
        try:
            value, position = decoder.raw_decode(output, position)
        except json.JSONDecodeError as error:
            raise ValueError("govulncheck JSON stream is malformed") from error
        if not isinstance(value, dict):
            raise TypeError("govulncheck JSON record is not an object")
        records.append(value)
    if not records:
        raise ValueError("govulncheck JSON stream is empty")

    config_records = [r["config"] for r in records if "config" in r]
    if not config_records:
        raise ValueError("govulncheck JSON stream has no configuration record")

    config = config_records[0]
    if not isinstance(config, dict):
        raise TypeError("govulncheck config record is malformed")

    scan_level = config.get("scan_level", "symbol")
    scan_mode = config.get("scan_mode", "source")

    if scan_level != "symbol":
        raise ValueError(
            f"govulncheck scan level '{scan_level}' is insufficient for symbol reachability; expected 'symbol'"
        )
    if scan_mode not in {"source", "binary"}:
        raise ValueError(f"govulncheck scan mode '{scan_mode}' is unsupported")

    findings = 0
    reachable = 0
    errors = 0
    reachable_osv_set: set[str] = set()
    module_package_osv_set: set[str] = set()
    all_osv_set: set[str] = set()

    for record in records:
        if "error" in record:
            errors += 1
        osv = record.get("osv")
        if isinstance(osv, dict) and osv.get("id"):
            all_osv_set.add(str(osv["id"]))
        finding = record.get("finding")
        if finding is None:
            continue
        if not isinstance(finding, dict):
            raise TypeError("govulncheck finding record is malformed")
        findings += 1
        finding_osv = finding.get("osv")
        if finding_osv:
            all_osv_set.add(str(finding_osv))
        trace = finding.get("trace", [])
        if trace is not None and not isinstance(trace, list):
            raise ValueError("govulncheck finding trace is malformed")

        has_symbol_frame = False
        if trace:
            for frame in trace:
                if not isinstance(frame, dict):
                    raise ValueError("govulncheck finding trace frame is malformed")
                if frame.get("function") or frame.get("receiver"):
                    has_symbol_frame = True
                    break

        if has_symbol_frame:
            reachable += 1
            if finding_osv:
                reachable_osv_set.add(str(finding_osv))
        else:
            if finding_osv:
                module_package_osv_set.add(str(finding_osv))

    module_package_records = findings - reachable
    pure_module_package_osvs = module_package_osv_set - reachable_osv_set

    return GovulncheckSummary(
        findings=findings,
        reachable=reachable,
        errors=errors,
        total_osvs=len(all_osv_set),
        reachable_osvs=len(reachable_osv_set),
        module_package_osvs=len(pure_module_package_osvs),
        module_package_records=module_package_records,
        unique_osv_ids=tuple(sorted(all_osv_set)),
        reachable_osv_ids=tuple(sorted(reachable_osv_set)),
        module_package_osv_ids=tuple(sorted(pure_module_package_osvs)),
    )


def evaluate(
    check: Check,
    returncode: int,
    stdout: str,
    stderr: str = "",
) -> tuple[str, str, str]:
    """Evaluate check execution outcome against policy, returning (status, detail, classification)."""
    failure_output = stdout + stderr

    # Explicit missing-executable exit from shells (127) or tool not found
    if returncode == 127 or "command not found" in failure_output or "No such file or directory" in stderr:
        return "failed", f"tool/executable unavailable: {check.name}", "tool-failure"

    if returncode != 0 and MODULE_FAILURE.search(failure_output):
        return "failed", "tool/bootstrap failure: Python module unavailable", "tool-failure"
    if returncode != 0 and INTERNAL_FAILURE.search(failure_output):
        return "failed", "tool/internal failure: bounded diagnostic retained", "tool-failure"

    if check.policy in {"ruff", "pyflakes"}:
        if returncode not in {0, 1}:
            return "failed", f"{check.name} execution failed", "tool-failure"
        try:
            findings = json.loads(stdout)
            if not isinstance(findings, list) or returncode != int(bool(findings)):
                raise ValueError(f"{check.name} result/exit disagreement")
            historical, claimed = (
                claim_historical_ruff_findings(check.cwd, findings)
                if check.policy == "ruff"
                else (0, set())
            )
        except (OSError, KeyError, TypeError, ValueError):
            return "failed", f"{check.name} result or historical input invalid", "tool-failure"

        try:
            baseline_identities = load_ruff_baseline()
        except RuffBaselineError as error:
            return "failed", f"ruff baseline verification failure: {error}", "tool-failure"
        except Exception as error:
            return "failed", f"ruff baseline load failure: {error}", "tool-failure"

        file_lines_cache: dict[Path, list[str] | None] = {}

        def get_line_context_hash(file_path: Path, row_num: int) -> str | None:
            if file_path not in file_lines_cache:
                try:
                    file_lines_cache[file_path] = file_path.read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                except OSError:
                    file_lines_cache[file_path] = None
            lines = file_lines_cache[file_path]
            if lines is None:
                return None
            if not isinstance(row_num, int) or not (1 <= row_num <= len(lines)):
                return None
            line_text = lines[row_num - 1]
            return hashlib.sha256(line_text.strip().encode("utf-8")).hexdigest()

        matched_identities: set[tuple[str, str, int, int, str, str]] = set()
        unresolved = 0

        for idx, row in enumerate(findings):
            if idx in claimed:
                continue
            reported = Path(row.get("filename", ""))
            if not reported.is_absolute():
                reported = check.cwd / reported
            try:
                rel_path = reported.resolve().relative_to(check.cwd.resolve()).as_posix()
            except ValueError:
                rel_path = reported.as_posix()

            location = row.get("location", {})
            r_num = location.get("row", 0)
            c_num = location.get("column", 0)

            # Grandfathering identity strictly derives context_hash from source file
            ctx_hash = get_line_context_hash(reported.resolve(), r_num)
            if ctx_hash is None:
                unresolved += 1
                continue

            ident = (
                rel_path,
                row.get("code", ""),
                r_num,
                c_num,
                ctx_hash.lower(),
                row.get("message", ""),
            )

            if ident in baseline_identities and ident not in matched_identities:
                matched_identities.add(ident)
            else:
                unresolved += 1

        grandfathered = len(matched_identities)
        detail = f"observations={len(findings)}; historical={historical}; grandfathered={grandfathered}; unresolved={unresolved}"
        return ("failed", detail, "policy-finding") if unresolved else ("passed", detail, "passed")


    if check.policy == "file-length":
        if returncode not in {0, 1}:
            return "failed", "file-length input or tool failure", "tool-failure"
        try:
            document = json.loads(stdout)
            if document["version"] != 1 or document["profile"] != "file-length":
                raise ValueError("unsupported file-length result")
            if (document["warning_limit"], document["failure_limit"]) != (400, 1000):
                raise ValueError("unapproved limits")
            scanned, warnings, failures = (document[key] for key in
                                          ("scanned_file_count", "warning_count", "failure_count"))
            if any(type(n) is not int or n < 0 for n in (scanned, warnings, failures)) or not scanned:
                raise ValueError("invalid counts or zero targets")
            findings = document["findings"]
            if not isinstance(findings, list) or len(findings) != warnings + failures:
                raise ValueError("incomplete finding inventory")
            if sum(f["severity"] == "warning" for f in findings) != warnings:
                raise ValueError("warning count disagreement")
            if sum(f["severity"] == "failure" for f in findings) != failures:
                raise ValueError("failure count disagreement")
            expected_status = "failed" if failures else "passed_with_warnings" if warnings else "passed"
            if document["status"] != expected_status or returncode != int(bool(failures)):
                raise ValueError("exit/result disagreement")
        except (KeyError, TypeError, ValueError):
            return "failed", "file-length result contract invalid", "tool-failure"
        detail = f"scanned={scanned}; warnings={warnings}; failures={failures}"
        return ("failed", detail, "policy-finding") if failures else ("passed", detail, "passed")

    if check.policy == "retained-python-ratchets":
        try:
            document = json.loads(stdout)
            if document.get("schema") not in {
                "apg-retained-python-ratchets-result-v1",
                "repomap-retained-python-ratchets-result-v1",
            }:
                raise ValueError("invalid schema")
            classification = document["classification"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return "failed", "retained ratchet JSON was invalid", "tool-failure"
        expected = {
            0: "passed",
            1: "policy-finding",
            2: "tool-failure",
        }
        if expected.get(returncode) != classification:
            return "failed", "retained ratchet exit contract was invalid", "tool-failure"
        if returncode == 0:
            return "passed", "exact retained baseline", "passed"
        if returncode == 1:
            return "failed", "retained Python ratchet delta", "policy-finding"
        return "failed", "retained Python ratchet tool failure", "tool-failure"

    if check.name == "python-retention-inventory":
        try:
            document = json.loads(stdout)
            if not isinstance(document, dict):
                raise TypeError("retention inventory is not an object")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return "failed", "retention inventory JSON was invalid", "tool-failure"
        if "error" in document:
            return "failed", f"tool/validation failure: {document['error']}", "tool-failure"
        status = document.get("status", "passed" if returncode == 0 else "failed")
        classification = document.get("classification", "passed" if returncode == 0 else "policy-finding")
        detail = document.get("detail", f"status={status}; exit={returncode}")
        if status == "passed" and returncode == 0:
            return "passed", detail, "passed"
        return "failed", detail, classification

    if check.name == "govulncheck":
        try:
            summary = _govulncheck_records(stdout)
        except (TypeError, ValueError) as error:
            return "failed", str(error), "tool-failure"
        if summary.errors:
            return "failed", f"govulncheck reported {summary.errors} error record(s)", "tool-failure"
        if returncode not in {0, 3}:
            return "failed", f"govulncheck operational failure: exit={returncode}", "tool-failure"
        if returncode == 3 and summary.findings == 0:
            return "failed", "govulncheck operational failure: exit=3 but 0 findings reported", "tool-failure"
        detail = (
            f"exit={returncode}; findings={summary.findings} (unique_osv={summary.total_osvs}); "
            f"reachable={summary.reachable} (reachable_osv={summary.reachable_osvs}); "
            f"module-package={summary.module_package_records} (module_package_osv={summary.module_package_osvs})"
        )
        if summary.reachable:
            return "failed", detail, "policy-finding"
        return "passed", detail, "passed"

    if check.name == "pip-audit":
        try:
            document = json.loads(stdout)
            if document.get("schema") != "apg-dependency-audit-v1":
                raise ValueError("unsupported dependency-audit schema")
            inventories = document.get("inventories")
            if not isinstance(inventories, list) or not inventories:
                raise ValueError("dependency-audit inventories are empty")
            finding_total = document.get("finding_count")
            tool_failure_count = document.get("tool_failure_count")
            policy_finding_count = document.get("policy_finding_count")
            if not all(
                isinstance(value, int) and value >= 0
                for value in (finding_total, tool_failure_count, policy_finding_count)
            ):
                raise TypeError("dependency-audit counts are invalid")
            for inventory in inventories:
                if not isinstance(inventory, dict):
                    raise TypeError("dependency-audit inventory is malformed")
                if inventory.get("classification") not in {
                    "passed",
                    "policy-finding",
                    "tool-failure",
                }:
                    raise ValueError("dependency-audit inventory classification is invalid")
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return "failed", "dependency-audit JSON was invalid", "tool-failure"
        if tool_failure_count:
            return "failed", f"dependency-audit tool failures={tool_failure_count}", "tool-failure"
        if policy_finding_count:
            return "failed", f"dependency-audit findings={finding_total}", "policy-finding"
        if returncode == 0 and finding_total == 0 and document.get("classification") == "passed":
            return "passed", "dependency inventories resolved; findings=0", "passed"
        return "failed", "dependency-audit exit/result contract was invalid", "tool-failure"

    if check.policy == "betterleaks":
        if returncode not in {0, 1}:
            return "failed", f"scanner operational failure: exit={returncode}", "tool-failure"
        try:
            count = finding_count("betterleaks", stdout)
            if returncode and not count:
                return "failed", "scanner failure supplied no findings", "tool-failure"
            records = load_records(check.cwd / "tools/ci/betterleaks_dispositions.json")
            result = reconcile(check.cwd, json.loads(stdout), records)
        except (OSError, TypeError, ValueError, KeyError):
            return "failed", "BetterLeaks disposition/source readback invalid", "tool-failure"
        detail = "; ".join(f"{key}={value}" for key, value in result.items())
        blocking = result["unresolved"] or result["unmatched_dispositions"]
        return ("failed", detail, "policy-finding") if blocking else ("passed", detail, "passed")

    if check.policy in {"hadolint", "pip-audit", "zizmor"}:
        # zizmor runs with --no-exit-codes: findings remain in JSON while
        # nonzero means operational failure. Other pinned scanners use 1
        # for findings and must never turn arbitrary error exits into a pass.
        admitted_exits = {0} if check.policy == "zizmor" else {0, 1}
        if returncode not in admitted_exits:
            return "failed", f"scanner operational failure: exit={returncode}", "tool-failure"
        try:
            count = finding_count(check.policy, stdout)
        except (TypeError, ValueError, json.JSONDecodeError):
            return "failed", "machine-readable finding output was invalid", "tool-failure"
        allowed = baseline().get(check.policy, {}).get("findings", 0)
        if returncode and not count:
            return "failed", "scanner failure supplied no findings", "tool-failure"
        return (
            ("passed", f"findings={count}; baseline={allowed}", "passed")
            if count <= allowed
            else (
                "failed",
                f"findings={count}; baseline={allowed}",
                "policy-finding",
            )
        )

    if check.policy == "malskanner":
        try:
            document = json.loads(stdout)
            findings = document["findings"]
            verdict = document["verdict"]
            if not isinstance(findings, list) or not isinstance(verdict, str):
                raise ValueError("invalid MalSkanner fields")
            count = len(findings)
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return "failed", "MalSkanner output was invalid", "tool-failure"
        if returncode not in {0, 1}:
            return "failed", f"MalSkanner operational failure: exit={returncode}", "tool-failure"
        passed = returncode == 0 and verdict == "OK" and count == 0
        return (
            "passed" if passed else "failed",
            f"verdict={verdict}; findings={count}",
            "passed" if passed else "policy-finding",
        )

    if check.policy == "suppressions":
        try:
            document = json.loads(stdout)
            if document.get("schema") not in {
                "apg-scanner-suppression-inventory-v1",
                "repomap-scanner-suppression-inventory-v2",
                "apg-scanner-suppression-inventory-v3",
            }:
                raise ValueError("unsupported suppression schema")
            counts = {
                name: len(document[name])
                for name in ("added", "broadened", "context_changed", "removed", "unchanged", "unapproved_or_expired")
                if name in document
            }
            blocking = bool(document.get("blocking", False))
        except (KeyError, TypeError, json.JSONDecodeError, ValueError):
            return "failed", "suppression inventory output was invalid", "tool-failure"
        detail = "; ".join(f"{name}={counts[name]}" for name in counts)
        if returncode not in {0, 1} or blocking != (returncode == 1):
            return "failed", "suppression inventory exit contract was invalid", "tool-failure"
        return (
            ("failed", detail, "policy-finding")
            if blocking
            else ("passed", detail, "passed")
        )

    if check.name == "prompt-defense-audit":
        try:
            summary = json.loads(stdout)
            valid = isinstance(summary, dict) and all(
                key in summary
                for key in ("score", "missing", "embedded_payloads", "unicode_issues")
            )
            valid = valid and all(isinstance(summary[key], list) for key in ("missing", "embedded_payloads", "unicode_issues"))
            valid = valid and isinstance(summary["score"], (int, float)) and not isinstance(summary["score"], bool)
        except (TypeError, json.JSONDecodeError):
            valid = False
        if not valid:
            return "failed", "tool/configuration failure: invalid prompt audit", "tool-failure"
        if returncode not in {0, 1} or summary["missing"]:
            return "failed", "prompt audit inputs or execution unavailable", "tool-failure"
        min_score = baseline().get("prompt-defense", {}).get("minimum_score", 80)
        score = summary.get("score", 0)
        findings = len(summary.get("embedded_payloads", [])) + len(summary.get("unicode_issues", []))
        if score < min_score or findings > 0:
            return "failed", f"score={score} (min {min_score}); findings={findings}", "policy-finding"
        return "passed", f"score={score}", "passed"

    if check.name == "ci-topology":
        if returncode == 0:
            return "passed", "topology contracts satisfied", "passed"
        if returncode == 1:
            return "failed", f"topology violation: {stdout.strip() or stderr.strip()}", "policy-finding"
        return "failed", f"ci-topology error: exit={returncode}", "tool-failure"

    if check.name == "generated-code-drift":
        if returncode == 0:
            return "passed", "zero generated drift", "passed"
        if returncode == 1:
            return "failed", "generated artifact drift detected", "policy-finding"
        return "failed", f"tool/configuration failure: generated drift exit={returncode}", "tool-failure"

    if check.name == "liquibase":
        if returncode == 0:
            return "passed", "liquibase validation clean", "passed"
        if "Liquibase" in failure_output and "Validation" in failure_output:
            return "failed", f"liquibase validation finding: exit={returncode}", "policy-finding"
        return "failed", f"liquibase tool failure: exit={returncode}", "tool-failure"

    if check.name in FINDING_RETURN_CODES and returncode != 0:
        if returncode in FINDING_RETURN_CODES[check.name]:
            return "failed", f"{check.name} policy findings (exit={returncode})", "policy-finding"
        return "failed", f"tool/configuration failure: exit={returncode}", "tool-failure"

    if returncode == 0:
        return "passed", "exit=0", "passed"

    classification = "policy-finding" if check.name in POLICY_CHECKS else "tool-failure"
    return "failed", f"exit={returncode}", classification
