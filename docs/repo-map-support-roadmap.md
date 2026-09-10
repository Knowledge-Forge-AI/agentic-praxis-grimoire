# Repo Map support roadmap

This documentation covers v0.10.0.

## Support principles and ownership

This roadmap ships with the APGR v0.10.0 documentation. It replaces
the earlier v0.11 assignment with product milestones RM-S0 through RM-S5.
Milestones are gates for separately authorized work, not promises of a release
date, automatic skill authoring or consumer adoption. Preceding releases
v0.9.0 and v0.8.1 remain frozen.

APGR owns reusable engineering guidance, skill lifecycle and discovery capacity,
and deterministic library/CLI primitives. Repo Map owns indexing, extraction,
graph identity and provenance, storage, query/protocol contracts, migrations
and product qualification. JACA owns its orchestration, runner registration and
adoption decisions. Each project retains its own mutation and release authority.

Read-only source observations can identify a candidate contract; they do not
establish hosted execution, graph quality or production readiness. Current Repo
Map evidence includes an ongoing qualification campaign with hosted gates still
deferred. Local checks cannot substitute for those gates.

## v0.10 reusable support baseline

The 45-leaf corpus already provides useful support through existing owners:

- Python and Go language/runtime guidance and their selected test profiles;
  JavaScript, TypeScript, Bash and related language owners where applicable.
- PostgreSQL and SQLite profiles for database-specific judgment, composed with
  planning, bounded implementation, debugging, verification and test strategy.
- Six provisional visual-web/toolchain profiles: SVG, Playwright Test, web
  accessibility, Vite, npm and browser runtime, when a task actually uses them.
- Public Go packages for canonical reports, skill selection, environment
  snapshots, structural hotspot analysis and context-footprint accounting.
  Footprint units and evidence quality remain explicit; bytes are not tokens.
- Repository qualification through `bin/apg-test` or `apgr test`, including
  `--summary-file`. The command is `unit-integration`; its receipt suite is
  `combined`. Bare native/npm packages do not contain the repository test runner.

These are reusable APGR capabilities, not a claim that Repo Map has integrated
them. Profile maturity remains 14 stable and 31 provisional. See the
[skill catalog](../skills/README.md), [Go reference](reference/go-library.md)
and [v0.10 notes](../release/v0.10.0-notes.md).

## RM-S0 — Contract watch and disposable consumer fixtures

Entry requires a named consumer need and a source-bound contract inventory.
Observe Repo Map's published main and explicitly selected candidate contracts
read-only, recording their different maturity and qualification status. Recheck
snapshot, extraction-receipt, publication-bundle and protocol assumptions when
their owners change; monitoring grants no automatic action authority.

Build separately authorized, disposable APGR consumer fixtures from public-safe
synthetic inputs. Exercise accepted and rejected versions, incomplete evidence,
identity drift, cancellation and caller-owned error boundaries where relevant.
Fixtures must disclose mocks and omitted live boundaries. They must not read
private graph content or mutate a consumer checkout, service or database.

Exit requires reproducible contract evidence, explicit unsupported cases and an
owner for refresh. A local fixture pass is APGR compatibility evidence only.

## RM-S1 — Versioned-protocol guidance gate

Before considering `versioned-protocol-profile`, require a stabilized,
consumer-qualified contract and a demonstrated gap in existing language,
serialization, testing and architecture guidance. Separate semantic identity
from wire versions, framing, compatibility negotiation and error envelopes.

Freeze positive and refusal scenarios for version mismatch, unknown fields,
partial messages, malformed payloads and compatibility claims. Record which
properties are guaranteed by the protocol owner and which remain unqualified.
Exit is a reviewed retain/defer/reject decision on reusable guidance. A new
provisional leaf requires separate authoring authority, provenance, independent
semantic validation and the post-v0.10 admission gate below; this roadmap does
not require or authorize one.

## RM-S2 — Knowledge-graph-quality guidance gate

Before considering `knowledge-graph-quality-profile`, require empirical,
source-bound extraction and multi-source evidence. Distinguish canonical entity
identity, deduplication, relationship direction, provenance, claim strength,
conflict resolution and materialization behavior from database implementation.
Cycles are not inherently defects; validity follows the graph's declared model.

Use synthetic graphs with known expected outcomes and independently supported
consumer examples. Measure missing and spurious claims, identity drift and
provenance loss without generalizing a bounded corpus to all repositories.
Exit requires a reusable ownership gap and reviewed scenarios, limitations and
rollback. Skill authoring and graph-quality product acceptance remain separate.

## RM-S3 — Local/hosted storage and migration composition

Use existing owners first: PostgreSQL or SQLite for storage semantics; Python
or Go for runtime changes; planning, design, implementation, debugging and
verification skills for bounded migration work. Use Bash-to-Python conversion
only when that specific conversion is the task.

Require explicit data ownership, schema/version compatibility, backup and
restore evidence, cutover criteria, rollback, failure recovery and local versus
hosted execution boundaries. Hosted topology and production data remain
Repo Map-owned. No disposable local test proves production migration safety.

Exit is a tested composition and gap analysis. Propose specialized migration
guidance only if existing owners demonstrably omit a reusable contract; neither
a migration leaf nor a production migration is authorized here.

## RM-S4 — APGR/Repo Map/JACA integration seams

Keep three independently accepted boundaries:

- APGR exposes deterministic library results and repository qualification
  summaries; callers own adapters, context propagation and error handling.
- Repo Map exposes its graph/protocol evidence and owns storage and extraction
  qualification. JACA runner registration is separately consumer-owned.
- JACA owns orchestration, scheduling, authorization, retries and workflow
  disposition. APGR results do not grant those powers or prove adoption.

Exit requires version-bound adapter fixtures, explicit unavailable evidence,
refusal/cancellation cases and consumer-owned acceptance for every live seam.
Use the existing [APG–JACA boundary](architecture/apg-jaca-integration.md),
[CI handoff](architecture/jaca-ci-handoff.md) and
[XO handoff](architecture/jaca-xo-handoff.md). No automatic runtime dependency
between these projects is introduced by this roadmap.

## RM-S5 — Ongoing compatibility and versioning

Maintain a compatibility matrix binding released APGR versions, selected Repo
Map contracts, fixture identities and qualified environments. Distinguish
published support from candidate-only evidence and recorded deferrals.

Each material contract change needs a scoped impact assessment, versioned
fixtures, negative cases and a refresh decision. Use each owner's adopted
versioning and deprecation policy; this roadmap creates no blanket guarantee
of compatibility across future minor releases. Retire support explicitly with
consumer notification and migration guidance where required by those policies.
Exit requires maintained owners and reproducible receipts, not a one-time pass.

## Post-v0.10 discovery-capacity requirement

[ADR 0053](adr/2026/09/0053-v0-10-discovery-capacity-and-svg.md) owns the current
capacity policy. All six named reservations are admitted: 45 leaves, 11,142
UTF-8 description bytes under an 11,507-byte ceiling. The historical 9,527-byte
control remains preserved. The remaining 365 bytes authorize no new leaf.

Any future protocol, graph-quality or migration leaf needs an explicit new
capacity and selection decision before authoring/integration. That decision
must justify discovery cost, existing-owner overlap, provenance, admission
identity and measurable headroom under a versioned policy. Existing descriptions
cannot be silently compressed or their frozen ownership changed to fit a leaf.
The present six 330-byte reservations are not allocations for future candidates.

## Explicit non-claims

This roadmap does not qualify hosted Repo Map, certify extracted graph quality,
execute or approve production migrations, or establish JACA adoption. It does
not implement a protocol, graph-quality or migration skill and does not modify
Repo Map or JACA. Future support work requires separate authorization.
