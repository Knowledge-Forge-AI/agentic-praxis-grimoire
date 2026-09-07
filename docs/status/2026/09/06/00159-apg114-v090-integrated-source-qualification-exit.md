# APG114 v0.9 integrated source qualification exit

Phase ID: `APG114`

## Status and scope

Terminal disposition: `V090_INTEGRATED_SOURCE_QUALIFIED`.

APG114 qualifies the integrated CI summary interface and XO consumer fixtures
on Darwin arm64. Manager acceptance of APG113 is preserved. The only tested
source changes are standard Go formatting in
`testing/fixtures/xo_consumer/adapter.go` and real CLI boundary assertions in
`src/test/int/python/agentic-praxis-grimoire/bin/apg-test.int.test.py` for combined
role error receipts, inline summary paths, private modes, and missing arguments.
No production API, dependency, version, capacity policy, or skill changes occur.
The corpus remains 39 leaves, 14 stable / 25 provisional, within the existing
9,527-byte discovery limit.

## Evidence basis and supersession

The APG114 producer evidence remains unchanged in this run's original
`evidence/` directory. Its passing combined log reports 3,420 unit tests and
621 integration tests with two skips; unit coverage is 9,570/11,141 statements
and 3,344/4,152 branches, integration is 9,557/11,141 and 3,324/4,152, and union
is 10,071/11,141 and 3,606/4,152. The integration repair closes the observed
3,321/4,152 branch shortfall without changing thresholds. The retained root Go
log has 157 top-level passes across 12 packages. The retained metadata log has
82 passes in 8.08 seconds. These are historical observations, not a retroactive
binding of mutable working bytes.

The APG113 XO-COMPAT2 evidence manifest predates its closer's edits to
`adapter.go`, `adapter_test.go`, and the fixture `README.md`. Its six command
logs remain historical producer evidence; their hashes do not establish
final-closer-source qualification. APG113's accepted implementation and original
archive remain unchanged. Its prior final-source authority is superseded by
this phase's new qualification attempt, without rewriting the old manifest or
relabeling that historical run's execution mode.

New closeout evidence resides under the dispatcher run
`APGR-V090-INTEGRATION1--20260907T023322668529Z/` in
`evidence-closeout-20260907T042216Z-repair/manifest.json`. That manifest binds raw command
logs, actual argv and statuses, platform/tool versions, source inventory,
consumer before/after inventories, summary receipt, and qualification limits.
The retained source archive and complete inventory identify the tested code
separately from subsequent documentation changes. The summary's `source_commit`
identifies entry HEAD only; it does not identify the modified test and formatted
fixture. The inventory and dispatcher candidate tree supply that distinction.

## Closeout review disposition

All ten advisory findings are accepted for amendment:

- F1: replace the unsupported binding-negative-control claim with a retained
  positive check and changed-fixture rejection using the same binding checker.
- F2: correct the historical Go count to 157 top-level tests across 12 packages.
- F3: correct the historical metadata duration to the retained 8.08 seconds.
- F4: rerun the required gates and both consumer lanes from the bound disposable
  source, inventorying all tracked files including ignored fixtures and the
  changed Python test before and after execution.
- F5: retain platform, tool versions, cache observation, and explicit skip and
  platform limitations in the new manifest.
- F6: retain the actual public-package diff command, status, and output.
- F7: distinguish APG113 historical evidence from APG114 final-source evidence.
- F8: enumerate the four remaining-work categories below.
- F9: state the actual formatting scope: tracked Go files excluding `testdata`.
- F10: apply maintained confidentiality markers to phase additions and record
  why the public-release candidate validator is inapplicable here.

The dispatcher-owned independent work review inspected the producer candidate.
These closeout amendments and reruns are closer revalidation, not another
independent review. Git finalization and archive outcomes belong exclusively
to the dispatcher's terminal records.

## Qualification and limitations

Closeout revalidation passed on Darwin arm64 (macOS 26.6.2), Python 3.13.12,
pytest 9.1.1, coverage 7.15.2, pytest-cov 7.1.0, pytest-xdist 3.8.0,
and Go 1.25.10. The canonical combined runner passed all 3,420 unit tests
and 621 integration tests with two declared skips.

| Gate | Statements | Branches |
| --- | --- | --- |
| unit | 9567/11141 | 3342/4152 |
| integration | 9556/11141 | 3322/4152 |
| combined union | 10069/11141 | 3603/4152 |

Policy and record identity pass. The root Go formatting check over tracked
Go files excluding `testdata`, vet, and uncached race tests pass: 157 top-level
passing tests/examples across 12 packages. Metadata regressions pass (82 tests);
source CLI version, help, and 39-skill listing pass. Both independent consumer
modules pass vet and uncached race tests in both lanes (7 XO and 5 existing
consumer tests per lane). Lane A uses the public proxy and checksum database
with a warm cache and the expected released v0.8.1 sums; Lane B uses only a
disposable consumer-local replace bound to the library inventory. The original
consumer fixture files match before and after each lane.

The first closer aggregate attempt is retained as failed: adding
`PYTEST_ADDOPTS=-rs` conflicted with a terminal-disabled nested pytest test,
and integration separately measured 3,321/4,152 branches below its threshold.
The second attempt removed that option: all assertions passed, but the same
integration branch shortfall remained. A bounded closer correction adds real
CLI assertions that a malformed final summary option preserves an earlier
receipt target. They pass on real source and fail on a deliberately faulty
scanner in a separate disposable copy. The third canonical attempt passes.
Production code, coverage sources, and thresholds remain unchanged.
The first failure is superseded for qualification, not erased.

The two integration skips concern absent historical `APG11_PUBLIC_V01_ROOT`
dogfood evidence and an unsupplied public v0.1.0 root (`APG12_PUBLIC_V01_ROOT`).
They do not claim that those historical external inputs were qualified.

Final binding accepts terminal source and fixture hashes and rejects the
separate mutated-fixture copy. Terminal documentation changes are separately
inventoried. One closer-only Python integration-test correction followed work
review; its focused CLI check, deliberately faulty scanner negative control,
and canonical gate were rerun. Library and fixture inventories are unchanged,
so the source-bound Go results retain their original tested snapshot identities.

The full public-release `check` command requires a projected release candidate,
base, and version and invokes release-wide validation. No release candidate is
created in this phase, so that command and the ten-asset reproducibility build
are inapplicable. The maintained local-path confidentiality rule is checked
against phase additions, and the normal policy/record gates cover changed docs.
Unchanged historical private-development references are not a public-surface
qualification claim; future public projection must enforce its full policy.

Linux remains unqualified: policy needs runner qualification, and whole-inventory
runtime preflight retains its documented Darwin-specific Node bindings. No
Linux provisioning, hosted pipeline activation, or ruleset change occurs.
Go fixture containment, reflection, dependency, and negative-control results
are bounded checks of these fixtures. Passive DTOs do not enforce workflow
security and the fixture is not JACA's production adapter.

## Remaining work and ownership

1. **APGR integrated source qualification:** addressed here through the passing
   canonical gate, dual consumer lanes, and final evidence binding.
2. **APGR release work, separately authorized:** prepare v0.9 version and
   metadata, public projection, reproducible release bundle, publication, and
   installed readback. Published v0.8.1 and its separate flake handoff remain
   unchanged; this phase performs no public release or host deployment.
3. **JACA adoption and platforms:** JACA owns CI role registration, runner and
   platform qualification, and the production XO adapter under `JACA-APG0`,
   `CTX-DOCS`, and `XO-APGR1`. These are not APGR runtime dependencies or
   authorization to change JACA.
4. **Later consumer backlog:** Theme Forge follows JACA CI and JACA XO; Repo Map
   follows Theme Forge. Their capacity, profile, protocol, and migration work
   remains allocated to later decisions. No successor starts automatically.
