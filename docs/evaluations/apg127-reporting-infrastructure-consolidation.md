# APG127 reporting infrastructure consolidation

## Status and authority

APG127 and exit 00172 were available and are allocated to the reporting
consolidation slice. Work-stage qualification passed, dispatcher pre-final
findings are dispositioned, and provider closeout is complete. The dispatcher
alone owns Git finalization and publication. No successor, JavaScript debt implementation, new skill, maturity promotion,
consumer change, host change or public release is authorized.

APG126 is manager-accepted after exact-tree recovery from its mechanical
finalization block. Its original dispatcher aggregate remains historically
blocked with `PATH_DISPOSITION_INVALID`. The APG125 preservation commit remains
custody evidence. Neither historical outcome is rewritten as a successful
dispatcher run.

## Proposal and review disposition

Producer proposal disposition: **amend**. The bound planner proposal is evidence
for implementing the three originally authorized items: persisted-record
verification, operational semantics and bounded idempotency. It does not replace
the task scope. No stage deltas were reported at entry.

All eight independent plan-review findings are incorporated:

1. Show/diff opaque sections require deterministic extraction confirmed by
   integrity hashes; delimiter-like content must remain data.
2. Diff status/staged/unstaged hashes admit the exact stored bytes or those
   bytes with the renderer-added terminal newline removed. Diff identity proof
   uses recorded hashes and the recorded real-index fingerprint only.
3. Maintained persisted fixtures and real-file tests supplement the optional
   historical Python oracle. Missing oracle source is not a parity pass.
4. Native and Python verification bypass repository/project/outbox preparation
   and use a dedicated argument route; verification help owners are updated.
   Closeout adds the initially omitted canonical idempotency help.
5. Newly supplied operational records receive shared semantic validation before
   append framing. This deliberately rejects malformed caller-constructed
   operational records previously accepted by envelope-only append. Show/diff
   append payload validation is unchanged.
6. Native Git rendering is part of complete record bytes. The same commit or
   state identity rendered differently, including by another Git version, is a
   replay conflict under opt-in idempotency.
7. Empty input remains accepted by `ParseRecords` as zero envelopes, but
   verification reports a distinct empty-artifact error and CLI exit 1. It
   cannot qualify a potentially truncated primary as a report.
8. Python route unit and real-boundary integration tests are required alongside
   the canonical component and union coverage gates.

## Frozen compatibility decisions

The common-envelope parser retains its historical public contract. Semantic
verification is additive and does not turn opaque parser fixtures into valid
report payloads. Envelope and record schema versions, accepted rendered bytes,
default duplicate appends, primary supersession and transaction recovery remain
the compatibility baseline.

Operational validation retains the line-oriented format, recognized aliases,
standalone legacy/free-form handling and open caller-owned result vocabulary.
New structured generation validates recognized fields and applicable
relationships before framing. Historical persisted verification uses explicit
compatibility allowances through the same semantic owner. No YAML/JSON parser,
new required result/project vocabulary or record migration is introduced.

Idempotency is explicitly selected by the library append policy or canonical
CLI `--idempotent` option. The retry key is project, phase, kind and record ID
within the retained current primary. Equal complete canonical bytes mean
already-present without replacing the primary. Any conflicting bytes for that
key mean replay conflict, including mixed identical/conflicting historical
duplicates. Default and historical adapters keep distinct-envelope appends.

The guarantee does not search superseded primaries or create an identity ledger.
Source bytes, basename, metadata, phase and associations affect complete bytes;
record ID alone is insufficient. Callers must not concurrently mutate input
buffers. Existing drift rejection and explicit transaction recovery remain
authoritative. `APGR-REPORT-STALELOCK` is superseded by the retained Go reporting
and `internal/atomicfile` owners, not redesigned by this phase.

## Verification and limitations

Work-stage qualification passed with unchanged thresholds:

| Evidence | Result |
| --- | --- |
| Affected Go packages (`report`, `internal/cli`, `internal/atomicfile`) | Fresh `go test -count=1`, `go vet` and race checks passed |
| Public Go surface | External consumer compilation/execution and `go doc -all ./report` passed |
| Persisted and filesystem contracts | Two independently sourced historical fixtures and six format regressions, reframed semantic negatives, overflow/delimiter cases, append/retry/conflict, concurrency and recovery tests passed |
| Python report route | Focused unit coverage and six real-boundary integration tests passed |
| Distribution surface | Two candidate tests passed, including host wheel console/module, actual sdist source build and host npm launcher verification; all supported distribution targets built |
| Canonical unit suite | 3,612 passed; statements 10,020/11,705 and branches 3,636/4,534 |
| Canonical integration suite | 686 passed, two skipped; statements 10,043/11,705 and branches 3,631/4,534 |
| Canonical union | Statements 10,577/11,705 and branches 3,940/4,534; all maintained gates passed |

The canonical run observed no repository-source changes during execution.
Integration branch coverage has three covered branches above the 80% minimum;
this remains a narrow margin. No threshold, exclusion or denominator policy was
changed. A first preflight attempt rejected runtime packages outside their newly
owned scratch roots; copying the existing qualified packages into those roots
resolved the prerequisite without installing or changing versions. A focused
packaging attempt exposed the virtual environment's missing pip module; the
test now uses installed pip's explicit target-interpreter route without a skip.

The unchanged APG126 source independently reproduced all three operational gaps.
Two fixtures preserve its accepted malformed declarations as historical input;
new generation rejects them. Earlier failing tests and producer corrections are
retained alongside passing checks. Internal worker results were independently
dispositioned and do not satisfy a dispatcher checkpoint.

Complete logs, their digests and reconstructible exact source bindings are
retained separately from this semantic phase record. The final record-identity
and whitespace checks cover the reconciled documentation. Provider closeout
adds fresh scoped checks and confirms retained canonical evidence as described
below; no Git finalization or publication outcome is claimed here.

One persisted file cannot prove truthful operational claims, historical test
execution, external Git state, external related-record existence or global
outbox consistency. Foreign-target cross-builds do not establish foreign runtime
qualification. No maturity receipt follows merely from passing this slice.

## Terminal work-review disposition

Disposition: amend

The terminal producer accepts the reporting slice and amends help and
compatibility documentation. This is the in-run disposition of the dispatcher's
pre-final review, not another independent review or publication outcome.

| Finding | Disposition and rationale |
| --- | --- |
| 1: idempotency and modern help | Amend: canonical show/diff/operational help exposes the modern operands and retry option; native/Python report help includes it. Historical help bytes are preserved and executable help tests distinguish both routes. |
| 2: renderer equality | Amend: renderer bytes are verification compatibility authority. Byte-changing renderer evolution requires version dispatch preserving accepted historical verification, not an unversioned replacement. |
| 3: extraction work and cancellation | Defer: the bounded read-only verifier qualifies artifact integrity, not latency. Repeated delimiter hashing can be superlinear and cancellation is not observed inside extraction. The limitation is explicit in the architecture, library reference and package docs; no prompt-cancellation guarantee or successor authorization is claimed. |
| 4: retained encoding error | Reject as a currently reachable defect: retained records pass `ParseRecords` and `validateExistingRecords`. These enforce every identity and safe-field condition that can make `buildRecord` fail; no mutation intervenes. A future renderer error source must revisit the defensive classification, but no present malformed retained artifact can reach that error arm. |
| 5: oversized read classification | Reject the proposed unification: initial oversize is unsupported input; a bounded read exceeding that size after accepted initial stat/open checks observes concurrent growth, an I/O stability failure. The distinction is now documented. |
| 6: CLI exit families | Accept clarification: malformed and I/O failures have distinct library families and diagnostic text, but both CLI statuses are 1; usage remains 2. |
| 7: fixture provenance | Amend: only two fixtures have unchanged APG126 renderer provenance; six are maintained format regressions without an independently recorded earlier renderer identity. Fixture bytes are unchanged. |
| 8: final source binding | Accept and confirm: all bound candidate source digests match. The canonical-to-candidate executable delta is exactly one terminal LF removal from a Python test, verified by reconstructing its original digest. Other product changes are documentation; a phase evidence entry is excluded from the candidate source manifest. |
| 9: archived republication | Amend: compatibility-limited verification does not grant strict `Append` acceptance for newly supplied historical operational records, including publication into a different outbox. |

Closeout re-executed affected Go tests, vet, race and public package documentation;
27 Python report-route unit cases, six real CLI integration cases and two
multi-distribution candidate cases passed. The initial Python unit invocation
failed collection because the checkout import path was absent; supplying the
explicit source path resolved it without source, dependency or environment
installation changes. The failing log remains retained.

The complete work-stage evidence index and log digests were verified. The
canonical gate above is confirmed retained evidence, not a closeout rerun.
Closeout changes only help selection/output, regression assertions and
explanatory documentation; report parsing, rendering, semantic validation,
append, identity and recovery executable bytes remain identical to the qualified
candidate. Python production execution is unchanged except the `HELP` literal;
no maintained Python coverage branch or threshold changed. Fresh focused checks
cover the amended help paths and distribution adapters. Final identity,
whitespace, source-delta and evidence readback checks bind the terminal files.

Unresolved concern: delimiter-heavy verification has no qualified latency or
prompt-cancellation bound. It is expressly deferred, without adding a fifth
implementation-ready consolidation item. No other review concern remains
unresolved; overruled findings and proof limits above remain part of acceptance.

## Rollback and stop

Rollback removes the additive verifier and retry surface through the authorized
repository workflow while preserving historical files, default append behavior
and existing recovery. No outbox repair or migration is performed. The work-stage
and terminal provider disposition is
`V0100_REPORTING_CONSOLIDATION_SLICE_QUALIFIED`. Git finalization remains
dispatcher-owned. The three reporting census items
are delivered in this candidate; only JS-QD-001 through JS-QD-004 remain
implementation-ready. External gates and condition-triggered/optional work are
unchanged. No automatic successor.
