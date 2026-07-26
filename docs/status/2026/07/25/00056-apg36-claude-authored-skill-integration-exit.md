# APG36 Claude-Authored Skill Integration Exit

Phase ID: `APG36`

Status: **Complete — five Claude-authored candidates independently disposed,
none retained, and ADR 0025 rejected**

Date: 2026-07-25

## Outcome

APG36 preserves the exact APG35 authoring commit, verifies the maintainer's
manual branch push and APG35 managed-report integrity, independently reviews
all five candidates, freezes all 154 scenario families into transient
executable fixtures, establishes failing-first evidence, and runs a disposable
pinned Go compatibility harness.

The terminal results are:

| Candidate | Disposition | Reason |
| --- | --- | --- |
| `go-test-profile` | `deferred-material-defect` | five independent lifecycle, version, fuzz, goroutine, and structure correction families |
| `matryer-is-test-profile` | `deferred-material-defect` | typed-nil and custom-helper contradictions plus separate routing, diagnostic, and structure defects |
| `go-cmp-test-profile` | `deferred-material-defect` | sorting, transformer/filter, unexported, approximation, diagnostic, and structure defects |
| `go-testing-stack` | `rejected-no-independent-value` | native-owner precondition failed and multiple trigger, duplicate-owner, thinness, and degradation corrections are needed |
| `nix-test-profile` | `deferred-material-defect` | flake-check, sandbox, evidence-taxonomy, structure, and package-default defects |

No candidate fits the one-behavior-correction retention budget. All five leaves
and both proposed specifications are removed through the APG36 forward commit.
Their APG35 authoring evidence remains in immutable history and their terminal
review evidence remains publication-excluded.

## Architecture and current state

ADR 0025 is **Rejected**. The proposed Go component split and stack are not
adopted. Existing language, repository, project-policy, and process owners
remain unchanged.

Development remains 25 canonical skills, 25 catalog rows, and 25 flat
projections, with fourteen stable and eleven provisional rows, twenty-three
general-router entries, one ChatGPT-local entry, and twenty-four checked route
edges. No APG35 candidate receives a maturity row. Public and active v0.3.0
remain 19/19/19.

## Validation

| Gate | Result |
| --- | --- |
| APG35 immutable object, parent, remote branch, Git-show, operational association, and manual push | Passed; exact identities remain in managed and publication-excluded evidence |
| Frozen fixtures and failing first | Passed: 154 continuous public-safe families; five fixture contracts passed and seven intended integration/stack assertions failed |
| Disposable Go compatibility | Passed: Go 1.25.10, matryer/is v1.4.1, and go-cmp v0.7.0; temporary root removed |
| Nix execution | Not run; current source review was sufficient for deferral and no store/cache effects were justified |
| Focused retained command-boundary tests | Passed: 26 tests and 9 subtests |
| Skill library | Passed in text and JSON at 25/25/25 |
| Full unit suite | Passed: 298 tests; statements 4315/5042; branches 1543/1928 |
| Full integration suite | Passed: 271 tests and 2 expected skips; statements 4426/5042; branches 1543/1928 |
| Current/public lifecycle, routers, release policy, and strict inventory | Passed; historical v0.3 remains 19/19/19 |
| Python, shell, help, Markdown, links, public/private, privacy, provenance, rights, identity, and whitespace | Passed |
| Disposable current-development v0.4.0 candidate | Passed build and check without publication |
| Fresh terminal independent review | Passed all ten required surfaces after resolving ADR and public-identity findings |
| External-state preservation | Passed for public, active, reference, RepoMap, private Codex VC, Claude branch, and target boundary |

The pre-existing integration branch-coverage deficit reproduced on the
untouched APG34 baseline under Python 3.13 and 3.14. APG36 added bounded
integration cases for real helper entrypoints and refusal paths; it did not
weaken coverage policy or use the combined suite.

## Division-of-labor assessment

The trial is `supported with required guardrails` for another bounded trial.
The APG35 handoff materially reduced orientation and fixture work, but
independent source and false-escalation review is mandatory because all five
retention predictions failed. Immutable author history, Codex-owned fixtures,
one correction allowance, forward-only corrections, individual dispositions,
and Codex-owned final status, testing, reports, publication, and deployment
remain required.

## Delivery and stop boundary

APG36 adopts the exact APG35 authoring object followed by one formal APG36
forward commit. Mainline adoption is a fast-forward only after the complete
tree passes, followed by one normal push and remote-equality verification.
Claude's branch is not moved.

Combined, readiness, smoke, release, publication, deployment, target-repository
tests, broad Go execution, and Nix execution are not run. No phase after APG36
is authorized. Any candidate redesign, readiness, smoke, v0.4 release, or
successor phase requires a fresh maintainer request.

## Subsequent authoring note

That redesign was separately authorized as APG37, which re-authored the four
deferred candidates on a branch from this phase's defect dossier. APG37 left
`go-testing-stack` rejected and absent, left ADR 0025 Rejected, and integrated
nothing; development remained 25/25/25. The APG36 dispositions recorded above
are unchanged. See
[exit 00057](00057-apg37-go-and-nix-test-profile-redesign-exit.md).
