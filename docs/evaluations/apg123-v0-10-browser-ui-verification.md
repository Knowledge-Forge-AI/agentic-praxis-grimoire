# APG123 v0.10 Browser/UI Verification

## Scope and status

APG123 implements provisional `playwright-test-profile` and
`web-accessibility-profile` and browser-backed composition with the existing
SVG authoring owner. The dispatcher pre-final review is complete with advisory findings. Closeout
amendments passed final-source verification. Git finalization remains
dispatcher-owned.

The manager accepted APG122 as
`V0100_FOUNDATION_SVG_VERTICAL_SLICE_QUALIFIED`. Its archive transport issue
does not reopen source acceptance or authorize provider replay. Current
launcher binding selects the content-authoritative archive implementation;
no APG122 archive recovery or Git refinalization is performed here.

## Proposal and review disposition

Disposition: **amend**. The original two-leaf vertical-slice task remains
controlling. The bound proposal and advisory findings add explicit browser
prerequisites to the maintained pytest runner, an exact current 42-leaf
policy, SVG-only complete-file size enforcement, inline-document external
resource evidence, read-only cache reuse and exact specification statuses.
There were no reported entry stage deltas. Neither proposal finalization
prose nor internal worker output grants publication or checkpoint authority.

## Compatibility and capacity

The read-only consumer manifest, lockfile and installed package select
Playwright Test 1.62.1. A task-owned installation matches its package
integrities and preserves the selected version despite newer documentation.
Chromium 151.0.7922.34, Firefox 153.0 and WebKit 26.5 launched and closed
successfully on the observed macOS ARM64 host. Launch evidence alone is not
semantic qualification.

The `v0.10-browser-ui` policy admits only the original 39 identities plus SVG,
Playwright and web accessibility. The current maximum is 10,517 UTF-8
description bytes; each candidate retains its independent 330-byte allowance.
Original descriptions and SVG's description remain frozen. The historical
9,527-byte limit, SVG-only 9,857-byte admission and six-candidate 11,507-byte
reservation remain distinct. SVG keeps its 20,480-byte complete-file ceiling;
the two new leaves have no added fixed complete-file ceiling. Caller bundle
budgets and exact measured metadata still apply.

The resulting corpus measures 10,273 description bytes and 10,261 characters:
42 canonical/catalog/projection/discoverable leaves, 14 stable and 28 provisional.
The two new descriptions are 266 and 262 bytes. All forty existing descriptions
and the complete SVG leaf were independently compared with entry source and
remain byte-identical. Individual selections and explicit three-owner composition
resolve; the composition contains 31,815 body bytes and 769 description bytes.
Each tested zero-body budget refuses. These measurements are bytes, not tokens.

## Ownership and evidence boundaries

[The Browser/UI contract](../architecture/v0-10-browser-ui-verification.md)
keeps SVG vector authoring, Playwright mechanics and accessible semantics
separate. Browser-runtime, Vite and package-manager leaves remain absent;
existing CSS/JS/TS/JSX/React/Node owners and explicit selection are preserved.

The synthetic fixture register separates Playwright, accessibility and SVG
resource scenarios. Browser corroboration supplements APG122's preserved
18-semantic / 6-navigation-only historical classification. It does not
retroactively relabel static evidence. Permitted SVG references require inline
document processing, an explicit local resource policy and a rendered effect;
secure image processing is a separate restriction.

| APG122 clause | Browser corroboration and limit |
| --- | --- |
| `SVG-07-DEFS-SYMBOLS-USE` | SVG01 proves permitted external-use fetch and rendered effect against a missing-resource control, in inline-document mode only. |
| `SVG-11-DOM-INTERACTION` | AX05 exercises Tab focus and Enter/Space activation; this does not establish image-mode interactivity. |
| `SVG-12-A11Y-SEMANTICS` | AX05–AX07 exercise naming, image purpose and structured alternatives; they provide no assistive-technology or WCAG conformance proof. |
| `SVG-13-SECURITY-PROCESSING` | SVG01–SVG03 distinguish permitted local references from denied foreign/path resources under the fixture policy; they do not qualify a sanitizer or arbitrary Internet resources. |

Other SVG clauses receive no new browser qualification from this matrix.

Playwright semantic snapshots are not a screen reader. DOM, semantic-tree,
keyboard and rendered checks do not prove WCAG conformance, speech output,
all assistive-technology interoperability or general visual equivalence.
Same-run image comparisons qualify controlled change detection for each
executed engine/platform, not portable golden baselines.

The selected role locator includes an inert DOM button despite blocked focus
and pointer interaction. That observation is retained as a tool-evidence limit;
it is not described as platform accessibility-tree exposure. Complex-image tests
bind chart labels to table values and remove the table as a negative control:
the short image name survives while the structured alternative disappears.
Rendered focus captures include the outer outline and were visually inspected
in all three engines; no contrast-ratio or assistive-technology claim follows.

## Verification

The frozen-source work-stage combined gate passed: 3,536 unit tests and 646
integration tests, with two existing public v0.1 dogfood prerequisite skips
(`APG11_PUBLIC_V01_ROOT` and `APG12_PUBLIC_V01_ROOT`). No Browser/UI lane was
skipped. Unit, integration and combined coverage gates passed; the combined
union covers 10,410/11,511 statements and 3,803/4,370 branches.

The maintained matrix passed all 72 scenarios across Chromium, Firefox and
WebKit. The combined gate exercises 39 runner/SVG combinations and 33 accessibility
combinations through its two maintained integration entrypoints.
Fourteen adverse supervisor-report cases verify exact result identity and reject
skips, extra results and unrelated failures. Fresh bounded checks also cover
prerequisites, existing profile composition, checker CLI behavior and metadata.
Existing qualified TypeScript and both Node identities were revalidated.
Affected Go tests, vet and race checks pass. Policy checks cover inventory,
skill library and record identity. Metadata and context reconstruction match
actual source; public-surface paths exist and frozen release policies remain
unchanged.

The 1,164-path source receipt remained unchanged through combined verification.
This evaluation, the exit record and the private work-verification receipt
receive subsequent result annotations;
executable, profile, harness and policy bytes remain bound to the passing run.
The producer candidate outcome was
`V0100_BROWSER_UI_VERIFICATION_SLICE_QUALIFIED`. These are historical work-stage
results, not the amended closeout-source result.

The initial combined run exposed stale current topology fixtures and incomplete
new lifecycle owner fields. Corrections update current fixtures to exact sets and
counts while preserving historical surfaces. A legacy test that treated current
development as publishable v0.7 now verifies historical-publication refusal instead;
production publication checks are unchanged. Later receipts supersede that initial
failing run. No coverage threshold, exclusion or runner policy was relaxed.

## Privacy, rollback and stop

Read-only consumer dogfood captured a disposable source/dependency tree and
ran the existing visual-equivalence and cross-browser smoke configuration.
The completed capture passed 111 tests: 99 Chromium visual-equivalence cases
and six smoke cases each in Firefox and WebKit. Snapshot updates were disabled,
zero-diff thresholds preserved and traces disabled for privacy. CI mode
prevented existing-server reuse; current configuration retained one worker and
zero retries. The server closed and observed source hashes remained unchanged.
An earlier 12-test smoke pass had an incomplete copied preview dependency;
the corrected 111-test run supersedes it. Preview, studio workbench and
external dogfood-shard suites were not selected. This bounded result is not
whole-consumer qualification or permission to change its visual baselines.

Packages, temporary profiles, local servers and artifacts remain in task-owned
external scratch; existing browser binaries are read-only. Synthetic fixtures
copy no consumer artwork. Runtime tests never attach to user browser sessions.
Consumer evidence is read-only or from a disposable capture with snapshot
updates disabled. No global package, host activation or public release occurs.

Rollback removes both new admissions, profiles and integration/harness surfaces
together while preserving SVG, historical records and public v0.9.0. No
successor, consumer mutation, JACA/Dinas change or public v0.10 publication is
authorized.

## Closeout disposition

Disposition: amend. All bounded prior implementation deltas are retained.
The advisory review is dispositioned without another substantive review:

1. Clarify the two specifications' clause/scenario namespaces and require full
   clause citations. Preserve existing IDs and mappings. Dedicated concurrency/
   sharding and dialog/popover/menu scenarios remain outside this representative
   matrix; no complete clause-coverage claim is made.
2. Correct PW-03 to await BrowserContext.close() and APIRequestContext.dispose();
   regenerate source-bound metadata.
3. Retain the resolved AbortSignal behavior and its three-engine negative-control
   evidence; no additional API eligibility or error-shape guarantee is claimed.
4. Defer stale private oracle modernization. The inspected legacy installed-skill
   oracle assumes 39 leaves and is outside both canonical runner roots. It is not
   current qualification evidence and would require modernization before reuse.
5. Correct the work-stage post-gate annotation inventory to include its own
   verification receipt, and distinguish historical from terminal evidence.
6. Defer standalone runner scratch hardening. Maintained entrypoints require the
   Python supervisor's explicit external private scratch and pass that path to
   the runner. Direct standalone invocation is not a qualified custody interface.

Terminal final-source checks passed. Only result annotations in this
evaluation, the exit record and private closeout evidence follow those
checks; profile, harness, policy, test and packaged metadata bytes remain
unchanged.
No new review, consumer rerun, public release qualification or successor is
performed at closeout. Prior consumer and Go evidence is confirmed only where
its tested inputs remain unchanged.

The first closeout combined run passed all 3,536 unit tests but failed one
integration cancellation probe (645 passed, two prerequisite skips). A focused
reproduction confirmed that its disposable checkout copied the candidate runner
without the new Playwright prerequisite helper, causing ModuleNotFoundError
before cancellation. The read-only SIGINT probe now invokes the complete current
checkout under its existing repository-state guard and external scratch. Its
focused rerun passed, preserving exit 130 and the error-status receipt contract.
The production runner, timeout, coverage thresholds and inventory are unchanged.
That correction required a new final-source combined run; the failed run is
retained and does not establish combined qualification.

The next combined run passed the corrected cancellation probe but failed PW01
in Firefox (3,536 unit passes; 645 integration passes, one failure and two skips).
The ambiguity probe discarded unexpected errors under a 300 ms deadline, so the
underlying error cannot be recovered from that run. Scheduling interference is
a plausible contributor, not an established root cause. PW01 now confirms two
matching elements, permits a 5-second action budget and propagates unexpected
errors. Its success predicate still requires the exact strict-mode rejection;
no timeout or unrelated error is accepted as evidence. Dedicated timeout cases
are unchanged. Both failed combined runs remain non-qualifying evidence.

## Terminal qualification

Outcome: `V0100_BROWSER_UI_VERIFICATION_SLICE_QUALIFIED`.
Disposition: amend. The terminal combined gate passed 3,536 unit tests and
646 integration tests, with the two existing public v0.1 prerequisite skips.
Unit coverage is 9,863/11,511 statements and 3,508/4,370 branches; integration
is 9,877/11,511 statements and 3,498/4,370 branches; the combined union is
10,411/11,511 statements and 3,803/4,370 branches. All coverage gates passed.
The 1,164-path terminal source receipt remained unchanged through the run.
The two earlier failed runs remain recorded above and are superseded for
qualification by this corrected-source result, not erased.

The affected profile rerun passed ten tests covering all 72 browser/scenario
combinations. The corrected cancellation probe passed both ordinary focused
execution and a bounded execution under the canonical coverage/worker setup,
and then passed in the terminal combined gate. Go test/vet/race, policy,
context, exact metadata and record-identity checks passed; the Go inputs were
unchanged by the later test/harness corrections. Engine binary hashes still
match the selected recorded identities. Discovery remains 42 leaves and
10,273 description bytes within 10,517.

Consumer readback still selects package 0.4.0 and Playwright Test 1.62.1. One
scene-test file differed from the producer's 640-file capture at closeout
readback. The 111-test dogfood result is therefore evidence for that historical
disposable capture, not a claim that the current consumer tree is identical or
newly qualified. No consumer rerun or mutation was performed at closeout.

The stale private oracle and direct standalone scratch-default hardening remain
deferred. The original PW01 unexpected error was not preserved, so its precise
cause remains unknown. These limitations do not weaken the current exact
strictness assertion, mandatory three-engine matrix or combined gate.
Only declared result annotations followed the passing source; no further
substantive review, Git mutation or successor work was performed by closeout.
