# APG121 v0.9.0 Terminal Publication Reconciliation Exit

Phase ID: `APG121`

## Terminal closeout

Terminal disposition: `V090_NIX_HANDOFF_PROOF_BLOCKED`. Public reconciliation
is `V090_PUBLICATION_RECONCILED_READ_ONLY`. Closeout amended the advisory
pre-final findings, corrected current distribution and npm publication statements,
and declared the three expected refusal exits. Affected documentation and
evidence verification passed; no independent review followed these amendments.
The [APG121 evaluation](../../../../evaluations/apg121-v090-publication-reconciliation.md)
records scope, publication history, evidence, and limitations.

The sealed production read-only check confirms `already_terminal_exact` across
the v0.9.0 public surfaces with no mutation attempts or failure. Exact attended
APG120 terminal result bytes and all four successful npm receipts are preserved.
Earlier failed or unavailable terminal attempt records remain historical.

Current documentation identifies v0.9.0 as publicly released across GitHub
Release, PyPI, npm, and Go. APGR-side JACA CI/XO compatibility is complete;
JACA adoption remains consumer-owned. Linux runtime execution was not part of
v0.9.0 product qualification. Nix adapter updates and host activation remain
separate work. No public mutation, real adapter mutation, host activation,
or successor dispatch occurs during provider-local work. Git staging, commit,
and publication remain dispatcher-owned.

The Nix handoff contains verified identities and hashes. Targeted source, wheel,
release-identity, package-smoke, and package builds pass. The full disposable
adapter check has one failure among 42 tests because its maintained identity
assertion still requires v0.8.1 and its v0.7.0 predecessor. That test is preserved
for the later adapter update; this closeout does not claim a successful full
adapter gate.
