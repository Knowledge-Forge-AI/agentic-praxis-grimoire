# APG26A Formal-Phase Commit-Message Enforcement Exit

Phase ID: `APG26A`

## Disposition

Complete — formal-phase commit-message enforcement added

## Scope and result

APG26A records that APG26's formal-phase commit contains only its subject and
therefore omits the body required by ADR 0020 and the structured project
defaults. APG26 is not amended or rewritten. Its substantive capability,
scenario, routing, maturity, and distribution decisions remain accepted.

The new dependency-free Python `apg-check-phase-commit-message` command enforces
an exact canonical phase subject, one blank separator, and one ordered nonempty
`Scope`, `Result`, `Verification`, and `Not run` section. It validates either a
regular message file or a Git commit, supports text and JSON output, uses fixed
Git argument vectors, and returns stable compliant, noncompliant, usage, and
repository-error exit classes. The checker does not judge imperative mood,
apply to non-phase commits, or grant authority.

## Validation and review

Failing-first unit and integration runs establish the absent module and command.
The resulting eleven unit tests and five real-CLI/Git integration tests pass.
The subject-only APG26 fixture is rejected. Initial fresh review found one
material evidence defect and no implementation defect: the section validator's
Orange fallback complexity and branch signals were omitted from the evaluation.
The corrected evaluation now records the Orange disposition, explicit cohesive-
validator retention decision, focused evidence, and rollback. Focused re-review
accepted the unchanged implementation and corrected records with no findings.

Eleven unit tests, five real-CLI/Git integration tests, and ten directly
affected record-identity integration tests pass. Identity is 22 ADRs, 43 exits,
and 43 phase IDs with ADR 0023 and exit 00044 next. The skill checker remains
21/21/21. Python compilation, Markdown links and fences, privacy, and whitespace
checks pass. The complete APG suite is deliberately not run because APG26A is
not a readiness or release checkpoint.

## Resulting boundary

No `SKILL.md`, capability map, maturity row, public or active v0.3.0 artifact,
report format or executable, target repository, personal skill, dependency,
pytest suite, ChatGPT skill, or later v0.4 slice changes in APG26A.

APG27 is the only supplied successor and remains blocked until APG26A is
complete, committed, pushed, remote-equal, and fully reported. No phase after
APG27 is authorized.
