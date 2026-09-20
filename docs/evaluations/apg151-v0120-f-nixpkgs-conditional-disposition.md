# APG151 — v0.12 Nixpkgs Conditional Disposition and Evidence Record

- **Phase**: APG151
- **Milestone**: V0120-F (Release Hardening, Conditional Nixpkgs, and Integrated Readiness)
- **Governing Decision**: [ADR 0062 §2](../adr/2026/09/0062-v012-release-hardening-and-conditional-nixpkgs.md)
- **Date**: 2026-09-17
- **Authority**: Samuel Lair <lair001@gmail.com>

---

## 1. Executive Summary and Formal Disposition

In accordance with [ADR 0062 §2](../adr/2026/09/0062-v012-release-hardening-and-conditional-nixpkgs.md), the inclusion of Nixpkgs as an active publication channel for APGR v0.12 was conditionally contingent upon Knowledge Forge AI establishing a qualified, production-proven Nixpkgs publication path (specifically within the Theme Forge product family) prior to the v0.12 release-channel freeze.

Following comprehensive re-verification of the Knowledge Forge AI repository family on 2026-09-17, the formal disposition is:

**`condition-not-met` / `deferred-not-admitted-for-v0.12`**

Per ADR 0062, this outcome is an anticipated, valid architectural determination and is **NOT** a release-readiness failure. Milestone V0120-G will execute publication across the five qualified, mature distribution channels:
1. **GitHub Releases** (binary distributions and release assets bound to numeric draft IDs)
2. **Go Module Proxy** (canonical Go module tag and proxy indexing)
3. **PyPI** (OIDC Trusted Publishing for Python source and binary wheels)
4. **npm Registry** (platform binary tarballs and launcher package)
5. **Homebrew Tap** (automated formula generation targeting `Knowledge-Forge-AI/homebrew-tap`)

---

## 2. Re-Verification Scope and Sources Consulted

During Phase APG151 execution on 2026-09-17, the following authoritative sources and repositories within the operator environment were systematically audited:

### 2.1 Theme Forge Monorepo (`theme-forge-stellar-burst`)
- **Repository**: `Knowledge-Forge-AI/theme-forge-stellar-burst`
- **Recent Git History**:
  - `5aa3399` (*TFSB70B-R1: Preserve APGR-assisted native packaging progress*)
  - `2c67a58` (*TFSB70B-R2: Close observed-artifact publication readiness*)
  - `7a003b2` (*TFSB70B-R3: Amend composition qualification and publication authority*)
  - `e1eec2e` (*TFSB70B-R4: Close post-checkpoint composition and authority qualification*)
  - `22d630e` (*TFSB70B-R5: Close published Burst input binding and authority qualification*)
- **Evidence Documents Inspected**:
  - `docs/evaluations/tfsb70b-publication-readiness.md`
  - `apps/studio/evidence/tfsb70b/`
- **Nix Artifacts Inspected**:
  - `flake.nix` (root flake exposing `packages.aarch64-darwin.default` and `apps.aarch64-darwin.default`)
  - `nix/packages/nebular-fusion.nix` (local derivation for Nebular Fusion `.app` candidate payload)
  - `pkgs/by-name/th/theme-forge-nebular-fusion/package.nix` (prospective Nixpkgs `by-name` derivation template)

### 2.2 Theme Forge Starlight Theme (`theme-forge-terminal-nova`)
- **Repository**: `Knowledge-Forge-AI/theme-forge-terminal-nova`
- **Findings**: Pure Astro/CSS component library published to npm and GitHub. Zero Nix expressions or Nixpkgs publication mechanisms present.

### 2.3 Agent-Central Reference Implementation (`agent-central`)
- **Repository**: `agent-central`
- **Findings**: Pure dispatcher runtime. Contains no distribution packaging for Nixpkgs.

### 2.4 Internal APGR Historical Evaluations
- **Inspected Records**:
  - `docs/evaluations/apg21a-nix-profile-correction.md`
  - `docs/evaluations/apg40-apg39-matryer-nix-integration.md`
- **Distinction Enforced**: As emphasized in Scope Section S, internal Nix expressions used for development environments, host runtime profiles, or CI provisioning are strictly distinct from public package publication precedent.

---

## 3. Detailed Findings from Theme Forge Audit

The audit of `theme-forge-stellar-burst_dev` revealed substantial engineering progress on local Nix packaging for the Theme Forge Nebular Fusion desktop workbench, but confirmed that no qualified upstream publication path exists:

1. **Explicit Stop Boundaries Enforced in TFSB70B**:
   In `docs/evaluations/tfsb70b-publication-readiness.md` §1 ("Stop Boundaries & Operational Constraints"), Theme Forge explicitly records:
   ```markdown
   - [x] No git staging, commit, tag, or push to public or private remotes
   - [x] No npm packages published to public registry
   - [x] No Homebrew tap repositories modified or PRs opened
   - [x] No nixpkgs pull requests submitted
   - [x] No persistent background daemon or VM processes spawned
   ```
   Theme Forge has deliberately withheld the submission of pull requests to upstream `NixOS/nixpkgs`.

2. **Nature of Existing Nix Expressions**:
   - The root `flake.nix` and `nix/packages/nebular-fusion.nix` files serve solely as local developer conveniences on Apple Silicon (`aarch64-darwin`) to wrap the candidate `Theme Forge Nebular Fusion.app` into a launcher binary (`tfnf`).
   - The file `pkgs/by-name/th/theme-forge-nebular-fusion/package.nix` is an unmerged draft derivation referencing pre-built binary tarballs (`https://github.com/Knowledge-Forge-AI/theme-forge-nebular-fusion/releases/download/...`).
   - Neither Theme Forge nor any other Knowledge Forge AI repository has submitted or merged a package into upstream Nixpkgs, established an automated Hydra/nix-review workflow, or proven multi-release maintenance.

3. **Conclusion**:
   There is zero active, production-proven Nixpkgs publication precedent within Knowledge Forge AI.

---

## 4. Architectural Assessment & Compatibility Evaluation

ADR 0062 §2 directs APGR to evaluate organizational precedent rather than invent speculative, uncoordinated release workflows. In the absence of an upstream precedent, attempting to introduce Nixpkgs publication into APGR v0.12 would entail substantial risks:

- **Source vs Binary Derivation**: Upstream Nixpkgs strictly prefers building Go and Python tools from clean source rather than wrapping pre-built binary tarballs. Maintaining a source build derivation for APGR inside Nixpkgs would duplicate the complex dual Go/Python toolchain build system (`internal/cli` + `libexec/`).
- **Asynchronous Review Cycle**: Upstream Nixpkgs review and merge cycles operate on days-to-weeks latency and cannot be synchronized with APGR's deterministic multi-channel publication epoch.
- **Maintenance Drift**: An uncoordinated derivation maintained outside Knowledge Forge AI's established distribution automation would suffer immediate bit-rot.

Therefore, adhering strictly to ADR 0062 §2 and rejecting speculative unilateral workflows protects release determinism.

---

## 5. Criteria for Reopening in Future Releases

The admission of Nixpkgs packaging may be reopened for reconsideration in a future APGR release (v0.13+) upon satisfying the following objective criteria:

1. **Upstream Merged Precedent**: At least one Knowledge Forge AI core project (e.g. Theme Forge or APGR) successfully merges a package derivation into the official `NixOS/nixpkgs` repository (`main` or `staging` branch).
2. **Automated CI/CD Integration**: Knowledge Forge AI establishes an automated release dispatch workflow that updates the Nixpkgs expression (or an official Knowledge Forge AI Nix flake channel) atomically alongside GitHub/PyPI/npm releases.
3. **Multi-Platform Hermetic Builds**: Demonstration of clean source builds passing `nix-build` across `x86_64-linux`, `aarch64-linux`, and `aarch64-darwin` without network access during the build phase.

Until these criteria are demonstrably met, APGR distribution remains focused on its five qualified channels.
