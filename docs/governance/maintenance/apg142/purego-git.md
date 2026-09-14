# APG142 pure-Go reporting Git audit

Closure ID and maintenance ID: `APGR-REPORT-PUREGO-GIT`.
Observation date: 2026-09-12. Producer finding: **FALSE**.
Status: terminal `MAINTENANCE_TRIGGER` after supplied review.

## Accepted condition and baseline

The [maintenance register](../../maintenance-triggers.json) preserves the exact
recurring condition: an environment strictly prohibiting subprocess execution or
Git CLI binary availability. The [backlog consolidation](../../../v0-10-backlog-consolidation.md)
and [v0.7 architecture](../../../architecture/v0-7-embeddable-toolkit.md) bind
its accepted source. The distinct repair condition is bit-for-bit Git CLI diff
parity without launching subprocesses. The broader evidence-required rationale
(demonstrated inadequacy, security defect or platform restriction of sanitized
Git invocation) does not silently replace the recurring condition.

## Current supported environment and positive evidence

The inspected scope comprises APGR's Go reporting library, Python and npm
wrappers, its current local development environment and the source-bound JACA
provider handoffs. This is a contract observation, not runtime qualification of
every machine on a supported operating system.

| Inspected owner | Positive evidence and significance |
| --- | --- |
| `report/types.go`, `report/service.go`, `internal/gitexec/gitexec.go` | Options explicitly selects native Git; construction invokes Git root discovery through the sanitized exact-argv runner. The current implementation retains the architectural process boundary. |
| `docs/architecture/v0-7-embeddable-toolkit.md` | Initial reporting explicitly permits native Git execution while prohibiting shell command strings. A process-free promise is not part of this baseline. |
| `src/agentic_praxis_grimoire/go_bridge.py`, `src/agentic_praxis_grimoire/reports.py` | Python delegates through subprocess execution to the Go binary; the reporting API retains the native-Git prerequisite. |
| `npm/README.md` and its packaged launcher | The launcher runs the native binary with inherited streams and `shell: false`. Its Git/Go prerequisite statement concerns source-checkout test roles, not a promise that every npm installation has Git installed. |
| `docs/architecture/apg-jaca-integration.md` | The explicit shell-free/process-free distinction permits APGR native Git behind direct Go imports. JACA library embedding alone does not establish subprocess prohibition. |
| `docs/architecture/jaca-ci-handoff.md` | The provider CI contract expressly requires Git and toolchain availability. |
| APG140 external support and APG141 terminal records | Provider-owned handoffs retain consumer-owned adoption and envelope adaptation limits; they do not add a process-prohibited reporting requirement. |
| Current development environment | Actual successful Git status, source comparisons and maintained reporting-tool invocations demonstrate Git availability and allowed subprocesses for this run. This observation does not attest consumer runtime state. |

These positive requirements and observed local operations are sufficient for a
bounded FALSE finding in the inspected supported/current contract scope. It does
not follow from an empty demand search, absence of telemetry, the existence of a
pure-Go library, or a platform's general ability to launch processes. No claim
is made that a hypothetical future consumer could never need in-process Git.
No consumer repository was executed or mutated; current provider handoff records
were sufficient to decide this contract question without a new consumer campaign.

APG141 hotspot history is a separate opt-in owner; its symlink/gitlink refusal,
256-commit ceiling and abandoned combined scoring do not repair or trigger this
reporting-backend item. Ordinary report APIs and native Git remain preserved.

## Consequence, next owner and refresh

Terminal outcome: `MAINTENANCE_TRIGGER`; no backend repair is proposed.
This condition has no stable-blocking skill consequence. The next owner is APGR
reporting maintainers. On an actual supported/current environment or consumer
contract change, inspect the exact prohibition and record TRUE/FALSE/UNKNOWN
with source-bound evidence. A demonstrated prohibition requires the smallest
qualified in-process reader through public reporting entry points, actual
subprocess prohibition and bit-for-bit parity. A required missing prerequisite
is not a pass. A major dependency or incompatible contract requires a narrow
decision. Future evidence collection must not depend solely on absence of demand.

No original historical report custody, cross-platform runtime campaign, consumer
adoption or new supported platform is attested. The supplied semantic review and separate terminal receipt are bound in the campaign index.

Terminal decision: [individual receipt](decisions/APGR-REPORT-PUREGO-GIT.json).
Review and post-review amendment boundary: [supplied work review](work-review.md).
