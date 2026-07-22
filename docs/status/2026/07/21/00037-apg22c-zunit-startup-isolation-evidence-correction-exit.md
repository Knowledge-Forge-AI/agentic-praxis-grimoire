# APG22C ZUnit Startup-Isolation Evidence Correction Exit

Phase ID: `APG22C`

## Disposition

Complete — ZUnit startup-isolation evidence corrected and exact support retained

## Scope and outcome

APG22C reproduces that APG22B placed its startup sentinel under a disposable
home while tested processes selected a separate startup directory through
`ZDOTDIR`. The sentinel remained absent even without `-f`, so the original
control did not prove selected user-startup isolation.

The corrected harness places the sentinel under the selected `ZDOTDIR`,
requires an unsuppressed positive control to load it, requires `-f` to suppress
it, and requires the focused ZUnit test process to observe its absence. This
proves the selected user `.zshenv` boundary only; platform and global startup
behavior is not claimed as controlled.

The corrected exact matrix retains ZUnit v0.8.2 with Zsh 5.9.2 after 98/98
tagged upstream tests, 7/7 focused tests, expected adverse cases, bounded
process cleanup, unchanged fingerprints, and no-residue cleanup. ZUnit v0.8.2
with Zsh 5.3.1 remains unsupported because its independent dependency probe
times out with status 124. No version range or other-platform claim is made.

The ZUnit skill bytes remain unchanged and the candidate correction count
remains zero. A focused non-author APG22A review preserves ADR 0017,
`composing-approved-roadmap-assignments`, catalog-heading compatibility, and
current manager-assignment documentation without a correction.

## Resulting repository and distribution

Private development remains 19 canonical leaves, 19 relative projections, 19
catalog rows, 6 stable rows, 13 provisional rows, and 18 routable non-router
capability-map entries. The six-skill v0.2 project, user, public-release, and
active public-backed integration contracts remain unchanged under schema
version 1.

## Validation and review

The corrected harness, 48 frozen ZUnit dispositions, 250 configured repository
tests with two expected fixture skips, development and active checkers, record
identity, compilation, applicable shell syntax, command help, changed Markdown
links, privacy, durable references, modes, schemas, whitespace, staged checks,
and fresh non-author defect, compatibility, semantic, APG22A, integration,
documentation, identity, and complete-diff reviews pass.

Current evaluation, roadmap, provenance, release-scope, language-profile,
project, user, release, historical subsequent-disposition, and status records
describe the resulting tree before commit. No tracked record uses an internal
commit hash as phase or state identity.

## External state and restart boundary

The public, reference, RepoMap, active integration, and private source
repositories preserve their pre-phase states. APG22C performs no application
smoke, public or active mutation, target mutation, global installation, Nix
operation, root cutover, private decommission, APG23 work, or successor work.

APG23 is authorized only after this phase is committed, pushed, remote-equal,
fully reported, followed by a full Command-Q application quit, and submitted
in a brand-new session rooted in the APG private development repository.
