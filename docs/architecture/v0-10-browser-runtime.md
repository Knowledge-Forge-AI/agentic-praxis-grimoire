# v0.10 Browser Runtime and Composition

## Scope and disposition

APG125 is the final capability slice, a work-stage candidate pending dispatcher
pre-final review and closeout. The proposal disposition is amend: consumer
prerequisites, separate consumer server, distinct old/new matrices, server-side
Fetch evidence, structured-fact refusal and final reservation semantics are
incorporated without expanding the original assignment. Exit 00170 is allocated.

## Owners and admission

`browser-runtime-profile` owns browser host behavior: DOM and lifecycle, events,
scheduling, origins, browser Fetch, storage scoping, resource loading and cleanup.
JavaScript owns language and module live bindings; TypeScript owns checking;
CSS and SVG own their authoring semantics; React and JSX own components/syntax;
Playwright owns the runner; web accessibility owns conformance hierarchy; Vite,
npm and Node own their tooling or execution concerns. HTML authoring outside
host behavior has no new owner. No Tauri or composition meta-skill is added.

Current `v0.10-browser-runtime` admits 45 canonical/catalog/projection/discoverable
leaves at 14 stable / 31 provisional. All 44 prior description bytes are frozen.
The final description reservation is at most 330 bytes and the combined ceiling
is 11,507 UTF-8 bytes. All six named reservations are admitted; unknown future
leaves are refused independently of remaining bytes. Historical policy meanings
and the SVG-only complete-file ceiling remain unchanged.

## Browser evidence

The maintained APG123 supervisor owns synthetic loopback fixtures. The original
SVG/Playwright/accessibility 24-scenario matrix stays separately identifiable
from fourteen browser-runtime cases, each required in Chromium, Firefox and
WebKit. Server allowlists and observations own CORS/preflight/credential and
worker/resource evidence. Browser interception alone cannot qualify these
boundaries. BR06 replaces interception with a restrictive meta-CSP for its four
local Fetch endpoints so native preflight reaches the server; a fifth valid local
endpoint is refused without a server request. This is a bounded containment
predicate, not full CSP conformance or OS isolation. Unexpected initiating errors retain sanitized class, message and
cause. Caller-owned scratch custody and exact process cleanup remain mandatory.
Optional service-worker behavior remains unqualified unless separately executed
with deterministic containment. No real browser profile or runtime external
network is used.

A normal-browser result, including WebKit, never qualifies an installed Tauri
WebView. Claims depending on embedded behavior need the actual host and engine.

## Composition and context

The versioned APG125 composition fixture supplies explicit sets for scripted and
typed SVG authoring, a React browser workbench, accessible/host/vector UI tests,
and build/install work. Each set has a reduced control task and explains every
added owner. A control is sufficient only for its narrower question. Vite/npm
are absent from UI-only questions. Adjacent leaves are not auto-loaded.

The existing resolver, materializer and footprint adapter measure selected
descriptions, bodies, support and actual materialized bytes. Comparisons bind
to corpus, request, result and measurement identities. Exact budget fits and
one-byte refusals are tested without truncating selections. Browser-runtime
language/capability aliases remain unknown and the accepted unmapped browser
runtime fact remains unmapped. These are byte measurements, not provider token
counts, prompt overhead or context-fit evidence.

## Consumer and handoff

A fresh committed consumer export supplies disposable dogfood. Entry observation
confirms a direct Vite 8.2.2 application, React 19.2.8 and a Node >=22.23.2 floor;
its Tauri surface is separate. A suitable consumer Node runtime is independently
required. Lockfiles and maintained preparation/build commands control the run.
Consumer output uses its own task-owned loopback server, never the synthetic
fixture server or fixture tree. Consumer failures are retained without fixes.
Concurrent source changes are excluded from qualification authority.

APG124 is manager accepted as `V0100_TOOLCHAIN_SLICE_QUALIFIED`; this fresh
observation does not revise its earlier capture, failures or drift-attribution
limitation. Success hands off only to separately authorized integrated readiness
and release qualification. No additional v0.10 leaf or public release follows
automatically. Rollback removes final admission and integration coherently,
restoring Toolchain current semantics while preserving historical phase records.
