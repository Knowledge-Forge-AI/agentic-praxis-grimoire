# APG v0.4 Roadmap

## Authority and status

APG25 accepts this dependency-ordered v0.4 roadmap. A roadmap entry records an
intended bounded result; it does not allocate a semantic phase ID or authorize
execution. The maintainer subsequently supplied APG26A and APG27, followed by
the bounded APG27A-to-APG28 sequence, APG28A-to-APG29, APG30-to-APG31,
APG31A-to-APG32, and APG33-to-APG34.
APG26A corrects
formal-phase commit-message enforcement; APG27 is the partial first report
slice; APG27A corrects and adopts that implementation. APG28 is Partial, and
APG28A corrects and adopts its test infrastructure before APG29. APG30
implements the topology slice. APG31 remains historically Partial, and APG31A
records its forward closeout and completes the remaining authorized personal
transition. APG32, APG33, and APG34 retain the Minitest, Dockerfile, and
Vagrantfile profiles provisionally. Later slices remain unallocated and
require separate authority.

The v0.4 line begins from published, externally smoked v0.3.0 with nineteen
skills, fourteen stable and five provisional. v0.4 work must preserve that
release and its active integration unless a later release or integration phase
explicitly owns a change.

## Accepted foundation

APG25 establishes:

- [structured formal and non-phase defaults](structured-project-phase-defaults.md)
  that allow manager assignments to state deviations rather than repeat
  ordinary procedure;
- [scoped testing, coverage remediation, mock boundaries, and the future APG
  pytest architecture](testing-and-coverage-policy.md);
- a [Python-first shared reporting architecture](agent-reporting-architecture.md)
  for Git show, Git diff, and associated operational records;
- a [nested ChatGPT-manager topology](chatgpt-manager-skill-topology.md) with a
  dedicated subrouter and flat Codex projections; and
- transition recommendations for three personal hygiene skills without
  changing them.

## APG26 — initial enabling capabilities

APG26 is complete. It evaluated and retained two provisional capabilities:

1. `pytest-test-profile`, owning pytest-specific discovery, fixtures,
   parametrization, mocking, xdist, coverage, and structural judgment without
   owning project thresholds or framework selection; and
2. `converting-bash-scripts-to-python`, owning characterization and compatible
   migration of an existing Bash executable or script family without mandating
   conversion or changing APG report tools.

The report scripts and planned test migration were read-only dogfood. Both
candidates are `retained-provisional`; pytest has zero behavior-bearing
candidate corrections and conversion has one bounded option-injection
correction. Private development is 21 canonical skills, 21 catalog rows, 21
relative projections, 14 stable rows, 7 provisional rows, and 20 routes.
Public and active v0.3.0 remain unchanged. APG26 starts no later slice.

## APG26A — formal-phase commit-message enforcement

APG26A records the subject-only APG26 formal-phase commit without rewriting it.
The correction adds one dependency-free Python checker and focused contracts,
then updates the current formal-phase, review, identity, and roadmap owners.
APG26's two capability dispositions and the 21/21/21 development library remain
unchanged. APG26A converts no report command and starts no APG27 work.

## Authorized slice status

### APG27 — Python report core and report composition

The uncommitted candidate implements the shared Python model, Git CLI adapter, renderer, envelope,
destination/locking owner, operational framing, and thin CLIs. Characterize and
convert `git-show-report`, `append-operational-report`, and their shared shell
owner; add `git-diff-report` with a temporary index; enforce associated
operational-record composition. Preserve exact current behavior or document an
explicit migration, test supported platform boundaries, and retain rollback.

Candidate result: Git-show version 2 and compatible standalone operational version 1
remain byte-compatible on the characterized POSIX platform. Git-diff version 1
uses a private temporary index and deterministic state-evidence IDs. Associated
operational records require an existing exact Git record in the same canonical
phase report. The phase stops partial because the public-release-policy owner
needs a second material correction to preserve historical v0.3.0
reconstruction, and the Python profile retains a Red branch signal. APG26's
conversion procedure remains retained. APG27 authorizes neither the pytest
migration nor any later slice.

### APG27A — reporting correction and adoption

APG27A preserves APG27 as a truthful partial phase. It freezes immutable v0.3.0
policy independently from current v0.4 report owners, fails closed for unknown
identities, and decomposes the Red path-safety branch owner. Focused report,
historical-release, and independent review gates accept the corrected Python
report core, which becomes current repository behavior without changing public
or active v0.3.0.

## Test-infrastructure slice

### APG28 — APG pytest path and runner migration

Add compatible pytest, pytest-xdist, pytest-cov, and coverage configuration;
move Python tests beneath the mirrored unit and integration roots; make eight
workers the default; enforce independent 80% statement and branch gates and a
combined union 85% statement and branch gate. Detect empty collection, wrong or
missing source targets, stale or duplicated mirrors, worker crashes,
incomplete data, rounding errors, suite contamination, and unsupported-platform
collection.

Dependencies: the pytest profile must be retained; report-core ordering may be
revisited only if the runner does not depend on it. The migration is a testing-
infrastructure phase and therefore owns broader regression than an ordinary
implementation slice. APG28 stops Partial with an uncommitted dependency
declaration, mirrored pytest suite, strict source inventory, and eight-worker
runner candidate. ADR 0024 remains Proposed; component and union branch gates,
release-policy tests, process completeness, and Bats equivalence remain open.

### APG28A — correction and adoption

Preserve APG28 as Partial, correct its aggregation, process-accounting,
artifact, release-policy, and coverage defects, retain Bats owners lacking exact
supersession, satisfy the accepted gates, and accept ADR 0024. APG29 remains
gated on complete APG28A delivery and remote equality.

### 3. Existing process-skill corrections

Completed by APG29 through separately frozen bounded corrections to existing
owners rather than duplicate skills:

- `implementing-with-test-discipline` receives coverage-remediation expansion
  and useful-test stop behavior;
- the applicable planning, implementation, and review owners consume scoped
  testing and real-boundary guidance; and
- `composing-approved-roadmap-assignments` and project documents remain aligned
  with commit, status/exit, ADR, formal docs-only, and non-phase docs-only
  defaults.

Each correction remains independently reviewable. Fifty-one frozen cases cover
the coverage-remediation hierarchy and stop, scoped-test expansion, mock and
real-boundary truthfulness, formal and non-phase defaults, Git/operational
evidence, and manager-assignment compression. No trigger, maturity, catalog,
route, or projection changes.

### 4. ChatGPT-manager relocation and subrouter

Completed by APG30. Recursive canonical discovery, catalog links, checked flat
projections, lifecycle resolution, current-development public projection, and
capability-map ownership support the accepted direct and ChatGPT-nested
classes. The dedicated provisional `chatgpt-manager-workflow` subrouter and
unchanged `composing-approved-roadmap-assignments` leaf are canonical under
`skills/chatgpt/`. Direct explicit selection remains valid and no mandatory
router chain is introduced.

Historical v0.1.0 through v0.3.0 direct-child policy remains immutable.
Post-restart application discovery is an APG31 entry gate.

### 5. Personal hygiene shadow and transition

APG31 evaluates `docs-only-change-hygiene`, `git-history-hygiene`, and
`repomap-phase-hygiene` independently against source-qualified APG and
repository owners. Fresh positive and non-trigger shadow evidence,
private-only behavior disposition, restoration proof, and non-author review
support one partial transition result:

- `docs-only-change-hygiene`: decommissioned;
- `git-history-hygiene`: scope reduction deferred unchanged; and
- `repomap-phase-hygiene`: decommission deferred unchanged.

The two deferrals preserve current private routing and destructive-stop
boundaries that APG31 cannot correct within target-only authority. At least one
private transition occurred, so refreshed client discovery remains pending a
full application restart.

APG31A records that external smoke as passed without rewriting APG31's
historical Partial result. It then completes the deferred transitions under
expanded caller authority:

- `git-history-hygiene`: scope-reduced after generalized behavior returns to
  APG and repository owners; and
- `repomap-phase-hygiene`: decommissioned after generalized behavior returns
  to current RepoMap owners.

Dependency: structured defaults, applicable process corrections, and the
ChatGPT topology must be installed and discoverable from the intended sources.

### 6. Remaining test and platform profiles

Evaluate and implement only coherent, independently triggerable owners:

- `minitest-test-profile`;
- `nix-test-profile`;
- `vagrantfile-profile`;
- `dockerfile-profile`;
- `go-test-profile`;
- `matryer-is-test-profile`;
- `go-cmp-test-profile`; and
- a unified Go testing-stack skill that can combine native `go test`,
  `matryer/is`, and `google/go-cmp` judgment when the stack as a whole is
  material.

The unified owner must preserve each component's independent trigger and
ownership. It must not make a helper library mandatory or erase the ordinary
native-Go non-trigger.

Each named capability receives a separately authorized, bounded evaluation and
implementation disposition; grouping them here does not authorize one combined
phase. Native `go test`, `matryer/is`, and `go-cmp` component evidence and
independent triggers precede any unified Go testing-stack owner. No semantic
phase ID is allocated for any of these slices.

APG32 completes only the `minitest-test-profile` item. It retains one
provisional owner after current-source calibration, thirty-six frozen
scenarios, failing-first focused evidence, integration, and fresh review.
Minitest 6 mock extraction, empty-run truthfulness, parallel thread safety, and
Minitest-specific effects around real integration claims remain explicit
version and stop boundaries. One bounded correction preserves generic
real-boundary truthfulness, Ruby subprocess semantics, and repository
isolation with their existing owners. Every other item above remains
unallocated.

APG33 completes only the `dockerfile-profile` item. It retains one provisional
owner after current Docker documentation, stable frontend, BuildKit, and OCI
calibration; forty frozen scenarios; failing-first focused evidence;
integration; and fresh review. Parser directives, stage and argument scope,
context and ignore ownership, copies and remote additions, mounts, cache,
protected-data flow, final-user and runtime-default behavior, platform support,
and source-versus-build truthfulness remain explicit version and stop
boundaries. Image, dependency, runtime, release, and live-operation decisions
remain with their existing owners. Every other item above remains unallocated.

APG34 completes only the `vagrantfile-profile` item. It retains one
provisional owner after current Vagrant release, development source,
documentation, licensing, and declared Ruby-compatibility calibration; forty
frozen scenarios; failing-first focused evidence; integration; and fresh
review. Configuration loading, boxes, providers, plugins, networks, synced
folders, provisioners, triggers, state, host-dependent behavior, and static
truthfulness remain explicit version and stop boundaries. Provider, box,
plugin, host, network, filesystem, project-command, lifecycle, and
live-operation decisions remain with their existing owners. One bounded
source-semantics and machine-measurement correction qualifies forwarded-port
behavior and prevents implicit-default overcount. Every other item above
remains unallocated.

APG35 **authors** the five remaining items — `nix-test-profile`,
`go-test-profile`, `matryer-is-test-profile`, `go-cmp-test-profile`, and the
unified Go testing-stack owner, named `go-testing-stack` — on the dedicated
authoring branch `claude/apg35-v0.4-remaining-skill-authoring`. It does not
complete them. Authoring produced five candidate leaves, proposed ADR 0025, two
proposed specifications, one hundred fifty-four frozen scenario families, and a
complete Codex integration handoff. It added no projection, catalog row, router
entry, release policy, inventory entry, executable fixture, or test, and it ran
no project test, `go test`, or Nix evaluation, build, or virtual-machine test.

The stack owner preserves each component's independent trigger and ownership,
forces no helper library, and preserves the ordinary native-Go non-trigger, as
this section requires. Native `go test`, `matryer/is`, and `go-cmp` component
evidence and independent triggers were authored before the unified owner, in
the order this section requires, though component *integration* evidence
remains outstanding and is a Codex precondition for retaining the stack.

Integrated development therefore remains 25/25/25. Each of the five items still
requires a separately authorized, bounded integration and disposition phase
before it can be called complete. No semantic phase ID is allocated for any of
them.

APG36 performs that bounded integration and disposition. It preserves the exact
APG35 authoring commit, independently reviews current sources and ownership,
freezes all 154 families into transient executable fixtures, and runs focused
Go compatibility evidence. Four candidates are
`deferred-material-defect`; `go-testing-stack` is
`rejected-no-independent-value`; ADR 0025 is Rejected. No candidate is
integrated, and the proposed Go-stack and Nix specifications are removed from
the current tree through the forward APG36 commit.

The v0.4 items remain unallocated after APG36. Development stays 25/25/25, and
no successor, readiness, smoke, release, publication, or deployment work is
authorized by this disposition.

APG37 **re-authors** the four deferred items — `go-test-profile`,
`matryer-is-test-profile`, `go-cmp-test-profile`, and `nix-test-profile` — on
the dedicated authoring branch `claude/apg37-v0.4-go-nix-redesign`, working
from the APG36 defect dossier and reverified current primary sources. It does
not revive `go-testing-stack`, which remains `rejected-no-independent-value`
and absent, and it does not reopen ADR 0025, which remains Rejected.

Authoring produced four replacement candidate leaves, proposed ADR 0026, two
proposed specifications, one hundred thirty frozen scenario families mapped to
their APG35 predecessors, measured structural calibration, and a complete
Codex integration handoff. All twenty-four APG36 material findings received a
terminal authoring disposition. APG37 added no projection, catalog row, router
entry, release policy, inventory entry, executable fixture, or test, and ran no
project test, `go test`, or Nix evaluation, build, or virtual-machine test.

ADR 0026 proposes three independent component owners and **no** composition
owner, so the unified Go testing-stack item recorded above is no longer a
proposed v0.4 deliverable. A future composition owner would require new
evidence and a new decision record.

Integrated development therefore remains 25/25/25. Each of the four items still
requires a separately authorized, bounded integration and disposition phase
before it can be called complete, and its review must be independent of the
APG37 author. No semantic phase ID is allocated for any of them, and no
successor, readiness, smoke, release, publication, or deployment work is
authorized by this authoring result.

APG38 performs that bounded integration. It retains provisional
`go-test-profile` and `go-cmp-test-profile` after independent current-source
review, 66 executable scenario families, a
disposable Go compatibility harness, one coherent correction cycle each, and
fresh corrected-state acceptance. ADR 0026 is Accepted for two direct
component owners without `go-testing-stack`.

`matryer-is-test-profile` and `nix-test-profile` are
`deferred-material-defect` because corrected-state review finds new
attribution/false-escalation and Nix 2.35.1 FreeBSD sandbox-default errors after
their correction cycles. Both are absent from the resulting current development
surface.

Integrated development becomes 27/27/27. Candidate re-authoring, individual
readiness, smoke, and v0.4.0 publication remain unallocated and require new
maintainer authority.

APG39 performs that separately authorized re-authoring for the two deferred
candidates only. It closes the registered-wrapper, relaxed-mode, and sandbox
platform-default defects from reverified exact sources, freezes 24 and 40
replacement scenario families, proposes ADR 0027 conditionally for a third
Go component, and hands independent review, executable fixtures, the ADR
decision, and atomic integration to a later separately authorized Codex
phase. Integrated development remains 27/27/27; both candidates are
`authored-pending-independent-review` on the APG39 authoring branch.

APG40 performs that bounded integration. It retains `nix-test-profile`
provisionally after one coherent source-fact correction pass, forty public-safe
scenario families, source-only corpus calibration, rights/privacy review, and
fresh corrected-state review. It defers `matryer-is-test-profile` because the
corrected equality mechanism remains materially inaccurate after its one
allowed behavior pass. ADR 0027 is Rejected; ADR 0026 remains Accepted;
`go-testing-stack` remains absent. Integrated development becomes 28/28/28.
No readiness, smoke, release, publication, deployment, or successor phase
begins.

### 7. Cross-repository dogfood and operational efficiency

Use public-safe frozen cases and authorized read-only or disposable repository
work to measure source-qualified selection, prompt repetition reduction,
scoped-test behavior, report reliability, wall-clock and agent-effort effects,
and false-trigger/non-trigger results. Do not use private source wording as a
public dependency or treat fewer prompt bytes alone as better performance.

### 8. Individual readiness and pre-release smoke

APG41 completes this slice. It reviews all fourteen provisional rows,
dogfoods direct cross-profile routing and owner boundaries, corrects
candidate-independent Minitest, Dockerfile, and Vagrantfile removal wording,
runs complete repository gates, builds two reproducible disposable v0.4.0
candidates, and performs isolated lifecycle smoke on the current host. All
fourteen rows remain provisional and included. The terminal disposition is
`ready-for-publication-with-provisional-limitations`; no publication or active
deployment occurs and no later phase is authorized.

### 9. v0.4.0 release

APG41 satisfies the individual readiness and pre-release candidate gate.
APG42 completes the separately authorized release slice: it reproduces APG41,
retains the canonical Agentic Praxis Grimoire NOTICE, freezes one formal release source, builds and reviews two deterministic final
candidates, preserves immutable v0.1.0-v0.3.0 history and tags, atomically
publishes v0.4.0, verifies a fresh public checkout, and advances the
aggregate-owned active integration by exact fast-forward. It retains 28/28/28,
fourteen stable and fourteen provisional rows, and the grouped provisional
limitations without procedure or maturity change.

## Cross-cutting gates

Every slice:

- receives an externally supplied semantic phase ID;
- follows the repository's current structured defaults and states deviations;
- freezes behavior-bearing cases before correction wording or implementation;
- preserves public v0.3.0, personal skills, and active integration unless the
  slice explicitly owns that boundary;
- updates current documents and terminal records before commit;
- receives fresh non-author review and proportional validation; and
- stops without beginning a successor that lacks authority.

No roadmap entry authorizes a dependency addition, public publication,
destructive history operation, private-skill removal, report conversion, suite
migration, or canonical-path move by implication.

## Next authorization boundary

No phase after APG42 is authorized. Signing, announcement, GitHub Release,
plugin publication, rollback, target mutation, and any successor work require
a separate explicit maintainer instruction.
