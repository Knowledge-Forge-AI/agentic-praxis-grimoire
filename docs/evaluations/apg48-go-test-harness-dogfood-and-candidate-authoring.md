# APG48 Go Test-Harness Dogfood and Candidate Authoring

Phase ID: `APG48`

Evaluation date: 2026-07-27

## Objective and boundary

APG48 opens v0.5 Workstream 2 from the exact accepted APG47 input — the
integrated evidence-guidance state at 28 canonical skills, 28 catalog rows,
and 28 projections — and reconsiders the two previously rejected or deferred
Go candidates, `matryer-is-test-profile` and `go-testing-stack`, against
bounded read-only dogfood in five public Go repositories:
conduitio-labs/conduit-connector-http, esnet/gdg, blockvisionhq/sui-go-sdk,
kubernetes-sigs/bom, and apache/skywalking-mcp. The dogfood exists to develop
or reject the two candidate owners, not to audit or grade any target
repository. All five clones were inspected read-only, each was verified equal
to its current public remote main, and no target test, build, or dependency
command ran anywhere.

## Source, rights, and access

Sources fall into three classes: the five public dogfood repositories
(Apache-2.0 and a BSD-style variant), inspected as facts with independently
written synthesis; the canonical matryer/is `v1.4.1` tag (MIT), whose
behavior facts were verified against the tag sources and cross-checked for
convergence with the prior exact-source and isolated runtime records for the
same tag; and go-cmp `v0.7.0` (BSD-3-Clause), used for version identity only.
Nothing was copied or adapted from any source, and no notice duty was
created. One material access limitation is recorded: the canonical matryer/is
sources were read through a fetch-summarized channel rather than byte-level
local files, so independent byte-level re-reading is a required Codex step.

## Dependency and direct-use findings

Direct versus indirect use was verified per clone rather than inferred from
module files. Two repositories select both matryer/is v1.4.1 and go-cmp
v0.7.0 directly in maintained tests. One declares matryer/is v1.4.1 only as
an unused indirect requirement while using go-cmp directly in one file. Two
are negative controls with no direct use of either library — one governed
entirely by a testify convention, one by pure native testing — and one of
them carries matryer/is v1.4.0 (not the calibrated release) in its module
checksums only. Every repository that actually imports a candidate component
selects exactly the calibrated release.

## Bounded sample

Twelve test files across ten packages were deep-read (four in the mixed
repository whose whole test surface is four files; four across three packages
in the largest repository; two in the go-cmp-only repository; one in each
negative control), inside the assignment's twenty-file budget, supplemented
by repository-wide import and construction inventories. Negative findings are
scoped to the inspected samples and inventories, never to whole repositories.

## matryer/is result

Disposition: **authored-pending-codex-review**. The candidate leaf and
specification exist on the APG48 authoring branch, calibrated to exact
v1.4.1, with a three-part trigger requiring prior selection in maintained
tests (an indirect requirement or checksum entry is not selection), the
exact calibrated release, and material library-specific dependence. All
eight historical defect families from the three prior failed attempts are
closed at authoring time with source-verified mechanisms — including the
equality mechanism's unconditional reflected-value comparison that ended the
previous attempt. Twenty-four scenario families, APG48-IS-01 through
APG48-IS-24, are frozen with dogfood citations. Dogfood calibration recorded
that routine field use is strict-mode, direct-call, and unregistered, so the
structural contract treats registry absence and all count or depth signals as
non-escalating.

## Go stack result

Disposition: **not-authored-no-independent-value**. The eight-part
stack-evidence gate was applied to the strongest recurring cross-component
observation — comparison output consumed through a second assertion surface —
and failed on residual ownership, procedure and trigger precision, and the
prohibition on presence-counting: the shape is fully answerable by the
retained go-cmp owner, the authored matryer/is candidate, the native owner,
and repository idiom convention, and one observed variant runs through a
library outside the three-component universe. Zero cases were observed, in
any sampled file across five repositories, of two selected owners giving
contradictory answers about the same part of one test's observable contract.
No stack leaf, specification, scenario set, or placeholder exists. A no-stack
result is a successful terminal result under the assignment.

## ADR 0030

`docs/adr/2026/07/0030-dogfood-grounded-go-testing-component-and-composition-ownership.md`
is created as **Proposed**: matryer/is as a third independent component, no
stack, no current architecture change. ADR 0025 remains Rejected, ADR 0026
remains Accepted and controlling, and ADR 0027 remains Rejected; none was
edited. The ADR defines the Codex evidence required for acceptance and the
supersession boundary that would apply only if a later authorized phase
accepts it.

## Limitations

This phase is author self-review only; the adversarial review lanes recorded
in the APG48 records are not independent Codex review. No APG executable
suite, Go test, build, benchmark, fuzz, race, coverage, generator, linter, or
package command ran; source inspection and dogfood are not runtime
compatibility evidence. No integration occurred: no catalog row, projection,
route, maturity change, release-policy entry, inventory entry, fixture, or
test was added, and the retained Go profiles were not edited. The complete
Codex handoff, including recommended probes and expected future counts, is
frozen in the publication-excluded APG48 records.

## State

Integrated development remains 28 canonical skills, 28 catalog rows, and 28
projections with unchanged maturity, routing, release policy, test inventory,
executables, and dependencies; the authoring branch adds one candidate leaf
and one candidate specification pending review. Public and active remain the
corrected v0.4.0 at 28/28/28. `main` did not move. No web or Node work began.
No successor phase is authorized; a future maintainer decision may authorize
Codex APG49 to verify the APG48 object, probe and correct the candidate,
decide ADR 0030, and integrate only what passes.

## Subsequent APG49 disposition

APG49 later preserved this exact authoring result, completed byte-level source
and runtime validation, and applied one correction pass. Fresh corrected-state
review found new material defects, so the candidate became
`deferred-material-defect` and its current surfaces were forward removed. ADR
0030 is Rejected; ADR 0026 remains Accepted and controlling. This note does not
rewrite APG48's authoring-time claims or imply that APG48 ran those checks.
