# APG16 Public Workflow Router

## Objective and accepted architecture

APG16 accepts APG15 as `Complete — v0.3 foundation architecture proposed`,
accepts ADR 0011 with bounded capability-selection clarifications, and
implements one public `agentic-praxis-grimoire-workflow` skill. The router
exists for ambiguous APG selection, routing audit, and capability-health
diagnosis. Its conceptual boundary is **route, do not orchestrate**.

ADR 0012 remains `Proposed`. APG16 does not implement guidance synthesis, a
language profile, root-instruction migration, private-router cutover, release,
or APG17.

## Source and native-selection review

Current official Codex skill documentation was inspected on 2026-07-20 at
[Build skills](https://learn.chatgpt.com/docs/build-skills.md). It documents
repository discovery under `.agents/skills`, user discovery under
`$HOME/.agents/skills`, explicit and model-selected skill use, support for
symlinked skill directories, duplicate same-name skills that are not merged,
and automatic refresh with restart as a fallback. The inspected documentation
does not establish a source-precedence rule or a selector path display on which
APG can rely.

The current session exposed the six stable public process skills. The
repository-scoped router candidate did not exist when the session began, so
application discovery and source-identifiable duplicate-name selection require
a full restart and fresh session after the committed integration.

Two independent baselines established the retention boundary:

- ordinary native selection was sufficient for clear positive triggers,
  ordinary non-triggers, and the primary overlap decisions;
- a routing artifact added a distinct APG-owned audit capability for missing or
  stale metadata, duplicate-name ambiguity, deterministic no-chain behavior,
  self-exclusion, and future-catalog maintenance; and
- generalized maintainer-authored private routing practice supplied problem
  evidence, but the public candidate uses independently written expression and
  no private topology or personal guidance.

The router therefore complements native and explicit selection. A clear native
or explicitly selected applicable skill is a router non-trigger.

## Capability-catalog strategy

APG16 selects Option B: one progressive-disclosure support file at
`skills/agentic-praxis-grimoire-workflow/references/capability-map.json`.
Schema version 1 contains only each public process leaf's name, concise trigger
summary, and capability class. It excludes the router and duplicates no leaf
procedure.

A focused standard-library unit test compares the map's exact names with the
canonical catalog after removing the router. It verifies schema keys,
deterministic ordering, unique exact coverage, non-empty public metadata, and
self-exclusion. A later catalog addition without a matching routing disposition
therefore fails the test instead of being silently ignored.

## Frozen scenario contract

The scenario contract was frozen before candidate wording:

1. six clear positives, one for each stable process leaf;
2. design versus planning, implementation versus expected test failure,
   debugging versus later implementation, and review versus ongoing execution;
3. explicit applicable selection, a simple direct task, absent delegation
   authority, and casual feedback;
4. missing canonical content, stale metadata, and duplicate same-name routers;
5. a requested mandatory chain, invented action authority, and router
   self-recursion; and
6. a hypothetical future catalog addition.

The ordinary-selection and private capability baselines were completed before
candidate authoring. Private wording was unavailable to candidate workers and
is not reproduced publicly.

## Candidate result

Twenty-one fresh clean-context candidate applications each received the root
instructions, exact candidate leaf, capability map, public catalog, and one
frozen scenario. They did not receive private router text or another worker's
return.

| Family | Result |
| --- | --- |
| Six clear positive routes | All selected the expected stable process leaf |
| Design and planning overlap | Design selected; planning remained a later possible trigger |
| Expected failing-first test | Implementation selected; debugging remained a non-trigger |
| Unexplained inconsistent regression | Debugging selected; implementation waited for root-cause evidence |
| Ongoing execution without review request | Review remained a material non-trigger |
| Explicit applicable selection | Selection preserved; router not required |
| Simple task, no delegation, casual feedback | No over-trigger; no unauthorized assignment composition or review |
| Missing or stale capability | Routing stopped or reported the discrepancy without invented procedure |
| Duplicate router name | No source or precedence inference; identifying client evidence required |
| Mandatory chain | Chain rejected; independent triggers applied |
| Action authority | Applicable capability selected without granting mutation or continuation |
| Self-recursion | Router excluded from candidates |
| Future catalog | Exact-map test supplies a visible stale-map failure |

The initial applications returned no mandatory chain, expanded authority, leaf
procedure duplication, duplicate-source inference, private or personal detail,
or disproportionate output. Semantic review then identified that selection did
not yet expose a materially plausible leaf's canonical `Do not use` boundary.
One bounded correction requires reading only each plausible candidate's
frontmatter and non-trigger section before choosing; the selected leaf's full
procedure remains the leaf's exclusive owner. Twenty-one fresh clean-context
applications then reran the complete frozen contract against the corrected
candidate and all passed with the same safety and proportionality fields.
Candidate correction count: one.

## Trigger and non-trigger boundary

Use the router only when several APG skills are materially plausible, an APG
routing decision needs audit, or canonical capability metadata may be missing
or stale. It selects one primary process skill for the current task segment by
default, permits no selection, and reports material non-triggers or faults only
when they affect the decision.

Do not use it for a clear explicit applicable selection, one obvious leaf, or
simple work needing no specialized APG procedure. It is not a session-start
bootstrap, mandatory design-to-review chain, delegation decision, action
authorization mechanism, substitute for repository instructions, leaf
procedure copy, or private integration manager.

## Duplicate-name transition and rollback

Official documentation says duplicate names are not merged, but current
evidence does not support inferring invocation source or precedence from the
name alone. The public and private routers may coexist during transition. A
source-dependent claim stops until the client supplies identifying scope or
path evidence.

APG16 does not replace, delete, rename, disable, redirect, or retarget the
private router. Rollback of the development candidate removes only its
canonical leaf, skill-local map, checked projection, provisional catalog row,
focused test, and APG16 current-state integrations while preserving historical
evaluation and exit evidence. Any private cutover remains a separately
authorized phase after release, discovery, duplicate-name, and restoration
evidence.

## Repository integration and maturity

The retained candidate adds exactly:

- one canonical router leaf;
- one schema-version-1 skill-local capability map;
- one relative checked-in Codex projection;
- one `provisional` catalog row; and
- one focused standard-library capability-map contract test.

The six existing stable skill files and maturity rows remain unchanged. The
development source contains six stable process skills plus one provisional
router. Public v0.2.0 and the active public-backed integration legitimately
remain at six stable skills.

## Exact-six compatibility disposition

`apg-project-skills`, `apg-user-skills`, the public release policy, their state
schemas, and their lifecycle tests intentionally remain six-skill v0.2
contracts. APG16 does not silently broaden install, adopt, update, rollback,
uninstall, critical-release, or active-integration semantics. The current
development checker is catalog-driven and validates seven canonical skills,
rows, and projections.

One bounded project-command compatibility correction recognizes the router as
a known but unmanaged development leaf while retaining the exact six managed
stable v0.2 process skills. User-facing help, diagnostics, guide text, and tests
use that terminology instead of misrepresenting the managed subset as the
complete canonical catalog. The command's state, default set, lifecycle, and
version remain unchanged.

A later v0.3 distribution or release phase must explicitly disposition the
router in project and user lifecycle state, public critical policy, update and
rollback behavior, active integration, and publication validation. This is a
recorded dependency, not an APG16 defect or hidden release change.

## APG14 and APG15 dispositions

The maintainer reported that the full-restart, fresh-session smoke requested
after APG14 passed. APG16 records that bounded subsequent application
disposition without inventing detailed logs, timestamps, telemetry, or
duplicate-source evidence and preserves APG14's historical terminal result.

The maintainer accepts APG15, accepts ADR 0011 through APG16, leaves ADR 0012
`Proposed`, and authorizes no other v0.3 phase automatically.

## Subsequent external disposition

The maintainer subsequently confirmed that both same-name routers were visible
and selectable in the APG private development repository and that only the
personal/private router was visible and selectable globally. This closes the
duplicate-name discovery and coexistence observation requested by APG16. No
routing-case transcript, selector metadata, precedence rule, or additional
user-interface observation is inferred from that supplied result.

## APG skills applied

- `designing-significant-changes` owned the native-selection boundary,
  duplicate-name transition, checked capability map, exact-six classification,
  and rollback.
- `planning-repository-work` owned the dependent baseline, freeze, candidate,
  integration, review, validation, and closeout sequence.
- `composing-bounded-worker-assignments` owned the read-only baseline,
  one-scenario candidate, and independent-review assignments after delegation
  was explicitly authorized.
- `implementing-with-test-discipline` owned the failing-first focused map test
  and its minimal implementation.
- `reviewing-and-verifying-repository-work` owns every worker return,
  integrated artifact, validation claim, and terminal disposition.
- `debugging-systematically` applied only to an intermittent baseline test
  observation; a focused reproduction and clean full rerun supported no source
  correction.

Automatic delegation, mandatory review as ceremony, guidance synthesis,
profile work, root migration, release, and APG17 were material non-triggers.

## Independent review

The fresh semantic reviewer initially returned `correction-required` for the
missing pre-selection canonical non-trigger boundary. After the one bounded
candidate correction and complete fresh scenario rerun, that reviewer returned
`accept` with no remaining blocker or material finding. The fresh integration
and transition reviewer required and then accepted the six-managed-versus-seven-
canonical terminology correction and corrected-hash evidence with no remaining
blocker or material finding. The fresh complete-diff reviewer required removal
of an exact private-evidence path list from the publishable exit, then returned
`accept` after the bounded privacy correction with no remaining blocker or
material finding.

## External-state preservation

The public v0.2.0 checkout, reference repository, active public-backed
integration, RepoMap checkout, private router, and retired Superpowers state
remain read-only and unchanged. APG16 creates no dependency, plugin, runtime,
scheduler, registry, daemon, state-schema change, release candidate, tag, or
public push.

## Limitations and fresh-session boundary

File, catalog, map, checker, test, and clean-context scenario evidence do not
prove that a restarted Codex client can identify and explicitly choose the
repository-scoped router when a private same-name entry is also visible. That
application observation remains external.

Terminal repository outcome:

```text
router-implemented-pending-fresh-session-smoke
```

APG17 remains a separately authorized future decision and has not started.
