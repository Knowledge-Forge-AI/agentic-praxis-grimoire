# ADR 0054 — JS-QD-005 Refresh Trigger Interpretation

Status: Accepted
Date: 2026-09-10
Phase: APG132

## Context

APG131 technically qualified v0.10.0, but its dispatcher aggregate remained
blocked pending a manager interpretation of the historical JS-QD-005 object.
The [current debt discussion](../../../governance/language-profile-known-debt.md)
distinguishes accepted historical verification from present artifact custody.
The complete machine debt object is immutable historical APG79E human acceptance;
its digest-pinned sibling prose must not be rewritten to modernize that history.
This ADR is current human-facing interpretation authority, not a debt resolution.

## Decision

The authoritative manager ruling is `JS_QD_005_REFRESH_NOT_TRIGGERED`:

1. `JS-QD-005.refresh_condition` is the canonical recurring trigger field.
2. The broader `why_integration_remains_safe` and
   `workaround_or_stop_behavior` text describes the required safety procedure
   when a named trigger fires; it is not a second trigger field.
3. The one-time phrase `before current JavaScript integration` was satisfied by
   APG79E, which directly verified the APG79B report and then provisionally
   integrated JavaScript.
4. APG127/APG129 report-verifier/parser changes do not, by themselves, alter
   the named APG79B managed-report path, bytes, record order, report IDs,
   generator, operational associations, source-role record,
   historical-false-identity disposition, or managed-report-integrity contract.
5. Therefore the current v0.10 report-verifier changes did not trigger a new
   APG79B refresh obligation.
6. JS-QD-005 remains active and stable-blocking.

### Generator scope and APG131 probe disposition

The manager adopts the historical byte-producing-owner reading reserved in
APG131's manager-facing decision. The recurring generator condition concerns
APG79B's historical byte-production and format authority. It does not encompass
stricter new-input acceptance or opt-in append behavior in a replacement tool
when the historical rendering contract remains compatible.

APG131 correctly observed a production acceptance change: historical Python and
pre-APG127 Go accepted two synthetic malformed requests that the current writer
rejects; the valid control retained identical payload bytes. That finding is
preserved. It does not demonstrate a change to the named APG79B generator or
prove that APG79B contains either malformed input. Renderer preservation alone
is not equivalence of the entire evolving production generator. The ruling
resolves the scope question, rather than denying those probe observations or
claiming a new execution of scratch-only probes. Earlier compatible Go migration
and oracle relocation likewise do not supply a second recurring trigger field.

### Historical prerequisite and future procedure

APG79E directly verified the canonical APG79B report through EOF at SHA-256
`9b56d503039c2907d371b37b72451b6e0b71cca41aa0cd23c074453229698827`,
then provisionally integrated JavaScript. Bounded APG129/APG130 searches later
did not locate the original artifact in configured agent-visible roots. Present
non-observation does not invalidate historical APG79E verification. This ADR
attests neither present custody nor fresh report bytes, order or associations.

The prerequisite was satisfied once before integration; releases are not new
integration events. If a named recurring trigger later fires, the workaround
is unsatisfied until direct refresh through EOF, regeneration and association
verification, or a separately accepted repair/human re-evaluation. Do not
reconstruct a substitute report. No renewed artifact search is required absent
a fresh mechanical comparison demonstrating a changed named condition.

## Alternatives considered

- Rewrite sibling JSON prose: rejected because it rewrites historical acceptance.
- Treat sibling prose or every release as an independent trigger: rejected by
  canonical-field precedence and the satisfied one-time prerequisite.
- Treat all replacement-writer acceptance changes as APG79B generator changes:
  rejected by the manager's historical-owner interpretation.
- Resolve or promote JavaScript now: outside scope; active debt still blocks
  stable maturity.

## Consequences and deferred decisions

APG131 technical qualification is accepted and its sole governance decision is
resolved. Its dispatcher transport remains historically blocked. APG132 records
current readiness separately; it does not rewrite historical phase outcomes.
JS-QD-005 remains active and stable-blocking, with repair or separate human
re-evaluation deferred. No skill, executable, debt JSON, release policy or
maturity change follows from this interpretation. Candidate freeze, publication
and deployment remain separately authorized actions.
