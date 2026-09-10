# APGR v0.10 backlog consolidation

## Scope and authority

v0.10 is a consolidation release. The six frontend leaves are authored and
integrated provisionally; the original APG125 dispatch remains provider-blocked
by Astra capacity failure. APG126 qualifies its preserved candidate without
replaying implementation. APG126 is manager-accepted after exact-tree recovery;
its original dispatcher aggregate remains historically blocked with
`PATH_DISPOSITION_INVALID`. APG127 delivers the reporting consolidation candidate
qualified through provider closeout after dispositioning dispatcher pre-final
findings. Publication remains dispatcher-owned.
APG124 remains manager accepted. This census authorizes no implementation,
maturity promotion, external-project mutation or release.

Current topology is 45 leaves, 14 stable and 31 provisional. Descriptions total
11,142 UTF-8 bytes under 11,507, leaving 365 bytes. All 44 pre-APG125 descriptions
are preserved. No unused named reservation remains. These are byte measurements,
not provider-token or context-fit measurements.

## Classification and source authority

- `V010_READY_NOW`: APGR-owned work with available prerequisites, a coherent
  consolidation purpose and a bounded implementation/qualification path.
- `EXTERNAL_GATE`: depends on an accepted contract or milestone owned by another project.
- `CONDITION_TRIGGERED`: waits for its recorded measured or maintenance trigger.
- `HISTORICAL_SUPERSEDED`: delivered, replaced or otherwise no longer actionable.
- `OPTIONAL_LATER`: useful work that does not need to hold v0.10.

A classification is not execution authorization. Historical deferments were traced
through the [v0.9 roadmap](v0-9-roadmap.md),
[reporting protocol](manager-worker-protocol.md),
[v0.7 architecture](architecture/v0-7-embeddable-toolkit.md),
[discovery decision](adr/2026/09/0053-v0-10-discovery-capacity-and-svg.md),
[known-debt register](governance/language-profile-known-debt.json) and subsequent
phase records. The machine-readable census retains exact source digests,
prerequisites, supersession, acceptance conditions and limitations.

## Backlog disposition

| Item | Classification | Bounded disposition |
| --- | --- | --- |
| `APGR-CAP1` | `HISTORICAL_SUPERSEDED` | Formal Capacity Decision Record (ADR 0053) reserving 6x 330 UTF-8 description bytes (up to 11,507 bytes ceiling) for six named candidates |
| `SKILL-SVG` | `HISTORICAL_SUPERSEDED` | Provisional `svg-language-profile` skill leaf under `skills/svg-language-profile/SKILL.md` with complete-file ceiling of 20,480 bytes |
| `SKILL-PLAYWRIGHT` | `HISTORICAL_SUPERSEDED` | Provisional `playwright-test-profile` leaf under `skills/playwright-test-profile/SKILL.md` |
| `SKILL-A11Y` | `HISTORICAL_SUPERSEDED` | Provisional `web-accessibility-profile` leaf under `skills/web-accessibility-profile/SKILL.md` |
| `SKILL-VITE` | `HISTORICAL_SUPERSEDED` | Provisional `vite-build-profile` leaf under `skills/vite-build-profile/SKILL.md` |
| `SKILL-NPM-PKG` | `HISTORICAL_SUPERSEDED` | Provisional `npm-package-manager-profile` leaf under `skills/npm-package-manager-profile/SKILL.md` |
| `SKILL-BROWSER` | `HISTORICAL_SUPERSEDED` | Provisional `browser-runtime-profile` leaf under `skills/browser-runtime-profile/SKILL.md` and composition verification |
| `APGR-REPORT-GO` | `HISTORICAL_SUPERSEDED` | Public Go package `report` providing `New`, `Show`, `Diff`, `Operational`, `ParseRecords`, and `Append` |
| `APGR-REPORT-STALELOCK` | `HISTORICAL_SUPERSEDED` | APG127 retains and regression-tests the existing `internal/atomicfile` transaction/dead-process lock recovery and `apgr report recover`; no recovery redesign |
| `APGR-REPORT-VERIFIER` | `HISTORICAL_SUPERSEDED` | Delivered in the APG127 candidate: read-only `Verify`/`VerifyFile` and `apgr report verify <path>`, canonical semantic owners and historical persisted fixtures |
| `APGR-REPORT-OPS-SEMANTICS` | `HISTORICAL_SUPERSEDED` | Delivered in the APG127 candidate: shared pre-framing recognized-field and association validation; explicit historical persisted compatibility and standalone legacy/free-form handling |
| `APGR-REPORT-PUREGO-GIT` | `CONDITION_TRIGGERED` | Replacement of internal Git CLI exec in `report.Service` with in-process pure-Go Git object reading |
| `APGR-REPORT-OUTBOX` | `EXTERNAL_GATE` | Downstream transaction manager in JACA consuming `report.Result` and handling outbox state |
| `APGR-DEBT-JS-QD-001` | `HISTORICAL_SUPERSEDED` | Exact two-artifact CommonJS seam qualified in APG128; superseded under the integrated Node runtime owner |
| `APGR-CI-QUAL` | `EXTERNAL_GATE` | CLI option `--summary-file <path>` emitting strict 6-field JACA summary; `policy`, `unit`, `integration`, `unit-integration` roles; handoff specification |
| `APGR-XO-COMPAT` | `EXTERNAL_GATE` | Caller-owned adapter fixture in `testing/fixtures/xo_consumer/` and `docs/architecture/jaca-xo-handoff.md` |
| `SKILL-KG-QUALITY` | `EXTERNAL_GATE` | Provisional `knowledge-graph-quality-profile` skill leaf under `skills/knowledge-graph-quality-profile/SKILL.md` |
| `SKILL-VER-PROTO` | `EXTERNAL_GATE` | Provisional `versioned-protocol-profile` skill leaf under `skills/versioned-protocol-profile/SKILL.md` |
| `SKILL-MIGRATION` | `CONDITION_TRIGGERED` | Ownership analysis document and potential generalized migration skill leaf (`migrating-system-implementations`) |
| `APGR-HOTSPOT-CHURN` | `OPTIONAL_LATER` | Additive churn and growth dimension in `hotspot` JSON schema `apg.hotspot-report/v1` |
| `APGR-CXT-FOOTPRINT` | `HISTORICAL_SUPERSEDED` | Public Go package `footprint` providing `Measure`, `Compare`, and `Project` |
| `APGR-CXT2B` | `OPTIONAL_LATER` | Optional adapter package importing third-party Caveman context measurement dumps |
| `APGR-CXT-BUDGET-COMPRESSION` | `CONDITION_TRIGGERED` | Aggressive semantic compression of existing 39 skill descriptions to reclaim 1,200–2,000 bytes |
| `APGR-DEBT-CSS-QD-001` | `CONDITION_TRIGGERED` | Introduce a compact independent source-purpose binding when future TARGET-007 maintenance justifies it. |
| `APGR-DEBT-CSS-QD-002` | `CONDITION_TRIGGERED` | Add an independently frozen disagreement index if the lane mechanism becomes current authority again. |
| `APGR-DEBT-CSS-QD-003` | `CONDITION_TRIGGERED` | Add a bounded row/source relation only when a real maintenance workflow needs machine generation or automatic adjudication. |
| `APGR-DEBT-CSS-QD-004` | `CONDITION_TRIGGERED` | Add the invariant during the next material route-schema revision. |
| `APGR-DEBT-CSS-QD-005` | `CONDITION_TRIGGERED` | Remove the arrays during a future compatible compact-schema revision. |
| `APGR-DEBT-JS-QD-002` | `HISTORICAL_SUPERSEDED` | APG128 qualifies narrow raw-stream custody, bounded escaping diagnostics and pytest-local rendering |
| `APGR-DEBT-JS-QD-003` | `HISTORICAL_SUPERSEDED` | APG128 qualifies the named static owner set and supported annotated/module/callable alias forms |
| `APGR-DEBT-JS-QD-004` | `HISTORICAL_SUPERSEDED` | APG128 qualifies four independent same-type wrong root values and retained positives |
| `APGR-DEBT-JS-QD-005` | `CONDITION_TRIGGERED` | Add one proportionate direct managed-report identity binding, preferably an existing report ID plus exact full-file digest or reusable report-integrity owner, that rejects a changed APG79B report without making the large report a semantic oracle, release payload, or duplicated current evidence system. |
| `APGR-REPORT-IDEMPOTENCY` | `HISTORICAL_SUPERSEDED` | Delivered in the APG127 candidate: opt-in exact-byte retry/conflict policy over retained identities, preserved default duplicates and recovery, golden and real-filesystem/source-stability tests |
| `APGR-REPORT-PROJECT-KEY` | `OPTIONAL_LATER` | Evaluate a mapping only for a concrete consumer naming requirement; existing override validation remains controlling. |
| `APGR-REPORT-RESULT-FIELDS` | `OPTIONAL_LATER` | Freeze a useful consumer vocabulary before restricting currently accepted fields. |
| `APGR-PUBLICATION-LINT` | `HISTORICAL_SUPERSEDED` | Current release projection and public-surface checks supersede the generic missing-lint deferment; further checks require a concrete uncovered failure. |

## Current external and consumer evidence

Fresh Repo Map inspection resolves ADR 0056 by its actual title, *Reconciled
Investigation And Program Direction*, and ADR 0057, *Cloud-First And Multi-Source
Architecture Reconciliation*. Later ADR 0059 already freezes portable snapshot,
receipt and publication-bundle contracts; ADR 0061 and STR-PUB5 implement a
publisher route. Therefore a claim that these contracts are simply absent would
be stale. The current REVISE22 status still records hosted-CI state as unknown,
with integration qualification and promotion separately gated. Graph-quality and
versioned-protocol profiles remain behind qualification of their specific stable
consumer-facing contracts and empirical multi-source evidence. An older version
assignment alone does not admit them into v0.10.

JACA's current CI contract follows ADR 0020, which partially supersedes
ADR 0008's earlier promotion topology. Project validation remains consumer-owned;
logical gates supply evidence without granting promotion authority. Its roadmap
artifact-interface contract reserves orchestration to JACA and permits future
imported APGR primitives. The earlier checkout observations remain historical;
this census binds the newer CI checkout separately. APGR's
[CI](architecture/jaca-ci-handoff.md) and [XO](architecture/jaca-xo-handoff.md)
provider-side handoffs are already qualified under APG114. Consumer adoption is
separate; this census does not assert that historical handoff labels are current
JACA milestone names or that adoption is complete. No Dinas runtime dependency
was needed for the surviving APGR implementation items.

Fresh Theme Forge package metadata remains consistent with studio 0.2.0,
Vite 8.2.2, React 19.2.8 and the retained compiler 0.1.1. This is read-only
metadata evidence. The earlier producer capture retains 177 passing studio tests
and one compiler-version assertion mismatch. No consumer tests/builds were run
in APG126, and later-source runtime parity or failure causality is not inferred.
The browser smoke exercised the host-unavailable fallback. Desktop-browser
results do not qualify actual Tauri/WebView, sidecars or assistive technology.

## Maturity census

The [maturity policy](skill-authoring-and-maintenance.md) requires repeated
positive use, representative non-triggers, no unresolved material defects,
required non-author review and rollback support. Provisional status is not itself
unfinished feature work. All 31 leaves have canonical/projection and metadata
integrity evidence; their historical authoring and integration records remain
valid. This audit establishes no new complete leaf-specific promotion receipt. The
per-leaf rows record a uniform evidence gap, not discriminating maturity scores
or completed per-leaf promotion investigations. Future promotion work must bind
actual usage and non-trigger observations for each selected leaf.
Unestablished current evidence is not a claim that historical scenario tests failed.

Go, Go-test and pytest are reasonable candidates for focused usage-evidence
readback because APGR repeatedly exercises their domains. Running those tools
does not itself prove agents used the corresponding guidance. No leaf is promoted.

| Provisional leaf | Current evidence and remaining promotion requirement |
| --- | --- |
| [`astro-profile`](../skills/astro-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`browser-runtime-profile`](../skills/browser-runtime-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`chatgpt-manager-workflow`](../skills/chatgpt/chatgpt-manager-workflow/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`composing-approved-roadmap-assignments`](../skills/chatgpt/composing-approved-roadmap-assignments/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`converting-bash-scripts-to-python`](../skills/converting-bash-scripts-to-python/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`css-language-profile`](../skills/css-language-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. Blocking debt: CSS-QD-001, CSS-QD-002, CSS-QD-003, CSS-QD-004. |
| [`dockerfile-profile`](../skills/dockerfile-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`go-cmp-test-profile`](../skills/go-cmp-test-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`go-language-profile`](../skills/go-language-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`go-test-profile`](../skills/go-test-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`gomock-test-profile`](../skills/gomock-test-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`javascript-language-profile`](../skills/javascript-language-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. Blocking debt: JS-QD-005. APG128 resolves the first four qualification debts without promotion. |
| [`jsx-language-profile`](../skills/jsx-language-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`markdown-language-profile`](../skills/markdown-language-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`mdx-profile`](../skills/mdx-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`minitest-test-profile`](../skills/minitest-test-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`nix-test-profile`](../skills/nix-test-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`nodejs-runtime-profile`](../skills/nodejs-runtime-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`npm-package-manager-profile`](../skills/npm-package-manager-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`playwright-test-profile`](../skills/playwright-test-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`postgresql-database-profile`](../skills/postgresql-database-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`pytest-test-profile`](../skills/pytest-test-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`react-component-profile`](../skills/react-component-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`ruby-language-profile`](../skills/ruby-language-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`sqlite-database-profile`](../skills/sqlite-database-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`svg-language-profile`](../skills/svg-language-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`typescript-language-profile`](../skills/typescript-language-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`vagrantfile-profile`](../skills/vagrantfile-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`vite-build-profile`](../skills/vite-build-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`vitest-test-profile`](../skills/vitest-test-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |
| [`web-accessibility-profile`](../skills/web-accessibility-profile/SKILL.md) | Catalog/projection and metadata verified; retain historical integration. Bind current repeated-use/non-trigger, defect, rollback and non-author maturity evidence before promotion. |

## Closeout follow-up and limitations

At the APG128 handoff, the fixed browser scenario sets validated successfully. The runner still
uses an APG123 fallback for an unrecognized family; the receipt validator rejects
an entirely unknown family. Shared family derivation and producer-side fail-closed
behavior are deferred to the integrated-readiness harness review before any new
scenario family is admitted. No unknown-family qualification is claimed.

APG126 entered with integration branch coverage at 3,625/4,530, one covered
branch above its minimum. APG127 passes at 3,631/4,534, three covered branches
above the 3,628 required at 80%. APG128 passes at 3,646/4,554, two above the
3,644 required. That was a fragile margin, not a durable slack guarantee.
Thresholds and historical failed attempts remain unchanged.

## Consolidation delivered; integrated readiness is next

APG127 is manager-accepted as `V0100_REPORTING_CONSOLIDATION_SLICE_QUALIFIED`.
The [APG128 qualified candidate](evaluations/apg128-javascript-qualification-debt-consolidation.md)
supersedes JS-QD-001 and repairs JS-QD-002 through JS-QD-004. Closeout amends evidence claims after advisory pre-final
review; Git finalization remains dispatcher-owned. Zero `V010_READY_NOW` implementation items
remain; external, condition-triggered and optional classifications are unchanged.
JS-QD-005 still waits for its recorded historical-report custody maintenance
trigger. APG127's verifier does not itself trigger it. All CSS debt and general
leaf-specific maturity evidence requirements remain unchanged.

Integrated readiness is next: browser/composition, Go, canonical component/union
coverage and multi-ecosystem candidate packaging, with explicit maturity and
limitation review. Carry APG126's unknown-family/family-table fallback limitation
and APG127's delimiter-heavy verifier responsiveness/cancellation limitation
into that review. Neither is implemented by APG128. Publication requires accepted
readiness and separate human authority; no automatic successor is authorized.

APG128 readiness limitations also include raw-stream reachability through
suppressed exception context in the shared Node identity probe, the static
guard's named-function boundary, and its deferred optional alias negatives.
These are explicit review dispositions, not new implementation-ready backlog
items. Retain the two-branch integration coverage margin in readiness planning.

## APG132 current readiness reconciliation

APG129 retained fail-closed shared browser-family authority, bounded report
extraction/cancellation work and strengthened Node probe custody and process
guard negatives. Its blocked outcome remains historical; APG131 independently
requalifies the terminal implementation. Earlier APG128 limitation paragraphs
above describe that handoff, not defects asserted against current source.

APG127's verifier does not itself trigger JS-QD-005. The APG131 audit separates
the named APG79B conditions from compatible production-tool migrations and
stricter rejection of malformed new requests. [ADR 0054](adr/2026/09/0054-js-qd-005-refresh-trigger-interpretation.md) records
the manager ruling `JS_QD_005_REFRESH_NOT_TRIGGERED`, adopting the historical
byte-producing-owner reading and canonical refresh-field precedence. This
ruling is not inferred from missing current custody. APG131 technical
qualification is accepted; its dispatcher aggregate remains historically blocked. The one-time
integration prerequisite was satisfied at APG79E. The
[current debt discussion](governance/language-profile-known-debt.md) owns the
accepted historical verification and future recovery boundary.

The [Repo Map support roadmap](repo-map-support-roadmap.md) now owns RM-S0
through RM-S5 gates. Earlier v0.11 candidate assignments are historical.
Zero `V010_READY_NOW` implementation items remain; neither this roadmap nor
spare discovery bytes authorizes a new leaf.

[APG132 readiness](evaluations/apg132-manager-trigger-interpretation-and-final-readiness.md)
records `V0100_INTEGRATED_READINESS_WITH_REPOMAP_ROADMAP_QUALIFIED` as the current
readiness disposition, with terminal provider closeout qualified;
dispatcher Git finalization remains pending. Deterministic candidate freeze is next and separately authorized.
