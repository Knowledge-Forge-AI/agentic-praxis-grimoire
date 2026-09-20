# APG162B / V0130-D-BOUNDARY2 — RTK Boundary and Authority Correction Exit

Phase ID: `APG162B`
Exit ID: `Exit 00217`
Roadmap Milestone: `V0130-D-BOUNDARY2`
Governing Decisions: [ADR 0072](../../../../adr/2026/09/0072-optional-rtk-integration-and-conditional-slices.md), [ADR 0071](../../../../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md), [ADR 0069](../../../../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md)
Exit Target: `V0130_D_QUALIFIED`

---

## 1. Status and Disposition

- **Disposition**: **checkpoint-ready** (V0130-D-BOUNDARY2 corrected across all R1–R3 requirements and verified against maintained suites, manager boundary probes, Go workspace, and skill governance; candidate tree left dirty unstaged for native V1 checkpoint finalization).
- **Candidate Lineage**: Reconstructed on exact APG162A candidate tree `63d8f98345b84ed6baa5b3646271fe59785191ed`, branch `v0.13.0/apg159-foundation`.
- **Milestone Outcome**: **checkpoint-ready pending manager acceptance** (R1 single package version authority `VERSION` = "0.12.0" and allowlist closure; R2 target project identity without sibling guessing; R3 conservative hook uncertainty, normal unavailability diagnostics at consumers, serializable fallback `as_dict`, and executed timeout probe accounting with direct child process reaping).
- **Execution Mode**: `gemini_flash_sub`, native V1 `work-reviewed` (produce, independent work review, revise_close), finalization `checkpoint`.
- **Review Checkpoint**: Exactly 1 dispatcher-owned review checkpoint. Dispatcher owns stage transitions, reviewer selection, and Git publication. Zero agent Git mutations (`git add`, `git commit`, `git push`, `git checkout`, `git branch`) executed.

---

## 2. Core Corrections

### 2.1 R1 — Single Package Version Authority and Allowlist Closure
- **Single Source Authority**: Maintained `src/agentic_praxis_grimoire/VERSION` ("0.12.0") as the sole authority for package versioning. `src/agentic_praxis_grimoire/__init__.py` cleanly imports `from .version import VERSION, __version__` without synthetic fallback strings.
- **Generation Store Allowlist**: Added `version.py` and `VERSION` to `ALLOWLIST` in `libexec/controller_generation_store.py`, ensuring native materialized generation stores retain version identity without falling out of allowlist scope.
- **Strict Validation & Rejection**: Missing or malformed package `VERSION` files are strictly rejected at import time with descriptive errors rather than silently suppressed.
- **Maintained Tests**: Added `test_materialized_generation_rtk_isolated` asserting `0.12.0` package identity and `test_version_authority_missing_and_malformed` verifying rejection on missing or corrupted version resources.

### 2.2 R2 — Explicit Target-Project Identity
- **Eliminate Sibling/Child Guessing**: Removed heuristic parent/sibling traversal in `src/agentic_praxis_grimoire/rtk.py`. `resolve_rtk_configuration` strictly uses `project_path.expanduser().absolute()`, preventing accidental adoption of unconfigured or sibling project settings.
- **Adapter Wiring**: Passed target project root explicitly in:
  - `libexec/claude_vc_profile.py`: Target resolved via `AGENT_CENTRAL_WORKER_WORKSPACE` or `Path.cwd()`.
  - `libexec/agent_phase/dispatch.py`: Passed `self.cwd` as project root and accurately threaded `worker_cap` state to guidance overrides.
  - `libexec/agent_phase/v2_dispatch.py`: Passed `work_tree` directly to `resolve_rtk_configuration`.
  - `libexec/agent_phase/v2_turns.py`: Dynamically determined `has_workers` based on execution mode (`gemini_flash_sub`, `gemini_flash_opus_sub`) and passed to guidance overrides; threaded `argv` through runner kwargs.
- **Contradictory & Isolation Tests**: Added `test_target_vs_controller_contradictory_config_isolation` verifying that target settings win over controller settings (and vice versa), and call-path tests covering both workers=False and workers=True variants.

### 2.3 R3 — Conservative Claude Hook Uncertainty, Diagnostics, and Probe Accounting
- **Conservative Matcher Parsing**: Implemented `_matcher_matches_bash` in `rtk.py` supporting `Bash`, `^Bash$`, `Bash|Read`, `Read|Bash`, and literal matchers. Unreadable or unsupported matcher patterns (e.g. unclosed regex brackets) fall back to `effective_mode: "off"` with clear diagnostics.
- **Double-Wrap Prevention**: When Claude declares `instructions` mode but an active matching PreToolUse hook is registered, switched effective mode to `hook` with diagnostic logging to prevent duplicate wrapping. Hook mode on Codex or Antigravity falls back safely to `off`.
- **Consumer Unavailability Diagnostics**: Surface normal unavailability (`status: "unavailable"`) visibly to stderr across consumers (`claude_vc_profile.py`, `dispatch.py`, `v2_dispatch.py`).
- **Serializable Fallback**: Provided JSON-serializable `as_dict` lambda on fallback resolution namespace (`SimpleNamespace`) across exception handlers.
- **Timeout Probe Accounting**: Enhanced `ProbeExecutionResult(tuple)` so that timed-out probes record `executed: True`, `started: True`, `timed_out: True`, `returncode: None`, and bounded partial stdout.
- **Reaping Wording**: Narrowed process-reaping documentation across status docs and code comments to "direct child process reaping".

---

## 3. Verification Matrix

| Check / Suite | Scope | Result | Details |
|---|---|---|---|
| `probe_boundaries.py` | Manager Boundary Diagnostics | **PASS** (16/16) | 100% pass across all 16 boundary cases with disposable fixtures and no real RTK. |
| `test_agent_phase_rtk.py` | RTK Dispatcher Suite | **PASS** (42/42) | Config resolution, deferred required rejection, bounded probes, Claude targeting, transport delivery, advertised digest fidelity, isolated homes, M1 tilde suite, M2 provider seams, R1 version authority, R2 contradictory isolation, R3 hook matcher patterns, double-wrap avoidance, runner boundary capture, consumer diagnostics, serializable fallback, and timeout execution recording. |
| `go test -count=1 ./...` | Full Go Workspace | **PASS** (20 ok, 1 [no test files]) | 20 ok packages and one package without tests under go1.25.10. |
| `go vet ./...` | Go Static Analysis | **PASS** | Clean, exit code 0. |
| `bin/apg-check-skill-library` | Canonical Skill Governance | **PASS** | 46 canonical skills, 46 catalog rows, 46 projections (11,507 bytes discovery ceiling). |
| `bin/apg-check-record-identity` | Record Identity Governance | **PASS** | 74 ADRs, 215 exits, 215 phase IDs; next ADR 0075; next exit 00218. |
| `git diff --check` | Whitespace Validation | **PASS** | Clean, zero whitespace errors. |

---

## 4. Operational Boundaries

- **Candidate Retained Dirty**: All modified and newly created paths remain dirty and unstaged.
- **No Git Publication**: Finalization is `checkpoint`; dispatcher owns review and commit.
- **Hermetic Execution**: Test suites isolate APGR_HOME, outbox, and project paths via temporary fixtures; live repository and operator provider settings isolated.
- **Raw Evidence Retained**: Distinct stdout/stderr pairs, exit codes, and test results preserved in foreground launcher evidence directory.
