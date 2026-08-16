# APG66D Repository-Import Cache Entry-Presence Exit

Phase ID: `APG66D`

Date: 2026-08-01

Result: Complete — APG66C import-isolation evidence is preserved while exact
`sys.modules` key presence and stored-object identity are made distinct for
`None` sentinels and all relevant module entries.

## Terminal state

- APG66, APG66A, APG66B, and APG66C: accepted and unchanged;
- APG66D: complete;
- `markdown-language-profile`: retained provisional;
- ADR 0037 and ADR 0038: Accepted with amendment;
- skills/catalog/projections: 29/29/29;
- maturity: 14 stable / 15 provisional;
- general/ChatGPT-local/checked routes: 27 / 1 / 28;
- CSS: absent; ADRs 0031, 0034, 0035, and 0036 Rejected;
- public and active corrected v0.4.0: unchanged;
- targets: unchanged and unexecuted;
- APG67: recommended at exit 00100 and not begun; and
- successor: not authorized.

The failing-first control proved that deleting a pre-existing relevant
`sys.modules` entry containing `None` passed the former `dict.get()` identity
check. The helper now requires explicit key presence before exact `is`
identity. Thirty sentinel controls and a direct import-semantics test close the
gap; relevant importer-cache `None` entries remain covered by their existing
exact key/count/identity implementation. Production repository-import and
accepted Markdown candidate bytes are unchanged.

The cache/import owners pass alone, repeated, in both orders, around the exact
1,386-test Markdown selection, and under configured xdist. Complete regression,
passes 2,646 unit tests, 563 integration tests with two expected skips,
combined-union coverage of 6,824/7,294 statements and 2,417/2,686 branches,
and 23/23 configured Bats tests. Release/lifecycle, privacy/rights, independent
review, normal delivery, fetched equality, associated managed reports, and
exact scratch cleanup complete the phase.
