# APG12A Public Lineage and Read-Only Validation Correction

## Disposition

APG12A is a narrow forward correction to accepted ADR 0009. It retains exact
projection of every tracked non-private path, one squashed public commit per
release, deterministic local construction, separate project and user
ownership, schema-version-1 policy and state, the v0.1 omitted-wrapper
regression, and the APG13 and APG14 boundaries.

The original APG12 commit did not contain this correction. Four subsequent
reproductions showed that an unrelated clean repository could be accepted as a
release base, an untagged intermediate commit could be accepted as a later user
source, configured validation could mutate the original base or candidate, and
an absent-state user `check` could create a persistent state directory and
lock.

## Corrected contracts

One shared verifier now treats exact public v0.1.0 commit, tree, and original
lightweight tag-ref identity as the release root. Later history must be a
complete linear sequence of single-parent release commits. Each commit has
exactly one matching SemVer
tag, later tags are annotated, subjects match tags, and every preceding release
tag remains intact. Every later current tree also satisfies the strict public
policy, critical-path, private-exclusion, and public-symlink contracts. Release
build, release check, and user source validation use the same result. Unrelated,
retagged, truncated, merged,
untagged-intermediate, subject-mismatched, and current-tag-mismatched histories
fail before release output or user mutation.

Mechanical release checks read the original source, base, and candidate.
Executable validation runs only in locally reconstructed disposable candidate
and base repositories with isolated HOME, XDG, temporary-directory, and Python
bytecode roots. Mutation of either copy fails. Complete HEAD, tree, ref, index,
index-flag, and status fingerprints prove that original repositories remain
unchanged on success and failure.

Configured processes receive the disposable candidate as both their working
directory and `PWD`; ambient `OLDPWD` is removed so original repository paths
are not inherited through those variables.

User `check` computes expected paths without creating them. It requires an
existing safe state directory and persistent lock, opens the lock without
creation, and uses a shared nonblocking advisory lock. Missing, malformed, or
locked state fails without replacement, cleanup, or new persistent paths.
Mutating commands retain their exclusive persistent lock.

Read-only state access requires the existing state directory to retain mode
`0700`; an overpermissive directory is rejected unchanged.

## Evidence and boundaries

Failing-first integration cases captured every reported violation before the
production correction. The corrected release suite contains eight unit and
thirty-two integration tests; the user suite contains eight unit and
thirty-nine integration tests. The complete checker, report-tool, and
project-lifecycle suites remain required, together with reproducible candidate
and isolated user-lifecycle dogfood.

The correction adds no command, option, dependency, plugin, registry, daemon,
policy version, state version, skill, projection, or maturity change. All six
skills remain `provisional`. The public and reference repositories, active
user integration, and RepoMap are read-only comparison surfaces. No public
release is constructed or published by this phase.

Mechanical lineage is not cryptographic publisher authentication. Trusted test
code is isolated from the original repositories and normal user state but is
not sandboxed against every same-user resource and can initiate its own network
activity. Semantic confidentiality, provenance sufficiency, licensing
interpretation, and publication fitness remain review responsibilities.

APG13 and APG14 have not started and require separate human authorization.
