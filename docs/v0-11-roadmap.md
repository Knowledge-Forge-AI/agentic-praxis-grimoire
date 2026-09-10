# v0.11 Roadmap Closure Program

## Direction and scheduling authority

The operator-approved release goal is v0.11.0: finish or permanently disposition
the inherited roadmap. Public v0.10.0 is released across GitHub, Go, PyPI and
npm and remains immutable. [APG138 reconciliation](evaluations/apg138-v0-11-foundation-closure.md)
records the publication authority and the foundation qualification boundary.

This roadmap and its [closure ledger](governance/v0-11-closure-ledger.json)
own current inherited scheduling. The [v0.10 roadmap](v0-10-roadmap.md),
[backlog consolidation](v0-10-backlog-consolidation.md),
[v0.9 roadmap](v0-9-roadmap.md), and
[Repo Map support roadmap](repo-map-support-roadmap.md) remain historical
source records. Their old `OPTIONAL_LATER`, `EXTERNAL_GATE`, and
`CONDITION_TRIGGERED` classifications do not independently schedule work.
Historical blocked outcomes remain unchanged.

The hard release exit invariant is:

```text
inherited_roadmap_open_items = 0
```

Zero backlog means terminal decisions, not implementation of every old idea.
The foundation freezes 55 inherited rows: 18 surviving backlog items, six
Repo Map milestones, and 31 individual provisional leaves. Superseded rows
remain excluded. New ideas unrelated to closing these identities belong to a
new post-v0.11 roadmap. A newly found defect in changed/current behavior can be
a release blocker without silently extending the inherited population.

## Closure contract

Ordinary terminal outcomes are `DELIVERED`, `REJECTED`,
`CONSUMER_HANDOFF_CLOSED`, and `MAINTENANCE_TRIGGER`. Each requires a reviewed
decision and outcome-specific evidence. A false trigger belongs in the
maintenance register; it is not a demand to manufacture a repair.

Each inherited provisional leaf receives `STABLE`,
`PROVISIONAL_MAINTENANCE`, or `DEPRECATED_OR_SUPERSEDED`. Promotion requires
leaf-specific repeated positive use, representative non-triggers, defect/debt
disposition, rollback, provenance, independent review and current validation.
There is no bulk promotion. A retained provisional lifecycle trigger leaves
the release roadmap and becomes maintenance after its individual disposition.

The [governance guide](governance/v0-11-closure-governance.md) owns the
machine-readable closure, maintenance, compatibility and maturity records.
Creating those records does not close their linked rows. Foundation validation
permits open rows; integrated readiness requires valid zero-open accounting.

## Semantic sequence

At the historical APG138 entry, only V0110-A was implemented. APG139 through
APG142 subsequently closed V0110-B through V0110-E. Current inherited
accounting is 55 terminal / zero OPEN / zero invalid. APG143 begins V0110-F
but its closeout remains blocked with incomplete readiness gates.
V0110-G requires separate bounded dispatch.

| Stage | Owned work | Required exit |
| --- | --- | --- |
| V0110-A | Publication reconciliation, frozen inheritance, capacity decision and governance tools | Valid complete foundation; open rows allowed |
| V0110-B | Individual maturity campaign for all 31 inherited provisional leaves | Every leaf has an individual terminal lifecycle decision |
| V0110-C | Repo Map, JACA and external-consumer closure | Source-bound compatibility and consumer ownership dispositions |
| V0110-D | Optional reporting, hotspot and context decisions | Each optional item delivered or explicitly rejected |
| V0110-E | Exact-trigger debt and maintenance closure | No condition-triggered row remains release work |
| V0110-F | Integrated readiness and zero-backlog proof | Local technical readiness and public CI preparation qualified (APG143) |
| V0110-G | Deterministic v0.11.0 release | Public staging candidate prepared (APG144); deterministic publication |

## V0110-B — Individual maturity

APG139 [closes individual maturity](evaluations/apg139-individual-maturity-closure.md)
with all 31 maturity rows terminal as PROVISIONAL_MAINTENANCE. Zero leaves
are promoted or deprecated; at the APG139 exit, 24 non-maturity inherited
rows remained open.
This does not authorize later stages.

The [maturity ledger](governance/skill-maturity-ledger.json) covers all 45
leaves and preserves the initial 14 stable / 31 provisional state. Work may be
batched by process, language/runtime/database, testing, frontend/toolchain or
cross-cutting guidance, but evidence and dispositions stay leaf-specific.
Existing CSS debts and JS-QD-005 constrain their individual owning leaves;
CSS-QD-005 is not a stable-maturity blocker. A lifecycle trigger is not itself
proof of promotion or rejection.

## V0110-C — External contract and support closure

APG140 [closure](evaluations/apg140-external-contract-support-closure.md)
terminalizes all twelve stage-owned rows after supplied independent review
and terminal verification: 55 inherited / 43 terminal / 12 open / zero invalid.
Compatibility continues as maintenance. At that historical APG140 exit,
V0110-D/E and release work were unstarted.

RM-S0 refreshes source-bound contract inventory and disposable APGR fixtures.
RM-S1 decides author/reject for versioned-protocol guidance only after a stable
consumer-qualified contract and reusable existing-owner gap are demonstrated.
RM-S2 decides graph-quality guidance using empirical multi-source evidence;
cycles and graph shape preferences are not generic defects. RM-S3 first tests
composition of existing process, database, language and testing owners against
a real migration fixture. Reject a migration leaf when those owners suffice.
Any demonstrated new leaf still requires a separate admission decision.

RM-S4 and RM-S5 close into version-bound compatibility, seam ownership and
refresh responsibility. Current consumer contracts, not historical proposals,
decide whether a reusable provider gap exists. No APGR fixture proves hosted
Repo Map quality, production migration safety or consumer adoption.

Refresh JACA CI/XO/outbox contracts read-only. `APGR-CI-QUAL` and
`APGR-XO-COMPAT` close as consumer handoffs on the existing provider delivery
unless a current contract demonstrates a missing APGR requirement. Outbox
transactions remain JACA-owned; add APGR reporting behavior only for a proven
reusable producer gap. JACA adoption is not a release prerequisite.

## V0110-D — Optional work decisions

APG141 closes these four obligations after supplied independent review and
terminal verification: two deliveries and two reasoned rejections, with
47 terminal / 8 open / zero invalid. The requirements below preserve the
phase scope; [terminal decisions](governance/optional/apg141/README.md) record
the explicit combined-scoring narrowing and supported-store limitations.

- `APGR-HOTSPOT-CHURN`: prefer implementation if additive deterministic
  semantics are honest. Require schema/version disposition, explicit history
  inputs, shallow/missing-history refusal, no hidden network and fixtures
  separating size, complexity, churn and growth. Version the schema if needed.
- `APGR-CXT2B`: recheck Caveman format, reuse rights and current consumer value.
  Implement or reject. Any adapter stays optional, pins its input version,
  refuses unknown fields/units and adds no core Caveman runtime dependency.
- `APGR-REPORT-PROJECT-KEY`: require a concrete current consumer naming problem;
  otherwise reject and retain explicit override semantics.
- `APGR-REPORT-RESULT-FIELDS`: require current consumer vocabulary before
  restricting accepted fields; otherwise reject the restriction.

## V0110-E — Trigger audit

Audit exact accepted conditions for pure-Go Git, context compression, five CSS
debts and JS-QD-005. Implement only when the corresponding trigger is true;
otherwise close into the [maintenance register](governance/maintenance-triggers.json)
with owner, condition, evidence requirement and refresh procedure. Unknown
trigger state does not establish false or qualify maintenance closure.

[ADR 0054](adr/2026/09/0054-js-qd-005-refresh-trigger-interpretation.md)
remains controlling: `JS_QD_005_REFRESH_NOT_TRIGGERED` stands unless one of its
named conditions changes. Do not reconstruct APG79B to fill a new register.
Keep accepted historical verification and stable-blocking debt intact.

## Capacity before admission

[ADR 0055](adr/2026/09/0055-v0-11-capacity-and-closure-governance.md)
owns the measured v0.11 decision. ADR 0053 remains historical policy. The
conservative effective ceiling remains 11,507 UTF-8 description bytes with no
new leaf admitted; spare bytes are not admission authority. Description bytes
and characters, selected materialized content, and unavailable provider
overhead are separate signals. Bytes are not tokens. Descriptions are not
compressed merely to fit a preferred future leaf.

## V0110-F and V0110-G — Acceptance and release

Readiness requires canonical unit/integration and coverage, public projection,
Go/Python/npm distribution qualification, catalog/projection/discovery
integrity, every individual maturity decision, exact maintenance triggers and
owners, source-bound compatibility, and preserved v0.10 historical records.
Run the maintained closure checker in its explicit zero-backlog mode; invalid
or missing rows cannot manufacture the invariant. Independent semantic review
must also establish trigger-state changes and consumer-handoff linkages; a
zero-open accounting result alone does not prove their truth.

V0110-F must bind the foundation checker, contract, schemas, governance records,
roadmap, ADR and phase records into the new versioned public release surface,
including critical-file registration and test-selection closure. V0110-G uses
that qualified surface; the historical v0.10 inventory remains unchanged.

Release follows the deterministic public-release architecture only after
readiness. GitHub, Go, PyPI and npm must each be exact, and human documentation
must describe final maturity, capacity and compatibility. DINAS deployment
remains a separate consumer handoff. APGR phases do not mutate JACA, Repo Map,
DINAS, Theme Forge or host state as compatibility proof. Linux artifact builds
do not qualify Linux runtime; desktop browser tests do not qualify Tauri,
WebView or assistive technology.

## APG141 V0110-D closure

APG141 closes [optional work](evaluations/apg141-optional-work-closure.md)
after supplied independent review and scoped terminal verification: 55 inherited /
47 terminal / 8 open / zero invalid. Separate decisions deliver bounded hotspot
history v2 and the report-key repair, and reject the Caveman adapter and result-field
restriction. Combined complexity/churn scoring is explicitly abandoned for the
inherited hotspot item. At that historical APG141 exit, V0110-E/F/G and
release remained unstarted.

## APG142 V0110-E terminal closure

APG142 [audits the eight exact maintenance triggers](evaluations/apg142-exact-trigger-maintenance-closure.md) and strengthens
maintenance receipt reference consistency. Supplied independent review supports
all eight FALSE findings; separate terminal receipts and ledger transitions are
post-review amendments with scoped closeout verification. Actual accounting is
55 inherited / 55 terminal / zero OPEN / zero invalid. Prior outcomes and all
active debt/maturity consequences remain intact. V0110-F must reconcile ADR 0055
status and qualify the new governance/checker/schema/test-selection surfaces.
No independent re-review of amended bytes is claimed. At the APG142 exit,
V0110-F/G remained unstarted.

## APG143 V0110-F recovery and public CI preparation

APG143 [reconciles capacity acceptance and records the snapshot prerequisite](evaluations/apg143-integrated-readiness-prerequisite.md). ADR 0055 is Accepted
on the manager's 2026-09-12 disposition; fresh measurements retain 45 leaves,
11,142 description bytes and 365 bytes of headroom under the 11,507-byte ceiling.
Both maintained closure checks pass with 55/55/0/0 accounting.

The original blocked READINESS1 attempt and its supplied review remain
historical evidence. READINESS2 continues APG143 and exit 00188, authorizing
the maintained capture adapter, unreleased v0.11 metadata and public staging
PR CI source. Local closeout remains blocked as recorded below. The existing release
CLI consumes clean disposable source through `--source`; working-tree suites
have no clean-source dependency. The later public route is `staging` → PR →
squash merge to `main` → release. Public v0.10, maturity and active debt
consequences remain unchanged. Public PR CI is not run and publication is not
started. No V0110-G authority is granted.

The historical READINESS2 terminal closeout remained blocked: 4,196 unit and 841 integration
tests pass with two skips, but integration branches are 4,109/5,168, below 80%.
The file-length policy/gate and static/suppression decisions remain unresolved.
Supplied review findings receive terminal corrections and scoped verification;
no independent re-review of amended bytes or readiness success is claimed.

### Historical READINESS3 continuation

READINESS3 continued APG143 / V0110-F / exit 00188 with file-length no-growth allowances, lint
corrections, and lexical suppression identity. The attempt was interrupted by provider transport
failure prior to pre-final review, remaining historically blocked alongside READINESS1 and 2.

### READINESS4 technical qualification

READINESS4 completes local technical readiness and public CI preparation under Manager Decisions
A–D following independent pre-final work-review verification: all 20 static checks pass cleanly
(exit=0), canonical pytest suites achieve 4,232 unit and 893 integration passes (union statements
90.63% and branches 87.09% >= 80% gates), package builds and Syft/Grype deliverable scans report
zero High/Critical vulnerabilities, and 225 scanner suppressions and nonsecrets are formally
approved. The original READINESS4 dispatcher run encountered a terminal commit-message/protocol
validation failure followed by a recovery digest-binding defect and remains historically blocked;
the operator's manually verified private publication checkpoint on main is accepted as entry basis.
Public PR CI is not run; public release is not started.

## APG144 public staging preparation

APG144 continues the approved v0.11 program as the bounded V0110-G preparation slice
and its corrective follow-up (STAGING-PREP4), allocating exit 00189. Following STAGING-PREP1/2
unaccepted handoff claims and STAGING-PREP3 candidate validation exit 1 under isolated test execution,
STAGING-PREP4 repairs candidate test execution, provisions pinned runtimes, and establishes
factual acceptance boundaries. The phase prepares a disclosure-safe, locally verified untagged public
candidate from prospective source against the accepted public base commit
`250ce73a3dac71a89b8efeee9b8fe6cb0420bf18`, closes the pre-disclosure documentation gap with
semantic labels, and delivers a tested, attended stage-only operator handoff via maintained
release staging operator tooling. All 55 inherited decisions remain terminal and valid; 45
canonical skills (14 stable / 31 provisional), six active CSS/JS debts, and the 11,507-byte
ceiling are preserved. External pending state is preserved: `public_staging: not_started`
(drift observed: diverged remote staging branch e537cb22 exists with parent 9813a152, requiring
reconciliation before attended staging), `public_pr_ci: not_run`, `public_release: not_started`,
and branch protection remains unconfigured (empirically verified on 2026-09-13 via GitHub API:
HTTP 404 branch not protected, rulesets empty). This dispatch performs no public mutation; the
dispatcher owns private Git publication.

## APG145 hosted CI repair and staging correction

APG145 continues the approved v0.11 program as the hosted-CI repair and staging
correction slice under V0110-G, allocating exit 00190. Following the 7 failed jobs and
1 skipped job observed in public PR #1 run 34796052087, APG145 incorporates 9
independent plan-review findings, deliberately reversing advisory finding E2
(mapping index == -1 to driver) per OASIS SARIF §3.54.4, to resolve root causes across
toolchain bootstrap (tomli==2.4.1 pin in bootstrap_static.sh), package qualification (python-work directory
creation in qualify_packages.sh), macOS Go toolchain provisioning (actions/setup-go in
public-pr.yml and error differentiation in apg_skill_library_check.py), CodeQL SARIF
tool extension rule resolution in codeql_policy.py, source and fixture security
remediations (skills.go slice allocation, runner.mjs descriptor-based O_NOFOLLOW file read
and origin reflection elimination, test permission normalization to 0o700/0o600/0o710),
matrix receipt resilience (prescribed artifacts and honest failure receipts recording
unavailable_artifacts in matrix_receipts.py), and linear staging correction operator
discipline (stage_operator.py and apg_public_release.py update mode on staging parent
cd525f33ba2527862670d34d01fbdfb5f267b66c, public base ancestry 250ce73a..., and PR #1
reuse without force-push). All 55 inherited decisions remain terminal and valid; 45
canonical skills (14 stable / 31 provisional), six active CSS/JS debts, and the 11,507-byte
ceiling are preserved. External pending state is preserved: hosted_pr_run_1: failed
(PR #1 run 34796052087), correction_hosted_validation: pending, public_release: not_started.
This dispatch performs no public mutation; the dispatcher owns private Git publication.
