# APG94 v0.7 Embeddable Toolkit Architecture Exit

Phase ID: `APG94`

## Status

**Complete candidate — v0.7 architecture frozen for separately authorized
APG95 implementation.**

Terminal disposition: `V07_ARCHITECTURE_FROZEN_READY_FOR_APG95`.

Dispatcher-owned commit and publication remain outside provider work.

## Decisions

1. APG v0.7 is library-first Go. JACA imports APG public packages directly and
   does not invoke `apgr` or a shell. APG remains stateless, provider-neutral,
   and acyclic with JACA.
2. The future root module is
   `github.com/Knowledge-Forge-AI/agentic-praxis-grimoire`, with Go 1.25,
   `schema`, `report`, `skills`, `envsnap`, `hotspot`, `cmd/apgr`, and private
   `internal/` implementation owners. APG94 adds no module or Go source.
3. Initial native Git execution uses fixed exact argv and
   `exec.CommandContext`; shell-free JACA integration does not require a
   process-free Git implementation.
4. APG95 preserves common envelope v1, Git-show v2, Git-diff v1, and
   operational v1 through Python/Go differential parity. Collection,
   normalized model, rendering/parsing, and optional publication are separate;
   JACA can consume records and bytes in memory.
5. The CLI strangler matrix assigns migrated portable behavior to one Go owner
   and classifies retained repository/host maintenance Python explicitly.
6. One editable version binds the Go tag/binary, Python, npm, Nix handoff,
   embedded resources, and checksums. Python uses binary-containing supported-
   target wheels; the npm launcher is `@knowledge-forge-ai/apgr` with three
   same-version platform packages. There is no runtime download or FFI.
7. The structured, model-free skill resolver preserves explicit selection,
   deterministic reasons and composition, fail-closed byte budgets, and an
   isolated agent-scoped discovery root. Canonical Markdown remains the sole
   source and is embedded directly.
8. The global 9,527-byte ceiling is unchanged. Corpus and selected-bundle
   footprints are separate measurements.
9. Portable environment v1 uses typed profiles, canonical JSON, fingerprints,
   no-churn owner-only storage, staleness, explicit precedence, in-process
   resolution, and a non-secret boundary. `.flakes` remains authority until
   APG98 parity and separately authorized cutover.
10. Hotspot v1 uses stable JSON, deterministic human renderings, an honest
    capability/confidence matrix, explicit unavailable values, and relative
    ranking. Growth/churn is deferred beyond v0.7.
11. APG101 owns the human README/documentation restructure and historical
    preservation. APG94 does not rewrite the README.
12. APG94 through APG103 is frozen with separate APG102 readiness and APG103
    publication phases.

## Source and verification basis

The architecture was reconstructed from current APG Python CLI/report/resource
owners, committed current JACA Go module/evidence/Git/context owners, and current
`.flakes` allowlist/snapshot/run/hook/test owners. Volatile external Git and
working-state identities are retained in publication-excluded evidence rather
than made public compatibility prerequisites.

Focused APG verification checks record identities, skill topology, context
readback, relevant narrative contracts, Markdown links, and diff whitespace.
The pre-final dispatcher checkpoint owns final acceptance; no provider-selected
reviewer is used.

## Preserved state

- Version remains 0.6.0.
- Skills remain 39 canonical / 39 catalog / 39 projections.
- Maturity remains 14 stable / 25 provisional.
- Discovery remains 39 with zero malformed, 9,504 UTF-8 description bytes, and
  9,492 characters.
- `CSS-QD-001..005` and `JS-QD-001..005` are unchanged.
- No Go, dependency, schema implementation, skill, analyzer, environment
  implementation, distribution, publication, deployment, JACA, `.flakes`, or
  Nix change occurred.

## Next authorization

APG95 is the frozen next phase: the Go reporting library vertical slice with
Python parity and a JACA-importable API. This exit does not authorize it.
