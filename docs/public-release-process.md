# Public Release Process

## Purpose and boundary

APG develops in a private history and publishes a separate public history. A
public release is a complete projection of the committed publishable source,
not a copy of the development commit graph. Each public version adds one
squashed release commit whose sole parent is the previous accepted public
release. The build and check command is local-only: it does not contact a
remote, push, publish, or mutate its source or base.

APG12 establishes this process and validates disposable candidates. APG13 owns
individual skill maturity decisions. APG14 applies the accepted process to the
real v0.2.0 candidate, public repository mutation, tag publication, active
integration source update, and release closeout.

## Roles

- The **source** is a clean non-bare APG development repository. Its committed
  tree supplies the publishable files.
- The **base** is a clean non-bare checkout at the previous accepted public
  release. It supplies the candidate's sole parent and reachable public
  history.
- The **candidate** is a new local repository written to an explicitly empty,
  non-symlinked, non-overlapping output path.
- **Publication** is the separately authorized act of integrating and pushing a
  checked candidate. The APG12 command never performs it.

## Projection and policy

Every Git-tracked source path is publishable by default except a path under the
single `private/` boundary. Unsuitable material must move under that boundary
before release. The candidate must contain every projected path exactly once
with the same raw path, regular or symbolic-link type, executable mode, blob
bytes, and raw symbolic-link target. This exact bijection prevents silent
omission; the critical-path lists do not replace it.

[`release/public-surface.json`](../release/public-surface.json) is the strict
schema-version-1 policy. It fixes the canonical identity, sole exclusion,
critical owners, wrappers, helpers, licensing files, six skills, six discovery
links, test entrypoints, and validation categories. Code owns the accepted
schema and executable test commands. The policy cannot execute commands or
remove a projected path.

An optional publication-excluded check policy may add only sorted literal
confidentiality patterns. It cannot weaken another check and never enters the
candidate.

## Command surface

[`bin/apg-public-release`](../bin/apg-public-release) uses Python 3 and Git:

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

Exit `0` is success, exit `1` is release, repository, candidate, or policy
noncompliance, and exit `2` is invalid usage or an unsafe build invocation.

`manifest` reads committed Git objects and emits deterministic schema-version-1
text or canonical JSON. It reports one sorted projected entry per path with
mode, type, SHA-256, and symbolic-link target where applicable. It deliberately
omits private development commit and full-tree identities, so source and exact
candidate manifests are byte-identical.

`build` requires explicit SemVer without a leading `v`, a strict RFC3339
timestamp with offset, and an author name and email. It creates branch
`release/<version>`, commit subject `Release v<version>`, and annotated tag
`v<version>`. Author, committer, and tagger metadata use the supplied identity
and timestamp. Identical committed source, base, version, identity, and date
inputs produce identical projected trees, commits, and tag objects.

`check` is read-only. It proves exact projection equality, one-parent history,
the complete expected ref set, branch, commit and annotated-tag metadata,
clean status and ordinary index flags, deterministic
manifest, critical owners, skill-library structure, wrapper help and syntax,
configured unit and integration tests, Python compilation, Markdown and local
links, public-to-private independence, generic confidentiality, and licensing,
notice, contribution, and CLA presence.

## Candidate sequence

1. Confirm source and base are clean and at reviewed commits. The base must be
   exact public v0.1.0 or the HEAD of a strict tagged single-parent release
   chain rooted at exact public v0.1.0. The roles must be physically disjoint;
   source, base, and candidate may not self-compare or nest.
2. Review all tracked non-private files and the public policy.
3. Render and retain the deterministic manifest as release evidence.
4. Build into a new disposable output using fixed version, identity, and date.
5. Run `check` against that candidate.
6. Rebuild from the same inputs and compare tree, commit, annotated tag, and
   manifest.
7. Review the resulting candidate and evidence independently.
8. Hand the accepted candidate to the separately authorized publisher without
   pushing from this command.

The v0.1.0 release omitted the documented `bin/apg-project-skills` wrapper even
though its helper modules and documentation were present. The APG12 integration
suite constructs that malformed projection and requires `check` to reject it
for the missing executable and exact-tree mismatch.

## APG12A lineage and validation correction

The original APG12 command checked candidate history only relative to the
supplied base. APG12A additionally verifies the base itself. Exact public
v0.1.0, including the original lightweight tag ref rather than a peeled
same-target replacement, is the lineage root. Each later commit must have the
immediately prior release as its sole parent, exactly one matching
`v<semver>` tag, an exact
`Release v<semver>` subject, and all prior required tags. Merges, untagged
intermediates, retagged or truncated history, and a tag that does not resolve
to HEAD fail before output construction or candidate acceptance. The current
tree of every later base must also satisfy the strict schema-version-1 policy,
critical-path, private-exclusion, and public-symlink contracts.

Projection, policy, history, refs, tags, links, and metadata are checked
mechanically against the original clean repositories. Executable validation
then receives local disposable copies of the candidate and base. Wrapper help,
shell syntax, Python compilation, and configured tests run with isolated HOME,
XDG config/cache/data/runtime/state, temporary-directory, and bytecode roots;
the base environment variable names only the disposable base. Mutation of
either copy fails validation. Complete refs, index, status, HEAD, and tree
fingerprints prove the original source, base, and candidate remain unchanged.
The configured process `PWD` names the disposable candidate and ambient
`OLDPWD` is removed.

Trusted test code is not sandboxed from every same-user resource and may still
initiate network activity on its own. The release command itself adds no
network or push path, and the lineage proof is not publisher authentication.

## Rollback and failure recovery

Before publication, remove only the disposable candidate output after its
evidence is no longer needed; source and base require no rollback because the
tool does not mutate them. A partial build remains an isolated output and is
never accepted without a clean `check`.

After publication, rollback is a separate public-release decision. The
append-only history preserves the previous release as an explicit parent. Do
not force-rewrite public history or delete a published tag through this tool.

## v0.2.0 publication

APG14 builds v0.2.0 twice from one reviewed private release-source commit, exact
public v0.1.0 base, frozen RFC3339 timestamp, and verified maintainer identity.
The builds must have identical manifests, trees, commits, and annotated tag
objects. Independent candidate, public-diff, and active-integration-plan review
precede an atomic dry-run and one normal atomic push of only public `main` and
`v0.2.0`. A fresh checkout then repeats lineage, policy, configured tests,
licensing, confidentiality, link, and skill-library gates. Exact object
identities belong in private operational evidence rather than the projected
tree.

The existing public-backed integration updates only by fast-forwarding its
clean source checkout. Its aggregate link objects and raw targets remain
unchanged; no user-state migration or Codex configuration change occurs. Shell
validation cannot establish application discovery after the content update, so
a full restart and fresh-session smoke remain an external observation.

## Limitations

The checker does not decide semantic confidentiality, provenance sufficiency,
license interpretation, or publication fitness. Candidate tests execute trusted
APG code without a sandbox. Advisory path and repository checks do not defend
against a hostile same-user process. Reproducibility covers Git objects and
declared output, not incidental `.git` filesystem layout.
