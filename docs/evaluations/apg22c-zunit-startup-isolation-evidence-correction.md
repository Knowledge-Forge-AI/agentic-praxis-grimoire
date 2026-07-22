# APG22C ZUnit Startup-Isolation Evidence Correction

Phase ID: `APG22C`

## Outcome

Complete — ZUnit startup-isolation evidence corrected and exact support retained.

APG22C accepts APG22A and APG22B in substance, corrects the APG22B harness's
selected user-startup control, and retains [`zunit-test-profile`](../../skills/zunit-test-profile/SKILL.md)
unchanged for exactly ZUnit v0.8.2 with Zsh 5.9.2 in the tested environment.

## Reproduced defect

The APG22B harness supplied separate temporary `HOME` and `ZDOTDIR` roots but
installed its contamination sentinel under the temporary home. Removing `-f`
still left the sentinel absent because Zsh selected `.zshenv` under the
supplied `ZDOTDIR`. The original absence assertion therefore did not prove
selected user-startup isolation.

A disposable exact Zsh 5.9.2 diagnostic reproduced the ineffective control.
With the sentinel at the selected `ZDOTDIR/.zshenv`, the same unsuppressed
runtime loaded it, and the same runtime with `-f` suppressed it. The defect was
in the harness evidence rather than the ZUnit skill wording.

## Corrected evidence and exact matrix

The corrected harness installs the sentinel at the selected user-startup path,
requires an unsuppressed positive control to load it, requires a `-f` negative
control to leave it absent, and requires the named focused ZUnit test to
observe its absence inside the test process. Separate temporary home and
startup roots, credential-free construction, exact source builds, bounded
process groups, copied fixtures, fingerprints, and no-residue cleanup remain.

| Exact pair | Startup controls | Upstream result | APG result | Disposition |
| --- | --- | --- | --- | --- |
| ZUnit v0.8.2 + Zsh 5.3.1 | positive and negative pass | dependency probe times out with status 124 before suite execution | not run | unsupported on the tested environment |
| ZUnit v0.8.2 + Zsh 5.9.2 | positive, negative, and in-runner pass | 98/98 pass | 7/7 focused pass; expected adverse cases pass | exact verified pair |

The startup claim is limited to the selected user `.zshenv` under the recorded
invocations. It does not claim suppression or control of unavoidable platform
or global startup behavior. No version range, adjacent version, other platform,
or current-stable inference is made.

## Skill and APG22A dispositions

The ZUnit leaf, projection, catalog row, route, known-unmanaged entry, and
focused fixture semantics remain retained. All 48 frozen scenario dispositions
remain supported. The candidate correction count remains zero because APG22C
changes the harness and its regression test, not the skill.

A focused non-author APG22A review finds no new defect in
`composing-approved-roadmap-assignments`, ADR 0017, catalog-heading
compatibility, or current manager-assignment documentation. APG22A skill bytes
and all substantive dispositions remain unchanged.

## Resulting state and validation

Private development remains 19 canonical skills, 19 catalog rows, 19 relative
projections, 6 stable rows, 13 provisional rows, and 18 routable non-router
capabilities. Project, user, public-release, and active public-backed defaults
remain the six stable v0.2 skills under schema version 1.

The corrected exact-version harness, 43-test skill-library unit suite, all
configured repository suites, development and active checkers, record identity,
Python compilation, applicable shell syntax, command help, changed Markdown
links, privacy, durable references, modes, schemas, whitespace, staged checks,
and fresh non-author review pass. The complete configured gate contains 250
passing tests and two expected fixture skips.

## Boundary

APG22C changes no skill wording, maturity row, dependency, schema, public APG,
active integration, target repository, managed default, root guidance, private
router, or source repository. It runs no application smoke, Nix operation,
global installation, publication, or APG23 work.

APG23 may begin only after APG22C is committed, pushed, remote-equal, fully
reported, and followed by a full Codex application quit and relaunch into a
brand-new APG-rooted session.
