# APG74 TypeScript Language-Profile Candidate Exit

Phase ID: `APG74`

- Date: 2026-08-03
- Phase: APG74 — Claude TypeScript Language-Profile Candidate and
  Intended-State Target Harness
- Result: Complete — narrow TypeScript language-profile candidate and
  TypeScript 7 intended-state fixture authored under ADR 0042; ADR 0043
  Proposed, candidate unintegrated, and APG75 hardening pending separate
  authority

## State

- Exact APG73 and its two-record omnibus were verified before authoring;
  APG73 and earlier history and reports remain unchanged.
- ADR 0042: Accepted and governing. ADR 0043: Proposed.
- ADRs 0031, 0034, 0035, 0036, 0039, 0040, and 0041: Rejected and
  unchanged. Markdown: retained provisional (ADRs 0037/0038 Accepted with
  amendment).
- Candidate: authored-proposed-unintegrated — one leaf, one specification,
  one navigation-only scenario-coverage record (24/24 scenarios mapped to
  24 stable clauses).
- Fixture: 14/14 cases authored, branch-only, with scratch-verified smoke
  checks and no generated output or target source committed.
- TypeScript primary generation: exact selected stable `typescript@7.0.2`,
  freshly verified against npm and the `microsoft/typescript-go` release
  tag.
- TypeScript 6 compatibility: explicit `not-required` disposition with a
  recorded refresh condition; no TypeScript 6 package installed.
- Targets: freshly pinned read-only objects; website unchanged from the
  APG72 pin; theme remote main rebuilt after APG72 and pinned at its
  current head; both unexecuted and unmodified. The live theme checks under
  `typescript@5.9.3` — migration baseline, not the destination.
- APG74 branch: transitional 30 canonical leaves / 29 catalog rows / 29
  projections. Integrated `main`: exact APG73 at 29/29/29.
- Maturity: 14 stable / 15 provisional. Routes: 27 general / 1
  ChatGPT-local / 28 checked.
- CSS, JavaScript, and TypeScript current integration: absent.
- Corrected public and active v0.4.0: unchanged, reverified live.
- APG75: recommended (exit 00108, terminal ADR 0043 decision), not begun,
  separately authorized only by a future human prompt.

## Verification boundary

APG74 ran docs-safe object, ancestry, omnibus, branch-parity,
record-identity, decision-state, integration-count, route, maturity,
release-fingerprint, fresh package/source-binding, target-pin, candidate
shape and clause-coverage, fixture schema/path/state-label, scratch smoke
(version, clean check, declaration-only emit, seeded-defect negatives),
link, JSON, privacy, rights, structure, change-size, whitespace,
complete-diff, and concrete-message checks, plus fresh non-author review
lanes.

No maintained executable, support, or test owner changed, so the full APG
regression suite was not run. No target command, integration, candidate
test authoring beyond the fixture, readiness, publication, deployment,
APG75, or successor work ran. Live remote re-fetch was broker-blocked this
session; remote parity rests on the operator's post-APG73 fetched refs and
reflog plus a live read of the public repository.
