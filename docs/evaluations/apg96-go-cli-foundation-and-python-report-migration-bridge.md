# APG96 Go CLI Foundation and Python Report Migration Bridge

## Result

APG96 establishes the first real root Go CLI at `cmd/apgr` and migrates normal
report command execution to the accepted Go `report` authority. The command is
a private adapter: APG96 adds no exported `report` API and changes no report
record bytes or schema versions.

Implemented private owners are `internal/cli` for command/configuration handoff,
source-file safety, legacy omnibus publication, path, recovery, cancellation,
and exit classes, and `internal/buildinfo` for deterministic build information.
The CLI implements help, version, build-info, and report show, diff,
operational/ops, path, and recover.

## Migration and oracle separation

Python continues to resolve APGR home, project/global configuration, project
identity, repository root, and outbox precedence. It then invokes Go with exact
argv and no shell. Canonical `reports.py`, `cli.py` historical dispatch, and the
three checkout-local wrappers all delegate to Go.

The frozen `libexec/agent_report` implementation is no longer a normal routing
owner. A test-owned `report/testdata/python_oracle.py` entry invokes it directly
for differential parity, avoiding Go-vs-Go self-comparison after wrapper
migration. No migrated route falls back to Python when the Go bridge is absent.

The locator accepts an explicit absolute direct executable, reserves the future
package-bundled binary location, and supports a verified source-checkout build
in an invocation-private temporary directory. It performs no runtime download
and no `apgr` PATH search. APG100 still owns wheel/npm binary bundling, so an
installed package without a bundled or explicitly supplied binary fails closed.

## Report and compatibility behavior

Show and Diff call `report.Service` and publish through `report.Append`.
Operational/ops performs bounded direct-regular source reads with no-follow,
owner mode, link-count, size, stable-identity, and destination-confusion checks,
then calls in-memory `report.Operational` and `report.Append`. Path performs no
publication. Recover exposes the accepted `internal/atomicfile.Recover`
transaction contract.

Historical compatibility preserves positional/help/success behavior and the
explicit `GIT_SHOW_REPORT_ROOT` omnibus layout in private CLI code. An empty
historical override selects the canonical destination. Canonical Python routing
passes an explicit resolved outbox, so it continues to ignore that legacy
override.

APG96 preserves APG95 supersession bytes: an ops-only primary is removed when a
later Git show/diff primary supersedes it, and its record is not copied forward.
Operational evidence created after a Git primary exists appends inside that Git
primary. Accepted ADR 0051, the normative architecture, and the reporting guide
now state this behavior unambiguously.

## Build-information foundation

Go source defaults report version and corpus fingerprint as `devel`. The
release-like helper reads the single editable Python `VERSION` resource and
injects `0.6.0` with linker flags. It injects the SHA-256 of the canonical skill
metadata resource as APG96's transitive current-corpus identity:
`0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c1`.

Machine JSON reports module path/version from normal Go build metadata, exact
target, Go toolchain, corpus fingerprint, schema-derived envelope/show/diff/
operational versions, and the ordered `darwin/arm64`, `linux/amd64`, and
`linux/arm64` matrix. Release-like builds use `CGO_ENABLED=0`. Cross-compilation
does not claim foreign runtime qualification. APG97, not APG96, owns embedded
skill bodies and bundle identity.

## APG95 follow-up and acceptance reconciliation

The four vacuous APG95 parity operations now fail immediately: both required
candidate/oracle publication reads check `os.ReadFile`, and both associated
operational record encodings check `buildRecord`. The remaining parity suite
was audited for the same discarded required-result class.

APG95 records now state the dispatcher-reported `ENTRY_DIRT_OVERLAP` closeout
provenance and the operator's exact acceptance commit
`04f135980385eda54496b89f9908cc86f52d2884`, tree
`fe3ca7a11007c09e165abddf0de2757dec4e2b08`, with no source-byte change from the
reviewed closeout tree. Those identities are historical evidence, not APG96
entry gates.

## Final-review corrections and disposition

The following accepted corrections from dispatcher final review were applied:
1. Publicly projected files (`AGENTS.md` and `docs/roadmap.md`) were updated to
   remove development commit/tree identities in compliance with working rules for
   publishable files.
2. `apgr report path` flag parsing in `internal/cli/report.go` was corrected to
   accept `--phase` and `--kind` in any order, matching canonical route handling,
   and test coverage was added.
3. Dead code (`_working_directory` and unused imports) in `reports.py` was removed.
4. `go_bridge.py` was updated to capture and surface Go build stderr on failure;
   source-checkout toolchain dependencies and per-invocation build behavior were
   documented.
5. Three error strings in `report/operational.go` and `report/parser.go` were
   reverted to exact accepted APG95 strings.
6. `buildinfo.go` was updated to check schema format version results explicitly.
7. `report/diff.go`'s `testPause` hook was verified as necessary for concurrent
   index-mutation testing parity with the migrated `git-diff-report` suite.
8. `release/public-surface.json` manifest reconciliation for `libexec/agent_report`
   is tracked for APG100 multi-ecosystem packaging.

## Verification and preserved state

Verification covers Go formatting, all packages, race, vet, host execution,
supported-target cross-builds, build-info injection/reproducibility, direct
external `report` consumption, canonical/historical Python bridge regressions,
frozen Python oracle parity, path/recovery, source mutation and link safety,
locks, transactions, interruption, APG record/skill/context invariants, and
public-projection policy. Exact commands, selections, counts, binary hashes,
and the prospective candidate tree belong to the dispatcher pre-final handoff.

Version remains 0.6.0. Skills remain 39 canonical / 39 catalog / 39 projections
/ 39 discoverable, with 14 stable / 25 provisional, zero malformed, 9,504
description bytes, 9,492 characters, and the unchanged 9,527-byte ceiling.
Current public v0.6 artifacts are not rewritten. No skill, environment,
hotspot, response, JACA, `.flakes`, Nix, wheel/npm, version-bump, publication,
deployment, APG97, or successor work occurs.

## Disposition

Terminal disposition:
`V07_GO_CLI_REPORT_BRIDGE_READY_FOR_APG97`.

APG97 is recommended but requires separate authorization.
