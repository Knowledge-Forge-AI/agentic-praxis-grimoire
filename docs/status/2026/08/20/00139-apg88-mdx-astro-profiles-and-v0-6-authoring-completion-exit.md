# APG88 MDX and Astro Profiles Complete the v0.6 Authoring Set Exit

Phase ID: `APG88`

## Status

The candidate accepts ADR 0050 with amendment and provisionally integrates
exactly `mdx-profile` and `astro-profile`. The candidate disposition is
`MDX_ASTRO_PROVISIONALLY_INTEGRATED`; dispatcher-owned pre-final review remains
an external gate and is not self-attested.

## Result

1. MDX owns one exact document/component seam without absorbing Markdown, JSX,
   React, TypeScript, JavaScript, or Astro.
2. Astro owns one exact framework, project, content, route, island, directive,
   and execution boundary without absorbing React, JSX, MDX, TypeScript, Node,
   Vite, Starlight, styling, accessibility, hosting, or deployment.
3. The fixed composition order, direct independent selection, and exact routes
   are preserved. Existing explicit project subsets do not expand implicitly.
4. The descriptions use 452 bytes and retain 23 bytes under the 9,527 ceiling.
5. The generic checker is unchanged and remains topology-agnostic.
6. All six frozen v0.6 profiles are now authored and provisionally integrated;
   this grants no APG89 or release authority.

## Resulting state

- topology: 39 canonical / 39 catalog / 39 projections;
- discovery: 39 measured / 39 discoverable / zero malformed;
- maturity: 14 stable / 25 provisional;
- MDX description: 214 UTF-8 bytes;
- Astro description: 238 UTF-8 bytes;
- APG88 pair: 452 bytes;
- total description bytes: 9,504;
- full-v0.6 delta from 7,967: 1,537 bytes; and
- remaining headroom under 9,527: 23 bytes.

## Verification

Focused profile and boundary tests demonstrate the intended delta from the
absent baseline and pass in the candidate state. The candidate handoff records
the exact configured unit, integration, combined, skill-library, metadata,
record-identity, context, whitespace, scope, and worktree evidence actually
observed. Final dispatcher review, Git publication, upstream verification, and
terminal archive creation remain later lifecycle work.

## Limitations and stop

APG88 adds reusable guidance and APG-owned falsification fixtures only. It runs
no target MDX compiler or Astro app, adds no dependency or lockfile, changes no
version or publication identity, supplies no advisory discovery, and mutates
no active projection or deployment.

No APG89, readiness, release publication, deployment, provider staging,
commit, push, or successor work ran.
