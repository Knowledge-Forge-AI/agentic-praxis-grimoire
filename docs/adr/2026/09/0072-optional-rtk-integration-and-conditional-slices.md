# ADR 0072 — Optional RTK Integration as Declared Metadata and Conditional Instruction Slices

- Status: Accepted with amendments (APG162A; APG162C caller clarification accepted for local development integration)
- Date: 2026-09-20
- Phase: APG159 (Roadmap Stage: V0130-A)

## Context

RTK provides token-efficient command execution by compressing and filtering shell command output before it enters model context. In v0.12, static RTK guidance was inlined into standing instruction files across Claude, Codex, and Antigravity. However, this implementation had several limitations:
1. It lacked formal configuration, assuming RTK was universally present on PATH.
2. It lacked provider-mode awareness, treating hook-based transparent rewriting (Claude) and prompt-based command prefixing (Codex) identically.
3. It had no mechanism to omit RTK text when RTK was absent, disabled, or broken.
4. It lacked canonical skill representation in the APGR skill corpus.

At the same time, integrating RTK must not weaken system integrity: RTK must never bypass Git mutation brokers, never compress authoritative evidence (hashes, candidate verification, machine JSON), and never alter host settings or shell hooks automatically.

## Decision

### 1. Configuration as Declared Metadata
APGR adopts closed configuration keys under `[integrations.rtk]`:

```toml
[integrations.rtk]
enabled = true
executable = "/run/current-system/sw/bin/rtk"  # absolute path; symlinks resolved
required = false                               # strict required=true deferred; required must be false
minimum_version = "0.43.0"

[integrations.rtk.providers]
claude = "hook"          # hook | instructions | off
codex = "instructions"   # instructions | hook | off
antigravity = "instructions" # instructions | hook | off
```

- `executable` must be an absolute path and resolve to an executable regular file.
- `required = false` is the only supported ordinary operational default. When RTK is absent, disabled, or broken, APGR logs an observation and proceeds with RTK instructions omitted.
- Configuration is declared metadata in APGR configuration, not an unverified token savings claim.

### 2. Bounded Availability and Identity Probe
APGR requires run-owned executable qualification before RTK guidance slices are rendered active:
- Probes are strictly bounded (<= 5s) read-only operations with streaming capture capped at 64 KB, monotonic deadlines, and prompt process reaping.
- `rtk --version` must confirm product identity (`rtk` banner) and semver compatibility against `minimum_version`. Unrelated banners or incompatible versions reject availability.
- `rtk hook check "git status"` verifies rewriting functionality as data; hook command strings or arbitrary shell commands are never executed.
- Merely verifying executable binary presence (`run_probes=False`) does not fabricate qualified availability; unqualified executables yield `status = "unavailable"` with diagnostic context and fall back to ordinary uncompressed dispatch.
- Probes are non-mutating and run once per execution context; no persistent daemon or background liveness gate is introduced.

### 3. Canonical Skill Adoption within Discovery Ceiling
The provisional skill `skills/rtk-command-proxy/SKILL.md` is approved for adoption as the 46th canonical skill, **subject to formal qualification in milestone V0130-D**.

Per `libexec/apg_skill_library_check.py:439,1399`, the discovery ceiling is enforced strictly on a **pure description-byte basis**:
- Current 45 canonical skills: 11,142 bytes.
- Measured `rtk-command-proxy` candidate description: 268 bytes.
- Projected corpus size: 11,410 bytes, leaving 97 bytes of headroom under the `v0.10-browser-runtime` ceiling of 11,507 bytes.

Because the skill fits within existing capacity, no ceiling increase is authorized for this adoption. Any subsequent (47th) skill in v0.13 will require a new measured discovery policy.

### 4. Conditional Instruction Slices and Baseline Correction
- **Instruction Slices**: Standing instructions render provider-specific slices based on effective mode: `hook` instructs the model to issue ordinary commands; `instructions` provides shell output efficiency guidance and recommends RTK-proxied forms for supported commands without prescribing prefixing every command; `off` omits RTK text entirely. Disabled or unavailable RTK leaves ordinary work available without RTK guidance.
- **Hook uncertainty**: Claude hook mode requires known registration and targeting of the configured executable. Unconfirmed registration, targeting, or an unrecognized matcher yields effective `off` with diagnostics. Codex and Antigravity do not support hook mode. Declared mode remains separately reported.
- **Conflict avoidance**: Declared Claude `instructions` switches to effective `hook` when a matching, targeted hook is known, avoiding manual double-prefixing. Registration and targeting do not prove that a hook ran or compacted any command output; guidance describes that effect conditionally.
- **Matcher boundary (F8)**: Inspection recognizes literal `Bash`, `^Bash$`, and common tool alternations such as `Bash|Read` and `Read|Bash`. Other strings currently use Python regular-expression search against `Bash`; invalid expressions are unknown. This is bounded static inspection, not qualification of all Claude matcher semantics, a JavaScript regex engine, or shell-wrapper execution. Cross-dialect matcher equivalence remains unqualified.
- **Corrected Static Baseline**: Removing RTK text when disabled changes prompt bytes compared to v0.12. The v0.13 static baseline is explicitly corrected for this versioned delta rather than pretending prompt bytes remain identical.

### APG162C caller correction

V2 worker guidance uses the maintained worker-capability resolver with the
selected provider, profile, execution mode and process posture. Read-only
bindings conservatively skip worker resolution and do not gain worker or Bash
permissions. Missing, broken or denied optional workers leave ordinary parent
execution available. Capability eligibility qualifies advertising only: V2 does
not yet establish V1-equivalent ParentLedger registration, worker context,
worker-envelope admission or Astra native binding. Actual V2 worker execution
remains unqualified (review advisory A1); this checkpoint does not close that gap.

V1 and Claude distinguish an explicit project selection from a discovery start.
An explicit config-free target remains authoritative; nested starts use the
maintained Git-marker discovery owner and stop at the nearest repository, even
when it has no project configuration. An ancestor `.apgr` directory alone is
not a project marker. A failed search does not restart at an unrelated ambient
directory. V1 passes the explicit root and original discovery start to Claude
through dedicated APGR target context, independently of worker workspace and
provider execution directory. Selected operator-home precedence is preserved.
The APG162C checkpoint does not itself accept milestone D.

### 5. Read-Only Doctor
`apgr integrations rtk doctor` provides non-mutating diagnostics inspecting configured executables, digests, provider hook registrations, and skill discovery. It never creates, edits, or installs hooks, settings, or project rules.

### 6. Raw Authoritative Evidence
RTK output is an advisory human-facing optimization. Canonical evidence—including Git commit hashes, candidate tree diffs, machine JSON reports, and candidate verification receipts—must always be obtained via raw, uncompressed commands.

## Consequences

- RTK is safely utilized where available without making it a brittle operational dependency.
- Provider prompts receive accurate, mode-appropriate guidance.
- Discovery ceiling invariants are preserved without arbitrary inflation.

## APG163 entry reconciliation

The manager/operator accepts V0130-D for local development integration through
APG162C-LOCAL-FINALIZE1. The checkpoint lifecycle and its original review
freshness remain unchanged. V2 worker admission, matcher dialect equivalence,
and diagnostic style remain bounded documented limitations. No D tests or
finalization are replayed by E; the factual Git addendum is in Exit 00218.
