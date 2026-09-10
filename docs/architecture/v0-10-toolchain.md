# v0.10 Toolchain architecture

APG124 implements the authorized Toolchain slice. APG123 is accepted as
`V0100_BROWSER_UI_VERIFICATION_SLICE_QUALIFIED`; its Browser/UI architecture
remains a historical slice contract. This additive document supersedes its
no-Vite/npm-admission statement for current development only.

## Ownership and composition

| Owner | Decision surface |
| --- | --- |
| SVG | Vector authoring and serialization |
| Playwright | Browser test automation and runner lifecycle |
| Web accessibility | Accessible semantics and testing hierarchy |
| Vite | Frontend build/dev tooling, configuration and asset transformation |
| npm | Selected-version package-management semantics |
| Future browser-runtime | Reserved DOM/browser/runtime semantics; absent |
| Node | Process and runtime host semantics |

CSS, JavaScript, TypeScript, JSX, React, Astro and MDX retain their existing
owners. Tailwind and shadcn/ui are consumer composition, not new profiles.
Explicit selection is unchanged; adjacent owners are not automatically loaded.

## Admission contract

`v0.10-toolchain` admits exactly the original 39 leaves plus SVG, Playwright,
web accessibility, Vite and npm: 44 canonical/catalog/projection/discoverable
leaves, 14 stable and 30 provisional. All 42 prior descriptions remain exact.
Each named candidate has at most 330 UTF-8 description bytes. The admission
ceiling is 9,527 + 5*330 = 11,177; the six-candidate reservation stays 11,507.
Unused reservation cannot transfer. Only browser-runtime remains unadmitted.
Historical policy meanings remain intact. Go code constants and Python selector
validation enforce parity without adding Go selector-file loading.

## Qualification boundary

Vite 8.2.2 and npm 12.0.2 are exact reference implementations. Acquisition and
scenario execution are separate, with dependencies confined to caller-owned
external scratch. npm requires Node ^22.22.2 || ^24.15.0 || >=26.0.0;
repository selection must be evidenced rather than inferred from a lockfile.
Vite 8 uses Rolldown. Native optional bindings and notices belong in acquisition
evidence. Installation uses `--ignore-scripts`; deliberate lifecycle fixtures
exercise scripts separately. No registry publication is authorized.

Synthetic harnesses fail closed on missing prerequisites and retain sanitized
scenario evidence. Actual output comparison is bounded to the controlled inputs,
versions and platform; it does not establish universal reproducibility.
Loopback dev/preview servers are temporary. Preview is not a production server.
The browser runner requires owned scratch and preserves initiating diagnostics
before supervisor cleanup. No real browser profile is used.

Consumer npm evidence uses a fresh disposable capture and preserves lock bytes.
The consumer has transitive Vite test-tool usage but no direct Vite application
build pipeline; synthetic Vite evidence does not qualify an existing consumer
Vite integration. No source consumer mutation is permitted.

## Disposition and rollback

The producer amends the exact bound proposal to incorporate the advisory
findings: freeze all prior descriptions, bind executing npm identity, avoid an
unneeded loopback registry, fail closed on harness prerequisites, run the private
oracle explicitly, preserve failure receipts before cleanup, preserve historical
architecture text, and retain native binding provenance. Original task scope
remains controlling. No stage deltas were supplied.

APG124 remains a pre-final candidate until dispatcher review and closeout.
Rollback removes both admissions and integration together, preserving accepted
APG123 behavior and independently valid maintenance fixes. Public v0.9.0,
consumers, adapters, host configuration, JACA, registry publication and automatic
successor dispatch remain outside this slice.
