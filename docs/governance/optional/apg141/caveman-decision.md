# APG141 Caveman adapter decision

Outcome: **REJECTED** for `APGR-CXT2B`, after supplied independent review. No adapter, dependency or capture runner is added.

## Dated authoritative inspection

Observation `APG141-CAVEMAN-SUBAGENT-TAX-20260912` inspected upstream
[Caveman subagent-tax](https://github.com/JuliusBrussee/caveman/tree/main/packages/subagent-tax)
on 2026-09-12, at one resolved immutable revision retained in the private
reproducibility binding. The public locator is mutable; the observation is dated,
not a claim that a branch name is immutable. Package metadata declares 0.1.0.
Selected emitter, analyzer, token accounting, example report and license files
were retrieved successfully. Source-access failures from planning are historical.

The diagnostic report contains `tool`, `tool_version`, `date`, `basis`,
`platform`, `prompt`, `calibration`, `repeat`, `honesty` and `rows`. Row data
includes harness, variant, version, status, primary request statistics and
estimated or exact token accounting. This is a version-labelled format; this
phase does not infer instability merely from its early version number.

[The licensing inventory](https://github.com/JuliusBrussee/caveman/blob/main/LICENSING.md)
explicitly classifies `packages/subagent-tax/` as MIT, and the root MIT license
requires retention of its copyright and permission notice for copies or
substantial portions. Other engine-linked directories have separate terms.
This decision copies no third-party implementation or substantial prose;
no rights failure is asserted and no core engine reuse is proposed.

## Units and useful mapping

The inspected analyzer uses JavaScript serialized-string lengths for
`total_chars`, `system_chars`, `messages_chars` and tool-schema character
counts: these are UTF-16 code units, not UTF-8 octets or Unicode scalar counts.
`body_bytes` records raw request bytes, whereas the analyzed body is scrubbed;
they are different observations. An adapter cannot reconstruct exact UTF-8 or
Unicode-scalar counts from these lengths alone.

Token accounting distinguishes `basis: est`, using rounded character count
with a default 6.4 ratio, from `basis: exact` obtained through an optional
Anthropic count endpoint. Estimated cross-provider counts cannot be relabelled
as tokenizer-specific exact values. APGR's [closed units](../../../../footprint/types.go)
contain no estimated-token unit, and modeled-estimate observation metadata does
not create one. Unmeasurable rows and null MCP attribution are not zero.

A deliberately narrow import of raw byte counts could be represented as
imported telemetry with explicit component and observation provenance. It
would still need a consumer-defined measurement boundary and cannot be assumed
to represent all prompt overhead. The current inherited record and inspected
APGR footprint/XO consumer contracts identify no concrete use of that mapping.
This is absence of demonstrated value in the inspected scope, not a claim to
have surveyed every external consumer or disproved future demand.

## Decision and existing behavior

Reject the inherited optional adapter because no current useful consumer
mapping has been established. Supporting a partial diagnostic import now would
add a format and unit-maintenance obligation without a demonstrated workflow.
Existing native footprint measurement and explicit canonical imported telemetry
remain sufficient for the established APGR byte/character measurement and
comparison requirements. No provider tokens are inferred from those measures.

A materially different future consumer may request a separately reviewed,
optional, version-pinned adapter with explicit units, provenance, unknown-field
refusal and loss disclosure. It belongs on a new roadmap. No runtime tool,
provider endpoint, harness capture, installation or upstream tests ran here.
Rollback is unnecessary because the existing footprint API is unchanged.
