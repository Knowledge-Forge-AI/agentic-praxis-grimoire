# APG20 Go and Ruby Language Profiles Evaluation

Phase ID: `APG20`

## Outcome

Complete — Go and Ruby candidate evaluations closed; both profiles deferred.

APG19A completed its accepted disposition, identity checks, commit, push,
remote-equality check, and managed reports before APG20 began. APG20 evaluated
two independent candidates and reached these terminal dispositions:

| Candidate | Disposition | Applied corrections | Reason |
| --- | --- | ---: | --- |
| `go-language-profile` | `deferred-material-defect` | 1 | Final review found additional licensing, measurement, safety-boundary, and calibration defects. |
| `ruby-language-profile` | `deferred-material-defect` | 1 | Final review found additional semantic-response, lifecycle, compatibility, and calibration defects. |

The assignment allowed one bounded behavior-bearing correction per candidate.
Each candidate consumed that correction during shared design review. The later
material findings therefore required deferral rather than a second correction.
Neither candidate leaf or integration is retained. No new architecture decision
was required; ADR 0016 remains unallocated.

## Ownership and source boundaries

The Go candidate was evaluated for material Go-specific judgment about
structure, errors, context, interfaces, goroutines, channels, synchronization,
modules, public compatibility, reflection, `unsafe`, cgo, and subprocess
boundaries. The Ruby candidate was evaluated for material Ruby-specific
judgment about structure, exceptions, closures, shared state, dynamic dispatch,
metaprogramming, constants, callbacks, concurrency, gems, public compatibility,
serialization, and subprocess boundaries. Neither candidate would own generic
process procedure or action authority, and APG20 adds no generic static-,
dynamic-, or all-language profile.

Sources were inspected on 2026-07-21. Go evidence uses Go 1.26.5, the Go 1.26
specification, compatibility and memory-model documents, modules and
standard-library documentation, and first-party diagnostics. APG20A later
clarifies that ordinary Go website prose is generally CC BY 4.0 except where
noted, displayed code and Go source-distribution material use BSD terms, and
third-party modules retain their own licenses. Ruby evidence uses Ruby 4.0.6, Ruby 4.0 language,
core, standard-library, security, maintenance, and compatibility material, and
RubyGems/Bundler 4.0.16. Ruby is available under the Ruby License or 2-clause
BSD subject to file-specific exceptions; RubyGems/Bundler is dual-licensed
under MIT or Ruby-like terms. golangci-lint v2.12.2 and RuboCop 1.87 supplied
factual calibration only and are not mandated tools. No external or private
expression, code, or table structure was copied or adapted.

## Candidate design evidence

The private evaluation preserves proposed Green, Yellow, Orange, and Red bands,
fallback measurement rules, frozen scenarios, and bounded read-only samples.
Those proposals are calibration evidence only. They are not an implemented APG
contract and do not authorize a future candidate to skip fresh source review,
scenario review, or false-escalation testing.

Shared design review applied one correction to each candidate:

- Go concurrency breadth changed from raw goroutine or channel counts to
  independently changeable lifecycle, cancellation, shutdown, failure,
  communication, or synchronization ownership families.
- Ruby dynamic and callback breadth changed from raw occurrence counts to
  closed, owner-scoped mechanism or lifecycle families with overlap disclosed.

Final review then found additional behavior-bearing defects. The Go proposal
needed corrected documentation licensing, reproducible grouped exported-API
measurement, a nested-function rather than nested-scope local-binding boundary,
the full protected-data sink boundary, and corrected dogfood classifications.
The Ruby proposal failed to translate already-frozen Orange and Red scenario
expectations for bounded dynamic dispatch, shared mutable state,
thread/fiber/ractor lifecycle, and authorized public compatibility change into
its candidate response guide; it also needed corrected dogfood classifications.
Correcting the candidate leaf was not applied because it would be a second
candidate correction. The frozen expectations themselves were not rewritten.

## Read-only calibration result

No sampled source was built, tested, executed, or changed. The maintained Go
sample originally described as Green is Orange on complexity and decision
signals. The maintained Ruby sample originally described as Green/Yellow is
Orange on method span and direct public API breadth. Current upstream Go and
Ruby Red-size sources were not shown to be owner-classified legacy artifacts;
they therefore cannot demonstrate the legacy-minimal-fix scenario. Generated
sources retained their classified-artifact treatment. These findings invalidate
candidate acceptance but remain useful calibration evidence for a future phase.

## Resulting repository and distribution

Candidate leaves, projections, catalog rows, capability-map entries,
known-unmanaged entries, and focused candidate tests were removed after
deferral. Private development remains twelve canonical skills, twelve relative
checked projections, six stable process rows, six provisional rows, and eleven
routable non-router capability-map entries. The map and project, user, and
release state schemas remain version 1.

`apg-project-skills`, `apg-user-skills`, and public release continue to manage
exactly the six stable v0.2 process skills. Public v0.2.0 and the active
public-backed integration remain 6/6/6. Go and Ruby are not current-development
known-unmanaged skills because no canonical profile exists.

## Validation and review

The temporary candidate implementation passed its mechanical suite, but fresh
semantic and threshold review invalidated the claimed scenario and calibration
results. Mechanical success therefore did not establish candidate acceptance.
Final validation of the rolled-back twelve-skill resulting tree passed:

- 22 Bats report-tool cases after one non-reproducing concurrency-test retry;
- 25 skill-library, 8 release, and 8 user unit cases;
- 10 record-identity integration cases;
- 28 project, 58 checker, 32 release, and 39 user integration cases, including
  the environment-conditioned public-v0.1 cases without a skip;
- development checker text and JSON at 12/12/12 and fresh public-v0.2 checker
  text and JSON at 6/6/6;
- Python compilation, applicable Bash and Zsh syntax, and all command help;
- phase-ID, ADR, and exit validation at 15 ADRs, 30 exits, and 30 unique phase
  IDs, with ADR 0016 and exit 00031 independently next; and
- changed-file durable-hash/private-path scans and whitespace checks.

No Go or Ruby leaf remains, so Go and Ruby syntax or build-free parse checks are
not applicable to the resulting tree.

Independent Go, Ruby, and shared-threshold reviewers required deferral. Fresh
resulting-tree reviews cover router/catalog/distribution, semantic identity and
current documentation, the complete diff, and the accuracy of the Go, Ruby,
and shared disposition records. Worker results are evidence; the final
repository state and validation decide completion.

## Boundary

No root migration, private-skill decommission, dependency, plugin, Nix,
PostgreSQL, SQLite, ZUnit, manager-prompt capability, public release,
active-integration change, or application smoke occurred. APG23 and APG24
retain application-smoke ownership. No phase after APG20 is authorized; APG21
did not begin.

## Subsequent APG20A disposition

APG20A accepts this phase's deferrals and complete defect ledger without
rewriting APG20's terminal result. It corrects the recorded source,
measurement, semantic-response, and dogfood defects; retains both profiles as
provisional development skills; and records the corrected source-license
boundary above. APG20A also reproduces and corrects the report-lock race behind
the concurrency retry. APG20 remains the historical deferred evaluation;
APG20A owns the later implementation result.
