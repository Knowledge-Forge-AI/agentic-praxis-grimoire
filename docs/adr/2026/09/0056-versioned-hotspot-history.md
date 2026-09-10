# ADR 0056: Versioned Hotspot History

## Status

Accepted with amendment after supplied independent review and APG141 terminal
verification. Terminal amendments are not independently re-reviewed.

## Decision date

2026-09-12

## Context

The inherited hotspot churn obligation requires deterministic bounded history
without changing default structural analysis. Existing v1 request decoding is
strict and report schemas/fingerprints explicitly identify v1. Adding fields
would not preserve strict consumers or canonical bytes.

## Decision

Add explicit v2 Go operations and CLI history selection while preserving v1
operations, default invocation, structural ranking and golden bytes. Reuse v1
structural analysis; keep a distinct file-level first-parent history observation.
The [history contract](../../../guides/hotspot-history.md) owns exact range,
path, unit, availability, resource, offline and compatibility rules. It adds no
function attribution or combined ranking. A local Git executable is required
only when history is explicitly requested. General reporting Git ownership and
its separate V0110-E trigger remain unchanged.

## Alternatives

- Add v1 fields: rejected because strict readers and canonical identity would
  change silently.
- Introduce a repository-history service or pure-Go reporting backend: rejected
  as unnecessary scope and runtime ownership expansion.
- Change structural ranking using absent-as-zero history: rejected because it
  changes default interpretation and rewards unavailable measurements.
- Defer churn despite a bounded local implementation: retain as fallback only
  if qualification or review cannot establish the required contract.

The inherited combined frequency/complexity score is deliberately abandoned
for this item. File-level transition frequency, churn and growth remain separate
from structural complexity: no justified weighting/availability contract warrants
a combined score. A materially different scoring request belongs on a new
roadmap. This narrowing explicitly dispositions the inherited consequence.

## Consequences, rollback and deferred decisions

Callers opt into new types and fields. Unsupported stores, incomplete history
and exhausted bounds refuse the historical request; no silent fetching occurs.
The implementation uses separate private collection, measurement and rendering
owners. Existing broad exported hotspot data types are retained for compatibility;
this phase adds one history responsibility without an opportunistic API rewrite.
Rollback uses v1 operations and omits history flags. Consumer adoption and full
release-surface/distribution qualification belong to their owners and V0110-F.
This ADR does not authorize V0110-E/F/G, public release or external mutation.
