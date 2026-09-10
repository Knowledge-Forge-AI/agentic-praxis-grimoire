# APG141 reporting project-key contract

Status: DELIVERED after supplied independent review and terminal verification.

## Observed problem and decision

The Go collector already strips every leading dot from the Git-root basename.
Modern report writes instead required the untrimmed basename and then required
an alphanumeric first character. A repository named `.example` could not use
modern report writes: `.example` failed identifier validation and `example`
failed the basename check. Modern response capture had the same restriction;
legacy report commands already used `example`.

Align modern CLI report and response selection with that existing Go/legacy
normalization. This is the complete mapping: remove leading ASCII dots from
the selected repository basename, then apply existing path-safe identifier
validation. Preserve case, internal dots, hyphens and underscores. No remote,
parent directory, host path, configuration lookup or implicit alias is used.

## Precedence, collision and compatibility

Repository-backed report writes still require explicit `--project` equal to
the normalized basename. Response capture derives it when omitted; an explicit
value must agree. Repository-free path and response operations keep their
existing explicit project semantics. Empty, dot-only, separator-bearing and
otherwise invalid identifiers remain refused. An unrelated alias is refused
before writing. Record and append project identities must still agree.

Normalization is not globally unique: `.example` and `example` deliberately
share the legacy key, as do equal basenames in different parent directories.
The caller must separate outbox roots for distinct projects with the same key;
this change introduces no collision detection or merging policy. Existing
outbox append/integrity rules remain controlling. No migration or public
repository identity is inferred. Previously successful writes keep their keys
and envelope bytes; previously refused dot-prefixed writes become usable.

## Qualification and rollback

CLI fixtures exercise actual report show/diff and response publication from a
dot-prefixed disposable repository, ordinary keys, mismatch refusal, and
identifier refusal. Existing report tests cover Go collection and append
identity checks. Wrappers continue to delegate to the CLI. This repair adds no
public Go type, envelope field or dependency. Rollback restores modern CLI
refusal; legacy commands and the existing Go interface remain available.
