# ADR 0050: MDX and Astro Profiles Complete the v0.6 Authoring Set

## Status

Accepted with amendment

## Decision date

2026-08-20

## Context

ADR 0047 freezes `mdx-profile` and `astro-profile` as the final v0.6 authoring
pair. MDX owns the document/component seam; Astro owns framework, project,
content, route, island, and execution placement. APG87 leaves exactly 475 bytes
under the 9,527-byte aggregate ceiling.

Post-planning review identified four integration obligations: every live
topology assertion must move coherently to 39; Markdown's abstract `mdx-owner`
route must become the canonical `mdx-profile`; the descriptions should avoid
asymmetric floor pressure; and `AGENTS.md` must be an explicit current-state
surface. These are implementation corrections, not architecture changes.

## Decision

1. Provisionally integrate `mdx-profile` for the Markdown-to-JSX/component
   seam, MDX ESM, expressions, provider mapping, and MDX-specific
   compile-versus-runtime distinctions.
2. Keep pure Markdown, JSX syntax, React component behavior, TypeScript
   checking, general JavaScript evaluation, and Astro framework concerns with
   their exact independent owners.
3. Provisionally integrate `astro-profile` for `.astro` structure,
   frontmatter/template execution, islands and client directives,
   server/client placement, content collections, routes, project conventions,
   and Astro integration configuration.
4. Keep React, JSX, MDX, TypeScript, generic Node, Vite, Starlight, styling,
   accessibility, hosting, and deployment outside Astro's authority.
5. Preserve the fixed document-to-mock-library composition order, direct
   independent selection, and non-expansion of existing explicit subsets.
6. Use 214 UTF-8 description bytes for MDX and 238 for Astro: 452 combined,
   9,504 total, and 23 bytes remaining under 9,527.
7. Keep `libexec/apg_skill_library_check.py` unchanged. APG039 and APG040
   remain relational and topology-agnostic; APG88 totals belong to focused
   tests and phase evidence.
8. Integrate both canonical leaves, catalog rows, exact relative projections,
   capability routes, generated metadata, current-development inventories,
   boundary fixtures, tests, and phase records as one local change.
9. Do not begin APG89, advance a version, add a dependency or lockfile change,
   publish a release, deploy, mutate active projections, add advisory
   discovery, stage, commit, or push in provider work.

## Alternatives considered

- Retain `mdx-owner` as an abstract Markdown route: rejected because the exact
  canonical leaf now exists and the placeholder would silently misroute work.
- Spend all 475 bytes: rejected because the 214/238 descriptions express the
  positive and adjacent non-trigger boundaries while preserving 23 bytes.
- Give MDX the smaller floor-adjacent description: rejected in favor of a
  near-parity split that reflects its dense document/component seam.
- Encode 39 or APG88 arithmetic in the generic checker: rejected because ADR
  0047 requires topology-agnostic APG039/APG040 enforcement.

## Consequences

Development becomes 39 canonical skills, 39 catalog rows, 39 exact relative
projections, and 39 discoverable metadata rows, with 14 stable and 25
provisional skills and zero malformed metadata. All six frozen v0.6 profiles
are authored and provisionally integrated, but this is not APG89 dogfood,
readiness, version advancement, release publication, or deployment.

The descriptions consume 452 of APG88's 475 available bytes and leave 23 bytes
under the full-v0.6 ceiling. Historical public and active v0.5.0 remain
unchanged. Dispatcher-owned review, Git publication, upstream verification, and
run archival remain external lifecycle work.
