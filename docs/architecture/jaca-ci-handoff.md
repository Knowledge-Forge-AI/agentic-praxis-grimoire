# JACA CI Integration and Qualification Handoff Specification

## 1. Status and Governing Decisions

This handoff specification establishes the integration interface between Agentic
Praxis Grimoire (APGR) and Joint Agentic Command Aegis (JACA) CI. It implements
the APGR-owned deliverable for backlog entry `APGR-CI-QUAL` in the v0.9 program.

Governing contracts and architectural decisions:
- JACA ADR 0008 (`docs/adr/2026/08/0008-ci-cd-platform-topology-and-boundary-contracts.md` in the JACA repository) (CI/CD Platform Topology and Boundary Contracts)
- JACA ADR 0020 (`docs/adr/2026/08/0020-staged-promotion-and-logical-gate-doctrine.md` in the JACA repository) (Staged Promotion and Logical Gate Doctrine)
- JACA Project Onboarding Contract (`docs/specs/ci-cd/project-onboarding-contract.md` in the JACA repository)
- [APGR–JACA Integration Boundary](apg-jaca-integration.md)
- [APGR v0.9 Roadmap](../v0-9-roadmap.md)

## 2. Channel and Authority Boundary

This specification defines qualification for the **private development channel**
(`staging` / `main` pull-request and promotion topologies) only.

> [!IMPORTANT]
> **APGR-Local Conformance vs JACA Registration**:
> APGR-local source qualification of the CI summary interface and execution roles
> is fully qualified on Darwin arm64 under APG114 (Exit `00159`). However, runner
> registration in JACA CI (`tools/ci/evidence.go`, `workflow.go`, `trustedRoleOrder`)
> is consumer-owned and remains pending. APGR-local conformance does not constitute
> or substitute for JACA registration.

Public confidence and release publication are governed separately by
[`docs/public-release-process.md`](../public-release-process.md) and APGR phase
dispatchers. JACA CI execution does not authorize, trigger, or simulate public
release publication, registry uploads, or host mutation.

## 3. Project Validation Inventory

In accordance with Section 2 of the JACA Project Onboarding Contract:

| Area | Required Record |
| --- | --- |
| **Entry points** | Canonical distributed entry point: `apgr test <suite> [--workers <N>] [--summary-file <path>]`<br>Checkout-local legacy wrapper: `bin/apg-test <suite> [--workers <N>] [--summary-file <path>]`<br>Supported `<suite>` roles: `policy`, `unit`, `integration`, `unit-integration` |
| **Populations** | `policy`: Repository inventory verification (`validate_inventory`), dependency stack version verification (`dependency_versions`), skill library mechanical rules and Go embedded corpus identity (`apg_skill_library_check.check_library` and `_embedded_corpus_failure`), and phase record identity (`apg_record_identity.check_records`).<br>`unit`: All Python unit tests under `src/test/unit/` (statements and branches of all declared coverage sources).<br>`integration`: All Python integration and CLI boundary tests under `src/test/int/`.<br>`unit-integration` (`combined`): Combined union gate executing both unit and integration suites. |
| **Thresholds** | Executable threshold authority is defined in [`libexec/apg_test.py`](../../libexec/apg_test.py):<br>- `policy`: 0 diagnostics, 0 structural errors, exit 0.<br>- `unit`: 80% statement coverage and 80% branch coverage minimum.<br>- `integration`: 80% statement coverage and 80% branch coverage minimum.<br>- `combined`: 85% statement coverage and 85% branch coverage minimum. |
| **Platforms** | Supported environments: macOS (Darwin arm64 / Apple Silicon) is fully qualified. Linux (x86_64) is pending qualification for `policy`, and currently BLOCKED for `unit`, `integration`, and `unit-integration` (`combined`) suites because whole-inventory preflight binds Darwin arm64 Nix store hashes for Node.js (`APG_NODEJS_PRIMARY_NODE`). Python 3.11+ runtime. |
| **Tools** | Pinned Python test toolchain: `coverage==7.15.2`, `pytest==9.1.1`, `pytest-cov==7.1.0`, `pytest-xdist==3.8.0`.<br>System prerequisites: Git 2.40+, Go 1.25+ toolchain (required for the source-checkout Go-Python bridge verifying embedded skill corpus identity in policy validation, and Go CLI compilation in integration tests), Node.js runtime (v22.22.2) and TypeScript compiler (`typescript@7.0.2` via `APG_TYPESCRIPT_TSC`). Whole-inventory preflight in `run()` inspects declared inventory requirements across all suites. |
| **Artifacts** | Machine-readable qualification summary is written only when explicitly requested via `--summary-file <path>`. By default, no summary file is generated. Consumers should specify a fresh path (recommended beneath the gitignored `.test-reports/apg/` directory, `.gitignore:21`, e.g. `.test-reports/apg/<role>/summary-$RUN_ID.json`). Files are written atomically with mode `0o600` and size <1 KiB. |
| **Terminal semantics** | Exit code 0: Test execution succeeded and all coverage/policy thresholds were met (`test_status: "pass"`, `gate_status: "pass"`).<br>Exit code 1: Classified according to underlying failure:<br>&nbsp;&nbsp;• Test assertion failure (`TestAssertionError` / pytest exit 1): `test_status: "fail"`, `gate_status: "fail"`.<br>&nbsp;&nbsp;• Coverage gate shortfall (`GateShortfallError`): `test_status: "pass"`, `gate_status: "fail"`.<br>&nbsp;&nbsp;• Policy check failure (`PolicyCheckError`): `test_status: "fail"`, `gate_status: "fail"`.<br>&nbsp;&nbsp;• Harness fault (`HarnessError`, e.g. worker crash, incomplete worker manifest, missing coverage slice, combined union merge failure, pytest exit 3): `test_status: "error"`, `gate_status: "error"`. Harness faults dominate simultaneous threshold shortfalls.<br>&nbsp;&nbsp;• Invocation / prerequisite error (`InvocationError`, e.g. missing prerequisites, empty test collection pytest exit 5, runtime/profile qualification error): `test_status: "error"`, `gate_status: "error"` when `--summary-file` is admitted. Summary path refusal is an invocation error that exits 1 with a diagnostic to stderr but emits no summary receipt file, preserving all target paths untouched.<br>Exit code 2: CLI argument parsing error (`test_status: "error"`, `gate_status: "error"` with sentinel `"suite": "unknown"` when `--summary-file` is requested).<br>Exit code 130: Process cancellation (`SIGINT`, `test_status: "error"`, `gate_status: "error"`). Non-success receipt attests error/interruption without claiming assertions ran.<br>`--help`: Informational flag displaying CLI usage and exiting 0 under an explicit non-validation contract. It generates no summary receipt, makes no validation assertions, and performs no filesystem mutations.<br>Admission strictly precedes invalidation: Target path admission check precedes every filesystem effect. Refused targets (leaf symlinks, Git metadata in `.git/` or linked worktrees, repository root, directories, non-gitignored in-repo paths, and tracked files evaluated across lexically normalized, addressed-in-parent, and resolved destination boundaries) remain completely untouched (no unlinking, writing, or parent creation). Dual-boundary evaluation fails closed on tracking check timeouts or errors, preventing accidental file modification.<br>Entry freshness invalidation: For an admitted destination, any recognized 6-field APGR summary receipt is safely invalidated at command entry before execution starts. Foreign non-receipt files and leaf symlinks at the target are preserved and raise `InvocationError`.<br>Git HEAD drift abort: When HEAD commit changes between invocation entry and completion, summary emission is aborted without emitting false attestations, and any admitted summary target is safely invalidated.<br>Git commit resolution & clean-tree proof: If Git commit resolution fails, summary emission is aborted. Note that `source_commit` attests only to the Git HEAD revision at execution time, not clean working tree proof; tree cleanliness and untracked artifact isolation are consumer-verified via candidate tree calculations in JACA CI.<br>Summary write failure: If writing the summary file fails (e.g. disk full / OSError), a diagnostic is emitted to `stderr`, preserving the underlying test failure or exiting 1 if the test passed. |
| **Isolation** | Execution is strictly read-only with respect to Git source, refs, and working tree index. When executed with pre-warmed runner caches (`GOPROXY=off` or local Go module cache, pre-installed Python virtualenv, and local npm cache), validation is completely offline and makes zero external network calls. In unseeded runner environments, initial Go compilation or dependency resolution requires local cache population. Intermediate test artifacts are isolated in temporary scratch directories and cleaned upon completion. |
| **Failure fixtures** | Maintained APGR-local illustrative contract fixtures under `testing/fixtures/jaca_ci/` (schema `apgr-ci-illustrative-fixture-v1`): `valid-apg-pr.json`, `invalid-role-pr.json`, `drift-pr.json`, `sample-summary-pass.json`, and `sample-summary-fail.json`. Executable conformance tests mechanically assert these fixtures adhere to schema and expected status. |

### 3.1 Per-Role Prerequisite and Platform Support Matrix

The table below defines the exact toolchain and platform requirements per role, reflecting observed execution behavior:

| Role / Suite | CLI Invocation | Python Environment | Go Toolchain | TypeScript Compiler | JavaScript / Node Runtimes | Platform Support | Cache / Timing Behavior |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `policy` | `apgr test policy [--summary-file <path>]` | Python 3.11+ (`coverage==7.15.2`, `pytest==9.1.1`, `pytest-cov==7.1.0`, `pytest-xdist==3.8.0`) | Go 1.25+ required for Go-Python bridge (`verify-corpus`), offline with warmed module cache | Not required (`run_policy` does not invoke compiler preflight) | Not required (`run_policy` does not invoke JS/Node preflight) | **Darwin arm64**: Fully qualified.<br>**Linux x86_64**: Pending runner qualification. | Warm cache: ~1.1s.<br>Cold cache: estimated ~5–15s for initial Go bridge compilation (timeout 120s). |
| `unit` | `apgr test unit [--workers <N>] [--summary-file <path>]` | Python 3.11+ with pinned pytest stack | Not required at runtime | Required: `APG_TYPESCRIPT_TSC` (`typescript@7.0.2` `tsc`) | Required: `APG_JAVASCRIPT_NODE` (v22.22.2 Nix store engine), `APG_NODEJS_PRIMARY_NODE`, `APG_NODEJS_SECONDARY_NODE`, `APG_NODEJS_OWNED_SCRATCH_ROOT` due to whole-inventory preflight in `run()` | **Darwin arm64**: Fully qualified.<br>**Linux x86_64**: **BLOCKED** by whole-inventory preflight binding Darwin arm64 Nix store digests. | Warm cache: ~19.5s with 8 workers (3,418 tests). |
| `integration` | `apgr test integration [--workers <N>] [--summary-file <path>]` | Python 3.11+ with pinned pytest stack | Required: Go 1.25+ at runtime (exercises Go CLI compilation in `cli.int.test.py`) | Required: `APG_TYPESCRIPT_TSC` | Required: `APG_JAVASCRIPT_NODE`, `APG_NODEJS_PRIMARY_NODE`, `APG_NODEJS_SECONDARY_NODE`, `APG_NODEJS_OWNED_SCRATCH_ROOT` | **Darwin arm64**: Fully qualified.<br>**Linux x86_64**: **BLOCKED** by whole-inventory preflight binding Darwin arm64 Nix store digests. | Full test execution with coverage checks. |
| `unit-integration` (`combined` / `apg-dev-gate`) | `apgr test unit-integration [--workers <N>] [--summary-file <path>]` | Python 3.11+ with pinned pytest stack | Required: Go 1.25+ at runtime (exercises Go CLI compilation in integration suite) | Required: `APG_TYPESCRIPT_TSC` | Required: `APG_JAVASCRIPT_NODE`, `APG_NODEJS_PRIMARY_NODE`, `APG_NODEJS_SECONDARY_NODE`, `APG_NODEJS_OWNED_SCRATCH_ROOT` | **Darwin arm64**: Fully qualified.<br>**Linux x86_64**: **BLOCKED** by whole-inventory preflight binding Darwin arm64 Nix store digests. | Union coverage gate (85/85% thresholds). |

**Whole-Inventory Preflight Note**: `run()` performs inventory-wide preflight checks (`requires_typescript_compiler`, `requires_javascript_engine`, `requires_node_profile_runtimes`) before executing test components. Because tests in the maintained repository inventory exercise compiler fixtures, the Nix-store JavaScript engine, and multi-profile Node.js runtimes, any execution through `run()` (`unit`, `integration`, or `combined`) requires these environment bindings. By contrast, `run_policy()` validates repository structure, inventory integrity, skill mechanical/corpus checks, and record identity without invoking external compiler or JavaScript engine checks.

## 4. Machine-Readable Summary Contract

When `--summary-file <path>` is provided, APGR emits a strictly formatted JSON
document adhering to JACA's subproject evidence contract:

```json
{
  "version": 1,
  "subproject": "apg",
  "suite": "policy",
  "test_status": "pass",
  "gate_status": "pass",
  "source_commit": "1111111111111111111111111111111111111111"
}
```

### Schema Properties
- `version` (`integer`, required): Always `1`.
- `subproject` (`string`, required): Always `"apg"`.
- `suite` (`string`, required): Name of the executed suite (`"policy"`, `"unit"`, `"integration"`, or `"combined"`; or sentinel `"unknown"` for argument parsing failures).
- `test_status` (`string`, required): `"pass"` if test assertions passed, `"fail"` on assertion failure, or `"error"` on invocation/configuration/harness fault.
- `gate_status` (`string`, required): `"pass"` if all coverage/policy gates were met, `"fail"` on gate shortfall or assertion failure, or `"error"` on invocation/configuration/harness fault.
- `source_commit` (`string`, required): Exact 40-character hexadecimal Git commit ID of `HEAD` at execution time (`git rev-parse HEAD`). Attests to HEAD commit identity only, not clean working tree state.

No supplementary fields are emitted to this file, preserving compatibility with
strict JSON decoders that enforce `DisallowUnknownFields()`.

The example commit is synthetic. CI illustrative fixtures use `example/apgr-fixture`
and synthetic base/head IDs; they are not records of actual pull requests.

## 5. Consumer-Owned Registration in JACA CI

### 5.1 Role Mapping

JACA CI maps its logical workflow roles to APGR entry points as follows:

| JACA Semantic Role | JACA Role ID | APGR Invocation | Expected Summary Path |
| --- | --- | --- | --- |
| PR Fast Policy | `apg-policy` | `apgr test policy --summary-file .test-reports/apg/policy/summary-$RUN_ID.json` | `.test-reports/apg/policy/summary-$RUN_ID.json` |
| PR Fast Unit | `apg-unit` | `apgr test unit --summary-file .test-reports/apg/unit/summary-$RUN_ID.json` | `.test-reports/apg/unit/summary-$RUN_ID.json` |
| Staging Gate Integration | `apg-integration` | `apgr test integration --summary-file .test-reports/apg/integration/summary-$RUN_ID.json` | `.test-reports/apg/integration/summary-$RUN_ID.json` |
| Promotion System Gate | `apg-dev-gate` | `apgr test unit-integration --summary-file .test-reports/apg/combined/summary-$RUN_ID.json` | `.test-reports/apg/combined/summary-$RUN_ID.json` |

*Note on Fresh Receipt Paths*: In automated CI pipelines, invocations should supply a distinct, run-specific target path (such as including `$RUN_ID` or a unique invocation token) rather than reusing a static file path, ensuring complete isolation across sequential or parallel attempts.

### 5.2 Consumer Ownership Boundary

Notice to JACA CI engineering team:
1. **Runner Registration**: In the JACA repository (`tools/ci/evidence.go`),
   `consumeRoleEvidence` has a closed switch currently enumerating `ci-policy` and
   `rnr-unit`. Registering `apg-*` roles in `consumeRoleEvidence`, `workflow.go`,
   and `trustedRoleOrder` is consumer-owned work in the JACA repository.
2. **Candidate Tree & Stability Verification**: JACA's CI runner (`tools/ci/candidate.go`
   and `tools/ci/runner.go`) computes prospective candidate trees (`candidateTree`)
   before and after role command execution to verify zero index mutation and zero
   untracked file leakage (`RunSummary.ExecutionSource{Commit, CandidateTree, Stable}`).
   APGR does not duplicate this calculation; APGR's summary file is written beneath
   the gitignored `.test-reports/` path so it does not alter candidate tree state.
3. **Execution Environment**: JACA CI provides the runner environment, manages
   timeout bounds, captures stdout/stderr streams to log files, and handles exit
   code aggregation.
4. **External Project Fixture Generalization**: The illustrative fixtures in
   `testing/fixtures/jaca_ci/` use schema `apgr-ci-illustrative-fixture-v1` and name
   the illustrative APGR repository. JACA's internal runner (`tools/ci/fixture.go`)
   currently validates strictly against its own repository identity
   and `canonicalBaseRef == "refs/heads/staging"` with `DisallowUnknownFields()`.
   For JACA to ingest external project PR fixtures directly, generalizing those
   identities and admitting project-scoped fields in JACA is consumer-owned work.

## 6. Measured Execution Timings & Resource Characteristics

Observed benchmark timings on local reference environment (Darwin arm64):

| Role / Suite | Measured Execution Time | Summary Artifact Size | Benchmark Context |
| --- | --- | --- | --- |
| `policy` | ~1.1s (warm cache) | 176 bytes | Full inventory validation, dependency versions, skill library mechanical & corpus identity check, record identity |
| `unit` | ~20–32s (8 workers) | 174 bytes | Pytest xdist across full unit test inventory with coverage gates (3,420 tests) |
| `integration` | ~760s (8 workers) | 181 bytes | Pytest xdist across full integration and CLI boundary inventory with coverage gates (621 tests passed, 2 skipped) |
| `unit-integration` (`combined`) | ~800s (8 workers) | 178 bytes | Sequential execution of unit and integration suites with combined union coverage merge (85/85% gates) |

### Notes on Execution and Measurement Scope
- **Deterministic Artifact Sizes**: Summary artifact sizes are deterministic JSON outputs governed by the 6-field schema:
  - When `test_status` and `gate_status` are `"pass"`: `policy` = 176 bytes, `unit` = 174 bytes, `integration` = 181 bytes, and `combined` = 178 bytes.
  - When `test_status` and `gate_status` are `"fail"`, output sizes are identical (both `"pass"` and `"fail"` are 4 ASCII bytes).
  - When a status field is `"error"` (5 ASCII bytes), the file size increases by exactly 1 byte per `"error"` field (+2 bytes when both `test_status` and `gate_status` are `"error"`: `policy` = 178 bytes, `unit` = 176 bytes, `integration` = 183 bytes, `combined` = 180 bytes).
- **Integrated Source Qualification**: All four suites (`policy`, `unit`, `integration`, and `unit-integration`) are fully qualified on Darwin arm64 under phase APG114 (Exit `00159`), satisfying all canonical coverage thresholds and machine-readable evidence contracts.
- **Cold-Cache Toolchain Characteristics**: In an unseeded runner where the Go build cache or Python bytecode is cold, the `policy` role will spend additional time compiling the Go-Python bridge (`verify-corpus`), taking an estimated ~5–15s (bounded by a 120s subprocess timeout). With a warm cache, measured execution is ~1.1s.


### APG114 source-binding qualification

The APG114 [exit record](../status/2026/09/06/00159-apg114-v090-integrated-source-qualification-exit.md)
identifies the closeout manifest, tested source inventory, summary receipt,
and platform/skip limitations. Earlier timings above remain producer
observations. Source-bound closeout qualification passed on Darwin arm64; the runner's
`source_commit` reports entry HEAD and does not attest changed working bytes.
JACA registration and Linux runner qualification remain consumer-owned.
