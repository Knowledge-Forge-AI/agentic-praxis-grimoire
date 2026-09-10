---
name: playwright-test-profile
description: Use when a project selects Playwright Test and decisions depend on configuration, fixtures, locators, waiting, isolation, parallel execution, browser projects, network controls, or test artifacts; not for accessibility standards or general browser/runtime semantics.
---

# Playwright Test Profile

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Proposed`.
Compatibility target: consumer-selected `@playwright/test` 1.62.1.

## Core principle

Bind runner evidence to the installed package, configuration, browser project
and actual execution. A passing test proves its asserted observation within
that environment; it does not establish universal browser behavior.

## Do not use

Use only when the project has selected Playwright Test. Generic test strategy,
JavaScript, TypeScript and Node keep their existing owners. SVG authoring belongs
to `svg-language-profile`; accessible semantics and the evidence hierarchy belong
to `web-accessibility-profile`. Browser/DOM runtime semantics need a separately
selected owner. Do not install dependencies or change project policy merely to
apply this profile. Selection is explicit; adjacent profiles are not implicit.

## Procedure

1. Inspect the manifest, lockfile, installed package, selected config and scripts.
   Record package integrity, Node/OS/architecture and browser revisions/versions.
   Keep the consumer's exact version; newer documentation is not upgrade authority.
2. Identify the test's observation and failure predicate, project dependencies,
   state and resource owners, allowed network, artifacts and cleanup boundary.
3. Apply the runner clauses below. Start with the smallest meaningful case and
   a negative control; broaden engines when the claim crosses browser projects.
4. Execute using owned temporary state and record failures, retries, skips,
   interruptions and unavailable engines separately. Report remaining limits.

### Runner contracts

**PW-01-IDENTITY.** Use the selected package's CLI and API declarations. Match
browser binaries to its manifest; installation is a separate authorized action.
Reuse existing caches read-only or install into task-owned scratch. Channels
such as branded Chrome are distinct from bundled Chromium. Record executable
identity and launched version; a cache directory alone proves no launch.

**PW-02-CONFIG.** Trace config loading, CLI overrides, testDir/testMatch/testIgnore,
projects, dependencies, use options, setup/teardown and webServer. Ensure discovery
actually collects the intended tests. Keep independent behavior in independent
tests; use describe groups for shared organization, not hidden order coupling.
Distinguish top-level worker/timeout/reporter settings from context use options.

**PW-03-FIXTURES.** Understand worker-scoped browser fixtures and test-scoped
context/page fixtures. Use fixture dependency teardown with try/finally; close
manually created BrowserContexts with await context.close() and dispose manually
created APIRequestContexts with await requestContext.dispose(). Fresh contexts isolate browser
storage but do not isolate servers, databases, files or shared accounts. Select
synthetic accounts or explicit external-resource coordination. Storage/auth state
is sensitive, scoped and expiring; never commit it or reuse real user profiles.

**PW-04-LOCATORS.** Prefer role/name, label and project-owned test identifiers.
Locators re-resolve elements; avoid stale handles and positional first/nth fixes
that conceal ambiguous intent. Single-element actions are strict: assert or
refine uniqueness. Frames require the intended frame boundary; popup/page events
must be registered before the action that opens them.

**PW-05-WAITING.** Let actionability checks establish visibility, stability,
event reception and enabled/editable conditions appropriate to the action.
Force bypasses checks and needs an explicit reason. Use awaited web-first
assertions; a one-time isVisible result is not a retrying assertion. Use
expect.poll/toPass for a bounded repeated observation with idempotent effects.
Wait on the specific response, URL or UI state, not arbitrary sleeps or network
idle as universal readiness. Auto-waiting does not prove application correctness.

**PW-06-FAILURE.** Distinguish test, assertion, action, navigation and global
timeouts. In 1.62, supported operations accept AbortSignal; use an AbortController
and verify the selected declaration before passing signal. Aborting does not
disable ordinary timeouts. SIGINT is runner interruption, not an assertion
failure; record terminal status and ensure owned workers/browsers terminate.
Retries diagnose instability and do not make a first failure disappear. Record
flaky classifications; do not blanket-annotate unrelated errors as expected.

**PW-07-CONCURRENCY.** Worker processes and shards multiply resource demand.
Tests in different files/projects can overlap; workers can restart after failure.
Use unique per-test resources or externally coordinated ownership, not in-memory
locks across workers. Check fullyParallel, serial groups, retries and shard
selection together. Do not use newer test-lock APIs as 1.62 capabilities.

**PW-08-NETWORK.** Install context-wide routing before pages, frames and popups.
Define allowed origins, paths, redirects and resource types; block service workers
when interception must observe every request. Mocked responses prove the mock
contract, not production service behavior. APIRequestContext may bypass page
network controls and can share or isolate cookie state depending on construction;
give it its own authorization, cleanup and assertions. Keep synthetic tests local.

**PW-09-FILES.** Register download/filechooser waits before triggering actions.
Save downloads explicitly into owned paths before context teardown; uploaded files
must be authorized fixtures. Reject traversal, unintended overwrite and private
payload retention. Assert intended URL/target for navigation, frames and popups;
do not assume the newest page is the right one.

**PW-10-ARTIFACTS.** Set screenshot, trace and video retention deliberately;
verify pass/failure behavior through actual runner outcomes. Traces, screenshots,
URLs, headers and storage state can expose secrets. Retain only permitted artifacts
with access, lifetime and cleanup ownership; scrub neither evidence nor failures
silently. Test interruption cleanup for browser processes and temporary profiles.

**PW-11-VISUAL.** Pin engine, OS, fonts, viewport, scale and rasterization context.
Control animation, time, randomness, asynchronous assets and dynamic content.
Review baseline updates as product changes; never update just to make a test pass.
Use a deterministic varied-image negative to prove comparator sensitivity.
Same-run image comparisons are not portable historical golden baselines.

**PW-12-SEMANTIC-EVIDENCE.** Role/name assertions and supported ARIA snapshots
observe Playwright's semantic representation. Playwright/ARIA snapshots are not
a screen reader. Route meaning, keyboard contracts and WCAG interpretation to
web accessibility; automated passes do not prove WCAG conformance. Do not claim
cross-browser support from one project or substitute channels for missing engines.

### Response guide

| Level | Runner signal | Response |
| --- | --- | --- |
| Green — routine | Known package/project and isolated observation | Run proportional project checks |
| Yellow — caution | Version, timing or browser difference is uncertain | Inspect the selected API and reproduce the bounded case |
| Orange — warning | Shared resources, retries or baseline changes alter evidence | Record the authorized decision, negative controls and rollback |
| Red — crisis / stop | Untrusted network, private state exposure or unproven cleanup | Stop the dependent action and resolve custody or authority |

## Project-owned parameters

The project selects versions, dependencies, browsers, environments, resources,
timeouts, retries, parallelism, snapshots, privacy and retention. This profile
does not create universal numeric test-size or file-size limits. Caller context
budgets remain enforced independently of discovery-description reservations.

## Evidence and completion

Report exact selection/config, discovered and executed cases, engine identities,
negative controls, failures/skips/retries, retained artifacts and cleanup evidence.
The APG123 register links PW01 strictness, PW02 actionability, PW03 assertions,
PW04 isolation, PW05 timeout/AbortSignal, PW06 routing, PW07 navigation,
PW08 artifacts, PW09 visual variation and PW10 actual runner interruption.
These are maintained browser observations, not complete API qualification.
Source and scenario boundaries are in the [contract](../../docs/specs/playwright-test-profile.md).

## Stop or escalate

Stop dependent qualification when version/config authority is missing, an engine
cannot launch, resource custody is unclear, private state could escape, required
cases skip, or cleanup is unproven. Keep the observed failure and route the missing
decision to its owner; do not upgrade, download globally or weaken assertions.

## Common mistakes

- Treating locators as cached elements or forcing an ambiguous action.
- Replacing awaited assertions with sleeps or one-time boolean checks.
- Assuming context isolation also isolates server state.
- Calling retry success deterministic or a semantic snapshot assistive technology.
- Updating baselines or retaining traces without reviewing their contents.
