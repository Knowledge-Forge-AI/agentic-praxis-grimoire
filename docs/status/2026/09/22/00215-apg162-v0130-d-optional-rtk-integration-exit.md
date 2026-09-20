# APG162 / V0130-D — Optional RTK Integration and Conditional Instruction Slices Exit

Phase ID: `APG162`
Exit ID: `Exit 00215`
Roadmap Milestone: `V0130-D`
Governing Decisions: [ADR 0072](../../../../adr/2026/09/0072-optional-rtk-integration-and-conditional-slices.md), [ADR 0071](../../../../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md), [ADR 0069](../../../../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md)
Exit Target: `V0130_D_QUALIFIED`

---

## 1. Status and Disposition

- **Disposition**: **checkpoint-completed** (Native V1 work-reviewed checkpoint completed successfully; manager review withheld V0130-D product acceptance pending APG162A focused correction).
- **Candidate Checkpoint**: `2e126852bf1a6d95980ee5b999667d488204c945` on committed C base `7e3a61b5055255f697309cefc63dbe9c92e0461d`.
- **Milestone Outcome**: **CHECKPOINT_RETAINED / CORRECTION_AUTHORIZED** (V0130-D optional RTK integration candidate preserved; manager authorized APG162A / V0130-D-INTEGRATION1 for M1–M3 and evidence reconciliation).
- **Execution Mode**: `gemini_flash_sub`, native V1 `work-reviewed` (produce, independent work review, revise_close), finalization `checkpoint`.
- **Publication Authority**: The dispatcher owns stage transitions, reviewer selection, and Git publication. No agent Git mutation (`git add`, `git commit`, `git push`, `git checkout`, `git branch`) executed.

---

## 2. Core Deliverables (D1–D5)

### 2.1 D1 — Closed Configuration Schema and Resolution
- **Closed Configuration Table**: Added `[integrations.rtk]` closed schema in `src/agentic_praxis_grimoire/config.py` and `libexec/agent_phase/config_routing.py` supporting `enabled` (bool), `required` (bool), `executable` (str), `claude` (str: `off` | `instructions` | `hook`), `codex` (str: `off` | `instructions` | `hook`), and `antigravity` (str: `off` | `instructions` | `hook`).
- **Deferred Required Rejection**: Default configuration sets `required = false`. Explicit configuration specifying `required = true` is strictly rejected with `ConfigError("strict rtk required=true is deferred; required must be false")` across both Python library resolution and dispatcher config routing.
- **Path and Key Validation**: Unknown keys under `[integrations]` or `[integrations.rtk]` fail closed with `ConfigError`. Custom executables must specify absolute paths or standard base name; non-absolute path strings with directory separators, tildes, and shell variables are strictly rejected.
- **Precedence Hierarchy**: Resolution evaluates Project configuration (`.apgr/config.toml`) > Operator custom configuration (`<APGR_HOME>/config.toml`) > Built-in defaults (`enabled = false`, `required = false`, `executable = "rtk"`). Detailed field-level provenance tracking (`RTKFieldProvenance`) records the winning source tier for each setting.
- **Single-Read Configuration Byte Capture**: Captured configuration bytes once for parsing and SHA-256 digest calculation; carried resolved `RTKResolution` to consumers without repeated disk reads. When disabled, skips ambient and provider-home directory inspections completely.

### 2.2 D2 — Read-Only Doctor CLI Diagnostics
- **Cross-Language Doctor CLI**: Registered `apgr integrations rtk doctor [--json]` CLI across Python (`src/agentic_praxis_grimoire/rtk.py`, `src/agentic_praxis_grimoire/cli.py`) and Go companion (`internal/cli/integrations.go`, `internal/cli/cli.go`). Go companion accepts `--from-json <file>` for typed viewing without spawning Python subprocesses.
- **Bounded Diagnostic Probes**: Executes non-mutating sub-process probes with strict 5-second timeouts for `rtk --version` and `rtk hook check "git status"`, capturing stdout, stderr, exit codes, and latency in milliseconds. Both stdout and stderr are strictly capped at 64KB (`MAX_PROBE_OUTPUT_BYTES = 64 * 1024`) with truncation diagnostics.
- **Launch-Selected Host Settings Inspection**: Non-mutating inspects Claude desktop and CLI settings (`Library/Application Support/Claude/claude_desktop_config.json`, `~/.claude/settings.json`, and `<APGR_HOME>/claude/settings.json`), honoring launch-selected settings (`--settings`), checking for `PreToolUse` hook matcher targeting Bash and executing `rtk hook claude`, and honestly evaluating targeting (`bare_rtk_unresolved` vs `matches_configured_executable`).
- **Canonical Skill Discovery Inspection**: Non-mutating verifies discovery and projection symlink of provisional skill `rtk-command-proxy`.
- **Zero Mutation Guarantee**: The doctor command never mutates host configurations, never installs shell hooks, and never alters repository rules. Disabled resolution executes zero subprocess probes.

### 2.3 D3 — Conditional Instruction Slices & No-RTK Golden Baselines
- **Golden Baseline Restorations**: Restored exact byte-identical no-RTK golden baselines across all static standing instructions:
  - `codex/AGENTS.md`: exactly **7,698 bytes**
  - `claude/CLAUDE.md`: exactly **11,035 bytes**
  - `antigravity/GEMINI.md`: exactly **3,196 bytes**
- **Dynamic Conditional Slices & Transport Wiring**: Implemented `render_rtk_slice(provider, mode, executable)` in `libexec/agent_source_guidance.py` generating provider-specific instructions:
  - `off`: returns empty string, preserving static golden baseline without injection.
  - `instructions`: injects prompt-based prefixing guidance referencing the configured executable (`rtk`).
  - `hook`: injects advisory hook guidance clarifying transparent compaction without manual double-prefixing.
- **Production Caller Transport Integration**: Wired `_ensure_rtk_resolution()` into Antigravity dispatch (`libexec/agent_phase/dispatch.py:703`), Codex dispatch (`dispatch.py:776`), and Claude launcher (`libexec/claude_vc_profile.py:1195`), carrying resolved `RTKResolution` to all transport callers.
- **Advertised vs Delivered Digest Consistency**: Emitted `Source standing instructions ({path}; sha256={rendered_digest})` so the advertised sha256 in transport prompts strictly matches the delivered byte content.
- **SourceGuidance Backward Compatibility**: Enhanced `SourceGuidance` named tuple in `libexec/agent_source_guidance.py` preserving full `(prompt, permissions)` compatibility while exposing `.source_digest` and `.rendered_digest` for transport and audit verification.
- **Doctrinal Preservation**: Preserved PreToolUse bash hook policy in `claude/CLAUDE.md` and aligned Antigravity modes to `{"instructions", "hook", "off"}`.

### 2.4 D4 — Provisional Canonical Skill `rtk-command-proxy`
- **Canonical Skill Standard**: Authored `skills/rtk-command-proxy/SKILL.md` strictly adhering to the 7-H2 standard, with exact 268-byte frontmatter description (total file size 5,702 bytes).
- **Skill Projection**: Created canonical projection symlink `.agents/skills/rtk-command-proxy -> ../../skills/rtk-command-proxy`.
- **Discovery Policy Admission**:
  - Updated discovery policy across Python (`libexec/apg_skill_library_check.py`) and Go (`skills/discovery_policy.go`, `skills/discovery_policy_test.go`, `skills/corpus_test.go`).
  - Admitted skill count advanced from 45 to 46 leaves (14 stable / 32 provisional).
  - Total discovery description bytes: 11,410 bytes, preserving 97 bytes of headroom below the 11,507-byte ceiling.
  - Enforced byte-identical description freeze for `FrozenRTKCommandProxySkillDescription` with strict reservation theft diagnostics (`APG044`).
- **Metadata Synchronization**: Regenerated `src/agentic_praxis_grimoire/resources/skill-metadata.json` (23,382 bytes), updated `skills/agentic-praxis-grimoire-workflow/references/capability-map.json`, and updated `skills/README.md`.

### 2.5 D5 — Governance Records and Test Suite
- **Dispatcher Test Suite**: Authored comprehensive test suite `src/test/dispatcher/test_agent_phase_rtk.py` with 26 tests validating closed configuration parsing, deferred required=true rejection, bounded probes (including 64KB output truncation and 5s timeouts), injected fixture executables, isolated provider-home inspection, doctor JSON/text output, CLI dispatch, transport prompt delivery with exact advertised digests across Antigravity, Codex, and Claude, golden baseline byte lengths, and skill invariants.
- **Regression Suite Hardening**: Fixed and verified all directly affected regression suites for 46 skills (`mdx-profile`, `jsx-language-profile`, `css-language-profile`, `markdown-language-profile`, `typescript-language-profile`, `apg_css_candidate_contract`, and `private/oracles/tests/skills.unit.test.py`).
- **Go Unit Tests**: Authored 8 unit tests in `internal/cli/integrations_test.go` covering Go companion parsing, execution, and flag handling.
- **Documentation**: Updated ADR 0072 with required=true deferral rationale, documented CLI command in `docs/reference/cli.md`, and recorded milestone exit in `docs/v0-13-roadmap.md`.

---

## 3. Verification Matrix

| Check / Suite | Scope | Result | Details |
|---|---|---|---|
| `test_agent_phase_rtk.py` | RTK Dispatcher Suite | **PASS** (26/26) | Config resolution, deferred required rejection, bounded probes (64KB cap, timeout), injected executables (symlinks, spaces, wrong product, old version), Claude targeting, transport delivery, advertised digest fidelity, isolated homes. |
| `internal/cli/integrations_test.go` | Go Companion CLI | **PASS** (8/8) | Go RTK doctor parsing, JSON formatting, flag handling, scope labelling. |
| `apg_skill_library_check.unit.test.py` | Python Skill Check Unit Suite | **PASS** (110/110) | 46-skill policy invariants, reservation theft, boundaries, Go source parity. |
| `test_agent_phase_config_routing.py` | Dispatcher Config Routing | **PASS** (23/23) | Closed schema validation, precedence, operator bundles, V1 roster reuse. |
| `test_source_guidance_portability.py` | Standing Instruction Portability | **PASS** (4/4) | Byte length assertions, source and rendered digest portability. |
| Skill Regression Suites (MDX, CSS, JSX, MD, TS) | Directly affected skill suites | **PASS** (244/244, 1 skipped) | Live repository surface count assertions aligned to 46 skills. |
| `private/oracles/tests/skills.unit.test.py` | Private Skill Oracle | **PASS** (21/21) | 46 skills, 11,410 bytes, 97 bytes headroom. |
| `go test -count=1 ./...` | Full Go Workspace | **PASS** (21 packages) | Clean pass across all 21 Go packages under go1.25.10. |
| `go vet ./...` | Go Static Analysis | **PASS** | Clean, exit code 0. |
| `bin/apg-check-skill-library` | Canonical Skill Governance | **PASS** | 46 canonical skills, 46 catalog rows, 46 projections. |
| `bin/apg-check-record-identity` | Record Identity Governance | **PASS** | 74 ADRs, 213 exits, 213 phase IDs; next ADR 0075; next exit 00216. |
| `git diff --check` | Whitespace Validation | **PASS** | Clean, zero whitespace errors. |

*Evidence reconciliation note*: Raw evidence in the APG162 packet corroborated 163 passes across 4 files and 20 Go ok packages with clean vet. Additional suite totals (253, 244, 167) were reported runs. Manager disposition retained checkpoint `2e126852bf1a6d95980ee5b999667d488204c945` and authorized APG162A for M1–M3 correction.

---

## 4. Operational Boundaries

- **Candidate Retained Dirty**: All modified and newly created paths remain dirty and unstaged.
- **No Git Publication**: Finalization is `checkpoint`; dispatcher owns review and commit.
- **Isolated State**: No operations against live shared database (`~/.apgr/state/dispatcher.sqlite3`); all tests execute in hermetic temporary fixtures.
- **Zero Host Mutation**: No host settings, shell configurations, or project rules were mutated.

---

## 5. Independent Review Findings Disposition

| Finding ID | Classification | Candidate Disposition | Resolution Summary |
|---|---|---|---|
| Defect 1 | Required | **Amended** | Wired `_ensure_rtk_resolution()` in `Dispatcher` (`libexec/agent_phase/dispatch.py`), Antigravity dispatch, Codex dispatch, and Claude launcher (`libexec/claude_vc_profile.py`). Tested at transport level in `test_agent_phase_rtk.py`. |
| Defect 2 | Required | **Amended** | Updated directly affected skill regression test suites (`mdx-profile`, `jsx`, `css`, `markdown`, `typescript`, `apg_css_candidate_contract`, `private/oracles/tests/skills.unit.test.py`) for 46 skills. All pass 100%. |
| Defect 3 | Required | **Amended** | Disabled/unconfigured RTK resolution skips provider-home directory inspections (`~/.claude`, `<home>/claude`). Tested in `test_agent_phase_rtk.py`. |
| Defect 4 | Required | **Amended** | Updated `libexec/agent_source_guidance.py` line 311 to emit `sha256={rendered_digest}`, ensuring advertised digest matches exact delivered prompt bytes. Tested in `test_agent_phase_rtk.py`. |
| Defect 5 | Required | **Amended** | Bound Claude hook inspection to launch-selected settings (`--settings`), evaluate targeting honestly (`bare_rtk_unresolved` vs `matches_configured_executable`), and report diagnostics. |
| Finding 6 | Advisory | **Amended** | Implemented `MAX_PROBE_OUTPUT_BYTES = 64 * 1024` (64KB cap) on stdout and stderr in `run_rtk_probes` with truncation diagnostics. Tested with oversize output fixture. |
| Finding 7 | Advisory | **Amended** | Expanded `test_agent_phase_rtk.py` from 17 to 26 tests with injected fixture executables (spaces, symlinks, non-executable, wrong-product, old-version, timeout, oversize). |
| Finding 8 | Advisory | **Amended** | Isolated test fixtures: hermetic per-case temporary homes, eliminating ambient host dependencies. |
| Finding 9 | Advisory | **Amended** | Removed expanduser/tilde from executable path resolution; removed bare `"rtk"` fallback in `_extract_rtk_mode_and_executable`. |
| Finding 10 | Advisory | **Amended** | Removed Python subprocess execution in `internal/cli/integrations.go`; requires `--from-json <file>` with explicit supplied-JSON scope header. |
| Finding 11 | Advisory | **Amended** | Aligned ADR 0072: removed SQLite references, fixed dispatch-time probe claim, and clarified advisory prefixing guidance. |
| Finding 12 | Advisory | **Amended** | Restored full non-slice PreToolUse policy sentence in `claude/CLAUDE.md`. |
| Finding 13 | Advisory | **Amended** | Aligned Antigravity provider modes to `{"instructions", "hook", "off"}` across code, ADR, and exit docs. |
| Finding 14 | Advisory | **Amended** | Captured configuration bytes once (`read_bytes()`), compute digest once, and pass to `load_config`; reused `resolution.configuration_sources` in `doctor_report`. |
| Finding 15 | Advisory | **Noted** | Provenance and provisional status verified in catalog, discovery policy, capability map, and exit records. |
| Finding 16 | Advisory | **Accepted** | Narrative accuracy clarified: all qualification runs performed synchronously in foreground without background tasks. |

