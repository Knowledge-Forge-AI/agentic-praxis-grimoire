# APG20 Go and Ruby Language Profiles Exit

Phase ID: `APG20`

## Disposition

Complete — Go and Ruby candidate evaluations closed; both profiles deferred

## Scope and outcome

APG19A completed every predecessor gate before APG20 began. APG20 evaluated
independent Go and Ruby profile candidates. Each candidate received one bounded
design correction and then failed final review on additional material defects.
The assignment prohibited a second behavior-bearing correction, so both
candidates are `deferred-material-defect`.

No candidate leaf or integration is retained. No new architecture decision was
required; ADR 0016 remains available. The phase uses semantic source versions
and phase-local evidence IDs, and no tracked record uses a project commit hash
as durable identity.

## Candidate findings

The Go candidate's first correction replaced raw goroutine/channel counting
with independent concurrency-ownership families. Final review then required
additional corrections to documentation licensing, grouped exported-API
measurement, local-binding scope, the protected-data sink boundary, and
dogfood classifications. The maintained sample is Orange rather than Green,
and the current upstream Red-size source was not shown to be owner-classified
legacy code.

The Ruby candidate's first correction replaced raw dynamic/callback occurrence
counting with owner-scoped mechanism and lifecycle families. Final review then
found that the candidate response guide did not implement already-frozen
Orange and Red expectations for bounded dynamic dispatch, shared mutable state,
thread/fiber/ractor lifecycle, and authorized public compatibility change; it
also required corrected dogfood classifications. The maintained sample is
Orange rather than Green/Yellow, and the current upstream Red-size source was
not shown to be owner-classified legacy code.

These findings are behavior-bearing and were not applied. Proposed thresholds,
measurement rules, scenarios, and dogfood remain publication-excluded
calibration evidence, not implemented APG guidance.

The unaccepted Go proposal used file-line bands of 400/700/1,000, callable
statement bands of 20/35/50, complexity bands of 5/10/20, decision bands of
5/9/16, nesting bands of 2/3/5, parameter bands of 4/6/9, local-binding bands of
10/15/20, exported-API bands of 15/30/50, concurrency-ownership bands of 2/4/7,
and responsibility-family bands of 1/2/3 before Red. The unaccepted Ruby
proposal used file-line bands of 250/400/600, method-span bands of 15/25/40,
complexity bands of 5/10/15, decision bands of 4/8/12, nesting bands of 2/3/5,
parameter bands of 3/5/8, local-binding bands of 8/12/16, public-API bands of
8/15/24, dynamic-family bands of 0/1/2, callback-family bands of 1/3/5, and
responsibility-family bands of 1/2/3 before Red. These bands are preserved only
to make the evaluated proposal reproducible; no repository behavior adopts
them.

## Resulting repository and distribution

The resulting private-development tree remains at twelve canonical skills and
projections, six stable process rows, six provisional rows, and eleven routable
non-router capability-map entries. Project, user, and public release commands
continue to manage exactly the six stable v0.2 skills. Public v0.2 and active
integration remain 6/6/6. State schemas remain version 1. No existing maturity
changes.

## Validation and review

The temporary candidate implementation passed mechanical checks, but those
checks did not establish semantic correctness. Fresh Go, Ruby, and shared
threshold reviews found the material defects above and required deferral.
After candidate removal, the resulting twelve-skill tree passed 22 Bats cases
after one non-reproducing concurrency-test retry; 25 skill-library, 8 release,
and 8 user unit cases; and 10 identity, 28 project, 58 checker, 32 release, and
39 user integration cases. The environment-conditioned public-v0.1 cases ran
without a skip.

Development checker text and JSON pass at 12/12/12; fresh public-v0.2 checker
text and JSON pass at 6/6/6. Python compilation, applicable Bash and Zsh syntax,
all command help, changed-file durable-hash/private-path scans, and whitespace
checks pass. Record identity passes at 15 ADRs, 30 exits, and 30 unique phase
IDs; ADR 0016 and exit 00031 are independently next. No Go or Ruby leaf remains,
so language syntax or build-free parse checks are not applicable.

Reference, RepoMap, public, active-integration, private-source, and dogfood
repositories remain unchanged. No target source was executed, built, tested, or
modified.

## Deferred work and next authority

A future separately authorized phase may reconsider either candidate from the
current source baseline and must address the recorded defects before retention.
Application discovery and explicit-use smoke remain intentionally deferred to
APG23 and APG24. No root guidance was migrated, no private skill was
decommissioned, and no public release, dependency, plugin, state-schema change,
other profile family, or manager-prompt capability was implemented.

No phase after APG20 is authorized by the current assignment. APG21 did not
begin.

## External disposition requested

Accept APG20 as `Complete — Go and Ruby candidate evaluations closed; both
profiles deferred`, preserve the twelve-skill private-development catalog and
six-skill public v0.2 lifecycle, preserve APG23/APG24 smoke deferral, and stop
without beginning APG21.

## Subsequent APG20A disposition

APG20A preserves this exit as APG20's truthful historical disposition. It uses
the complete defect ledger as its corrected baseline, retains both profiles as
provisional development skills after independent acceptance, and reproduces
and corrects the report-lock race behind APG20's concurrency retry. APG20A does
not retroactively change the APG20 outcome or correction accounting.
