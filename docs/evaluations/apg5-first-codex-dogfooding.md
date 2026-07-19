# APG5 First Codex Dogfooding

## Observation

- **Fresh-session date:** 2026-07-18
- **Repository class:** APG private working repository
- **Harness class:** Codex macOS application with repository skill discovery
- **Discovery:** six of six repository-scoped APG skills available
- **Skill:** `reviewing-and-verifying-repository-work`
- **Task class:** read-only integration and completion-evidence review
- **Selection mode:** explicit
- **Trigger result:** applicable
- **Artifact:** evidence-backed discovery disposition
- **Terminal result:** pass

The human maintainer supplied and accepted the application observation. APG5
independently reproduced the locally observable repository facts, including the
clean expected project state, canonical skill files, and repository discovery
links. Shell inspection cannot independently reproduce the application UI or
its explicit invocation event.

This is APG's first real explicit-use dogfooding observation. It does not
measure automatic selection and does not promote the skill beyond
`provisional`.

## Evidence categories

The accepted observation covered the active instruction chain, clean repository
state, six-skill availability, canonical-to-projection identity, exact relative
symlink targets, target containment, readable canonical leaves, matching
frontmatter names, absence of duplicates or broken links, and an explicit
review-skill result.

Superpowers remained globally installed and visible in the broader registry.
It was not invoked or followed and did not obtain effective workflow authority.
APG's repository-local behavioral policy remained effective; no mechanical
plugin disablement is claimed.

## Commit-message investigation

APG4A's structured commit body contains literal backslash-`n` sequences in the
commit object. Normal Git rendering preserves them, and the managed Git report
preserves the same commit-message payload byte for byte. The report executable
did not introduce or escape the sequences.

The cause was caller-side construction: a multiline value was serialized and
its escaped representation was interpolated into a shell command. Shell quoting
then passed the backslash characters literally to Git. Historical evidence was
left unchanged. The narrow correction adds commit-message construction and
self-verification guidance to the manager-worker reporting contract; no report
executable changed.

## APG5 skill-use decisions

Positive use:

- `debugging-systematically` localized the newline symptom through competing
  hypotheses and exact-byte evidence.
- `planning-repository-work` organized the accepted multi-stage phase and its
  integrated closeout.
- `composing-bounded-worker-assignments` bounded the required fresh internal
  finished-diff review.
- `reviewing-and-verifying-repository-work` governed final evidence review and
  the completion claim.

Material non-triggers:

- `implementing-with-test-discipline` did not apply because no executable
  defect or behavior change was found.
- `designing-significant-changes` did not apply because no consequential
  interface, report-format, or ownership decision remained unresolved.

No skill procedure required correction. The phase makes no automatic-selection,
comparative, stable-maturity, production-readiness, or decommission-readiness
claim.

## Limitations and next evidence

One explicit observation in APG does not establish universal trigger quality,
automatic invocation, causal advantage, or repeated real-project reliability.
Serena was not exposed in the accepted fresh-session smoke, although that did
not prevent the bounded application observation.

The next evidence should be natural, bounded use of APG skills in another real
repository, including proportionate non-trigger decisions and review of
authority, privacy, ceremony, and project-owned parameters. Another synthetic
activation gate is not required.
