# APG26A Formal-Phase Commit-Message Enforcement

Phase ID: `APG26A`

## Outcome

Complete — formal-phase commit-message enforcement added.

## Defect and disposition

APG26's substantive `pytest-test-profile` and
`converting-bash-scripts-to-python` results remain accepted. Its formal-phase
commit contains only the subject line and omits the material scope, result,
verification, and deliberately unrun checks required by ADR 0020 and the
structured project defaults.

APG26A does not amend, replace, or rewrite APG26. It records the deviation in
the APG26 evaluation and exit, then corrects forward for new APG formal phases.
No APG26 skill, scenario, routing, maturity, or distribution decision changes.

## Enforced contract

[`bin/apg-check-phase-commit-message`](../../bin/apg-check-phase-commit-message)
requires:

- an exact canonical `<PHASE-ID>: <nonempty result>` subject;
- exactly one blank line between subject and body;
- exactly one `Scope`, `Result`, `Verification`, and `Not run` heading in that
  order;
- one or more nonempty dash-space entries in every section; and
- UTF-8 text without malformed control characters.

`- none` is a valid `Not run` entry. The checker does not attempt to infer
imperative grammar. Non-phase commits and repositories that own a different
convention remain outside its scope.

The command accepts exactly one of `--message-file <path>` and `--commit
<revision>`, plus `--phase <PHASE-ID>` and `--format text|json`. Exit classes
are `0` compliant, `1` noncompliant, `2` usage, and `3` message-source or
repository error. Commit retrieval uses fixed Git argument vectors and a
resolved commit object. Diagnostics do not reproduce the commit message,
revision, or source path.

## Integration and use

For a new APG formal phase, the top-level manager writes the complete message
to a private file, validates that file, commits with `git commit -F`, validates
the resulting commit, and only then generates managed reports. The checker is
read-only and grants no commit, push, report, acceptance, or successor
authority.

The executable is a thin installed-layout-aware entry point over one
standard-library Python owner. The source supports Python 3.10+ and uses no new
dependency. Public and active v0.3.0 do not receive the command in APG26A.

## Executable evidence

The subject-only APG26 message is frozen as a focused regression fixture. The
initial unit run failed because the validation module was absent, and the
initial integration run failed because the command was absent. The resulting
focused contracts cover a valid APG26A message, the APG26 subject-only
regression, wrong phase, empty result, missing/duplicate/out-of-order sections,
empty and malformed entries, missing blank line, `Not run: - none`, invalid
UTF-8 and control characters, exact source selection, noncommit revision,
fixed installed layout, and deterministic text and JSON results.

### Python profile disposition

Python profile level: `Orange`.

No repository-configured analyzer exists, so the following are APG fallback
counts. The maintained module is 421 physical lines, Yellow. Its
`_validate_sections` callable is 24 recursive statements, Yellow; cyclomatic
complexity 15 and 9 branches, both Orange; nesting depth 2 and 2 arguments,
both Green. No other callable or semantic signal raises the disposition, and no
Red signal is present.

Project policy supports Python 3.10+, the standard library, fixed Git argument
vectors, no new dependency, and proportional focused evidence. APG26A makes an
explicit local decision to retain the cohesive section validator: its branches
directly represent one machine-checkable contract's separator, heading
cardinality, order, and entry invariants, and splitting that decision table
would add ownership without reducing the external risk. The Orange response is
focused unit and real-repository integration validation, explicit review, and
documented rollback rather than unrelated decomposition.

The rollback is removal of the command, helper, focused tests, and current-owner
enforcement text while preserving this correction history. The classification
does not relax any safety, compatibility, privacy, or authority boundary.

## Validation and review

The resulting eleven unit tests and five real-CLI/Git integration tests pass.
Ten directly affected record-identity integration tests pass. The mechanical
identity checker reports 22 ADRs, 43 exits, 43 phase IDs, next ADR 0023, and
next exit 00044. The skill checker remains 21/21/21. Python compilation,
Markdown links and fences, privacy, and whitespace checks pass.

Initial fresh non-author review found the omitted Orange classification and no
implementation defect. After the bounded evidence correction, focused
re-review accepted the unchanged implementation, explicit retention decision,
tests, rollback, current documents, and complete APG26A surface with no
unresolved findings. The complete APG suite was deliberately not run because
APG26A is a scoped correction rather than readiness or release work.

## Preserved boundaries

APG26A changes no `SKILL.md`, capability map, maturity row, report format,
report executable, public release, active integration, target repository,
personal skill, dependency, pytest migration, ChatGPT location, or later v0.4
slice. APG27 remains gated until APG26A is committed, pushed, remote-equal, and
fully reported.
