# APG166V — H granted execution path

Continuation: H-COMPLETE1 within the existing V0130-H milestone. No new ADR or exit.
Status: implementation preparation candidate; the host mechanical result and
manager acceptance are separate, later records.

COMPLETE1 adopts READY1's eight preserved paths and the eleven-path
user-authorized `claude_only` correction as its entry. READY1's blocked record
remains immutable. APG166S, D1 observed capability plus corrected offline replay,
and REGRESSION1 remain closed. Both original D1 attempts remain failed and
consumed.

## Scenario 14 packaging

The subject manifest requires `scenario-14/pkg/data/models.go`, which the root
`data/` rule excluded. A three-line exact-file exception re-includes only that
file; sibling files, other `data/` directories and generic data paths stay
ignored. The file's 120 bytes, mode and SHA-256 match the unchanged manifest. A
focused regression captures the candidate with the maintained
`agent_phase.candidate.tree_identity` owner in a disposable shared clone, exports
the resulting tree, and verifies every subject manifest entry from that export.
The same capture with the historical ignore rule omits the file and fails
verification. The real repository index is not written.

## Mode-correction binding refresh

The mode correction changed `common/dispatcher/routes.toml`, `endpoints.toml`
and `models.toml` bytes. Only the corresponding route-source digests in
`testing/h_eval/scenario-bindings.json` are refreshed (90 digests over 15 rows
and 30 routes). Every other route field, scenario, subject, metric, budget,
model and effort is unchanged, and `verify_bindings` passes on the real tree.
`testing/h_eval/d1-descriptor.json` pins the same three older digests and is a
fixed, closed D1 input; it is not refreshed here. Its descriptor-based tests fail
on that mismatch until a manager decides between refreshing the pins and
retaining the red tests.

## Evidence separation

These facts remain distinct and none implies another:

- preparation evidence: source bindings, the recomputed READY1-shape readiness
  seal and the provider-free package seal;
- conditional independent preregistration approval for the five skills;
- the host provider-free mechanical result, which does not yet exist;
- the external D1 acceptance/replay decision, bound only by digest;
- a later external manager decision and live grant.

The readiness seal still reports `prerequisites_ready: false` and its
`live_admission_available` gate still reads the source default, which is always
false. That gate now means only "source-default admission without an external
grant"; it is not how a granted arm is admitted.

## Live admission contract

`testing/h_eval/live_admission.py` is the only admission owner. Authorization is
exactly two absolute paths, `decision_path` and `grant_path`, to private
operator-owned records under a custody root outside the source tree. Booleans,
`authorized` flags, readiness seals and `LIVE_ADMISSION_AVAILABLE` are refused.

The decision (`apg.h-manager-decision/v1`) binds the recomputed source identity,
scenario-binding, preregistration, subject-manifest and D1 carry-forward digests,
the route digest of every derivable unit, the sealed live runtime manifest
digest, the retained host transaction directory, and digests of the readiness
seal, package seal, host result, external D1 decision, installed-home comparison
and all five skill approvals. The grant (`apg.h-live-grant/v1`) names derived
units (`scenario-NN/static|adaptive` for 01–14, `promotion/<case_id>`), a start
ceiling equal to its unit count and at most 53, one start per unit, no replay,
no retry and an expiry. Acceptance units also require a digest-bound evaluation
seal and binary; building those is a later manager step.

Admission recomputes the readiness seal and its embedded package seal from the
retained transaction and requires byte-for-byte equality with the bound
evidence, a passing host result for the same source identity, current bindings
and routes, and the decision's runtime digest. Acceptance units are refused until
every calibration unit has been consumed under the same decision.

Consumption writes `<custody>/h-consumed/<unit>.json` exclusively before any
arm directory, context or provider work exists. The ledger is unit-scoped across
all grants under one custody root: a consumed unit cannot be admitted again, and
a grant listing a unit consumed under another grant is refused. Accounting
reports granted, consumed, retained, consumed-without-result and unconsumed
units and never starts, retries or deletes anything.

The custody root is named by the decision, so replay protection holds only
within one custody root. A later decision naming a fresh custody root would start
with an empty ledger. The code does not prevent that. It is a manager-owned
invariant: one H campaign uses one custody root for every decision and grant, and
its ledger is never moved, copied away or deleted. Any decision with a different
custody root needs an explicit manager record that carries every earlier ledger
forward. Otherwise it is an alternate identity and is prohibited.

Consumption also happens before the arm or case output directory is created. If
creating that directory fails, the unit stays consumed with no retained result.
Accounting reports it as `consumed-missing-result`. It is never retried.

## Pair stop and calibration interaction

`run_granted_pair` does not start the adaptive arm whenever the static arm is
refused, incomplete or unreadable. That includes a model-caused authority
violation, which the existing arm owner reports as incomplete. The adaptive unit
then stays unconsumed. `admit` refuses every acceptance unit until all ten
calibration units are consumed under the same decision, and aggregation requires
all 28 arms measured live. As a result, one failed static arm has two effects:

- a calibration failure blocks acceptance admission unless the manager decides
  otherwise;
- any failed arm makes the complete aggregate permanently unavailable.

This phase does not authorize a later separate start of a skipped adaptive unit,
and it does not decide whether such a start is a prohibited selective rerun.
Both remain explicit manager decisions. Until one is recorded, the skipped unit
stays unconsumed, is named as missing, and is never started.

## Execution, promotion cases and assembly

`construct_arm(..., execution="live", live_authorization=...)` refuses malformed
authority and caller injection first, then admits, runs the existing frozen
route, scenario, construction and runtime checks, and consumes immediately before
creating the arm. The receipt is retained in `admission.json` and the result.
The sealed runtime inputs are retained with each arm so a consumed failure can
still be read back. The post-run check re-verifies source, route and runtime.
Qualification eligibility accepts a verified admission receipt that binds the
arm's unit, route and retained source inventory in place of a ready seal; the
seal boolean itself stays false.

`granted_execution.run_granted_pair` runs static then adaptive through that owner
with immediate readback and stops without starting adaptive when static is
refused, incomplete or unreadable. `run_promotion_case` admits and consumes one
promotion unit, materializes the preregistered subject with the exact
preregistered skill body at `.agents/skills/<skill>/SKILL.md`, requires the
operator's global Codex skill root to be absent, builds the Codex producer argv
through the maintained provider builder with frozen source guidance and no
skill-disable configuration, and invokes the manifest-bound provider runner
exactly once. It retains streams, subject inventories and diff, a delivery
receipt, the import receipt and a graded copy that excludes git metadata and the
delivered skill. Oracle status is retained for later independent attribution
review; `promotion_authorized` and `maturity_ledger_written` stay false.

Assembly aggregates only when every row 01–14 is measured live with a verified
admission receipt, Scenario 15 is explicitly unavailable under the contingent
disposition, and grant accounting shows every scenario unit retained. Missing
arms are named. The frozen `evaluate.aggregate` formulas and quality checks are
unchanged; with Scenario 15 contingent the benefit gate stays false.

## Host mechanical transaction

`testing/h_eval/host_mechanical.py`, wrapped by the delivered
`host-mechanical.py`, validates the host layout, local tools, the reviewed cache
input and IPv4 loopback, seals a runtime with three separate version-only
simulated providers, runs exactly one transaction through
`run_final_b8_transaction.run_transaction`, reads the retained evidence back and
writes `host-mechanical-result.json`. It never probes or starts a real provider
and never retries. The coding sandbox denies loopback, so the complete
transaction runs only on the operator host.

## Limitations

- Custody checks are local ownership, mode and digest checks. A process running
  as the operator can author both records; this is not a signature.
- The external D1 decision, installed-home comparison and skill approvals are
  bound only by path and digest. Their contents are not structurally validated,
  and the source carry-forward remains structural.
- Promotion route checks verify the pinned model-source digest. They do not
  compare the preregistered `route.model` with the pinned profile or with the
  observed imported model.
- The delivered host wrapper pins the digest of `testing/h_eval/host_mechanical.py`
  only. The contract records the digest of `run_final_b8_transaction.py`, and
  the source identity is recorded before and after the run. Its `sentinels` count
  comes from the provider-free guard receipt, where a detected sentinel raises
  rather than increments, so the count is not independently informative.
- Promotion delivery relies on Codex repository-scoped skill discovery; this
  phase measures delivery, not discovery or use.
- Real scenario and promotion oracles need the host toolchain; fake-provider
  tests use a deterministic oracle double only where oracle execution is not the
  behavior under test.
- Stable promotion still requires actual guidance use and its own independent
  decision.

## What would make this wrong

- A live arm or promotion case starts without a valid decision and grant, or a
  consumed unit starts again under any grant in the campaign custody root.
- A refusal consumes a unit or creates an arm.
- A failed live start cannot be read back, or a missing arm is aggregated.
- Scenario 15 is measured while contingent, or the benefit gate becomes true.
- The host result reports expected counts instead of observed ones.
