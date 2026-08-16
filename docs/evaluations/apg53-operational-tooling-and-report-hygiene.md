# APG53 Operational Tooling and Report Hygiene

## Scope and outcome

APG53 starts from formal APG52 commit
`0c4dfe7706cc570ad5e7bfcf7c4f82eebbf0a1ff`, whose parent is selection-freeze
commit `92f01e663f610400604e415929c28f1da9d37e3c`. The result is **Complete —
shared-skills projection command added, report storage and project
identity corrected, and regenerable evidence-size policy enforced**.

APG53 does not reconstruct the Web/Node architecture, author a skill, publish
v0.5, or mutate a live Claude integration.

## Report evidence and cause

The historical APG52 managed report is an owner-only, single-link regular file
containing one complete Git-show record and one associated operational record.
Its 18,424,589 bytes regenerate exactly. The formal patch contributes
18,400,353 bytes; the three complete generated JSONL datasets contribute
18,194,578 bytes, or 98.88% of that payload. The limitation was tracked
artifact practice, not the complete report renderer, so rendering remains
unchanged.

## Shared command

The exact maintainer-supplied input was
`flatten-skill-symlinks`, SHA-256
`b8b9ef833465ba01485d635db7eb1cd7bda2b65b191c633952bfabe47d150c00`.
Its basename is retained. A thin `bin/flatten-skill-symlinks` launcher owns a
bounded maintained implementation under `libexec/`.

The command accepts one explicit source and destination, refuses overlap,
traversal, unsafe ancestors, unmanaged collisions, and ambiguous duplicate
names, and never executes source content. Exact owner-state, a destination
lock, immediate symlink revalidation, no-overwrite transactional replacement,
state-last updates, rollback, deterministic output, `--dry-run`, `--check`,
and owned cleanup support repeatable projection. Disposable APG-shaped and
other shared-skill roots were exercised against a disposable Claude-shaped
target; no live target changed. The reviewed Claude documentation does not
explicitly guarantee directory-symlink discovery, so this is filesystem
projection evidence rather than Claude-runtime recognition evidence. The
command is included in the current-development and future v0.5 public surface,
without publication.

## Report storage and project identity

`git-show-report`, `git-diff-report`, and `append-operational-report` now
default to:

```text
~/Documents/agent/reports/<project>/<ticket>.report.txt
```

An explicit `GIT_SHOW_REPORT_ROOT` remains exact and does not gain a `reports`
component. The intermediate default root is created privately and refused when
unsafe. Historical reports remain at the old default and are neither searched,
migrated, nor deleted.

Project identity removes all consecutive leading ASCII periods from the Git
root basename. Thus `.repo`, `..repo`, and `.repo.dev` become `repo`, `repo`,
and `repo.dev`; `repo.`, spaces, and non-ASCII text remain supported. `.`,
`..`, and `...` normalize empty and are rejected. Metadata, paths, and
diagnostics use the same identity.

## APG52 compaction and prevention

Before removal, APG53 reverified the accepted APG52 counts, hashes, and
byte-identical two-run result:

| Current-tree path | Records | Accepted SHA-256 |
| --- | ---: | --- |
| `corpus-artifacts.jsonl` | 4,612 | `d0a4e61b2ff87c304a3b71c888c4179cd8bea316ea6907212c0281a535eb5b19` |
| `corpus-exclusions.jsonl` | 4,365 | `99804eea8daa90c19f8c07c50e2aa3c60577d10b8966ce92ddbdb9a8d8828b88` |
| `corpus-measurements.jsonl` | 4,612 | `07cac27b9c8eec1ba3b534dbffcdb3423e52ba982a6b0e9646b691bbeaf29142` |

Those three complete derived datasets are absent from the APG53 current tree.
Compact inputs, summaries, hashes, samples, rights, tooling, and reproduction
records remain. A complete disposable regeneration from exact Git objects
matched every retained and removed accepted output. The tool now rejects
non-empty, symlinked, source-overlapping, or APG-contained output roots.
Historical objects remain in Git history.

The accepted size policy limits ordinary blobs to 262,144 bytes,
generated-derived blobs to 131,072 bytes, aggregate generated evidence to
524,288 bytes per change, and a text line to 65,536 bytes. Archives fail by
default and binary assets require exact reviewed exceptions. The checker
reports largest resulting and rewritten blobs, aggregate new and generated
bytes, largest line, and exceptions. An APG52-style generated control fails;
the APG53 staged result passes with no exception.

## Verification and disposition

Focused failing-first, unit, real-Git integration, complete unit/integration/
combined, configured Bats, compilation, help, release-candidate, identity,
Markdown/link, JSON, privacy, rights, whitespace, coverage, isolated dogfood,
and independent review gates pass. Public and active corrected v0.4.0 remain
unchanged.

ADR 0032 is Accepted. Development remains 28 canonical skills, 28 catalog
rows, 28 projections, fourteen stable and fourteen provisional, with 26
general routes, one ChatGPT-local route, and 27 checked edges. ADR 0031 remains
Rejected, all ten Web/Node candidates remain deferred, and React and Vitest
retain Policy A.

## Stop

No target Web/Node command, browser/HTML/accessibility work, readiness,
publication, deployment, live Claude integration mutation, or successor phase
began. No successor is authorized.
