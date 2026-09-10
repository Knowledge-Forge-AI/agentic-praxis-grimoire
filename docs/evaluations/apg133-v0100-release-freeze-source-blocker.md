# APG133 v0.10.0 release freeze source blocker

## Scope and disposition

APG133 attempted the authorized deterministic freeze of accepted APG132 source.
Proposal disposition: **amend**. The pre-construction wording audit is mandatory;
the original qualification scope remains unchanged. Construction stopped before
candidate or distribution creation because the selected source contains a
release-facing documentation defect. Bundle qualification is not achieved.

## Source finding

The [README upgrade guidance](../../README.md#upgrade-guidance-and-release-status)
describes v0.10.0 preparation but directs Go, Python and npm consumers to install
v0.9.0. The [release notes](../../release/v0.10.0-notes.md) retain preparation-only
status and pending dispatcher finalization. The documentation index also retains
internal dispatcher/future-freeze process prose in a permanent public surface.
The correction must address that prose as well as version numbers.

This is material to the permanent release artifact: `pyproject.toml` selects
the root README as the package description, and the maintained Python backend
embeds that text while rewriting relative links, without rewriting version
instructions. This source inspection establishes propagation; no package build
or runtime reproduction is claimed.

[APG116](apg116-v090-release-wording-amendment.md) records the applicable
precedent: permanent documentation must describe the accompanying version and
condition installation on publication without announcing a publication event.
Historical preparation records can remain historical. The current source is
not suitable for the requested final release freeze on that basis.

## Complete correction scope

Closeout accepts independent findings F1 and F2. The maintained APG116-derived
wording audit contains twelve surfaces; a corrected-source phase must inspect
all twelve, preserving already suitable conditional and historical wording:

| Audited surface | Required disposition for corrected source |
| --- | --- |
| `README.md` | Replace predecessor installation guidance and preparation status. |
| `release/v0.9.0-notes.md` | Preserve historical v0.9.0 wording. |
| `release/v0.10.0-notes.md` | Finalize accompanying-version wording and remove internal process prose. |
| `docs/distribution.md` | Finalize development status and predecessor installation guidance. |
| `docs/README.md` | Finalize version status and remove dispatcher/future-freeze process prose. |
| `docs/reference/cli.md` | Finalize development-interface wording. |
| `docs/reference/go-library.md` | Finalize development status and predecessor installation guidance. |
| `npm/README.md` | Replace predecessor package installation guidance. |
| `npm/templates/launcher/README.md` | Preserve suitable conditional publication wording and placeholders. |
| `npm/templates/platform/README.md` | Preserve suitable conditional publication wording and placeholders. |
| `testing/fixtures/external_consumer/README.md` | Finalize development qualification and predecessor consumer wording while preserving control lanes. |
| `testing/fixtures/xo_consumer/README.md` | Finalize development qualification and predecessor consumer wording while preserving control lanes. |

The executable owner is
`src/test/unit/python/agentic-praxis-grimoire/libexec/apg_python_publication.unit.test.py`.
Its `test_package_metadata_distinguishes_v0100_candidate_from_public_release`
and `test_audited_package_surfaces_have_durable_release_wording` currently require
the development-candidate wording, including predecessor public-version text.
The corrected-source scope must re-baseline those assertions to durable v0.10.0
consumer wording, conditional on publication without asserting publication has
occurred. Keep the complete twelve-surface audit, historical release wording,
template placeholders and maturity checks. The current wording is deliberately
tested development-candidate wording that has not been release-finalized;
changing documentation alone would fail its maintained gate. No test or source
correction is made in this blocked closeout.

## Plan findings

The wording finding is accepted as a construction blocker. The supplemental
Go ordinary/race/vet and npm launcher receipts, full-history public base with
complete tags and no extra local branches, direct distribution-module invocation,
separate archive epoch, owned process temporary root, exact browser skip counts,
explicit ADR inclusion and source-commit packet binding are accepted amendments
for any authorized reconstruction. They are requirements, not executed evidence.
The producer initially reported a clean selected source. Closeout dispositions
all five cumulative phase paths as phase-owned blocker/status evidence. Findings
F1, F2 and F5 expand this handback; F3 is satisfied by read-only exit observation;
F4 is corrected by placing APG133 after APG132 in the roadmap. No additional
substantive review was requested or performed.

## Boundary and deferrals

The task requires a corrected source commit and complete reconstruction upon a
public-source defect. This assignment freezes APG132 and does not authorize
silently selecting corrected source. No source correction, candidate patch,
release build, test qualification, operator executable, external reviewer, Git
staging, commit, push or publication occurred.

At closeout on 2026-09-10, read-only public ref inspection confirmed the required
public main and annotated v0.9.0 tag identities, with no v0.10.0 release branch
or tag. The public GitHub v0.10.0 release endpoint returned HTTP 404. This is an
exit observation, not a retrospective pre-build receipt or a registry audit;
no build occurred. Publicly visible release absence does not attest private draft
release state. This phase performed no public mutation.

Affected closeout verification covers record identity, local links in the two
APG133 records, the twelve-entry audit mapping, evidence JSON, roadmap order,
source preservation outside the five phase paths, and whitespace. Release,
package and runtime gates remain unrun because construction is blocked.

The dispatcher must disposition the source defect and obtain corrected-source
authority before construction resumes. APG132 readiness acceptance, ADR 0054,
Repo Map roadmap, maturity and debt remain unchanged. See
[exit 00178](../status/2026/09/10/00178-apg133-v0100-release-freeze-source-blocker-exit.md).
