# APG134 v0.10.0 release wording amendment

## Scope and proposal disposition

Proposal disposition: **amend**. APG134 is the authorized corrected-source
amendment for permanent v0.10.0 wording and its maintained tests. The bound
proposal is accepted with the additional npm test correction identified by
plan-review F1 and explicit supplemental roadmap dispositions from F3. No stage
deltas were supplied at entry. The canonical unit run additionally reproduced
a topology assertion in `apg_public_release.unit.test.py` that pinned the old
README candidate sentence. Its wording is corrected while preserving the exact
45/14/31 topology contract. This observed implementation delta remains within
the original maintained-wording-test scope.

[APG133](apg133-v0100-release-freeze-source-blocker.md) remains historically
blocked: it found the release-final wording defect and built no candidate.
Its final review expanded remediation to the maintained twelve-surface audit
and wording tests. No APG133 candidate or artifact identity exists to reuse.
[APG116](apg116-v090-release-wording-amendment.md) supplies the precedent:
describe the accompanying version and condition installation on publication
without announcing a remote publication event.

## Surface dispositions

| Surface | Disposition |
| --- | --- |
| `README.md` | `CORRECT_NOW` |
| `release/v0.9.0-notes.md` | `HISTORICAL_PRESERVE` |
| `release/v0.10.0-notes.md` | `CORRECT_NOW` |
| `docs/distribution.md` | `CORRECT_NOW` |
| `docs/README.md` | `CORRECT_NOW` |
| `docs/reference/cli.md` | `CORRECT_NOW` |
| `docs/reference/go-library.md` | `CORRECT_NOW` |
| `npm/README.md` | `CORRECT_NOW` |
| `npm/templates/launcher/README.md` | `DURABLE_ALREADY` |
| `npm/templates/platform/README.md` | `DURABLE_ALREADY` |
| `testing/fixtures/external_consumer/README.md` | `CORRECT_NOW` |
| `testing/fixtures/xo_consumer/README.md` | `CORRECT_NOW` |

The historical notes and conditional npm templates are preserved. Supplemental
current introductions in the Repo Map support roadmap and v0.10 roadmap are
`CORRECT_NOW`; their historical phase records remain historical. APG122/APG123
sections in `AGENTS.md` are `HISTORICAL_PRESERVE`. These supplemental dispositions
do not enlarge the maintained twelve-entry inventory.

Plan-review F2 is accepted for the complete README and documentation-index
wording scope. F4 preserves substantive release contents, maturity and platform
limitations. F5 keeps checks scoped to preparation phrases, allowing legitimate
technical uses of “candidate” and preserving historical/template semantics.
The public-surface presence policy is unchanged.

## Work-stage verification

The corrected source passed work-stage qualification. Closeout dispositions
the dispatcher-supplied pre-final findings below; Git finalization remains
dispatcher-owned.

The three affected wording-test files pass 157 tests and 89 subtests. The
maintained audit enumerates exactly twelve surfaces. Its shared guard rejects
injected case/line-wrap regressions and all nine stale current-surface baselines;
historical notes and both templates remain byte-preserved. The stronger guard
also reproduced and closed one line-wrapped candidate phrase in the Go reference.

Actual maintained-backend sdist and Darwin arm64 wheel construction passes.
`PKG-INFO` and wheel `METADATA` agree at version 0.10.0, contain the complete
projected README with current Python/npm/Go pins and version-pinned relative
links, and pass the private-path scan. The sdist README matches source bytes.
These are disposable packaging checks, not a public release candidate or bundle.

The canonical `bin/apg-test unit-integration` run passes 3,774 unit tests and
708 integration tests, with two maintained skips. Exact coverage is:

| Scope | Statements | Branches | Required threshold |
| --- | --- | --- | --- |
| Unit | 10,176 / 11,865 | 3,689 / 4,598 | 80% each |
| Integration | 10,202 / 11,865 | 3,691 / 4,598 | 80% each |
| Union | 10,745 / 11,865 | 4,002 / 4,598 | 85% each |

The entire worktree inventory is unchanged through that successful run. An
earlier run found the third stale wording assertion; parent correction during
integration also correctly tripped a repository-status preservation check.
Neither result is treated as a pass. The stable rerun supersedes both failures.
An earlier prerequisite rejection was resolved by copying existing qualified
packages into owned scratch, without dependency or runner-policy changes.

Policy, record identity, skill-library/discovery and context checks pass:
45 canonical/catalog/projected/discoverable leaves, 11,142 description bytes,
and 365 bytes below the unchanged 11,507-byte ceiling. Version, public-surface,
projection/confidentiality dry checks and whitespace checks pass. Local Markdown
rendering covers all ten requested documents, the supplemental v0.10 roadmap,
and phase/index records; 361 local links and fragments resolve. Chromium DOM
checks show nonempty content, matching headings and no horizontal overflow.
This is local rendering evidence, not hosted-renderer or accessibility acceptance.

No browser/report/Node/JavaScript/Go runtime implementation, fixture behavior,
threshold, exclusion, denominator, maturity or debt owner changes. The expensive
114-browser matrix and unrelated Go runtime gates were therefore not rerun.
Reporting-only updates after the canonical run receive affected document,
identity and projection checks. Closeout retains this verified canonical evidence
and reruns affected checks after its documentation and test-only amendments.

## Terminal closeout

Disposition: **amend**. The bound producer candidate and cumulative phase changes
are accepted with the following corrections to the supplied work-review findings:

- F1: remove the subsumed npm assertions and require the complete release sentence.
- F2: normalize whitespace in the npm README/template assertions and case-fold
  stale-phrase checks. The publication test remains the shared twelve-surface
  guard; the npm test retains its package-specific contract without importing
  another test module.
- F3: remove both unused phase-specific anchors; no repository inbound link
  targets either fragment.
- F4: retain the APG132 section of the general roadmap as historical phase
  evidence, consistent with APG116. The v0.10 roadmap introduction describes
  current product scope. Replace APG134 in-flight roadmap and exit wording with
  its terminal source disposition. APG133 remains historically blocked.

Closeout verifies the retained canonical log digest and compares its complete
source inventory with current bytes. The only additional terminal changes are
wording assertions, two documentation anchors and phase reporting; runtime,
coverage-policy and skill inputs remain unchanged. The canonical results above
are confirmed work-stage evidence, not a newly executed terminal full gate.
Affected final verification reruns all three wording-test files, actual backend
sdist/wheel construction and metadata inspection, the twelve-surface audit,
policy, skill/context, identity, public-surface/confidentiality dry checks,
rendering and local links. No additional substantive review is obtained.

The terminal source disposition is
`V0100_RELEASE_SOURCE_CORRECTION_QUALIFIED`. Git finalization remains outside
provider-local closeout. No unresolved work-review concern remains; public
visibility, local-renderer and unchanged-runtime limitations above still apply.

## Public-state observations

Fresh entry and exit observations on 2026-09-10 match the requested public main
and v0.9.0 annotated tag baseline. No public v0.10.0 tag is present and the public
GitHub release endpoint returns HTTP 404. This observes public visibility only;
private drafts and registries are not inspected. No public state was mutated.

## Boundary and next source

Deterministic release freeze must restart from the resulting committed APG134
source and rebuild the complete candidate and bundle. APG132 is not the corrected
freeze input. Disposable Python packaging checks do not create a deterministic
public candidate. No public refs, releases, registries, consumer repositories,
host activation, maturity, debt, or runtime implementation change belongs to
this amendment. Git commit and push remain dispatcher-owned; no successor is
automatically dispatched.

See [exit 00179](../status/2026/09/10/00179-apg134-v0100-release-wording-amendment-exit.md).
