# APGR dispatcher bundle v1

Status: Accepted with APG166S under ADR 0075.

The selected APGR home owns `dispatcher/models.toml`, `workers.toml`,
`endpoints.toml`, `routes.toml`, `capabilities.toml`, `policy.toml` and a
`bundle.json` manifest binding their bytes. All members have the same positive
generation. Home resolution follows the existing explicit option, environment,
then default precedence. No other dispatcher's home participates.

`models.toml` maps provider/profile selections to models and efforts.
`workers.toml` owns policy, pool ceilings, worker profile references and required
modes. The remaining members retain their route, endpoint, capability and
operator-policy responsibilities. Selected references must validate; unused
valid inventory entries are not forced to match a historical full catalog.

An absent home bundle permits source defaults only when
`[dispatcher.bundle] required = true` is not selected. An existing incomplete
bundle, mismatched generation, invalid member or manifest mismatch fails closed.
A legacy four-file home bundle requires explicit projection/migration; it is
never silently upgraded. Candidate tests and canaries use explicit isolated
homes and never depend on live operator configuration.

## Deployment contract

`apgr dispatcher bundle project` prepares source defaults in an explicit target
home. `apgr dispatcher bundle verify` checks the resulting complete generation.
The deployment owner must validate before activation, preserve the previous
generation for rollback and change the complete directory atomically. A
platform without the required atomic replacement operation must refuse an
existing-target update; two renames with an absent-target window are not atomic.

DINAS is a future deployment consumer of this contract. APGR loading, local
projection, testing and worker operation do not import or execute DINAS.
Deployment is not authorized by successful local projection.

## Launch and evidence

The dispatcher captures the bundle once. Child launchers receive captured model
bytes and their digest; the snapshot selects actual launch arguments. Provider
profiles retain posture, while the bundle determines model and effort. Worker
entrypoints and MCP commands resolve absolutely under the candidate runtime.

Requested model and effort are distinct from provider-observed effective
values. Pass the selected model/profile and effort correctly and trust the
provider to honor accepted parameters. Missing internal provisioning metadata
remains explicitly unknown, not a failed worker or an acceptance blocker.
Preserve provider errors, explicit mismatches, task results and cleanup under
this settled provider-contract standard (ADR 0075).
External ledger custody remains until cleanup is proven; native occupancy is
owned by Codex runtime events and its launch-bound cap. Neither a capability
label nor a zero exit code substitutes for task results and cleanup evidence.
