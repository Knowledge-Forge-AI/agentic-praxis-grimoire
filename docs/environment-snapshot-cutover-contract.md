# Thin `.flakes` environment hook cutover contract

This document is a readable, separately executable contract for a future
`.flakes` maintainer-authorized cutover. It is not an activation instruction
for APG98. APG98 does not edit `.flakes`, shell startup files, live hooks,
profiles, or current snapshots.

## Ownership and authority

1. `.flakes` retains ownership of profile contents, profile selection, shell
   startup composition, and host-specific activation.
2. APG owns the portable JSON snapshot schema, validation, storage, locking,
   staleness, and in-process Go API only after APG98 qualification.
3. JACA and other Go consumers load APG JSON or import `envsnap`; they do not
   source a shell file.
4. A cutover is valid only after an independently authorized migration review
   accepts the selected profile, APGR binary availability, storage root, and
   rollback path.

## Required command shape

The future hook may call the Go adapter with an exact argv equivalent to:

```text
apgr env snapshot \
  --profile <flakes-owned-profile.json> \
  --storage-root <flakes-selected-apgr-environment-root> \
  --context global
```

The profile and storage-root arguments are explicit. The profile remains
`.flakes`-owned; the storage path is selected by the maintainer and must be an
owner-safe APGR environment root. The command must construct a caller map and
invoke the public API through the Go CLI adapter, never through a shell string
or an implicit profile default.

## Hook behavior to preserve

The cutover adapter must retain the observable current hook contract:

- detect only an active Bash or Zsh shell;
- silently no-op when the APGR binary is unavailable;
- perform one immediate refresh when the hook is installed;
- refresh on every Zsh `precmd`;
- prepend exactly one Bash `PROMPT_COMMAND` entry without duplicates;
- redirect snapshot output and diagnostics away from the prompt;
- treat a refresh failure as non-fatal to the shell prompt; and
- preserve exact argument boundaries and avoid `eval`, `source`, `bash -c`, or
  `zsh -c` for the APGR invocation.

The hook must not print environment values. It must not turn a prompt refresh
into a shell export-file source operation.

## Canonical data and shell rendering

APG JSON is the canonical store. The current `.flakes` shell export files are
not rewritten by APG98 and must not become a hidden second authority.

If a future hook or legacy consumer still requires `export NAME=...` text, a
separate, explicitly authorized parser-safe renderer/adapter must be designed,
owned, and qualified. That renderer is deferred by this contract: it is not a
canonical store, it must not be sourced as arbitrary shell code, and it must
not silently be added to `env snapshot`. A cutover cannot claim completion
while an existing consumer still depends on an unqualified shell-file view.

## Rollback and non-actions

Before activation, a maintainer must record the prior hook/profile/storage
owners and a disposable rehearsal result. Rollback restores the prior
`.flakes` hook call and leaves APG JSON available for inspection; it does not
delete foreign files or rewrite historical values.

The following actions are outside this contract and remain prohibited in
APG98:

- editing `.flakes` or Nix sources;
- changing live Bash/Zsh startup files or hooks;
- replacing `env-snapshot` in the active shell;
- deleting or rewriting `~/.codex` snapshots;
- creating or changing real `~/.apgr/environment` state;
- changing JACA; and
- publishing or bumping APG version identity.

## Acceptance checklist for a later phase

The maintainer-authorized cutover phase must independently show:

1. the selected `.flakes` profile is explicit and passes APG profile checks;
2. the APGR binary is present, version-checked, and invoked by exact argv;
3. a disposable store/load/resolve rehearsal passes with no value leakage;
4. immediate Bash/Zsh refresh, repeat-refresh no-churn, missing-binary, and
   non-fatal failure cases pass;
5. any required shell export renderer has its own owner, schema, parser-safe
   implementation, and rollback evidence; and
6. active hook, snapshot, Nix, JACA, and host-state diffs are absent unless a
   separate authorization explicitly includes them.

Until that checklist is accepted, `.flakes` remains the live environment
authority and this document is only a migration boundary.
