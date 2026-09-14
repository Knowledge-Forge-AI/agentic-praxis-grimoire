# APG142 JS-QD-005 historical-report trigger audit

Closure ID: `APGR-DEBT-JS-QD-005`. Maintenance ID: `JS-QD-005`.
Observation date: 2026-09-12. Producer finding: **FALSE**,
`JS_QD_005_REFRESH_NOT_TRIGGERED`. Status: `REVIEWED_WITH_FINDINGS_AMENDED`.

## Accepted baseline and condition

[ADR 0054](../../../adr/2026/09/0054-js-qd-005-refresh-trigger-interpretation.md)
is the accepted APG132 interpretation. The recurring condition concerns APG79B's
managed-report path, bytes, record order, report IDs, historical byte-producing
generator/format authority, operational associations, source-role record,
historical-false-identity disposition or managed-report integrity contract.
The [known-debt owner](../../language-profile-known-debt.json) remains intact.

APG79E satisfied the one-time pre-integration direct verification obligation.
A new release is not another integration. Sibling workaround prose describes
the procedure after a named trigger, not another condition. ADR 0054's generator
scope excludes compatible replacement-tool input acceptance or opt-in append
behavior from the historical byte-producing-owner condition. This audit does
not re-attest present custody or unseen report bytes.

## Fresh path and semantic comparison

The parent compared the APG132 interpretation baseline to current source over
`report/`, `schema/`, `internal/gitexec/`, JavaScript fixture/support authorities,
the debt JSON/prose, ADR 0054 and APG79E decision evidence. The two changed
reporting selection paths in that bounded comparison are `internal/cli/cli.go`
and `internal/cli/response.go`. APG141's own source diff was then inspected.

- `validateExplicit` now removes leading ASCII dots from the repository basename
  for modern report writes as legacy writes already did. An explicit project
  must still match the result. No alias or remote identity mapping was added.
- Response capture applies that same normalization to derived or explicit project
  selection. It is therefore broader than explicit-option acceptance alone,
  but changes only previously refused dot-prefixed basename cases.
- APGR's own development basename has no leading dot; its derived project and
  managed-report path are unchanged. Previously successful requests retain keys
  and envelope bytes under the [APG141 contract](../../optional/apg141/project-key-contract.md).
- The collector, renderer, record-ID algorithms, operational association owner,
  integrity schema, source-role evidence and historical disposition in the
  inspected source set are unchanged since the controlling interpretation.

| Named condition | Source-bound conclusion and limit |
| --- | --- |
| Historical path | No APG141 change to APGR's path derivation and no artifact move by this campaign. Original custody is not asserted. |
| Bytes, order and IDs | No changed historical byte-production, ordering or ID authority in the compared source. Original artifact bytes were not read. |
| Generator/format | Compatible modern acceptance normalization falls outside ADR 0054's historical-generator condition; rendering owners are preserved. |
| Operational associations | Association owner preserved; no fresh parsing of original associations is claimed. |
| Source-role record | JavaScript source-role/fixture authorities in the bounded comparison are unchanged. |
| Historical-false-identity disposition | APG79E acceptance and ADR 0054 interpretation are preserved. |
| Integrity contract | Reporting schema/verifier and named interpretation are preserved. |

Thus the observed APG141 delta demonstrates no changed named recurring condition.
This is a bounded source comparison under the accepted historical interpretation,
not a claim that current bytes of an unavailable original artifact were verified.
No APG79B artifact search or substitute reconstruction occurred. Present absence
is neither trigger nor disproof of accepted historical verification.

## Repair distinction and consequences

The separate repair is a proportionate direct managed-report identity binding,
preferably existing report ID plus full-file digest or reusable integrity owner,
rejecting a changed APG79B report without making it a semantic oracle or duplicated
current evidence system. It is not performed here. Terminal outcome is
`MAINTENANCE_TRIGGER`; the closure row is terminal after supplied review and closeout verification.
JS-QD-005 remains active, stable-blocking and non-blocking for the accepted
provisional integration. No debt resolution or maturity promotion is proposed.

Next owner: JavaScript profile and APGR managed-report maintainers. When a named
condition changes, record the change and perform the accepted direct refresh:
locate the original, parse through EOF, regenerate immutable Git-show payloads,
verify operational associations and exact full-file digest, or obtain the
separately accepted repair/human re-evaluation. If the required original is
unavailable, retain OPEN and report that prerequisite. Never synthesize it.
The supplied pre-final review corroborated this interpretation and comparison.

Terminal decision: [individual receipt](decisions/APGR-DEBT-JS-QD-005.json).
Review and post-review amendment boundary: [supplied work review](work-review.md).
