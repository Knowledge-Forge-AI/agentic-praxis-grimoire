# ADR 0061 — First-Class Provider Capability Matrix and Asymmetry Reconciliation

- Status: Accepted
- Date: 2026-09-16
- Phase: APG146 (Roadmap Stage: V0120-A)

## Context

In Agent-Central's prototype dispatcher, provider implementations grew organically around specific tooling: Codex via CLI and JSON protocol, Claude via Anthropics CLI wrappers, and Antigravity via IDE sidecars or local CLI profiles. This organic growth resulted in behavioral asymmetries across providers:
1. Inconsistent profile compilation and option flags across providers.
2. Divergent activity-pipe and liveness monitoring (varying timeout thresholds, inconsistent detection of silence vs progress).
3. Uneven support for thinking/reasoning modes, schema enforcement, and tool definitions.
4. Varying command and file mutation security controls across runner scripts.

To serve as a production-grade single-phase execution runtime, APGR must establish Codex, Claude, and Antigravity as first-class provider targets with normalized capabilities and explicit conformance standards.

## Decision

1. **First-Class Provider Targets**:
   Codex, Claude, and Antigravity are formal first-class execution provider targets in APGR.

2. **Provider Capability and Conformance Matrix**:
   APGR establishes a normalized capability matrix covering:
   - **Invocation and Transport**: Subprocess lifecycle management, argument construction, clean environment isolation, and standard process group isolation (`setpgid`).
   - **Stream and Output Capture**: Line-buffered stdout/stderr streaming, activity tracking, and bounded turn-log capture.
   - **Liveness and Silence Monitoring**: A normalized advisory silence observation threshold (900 seconds) and an absolute outer timeout ceiling (90,000 seconds) across all provider process wrappers.
   - **Reasoning / Extended Thinking**: Explicit declaration of thinking token budgets and reasoning effort controls.
   - **Structured Outputs**: Native JSON schema enforcement where supported by the underlying CLI/API.
   - **Tool Group Integration**: Definition and injection of read tools, write tools, and diagnostic execution tools.

3. **Reconciling Upstream Asymmetries**:
   - Where upstream CLIs support equivalent functionality (e.g., streaming output capture, clean environment injection, token budget configuration), APGR standardizes configuration parameters across all three providers.
   - **Fail-Closed on Unsupported Features**: Where an upstream provider lacks a capability (e.g., native schema constrained generation, subagent delegation, specific tool execution modes), APGR enforces explicit refusal or declared absence. APGR will **not** attempt weak, brittle software emulation of missing upstream provider capabilities.
   - **Precedence over routing fail-open**: This fail-closed rule takes precedence over the unknown-usage fail-open default in ADR 0060 §3. Capability eligibility is evaluated before usage state; an ineligible provider is never selected on the strength of favourable or unknown quota.

4. **Minimal Command and Security Brokering**:
   - Standalone APGR enforces minimal, high-assurance security brokering.
   - It guarantees repository fence boundaries and prevents mutation of Git metadata (`.git/`) or out-of-bounds filesystem paths.
   - **Evidence vs Abortion**: If a nominally read-only role (such as `Plan Reviewer` or `Work Reviewer`) produces unexpected source modifications, APGR does not automatically abort or crash the phase unless a fatal runtime integrity invariant (e.g., git index corruption) is violated. Instead, unexpected modifications are captured, isolated, and emitted as typed diagnostic evidence for the subsequent dispositioner or operator to evaluate.

## Alternatives Considered

- **Emulating Missing Capabilities**: Rejected. Software approximations (such as parsing unconstrained text to simulate structured JSON schema support) lead to fragile failure modes, hallucinations, and false guarantees.
- **Aggressive Execution Abort on Minor Read-Only Edits**: Rejected. Models occasionally emit temporary scratch files or formatting touches. Crashing an entire multi-stage phase over a minor non-fatal file touch wastes tokens; treating unexpected edits as reviewable evidence preserves both progress and auditability.

## Consequences

- In stage `V0120-D`, APGR will implement normalized provider adapters for Codex, Claude, and Antigravity following the capability matrix.
- Provider catalogs and profile templates in `common/dispatcher/` and `antigravity/`, `claude/`, `codex/` will be synchronized and validated.
