# APG143 — Integrated Readiness Prerequisite

## READINESS4 terminal candidate

Disposition: **amend**. Outcome: `V0110_READINESS_AND_PUBLIC_CI_PREPARATION_QUALIFIED`.
Status: **completed**. This continues APG143 / V0110-F / exit 00188 under
`execution_mode: gemini_flash_sub`. READINESS1, READINESS2, and READINESS3 below
are historical blocked attempts. Following independent work-review findings
(`reviewed_with_findings`, advisory), READINESS4 qualifies the complete local readiness
and public-CI preparation implementation under Manager Decisions A–D with all
review amendments verified:

The maintained Python census binds tracked prospective public files (278 files
in repo, 331 in public prospective capture), including extensionless Python
entry scripts and release CI helpers. File size warns above 400 LF-delimited
lines and fails above 1,000, with eighteen explicit source-bound entry allowances
from the verified READINESS2 baseline that prohibit growth and transfer. Oversized
files remain visible debt (88 warnings locally, 99 in public capture; 0 failures).
Review finding F8 is resolved by adding `unmatched_allowances` reporting to
`tools/ci/file_length_policy.py`; review finding F10 is resolved by adding the
`test_cli_public_inventory_completeness` fixture across all six candidate roots.

Of 147 recorded Ruff findings, 145 are corrected. Two unused imports belong to
the immutable APG140 support fixture (`src/test/support/apg_external_compatibility_fixture.py`);
exact source bytes and both occurrences are classified explicitly in
`tools/ci/pre_review_evaluation.py`, preserving its accepted integrity oracle.
Zero unaccepted Ruff/Pyflakes findings.

All 225 active scanner suppression directives (224 bootstrap `noqa: E402` and
1 `type_ignore: no-redef` at `src/agentic_praxis_grimoire/config.py:14`) are
formally approved in `tools/ci/scanner_suppressions_known.json` following
independent work-review verification (`APGR-V0110-READINESS4 pre_final review; Decision C`),
with concrete owners, reasons, and expiry `2026-12-31`. Review finding F11 is
resolved by removing the unreachable fail-open `except TypeError` in `scanner_suppressions.py`.
The terminal static pre-review aggregate passes cleanly (`exit=0`) across all 20 checks
with 0 tool failures and 0 policy findings.

The three manager-authorized BetterLeaks nonsecret dispositions bind exact
source context and occurrence identity (2 synthetic URIs in browser UI test
and 1 SHA-256 integrity constant in roadmap contract), updated to cite the
current pre-final review (resolving review finding F12). Raw observations (3)
and reviewed nonsecrets (3) are reported separately with zero unresolved
findings and zero tool failures.

Canonical pytest suite (`bin/apg-test unit-integration --public-version 0.11.0`,
exit 0, qualified READINESS4 source tree) passes through qualified runtime with
0 failures, resolving the historical READINESS2 26-branch deficit. Full qualification
receipt is retained in publication-excluded READINESS4 qualification receipts
(resolving review finding F1):
- Unit suite: 4,232 passed, 0 failed, 62 skipped; statements 11,321/13,249 (85.45% >= 80%);
  branches 4,142/5,168 (80.15% >= 80%). Gate status: `pass`.
- Integration suite: 893 passed, 0 failed, 2 skipped; statements 11,391/13,249 (85.98% >= 80%);
  branches 4,135/5,168 (80.01% >= 80%, resolving the 4,109 branch baseline by +26). Gate status: `pass`.
- Combined union: statements 12,008/13,249 (90.63% >= 85%); branches 4,501/5,168 (87.09% >= 85%).
  Gate status: `pass`.

Go test, vet, and race pass with 0 failures. Roadmap closure checks (55 terminal / 0 open),
skill library (45 canonical skills), and record identity checks pass. Package builds (Go CLI,
Python sdist/wheel, npm packages) and Syft/Grype vulnerability scans produce zero High/Critical
vulnerabilities under verified toolchains (Go `go1.25.14`, Govulncheck `v1.1.4`, Syft `1.51.1`,
Grype `0.118.0`; resolving review findings F4, F6). Owned paths and post-capture receipts
are reconciled to exact 321 paths (274 adopted entry + 47 readiness4 receipts) in
publication-excluded owned paths and capture applicability records (resolving review
findings F2, F3).

Accounting remains 55 terminal / zero OPEN / zero invalid; inventory remains
45 leaves with 14 stable / 31 provisional maturity, six active CSS/JS debts and
11,142 description bytes under the retained 11,507-byte ceiling. No new phase,
exit, skill, consumer adoption or publication authority is allocated.
`public_pr_ci: not_run`; `public_release: not_started`; hosted protection
settings remain unverified. Public staging disclosure and V0110-G require
separate authorization. Git publication and final delivery are dispatcher-owned.

## Historical READINESS3 pre-final candidate

Disposition: **amend**. Status: **blocked**. Attempt interrupted by provider transport
failure (`PROVIDER_TRANSPORT_FAILED` exit 1) following operator-reported Codex
quota exhaustion prior to pre-final review, final review, or Git publication.
All 274 paths and evaluation records are preserved as historical evidence for
continuation under READINESS4.

## Historical READINESS2 terminal closeout

Disposition: **amend**. Status: **blocked**. The supplied independent work
review is dispositioned with terminal corrections; no further reviewer was
selected. This remains APG143 / V0110-F and reuses exit 00188. Terminal
amendments do not receive an automatic independent re-review.

The frozen closeout checkpoint passes 4,196 unit tests and 841 integration
tests with two skips. Unit statements are 11,329/13,257 and branches
4,142/5,168. Integration statements are 11,365/13,257, but branches are
4,109/5,168: 26 short of the unchanged 80% gate. The constructed union reaches
12,007/13,257 statements and 4,496/5,168 branches; it does not override the
failed component. The canonical command exits 1. All selected source inputs
remain stable throughout that run. Later removal of two unused test imports,
a test-docstring correction, and a package-export repair receive scoped tests
and lint checks. The package-export repair excludes the nested Python build
checksum from the distribution file set; actual archive bytes are preserved.

Corrections remove the unused bootstrap request and duplicate Nix installer,
make absent target discovery fail through independent aggregation, bind all
required workflow/member/publisher lists, strengthen release topology checks,
clarify scanner policy and coverage boundaries, and preserve public v0.10
objects explicitly. Fresh action-pin readback covers the actual workflows.
The two renamed synthetic npm identities pass real npm scenarios and a targeted
27-package Syft/Grype scan with no findings. Full source and artifact attempts
remain separately bound evidence; the targeted scan does not qualify them.

Readiness remains blocked by integration coverage, the absent accepted
file-length policy and maintained gate, and unapproved static/suppression
findings. The file-length lane now fails explicitly rather than silently
omitting the requirement. No vulnerability waiver, suppression approval,
existing-debt baseline, coverage relaxation, or unrelated mass cleanup is
adopted. The CI helper directories remain outside canonical percentage coverage;
focused tests do not establish exhaustive bootstrap or helper qualification.

Fresh policy, both closure modes, allocated identity, Go test/vet/race and
scoped CI/capture/npm checks pass. All 55 terminal decisions, 45 leaves,
14 stable / 31 provisional maturity, 11,142 description bytes under 11,507,
and six active debt flags remain unchanged. Consumer handoff remains distinct
from adoption. Historical attempts below are not current-tree passes.

`public_pr_ci: not_run`; `public_release: not_started`. Git finalization belongs
to the dispatcher. No public staging, PR, merge, settings mutation, production
release, registry upload, consumer adoption, or host activation is performed.

## Historical READINESS2 work-stage candidate

Work-stage proposal disposition: **amend**. This continues APG143 / V0110-F and
reuses exit 00188. The prior attempt below is historical evidence, including
its failed integration run; it is not current-tree qualification. The amended
task authorizes the bounded capture adapter and public staging PR CI source.
The dispatcher owns pre-final review and final verification at closeout.

The exact supplied plan is retained separately from task authority and review
findings. Amendments prioritize reproducible runtime provisioning, require a
pre-merge public-base check, explicitly cover the JSON release workflow tests,
preserve the flat current public-surface schema and historical version maps,
and test the new untagged candidate mode. Change-size evidence must be recorded
without raising thresholds.

Entry readback matched all eighteen retained candidate paths by mode, size and
digest, plus the retained real-index digest. No staged changes or active Git
operation were found. ADR 0055's correctly dated acceptance and both test
fixture corrections are retained. The original attempt and report artifacts
remain preserved; its managed report verifies as four historical records.

The existing runtime contract admits two public sources. The primary Node
engine is the pinned Nix output; the secondary is the official upstream release
binary and is not required to reside in Nix. Local realization of the pinned
primary output and a fresh upstream archive/binary digest check match the
existing required identities. This does not establish hosted provisioning.

Version authority is now unreleased `0.11.0`. New source and artifact
qualification remain in progress. The later public release route is
`staging` → PR → squash merge to `main` → release; it supersedes direct-main
directions for v0.11 without rewriting historical releases.

`public_pr_ci: not_run`; `public_release: not_started`.

### READINESS2 implementation and evidence boundary

The maintained source capture adapter creates an independently committed,
clean disposable repository from tracked prospective bytes and an explicit
new-file manifest. Its CLI contract covers deletion, executable modes, raw
symlink targets, source/index/ref immutability, and unsafe input/output refusal.
Private qualification source remains separate from exact public projection.

The additive v0.11 release maps register governance, hotspot/report-key,
capture, CI, and test owners while retaining historical validator maps. The
release procedure is proposed in ADR 0057: an untagged staging candidate,
observed squash merge with the accepted public base as sole parent, then
rebuild and qualification of commit-bound final artifacts before publication.
The current public policy inventory remains a flat schema; historical version
identity lives in the maintained release selection maps.

Public PR source now provisions the exact declared runtimes in disposable
jobs, runs independent static checks, canonical suites, Go checks, package
qualification, source/deliverable SBOM scans, and four CodeQL categories.
Explicit member receipts and the aggregate reject missing or unsuccessful
lanes. The publisher checks actual PR approval, workflow execution, and merged
source identity. Local fixtures do not establish hosted execution, protection
settings, or external acceptance.

This remains an **unqualified pre-final candidate**. The first READINESS2
canonical diagnostic had 4,074 unit passes with fourteen failures and 787
integration passes with five failures and two skips. Stale current-version
assertions were corrected; the diagnostic also exposed component branch
coverage shortfalls. It is not an accepted integration or union result.
Subsequent source-bound work-stage checks and artifact manifests belong in
the associated managed operational report; final verification remains the
dispatcher closeout's responsibility.

Broader Ruff findings are attributable to existing owners, and scanner
suppression inventory entries remain unapproved. Synthetic npm fixture
identities also collide with malicious-package advisories; those scanner
matches require an explicit disposition and fresh exact-source evidence.
No blanket suppression, automatic baseline growth, lowered coverage threshold,
or vulnerability waiver is adopted. Proposed existing-debt dispositions are
review material, not accepted exceptions. Successful earlier package and
scanner attempts do not qualify later changed inputs.

The semantic crosswalk retains all 55 terminal decisions, their individual
receipts and consumer ownership. It preserves 45 leaves, 14 stable / 31
provisional, 11,142 description bytes within 11,507, and the six active debt
flags. Consumer handoff remains distinct from consumer adoption. The new
dispatcher pre-final review must assess the complete integrated result;
internal worker evidence does not satisfy that checkpoint.

### Frozen work-stage checkpoint and pre-final amendments

The completed work-stage checkpoint observed unchanged source fingerprints
throughout policy and canonical unit/integration execution. Policy passed.
All selected tests passed, but the integration component failed its unchanged
branch threshold:

| Component | Test result | Statements | Branches | Disposition |
| --- | --- | --- | --- | --- |
| Unit | 4,179 passed | 11,329 / 13,257 | 4,142 / 5,168 | Passes 80/80 |
| Integration | 814 passed, 2 skipped | 11,347 / 13,257 | 4,090 / 5,168 | Branch gate below 80% |
| Combined union | Constructed | 12,006 / 13,257 | 4,495 / 5,168 | Exceeds 85/85; does not override component failure |

Both roadmap-closure modes and the skill-library check pass. Maintained
discovery again measures 45 leaves and 11,142 description bytes. Fresh Go test,
vet, and race checks pass. Exact public-candidate package qualification passes
all 22 qualification commands, with reproducible Go, Python, and npm artifacts;
Linux targets are cross-build/readback evidence, while isolated Darwin entry
points execute natively.

The complete source/deliverable scan produces fourteen SBOMs and fourteen
Grype results, including a separately bound conditional Python 3.10 dependency
view. No coverage gaps or tool failures are reported. Two Critical synthetic
npm fixture identity matches remain unwaived, and one Low finding stays visible.
Static lanes distinguish policy findings from tool failures. No existing-debt
proposal is accepted merely because its source context is explained.

An actual public-source run exposed a collection/deselection evidence-timing
defect. The maintained runner now records raw, deselected, and remaining worker
collections and requires exact partitioning, worker agreement, approved
deselections, and complete terminal results. Focused real xdist evidence passes;
the associated operational report records the full public run and its limits.
Twenty-eight public-capable CSS tests are restored from a former module-wide
skip; private historical-oracle applicability remains explicit per test.

After the frozen checkpoint, pre-final amendments reconcile current status
paragraphs and remove an import-order finding in the new capture test through
the existing package import. They do not change production behavior, coverage
thresholds, or accepted debt. Their scoped verification and refreshed artifact
bindings belong in the managed operational report. This is still an unqualified
pre-final candidate; final resulting-state verification and independent review
remain dispatcher-owned.

## Historical READINESS1 attempt

The following sections preserve the prior blocked attempt's observations and
scope. Its restriction on authoring capture is superseded for READINESS2.

## Status and authority

Closeout status: `V0110_INTEGRATED_READINESS_PREREQUISITE_BLOCKED`.
APG143 and exit 00188 were available at entry and are allocated without
renumbering history. This is a bounded partial terminal candidate, not a readiness qualification.
The supplied dispatcher pre-final review was dispositioned at closeout.
Terminal amendments received scoped verification, not another independent review.
Git finalization remains dispatcher-owned.

Proposal disposition: **amend**. The original V0110-F task remains the scope
authority. The supplied proposal and advisory plan review are separate
evidence. Closeout adopts the supplied cumulative phase delta and amends its documentation
and evidence in response to the supplied independent work review.

## Proposal and plan-review disposition

1. Accept the clean-source finding and resolve it before release policy,
   package qualification. Closeout supersedes the earlier dependency claim:
   integrated suites operate on the working tree and do not require clean source.
2. Accept the additional version owners: archive epoch, public validation
   version/deselection/supplement maps and release workflow guards. Their
   implementation is deferred behind the prerequisite. Any candidate epoch
   must follow the unreleased-epoch precedent, not claim a publication date.
3. Accept the packaged-documentation finding. README, distribution and npm
   guidance require candidate wording and actual artifact readback before
   v0.11 qualification; neither metadata nor package contents changed here.
4. Accept the distinction between manifest/projection qualification and
   deterministic release-object construction with accepted public lineage.
   No public base clone, release build/check or official object is created.

## Snapshot prerequisite

The maintained [release owner](../../libexec/apg_public_release.py) resolves
clean repositories for every CLI operation, including `manifest`, and
`tree_entries` reads committed Git objects. `initialize_validation_copy`
recreates committed objects and refs; it does not capture prospective changes.
The [release process](../public-release-process.md) documents that contract.

The maintained [snapshot helper](../../src/test/support/apg_repository_snapshot_contract.py)
is bounded to `skills` and `.agents`. The [reporting diff owner](../../report/diff.go)
captures two matching diffs using a temporary index and observes the real index
and source state for drift. It emits report evidence, not a complete
path/type/mode/byte source export or a disposable committed qualification tree.
The [release integration fixtures](../../src/test/int/python/agentic-praxis-grimoire/bin/apg-public-release.int.test.py)
create synthetic source repositories rather than materializing the actual
prospective source.

[APG129](apg129-v0-10-integrated-readiness.md) used phase-local projection
scripts. Its terminal projection lacked Git metadata and retained prior
wrapper-help evidence. That precedent does not establish the complete
maintained snapshot route required here. This is a limitation of the inspected
APGR route, not a claim that Git cannot create disposable fixture commits.

The missing item is an APGR-owned maintained prospective-source capture helper,
not a general inability to consume a disposable repository. The existing
`manifest --source` interface accepts a clean external repository; fixture Git
commits are permitted by the assignment. The inspected helpers do not capture
all authorized prospective paths, preserve types/modes/bytes, materialize them
outside active repositories and prove correspondence plus source/index/ref
preservation. No capture helper is introduced at this closeout. That narrow
prerequisite applies to prospective-source package/projection qualification;
it does not gate working-tree policy, Python coverage or Go tests.

## Independent work-review disposition

Disposition: **amend**. Accept all three advisory findings and the footprint note.
Current roadmap policy now reports 55/55/0/0; the remaining APG141 copies and
foundation dispatch wording explicitly identify their historical scope. The
integrated working-tree checkpoint is attempted independently of package source
capture. The prerequisite description now identifies the missing helper and
the release CLI's existing `--source` consumption point. Preservation evidence
includes authorized additions as well as modified tracked files.

The supplied review supports the partial candidate's capacity, accounting,
record identity and honest omissions. It did not establish the required fresh
substantive review of all inherited terminal decisions. No additional reviewer
was selected or invoked. Terminal corrections are dispositioner amendments.

## Completed independent work

[ADR 0055](../adr/2026/09/0055-v0-11-capacity-and-closure-governance.md) now
records the manager's later acceptance on 2026-09-12, preserving the APG138
proposal and measurement history. Current navigation distinguishes historical
phase-entry states from present 55-terminal accounting. No companion
instruction file is manufactured.

Fresh maintained context measurement reports 45 discoverable skills, 11,142
description UTF-8 bytes and 11,126 characters. The unchanged 11,507-byte
ceiling leaves 365 bytes of headroom. The explicit retained discovery-policy
check reports 45 canonical skills, 45 catalog rows and 45 projections. Provider
token/context overhead remains unavailable.

## Evidence and applicability

The canonical policy gate (`.venv/bin/python bin/apg-test policy`), allocated
record-identity check, proposed commit-message form check and whitespace check
pass. The current dirty-source `apg-public-release manifest --format json`
refuses with exit 1 and `source repository must be clean`, as expected.

The compact phase evidence map records exact commands, retained outputs,
source bindings, preservation and run/not-run distinctions. Both closure
commands pass with 55 inherited / 55 terminal / zero OPEN / zero invalid,
including zero missing and unknown rows. This checks actual terminal receipts
and checker consistency; it does not newly review the substantive truth of
55 decisions, all eight FALSE observations or individual consumer ownership.
The prior manager acceptance of APG142 remains the entry authority.

ADR 0053, ADR 0054, all skill content, capacity enforcement, governance ledgers,
active debts, historical policies and runtime code are preserved. A bounded
report-verifier test fixture now changes file size when preparing a diff.
Before correction, ordinary Go tests and a package repeat intermittently refused
with repository drift; a diagnostic scratch overlay also observed no reportable
change after the same-size edit. The correction preserves every metadata
contradiction assertion and runtime drift refusal. It is a fixture-stability
repair, not a claim of general same-size filesystem qualification.

No readiness repair changes a named APG79B condition;
`JS_QD_005_REFRESH_NOT_TRIGGERED` remains applicable under ADR 0054. No old
report is retrieved or reconstructed.

## Terminal working-tree verification

The existing qualified tool bindings and virtual environment were reused with
external task-owned temporary roots; no dependencies were installed or upgraded.
An initial unbound invocation refused before collection. A subsequent attempt
was interrupted by a parent process-identification error and is not accepted
evidence. Its completed unit output does not establish integration success.
The fresh replacement invocation completed with exit 1:

| Component | Test result | Statements | Branches | Gate disposition |
| --- | --- | --- | --- | --- |
| Unit | 3,968 passed | 10,596 / 12,292 | 3,873 / 4,790 | Accepted 80/80 component |
| Integration | 762 passed, 2 skipped, 1 failed | 10,583 / 12,292 | 3,847 / 4,790 | Raw counts only; failed worker completion |
| Union | Not constructed | Unavailable | Unavailable | Not qualified |

The failure was a stale success-text expectation in the policy integration
fixture: the maintained command now includes roadmap-closure checks. The
assertion now expects that complete text and retains all real summary-file,
mode, status and source-identity assertions. Its focused integration rerun
passed (one test). A successful focused correction does not retroactively
qualify the failed full run; no replacement full integration/union gate is
claimed. Coverage thresholds, universes, exclusions and skips are unchanged.

Final `go test -count=1 ./...`, `go vet ./...` and
`go test -race -count=1 ./...` pass. The corrected report fixture also passed
20 consecutive focused runs. Earlier failures remain in the evidence map.
The two terminal test edits received affected verification; runtime code is
unchanged. Final policy, identity, message form, whitespace and document-link
checks cover the terminal documentation amendments. These are dispositioner
corrections after the supplied review, not independently re-reviewed bytes.

## Not qualified and next boundary

Versioned v0.11 test-selection/projection support and Go/Python/npm distribution
qualification remain unimplemented or unrun. No prospective-public identity,
package checksums, installed-package checks or public import qualification is
claimed. Source tests are not qualification of built v0.11 packages. Version
remains 0.10.0. Historical selection/materialization and release results are not
substituted for fresh prospective-source evidence.

The supplied review assessed the partial candidate's truthfulness; required
substantive readiness review of all terminal inherited decisions remains
incomplete. A maintained prospective-source capture helper and completed v0.11
surface/artifact work remain prerequisites alongside a successful integrated
gate. Dispatcher disposition of this blocked closeout is required before
continuation. No V0110-G work, public release, registry write, installation,
consumer adoption or host activation is authorized.
