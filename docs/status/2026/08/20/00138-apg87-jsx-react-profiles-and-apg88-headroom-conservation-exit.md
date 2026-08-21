# APG87 JSX and React Profiles with APG88 Headroom Conservation Exit

Phase ID: `APG87`

## Status

The candidate accepts ADR 0049 with amendment and provisionally integrates
exactly `jsx-language-profile` and `react-component-profile`. The candidate
disposition is `JSX_REACT_PROVISIONALLY_INTEGRATED`; dispatcher-owned pre-final
review remains an external gate and is not self-attested by this record.

## Result

1. JSX has one library-independent syntax and transform owner without absorbing
   React, TypeScript, JavaScript, Node, build tooling, MDX, or Astro.
2. React has one host-independent component and render owner without absorbing
   JSX, language semantics, Vitest mechanics, test sufficiency, routing,
   styling, accessibility, MDX, Astro, or metaframework behavior.
3. The fixed composition order, direct independent selection, and absent-owner
   stop are preserved. No profile silently invokes another.
4. The reviewed conservation disposition uses 516 APG87 description bytes and
   retains 475 bytes for APG88 rather than spending the 651-byte maximum.
5. The APG86 generic checker is unchanged and remains topology-agnostic.
6. Catalog rows, exact projections, capability routes, packaged metadata,
   project and current-development release inventories, boundary fixtures,
   focused tests, and current documentation are integrated together.

## Resulting state

- topology: 37 canonical / 37 catalog / 37 projections;
- discovery: 37 measured / 37 discoverable / zero malformed;
- maturity: 14 stable / 23 provisional;
- JSX description: 248 UTF-8 bytes;
- React description: 268 UTF-8 bytes;
- APG87 pair: 516 bytes;
- total description bytes: 9,052;
- full-v0.6 delta from 7,967: 1,085 bytes; and
- remaining headroom under 9,527: 475 bytes.

## Verification

Focused profile and boundary tests demonstrate the intended delta from the
absent baseline and pass in the candidate state. The candidate handoff records
the exact configured unit, integration, combined, skill-library, resource-sync,
record-identity, context, change-size, whitespace, scope, and worktree evidence
actually observed before commit. Final mechanical verification and APGR
terminal artifacts remain later lifecycle work.

## Limitations and stop

APG87 adds reusable guidance and APG-owned falsification fixtures only. It runs
no target JSX transformer or React renderer, adds no dependency or lockfile,
changes no version or publication identity, and supplies no advisory discovery
surface.

No MDX/Astro implementation, APG88, publication, deployment, target mutation,
remote push, or successor work ran. The local APG87 commit is authorized; no
push is authorized.
