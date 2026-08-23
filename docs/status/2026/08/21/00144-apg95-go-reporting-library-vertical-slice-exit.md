# APG95 Go Reporting Library Vertical Slice Exit

Phase ID: `APG95`

## Status

**Terminally accepted — Go reporting core ready for APG96.**

Terminal disposition:
`V07_REPORTING_GO_CORE_READY_FOR_APG96`.

The dispatcher-reported closeout could not own the commit because entry was
classified `ENTRY_DIRT_OVERLAP`. The operator then accepted and committed the
exact reviewed closeout tree, with no source-byte change, as commit
`04f135980385eda54496b89f9908cc86f52d2884`, tree
`fe3ca7a11007c09e165abddf0de2757dec4e2b08`. These are historical acceptance
evidence rather than successor entry gates.

## Outcome

APG95 adds the root Go 1.25 module, narrow public `schema` and `report`
packages, native exact-argv Git execution, and private atomic publication
helpers. Show, Diff, Operational, ParseRecords, and Append operate through the
frozen in-memory API. The module uses only the standard library.

The Python report implementation remains the active CLI and byte oracle. The
Go differential corpus covers 22 accepted exact-byte cases and 11 rejected
failure-class cases, plus drift, cancellation, mutation safety, parsing,
locking, recovery, permission, and path invariants. A disposable external Go
module imports and uses `report` without the APG CLI, Python, a shell, or APG
internals at the consumer boundary.

The implementation follows observed Python publication behavior: a later Git
primary removes an ops-only primary without copying its record. The evaluation
records the mismatch with the APG94 architecture's “absorbs” wording; Python
behavior was not changed.

## Verification basis

- Go formatting, tests, race tests, and vet for all owned packages;
- current 114-test focused Python report regression (82 unit tests in `libexec/agent_report` and 32 CLI integration tests in `bin/`);
- maintained Python/Go exact-byte and rejected-class corpus;
- external temporary consumer compile and execution;
- APG record identity, skill-library, context, invariant, projection-hygiene,
  and diff checks.

The focused public-release policy unit suite passed 46 cases. Its broader
historical integration selection passed 15 cases and had one infrastructure
failure before candidate validation because the fixture-selected Python
interpreter lacked pytest. This exit does not represent that integration
selection as fully passing; the failure named no APG95 source or policy
mismatch.

Fresh command results belong to the dispatcher handoff summary and are not
replaced by this durable record.

## Preserved state

- Version remains 0.6.0.
- Skills remain 39 canonical / 39 catalog / 39 projections / 39 discoverable.
- Maturity remains 14 stable / 25 provisional.
- Discovery remains zero malformed, 9,504 UTF-8 description bytes, and 9,492
  characters under the unchanged 9,527-byte ceiling.
- At the APG95 exit, Python routes remained active and no `cmd/apgr` existed.
- No JACA, `.flakes`, Nix, environment, hotspot, packaging, release,
  publication, or deployment change occurred.

## Next authorization

APG96 is now the separately authorized active successor for the Go CLI, report
path/recovery adapters, build information, corpus-identity foundation, and thin
Python report delegation.
