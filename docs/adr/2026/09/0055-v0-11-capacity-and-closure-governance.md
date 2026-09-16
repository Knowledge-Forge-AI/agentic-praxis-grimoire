# ADR 0055: v0.11 Capacity and Closure Governance

## Status

Accepted — APG143 manager disposition, 2026-09-12.

The original APG138 proposal implemented this conservative decision within the
authorized foundation and awaited acceptance. The later APG143 manager
disposition explicitly accepts its conservative substance; this is not an
inference from APG138 authoring, worker evidence or an earlier reviewer.
The APG138 measurements and selection observations below remain historical.

## Decision date

2026-09-12

## Context

APG138 initiates Stage V0110-A foundation of the v0.11 Roadmap Closure Program
following public v0.10.0 publication. The maintained context report observes
exactly 45 canonical leaves, 45 catalog rows in `skills/README.md`, and 45
projections, comprising 14 stable and 31 provisional skills.

Historical ADR 0053 is immutable evidence that documented the phased discovery
capacity expansion across v0.10 development:
1. The historical 39-leaf baseline (9,504 description bytes, 9,492 characters,
   9,527-byte integrity allowance, SHA-256 digest `f9255d38eadff7b2bfc5ab13cd1722b8d98ac1ea974d8220475ff7067a1e8cc7`).
2. APG122 foundation admission of `svg-language-profile` (40 leaves, 9,857-byte
   ceiling).
3. APG123 browser-ui admission of `playwright-test-profile` and
   `web-accessibility-profile` under `v0.10-browser-ui` (42 leaves, 10,517-byte
   ceiling).
4. APG124 toolchain admission of `vite-build-profile` and
   `npm-package-manager-profile` under `v0.10-toolchain` (44 leaves, 11,177-byte
   ceiling).
5. APG125 final admission of `browser-runtime-profile` under
   `v0.10-browser-runtime` (45 leaves, 11,507-byte ceiling).

Remeasurement under APG138 with maintained tooling (`apgr skills context-report`)
confirms:
- Total description UTF-8 bytes: 11,142 bytes.
- Total description UTF-8 characters: 11,126 characters.
- Effective discovery ceiling: 11,507 bytes.
- Spare headroom: 365 bytes (11,507 - 11,142).
- Full canonical content (`SKILL.md` bodies) separately totals 562,538 UTF-8
  bytes (561,448 characters across 9,840 lines).
- Historical 39 original skills remain byte-identical (9,504 description bytes).
- Six admitted candidate profiles occupy 1,638 description bytes, each <= 330
  UTF-8 bytes.

## Alternatives

| Alternative | Cost and disposition |
| --- | --- |
| Description compression across 45 skills | Reclaiming description bytes would require modifying descriptions across established skills, causing churn and risking semantic discovery drift. With 365 bytes of spare headroom and zero candidate additions in the APG138 foundation, description compression is deferred. The compression trigger is `false`. |
| New Go/Python mechanical policy version `v0.11` | Introducing a new policy string constant and selector schema version would require code changes to `skills/discovery_policy.go`, `testing/apg-discovery-policy.json`, and `libexec/apg_skill_library_check.py` without changing the effective ceiling (11,507) or admitted count (45). Rejected to avoid unnecessary API churn. |
| Versioned governance identity reusing enforcement identity | Establish `v0.11` as the formal governance decision identity while retaining `v0.10-browser-runtime` as the mechanical enforcement identity in Go and Python without code changes. Selected for APG138. |

## Decision

1. **Governance Identity `v0.11`**: APG138 establishes the `v0.11` capacity and
   closure governance decision for the v0.11 Roadmap Closure Program.
2. **Reused Enforcement Identity**: Mechanical discovery policy enforcement
   reuses the existing `v0.10-browser-runtime` identity and constant bindings in
   Go (`skills/discovery_policy.go`) and Python
   (`testing/apg-discovery-policy.json`, `libexec/apg_skill_library_check.py`)
   without code changes. This avoids API version churn while preserving strict
   fail-closed validation against unadmitted leaves.
3. **Effective Ceiling and Admitted Count**: The effective description ceiling
   remains 11,507 UTF-8 bytes. The admitted inventory remains exactly 45 leaves
   (14 stable, 31 provisional). All 45 skill descriptions are unchanged in APG138;
   any future description change remains subject to ordinary semantic qualification.
4. **Compression Trigger**: The compression trigger is `false` (untriggered).
   Measured headroom is 365 spare bytes; all candidate descriptions remain
   bounded (<= 330 bytes). No description compression is required or executed.
5. **Closed Inventory and Future Decisions**: Zero new skills are admitted in
   the v0.11 foundation. The 31 provisional leaves are subject to individual
   terminal lifecycle review in Stage V0110-B. Any future leaf candidate
   requires a separate versioned governance decision.
6. **Provider Overhead Limitation**: APG measures deterministic UTF-8 bytes
   and characters, never provider tokens. Live model runtime token counts and
   context overhead are outside the deterministic APG measurement boundary and
   are explicitly recorded as `unavailable`. Context-footprint observations
   exclude `provider_prompt_overhead`, `provider_total_context`, and
   `provider_context_fit`, with tokenizer recorded as `not_applicable`. Fixed
   caller prompt overhead may be supplied as a byte parameter without claiming
   provider token equivalence.
7. **Historical Invariant**: Historical ADR 0053 is immutable. Reusing the
   `v0.10-browser-runtime` enforcement identity satisfies the current closure
   governance requirements without silently rewriting historical release
   policies.

## Selection, materialization, and verification evidence

Maintained tooling (`apgr skills resolve`, `apgr skills materialize`, and the
Go `skills` / `footprint` packages) provides reproducible verification:

- **Supported Consumer Kinds**: Validated across all four supported consumer
  kinds: `go_library`, `codex`, `claude`, and `chatgpt`.
- **Representative Selections**:
  - `go_library`: Go development profile (`go-cmp-test-profile`,
    `go-language-profile`, `go-test-profile`), measuring 831 description bytes,
    50,231 body bytes, and 51,303 materialized disk bytes.
  - `codex`: Python test profile (`implementing-with-test-discipline`,
    `pytest-test-profile`, `python-language-profile`), measuring 612 description
    bytes, 38,513 body bytes, and 39,672 materialized disk bytes.
  - `claude`: TypeScript React component profile (`react-component-profile`,
    `typescript-language-profile`, `vitest-test-profile`), measuring 812
    description bytes, 34,090 body bytes, and 35,226 materialized disk bytes.
  - `chatgpt`: Manager workflow profile (`chatgpt-manager-workflow`,
    `composing-approved-roadmap-assignments`), measuring 387 description bytes,
    12,590 body bytes, and 13,532 materialized disk bytes.
- **Isolated Materialization**: All filesystem materializations produce owner-only
  0700 directories containing single-link, non-symlink 0600 regular files and
  canonical `manifest.json`, byte-identical to embedded source bytes.
- **Selection Positives**: Structured facts across capability, language,
  repository characteristic, runtime, test framework, work class, and explicit
  IDs resolve deterministically to exact single or composite skill sets.
- **Selection Nontriggers**: Closed-vocabulary accepted values (`accessibility`,
  `rust`, `browser`, `jest`, `research`) return zero selected skills with
  `no_unique_owner` exclusions.
- **Unsupported Combinations**: Invalid structured identifiers (such as
  `languages: ["svg"]`), unknown explicit IDs, provider-specific consumer
  mismatches (such as ChatGPT manager skills requested by Codex), invalid
  materialization forms, and budget overages fail closed with distinct errors.

## Authority and evidence records

This ADR governs v0.11 capacity and closure boundaries. Source-bound compact
verification receipts retain the measurement inputs and output identities in
publication-excluded evidence. Public interpretation relies on the measurements
and limitations recorded here. This decision grants no successor phase or
release authority; Git publication remains dispatcher-owned.

## APG143 acceptance and current measurement

On 2026-09-12 the manager accepted governance identity `v0.11`, retained
`v0.10-browser-runtime` enforcement, 45 admitted leaves and the 11,507-byte
description ceiling. No new admission or compression is authorized.

Fresh maintained `apgr skills context-report --json` reports 45 discoverable
skills, 11,142 description UTF-8 bytes and 11,126 characters, leaving 365 bytes
of headroom. The maintained skill-library check with explicit policy
`v0.10-browser-runtime` passes with 45 canonical skills, 45 catalog rows and
45 projections. Provider token/context overhead remains unavailable. The
14 stable / 31 provisional dispositions and active debt consequences remain
unchanged. Historical selection/materialization observations above are not
represented as freshly rerun APG143 qualification. Acceptance of this capacity
policy does not establish integrated readiness or authorize release.
