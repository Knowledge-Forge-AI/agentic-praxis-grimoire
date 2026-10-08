# ADR 0075: APGR worker and model configuration authority

Status: Accepted — APG166S manager acceptance after local R2 finalization.
Historical findings and amendments below retain their original dispositions.

## Context

The transferred dispatcher still depended on an external worker package, while
provider profile files duplicated model choices. Static worker labels did not
establish usable delegation and optional fallback could silently remove workers
from a route that required them.

## Decision

APGR owns worker admission, custody, supervision, cleanup, external transports,
the Claude MCP facade and the Codex native-pool binding. The `apgr_workers`
package has no runtime dependency on the emergency dispatcher's installation.
Each dispatcher owns its guidance copy and configuration. Emergency selection
is an explicit operator action; APGR performs no automatic failover.

The APGR-home dispatcher bundle owns runtime model, effort, route and worker
policy selection. Source defaults supply development and deployment inputs.
This supersedes the earlier invariant that model and effort exist exclusively
in provider profiles. Profiles continue to own tool, permission and directory
posture. Captured model bytes are carried to child launchers so a home update
cannot silently change an admitted stage's model choice.

The standard `gemini_sub` route uses Opus 5.5/high for plan and both reviews,
and Astra 6/medium for work and closeout, across existing phase types.
Every stage receives independent Gemini and Luna ceilings of four, without
borrowing. Luna is GPT-6 Luna/max: external for Claude, native for Astra.
Workers are leaves and inherit no greater task authority than their parent.
Read-only delegation cannot run tests, builds or product mutations.

Required worker modes fail before parent invocation when qualification or
binding fails. Dynamic routing must qualify the subsystem and bindings beyond
static capability labels. Stage evidence distinguishes used, declined with
reason, and technically unavailable.

## Compatibility and qualification

The historical Claude `primary` model remains Opus 5. A separate `opus` role
serves the new route. The legacy catalog schema identifier remains a format
compatibility label, not external runtime authority.

Incomplete and legacy operator bundles require explicit migration. Missing
optional bundles may use source defaults; required bundles cannot. DINAS may
later deploy a verified complete bundle atomically, but is not a runtime
dependency. No live home is changed by this phase.

Configuration alone does not qualify any canary. Four bounded parent/worker
combinations require retained admission, effective-model observation, result
and cleanup evidence. D1 source bindings change and require provider-free
carry-forward plus independent disposition before APG166T. No live D1 or H
holdout is authorized by this decision.

Rollback is an operator-selected previous complete bundle and matching APGR
runtime after all admitted worker custody has drained. Never resize a live pool
or reinterpret a prior ledger under a new policy.


## APG166S-R1 amendment

The repair retains Proposed status. Explicit historical source-default
qualification remains distinct from ordinary selected-home authority. Runtime
consumers use captured selections; generated projections do not become another
model owner. Fixed four-plus-four pools remain policy. Canary qualification
requires genuine bound observations and durable consumed-attempt accounting;
requested configuration alone cannot satisfy missing effective-model evidence.

R1 producer evidence repairs selected runtime authority and separates historical
source-default qualification from current home-path qualification. The live
four-case requirement remains incomplete. One case qualified the producer seal;
closeout runtime corrections invalidate that seal for the terminal candidate.
Zero cases qualify the terminal runtime. This ADR remains Proposed; acceptance
is deferred to the manager with exhausted Luna budgets and remaining evidence gaps.

## APG166S manager acceptance — 2026-09-27

APG166S and all four parent/worker combinations are accepted. Both Luna
carry-forwards are settled; accepted source has been locally committed without
push. Historical findings, receipts, requested settings and observed values
remain unchanged.

The settled provider-contract standard is to pass the selected model/profile
and effort correctly and trust the provider to honor accepted parameters.
Preserve normal provider errors, explicit mismatches, task results and cleanup.
Missing internal provisioning metadata remains unknown; it is neither a failed
worker nor an acceptance blocker. This is the normal standard, not a temporary
exception. It supersedes historical effective-observation acceptance requirements
in this record without relabelling requests as observations.

APG166T-PREP1 prepares the existing one-shot D1 handoff only. It authorizes zero
D1 starts and issues no live authority. H remains static by default, its gate
remains false, and promotion, V0130-I, deployment and publication remain outside
this preparation scope.
