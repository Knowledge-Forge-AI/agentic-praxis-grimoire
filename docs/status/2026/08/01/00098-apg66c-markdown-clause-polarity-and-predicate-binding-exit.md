# APG66C Markdown Clause-Polarity and Predicate-Binding Exit

Phase ID: `APG66C`

Date: 2026-08-01

Result: Complete — accepted Markdown semantics are preserved while coordinated
predicates, clause polarity, targeted contradictions, and the repository-import
cache-restoration test boundary are closed with order-independent evidence.

## Terminal state

- APG66, APG66A, and APG66B: accepted and unchanged;
- APG66C: complete;
- `markdown-language-profile`: retained provisional;
- ADR 0037 and ADR 0038: Accepted with amendment;
- skills/catalog/projections: 29/29/29;
- maturity: 14 stable / 15 provisional;
- general/ChatGPT-local/checked routes: 27 / 1 / 28;
- CSS: absent; ADRs 0031, 0034, 0035, and 0036 Rejected;
- public and active corrected v0.4.0: unchanged;
- targets: unchanged and unexecuted;
- APG67: recommended at exit 00099 and not begun; and
- successor: not authorized.

The first invocation's exact blocked Git-diff and associated operational records
remain preserved. Continuation authority reproduced the isolated whole-cache
assertion, narrowed it to relevant repository-import state without changing
production importer bytes, and proved isolation in both orders, repeated in one
process, around Markdown owners, and through xdist.

Final Markdown owners pass 1,386 unit tests and 1,391 with integration. C1
owners pass 45 tests. Terminal regression passes 2,614 unit tests, 563
integration tests with two expected skips, combined-union coverage of
6,822/7,293 statements and 2,416/2,686 branches, and 23/23 Bats tests.
The APG66C commit is the sole child of exact APG66B; normal mainline and branch
delivery, fetched equality, the four-record omnibus, and exact scratch cleanup
complete the phase.

APG66D later forward-corrected one test-helper entry-presence false pass for a
pre-existing relevant `sys.modules` key whose value was `None`. APG66C remains
accepted; its C1 bounded-state design, production importer, Markdown semantics,
ADRs, and delivered history are unchanged.
