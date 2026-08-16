# APG81 Node.js Runtime and CLI Iterative Hardening Repair Checkpoint

## Status

Complete as a repair checkpoint. APG81 preserves three immutable correction
rounds under accepted ADR 0042. ADR 0046 remains **Proposed**,
`nodejs-runtime-profile` is `repair-required-after-round-3`, and no Node
integration owner exists.

## Preserved hardening history

Round 1 corrected two High and seven Medium findings across candidate routing,
fixture contracts, runtime binding, source and rights evidence, target facts,
lifecycle state, and report ownership. Round 2 corrected four High and four
Medium findings across closed contracts, exact runtime roles, process and
filesystem evidence, traceback privacy, rollback ownership, and report binding.
Round 3 corrected its two frozen High path-replacement families by adding
user-immutable flags, post-pin revalidation, protected parents, and maintained
replacement negatives. Every round has a separate immutable commit and exact
Git-show/operational report pair.

Round 3 produced 97 passing focused tests under the exact primary and secondary
Node runtimes. Full unit evidence is 3,022 passing tests at 6,693/7,736
statements and 2,277/2,846 branches. Those results remain real evidence for the
contracts they exercise.

## Terminal review

Three fresh non-author lanes independently reviewed the immutable Round 3
object. They confirmed zero Critical, three High, two Medium, and zero Low
material findings:

1. The Darwin user-immutable flag is owner-clearable. Same-UID code can clear
   it and replace an executable or protected pathname before path-based spawn or
   write resolution, so unvalidated bytes can execute before post-check refusal.
2. Pinning the owned root or one direct parent does not close deeper accepted
   environment components or writable nested leaves. A redirect can carry a
   path-based write outside owned scratch. The writable nested-leaf symlink case
   belongs to this same finding family.
3. Runtime setup performs path-based temporary-directory creation, copy, mode,
   and digest work before the immutable pins, leaving a pre-pin replacement
   window.
4. Supplying the owned root itself as a protected directory can select and
   temporarily change flags on its parent outside the assignment-owned root.
5. Partial pin or restoration failure can retain flags or artifacts, while the
   maintained evidence states stronger identity, restoration, and cleanup
   guarantees than the implementation proves.

No finding was falsified or newly split. The passing test selections do not
establish hostile same-UID resistance, full descendant-path containment,
pre-pin setup safety, outside-parent ownership, or complete partial-failure
restoration. No finding is accepted as debt. With the default three-round
budget exhausted, integration is blocked and a new human continuation decision
is required.

## Preserved product state

Node remains branch-only at 33 canonical skills, 32 catalog rows, and 32
projections. Integrated main remains exact APG79E at 32/32/32, 14 stable / 18
provisional rows, and 30 general / one ChatGPT-local / 31 checked routes. The
known-debt register remains exactly CSS-QD-001 through CSS-QD-005 and JS-QD-001
through JS-QD-005: ten entries, nine Medium and one Low. APG81 accepts no Node
debt.

ADR 0042 remains Accepted; ADRs 0043, 0044, and 0045 remain Accepted with
amendment; ADR 0046 remains Proposed. Corrected historical, public, and active
v0.4.0 remain unchanged. Both read-only targets remain unmodified and
unexecuted.

## Boundary

No fourth correction, APG81A implementation, Node integration, mainline
adoption, target command, package installation, stable maturity, readiness,
publication, deployment, rejection, removal, APG82, or successor work ran.

A future human decision may consider a narrow APG81A threat-model and harness-
simplification continuation: state a controlled local/CI threat model, keep
fixtures non-sensitive and APG-owned, treat scratch containment as correctness
and cleanup rather than an operating-system sandbox, and route hostile same-UID
isolation to a separately selected security owner. This is a recommendation,
not authorization, and no APG81A work has begun.
