# APG121 v0.9.0 Terminal Publication Reconciliation

Phase ID: `APG121`

## Scope and terminal state

APG121 reconciles publicly released v0.9.0 without replaying publication. This
phase preserves exact attended APG120 terminal evidence, performs fresh read-only
registry observations, updates current development documentation, and prepares
a separately owned Nix adapter handoff. The dispatcher-owned pre-final review
returned advisory findings. Closeout corrected both remaining current publication
statements and documented the three expected nonzero refusal checks. Affected
documentation and evidence checks passed after those amendments; no further
independent review occurred. The full Nix adapter proof remains blocked.

The sealed production read-only resume check returned
`V090_RECOVERY_RESUME_CHECK_PASSED` with `already_terminal_exact`, no failure,
and no mutation attempts. Its expected dirty-development observation includes
APG121 evidence additions; read-only checking does not require a clean worktree.

## Publication history

The first APG119 attended attempt published public Git main and the annotated
tag. Its Go-proxy list propagation stop remains manager-reported because its
overwritten terminal machine result is unavailable. The second attempt found
Git/tag already exact, published the GitHub Release, and completed trusted PyPI
publication before the reader failed on missing `pypi.license_expression`.
Neither earlier attempt is rewritten as terminal success.

APG120 corrected the private recovery metadata and validation. A subsequent
attended execution published all four exact npm packages, with four successful,
non-timeout `performed_and_read_back` receipts, and reached
`already_terminal_exact`. APG121 preserves both terminal result files byte-for-byte
and distinguishes that execution from APG120's historical packet closeout.

## Verification and limitations

Independent public GitHub, PyPI, npm, and Go observations pass, including all
ten downloaded release assets, four PyPI distributions, four npm tarballs and
human-facing READMEs, historical tags, release workflow, and Go proxy/checksum
identity. Public Darwin wheel, public sdist build/install, and registry npm
installation pass representative CLI smokes. Disposable external and XO Go
consumers pass vet, test, and race lanes using public v0.9.0 without replacements.

Terminal disposition: `V090_NIX_HANDOFF_PROOF_BLOCKED`. Public reconciliation
is `V090_PUBLICATION_RECONCILED_READ_ONLY`. Fresh Nix source unpack and actual
fetcher NAR hashes agree; targeted source, wheel, release-identity, package-smoke,
and package builds pass. The full disposable adapter check runs 42 tests with
one failure: its unchanged test hard-codes the v0.8.1 upstream record and v0.7.0
predecessor. This is a maintained adapter test-contract blocker, not a network
or artifact-hash failure. Only the disposable upstream values changed; a later
adapter phase owns updating the release-specific test expectations and rerunning
the full gate. No hashes or tests were weakened.

Record identity, current local links, frozen-input preservation, and whitespace
checks pass. No product-wide requalification suite was run for these Markdown
and private evidence changes.

Frozen v0.9.0 release notes, npm README templates, projection policy, release
artifacts, and historical APG115–APG120 records remain unchanged. Checked-in Go
consumer requirements retain the v0.8.1 control lane. Public v0.9.0 lanes use
separate disposable environments.

APGR-side JACA CI/XO compatibility work is complete for this release. Actual
JACA adoption and activation remain JACA-owned. Linux runtime execution was not
part of v0.9.0 product qualification. Source-distribution installation is consumer
verification, not a rebuilt replacement public artifact.

## Handoff and stop boundary

Nix adapter identity and disposable proof evidence support a later separately
authorized adapter update. The real adapter repository, its lockfile, JACA
repositories, and host configuration are outside mutation scope. No host APGR
installation or activation occurs. Theme Forge and Repo Map remain separate
roadmap scope. No successor is dispatched. Git staging, commits, and pushes
remain dispatcher-owned; provider-local closeout performed none of those actions.
