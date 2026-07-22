# APG22B Version-Bounded ZUnit Profile

Phase ID: `APG22B`

## Outcome

Complete — version-bounded ZUnit profile implemented.

APG22B retains [`zunit-test-profile`](../../skills/zunit-test-profile/SKILL.md)
provisionally for exactly ZUnit v0.8.2 with Zsh 5.9.2. No version range is
claimed. ZUnit v0.8.2 with Zsh 5.3.1 is explicitly unsupported on the tested
environment because its runner dependency probe did not complete.

## Source, rights, and compatibility

The evaluation refreshed the ZUnit v0.8.2 release, tagged source, MIT license,
documentation, runner, assertions, hooks, configuration, discovery, output,
upstream tests, and historical CI; Revolver v0.2.4 under MIT; and the official
Zsh 5.3.1 and 5.9.2 sources, release notes, and manuals under the Zsh
distribution terms. APG copies no upstream expression and adds no runtime
dependency.

One unprivileged disposable arm64 Darwin harness built both exact Zsh releases
in temporary prefixes, supplied a temporary credential-free home and XDG
environment, suppressed user startup files, built ZUnit from its exact tag,
and cleaned its source, work, and installation roots.

| Exact pair | Upstream result | APG result | Disposition |
| --- | --- | --- | --- |
| ZUnit v0.8.2 + Zsh 5.3.1 | runner dependency probe timed out before suite execution | not run | unsupported on the tested environment; excluded |
| ZUnit v0.8.2 + Zsh 5.9.2 | 98/98 pass | 7/7 focused pass; expected risky, assertion-failure, and invalid-discovery cases pass | exact verified pair |

The focused contract covers exact runtime identity, recursive discovery,
bootstrap, per-test setup and teardown, startup isolation, status/output/line
capture, fixed argument vectors, temporary directories, owned child cleanup,
version conditioning, risky tests, failure status, invalid test files, and no
residue. Official Zsh detached signatures were available; no OpenPGP verifier
was available in the harness environment, so signature validation is not
claimed.

## Ownership and thresholds

The leaf owns ZUnit-specific runner, discovery, assertions, hooks,
configuration, output, fixtures, isolation, lifecycle, and structural
judgment. It leaves Zsh semantics to `zsh-language-profile`, generic work to
the applicable process owner, and project commands, versions, dependencies,
authority, exceptions, validation, and rollback to the repository.

| Signal | Green | Yellow | Orange | Red |
| --- | ---: | ---: | ---: | ---: |
| Test-file physical lines | `<= 150` | `151–300` | `301–500` | `>= 501` |
| Tests per file | `<= 8` | `9–15` | `16–24` | `>= 25` |
| Commands in one test body | `<= 12` | `13–20` | `21–35` | `>= 36` |
| Setup/teardown/bootstrap span | `<= 25` | `26–50` | `51–80` | `>= 81` |
| Helper function span | `<= 20` | `21–35` | `36–50` | `>= 51` |
| Mutable shared fixture/state domains | `<= 3` | `4–6` | `7–10` | `>= 11` |
| Cleanup-owned children/jobs | `<= 1` | `2–3` | `4–5` | `>= 6` |
| Independent responsibilities | `1` | `2` | `3` | `>= 4` |

Measurements are syntax-aware and distinguish physical lines, runner-
recognized declarations, commands, lifecycle spans, shared-state domains,
simultaneous owned children, and responsibilities. Generated, fixture,
compatibility, and data artifacts are classified first. Three coupled Yellow
signals normally justify Orange, two coupled Orange signals over one owner are
presumptively Red, and one Red remains Red. No level grants authority.

The tagged upstream suite's 33 files and 98 tests remain Green by file and
test-count defaults. APG's five public-safe fixture files and nine declarations
also remain Green. Earlier read-only maintained examples span Green and Yellow
by line count without false Orange escalation. Semantic Red independently
stops unsupported pairs, false-passing status, unresolved runner/discovery,
order dependence, startup or host mutation, process leaks, protected output,
dynamic evaluation of untrusted input, unauthorized destructive action, and
unaccepted crisis growth.

## Frozen scenarios and disposition

All 48 frozen compatibility, trigger, runner, discovery, assertion, output,
fixture, lifecycle, structural, and pairing scenarios pass against the exact
5.9.2 matrix and the explicit unsupported-runtime stops. Fresh non-author
compatibility, semantic, and threshold/integration reviews accept the resulting
candidate. Candidate correction count is recorded in the publication-excluded
review evidence.

The resulting development tree contains 19 canonical leaves, 19 relative
projections, 19 catalog rows, 6 stable rows, 13 provisional rows, and 18
routable non-router capability-map entries. The map and all lifecycle schemas
remain version 1. The six managed v0.2 project, user, and public-release skills
remain unchanged. No root or private guidance is removed or decommissioned.

## Validation and boundary

Focused skill-library, checker, and project-lifecycle suites pass. Complete
repository, checker, identity, compilation, syntax, help, Markdown, link,
privacy, mode, schema, whitespace, staged-diff, and review evidence is recorded
in [exit 00036](../status/2026/07/21/00036-apg22b-version-bounded-zunit-profile-exit.md).

APG22B runs no application smoke, Nix operation, target-repository test outside
the authorized disposable ZUnit harness, public release, active-integration
mutation, root cutover, private decommission, or APG23 work. Aggregate pre-
release smoke remains deferred because APG23 has not begun.

## Subsequent APG22C disposition

APG22C reproduced that the APG22B startup sentinel was outside the user startup
path selected by the supplied `ZDOTDIR`, invalidating the original startup-
isolation evidence. The corrected harness requires a loading positive control,
a suppressing `-f` negative control, and sentinel absence inside the focused
ZUnit test process.

The corrected exact rerun retains the 98/98 upstream and 7/7 focused results
for ZUnit v0.8.2 with Zsh 5.9.2, preserves the Zsh 5.3.1 dependency-probe
timeout and unsupported disposition, and passes process, fingerprint, and no-
residue gates. The ZUnit skill remains unchanged, so its candidate correction
count remains zero. APG22C records the forward correction without rewriting
the historical APG22B collection.
