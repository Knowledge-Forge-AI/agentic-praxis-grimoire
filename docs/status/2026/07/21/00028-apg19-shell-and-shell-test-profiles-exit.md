# APG19 Shell and Shell-Test Profiles Exit

## Disposition

Partial — Bash, Bats, and Zsh profiles implemented; ZUnit deferred

## Scope and outcome

APG18A completed its review, commit, push, remote-equality, and managed-report
gates before APG19 began. APG19 accepts ADR 0014, implements three provisional
profiles, and records an independent disposition for every evaluated candidate:

| Candidate | Disposition | Candidate corrections |
| --- | --- | ---: |
| `bash-language-profile` | `retained-provisional` | 1 |
| `bats-test-profile` | `retained-provisional` | 1 |
| `zsh-language-profile` | `retained-provisional` | 1 |
| `zunit-test-profile` | `deferred-source-or-version` | 0 |

Current ZUnit maintenance and runtime evidence does not support a truthful
current-stable-Zsh profile. Re-entry requires a current canonical release or
maintained successor with fresh supported-runtime verification, or separate
authorization for an explicitly legacy-only pinned profile.

## Ownership and thresholds

ADR 0014 keeps Bash and Zsh language semantics separate from Bats and the
reserved ZUnit test-harness ownership. Process, language, and test profiles
are selected independently, and none grants action authority. No generic
all-shell owner was adopted.

Each retained profile defines Green, Yellow, Orange, and Red bands across the
required structural signals. Bash reaches Red at 501 script lines, 41 commands
in one function or top-level region, 13 decision paths, nesting depth 5, 10
fixed positional parameters, 7 mutable shared-state domains, process breadth
8, or 4 responsibilities. Bats reaches Red at 601 test-file lines, 41 tests,
51 commands in one test body, 36 hook/bootstrap commands, 51 helper commands,
6 shared-state owners, 4 concurrent child groups or any unowned child, or 4
responsibilities. Zsh reaches Red at 501 script lines, 41 commands, 11 decision
points, nesting depth 6, 10 positional parameters, 10 option mutations, 10
mutable global parameters, autoload/module/hook breadth 11, external-process
breadth 10, or 4 responsibilities.

One Red signal remains Red. Related signals may raise the response, and two
materially coupled Orange signals in one owner are presumptively Red. Artifact
classification and narrowly bounded coherent-matrix exceptions prevent
line-count-only decisions. Existing Red legacy artifacts may receive the
smallest safe fix without meaningful growth or a new responsibility.

## Evaluation, correction, and review

Each retained candidate passed twelve shared scenarios, twelve domain-specific
scenarios, every exact threshold boundary, and the coupled upper-Orange case.
Each received one bounded correction after shared design review. The
corrections closed the combined-signal loophole, made measurements
reproducible, added Bats status and pipeline false-confidence handling, and
tightened unsupported Zsh size thresholds. No retained candidate required a
second wording correction.

Read-only dogfood covered seven cases per retained profile across APG and at
least one other maintained repository: Green, Yellow, Orange, Red or near-Red,
legacy minimal fix, classified or coherent-large artifact, and semantic safety
or compatibility. No sampled source or test was changed or executed as part of
dogfood.

Independent reviews covered each retained profile's semantics and thresholds,
cross-profile ownership and pairing, router/catalog/distribution integration,
and the complete resulting diff. Material Bats evidence and focused-test
findings were corrected without changing the accepted candidate wording and
were accepted on re-review.

## Integration and validation

Private development contains twelve canonical skills, twelve relative checked
projections, six stable process rows, six provisional rows, and eleven routable
non-router capability-map entries. The map and lifecycle state schemas remain
version 1. Project/user lifecycle and public-release behavior still manage
exactly the six stable v0.2 skills. Public v0.2 and active integration remain
unchanged at 6/6/6.

Resulting-state validation passed:

- 22 Bats report-tool cases;
- 25 skill-library, 8 release, and 8 user unit cases;
- 28 project, 58 checker, 32 release, and 39 user integration cases, including
  both exact public-v0.1 compatibility cases without a skip;
- development checker text and JSON at 12/12/12 and fresh public-v0.2 checker
  text and JSON at 6/6/6;
- Python compilation, applicable Bash syntax, and six command-help checks;
- profile scenarios, read-only dogfood, source/provenance review, Markdown,
  local links, privacy, public/private separation, sequence, modes, schemas,
  protected hashes, complete-diff review, and Git whitespace checks; and
- unchanged reference, RepoMap, public, active-integration, and fresh public
  checkout states.

All nine preexisting skill files, including the workflow router, remain
byte-identical to the APG18A baseline. No root guidance was removed, no private
skill was decommissioned, and no dependency, plugin, public release, active
integration, project/user default, or state-schema change occurred.

## Deferred work and next authority

Application discovery and explicit-use smoke were intentionally not run.
APG23 owns aggregate v0.3 readiness smoke, and APG24 owns public-candidate and
active-integration release-preparation smoke. ZUnit remains deferred under the
source/version condition above.

No Go, Ruby, Nix, PostgreSQL, or SQLite profile and no
roadmap-to-manager-prompt skill was implemented. APG20 did not begin and is not
authorized by this phase.

## External disposition requested

Accept APG19 as a partial terminal outcome with Bash, Bats, and Zsh retained
provisionally and ZUnit deferred. Preserve the APG23/APG24 smoke deferral and
await separate maintainer authorization for APG20 or any other successor work.

## Subsequent APG19A correction

APG19A later accepted this substantive partial outcome and corrected one
reproduced Bats fallback-count defect for the runner-supported comment function
form. The correction changes no APG19 threshold, ownership, maturity, catalog,
ZUnit, distribution, or smoke disposition. ADR 0015 and exit 00029 record the
later semantic-identity policy and reconciliation.

## Subsequent APG22B disposition

APG22B later retains a provisional ZUnit profile only for exact ZUnit v0.8.2
with Zsh 5.9.2 in the tested environment. The exact Zsh 5.3.1 pair is
unsupported. The APG19 partial outcome remains historically accurate.
