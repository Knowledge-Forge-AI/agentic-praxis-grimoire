# APG162A / V0130-D-INTEGRATION1 — RTK Integration Correction and Qualification Exit

Phase ID: `APG162A`
Exit ID: `Exit 00216`
Roadmap Milestone: `V0130-D-INTEGRATION1`
Governing Decisions: [ADR 0072](../../../../adr/2026/09/0072-optional-rtk-integration-and-conditional-slices.md), [ADR 0071](../../../../adr/2026/09/0071-apgr-home-layout-and-portable-hosting-seams.md), [ADR 0069](../../../../adr/2026/09/0069-v0-13-program-scope-and-dispatcher-reference-doctrine.md)
Exit Target: `V0130_D_QUALIFIED`

---

## 1. Status and Disposition

- **Disposition**: **checkpoint-ready** (V0130-D-INTEGRATION1 corrected across all M1–M3 areas and evidence reconciliation; candidate tree left dirty unstaged for native V1 checkpoint finalization).
- **Candidate Lineage**: Adopted all 41 candidate paths from APG162 (`2e126852bf1a6d95980ee5b999667d488204c945`) on committed C parent `7e3a61b5055255f697309cefc63dbe9c92e0461d`, branch `v0.13.0/apg159-foundation`.
- **Milestone Outcome**: **checkpoint-ready pending manager acceptance** (M1 ordinary path restoration, M2 native generation closure and transport branch wiring, M3 streaming bounded probes, product banner verification, isolated hook targeting, and skill provenance qualified; checkpoint only pending manager acceptance).
- **Execution Mode**: `gemini_flash_sub`, native V1 `work-reviewed` (produce, independent work review, revise_close), finalization `checkpoint`.
- **Publication Authority**: Dispatcher owns stage transitions, reviewer selection, and Git publication. Zero agent Git mutations (`git add`, `git commit`, `git push`, `git checkout`, `git branch`) executed.

---

## 2. Core Corrections

### 2.1 M1 — Ordinary Path Semantics Restored
- Restored `Path(raw).expanduser()` in `src/agentic_praxis_grimoire/config.py::_absolute` for ordinary configuration paths and outbox values, permitting established home tilde expansion (`outbox_root = "~/Documents/agent/outbox"`).
- Restricted strict tilde and dollar rejections strictly to the RTK executable field boundary (`_validate_executable_path`), ensuring that disabled or broken RTK never invalidates an otherwise valid operator configuration.
- Added maintained tests for tilde outbox and tilde config path across canonical and native config owners, disabled and enabled RTK, and strict executable rejection.

### 2.2 M2 — Native Generation Closure and Transport Seams
- Added minimal admitted source closure (`src/agentic_praxis_grimoire/__init__.py`, `paths.py`, `config.py`, `rtk.py`) to `ALLOWLIST` in `libexec/controller_generation_store.py`.
- Restored strict literal ancestor symlink validation in `no_symlinks` with narrow Darwin system-root exemption (`/var`, `/tmp`, `/etc`) to preserve accepted-C security posture while accommodating macOS temp directories.
- Eliminated persistent `sys.path` pollution in `Dispatcher._ensure_rtk_resolution` and `libexec/claude_vc_profile.py` using structured `try...finally` cleanup blocks.
- On exception or failure across all three seams (`dispatch.py`, `v2_dispatch.py`, `claude_vc_profile.py`), emitted visible stderr diagnostics and returned diagnostic `SimpleNamespace` rather than silent `None`, preventing false positive caching.
- Resolved Claude launcher target project root reliably across provider directories and grandparent structures (`resolve_rtk_configuration`), and passed launcher-selected isolated settings view.
- Wired Antigravity guidance in `libexec/agent_phase/dispatch.py` when worker availability is absent or not permitted.
- Wired Codex guidance overrides for both ordinary invocations and native-worker invocations.
- Wired V2 dispatch and turns integration (`libexec/agent_phase/v2_dispatch.py`, `libexec/agent_phase/v2_turns.py`).
- Added maintained tests exercising Claude launcher isolation and final argv prompt bytes, Dispatcher resolution, V2 turns, and materialized generation closure.

### 2.3 M3 — Bounded Probes, Truthful Hook Eligibility, and Skill Standards
- **Streaming Bounded Capture**: Implemented `_execute_bounded_probe` using `subprocess.Popen` with `selectors` streaming capture capped at 64 KB, monotonic deadlines, direct child process reaping, and Unicode replacement with diagnostic logging. Zero calls to `subprocess.run` in probe paths.
- **Product Banner & Version Verification**: Verified product banner begins with `rtk` (case-insensitive) and parsed semver against `minimum_version`. Unrelated banners and old versions yield `status = "unavailable"` with diagnostic entries.
- **Isolated Hook Targeting**: Honored launch isolation arguments (`--setting-sources ""`, `--settings`), handled non-dict JSON settings gracefully without `AttributeError`, verified hook command using `_is_rtk_hook_command`, rejected unrelated shell text (e.g., `echo hook claude`), and set `effective_mode = "off"` on target mismatch or unresolved bare targeting. Gated hook slice wording on registered and targeted PreToolUse hook rather than asserting active rewriting.
- **Shell Quoting**: Ensured configured executables containing spaces are quoted as a single shell word in rendered instruction examples.
- **Canonical Skill Provenance**: Added truthful APGR authorship and provisional status statement to `skills/rtk-command-proxy/SKILL.md` while preserving the exact 7-H2 canonical section structure and 268-byte frontmatter description. Clarified that 'stop or escalate' on a missing binary means stopping RTK optimization, not blocking user work. Clarified that meta commands are task-authorized operations.

---

## 3. Verification Matrix

| Check / Suite | Scope | Result | Details |
|---|---|---|---|
| `probe_rtk_candidate.py` | Manager Boundary Diagnostics | **PASS** (19/19) | 100% pass across all 18 executed boundary checks and 1 AST source check. |
| `probe_generation.py` | Materialization Diagnostics | **PASS** (2/2) | Verified native materialization closure and diagnostic retention. |
| `test_agent_phase_rtk.py` | RTK Dispatcher Suite | **PASS** (33/33) | Config resolution, deferred required rejection, bounded probes, Claude targeting, transport delivery, advertised digest fidelity, isolated homes, M1 tilde suite, M2 provider seams. |
| `test_agent_phase_config_routing.py` | Dispatcher Config Routing | **PASS** (23/23) | Closed schema validation, precedence, operator bundles, V1 roster reuse. |
| `test_source_guidance_portability.py` | Standing Instruction Portability | **PASS** (4/4) | Byte length assertions, source and rendered digest portability. |
| `apg_skill_library_check.unit.test.py` | Python Skill Check Unit Suite | **PASS** (110/110) | 46-skill policy invariants, reservation theft, boundaries, Go source parity. |
| `apg_project_skills_core.unit.test.py` | Skills Core Unit Suite | **PASS** (14/14) | State parser, projection queries, exclude parser, snapshot handling. |
| `go test -count=1 ./...` | Full Go Workspace | **PASS** (20 ok, 1 [no test files]) | 20 ok packages and one package without tests under go1.25.10. |
| `go vet ./...` | Go Static Analysis | **PASS** | Clean, exit code 0. |
| `bin/apg-check-skill-library` | Canonical Skill Governance | **PASS** | 46 canonical skills, 46 catalog rows, 46 projections. |
| `bin/apg-check-record-identity` | Record Identity Governance | **PASS** | 74 ADRs, 214 exits, 214 phase IDs; next ADR 0075; next exit 00217. |
| `git diff --check` | Whitespace Validation | **PASS** | Clean, zero whitespace errors. |

---

## 4. Operational Boundaries

- **Candidate Retained Dirty**: All modified and newly created paths remain dirty and unstaged.
- **No Git Publication**: Finalization is `checkpoint`; dispatcher owns review and commit.
- **Hermetic Execution**: Test suites isolate APGR_HOME, outbox, and project paths via temporary fixtures; live repository and operator provider settings isolated.
- **Raw Evidence Retained**: Distinct stdout/stderr pairs, exit codes, and test results preserved in foreground launcher evidence.
