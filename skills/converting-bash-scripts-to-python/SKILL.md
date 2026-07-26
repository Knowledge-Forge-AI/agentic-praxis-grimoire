---
name: converting-bash-scripts-to-python
description: Use when an existing Bash executable or script family needs a bounded conversion to Python that preserves or deliberately migrates its observable contract.
---

# Converting Bash Scripts to Python

## Core principle

Convert an existing Bash executable or coherent script family only for an
accepted migration goal, and preserve every required observable contract unless
a deliberate contract change has separate authority, migration evidence, and
rollback. Characterize behavior before replacing it. A successful Python
implementation is not equivalent merely because its happy-path output looks
similar.

Keep this skill as the migration procedure. Use `bash-language-profile` for
material Bash semantics, `python-language-profile` for material Python
semantics, and the applicable APG process skill for implementation or review.
The target project retains platform, dependency, packaging, release, and
action authority.

## Do not use

Do not use this skill for:

- a trivial new Python script with no existing Bash contract;
- a Bash script that remains the clearest, safest, and best-supported
  implementation for the required task and platforms;
- a mandate to convert every shell script or pipeline;
- generic Bash or Python implementation, debugging, or review guidance;
- selecting Python, Bash, GitPython, a package manager, a dependency, a target
  platform, or a release mechanism for the project;
- unrelated refactoring, cleanup, feature work, or architecture change bundled
  into a conversion;
- inventing Windows or other platform support the project does not require;
- replacing a sourced Bash library without inventorying its shell-level
  callers and state contract; or
- migration, publication, deletion, or destructive action without exact
  authority.

## Procedure

1. Confirm the **authority and migration goal**. Name the exact executable or
   script family, allowed write scope, preserved consumers, intended benefits,
   accepted behavior changes, delivery boundary, and completion authority. If
   the goal is only aesthetic preference, retain the current owner.
2. Establish **current interpreter and platform support**. Record supported
   Bash and Python versions; Windows, macOS, Linux, or narrower platform scope;
   Git and other executable versions; installation and invocation paths;
   filesystem capabilities; locale; and packaging. Do not claim untested
   portability.
3. Inventory **CLI arguments and help**. Capture entry paths, shebang or
   launcher behavior, argument grammar, defaults, ordering, repeated options,
   `--` handling, help and usage bytes, invalid-input diagnostics, callers, and
   whether the file is executed, sourced, or both.
4. Characterize **stdin, stdout, and stderr** independently. Record text versus
   bytes, encoding, newline and terminal behavior, buffering, stream routing,
   pager suppression, pipeline consumers, empty output, and broken-pipe
   behavior. Keep machine-consumed stdout free of diagnostics.
5. Freeze **exit codes** for success, usage error, input rejection, dependency
   failure, partial work, interruption, timeout, and internal failure. Preserve
   signal-derived behavior where it is part of the supported contract, and do
   not collapse distinct failures into a generic success or failure.
6. Map **environment variables and locale**. Classify inherited, overridden,
   defaulted, exported, removed, and protected values. Preserve deterministic
   locale, pager, Git, temporary-directory, and test-injection behavior without
   exposing secrets or private paths.
7. Map **cwd and path resolution**. Distinguish caller cwd, repository root,
   script location, module resources, user directories, temporary roots,
   relative operands, symlinks, case sensitivity, path separators, non-ASCII
   names, and names containing whitespace or control characters.
8. Characterize **file modes, ownership, and links**. Record regular-file and
   directory checks, symlink rejection or preservation, hard-link constraints,
   ownership, permissions, umask, executable bits, metadata changes, and
   platform-unavailable concepts. Fail closed when the contract requires an
   unsupported check.
9. Preserve **atomicity and locking**. Map temporary-file location, private
   permissions, same-filesystem replacement, flush policy, lock acquisition,
   owner identity, contention, retries, unsafe/stale lock handling, append
   serialization, destination revalidation, and failure injection. Verify that
   preexisting destination bytes survive every pre-replacement failure.
10. Preserve **signals, interruption, and cleanup**. Inventory traps, cleanup
    order, lock release, temporary state, child processes, double-failure
    behavior, termination escalation, timeout handling, and observable status.
    Python signal and process behavior differs across platforms; design the
    required platform contract explicitly.
11. Preserve **subprocess argument vectors**. Prefer an explicit executable and
    argument sequence with shell interpretation disabled. Record cwd,
    environment, encoding or raw bytes, stdin, captured streams, expected
    statuses, timeout, process-group ownership, and cleanup. Never flatten
    untrusted or structured arguments into shell text. Keep executable and
    option tokens fixed or drawn from a trusted allowlist. Validate untrusted
    operands and place the interface-specific end-of-options marker before
    them where it is supported and preserves the contract. Disabling shell
    interpretation does not by itself prevent argument or option injection.
12. Preserve **Git semantics**. Freeze repository discovery, revision
    verification, object type, root and parent selection, first-parent merge
    behavior, rename detection, binary treatment, path quoting, configuration,
    pager and color suppression, external-diff and textconv suppression,
    staged/unstaged/index behavior, output bytes, error classes, and supported
    Git versions. Verify real disposable repositories rather than approximating
    Git in Python.
13. Bound **security and protected data**. Trace arguments, environment,
    repository data, paths, report bodies, errors, logs, temporary state, and
    generated artifacts. Remove dynamic shell interpretation where possible,
    validate destructive targets, use private temporary state, and sanitize
    durable output without weakening the required exact private payload.
14. Build **characterization tests** before implementation. Cover positive,
    invalid, empty, boundary, failure-injection, interruption, concurrency,
    path, byte, mode/link, Git root/merge/binary/rename, and platform cases
    proportionate to the contract. Record known uncharacterized behavior as a
    stop, not an assumption.
15. Design the **Python package, module, and entry point**. Separate reusable
    model and adapters from CLI parsing; avoid import-time I/O; keep `main()`
    return/exit ownership explicit; preserve invocation from installed and
    repository contexts; and follow project packaging without adding a
    dependency or release change implicitly.
16. Decide **shell wrapper retention or removal**. Retain a thin wrapper when
    callers, executable paths, shebang behavior, or rollout require it, and
    test exact argument, environment, stream, and exit passthrough. Remove it
    only when all consumers and projections are migrated and rollback remains
    viable.
17. Plan **compatibility rollout**. Run old and candidate implementations
    against the same characterized cases, compare exact observable results,
    shadow when risk warrants, migrate callers and release projections
    deliberately, and record any intentional divergence as a contract change.
18. Define **rollback** before cutover. Preserve an exact retrievable prior
    owner, reversal steps, wrapper or entry-point restoration, dependency and
    packaging reversal, data/destination invariants, and the evidence that
    decides rollback. Do not delete the old owner before the accepted boundary.
19. Update **documentation and release projection** only within authority.
    Reconcile help, operator guidance, supported platforms, packaging,
    projections, tests, deprecation notices, ownership, and removal records.
    Complete with observed compatibility evidence, deviations, unresolved
    limits, rollback, and actions deliberately not performed.

### Conversion decision guide

Retain Bash when shell syntax materially expresses a small fixed pipeline,
platform-specific lifecycle, or direct shell integration more clearly and
safely than a Python replacement, and the project has no accepted migration
need. A line count or general Python-first preference is not sufficient by
itself.

Conversion is plausible when the current contract is characterized and an
accepted goal benefits from Python's data modeling, error structure, tests,
cross-platform APIs, or reusable core boundaries. Public CLI compatibility,
locking, atomic replacement, Git fidelity, signal handling, and protected-data
requirements make the migration higher risk even when the source is short.

A script sourced as a library exports a shell API: functions, variables,
options, traps, cwd changes, and process state can all be consumers. Replace it
only through an explicit caller migration or a compatible retained shell
owner. An executable-only Python CLI cannot silently substitute for `source`.

### Git adapter decision

Use the smallest adapter that preserves the required contract:

- Standard-library `subprocess` plus the Git CLI is the baseline when exact
  Git options, object verification, configuration, path quoting, diff bytes,
  exit statuses, or diagnostic behavior control.
- GitPython can be evaluated for a bounded object-model benefit. It still
  depends on Git for most operations, adds a dependency and abstraction
  surface, and must not obscure raw behavior that the contract exposes.
- A bounded combination may use GitPython for a proven high-level operation
  and fixed Git argument vectors for fidelity-sensitive output. Document the
  boundary and test both.
- Reject GitPython or any other dependency when the standard library and Git
  CLI already meet the need or project dependency authority is absent.

Git semantics are approximated rather than verified when a replacement
reimplements revision, merge, rename, binary, quoting, index, configuration,
or error behavior from assumptions instead of testing the selected Git
interface. That is a stop.

### Compatibility and evidence rules

Compare preserved contracts from clean disposable states. Exact compatibility
may require byte comparison, not normalized text. Test root, single-parent,
and first-parent merge commits separately; rename and binary cases; empty
payloads; marker-like untrusted content; whitespace and non-ASCII paths;
concurrent append; lock disappearance; injected generation and replacement
failure; destination symlinks and metadata; and operational association.

For an intentional change, state the old behavior, new behavior, authority,
affected consumers, migration, version or release treatment, adverse cases,
and rollback. Do not label an authorized breaking change behavior-equivalent.

Windows does not share every POSIX mode, signal, executable-bit, shebang,
rename, lock, or path behavior. macOS and Linux can also differ in `stat`,
filesystem, encoding, and utility behavior. Support only the explicit project
matrix, use platform-specific implementation behind one truthful contract, and
mark unsupported behavior rather than emulating it inaccurately.

### Source and maintenance boundary

This skill was inspected and calibrated on 2026-07-22 from Python 3.14.6
standard-library and Windows documentation, current Git CLI documentation,
GitPython 3.1.54, and APG's accepted reporting architecture and current Bash
reporting family. Python documentation is PSF-2.0 with examples additionally
available under 0BSD; Git source is GPL-2.0-only; GitPython is BSD-3-Clause.
APG copies or adapts no external source expression or code; this procedure is
independently written synthesis. GitPython 3.1.54 hardens unsafe Git option
validation; that security delta reinforces the fixed-vector standard-library
and Git CLI baseline rather than selecting the dependency.

These versions are calibration evidence, not mandated project versions,
platforms, adapters, or dependencies. Refresh affected guidance before a
behavior-bearing correction, maturity review, or publication when supported
Python, Git, GitPython, platform, process, filesystem, or packaging semantics
materially change.

Behavior-bearing corrections follow the APG skill authoring and maintenance
guide. Deprecation or removal removes the canonical leaf, checked projection,
catalog and capability-map entries, and focused active tests while preserving
evaluation, provenance, and exit history. Removal of this skill does not
convert, restore, or delete any target script.

## Project-owned parameters

The target repository owns:

- whether conversion is desired and authorized, and the accepted migration
  goal;
- supported Bash, Python, Git, platform, filesystem, locale, and packaging
  versions;
- CLI, stream, exit, environment, path, file, locking, signal, Git, security,
  compatibility, and release contracts;
- dependency, license, supply-chain, package-manager, entry-point, and
  installation policy;
- architecture, wrappers, rollout, shadowing, deprecation, release projection,
  validation, and rollback;
- protected-data classification, report destinations, external resources, and
  artifact retention; and
- mutation, migration, publication, deletion, cutover, and destructive-action
  authority.

Stricter project policy controls. No migration benefit, wrapper, test, or
dependency grants action authority or weakens a superior safety, privacy,
compatibility, or task boundary.

## Evidence and completion

When this skill is material, report:

```text
Migration owner: <script or coherent family>
Goal and authority: <accepted outcome and boundaries>
Platforms and versions: <Bash, Python, Git, OS, filesystem, packaging>
Preserved contracts: <CLI, streams, status, env, paths, files, locks, signals, Git>
Intentional changes: <none or accepted migration>
Characterization: <positive, adverse, failure, concurrency, path, and platform>
Implementation shape: <core, adapters, entry point, wrapper, dependencies>
Compatibility result: <exact, bounded differences, blocked, or deferred>
Rollout and rollback: <consumers, projection, restoration, decision evidence>
Deferred work: <unrelated changes and unsupported platforms>
```

Completion requires fresh evidence from the resulting integrated state. It
does not follow from Python syntax, unit tests alone, a similar help screen, or
one happy-path report. Record every check not run and why. If exact required
compatibility remains unresolved, stop with the smallest next evidence needed.

## Stop or escalate

Stop or escalate when:

- current behavior is not sufficiently characterized;
- migration authority or target platforms are unclear;
- exact CLI or report compatibility cannot be established;
- shell, argument, or option injection or protected-data exposure exists;
- file, lock, or atomic behavior would weaken;
- Git semantics are approximated rather than verified;
- signal, interruption, child-process, timeout, or cleanup ownership is
  unresolved;
- a sourced-library or machine-consumed-stream contract lacks a migration;
- rollback or restoration is missing; or
- unrelated rewrite is required to claim completion.

## Common mistakes

- Treating Python-first policy as authority to replace every Bash script.
- Converting a clear fixed shell pipeline without an accepted project benefit.
- Inventing Windows support or claiming POSIX behavior is portable unchanged.
- Characterizing only the happy path.
- Normalizing bytes, paths, errors, or statuses that consumers observe.
- Flattening a subprocess argument vector into shell text.
- Mocking Git, filesystems, or processes while claiming their integration.
- Assuming `Path.replace`, a temporary file, or a lock library reproduces the
  full current atomic and contention contract automatically.
- Replacing an executable while ignoring sourced callers.
- Adding GitPython or another dependency without a demonstrated bounded need.
- Removing the Bash owner or wrapper before compatibility and rollback gates.
- Bundling unrelated refactoring or new behavior into the migration.
- Calling an intentional contract change behavior-equivalent.
