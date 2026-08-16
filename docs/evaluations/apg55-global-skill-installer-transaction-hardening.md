# APG55 Global Skill Installer Transaction Hardening

## Result

APG55 is a bounded forward correction to the APG54
`install-global-skills` implementation. It preserves the command, CLI,
source-set semantics, ownership model, and Accepted ADR 0033 while correcting
three transaction and state defects through one forward phase.

Failing-first controls reproduced:

- partial destination-chain creation could escape the caller's rollback
  boundary;
- a replacement record created before quarantine could misclassify a
  pre-mutation failure as incomplete rollback; and
- the private ownership-state reader performed one read without proving exact
  bytes, EOF, or stable descriptor metadata.

## Transaction corrections

Destination creation now owns its partial journal until it can return a
complete container tuple. Each component is first created as an owner-only
staged sibling, immediately validated and identified, and then installed at
the final pathname with an atomic no-overwrite directory rename. The helper
reconciles the known staged identity across both names until journal ownership
has transferred. Failure cleans the journal in reverse order and removes only
identity-equal empty directories. Changed, replaced, or non-empty entries are
preserved; incomplete cleanup is reported as a secondary bounded failure with
path basenames only.

Replacement changes use explicit stages:

```text
planned
old quarantined
new installed
state committed
backup cleaned
```

Quarantine registers a rollback record only after the old link has moved and
been revalidated. Link installation advances the stage only after the new
link exists with the expected identity and target. A pre-quarantine failure
therefore preserves its original error without invented rollback work.
Pre-commit failures restore quarantined old links, while committed state
remains authoritative and backup-cleanup failure becomes a warning.

## Exact state reads

Private installer state remains owner-only, regular, single-linked, and
bounded to one mebibyte. The POSIX reader now:

1. opens without following a final symlink;
2. validates initial descriptor metadata;
3. reads in bounded chunks until the declared size is complete;
4. reads once more to establish EOF;
5. compares device, inode, mode and file type, owner, group, link count, size,
   modification time, and change time; and
6. closes the descriptor on success, error, or interruption.

Short reads are accepted and completed. Premature EOF, excess bytes, unsafe
shape, and metadata drift are rejected with bounded diagnostics. The same
owner serves normal state loads and installer-owned state backups; no
repository-wide filesystem framework was introduced.

## Path and source hardening

All environment and CLI path sources reject ASCII controls before values can
enter line-oriented or JSON output. NUL is rejected through the underlying
path API. Spaces, supported Unicode, and interior periods remain valid.

Inventory retains transaction-local identities for repository roots, skill
roots, skill directories, and direct `SKILL.md` files. Revalidation rejects
root, directory, ancestor-symlink, marker-identity, or marker-hash changes
inside link installation and immediately inside state installation. These
identities do not enter deterministic output or user-local state.

## Verification and preservation

Focused unit and integration controls exercise partial creation after the
first and second directory, permission failure, interruption, changed and
non-empty residue, pre-quarantine failure, backup collision, link failure,
two-skill rollback, committed cleanup warnings, short reads, EOF, growth,
shrink, metadata drift, unsafe file shapes, every declared path source, and
same-marker source replacement.

Complete unit (477 passed), integration (356 passed, 2 skipped), combined,
configured Bats (23 passed), disposable Codex and Claude dogfood, existing
installer/flattener/user-lifecycle regression, current-development and
historical release policy, local release candidate, skill-library, identity,
report, documentation, privacy, rights, size, whitespace, and independent
review gates pass in the terminal phase record. Combined coverage is
6,806/7,279 statements and 2,418/2,686 branches.

ADR 0033 remains Accepted. Development remains 28/28/28 with fourteen stable
and fourteen provisional rows. ADR 0031 remains Rejected, all ten Web/Node
candidates remain deferred, React and Vitest retain Policy A, and corrected
public and active v0.4.0 are unchanged.

No live Codex or Claude installation or discovery, source execution, network
source acquisition, readiness, publication, deployment, Web/Node work,
browser work, or successor phase occurred.
