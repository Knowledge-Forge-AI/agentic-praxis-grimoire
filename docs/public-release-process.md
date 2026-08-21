# Public Release Process

<!-- APG-CANDIDATE-STATE: css-language-profile retained-provisional -->

The marker above is the mechanical current-state authority. Bounded
contradiction diagnostics cover only their frozen vocabulary; arbitrary prose
still requires human review.

## Purpose and boundary

APG develops in a private history and publishes a separate public history. A
public release is a complete projection of the committed publishable source,
not a copy of the development commit graph. Each public version adds one
squashed release commit whose sole parent is the previous accepted public
release. The build and check command is local-only: it does not contact a
remote, push, publish, or mutate its source or base.

APG12 establishes this process and validates disposable candidates. APG13 owns
individual skill maturity decisions. APG14 applies the accepted process to
v0.2.0. APG24 applies it to the nineteen-skill v0.3.0 release and the
source-specific lifecycle contract accepted by ADR 0019.

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
schema-version-1 current-development policy. It fixes the canonical identity,
sole exclusion, critical owners, wrappers, helpers, licensing files,
thirty-nine skills, thirty-nine discovery links, test entrypoints, and
validation categories for current development. Code separately owns immutable
historical v0.1.0 through v0.5.0 surfaces: v0.3.0 remains nineteen skills and
nineteen discovery links, corrected v0.4.0 remains twenty-eight, and public
v0.5.0 remains thirty-three. Exact digests pin the v0.4.0 and v0.5.0 policy
surfaces, and versioned exclusion sets reject later owners. The policy cannot
execute commands or remove a projected path.

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

The current-development public candidate also owns
`flatten-skill-symlinks`, `install-global-skills`, `apg-check-change-size`,
their maintained Python helpers, mirrored tests, and
`testing/apg-change-size-policy.json`. Exact projection makes those paths
future v0.5 candidate content; APG53 and APG54 do not publish a v0.5 release.
Versioned policy reconstruction excludes all APG53 and APG54 owners from the
immutable historical v0.4 surface.

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

APG16 through APG19 add the provisional router, synthesis, Python, Bash, Bats,
and Zsh profiles to private development without authorizing a v0.3 release;
ZUnit remains deferred. APG20A adds corrected Go and Ruby profiles to private
development without adding a public leaf. APG21 likewise adds provisional
PostgreSQL and SQLite profiles only to private development and defers Nix. The
schema-version-1 policy's six critical skill and projection entries remain the
accepted v0.2 release contract; exact projection would still include every
committed public path, but a future v0.3 release phase must make an explicit
distribution, critical-policy, user-lifecycle, and rollback disposition before
publication. Those phases do not weaken the existing lists or silently treat
repository consistency as release readiness.

APG19A adds semantic record-identity validation to the exact projected public
surface and corrects the private-development Bats counting guidance. It does
not broaden the six critical v0.2 skills, authorize a v0.3 candidate, or mutate
the published repository. Candidate validation composes both the skill-library
and record-identity checkers.

APG20A likewise leaves the six-skill schema-version-1 public contract unchanged.
Its retained provisional candidates do not authorize a candidate, publication,
or active-integration mutation.

APG21 also leaves the six-skill schema-version-1 public contract unchanged. Its
two retained profiles do not authorize a candidate, publication, or active-
integration mutation.

APG21A retains corrected Nix only in private development and applies one
bounded PostgreSQL correction. It does not add a critical public skill, change
schema version 1, authorize a candidate, or mutate public or active integration.

APG22 leaves the same release contract unchanged. Its 35-case explicit-use
dogfood is not fresh-session application discovery, release readiness, or
publication authority. The recorded migration and scope proposals do not add a
critical skill, widen schema version 1, build a candidate, modify public or
active integration, or authorize private-router replacement. A manager-
assignment candidate evaluation and an explicit ZUnit scope decision remain
pre-APG23 work; APG24 remains the earliest public-candidate owner.

APG22A retains the approved-roadmap manager-assignment leaf only in private
development. It adds no critical public skill, changes no schema-version-1
policy, and authorizes no candidate, publication, or active-integration
mutation.

APG22B retains one provisional ZUnit profile only for exact ZUnit v0.8.2 with
Zsh 5.9.2 in the tested environment; the exact Zsh 5.3.1 pair is unsupported.
It adds no critical public skill and changes no candidate, public checkout,
active integration, or six-skill schema-version-1 contract. The pre-APG23
manager-assignment and ZUnit objectives are terminal. APG23 still requires
separate authorization, and APG24 remains the earliest public-candidate owner.

APG22C corrects the ZUnit harness's selected user-startup evidence and retains
the same exact support disposition. It changes no critical public skill,
candidate, public checkout, active integration, release policy, or schema-
version-1 contract.

APG23 completes the fresh-session readiness gate. All thirteen v0.3 skills are
`include-v0.3`; eight are stable and five remain truthfully provisional. The
phase builds no candidate and changes no critical v0.2 list, public checkout,
active integration, release policy, or schema-version-1 contract. APG24 remains
the earliest public-candidate and publication owner.

APG24 accepts ADR 0019 and updates the current schema-version-1 policy to the
exact nineteen APG23-included skills and projections. Retaining the schema
number is supported by explicit variable-set validation; it does not make the
old six-name current policy valid. Historical v0.2.0 remains validated against
its source-declared six-skill policy and immutable release identity. Historical
v0.3.0 has an independently frozen nineteen-skill policy, while v0.4.0 is the
current development surface. Malformed or unsupported public identities fail
closed rather than inheriting the current inventory.
Release inclusion remains independent of the fourteen-stable/five-provisional
catalog maturity split.

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
validation cannot establish application discovery after the content update.
The maintainer subsequently completed the requested full restart and
fresh-session smoke and reported that it passed.

## v0.3.0 publication

APG24 builds v0.3.0 twice from one reviewed private release-source commit,
exact public v0.2.0 base, one frozen RFC3339 timestamp, and verified maintainer
identity. Identical manifests, trees, commits, annotated tags, refs, and
metadata are required before an atomic dry-run and one normal atomic push of
only public `main` and `v0.3.0`. A fresh checkout repeats the complete lineage,
policy, test, lifecycle, licensing, confidentiality, link, catalog, map, and
projection gates.

The release contains nineteen skills, fourteen stable rows, five provisional
rows, and eighteen non-router routes. Public v0.1.0 and v0.2.0 remain unchanged.
The active public-backed source advances only by exact fast-forward, preserving
its aggregate links and ownership. The personal router remains installed for
an external source-qualified shadow smoke; publication does not authorize its
decommission or a successor phase.

APG24A subsequently records the maintainer-reported successful fresh-session
shadow and the personal-router decommission performed under separate human
authority. Focused live inspection confirms that public and active v0.3.0 and
all three public release tags remain unchanged. This later disposition closes
the external observation; it does not alter the APG24 publication record or
release procedure.

## v0.4 architecture boundary

ADR 0022 and APG30 support nested canonical ownership for ChatGPT-manager
leaves with flat Codex projections in current-development candidates.
Recursive allowed-owner, catalog-path, lifecycle, manifest,
projection-target, and historical-release tests preserve nested leaf bytes,
modes, support files, and raw link targets. Immutable v0.1.0 through v0.3.0
policy remains direct-child and version-bounded. APG30 validates only a
disposable local current-development candidate; it does not authorize or
perform v0.4.0 publication.

ADR 0021 also requires a later public projection to include the shared Python
reporting core and thin adapters only after report conversion and cross-platform
parity are accepted. Architecture documentation is not a critical-path or
release-policy mutation.

APG27A satisfies the report-core adoption condition. APG28 remains Partial.
APG28A adopts the corrected current-development pytest runner, dependency
declaration, coverage configuration, strict inventory, shared helpers, and
mirrored test owners. Configured current tests include required unit and
integration owners. Validation directly invokes the required Bats and mirrored
pytest paths in a sanitized environment, without trusting a caller-controlled
recursion guard. Nested release fixtures remain bounded by their explicit test
policy. Immutable v0.2.0 and v0.3.0 policy arrays retain their historical Bats
and flat-Python identities.

APG41 exercises the current-development v0.4.0 projection twice in disposable
local Git candidates and smokes one candidate through isolated user and
project lifecycle roots. The reproducible fields, current public inventory,
historical policy, privacy, licensing, provenance, relative projections, and
cleanup pass. Its terminal
`ready-for-publication-with-provisional-limitations` disposition is a
pre-release gate only. It creates no public tag, release, push, signing event,
announcement, active installation, or publication authority.

## v0.4.0 publication

APG42 builds v0.4.0 twice from one formal release-source commit, exact public
v0.3.0 base, one frozen RFC3339 timestamp, and the maintainer identity verified
from prior public commit and annotated-tag evidence. Identical manifests,
trees, commits, annotated tags, refs, metadata, modes, and raw symbolic-link
targets are required before one atomic dry-run and one normal atomic push of
only public `main` and `v0.4.0`.

The release contains twenty-eight skills, fourteen stable rows, fourteen
provisional rows, twenty-six general routes, one ChatGPT-local direct route,
and no mandatory chain. APG42 publishes no private development history and
changes no skill procedure or maturity row. Public v0.1.0 through v0.3.0
commits and tags remain unchanged.

A distinct live-remote context and fresh public clone verify the reviewed
objects and complete release gates before the aggregate-owned active source
advances by exact fast-forward. No schema-version-1 direct-link state, aggregate
link recreation, or Codex configuration change occurs. Mechanical discovery
does not establish refreshed client invocation; that observation remains
truthfully pending when no safe fresh client is available.

APG43 is a separately recorded, one-time exception for a release-blocking
identity defect in `NOTICE`. Its explicit leases and replacement of the named
development and v0.4.0 objects do not alter this normal process into a reusable
force-push policy. Future releases return to append-only publication.

APG49 is development-only validation. Its terminally deferred matryer/is
candidate adds no current release-policy path and does not change the
corrected public or active v0.4.0 surface. No v0.5 candidate construction,
publication, or deployment is implied.

APG55 is also development-only. It hardens the already selected
current-development `install-global-skills` transaction and its tests without
changing the immutable historical v0.4.0 projection policy, public refs,
active checkout, or publication authority. A later candidate includes the
corrected resulting source through the ordinary current-development manifest.

APG59 rejects the CSS candidate after corrected-state review and adds no
current release-policy path. Historical v0.4.0 reconstruction, public refs,
the active checkout, and publication authority remain unchanged.

APG62 rejects the separately authored APG61 CSS candidate after independent
sixty-case validation, one permitted correction, and fresh corrected-state
review. It adds no current release-policy path or release owner. Historical
v0.4.0 reconstruction, public refs, the active checkout, and publication
authority remain unchanged.

## Limitations

The checker does not decide semantic confidentiality, provenance sufficiency,
license interpretation, or publication fitness. Candidate tests execute trusted
APG code without a sandbox. Advisory path and repository checks do not defend
against a hostile same-user process. Reproducibility covers Git objects and
declared output, not incidental `.git` filesystem layout.

APG66 adds the retained Markdown leaf, projection, specification, coverage,
public-safe fixture, focused test contract, and unit/integration entrypoints
only to current-development release ownership. Explicit APG66 exclusion sets
keep every one of those paths out of immutable historical v0.4 reconstruction;
the frozen v0.4 surface digest and public/active objects remain unchanged.

APG75 similarly adds the retained TypeScript leaf, projection, specifications,
TypeScript 7 fixture, support contracts, and maintained unit/integration tests
only to current-development ownership. `APG75_V05_*` exclusion sets keep every
APG75 owner out of historical corrected v0.4 reconstruction. This is current
development integration, not readiness, publication, or active deployment.

APG75A modifies existing APG75-excluded TypeScript owners and adds only bounded
current-development evaluation, exit, runner-prerequisite, and runner-test
owners. Exact APG75A exclusions keep those new paths out of historical
corrected v0.4 reconstruction. The current compiler prerequisite is not needed
to reconstruct v0.4. Published and active corrected v0.4.0 remain immutable;
APG75A performs no readiness, publication, or deployment.

APG77D adds the retained CSS leaf, projection, specification, navigation
coverage, target-first fixture, semantic scenarios, known-debt owner, current
support contracts, maintained tests, accepted ADR, and APG76 through APG77D
public phase records only to current-development ownership. `APG77D_V05_*`
exclusion sets keep every current-only CSS owner out of corrected historical
v0.4 reconstruction. Published and active corrected v0.4.0 remain immutable;
APG77D performs no readiness, publication, or deployment.

APG79E adds the retained JavaScript leaf, projection, specifications, APG-owned
fixture, semantic scenarios, source-role association, known-debt association,
support contracts, maintained tests, accepted ADR, and APG78 through APG79E
public phase records only to current-development ownership. `APG79E_V05_*`
exclusion sets keep every current-only JavaScript owner out of corrected
historical v0.4 reconstruction. The private Test262 source-role record and
managed reports remain excluded by their standing boundaries. Published and
active corrected v0.4.0 remain immutable; APG79E performs no readiness,
publication, or deployment.

APG81H adds the retained Node.js leaf, projection, specifications, APG-owned
fixture, semantic scenarios, support contracts, maintained tests, accepted
ADR, and APG80 through APG81H public phase records only to current-development
ownership. `APG81H_V05_*` exclusion sets keep every current-only Node owner out
of corrected historical v0.4 reconstruction. Published and active corrected
v0.4.0 remain immutable; APG81H performs no readiness, publication, or
deployment.

APG82 adds `bin/apgr`, the `agentic_praxis_grimoire` package, package metadata,
exact package-owned skill resources, APGR configuration/report/response/context
owners, and their maintained tests only to current-development v0.5 ownership.
`APG82_V05_*` exclusions keep every new APG82 owner out of corrected historical
v0.4 reconstruction. `src/agentic_praxis_grimoire/VERSION` is the sole package
version resource and setuptools reads that exact file dynamically. Local wheel
and sdist construction in APG82 is qualification evidence only; APG84 owns any
final exact release build and publication.

APG83 proves the approved v0.5 deployment split. The public Git release is the
versioned authority for complete skill bodies, projections, and repository
maintenance owners. The PyPI `agentic-praxis-grimoire` distribution is the
versioned authority for the checkout-independent `apgr` runtime and exact
packaged skill metadata. Qualification binds every installed metadata row to
the corresponding skill in the exact reconstructed public release; consumer
commands do not silently depend on a development checkout. A downstream
adapter can therefore consume the exact versioned pair reproducibly.

Python release qualification builds the wheel and sdist in two disjoint clean
roots under one controlled release environment. Historical v0.5 keeps its
exact release epoch `1700000000`. v0.6 uses the separately frozen epoch
`1787270400`, representing 2026-08-21 00:00:00 UTC. The maintained normalizer
accepts only those two named release epochs and requires `SOURCE_DATE_EPOCH` to
equal the selected value; the v0.6 bundle owner always selects `1787270400`.
This preserves historical reconstruction without silently reinterpreting the
v0.5 epoch. The repository-maintenance wrapper deliberately has no installed-
consumer `apgr` route.
The normalizer is part of the publication procedure, not a comparison-only
filter: the normalized sdist is the release artifact. It accepts only
canonical relative safe regular-file and directory members (including PAX long
names, but excluding `./` aliases), emits ordered PAX gzip/tar bytes, clears
input PAX headers, and fixes ownership, regular-file mode `0644`, directory mode
`0755`, timestamps, and output-file mode `0600`. Both final wheel and normalized
sdist must match by exact filename, contents, metadata, and SHA-256 in the same
Python and linked-zlib release environment. APG90 owns the v0.6 publication
build and handoff; actual public GitHub and PyPI finalization remains separately
evidenced when it is outside dispatcher Git authority.

The normalizer accepts only a trusted locally built setuptools sdist and reads
that bounded release artifact in memory. The v0.5 and v0.6 package manifests contain no
executable-intended member; forcing regular members to `0644` is therefore part
of this release contract. A future manifest that adds executable content must
change this contract and its tests before publication.

APG84 makes that qualification contract the publication path.
`bin/apg-build-python-release-bundle` builds in two disjoint roots, invokes the
maintained normalizer on each raw sdist, validates exact cross-format metadata,
independently re-normalizes each selected sdist to prove its canonical bytes,
requires byte and mode equality, writes canonical `SHA256SUMS`, and selects one
directory containing only the final wheel, normalized sdist, and checksum
manifest. The trusted local input is the exact reviewed release reconstruction;
the operator binds its public Git identity and artifact metadata before upload.
GitHub Release upload consumes only that directory.

The v0.6 PyPI workflow runs only for a published GitHub Release and downloads
the triggering release's exact three asset IDs. It rejects any tag, filename,
asset count, or checksum mismatch before supplying only the verified wheel and
sdist directory to PyPA Trusted Publishing. The checked-in action identity is
PyPA `gh-action-pypi-publish` v1.14.2 at immutable commit
`dc37677b2e1c63e2034f94d8a5b11f265b73ba33`. The workflow binds tag `v0.6.0`
and exactly the v0.6 wheel, normalized sdist, and `SHA256SUMS`. Release
publication and immutable GitHub/PyPI readback remain external operational
evidence rather than tracked self-attestation.

APG87 adds the JSX and React leaves, projections, tests, fixture, ADR,
evaluation, and exit only to current-development audit ownership through
`APG87_V06_*` sets. Historical v0.1 through v0.4 surfaces remain excluded from
every APG87-only owner, and published/active v0.5.0 remains unchanged. This
current-development inventory update is not a version advance, release
candidate, publication, deployment, or remote push.

APG88 adds the MDX and Astro leaves, projections, tests, fixture, ADR,
evaluation, and exit only to current-development audit ownership through
`APG88_V06_*` sets. Historical v0.1 through v0.4 surfaces remain excluded from
every APG88-only owner, and published/active v0.5.0 remains unchanged. This
current-development inventory update is not a version advance, release
candidate, publication, deployment, active projection mutation, or provider
Git publication.

APG89 adds its composition fixture, evaluation, and exit only to
current-development audit ownership through `APG89_V06_CRITICAL`. Historical
v0.1 through v0.5 surfaces remain excluded from every APG89-only owner. Its
later supervisory review accepted the exact candidate with C0/H0/M0/L0
findings and terminalized the phase as `READY_FOR_APG90`; the historical APG89
commit remains unchanged. This readiness evidence is not a version advance,
named release candidate, publication, deployment, active projection mutation,
or provider Git publication.

APG90 makes the policy explicitly versioned: v0.5.0 reconstructs the digest-
pinned thirty-three-skill historical surface and rejects all APG86-APG90
owners, while v0.6.0 selects the thirty-nine-skill current surface and release
records. Public construction remains a normal single-parent release from the
live v0.5.0 line. When public Git/tag/GitHub/PyPI operations are outside the
dispatcher boundary, APG90 stops at an exact same-phase operator handoff and
does not claim publication.
