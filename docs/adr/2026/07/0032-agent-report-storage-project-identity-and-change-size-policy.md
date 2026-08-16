# ADR 0032: Agent Report Storage, Project Identity, and Change-Size Policy

- Status: Accepted
- Date: 2026-07-28
- Decided in: APG53
- Relates to: ADR 0023 (Accepted), ADR 0031 (Rejected; unchanged)

## Context

The complete APG52 Git-show report was correct but exceeded 18 MB because its
formal patch rewrote three complete generated JSONL datasets. Those datasets
accounted for 98.88% of the patch payload. Truncating reports would conceal the
artifact problem rather than correct it.

The report commands also stored new reports directly below
`~/Documents/agent/<project>`, and Git repositories whose basenames began with
periods produced hidden report directories and hidden project metadata. A
maintainer-supplied shared-skills projection prototype additionally needed a
bounded, repository-owned implementation before it could become a public
current-development command.

## Decision

All three report commands now default to:

```text
~/Documents/agent/reports/<project>/<ticket>.report.txt
```

`GIT_SHOW_REPORT_ROOT` remains an exact override root. The implementation does
not append `reports` to that override, search the old default, or migrate or
delete historical reports.

Project identity is the Git-root basename after removing every consecutive
leading ASCII period. Interior and trailing periods, spaces, and non-ASCII
characters remain unchanged. An empty result, a separator, or a control
character is rejected. The same normalized value owns report metadata,
destination paths, and success diagnostics.

Complete report rendering remains unchanged. Large-report prevention belongs
at the change boundary:

- ordinary tracked blobs are limited to 262,144 bytes;
- generated-derived-evidence blobs are limited to 131,072 bytes;
- aggregate generated-derived evidence is limited to 524,288 bytes per
  change;
- a text line is limited to 65,536 bytes;
- archives are refused by default; and
- binary assets require an exact identity-bound exception.

`testing/apg-change-size-policy.json` is the closed, versioned owner.
`bin/apg-check-change-size` checks staged, commit, or tree Git objects without
executing repository content. Exceptions must bind an exact path, mode, blob,
maximum size, owner, reason, rights disposition, phase, review condition, and
expiry condition. APG53 accepts no exception.

The three APG52 complete derived datasets are removed from the current tree
only after their accepted hashes, counts, and two-run equality were verified.
Exact source selection, manifests, rules, rights, compact summaries, hashes,
sample, tools, and reproduction records remain. Complete regeneration must use
an explicit empty, non-symlink output root outside both the APG repository and
bound source repositories. Deletion from the current tree does not remove the
historical Git objects.

The maintainer-supplied `flatten-skill-symlinks` basename is retained as a
thin public launcher with maintained logic under `libexec/`. It projects one
explicit source into an explicit destination using exact owner-state, a
destination lock, no-overwrite transactional replacement, rollback, dry-run,
and check behavior. It is a current-development and future-v0.5 public surface;
it does not prove Claude runtime discovery, publish v0.5, or mutate a live
Claude integration in APG53.

## Alternatives considered

- Truncate or summarize large Git-show reports: rejected because complete
  rendering is an audit property.
- Keep complete APG52 datasets tracked: rejected because compact accepted
  evidence and deterministic regeneration preserve reviewability without
  repeating multi-megabyte rewrites.
- Add Git LFS or compressed archives: rejected because neither corrects review
  volume, and archives can conceal generated bulk.
- Derive generated status only from hosted-repository display metadata:
  rejected because display classification is not a repository storage policy.
- Reuse the supplied prototype unchanged: rejected because its direct mutation
  and ownership model did not safely support replacement or rollback.

## Consequences and rollback

New reports are grouped below one private `reports` directory, while exact
override callers and historical records remain stable. Leading-dot repository
names no longer create hidden report identities. APG52-style bulk generated
changes fail before commit unless a narrow reviewed exception is added.

Rollback may revert the APG53 implementation and policy commit. Historical
reports remain untouched. A projection created by `flatten-skill-symlinks`
may be cleaned only from its exact owner-state; unmanaged entries are never
adopted or removed. Restoring the deleted APG52 datasets in a later current
tree would require separate authority and would fail the accepted size policy
without explicit exceptions.

## Deferred decisions

ADR 0032 is not a Web or Node architecture decision. ADR 0031 remains
Rejected, all ten candidates remain deferred, and React and Vitest retain
Policy A. Publication, deployment, target mutation, live Claude mutation, and
every successor phase remain separately authorized.
