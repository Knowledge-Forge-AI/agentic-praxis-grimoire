# ADR 0009: Public Distribution and Reproducible Release Validation

## Status

Accepted

## Date

2026-07-20

## Acceptance authority

The human maintainer's APG12 assignment accepts this decision. It authorizes
private-development architecture, policy, dependency-free tooling, tests,
isolated dogfood, documentation, evidence, one private commit, and managed
reports. It does not authorize public or reference mutation, active user
integration mutation, a plugin, skill changes, maturity changes, APG13, or
APG14 publication.

## Context

Public v0.1.0 is one intentionally squashed public release commit. It preserved
the selected files exactly but omitted two then-publishable tracked paths,
including the documented executable `bin/apg-project-skills`, while retaining
that command's implementation modules and documentation. The release process
therefore had no mechanical invariant equating the public tree to the complete
publishable source tree.

The maintainer also uses a public-backed user integration. Current official
Codex documentation, inspected on 2026-07-20, documents repository discovery
under `.agents/skills` from the working directory through the repository root,
user discovery under `$HOME/.agents/skills`, supported symbolic-link targets,
non-merged duplicate names that may both appear, automatic change detection
with restart as a fallback, and plugins as the broader reusable-distribution
mechanism. APG12 needs a supported local user lifecycle without mutating the
legacy active integration or turning APG into a plugin.

## Decision

### Public projection

Every Git-tracked development path is publishable by default except a path
whose first component is `private`. A path unsuitable for publication must
move under `private/` before a release. No policy allowlist or ad hoc release
step may silently omit another tracked path.

The candidate tree and the committed source projection form an exact raw-path
bijection. Each path appears exactly once with the same Git object type, mode,
blob bytes, and raw symbolic-link target. Supported public modes are ordinary
files `100644`, executable files `100755`, and symbolic links `120000`.
Unsupported publishable types stop the build rather than disappearing.

Critical-path policy supplements the bijection. It detects deletion of an
owner from the development source itself; it does not define the public
projection. Public files and links remain independent of `private/`.

### Public history and reproducibility

Each public version appends one squashed release commit to the prior accepted
public history. v0.1.0 remains the first public commit. A candidate adds exactly
one commit whose sole parent is the accepted public base. The local candidate
uses branch `release/<version>` and tag `v<version>`; APG14 owns any final
public-branch integration.

The commit and annotated tag use the supplied author name, author email, and
strict RFC3339 release timestamp. The same source tree, public base commit,
version, identity, and timestamp produce the same projected tree, commit, and
tag object. This claim excludes incidental `.git` filesystem layout.

The builder never pushes, contacts a remote, mutates source or base, imports
private development history, or publishes. APG14 alone owns public mutation,
the real v0.2.0 candidate, and publication.

### Public policy

`release/public-surface.json` is a strict schema-version-1 public policy. It
records the fixed `private/` exclusion, canonical public identity, critical
owners, required wrappers and helpers, licensing and governance owners, six
canonical skills, six projections, test entrypoints, and fixed validation
categories. Arrays and keys are deterministic. It contains no private path,
private identity, credential, command array, shell snippet, or second exclusion
mechanism.

An optional publication-excluded check policy may add sorted literal
confidentiality patterns. It cannot remove paths, weaken checks, execute code,
or enter the candidate.

### Candidate command

`bin/apg-public-release` is a thin Python 3 command over a standard-library
helper and Git. Its public surface is:

```text
apg-public-release manifest [--source <path>] [--format text|json]
apg-public-release build --source <path> --base <path> --output <path> \
  --version <semver> --release-date <rfc3339> \
  --author-name <name> --author-email <email>
apg-public-release check --source <path> --base <path> \
  --candidate <path> --version <semver> \
  [--private-policy <path>] [--format text|json]
apg-public-release --help
```

The command requires clean non-bare source and base repositories, committed
policy bytes, ordinary index flags, explicit metadata, and a safe output. It
refuses self-comparing or nested repository roles and conflicting,
nonempty, symlinked, or unsafe output paths. Construction copies reachable
public-base objects and projected source blobs locally, writes an exact Git
tree through a temporary index, creates one commit and tag, and materializes
only the candidate. It never uses archive extraction, shell evaluation,
network operations, push, or source-provided commands.

`check` owns exact projection equality, modes, bytes, link targets, absence of
`private/`, critical paths, history, parent, subject, branch, tag, deterministic
manifest, clean status, skill-library validation, fixed command help and
syntax, configured repository tests, Markdown/local links, generic
confidentiality, licensing, notices, contribution, and CLA presence. Semantic
publication classification, provenance sufficiency, license interpretation,
and judgment-heavy confidentiality remain review-owned.

Exit `0` means success, `1` means source/candidate/policy noncompliance, and
`2` means malformed usage or an unsafe build invocation.

### User-scoped command

`bin/apg-user-skills` is a separate thin Python 3 command over a
standard-library helper and local Git queries:

```text
apg-user-skills list --source <public-checkout> [--format text|json]
apg-user-skills install --source <public-checkout> [--skills-root <path>]
apg-user-skills adopt --source <public-checkout> [--skills-root <path>]
apg-user-skills check [--skills-root <path>] [--repo <path>] \
  [--format text|json]
apg-user-skills update --source <new-public-checkout> [--skills-root <path>]
apg-user-skills rollback [--source <restored-public-checkout>] \
  [--skills-root <path>]
apg-user-skills uninstall [--skills-root <path>]
apg-user-skills --help
```

The default discovery root is `$HOME/.agents/skills`; `--skills-root` is an
explicit local override for tests or separately authorized roots. The command
never writes `~/.codex/config.toml`, a target repository, or a source checkout.

The tool validates the exact accepted public v0.1.0 identity or a clean tagged,
strict-policy-complete descendant with exactly six canonical skill leaves. It
installs six direct per-skill symbolic links. A strict
version-1 state at
`${XDG_STATE_HOME:-$HOME/.local/state}/agentic-praxis-grimoire/user-skills-v1.json`
records the exact skills root, current source path/version/tag/commit/tree and
skill hashes, previous source identity, six managed names, and created
container ownership. State and the persistent lock are mode `0600`; state is
written by atomic replacement while the separate lock inode remains stable.

Install owns only links it creates. Adopt requires all six exact compatible
links and does not claim their parent containers. Update preflights the complete
current installation, retains the prior source, replaces links, and commits
state last. Rollback requires the exact stored prior identity or an explicitly
supplied checkout with matching immutable identity. Uninstall removes only
state-proven exact links and only unchanged empty containers recorded as
tool-created. Unrelated skills remain untouched.

`check --repo` reports duplicate repository-scope canonical names as a warning
because official documentation says duplicates are not merged and both may
appear. It makes no precedence or invocation-source claim. Mutating success
states that Codex normally detects changes automatically and that a full
restart is the fallback when a change does not appear.

User-command exit `0` means success, `1` means source/state/ownership
noncompliance, and `2` means argument-parser usage failure.

### Current integration and successor boundary

The active public-backed integration remains accepted read-only evidence. Its
legacy aggregate-link shape is not normalized, adopted, or migrated in APG12.
The documented migration first proves the lifecycle in temporary roots and
requires separate authorization before changing active discovery state.

Direct user-scoped links do not make APG a plugin. APG13 alone owns individual
skill stability dispositions. APG14 alone owns the real public v0.2.0
candidate, active integration update, public branch and tag mutation,
publication, and release closeout.

## Alternatives considered

### Continue manual public copying

Rejected. Public v0.1.0 demonstrates that selected exact files can still omit
a required publishable owner.

### Permit arbitrary release exclusions

Rejected. Multiple omission mechanisms make the intended public surface
unobservable. Unsuitable material belongs under `private/` before release.

### Publish every tracked non-private path

Accepted. A complement rule plus exact bijection is smaller and safer than a
publication allowlist.

### Package a plugin now

Rejected. Plugins remain the broader distribution mechanism, but APG12 is
limited to a local public-sourced user integration.

### Retain only the project-local installer

Rejected as the complete distribution model. Project-local and user-scoped
links have different roots, state, ownership, duplication, and rollback.

### Copy skill directories

Rejected. Copies create a second source of truth and obscure update identity.

### Direct links without ownership state

Rejected. They cannot prove update, rollback, or uninstall authority.

### Direct links with user-local state

Accepted. Each link has an exact source and independent ownership proof while
unrelated user skills remain outside scope.

### Rewrite public history into a new root for every release

Rejected. It implies destructive public replacement and breaks the accepted
v0.1 lineage.

### Append one squashed commit per release

Accepted. Each public version remains compact while preserving release order
and an explicit rollback base.

### Combine user-global and project-local commands

Rejected. Their authority, discovery roots, state, and removal boundaries are
materially different.

## Consequences and limitations

- Exact projection and critical paths detect the v0.1 omitted-wrapper class.
- Candidate construction remains offline, local, deterministic, and
  non-publishing.
- Direct links require the recorded public checkout to remain available.
- Six link replacements are not one filesystem transaction; state-last updates
  make partial interruption observable and refuse ambiguous recovery.
- Advisory locking and path checks coordinate cooperative same-user operations;
  they are not a sandbox against a hostile same-user process.
- Executing candidate tests assumes trusted APG source. Fixed commands and
  isolated state reduce side effects but do not sandbox malicious test code.
- Public lineage and structural validation are mechanical integrity evidence,
  not a publisher signature or cryptographic authenticity proof.
- Mechanical checks cannot determine semantic confidentiality, provenance, or
  license interpretation.
- No skill content, projection, or maturity changes result from this decision.

## Subsequent correction: APG12A

APG12A preserves this decision but corrects four tooling defects that were not
fixed by the original APG12 commit. Release construction previously trusted any
clean caller-supplied base, later user sources could contain untagged
intermediate commits, configured validation executed in and could mutate the
original candidate or base, and an absent-state user `check` created a state
directory and lock before failing.

The corrected implementation has one shared mechanical lineage verifier. It
accepts v0.1.0 only by its exact commit, tree, and original lightweight tag-ref
identity. Every later release must be a single-parent,
one-commit-per-version chain from that root;
every commit has exactly one matching SemVer tag, later tags are annotated,
subjects match their tags, and prior release tags remain intact. The current
tree of every later checkout must also satisfy the strict public policy,
critical-path, private-exclusion, and public-symlink contracts. Release
`build`, release `check`, and user-source validation use the same verifier.

Mechanical checks remain against the original read-only roles. Help, syntax,
compilation, and configured tests execute in disposable candidate and base
repositories with temporary HOME, XDG, temporary-directory, and bytecode
state. Mutation of either copy is noncompliance, and complete source, base, and
candidate Git fingerprints must remain unchanged. User `check` opens only an
existing lock without creation and takes a shared nonblocking lock; mutating
commands retain the persistent exclusive lock.

This is mechanical lineage integrity, not cryptographic publisher
authentication. It changes no command, public-policy schema, user-state
schema, skill, projection, maturity, publication boundary, or APG13/APG14
ownership.
