# ADR 0001: Public Projection, Private Evidence, and Agent Reporting Boundaries

## Status

Accepted

## Date

2026-07-18

## Context

Agentic Praxis Grimoire is developed in a private working environment and may
later be released through periodic public projections with squashed history.
The APG0 foundation established useful governance, but its publishable files
also recorded working-repository identities, private source topology, private
snapshot commits, and checkout-specific report observations. Those details are
useful for internal reproducibility but are unsafe and unnecessary in a public
project surface.

Removing all exact evidence would make future maintenance harder. Publishing it
would disclose non-public projects and produce public records that depend on
inaccessible sources. APG therefore needs an explicit boundary between
publication-safe rationale and publication-excluded evidence.

The source corpus also exposed a provenance error: evidence location, source
ownership, publication eligibility, and licensing answer different questions.
Maintainer-authored material may still be private; external material may be
publicly available under a license; and neither condition selects APG's eventual
distribution license.

APG0 also treated managed Git and operational report records as a possible
manager-to-worker channel. In the actual agent environment, internal Codex
workers already return bounded results through the agent harness. Managed report
records instead serve the final handoff from the top-level Codex process to the
external authority when a phase requires them.

Finally, architecture decisions and phase exits serve different purposes. ADRs
record durable decisions and their alternatives. Exit records state what a
bounded phase actually achieved. A combined counter would couple unrelated
histories and obscure their different contracts.

## Decision

### 1. Canonical public identity

- The public project identity is `agentic-praxis-grimoire`.
- Public references to RepoMap use `repo-map`.
- Private working-repository suffixes, checkout identities, and development
  commit identities are not part of publishable artifacts.

### 2. Public projection

- Future public releases are filtered projections with squashed history.
- The tracked `private/` tree is excluded from those projections.
- Every public file must be independently understandable without excluded
  material.
- Public files must not link to or otherwise depend on publication-excluded
  paths.
- This decision establishes a publication contract; it does not create or
  publish a public repository.

### 3. Tracked private material

- The private working repository may track exact internal source repositories,
  commits, path mappings, private operational analysis, and non-public
  provenance under `private/`.
- Private evidence must retain historical and current source organization as
  separate facts rather than rewriting old observations.
- `private/` is not a dumping ground for credentials, secrets, raw report
  payloads, private runtime state, or avoidable personal information.

### 4. Two-level provenance

- Public provenance records source families, genuinely public external sources,
  applicable licenses, derivation mode, adoption status, rationale, and
  validation evidence.
- Private provenance retains exact internal repository identities, snapshots,
  paths, object mappings, and migration history.
- Useful immutable pins for genuinely public upstream sources may remain public.
- Private development and private source-repository commits may not.
- Ownership, publication eligibility, license, derivation, and adoption are
  recorded independently.

### 5. External source licensing

- The captured Superpowers material is external work under the MIT License.
- Copied or adapted Superpowers expression must preserve the applicable
  copyright and license notice.
- Maintainer-authored source material remains maintainer-owned, whether public
  intended or publication excluded.
- Source ownership and reuse permission do not establish APG's distribution
  license. APG's own license remains deferred.

### 6. Agent role boundaries

- The human maintainer retains ultimate project, roadmap, publication, license,
  and destructive-action authority. The maintainer may authorize one task or
  phase or preapprove a bounded roadmap envelope with a defined stop condition.
- ChatGPT exercises delegated planning and review authority only inside that
  human-authorized envelope. It may construct Codex prompts, review Codex
  reports, and advance bounded phases when the envelope expressly permits it.
  It may not expand the roadmap, introduce an unapproved epic, approve
  destructive work, select publication or license terms, or grant itself broader
  authority.
- The top-level Codex process executes the bounded ChatGPT assignment, manages
  internal delegation, integrates and validates the result, commits and pushes
  when authorized, and owns required final reporting.
- Internal Codex workers perform bounded research, implementation, or review and
  return findings through the agent harness. They may not expand the top-level
  Codex assignment.
- Top-level Codex may narrow an internal assignment but may not expand the
  ChatGPT assignment. ChatGPT may not expand the human-authorized envelope.
- Managed Git and operational report records flow from top-level Codex to
  ChatGPT when the phase contract requires them, and onward for human review
  when the envelope or a reserved decision requires it.
- Internal workers do not normally invoke those report commands.
- A worker result, commit, or report is evidence. It is not automatic acceptance
  or authority to continue.
- Top-level Codex disposition governs internal worker output. ChatGPT review
  governs only delegated follow-up inside the approved envelope. Neither
  replaces the human maintainer's ultimate control.

APG2 clarified this four-level chain under explicit human authority. The
clarification corrects actor boundaries without changing this ADR's accepted
publication, provenance, reporting, or record decisions.

### 7. ADR and exit records

- ADRs use `docs/adr/YYYY/MM/NNNN-<slug>.md` and an independent repository-wide
  four-digit sequence beginning at `0001`.
- Exit records use
  `docs/status/YYYY/MM/DD/NNNNN-<phase>-<slug>-exit.md` and an independent
  repository-wide five-digit sequence beginning at `00001`.
- An exit filename ends in `-exit.md`, its title contains `Exit`, and its
  disposition truthfully describes the completed, partial, blocked, rejected,
  or stopped phase.
- Assigned numbers remain stable within their own namespace.

### 8. Roadmap governance

- APG1 establishes this ADR and performs the required documentation cleanup; it
  does not implement the previously proposed manager-work-order skill.
- APG2 is a bounded roadmap-reconciliation and first-implementation proposal
  phase.
- APG2 decides whether publication validation must precede skill work and
  whether a manager-oriented assignment skill remains the best first candidate.
- APG2 may recommend exactly one bounded next phase. Its commit does not
  authorize that implementation. External disposition under the authority model
  is required before implementation begins.
- Existing later topics remain unnumbered candidate themes until a later
  authorized decision assigns them phase identities.

## Alternatives considered

### Publish the private working repository directly

Rejected. Its history and tracked evidence contain development details that are
not part of the public product contract.

### Preserve private commit identities in public provenance

Rejected. They disclose the private development lineage and do not help a public
reader resolve inaccessible evidence.

### Delete internal provenance instead of retaining it privately

Rejected. Exact evidence remains useful for reproducibility, maintenance, and
future source reconciliation when kept within the publication boundary.

### Keep exact private source project names in public research

Rejected. Generalized source families preserve relevant rationale without
publishing private topology.

### Use final report scripts for every internal Codex worker interaction

Rejected. The agent harness already owns internal result delivery. Requiring
external report artifacts would add writes and ceremony without improving the
manager's evidence.

### Maintain one combined ADR and status counter

Rejected. Decisions and exits have different lifecycles, schemas, and rates of
change; coupling them supplies no useful invariant.

### Postpone privacy cleanup until the first public release

Rejected. Publication safety is cheaper to preserve continuously than to
reconstruct after additional private evidence accumulates.

### Build a publication framework immediately

Deferred. The projection contract must stabilize before APG invests in a
validator, filter, or release system.

## Consequences

- The future public surface is safer and uses stable public identities.
- Public readers lose exact reproducibility for publication-excluded evidence;
  the private ledger retains that reproducibility for maintainers.
- Public and private provenance can drift, so later validation or projection
  tooling may be justified.
- Two-level provenance adds maintenance work but makes ownership, licensing, and
  publication status explicit.
- The roadmap requires reconciliation and reauthorization rather than automatic
  renumbering.
- Managed report tools remain unchanged; their project-key and destination
  behavior must be treated as executable details rather than public identity.
- No public repository or release is created by this decision.

## Deferred decisions

- APG's distribution license and contribution policy, resolved by
  [ADR 0005](0005-public-license-and-contribution-governance.md);
- public repository creation;
- publication tooling;
- automated publication-surface validation;
- release cadence;
- tags or generated notices for public projections; and
- selection of the first substantive skill, pending APG2.
