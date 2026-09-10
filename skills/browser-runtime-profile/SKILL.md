---
name: browser-runtime-profile
description: Use when web decisions depend on browser host behavior — Window, Document, DOM mutation, event phases, tasks, microtasks, timers, rAF, MutationObserver, URL, History, Fetch, CORS, cookies, WebStorage, IndexedDB, custom elements, Shadow DOM, geometry, workers, or object URLs — for an established browser execution role.
---

# Browser Runtime Profile

Normative detail: [Browser Runtime Profile](../../docs/specs/browser-runtime-profile.md).
Status: Retained provisional after APG126 qualification.
Lifecycle: `provisionally-integrated`.
Lifecycle ADR: `Accepted with amendment`.

## Core principle

Use this profile when a material question depends on a browser host contract.
Establish the actual engine/version, platform, execution context and origin for
that claim. Distinguish Window/Document, iframe and worker globals. Capture the
user agent as evidence; use feature detection and executed compatibility cases
instead of selecting behavior from UA strings. Missing facts narrow a claim;
they do not prevent read-only investigation to obtain those facts.

## Do not use

Route ECMAScript and Promise/module live-binding semantics to
`javascript-language-profile`; typing to `typescript-language-profile`; CSS
cascade/value semantics to `css-language-profile`; SVG authoring to
`svg-language-profile`; components to `react-component-profile`; JSX syntax to
`jsx-language-profile`; runner mechanics to `playwright-test-profile`;
accessible semantics and conformance hierarchy to `web-accessibility-profile`;
build/dev tooling to `vite-build-profile`; selected npm package management to
`npm-package-manager-profile`; and Node process/runtime behavior to
`nodejs-runtime-profile`. HTML authoring outside host/runtime behavior remains
unallocated. Select simultaneous owners only when their semantics matter.
Do not infer actual Tauri WebView behavior from ordinary browser tests.

## Procedure

1. Identify the concrete host question, artifact, browser/context facts and
   authorized verification boundary. Separate standards, declarations and
   executed evidence; a package installation proves no browser behavior.
2. Apply the relevant clauses below and identify the smallest observable
   predicate with a meaningful failure/control case. Keep engine differences
   visible rather than weakening predicates to obtain a pass.
3. Establish resource lifetimes and cleanup before listeners, timers, workers,
   observers, requests, object URLs or storage are created.
4. Verify with synthetic local data and actual selected hosts where authorized.
   Preserve sanitized initiating error class, message and cause on failure.
5. Report observations, routing, unresolved facts and unqualified surfaces.
   Apply proportional project checks; no automatic adjacent profile loading.

### Host runtime contracts

**BR-01-LIFECYCLE.** Identify Window, its active Document and relevant Node/Element
realm. Inspect `readyState` before installing readiness listeners to avoid
missing an event. `DOMContentLoaded` follows parsing and deferred/module script
processing, not every async script or resource. `load` waits for load-delaying
resources, not all later or lazy work. Treat `visibilitychange`, `pageshow` and
`pagehide` (including `persisted`) as separate signals; background termination
may omit events. Do not infer bfcache restoration or user-visible rendering from
ordinary startup alone.

**BR-02-DOM-OBSERVER.** Distinguish parsing-created DOM (including parser repair)
from script-created nodes and mutations. A Document is not interchangeable with
an Element or detached fragment; inspect ownership/connectivity and namespaces.
DOM mutation is synchronous, while `MutationObserver` delivers queued records
at microtask checkpoints. Select the observed node, mutation types and subtree
scope. Use `takeRecords()` if pending records must be retained before
`disconnect()`; disconnect discards pending records. Remove owned nodes and
references at the end of their lifetime. Observation is not mandatory for every
DOM operation and does not establish painted pixels.

**BR-03-EVENTS.** Distinguish capture phase, target phase and bubbling phase;
not every event bubbles or crosses a shadow boundary. Inspect `bubbles`,
`composed`, retargeting and `composedPath()` when material. `preventDefault()`
cancels an eligible default action only for cancelable events outside passive
listeners. `stopPropagation()` affects further propagation, not default actions;
`stopImmediatePropagation()` also stops remaining listeners on the current
invocation target. Synthetic dispatch is not trusted user activation. Establish
`capture`, `once`, `passive` and `signal` options, and remove listeners using the
same type/callback/capture identity or abort the owning signal.

**BR-04-SCHEDULING.** Reason about host task sources, microtask checkpoints and
rendering opportunities without inventing one total timer/frame order. A
`queueMicrotask` scheduled in a task runs at a checkpoint before the next task;
Promise evaluation belongs to JavaScript. `requestAnimationFrame` schedules
work at a rendering opportunity, not a guarantee of paint or a fixed frame
rate. Hidden/background contexts can throttle or suspend work. Timer delay is
a minimum scheduling input, not an exact deadline; HTML clamps short timers
when timer nesting level exceeds five. Use `clearTimeout`, `clearInterval` and
`cancelAnimationFrame` for owned work. Bound microtask chains to avoid starvation.

**BR-05-URL.** Use `new URL(input, base)` and `URLSearchParams`, keeping parse
failure separate from navigation authorization. Document-relative URLs use the
relevant base (including `baseURI`); worker and module bases differ. Compare
normalized URL origins for ordinary HTTP(S) scheme/host/port tuples; opaque
origins may serialize to the same `null` string without being same-origin.
Different loopback ports are cross-origin, not distinct cookie hosts. Avoid
string-prefix origin/security checks.

**BR-06-CORS.** CORS controls browser access to cross-origin responses; a denied
read does not prove that no request or server-side effect occurred. Inspect
safelisted methods/headers, preflight and actual response authorization, including
credentialed explicit origins and exposed headers. Use local server observations
for preflight success/refusal rather than relying only on interception events.
A cross-origin `no-cors` request can yield an opaque filtered response with
status 0 and inaccessible headers/body; same-origin `no-cors` is not necessarily
opaque. Distinguish CORS/network errors from readable HTTP error responses.

**BR-07-FETCH.** Set credentials (`omit`, `same-origin`, `include`), redirects
(`follow`, `error`, `manual`) and cancellation deliberately. Credential inclusion
still depends on cookie attributes, site/privacy policy and server permission;
CORS is not CSRF protection. Abort with an owned AbortSignal and preserve its
reason: default `abort()` uses AbortError, while custom reasons can differ.
Aborting cannot undo completed server work; after headers resolve, body reads
can still fail. HTTP error status ordinarily resolves a Response; inspect `ok`.
Consume or cancel response streams and release readers as appropriate. Manual
redirect filtering is separate from ordinary opaque responses.

**BR-08-STORAGE.** Web Storage is synchronous: `localStorage` shares an origin
storage area; `sessionStorage` additionally separates top-level page sessions
(with opener-copy behavior where applicable). Cookies use domain/host, path,
security and site rules, not port-isolated origin scoping. `HttpOnly` is set by
the server and excludes script reads; assess Secure and SameSite independently.
IndexedDB provides asynchronous transactions; CacheStorage holds request/response
pairs and is not the HTTP cache. Quotas, partitioning, user clearing, private
mode and eviction vary: persistent storage is not guaranteed. Handle access and
quota failures, minimize retained data and remove task-owned entries. Never
retain real cookies, authorization headers, tokens or user project data in tests.

**BR-09-HISTORY.** `pushState`/`replaceState` update same-origin session history
without a full navigation and do not themselves fire `popstate`; traversal is
separate. Location assignment can cause document navigation or same-document
fragment navigation. Changed fragments normally fire `hashchange`; same-value
assignments and History API changes differ. Observe the committed destination,
history state and lifecycle rather than assuming a URL change means reload.
Do not trigger real user navigation for synthetic qualification.

**BR-10-CUSTOM-SHADOW.** Inspect custom-element definition/upgrade timing and
connected/disconnected/adopted/attribute callbacks for the concrete operation.
Shadow DOM and slot assignment affect tree traversal, event retargeting and
composition; slotted nodes remain in the light DOM. A closed shadow root is
not a security boundary. Observe `slotchange` when assigned-node changes matter.
Disconnect owned elements/listeners and avoid assuming every move has identical
lifecycle behavior across APIs.

**BR-11-GEOMETRY.** `getComputedStyle` exposes resolved style values;
`getBoundingClientRect` measures viewport-relative geometry. Identify viewport,
zoom, scroll, transforms, box model and CSS-owned fixture values. Layout reads
after invalidating writes can force layout; measure before declaring a
performance defect. Batch only when behavior allows. Geometry does not prove
CSS cascade semantics, accessibility, painted output or a stable frame rate.

**BR-12-WORKERS.** Identify dedicated/shared/service worker contexts separately.
A dedicated worker has no Window/Document/DOM; select classic/module loading and
resolve its script URL under browser host restrictions. Use bounded message and
error handling, structured clone or transfer ownership (no promised zero-copy
performance), and `terminate()` or `close()` with cleanup of listeners/ports.
Do not infer worker request containment from page-route interception alone.
Server allowlists and synthetic scripts define the exercised resource boundary.

**BR-13-MODULES-RESOURCES.** Browser module and resource loading depends on URL
resolution, import maps, fetch policy, MIME type, CORS and CSP. Parser-inserted
non-async module scripts have readiness behavior distinct from async or dynamic
imports. Script load success is not proof that later application work succeeded.
Observe load/error and refused resource controls. JavaScript owns module syntax,
strict-mode and live bindings; Vite owns bundling/transforms. Runtime fixtures
must not acquire external resources.

**BR-14-BLOB-REVOKE.** Object URLs keep a Blob/File resource reachable until
released or its governing environment is cleaned up. Pair `createObjectURL`
with `revokeObjectURL` once all intended consumers and user interactions have
finished, not automatically at image load or download initiation. Revocation
prevents future dereference; it does not necessarily stop an already-started
read or free every other Blob reference. Bound tests to observed release behavior.

**BR-15-SECURITY-CSP.** Detect `isSecureContext`, API availability and permission
state in the actual global. Trustworthiness includes loopback rules and ancestor
context; HTTPS spelling alone is insufficient. CSP, mixed-content enforcement,
sandboxing and Permissions Policy are separate host controls. Permissions API
`query` observes state; it does not request permission, and not every permission
name/API is supported. Permission-sensitive operations need task authority and
user activation where required. Service workers require a suitable secure host,
same-origin script/scope rules and lifecycle handling: registration, installation,
activation and control are distinct. Cache API/offline persistence needs explicit
ownership and cleanup; do not infer control from successful registration. This
leaf is not a PWA manual, and blocked service workers are unqualified evidence.

**BR-16-ROUTING-BOUNDARIES.** Ordinary browser engines do not qualify actual
Tauri or other embedded WebView behavior. Require actual embedded host/engine,
platform, origin/scheme, bridge configuration and security-policy evidence when
those facts affect a claim. Do not assume a particular Tauri global, protocol or
API exposure without inspecting that application. A browser web build qualifies
only its exercised browser surface. Preserve all adjacent ownership seams above.

## Project-owned parameters

The project owns supported browser/embedded hosts, test tooling, API policy,
origins, credentials, permissions, storage/retention limits, resource lifetimes,
performance targets, accessibility acceptance, and mutation/release authority.
No new numeric file-size or complexity policy is introduced by this profile.

## Evidence and completion

Record actual engine/version, OS/architecture, user agent, headless/headful mode,
execution context, origin role and feature detection for each material predicate.
The APG125 register requires BR01 through BR14 in three engines; only executed
receipts qualify them. Standards prose and a test-name/keyword check are not
browser evidence. Report failed and unrun cases without replacing their original
sanitized errors. Full conformance, bfcache/visibility guarantees, arbitrary
storage persistence and actual embedded WebViews remain outside those predicates.

## Stop or escalate

Stop an unsupported completion claim, unauthorized external navigation or
permission action, leaked protected data, uncontrolled resource lifetime, or
browser evidence presented as embedded-host qualification. Route adjacent
semantics without treating routing alone as a failure. Investigate missing
facts read-only when possible; seek a project decision for behavior changes or
exceptions beyond the authorized scope.

## Common mistakes

- Treating UA detection or installed engines as executed compatibility evidence.
- Treating denied CORS reads as proof no request reached the server.
- Treating cookies as port-isolated storage or persistence as guaranteed.
- Confusing cancellation, propagation, default actions and user activation.
- Revoking a resource before its final consumer has finished.
- Assuming a timer/frame ordering or browser/WebView equivalence not tested.
