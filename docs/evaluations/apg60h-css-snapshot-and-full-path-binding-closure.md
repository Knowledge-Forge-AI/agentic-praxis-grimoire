# APG60H CSS Snapshot and Full-Path Binding Closure

APG60H completes verification of immutable Claude implementation commit
`25ccebb288ba3530121a94b5f0df48a88d065fef` on exact APG60G commit
`4bd8f216c6c611905c87fd5332f29ec362c5da8b`. Claude truthfully recorded an
environment-blocked result. Codex preserved that object and its four append-only
records, reproduced the blocked lanes under authorized shared scratch, and
completed the phase forward.

## Corrected contracts

The worker receives one validated caller-controlled temporary root outside the
repository. Its stripped environment contains only locale, default executable
path, and identical temporary variables. The parent owns and removes the worker
child after return, timeout, interruption, and launch failure.

Missing, detached, replaced, symlinked, or unrevalidatable path components use
one public-safe error family. Successful absence observes the exact missing
component, revalidates every present ancestor, then observes that component
absent again. Final entries, missing ancestors, and fixed glob prefixes share
this contract. Snapshot cleanup does not chmod through replacement symlinks,
and glob enumeration errors remain inside the repository path boundary.

## K1 through K4

- K1 requires exact declared bytes, completed short reads, and explicit EOF.
- K1B requires lexical cleanup absence and truthful failure ordering.
- K2 retains present chains and double-observes absent components.
- K3 checks the pinned root immediately before successful return.
- K4 retains no-follow projection identity and fails closed by platform.

## Versioned and preserved state

The manifest and removal plan advance from schema 6 to 7, test inventory from
1 to 2, and APG60H phase history to schema 3. APG58 through APG60H are the
foundation; APG61 is authored Proposed unintegrated; APG61 and APG62 are the
terminal histories. APG60H consumes exit `00088`; future exits are `00089`
and `00090`.

All sixty CSS cases and 300/600/900 remain unchanged. CSS is absent; ADR 0035
is Rejected; ADR 0036 is unused. Development remains 28/28/28 and 14 stable /
14 provisional. Corrected public and active v0.4.0 are unchanged. No target,
candidate, readiness, publication, deployment, APG61, or successor work ran.

## APG60I subsequent correction

APG60H remains adopted through explicit maintainer direction with known review
exceptions. APG60I corrects forward the temporary-root substitution and
pre-cleanup residue defects; it does not rewrite this disposition or claim the
APG60H implementation had already satisfied those corrected contracts.
