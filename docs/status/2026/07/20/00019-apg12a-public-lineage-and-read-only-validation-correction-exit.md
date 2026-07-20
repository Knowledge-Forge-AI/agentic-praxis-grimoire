# APG12A Public Lineage and Read-Only Validation Correction Exit

## Disposition

Complete — public lineage and read-only validation corrected.

APG12 remains accepted in substance. APG12A is a forward correction to its
tooling and evidence, not a replacement architecture. It retains ADR 0009,
exact non-private projection, one squashed commit per public release,
deterministic local construction, separate user ownership, the v0.1
omitted-wrapper correction, and the APG13 and APG14 boundaries.

## Reproduction and root cause

The APG12 implementation was reproduced accepting an unrelated clean base and
an untagged intermediate commit in later user-source history. A successful
configured test could dirty the original base while release `check` returned
success. A configured test could also leave the original candidate dirty on a
noncompliant result, and absent-state user `check` created a persistent state
directory and lock.

The release tool validated history only relative to the caller-supplied base
and executed configured code in original repositories. The user tool validated
only ancestry and the current release tag, and its read path reused the
creating exclusive mutation lock.

## Corrected behavior

One immutable shared lineage result anchors release bases and user sources to
exact public v0.1.0. Every later commit is the sole tagged release successor of
the preceding release; merges, untagged intermediates, retagged or truncated
history, subject mismatch, missing prior tags, and disagreement between HEAD
and its release tag fail closed.

Executable candidate validation uses locally reconstructed disposable
candidate and base repositories plus isolated HOME, XDG, temporary-directory,
and bytecode roots. Dirty copies fail precisely. Complete Git fingerprints
prove that the original source, base, and candidate remain unchanged.

User `check` creates no state directory, lock, state file, or link. A managed
installation is checked under an existing shared nonblocking lock opened
without `O_CREAT`; mutating lifecycle operations retain the exclusive
persistent lock.

## Validation and review

Failing-first tests captured the four original violations. The corrected
surfaces contain eight release unit tests, thirty-two release integration
tests, eight user unit tests, and thirty-nine user integration tests. The
complete checker, report-tool, project-lifecycle, candidate reproducibility,
v0.1 omission, user lifecycle, syntax, help, compile, Markdown, link,
confidentiality, sequence, file-mode, and Git gates are the terminal validation
set. Separate final reviewers examined public-lineage and release-isolation,
user-lifecycle, and the complete diff. Their findings added failing-first
coverage for raw v0.1 tag identity, ambient working-directory isolation,
read-only state-directory permissions, and strict policy completeness of every
later base; each correction remained inside the accepted APG12 architecture.

The selected process skills are `debugging-systematically`,
`implementing-with-test-discipline`, and
`reviewing-and-verifying-repository-work`.
`planning-repository-work` organized the dependent correction, and
`composing-bounded-worker-assignments` applies only to the three final review
assignments. `designing-significant-changes` is a non-trigger because ADR 0009
and all ownership boundaries remain accepted.

## Unchanged boundaries and limitations

Public-policy schema version 1 and user-state schema version 1 are unchanged.
No `SKILL.md`, checked-in projection, maturity state, CLI surface, dependency,
plugin, registry, daemon, report tool, or publication behavior changed. All six
skills remain `provisional`. The public and reference repositories, active
user integration, RepoMap, and retired Superpowers state remain outside the
mutation scope.

Lineage verification proves local mechanical continuity, not cryptographic
publisher identity. Trusted configured code is separated from the original
repositories and ordinary user state but is not a complete hostile-process
sandbox. Semantic confidentiality, provenance, licensing, and publication
fitness remain review-owned.

## Artifacts and next authority

The publishable correction evaluation, corrected ADR and guides, APG12
subsequent-correction notes, this exit, and the strict public-surface index own
the public record. Exact reproductions, commands, fingerprints, test output,
and independent-review details remain publication-excluded.

External review is requested to **accept APG12A as Complete — public lineage
and read-only validation corrected; retain APG12's accepted projection and
release architecture, exact public v0.1.0 root, strict tagged linear later
history, isolated disposable configured validation, genuinely read-only user
checking, unchanged schema versions, exactly six unchanged provisional skills
and projections, unchanged external and active integration state, and the APG13
and APG14 boundaries; authorize no successor phase automatically**.

APG13 and APG14 have not started. Either requires a separate human assignment.
