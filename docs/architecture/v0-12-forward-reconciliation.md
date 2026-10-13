# APGR v0.12 Forward Reconciliation Record

- **Status**: Informative Architecture and Release Authority Record
- **Date**: 2026-09-20
- **Authority**: APG159 / APG159A (Milestones V0130-A / V0130-A-CORR1), under governing manager disposition
- **Evidence Reference**: Milestone V0130-A-CORR1 qualification bundle and multi-channel observation receipts

---

## 1. Purpose and Scope

This forward reconciliation record establishes the factual baseline of APGR v0.12.0 publication and development accounting as observed at the start of the v0.13.0 program. It reconciles real-world distribution outcomes across public registries, documents the development commit lineage that landed after historical release milestone V0120-G1, and clarifies the relationship between the read-only development source checkout and the isolated v0.13 foundation clone.

Per repository governance ([phase and record identity](../phase-and-record-identity.md)), this document uses durable semantic references rather than brittle commit hashes. Historical records (including exit records and previous roadmaps) are preserved unchanged; this record provides forward reconciliation without retroactively inventing historical receipts or rewriting closed milestones.

---

## 2. Multi-Channel v0.12.0 Publication Reality

The consolidated proposal dated September 20 stated that v0.12.0 was not published. That premise is stale: **APGR v0.12.0 is visible on the public distribution channels below**. Each channel is dispositioned individually with the date and kind of its observation. Raw readback bodies and digests are retained in publication-excluded APG159A evidence; this record does not depend on them.

| Distribution Channel | Version / Identifier | Status | Evidence / Observation |
|---|---|---|---|
| **GitHub Releases** | Release ID `392534425`, tag `v0.12.0` | **Published (manager API readback, 2026-09-20)** | The manager's dated API readback observed the release published at 2026-09-20 18:40:56 UTC, not draft, not prerelease. APG159A re-observed only the release ID and tag from the release page on 2026-09-20; the Releases API was unreachable from the sandboxed phase, so publish time and flags were not independently re-observed. |
| **PyPI** | `agentic-praxis-grimoire` 0.12.0 | **Verified by registry readback (2026-09-20)** | Registry JSON lists three platform-tagged `py3-none` wheels and one sdist uploaded between 18:56:06 and 18:56:11 UTC with SHA-256 digests. |
| **npm** | `@knowledge-forge-ai/apgr` 0.12.0 | **Verified by registry readback (2026-09-20)** | `latest` dist-tag is 0.12.0, published 19:13:27 UTC; the three optional platform packages were read back at 0.12.0. |
| **Go Module Proxy** | `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire` `v0.12.0` | **Verified by proxy readback (2026-09-20)** | The proxy `.info` record lists `v0.12.0` with a Git origin bound to `refs/tags/v0.12.0`; the module path case matches `go.mod` at the tag. The proxy's recorded module time is the tag time, not an observation time. |
| **Homebrew Tap** | `Knowledge-Forge-AI/homebrew-tap` | **Formula readback only (2026-09-20)** | `Formula/agentic-praxis-grimoire.rb` on the mutable default branch declares version 0.12.0 and passes a Ruby syntax check. `brew install` and `brew audit` were not run; asset download and install remain a V0130-I distribution-surface check. |

Registry visibility does not prove every terminal release receipt, the release tree identity, the hosted run, or identical tree state across private development branches. The release tree hash and hosted run ID are recorded as `unverified` in the excluded evidence. Those aspects are accounted for below.

---

## 3. Forward Accounting of Post-G1 Development Commits

Between the closure of historical milestone V0120-G1 (Exit 00204, Phase APG152C) and the initiation of milestone V0130-A (Phase APG159), seven development commits landed in the private development branch:

1. **APG153E**: Core unit test coverage gate closure, resolving test matrix regressions.
2. **APG153G**: macOS 27 Firefox deferral binding, formalizing local browser deferral authority.
3. **APG153J**: Public portability gate closure and scratch directory path isolation.
4. **APG155B**: Hosted PR repair qualification, validating attended PR workflow.
5. **APG156A**: Candidate qualification regressions repair, resolving edge cases in multi-role dispatch.
6. **APG156C**: Release-matrix projection-awareness, ensuring accurate candidate package verification.
7. **APG158A**: Supervisor cleanup repair qualification, hardening external supervisor process management.

These commits landed without allocating formal exit records in `docs/status/` or updating the forward status table in `docs/v0-12-roadmap.md`. Historical exit records and closed milestone tables are preserved as immutable history. This forward reconciliation record explicitly accounts for phases APG153E through APG158A as adopted into development baseline state, ensuring no unaccounted changes precede v0.13.0.

---

## 4. Public Distribution vs Private Checkout Reconciliation

A critical architectural distinction must be maintained between **public distribution outcomes** and **private development checkout reconciliation**:

1. **Public Channel Visibility (Observed, per channel)**: As documented in Section 2, v0.12.0 is visible on PyPI, npm, and the Go module proxy by dated registry readback, on GitHub Releases by the manager's dated API readback, and on the Homebrew tap by formula readback only. Visibility is not proof of installability or of every terminal receipt.
2. **Private Development Checkout Reconciliation (Unresolved)**: The existence of public artifacts does not mean the internal development branch, uncommitted scratch artifacts, and post-G1 commits have been formally closed out. The development repository reflects:
   - Untracked artifacts from historical packaging scratch areas in the primary development checkout.
   - Seven post-G1 commits without a corresponding V0120-G2 exit record.
   - `docs/v0-12-roadmap.md` marking V0120-G2 as `NOT STARTED` and release notes marking `public_release: not_started`.

### Isolation of the Foundation Workspace
The launcher-established workspace enforces strict isolation:
- **Source Checkout (Read-Only)**: The primary development checkout remains clean of uncommitted production code. Historical packaging metadata and tree receipts in pre-release qualification scratch areas are uncommitted, unadopted, and excluded from the v0.13 program.
- **Foundation Workspace (Active Clone)**: Execution proceeds in an isolated local clone on branch `v0.13.0/apg159-foundation`. The workspace is clean and contains no uncommitted historical artifacts.
- **Uncommitted Source Edits Excluded**: No uncommitted edits from the source checkout are adopted into this clone. All mutations in milestone V0130-A are confined to authorized documentation, non-executable evaluation fixtures, and publication-excluded evidence.

---

## 5. Status of the V0120-G2 Terminal Reconciliation Gate

In the active clone, the repository status reflects:
- `docs/v0-12-roadmap.md` marks milestone V0120-G2 as `NOT STARTED`.
- `release/v0.12.0-notes.md` marks `public_release: not_started`.
- No formal exit record exists for V0120-G2.
- The repository contains historical pre-release repair qualification records and an early G2A blocked record, but no terminal publication receipts in the development branch tree.
- The read-only primary development checkout carries no `v0.12.0` tag (observed 2026-09-20); the public release commit identified by the Go proxy origin is not recorded in that checkout's history. Source/terminal alignment therefore remains unestablished.

### Gate Evaluation
- **For Milestone V0130-A / APG159A (Architecture / Documentation)**: The G2 terminal reconciliation gate was **satisfied to proceed**. V0130-A was strictly confined to documentation, specifications, evaluation fixtures, and reconciliation records.
- **For Milestone V0130-B / APG160 (Local Code Implementation Under Manager Disposition M5)**:
  The governing manager reviewed the public release commit (`919a04f493f79d91315668b5b1b9794e8e35b284`, staging tree `7e40c0f62204d2b9d3f7210812f31229b60988e4`, 13 green hosted jobs) via the GitHub connector. The release commit explicitly names the private APG158A baseline (`c4ac2a122e9f786fd7208a4619da47ebe468d3e9`) from which the isolated development line descends (`APG158A -> APG159 -> APG159A -> APG160`). Under delegated user authority, this **settles the source-entry question for APG160 local development on the isolated development branch**.
  - This is an explicit manager scheduling disposition supported by connector source evidence; it does **not** declare historical G2 administrative paperwork globally closed.
  - Scope limits: Does not claim full private-to-public re-execution or recovery of all historical receipts; does not assert Homebrew install/audit execution; does not mutate released assets, create tags, or reopen publication; and does not extend any exact-head waiver forward.
  - Remaining terminal administrative reconciliation is carried to the release owner and v0.13 release-readiness work (Milestone V0130-I).

---

## 6. Summary of Dispositions

1. v0.12.0 is observed on five distribution channels with per-channel observation kinds and dates; three registries are verified by retained readback, GitHub rests on the manager's dated readback, and Homebrew is a formula readback only.
2. The seven post-G1 commits (APG153E through APG158A) are accounted for forward without retroactively altering historical exit records.
3. Untracked historical scratch evidence in the source checkout is explicitly excluded from v0.13.
4. Private development checkout reconciliation remains unresolved and is explicitly separated from public distribution status.
5. The source-entry requirement for local implementation on the isolated branch is dispositioned by Manager Authority M5 for Milestone V0130-B (APG160), while global historical G2 paperwork reconciliation remains designated for Milestone V0130-I.
