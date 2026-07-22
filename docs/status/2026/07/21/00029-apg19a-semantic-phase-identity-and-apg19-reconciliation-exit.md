# APG19A Semantic Phase Identity and APG19 Reconciliation Exit

Phase ID: `APG19A`

## Disposition

Complete — semantic phase identity adopted and APG19 reconciled

## Scope and outcome

APG19A independently rechecked APG19 and accepts its substantive partial
outcome: ADR 0014, separate Bash, Bats, Zsh, and reserved ZUnit ownership,
three retained provisional profiles, the ZUnit source/version deferral,
calibrated thresholds and combined signals, semantic Red stops, read-only
dogfood, twelve-skill development integration, six-skill public v0.2 lifecycle,
unchanged maturity, and deferred application smoke.

APG19A accepts ADR 0015 and adds the normative phase/record identity guide.
Phase IDs are globally unique semantic identifiers assigned before commit and
never reused. ADR and exit numbers are independently allocated and unique only
inside their own namespaces; numeric equality across them is valid. Tracked
public and private records use semantic phase, decision, exit, release, source,
and phase-local evidence IDs. Exact Git identities remain in managed reports
and transient verification output.

Implementation, current owners, evaluation, exit, applicable ADR, and indexes
were finalized before commit. Post-commit Git and operational reports do not
substitute for that precommit consistency.

## APG19 correction

| Candidate | APG19A disposition | Forward corrections |
| --- | --- | ---: |
| `bash-language-profile` | Accepted; byte-identical | 0 |
| `bats-test-profile` | Accepted after correction | 1 |
| `zsh-language-profile` | Accepted; byte-identical | 0 |
| `zunit-test-profile` | `deferred-source-or-version`; no leaf | 0 |

The Bats audit reproduced a material test-count defect. bats-core v1.13.0
recognizes a supported comment function form that the prior fallback could
exclude as a comment, understating the 13/25/41 count bands. One bounded forward
correction now counts runner-recognized native and supported comment forms,
excludes incidental static text, and does not authorize evaluating a target
Bats file merely to count tests. The complete shared, Bats-specific,
exact-boundary, composite, and read-only dogfood evidence passed after the
correction. No threshold or other Bats semantic changed.

Bash required no correction. Zsh required no correction. ZUnit v0.8.2 remains
the latest canonical release, later upstream evidence remains insufficient for
current stable Zsh, and the ADR 0014 re-entry condition remains truthful.

## Durable identity and current owners

APG19 dogfood and candidate digests were replaced with stable phase-local case
IDs. External sources use semantic releases when available. Unversioned Agent
Skills, experimental Karpathy, and later ZUnit observations use stable
phase-local source IDs, public locators, inspection dates, and explicit
mutability limitations rather than invented immutability.

Root and private instructions, project model, manager-worker protocol,
provenance, skill authoring, ADR/status indexes, README, roadmap, catalog,
language-profile contract, project/user/release integration, APG19 records, and
APG19A records describe the actual resulting state. A focused changed-file and
current-owner scan found no remaining internal or maintainer-project hash used
as a durable tracked-document identity.

## Mechanical checks and integration

`apg-check-record-identity` is a dependency-free read-only command with text and
schema-version-1 JSON output. It verifies exact exit indexing, independent ADR
and exit uniqueness, case-insensitive canonical phase uniqueness, new-record
path/index/H1/field agreement, allocation expectations, and independently
computed next values. It confirms fifteen ADRs, twenty-nine exits, twenty-nine
unique phase IDs, next ADR 0016, next exit 00030, APG19A allocated, and APG20
available.

The public-release audited surface includes the command, helper, test, ADR,
guide, help, compilation, and validation category. The public release schema
remains version 1. Private development remains twelve canonical skills,
twelve projections, six stable and six provisional catalog rows, and eleven
routable non-router map entries. Project and user lifecycle defaults and the
six critical v0.2 release skills remain unchanged.

## Validation and review

Failing-first Bats wording and identity-command evidence was preserved. The
resulting tree passed:

- 22 Bats report-tool cases;
- 25 skill-library, 8 release, and 8 user unit cases;
- 10 focused record-identity integration cases;
- 28 project, 58 checker, 32 release, and 39 user integration cases, including
  both exact public-v0.1 compatibility cases without a skip;
- development checker text and JSON at 12/12/12 and fresh public-v0.2 checker
  text and JSON at 6/6/6;
- record-identity text and JSON with APG19A allocated and APG20 available;
- Python compilation, applicable Bash syntax, and seven command-help checks;
- Bats correction scenarios, APG19 profile rechecks, Markdown, local links,
  privacy, modes, schema, stale-current-state, semantic-source, sequence,
  complete-diff, staged-diff, and whitespace checks; and
- unchanged reference, RepoMap, public, active-integration, and dogfood source
  states.

Fresh non-author policy/record, semantic profile, integration, and complete
resulting-diff reviews accepted the corrected tree after all material findings
were resolved.

## Deferred work and APG20 gate

No application discovery or explicit-use smoke was run. APG23 owns aggregate
v0.3 readiness smoke; APG24 owns public-candidate and active-integration
release-preparation smoke. No root guidance was removed, no private skill was
decommissioned, no public release occurred, and no external repository or
integration was mutated.

No Go, Ruby, Nix, PostgreSQL, SQLite, ZUnit, or roadmap-to-manager-prompt skill
was implemented in APG19A. Under the maintainer's two-phase authorization,
APG20 may begin only after this phase completes independent review, identity
checks, commit, push, remote equality, and schema-valid managed reports. No
phase after APG20 is authorized.

## External disposition requested

Accept APG19A as `Complete — semantic phase identity adopted and APG19
reconciled`. After every post-commit APG19A closure gate passes, proceed directly
to the independently reviewable APG20 Go and Ruby profile phase without running
application smoke or requesting another disposition.

## Subsequent APG22B disposition

APG22B later retains a provisional ZUnit profile only for exact ZUnit v0.8.2
with Zsh 5.9.2 in the tested environment. The exact Zsh 5.3.1 pair is
unsupported. APG19A's identity and reconciliation outcome remains unchanged.
