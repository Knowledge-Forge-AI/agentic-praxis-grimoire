# APG5 First Codex Dogfooding and Commit-Message Hygiene Exit

## Phase identity

- **Phase:** APG5
- **Date:** 2026-07-18
- **Exit sequence:** `00008`
- **Disposition:** Complete — first explicit dogfooding observation recorded and hygiene corrected
- **Controlling decision:** ADR 0003, Accepted and unchanged

## Accepted discovery result

The human maintainer supplied and accepted a fresh Codex macOS application
observation: all six repository APG skills were discovered, root instructions
were loaded, `reviewing-and-verifying-repository-work` was explicitly selected,
and its evidence-backed discovery disposition was `pass`. Locally observable
repository and projection facts were independently reproduced during APG5.
Shell inspection does not reproduce the application UI or explicit invocation
event.

The observation is APG's first real explicit-use dogfooding evidence:

- repository class: APG private working repository;
- task class: read-only integration and completion-evidence review;
- selection mode: explicit;
- trigger result: applicable;
- artifact: evidence-backed discovery disposition; and
- terminal result: pass.

No authority, privacy, ceremony, or skill defect was observed. Automatic
selection was not evaluated.

## Commit-message investigation and correction

APG4A's commit object contains literal backslash-`n` sequences in its structured
body. Raw Git plumbing, normal Git renderings, and exact-byte comparison with the
managed report establish that the report faithfully preserved the malformed
historical message. Caller-side serialization created escaped newline text and
shell quoting passed it literally to Git.

No report executable, shared helper, interface, framing rule, or format changed.
The single correction adds focused commit-message construction and
self-verification guidance to the manager-worker reporting contract. APG4A was
not rewritten.

## Skill-use decisions

Positive uses:

- `debugging-systematically`: exact-layer diagnosis and correction selection;
- `planning-repository-work`: dependent APG5 phase and closeout units;
- `composing-bounded-worker-assignments`: one required read-only independent
  finished-diff review; and
- `reviewing-and-verifying-repository-work`: final evidence and completion
  review.

Material non-triggers:

- `implementing-with-test-discipline`: no executable defect or behavior change;
- `designing-significant-changes`: no unresolved consequential design or ADR
  decision.

Skill correction count: zero. Documentation hygiene correction count: one.

## Independent review and validation

The fresh non-author reviewer initially returned `accept with follow-up`: no
blocker or material finding and one minor correction to the private exact-byte
wording. The correction now states that the stored payload's three line feeds
are the two line feeds separating subject from body plus the final terminator;
the report script strips its additional formatter line feed. Corrected-candidate
re-review returned `accept` with no remaining blocker, material finding, minor
finding, unrelated change, or regression against the 18 review criteria.

The integrated validation passed:

| Check | Result |
| --- | --- |
| Markdown headings, fences, and local links | Passed across 59 Markdown files and 116 local links. |
| Public confidentiality and public-to-private dependencies | Passed across 31 publishable Markdown files. |
| Canonical skills and Codex projections | Passed for six of six with frozen hashes and exact Git symlink modes and targets. |
| ADR and exit sequences | Passed through ADR `0003` and exit `00008`. |
| Read-only source state | Passed; clean and locally equal to its fetched tracking ref. |
| `git diff --check` | Passed. |
| `git diff --cached --check` | Passed. |
| Source tests | not run; documentation and evidence only. |

## Maturity, Superpowers, and limitations

All six skills remain `provisional`. One explicit observation does not establish
automatic invocation, comparative advantage, statistical reliability, stable
maturity, production readiness, or decommission readiness.

Superpowers remains globally installed and reference-only for APG. It did not
govern APG5. No plugin state changed, and the decommission gate remains false.
No additional Codex harness projection is needed.

## Next boundary

The next recommended evidence is natural, bounded APG skill use in another real
repository, including positive and non-trigger observations. Another synthetic
invocation gate is not required. This exit does not authorize another
implementation phase, promotion, decommissioning, publication, or license
decision.

## Subsequent correction

APG6 corrected this record's archive placement from `2026/07/19/` to
`2026/07/18/`, the local calendar date encoded in APG5's introducing commit
committer timestamp. The correction changed the declared date and inbound links
without changing APG5's outcome, evidence, or disposition.
