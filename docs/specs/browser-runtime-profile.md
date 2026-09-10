# Browser Runtime Profile Specification

Status: Retained provisional after APG126 qualification.
Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

## Contract and ownership

The [browser-runtime leaf](../../skills/browser-runtime-profile/SKILL.md) owns
operational clauses BR-01 through BR-16. This specification owns provenance,
traceability and qualification limits; it does not duplicate the leaf's API
rules. ADR 0053 authorizes the sixth named discovery reservation. No extra leaf,
new complete-file ceiling, Tauri profile or composition meta-skill is allocated.

Host DOM, events, scheduling, navigation, origins, browser Fetch/storage and
resource lifetime belong here. ECMAScript and Promise/module live bindings belong
to `javascript-language-profile`; typing to `typescript-language-profile`; CSS
to `css-language-profile`; vectors to `svg-language-profile`; components to
`react-component-profile`; JSX syntax to `jsx-language-profile`; runner mechanics
to `playwright-test-profile`; accessible semantics/conformance hierarchy to
`web-accessibility-profile`; build tooling to `vite-build-profile`; selected npm
to `npm-package-manager-profile`; and Node execution to `nodejs-runtime-profile`.
HTML authoring outside host/runtime behavior remains unallocated.

## Source basis and rights

APG125 uses original operational synthesis and synthetic fixtures. The primary
sources below were inspected on 2026-09-09. Living Standards are mutable;
a date and anchor are navigation/provenance, not an immutable snapshot. Drafts
are not Recommendations and standards prose does not establish engine support.
Refresh affected source facts when correcting behavior or qualifying new hosts.
MDN may help implementation research only as secondary material; it is not the
normative basis or a source of copied prose here. No external code or prose is
copied into the leaf. Any later reuse must preserve its source-specific notices.

| Source | Status / Date | Anchors and Scope | Rights boundary | Limitation |
| --- | --- | --- | --- | --- |
| [WHATWG HTML](https://html.spec.whatwg.org/multipage/) | Living Standard, inspected 2026-09-09 | Window (`#windows`), Document (`#the-document-object`), readiness (`#current-document-readiness`), pageshow/pagehide (`#pageshow-event`), visibility (`#page-visibility`), event loops (`#event-loops`), task queues (`#task-queues`), timers (`#timers`), Location (`#the-location-interface`), History (`#the-history-interface`), custom elements (`#custom-elements`), script modules (`#the-script-element`), Workers (`#workers`) | CC BY 4.0 | Mutable Living Standard; continually updated without immutable recommendation freeze. |
| [WHATWG DOM](https://dom.spec.whatwg.org/) | Living Standard, inspected 2026-09-09 | Node tree mutation (`#nodes`), MutationObserver (`#mutation-observers`), Events and 3-phase dispatch (`#dispatching-events`), EventTarget options (`#interface-eventtarget`), Shadow DOM and slots (`#shadow-trees`, `#slots`) | CC BY 4.0 | Mutable Living Standard; continually updated. |
| [WHATWG Fetch](https://fetch.spec.whatwg.org/) | Living Standard, inspected 2026-09-09 | Fetch API (`#fetch-api`), Request/Response (`#response-class`), CORS protocol and preflight (`#http-cors-protocol`), opaque filtered responses (`#concept-filtered-response-opaque`), credentials mode, AbortSignal (`#abort-fetch`) | CC BY 4.0 | Mutable Living Standard; continually updated. |
| [WHATWG URL](https://url.spec.whatwg.org/) | Living Standard, inspected 2026-09-09 | URL interface (`#url-class`), URLSearchParams (`#interface-urlsearchparams`), URL parsing and base resolution (`#concept-url-parser`), origin serialization (`#origin-serialization`) | CC BY 4.0 | Mutable Living Standard; continually updated. |
| [WHATWG Storage](https://storage.spec.whatwg.org/) | Living Standard, inspected 2026-09-09 | Storage architecture (`#storage-architecture`), quota and persistence estimation (`#storage-quota-and-usage`), origin scoping | CC BY 4.0 | Mutable Living Standard; continually updated. |
| [Web IDL](https://webidl.spec.whatwg.org/) | Living Standard, inspected 2026-09-09 | ECMAScript type mapping (`#es-type-mapping`), global interface objects, feature detection | CC BY 4.0 | Mutable Living Standard; continually updated. |
| [W3C CSSOM](https://www.w3.org/TR/cssom-1/) | Working Draft (2021-08-26), inspected 2026-09-09 | `getComputedStyle` and resolved values (`#dom-window-getcomputedstyle`, `#resolved-values`) | W3C permissive document license | Host observation does not transfer cascade/value ownership from CSS. |
| [W3C CSSOM View](https://www.w3.org/TR/cssom-view-1/) | Working Draft (2025-09-16), inspected 2026-09-09 | Element geometry (`#dom-element-getboundingclientrect`), box metrics (`clientWidth`, `offsetWidth`, `scrollWidth`, `scrollTop`), reflow triggers | W3C permissive document license | Working Draft; syntax and exact metrics subject to engine implementation. |
| [W3C Secure Contexts](https://www.w3.org/TR/secure-contexts/) | Candidate Recommendation Draft (2023-11-10), inspected 2026-09-09 | Trustworthy origin evaluation (`#is-origin-trustworthy`), feature gating (`#feature-restricted-to-secure-contexts`) | W3C permissive document license | Candidate Recommendation; exact localhost/loopback semantics apply. |
| [W3C Service Workers](https://www.w3.org/TR/service-workers/) | Candidate Recommendation Draft (2026-08-12), inspected 2026-09-09 | Lifecycle (`#service-worker-concept`), scope path restrictions (`#service-worker-registration-scope`), fetch interception (`#fetch-event-section`), offline cache | W3C permissive document license | Candidate Recommendation Draft; offline persistence subject to client quota and eviction. |
| [W3C File API](https://www.w3.org/TR/FileAPI/) | Working Draft (2026-08-23), inspected 2026-09-09 | Blob interface (`#blob-section`), File interface, object URL creation and explicit revocation (`#url`) | W3C permissive document license | Working Draft; object URLs require manual lifecycle revocation. |
| [W3C CSP Level 3](https://www.w3.org/TR/CSP3/) | Working Draft (2026-08-13), inspected 2026-09-09 | Directives (`script-src`, `connect-src`, `default-src`), mixed content blocking, policy enforcement | W3C permissive document license | Working Draft; browser directive support varies by release. |
| [W3C Mixed Content](https://www.w3.org/TR/mixed-content/) | Candidate Recommendation Draft (2023-02-23), inspected 2026-09-09 | Browser fetching enforcement in authenticated contexts | W3C permissive document license | Documentation boundary; not executed by this loopback matrix. |
| [HTTP cookies](https://httpwg.org/specs/rfc6265.html#s-8.5) | RFC 6265, April 2011; inspected 2026-09-09 | Domain/path rules and lack of port isolation | IETF Trust terms | Historical base protocol; modern site/partition policy requires current implementation evidence. |

## Qualification ladder and browser boundary

Distinguish declared targets, installed packages/binaries, launched engines,
created execution contexts, invoked APIs and observed predicates. Record the
actual version/user agent, platform/architecture, headless mode, context, origin
role and feature detection with each executed matrix. No engine version is
qualified merely by appearing in this specification. Unexpected failures retain
sanitized initiating class, message and cause.

Ordinary browser engines do not qualify actual Tauri or other embedded WebView
behavior. Inspect the actual host engine, schemes/origins, bridges, configuration
and API restrictions when they matter; do not assume one universal Tauri global
or protocol. A browser build/smoke result qualifies only its exercised web surface.
The default service-worker block means service-worker behavior is unqualified.

## Clause-to-scenario traceability

The maintained APG123 supervisor and its scenario register own executed
predicates; this table records intended coverage, not passing outcomes. Every
BR01 through BR14 lane must execute across Chromium, Firefox and WebKit.

| Case | Clause | Required semantic predicate | Limit beyond the predicate |
| --- | --- | --- | --- |
| BR01 | BR-01-LIFECYCLE | Window/Document identity and instrumented readyState/DCL/load | bfcache, visibility and termination delivery need separate evidence |
| BR02 | BR-02-DOM-OBSERVER | Parser/script tree distinction, mutation records and disconnect | No full HTML parser conformance or arbitrary retention proof |
| BR03 | BR-03-EVENTS | capture/target/bubble, default cancellation and listener lifetime | Synthetic events do not prove trusted user activation |
| BR04 | BR-04-SCHEDULING | Task/microtask invariants, timer cancellation and rAF completion | No timer/frame total order, exact clamp timing or paint guarantee |
| BR05 | BR-05-URL | Relative resolution and same/different-port origins | No cookie isolation or opaque-origin equivalence |
| BR06 | BR-06-CORS | Real local allow/deny/preflight/opaque controls and bounded meta-CSP containment | No external network or CSRF protection claim |
| BR07 | BR-07-FETCH | Abort, redirect and synthetic include/omit credentials | No rollback of server-side work or arbitrary cookie policy proof |
| BR08 | BR-08-STORAGE | localStorage sharing and sessionStorage page-session separation | IndexedDB, cookies, quota and persistence remain documented boundaries |
| BR09 | BR-09-HISTORY | History state and loopback Location transition | No universal navigation/bfcache promise |
| BR10 | BR-10-CUSTOM-SHADOW | Custom lifecycle, shadow and slot assignment | Closed shadow is not a security boundary |
| BR11 | BR-11-GEOMETRY | Resolved style and geometry of CSS-owned values | No cascade, accessibility, paint or performance proof |
| BR12 | BR-12-WORKERS | Startup, messages, termination and owned cleanup | No service/shared worker or zero-copy performance qualification |
| BR13 | BR-13-MODULES-RESOURCES | Local module/resource URL success and refusal | JavaScript semantics and bundler transforms retain separate owners |
| BR14 | BR-14-BLOB-REVOKE | Object URL use and refusal after revocation | No immediate deallocation or cancellation of in-flight reads |

BR-15-SECURITY-CSP has only the bounded BR06 meta-CSP/connect-src containment
control; broader CSP behavior remains unqualified. BR-16-ROUTING-BOUNDARIES is
guidance. Secure-context/service-worker, permission, mixed-content and embedded
behavior require their own executed predicates before a runtime claim.
Neighbor references are navigation coverage only. Keyword/clause checks enforce
bounded document structure; they are not semantic browser tests.

## Composition and context

The [architecture](../architecture/v0-10-browser-runtime.md) and versioned APG125
composition fixture own exact explicit sets, exclusions and narrower controls.
Measured description/body/support/materialized bytes remain distinct from
provider overhead, tokens and context fit. No capability alias silently selects
the new leaf, and no adjacent owner is loaded merely because it is mentioned.

## Correction, rollback and completion

Coherent rollback removes the current leaf, catalog, projection, policy admission,
metadata and focused tests while preserving phase/provenance history. No
qualification is claimed before real browser, composition and integration evidence
is recorded. Final review and verification remain dispatcher-owned.
