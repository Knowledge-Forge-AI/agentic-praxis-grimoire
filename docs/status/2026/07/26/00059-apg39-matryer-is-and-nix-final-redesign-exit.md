# APG39 matryer/is and Nix Final Redesign Exit

Phase ID: `APG39`

Status: **Complete — final matryer/is and Nix replacement candidates
authored from APG38 corrected-state defects; Codex integration pending**

Date: 2026-07-26

## Outcome

APG39 accepts APG38 as a complete integrated phase, reverifies the exact
primary sources, closes the three APG38 corrected-state defects — registered
nested wrapper attribution, relaxed-mode count escalation, and sandbox
platform defaults — and authors final replacement candidates for the two
deferred profiles with frozen scenario families, corrected specifications,
structural counterexamples, one Proposed ADR, and a complete
publication-excluded Codex integration handoff.

```text
candidate leaves authored:
  2

matryer-is-test-profile:
  authored-pending-independent-review, 24 frozen APG39-IS families

nix-test-profile:
  authored-pending-independent-review, 40 frozen APG39-NIX-TEST families

integrated current skills:
  27

catalog/routes/projections/tests:
  unchanged / not added

go-test-profile:
  unchanged and provisional

go-cmp-test-profile:
  unchanged and provisional

go-testing-stack:
  remains rejected and absent

ADR 0025:
  Rejected

ADR 0026:
  Accepted and still controlling

ADR 0027:
  Proposed

public and active v0.3.0:
  unchanged
```

## Authoring evidence

Every behavior-bearing fact was reverified on 2026-07-26 against the exact
canonical sources: matryer/is tag `v1.4.1` (newest upstream tag), Nix tag
`2.35.1` (newest upstream release), and the Nixpkgs/NixOS 26.05 line at the
exact APG38-pinned commit. The Nix sandbox default is stated separately and
exactly for Linux and FreeBSD from the implementation conditional and
release notes, with a recorded discrepancy against the setting's stale
descriptive text and with the actual project configuration controlling over
every default. All 64 APG37 predecessor families and every APG38 correction
family map to APG39 successors. Both structural models are categorical with
named-risk escalation and recorded counterexamples.

The review is an adversarial author self-review with one coherent final
correction pass; it makes no retention prediction. A later separately
authorized Codex phase (APG40) must independently review both candidates,
convert 64 scenarios into executable fixtures, run exact-version and
source probes, apply at most one correction cycle per candidate,
disposition each independently, decide ADR 0027, and integrate retained
candidates atomically.

## Validation

Authoring-safe checks only: clean fetched-equivalent APG38 base at the
exact mainline object; exact branch identity; authorized write scope; two
unique candidate names; required headings; complete APG38 defect closure;
scenario counts 24 and 40 with continuity and complete predecessor mapping;
no stack artifact; ADR 0025 Rejected, ADR 0026 Accepted and unchanged, ADR
0027 Proposed; source, rights, and version completeness; structural
counterexample evidence; copied-expression review; public/private
independence; integrated counts 27/27/27; Markdown and links; privacy;
whitespace and staged-diff review; and the formal commit-message check.

No project test suite, `go test`, Nix execution, integration checker,
readiness, smoke, release, publication, or deployment ran.

## Delivery and stop boundary

APG39 delivers one formal authoring commit on
`claude/apg39-v0.4-matryer-nix-final-redesign` and attempts one bounded
push; the exact push result is recorded in the APG39 phase report and its
explicitly associated operational record. `main` is not moved. Neither
earlier Claude branch is moved or deleted.

No candidate is integrated, adopted, mature, compatible, published, or
deployed. No public or active v0.3.0 object, reference, RepoMap, personal,
or target repository, Nix state, database, container, virtual machine, or
external service changed. No phase after APG39 is authorized; APG40
requires a fresh maintainer request.

## Subsequent APG40 disposition

APG40 accepted this exit as the truthful close of a complete authoring phase.
It retained `nix-test-profile` provisionally, deferred
`matryer-is-test-profile` after a remaining corrected-state equality defect,
Rejected ADR 0027, preserved ADR 0026 as Accepted, and kept
`go-testing-stack` absent. These are forward APG40 facts; they do not alter
APG39's authoring-only evidence or original stop boundary.
