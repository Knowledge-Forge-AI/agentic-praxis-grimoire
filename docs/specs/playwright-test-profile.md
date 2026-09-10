# Playwright Test profile contract

Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Proposed`.

APG123 admits this provisional runner owner for the consumer-selected exact
`@playwright/test` 1.62.1 package. The task does not authorize an upgrade.
This is original guidance, not copied upstream prose or consumer artwork.

## Sources and compatibility

Primary documentation inspected 2026-09-09 is mutable. The
[1.62 release section](https://playwright.dev/docs/release-notes#version-162)
and the installed 1.62.1 package declarations bound feature eligibility.
The separately observed 1.63 documentation is newer-version evidence only:
its test locks and newer snapshot conveniences are not admitted here.
The selected 1.62 cancellation mechanism is AbortController/AbortSignal on
supported locator operations; runner interruption is a separate SIGINT case.

| Clauses | Primary source | Evidence boundary |
| --- | --- | --- |
| PW-01, PW-12 | [Browsers](https://playwright.dev/docs/browsers), release notes | Package revision and launched engine are distinct identities |
| PW-02 | [Configuration](https://playwright.dev/docs/test-configuration) | Actual config and collected cases control |
| PW-03 | [APIRequestContext disposal](https://playwright.dev/docs/api/class-apirequestcontext#api-request-context-dispose), [Fixtures](https://playwright.dev/docs/test-fixtures), [authentication](https://playwright.dev/docs/auth) | Context isolation does not isolate external resources |
| PW-04 | [Locators](https://playwright.dev/docs/locators), [frames](https://playwright.dev/docs/frames), [pages](https://playwright.dev/docs/pages) | Strictness is an automation contract |
| PW-05 | [Actionability](https://playwright.dev/docs/actionability), [assertions](https://playwright.dev/docs/test-assertions) | Waiting is bounded and assertion-specific |
| PW-06 | [Timeouts](https://playwright.dev/docs/test-timeouts), [retries](https://playwright.dev/docs/test-retries), release notes | Retry and interruption outcomes remain visible |
| PW-07 | [Parallelism](https://playwright.dev/docs/test-parallel) | Shared-resource coordination is project-owned |
| PW-08 | [Network](https://playwright.dev/docs/network) | Routing and API request custody are separate |
| PW-09 | [Downloads](https://playwright.dev/docs/downloads), pages and frames | Files and event ordering require explicit ownership |
| PW-10 | [Trace viewer](https://playwright.dev/docs/trace-viewer), configuration | Retention is tested on actual outcomes |
| PW-11 | [Visual comparisons](https://playwright.dev/docs/test-snapshots) | Engine/platform-specific pixels do not generalize |

The Playwright package is Apache-2.0; retain its installed notices. The harness
dependency is test-only and scratch-installed with lifecycle scripts disabled.
No production dependency, global package installation or package-policy change
is implied. The checked-in exact dependency contract and lockfile reproduce the
test package; downloaded browsers, if needed, belong in owned scratch only.
Existing browser caches are reusable read-only, never installation destinations.

## Maintained evidence

The [scenario register](../../src/test/fixtures/apg123-browser-ui/scenarios.json)
contains expected predicates and engine sets. `runner.mjs` exercises the selected
library; `playwright.config.js`, `supervisor.spec.js` and `supervisor_runner.mjs`
exercise actual Test discovery, fixtures, pass/failure retention and interruption.
The Python supervisor validates prerequisites and receipts. The leaf's scenario
references are navigation checks, not semantic proof of every guidance clause.
Clause IDs contain a hyphen and a descriptive suffix (for example,
`PW-07-CONCURRENCY`); scenario IDs do not (`PW07` tests navigation).
Cite the full clause ID for guidance and the scenario ID for executed evidence;
matching numeric portions do not imply coverage. No dedicated scenario qualifies
`PW-07-CONCURRENCY` sharding or cross-worker shared-resource coordination.

| Cases | Clause coverage | Adverse control / limitation |
| --- | --- | --- |
| PW01–PW03 | PW-04–PW-05 | Ambiguity, permanent disablement and impossible text reject |
| PW04 | PW-03 | Concurrent fresh contexts do not inherit synthetic state |
| PW05 | PW-06 | Timeout and explicit AbortSignal cancellation are distinct |
| PW06–PW07 | PW-04, PW-08–PW-09 | Untrusted requests blocked; exact frame/popup targets asserted |
| PW08, PW10 | PW-02–PW-03, PW-06, PW-10 | Pass artifacts absent, controlled failure artifacts present, real interruption |
| PW09 | PW-11 | Controlled image variation rejects equality; same-run comparison only |
| SVG01–SVG03 | Composition with SVG | Inline document external use allowed locally; denied origin/path rejected |

Principal lanes have zero retries and require all mandatory IDs in Chromium,
Firefox and WebKit. Missing, duplicate, skipped, failed or unavailable cases cannot
qualify the matrix. The suite does not exhaust sharding, uploads, video, production
authentication or every API request configuration; those remain project evidence.

## Runner and context integration

The canonical pytest combined runner has a fail-closed Playwright prerequisite
class keyed to both profile integration entrypoints. It reuses the qualified
Node contract and requires explicit `APG_PLAYWRIGHT_PACKAGE_ROOT`,
`APG_PLAYWRIGHT_OWNED_SCRATCH_ROOT` and `PLAYWRIGHT_BROWSERS_PATH`.
Packages must be exact and inside owned external scratch; all three selected
executables must exist. Validation does not download or launch them. Browser
launch and semantic evidence occur inside the maintained pytest integration tests,
so a combined pass includes the browser matrix rather than merely static tests.

Select the leaf explicitly through the existing resolver. No structured fact
vocabulary expansion or implicit neighbor loading is introduced. The description
reservation is at most 330 UTF-8 bytes. No new numeric body ceiling is introduced
for this owner; caller-supplied context budgets still fail closed.

## Completion and rollback

The phase evaluation owns current executed versions/results and limitations.
Dispatcher pre-final review and closeout remain separate from work-stage evidence.
Rollback removes the two Browser/UI leaves and their integration together while
preserving SVG, original descriptions and historical records.
