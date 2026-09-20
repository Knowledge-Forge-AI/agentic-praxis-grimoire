# ADR 0062 — v0.12 Release Hardening, Operator Discipline, and Conditional Nixpkgs Policy

- Status: Accepted
- Date: 2026-09-16
- Phase: APG146 (Roadmap Stage: V0120-A)

## Context

The APGR v0.11.0 release sequence surfaced crucial operational edge cases across hosted CI, multi-channel distribution, and GitHub API interactions. Achieving terminal publication required 13 hosted CI / operator repair increments (`R1`–`R13`, exit `00190`) and 12 publication-stage finding remediations (`F1`–`F12`, `private/releases/v0.11.0/publication1/README.md` §1). Those identifiers belong to the historical records and are not reassigned; `docs/architecture/v0-12-v011-publication-regression-inputs.md` owns the derived `REG-R*` / `REG-P*` test namespace and carries the `F1`–`F12` traceability table. The hard lessons learned during this process must be codified as durable invariants for v0.12 and subsequent releases.

Additionally, while APGR currently publishes to GitHub Releases, Go, PyPI, npm, and Homebrew, packaging for Nixpkgs has been discussed across Knowledge Forge AI projects. Establishing clear criteria for evaluating Nixpkgs admission without premature or speculative policy formulation is required.

## Decision

1. **Codifying Release Operator Hardening Invariants**:
   For v0.12 and subsequent releases, APGR's release automation and operator tooling must enforce the following invariants:
   - **Numeric Draft Release ID Binding**: To avoid race conditions and tag-name ambiguity in the GitHub API, release asset uploads and publication operations must bind directly to the immutable numeric draft release ID.
   - **Strict Release Authority Invariant**: A valid release candidate must be a single-parent squashed commit whose parent is the preceding public release, whose tree matches the projected publishable source tree, whose commit subject matches the version contract (`Release vX.Y.Z`), and whose assets match signed checksum manifests. (Historical commit and tree identities are preserved in regression input evidence documents rather than hardcoded as gates in release policy).
   - **Trusted PyPI Publication Alignment**: Maintain OIDC trusted publishing alignment with GitHub Actions release workflows, compatible with the manual squash release procedure.
   - **npm Distribution State Machine**: The npm publishing workflow must explicitly handle intermediate states (`accepted`, `processing`, `published`) and verify tarball payload byte parity against the distribution manifest.
   - **Resumable Multi-Channel Publication Receipts**: Each publication channel (GitHub, Go, PyPI, npm, Homebrew) must emit an independent, durable receipt. If a failure occurs on one channel, the operator can resume publication on remaining channels without re-executing completed channels or creating duplicate releases.
   - **Automated First-Class Homebrew Formula Support**: Maintain automated formula generation and SHA-256 validation targeting `Knowledge-Forge-AI/homebrew-tap` for all supported platforms (`darwin/arm64`, `linux/amd64`, `linux/arm64`).
   - **Machine-Readable Postmerge Proof**: Execute and require passing postmerge verification (`reconcile_postmerge.py`) prior to declaring terminal release success.

2. **Conditional Nixpkgs Target Policy**:
   - If Knowledge Forge AI establishes a qualified, production-proven Nixpkgs publication path before the v0.12 release-channel freeze (such as via the Theme Forge project), APGR will disposition Nixpkgs admission using that exact organizational precedent.
   - The default disposition will be toward **admission**, provided there are no APGR-specific incompatibilities (e.g., toolchain packaging gaps, licensing conflicts, or binary distribution mismatches).
   - APGR will **not** prematurely invent speculative, blocking, or asynchronous Nixpkgs release policies before organizational precedent is established and qualified.

## Alternatives Considered

- **Ad-Hoc Manual Fixes for Future Releases**: Rejected. Repeating manual troubleshooting for multi-channel publishing failures increases human error risk and delays releases. Codifying invariants into reusable operator tools guarantees deterministic execution.
- **Immediate Unconditional Nixpkgs Packaging in v0.12**: Rejected. Authoring and maintaining a standalone Nixpkgs derivation without shared Knowledge Forge AI infrastructure risks bit-rot, divergence, and uncoordinated maintenance burdens.

## Consequences

- In stage `V0120-F`, the v0.11 repair cases (`R1`–`R13`) and publication findings (`F1`–`F12`) will be integrated into the regression test harness as `REG-R*` and `REG-P*` specifications, with every historical finding either covered by a test or explicitly recorded as a non-durable one-time act.
- Operator scripts will enforce draft ID binding, npm state transitions, and resumable execution.
- At the v0.12 release-channel freeze, Knowledge Forge AI's Nixpkgs status will be evaluated against this policy.
