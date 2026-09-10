# APG135 v0.10.0 release freeze qualification boundary

## Scope and proposal disposition

Proposal disposition: **amend**. APG135 executes the deterministic release
freeze assignment from APG134's qualified corrected source. The proposal is
amended for all six advisory findings: distinct Git and archive timestamps,
the interpreter-owned distribution entrypoint, the APG119 phase-owned canonical
Go ZIP helper, an explicit confidentiality policy, a full-history public base,
and both nested ChatGPT skill leaves. No stage deltas were supplied at entry.
The dispatcher owns independent review, closeout and Git finalization.

APG133 remains historically blocked before construction. APG134 packaging
readbacks are not reused as release artifacts. APG135 and exit 00180 were
available and are allocated without substitution.

## Completed construction evidence

Fresh public entry observations match the required v0.9.0 main, tree, sole
parent and annotated tag. No public v0.10.0 tag is present; the public GitHub
release endpoint returns HTTP 404. This establishes public visibility, not
private draft visibility.

The cheap corrected-source preflight passes. All three maintained wording test
files have successful command receipts, including the exact twelve-surface audit
and stale-wording negative controls. Fresh Python metadata contains the complete
README, version 0.10.0 and conditional Python/npm/Go installation pins. Local
Markdown rendering, link checking and record identity have successful receipts.
Detailed preflight counts and the producer-reported release-surface, symlink,
versioned-exclusion and confidentiality checks depend on retained scratch logs;
the compact packet alone does not independently establish those details.
APG133's wording defect is absent.

Two independent maintained public-release builds produce identical projected
manifest bytes, release tree, commit, annotated tag, complete ref topology and
Git metadata. The candidate has 1,278 projected paths, all 45 skill leaves and
45 projections, including both nested ChatGPT leaves. The Repo Map roadmap,
ADR 0054 and v0.10.0 notes are included. No private development path enters the
candidate. Exact objects and compact manifests remain publication-excluded
reproducibility evidence; raw candidate repositories remain in retained external
task scratch.

## Observed qualification boundary

The governing blocker is a defect in frozen APG134 source: the release-workflow
fixture supplies v0.9.0 assets and tag to a verifier requiring v0.10.0. The
focused source reproduction fails independently of public projection. This
requires corrected source and complete reconstruction under separate authority;
a checker-only repair cannot qualify the retained candidates.

The dispatcher review also identifies a collection gap. The canonical runner
passes suite directories to pytest, whose default dot-directory exclusion
prunes the workflow integration file and its unit sibling beneath `.github`.
The inventory uses recursive path enumeration and includes these files, but
does not compare inventory entries with collected pytest node IDs. The public
checker supplies explicit file paths and consequently exercises the workflow
fixture. Canonical passes therefore do not establish coverage of those files;
the complete defect inventory remains unknown.

The public checker owns seven exact exclusions for tests requiring private
development history or source oracles. Its `validate_categories` implementation
applies that list only when the selected Python test files exactly equal the
v0.7 tuple. The current v0.10 policy selects 151 Python test files; the v0.7
tuple has 134. The exclusion branch therefore does not execute for v0.10. Versions v0.8
through v0.9 added Go entries only and preserved the v0.7 Python subset;
v0.10 adds seventeen Python files and first breaks the equality.

A focused run on an exact projected copy reproduces failure in
`test_python_skill_bridge_matches_oracle_and_routes_new_go_surfaces`: its
private oracle is absent, so the imported `skills` namespace has no `main`
attribute. This test is explicitly named in the maintained exclusion list.
The same test passes against the frozen private source with its oracle present.
The canonical coverage runner also selects the test without a built-in
public-candidate exclusion route. This is distinct from a release-wording
regression and does not establish a consumer runtime defect.

Both maintained candidate checks and the canonical coverage invocation were
already in flight when the focused failure was established. The canonical run
finishes with 3,684 unit passes and 23 reported skips, with coverage passing at
10,176 / 11,865 statements and 3,689 / 4,598 branches. This projected run does
not claim to reproduce the private-development test count. Integration finishes
with seven failures, 701 passes
and two maintained skips. The seven failed node IDs exactly equal the
maintained public exclusion list. The union gate is not reached. After this
completed canonical result established the stop boundary, the two remaining
candidate checks were deliberately interrupted with SIGINT. They return
nonzero and are incomplete, not completed qualification runs. Both preserve
the exact source/base/candidate fingerprints; their isolated validation copies
also pass the checker's preservation checks before it returns the test error.
No failure is treated as a pass and no threshold, exclusion, denominator,
source file or candidate byte is changed to bypass the boundary.

The only observed failure in each interrupted candidate check is in
`test_verification_step_selects_the_exact_checked_distribution_paths`. Its
workflow fixture still supplies v0.9.0 asset names, manifest version and event
tag, while the current workflow requires v0.10.0. A separate focused run on
frozen APG134 source reproduces the same failure. This source defect governs the corrected-source requirement and is independent
of the release-tooling exclusion-policy defect.

The partial candidate results are one failure, 234 passes and two skips for A,
and one failure, 231 passes and two skips for B; each also reports 95 subtest
passes. These partial counts are not a complete defect inventory. The producer reports no remaining check processes or workers, but the compact
cleanup receipt contains scalar assertions without process-table evidence;
independent review could not verify process cleanup. It also records one
remaining isolated-validation temporary root. Retained scratch and this residue
are preserved; filesystem cleanup is not claimed.

## Stop and retained limitations

Dependent distribution construction is stopped. There is no qualified ten-asset
bundle, canonical Go module freeze, archive/runtime smoke result or usable
publication operator packet. Candidate identity equality alone is insufficient
for release qualification. The requested success state
`V0100_RELEASE_BUNDLE_QUALIFIED_FOR_OPERATOR_PREFLIGHT` is not achieved.

Linux runtime execution, Tauri embedded WebView and assistive-technology
qualification remain unestablished. Skill maturity, JavaScript debt and CSS debt
dispositions remain unchanged. No registry, public ref, GitHub Release, host or
consumer state is mutated. Exit readback again matches the required public
v0.9.0 main and annotated tag, with no public v0.10.0 tag and HTTP 404 for the
public v0.10.0 release endpoint. No source correction or successor is authorized.
Resolution requires dispatcher disposition of the qualification boundary;
any corrected release input requires complete reconstruction under fresh
authority. The retained candidates are not approved for publication.

See [exit 00180](../status/2026/09/10/00180-apg135-v0100-release-freeze-qualification-boundary-exit.md).

## Terminal review disposition

Disposition: **amend**. The blocked result is retained. Source-defect emphasis,
workflow collection limitations, roadmap wording, attribution and evidence
limitations are corrected as reporting-only changes. No frozen release input,
build tool, operator executable, candidate or asset identity changes.

The recommendation to complete both candidate checks is deferred to a separately
authorized corrected-source phase, before dependent artifact construction. This
closeout does not restart interrupted checks or seek another substantive review.
The scratch root's mode 0700 meets the storage requirement; inner mode 0755
directories do not require correction. Process cleanup remains unverified by
independent evidence. Final bounded documentation and packet-integrity checks
are recorded in the closeout evidence; no full qualification gate is rerun.
