# APG107 v0.8.1 Qualification and Recovery Exit

Phase ID: `APG107`

## Status

**Historical work-stage checkpoint — the earlier preparation and verification
claims were withdrawn on 2026-09-05 after independent review found source,
documentation, and evidence defects. This record is retained for history and
does not establish current qualification or publication.**

Terminal disposition: `V081_RELEASE_CANDIDATE_CORRECTION_REQUIRED`.

> **Historical claim notice (2026-09-05):** The qualification and all-green
> statements below describe the earlier APG107/APG108 checkpoint and are
> retained as historical record. They are superseded for current use by the
> APGR-V081-CORRECTION1 source-correction phase. The corrected source must
> complete the required qualification before a later freeze disposition; this
> record does not announce source-freeze or publication readiness.

## Scope and decisions

1. **Predecessor immutability**: Preserves the public v0.8.0 Git commit (`fc0fd99b41d24951d7db3535402c46ef9c671143`), annotated tag (`aa83b64f019b92e211154cd246b939f3fc62ac91`), sole parent (`718344778e937629b8db7e164ae600a95142c05d`), and Go module proxy entries without force-pushing, retagging, or deletion.
2. **Release-line recovery (historical, superseded 2026-09-05)**: The earlier checkpoint described v0.8.1 as a single-parent child of public v0.8.0 and as a complete synchronized release. That statement is withdrawn; source freeze, final identities, and downstream publication were not established by this record.
3. **Product semantics preserved**: Retains all v0.8.0 code and public package behavior. Zero public API changes.
4. **Human-facing documentation and presentation**: Comprehensive rewrite of root `README.md` around user success and first use; full audit of first-hop documentation; updated Python `pyproject.toml` long description and project URLs; packaged npm launcher and platform READMEs; and prepared GitHub repository About metadata transaction (`https://www.knowledge-forge.ai/agentic-praxis-grimoire/`).
5. **Publication-excluded release packets**: Retains the canonical authority and
   fail-closed publication-executor packets for release operations outside the
   public documentation projection.

## Evidence state

- **Historical Go evidence**: The earlier packet recorded `gofmt`, `go vet ./...`,
  `go test -count=1 ./...`, and `go test -race -count=1 ./...` as passing; this
  record does not re-attest those results against the corrected source.
- **Historical Python and npm evidence**: Earlier distribution, packaging,
  backend, CLI, publication, launcher, metadata, tarball, and install claims
  are retained as prior packet observations and are not current acceptance.
- **Documentation audit**: The earlier all-green audit claim is withdrawn; the
  correction phase supplies fresh, command-bound link, example, and rendering
  evidence separately.
- **Historical zero-mutation observation**: The earlier packet reported no
  public ref, registry, or global-state mutation; this remains historical
  evidence and is not a publication result.

## Correction and supersession addendum (2026-09-05)

Following independent review under `APGR-V081-CORRECTION1`, this qualification record was amended:

The initial documentation-audit, package-availability, and complete-candidate
claims above are not current evidence. The correction phase found that the
first-use README contained an unsupported footprint command, the root README
advertised unpublished v0.8.1 installs, and the retained summary did not bind
its counts to inspectable commands, source trees, logs, or digests. Those
claims are superseded rather than re-used. Fresh source-correction evidence is
retained in the phase evidence packet; final asset reconstruction, production
wrapper qualification, and live registry readback remain deferred to the
subsequent source-freeze/publication boundaries.

1. **Packaging durability across versions**: npm template READMEs and Python backend metadata projection were parameterized and decoupled from the version literal `0.8.1` so that future release lines (e.g. `0.10.0+`) preserve metadata projection and README packaging.
2. **Predecessor invariants tightened**: Verification was expanded to assert that historical predecessor v0.8.0 remains absent from GitHub Releases, PyPI, and npm, while preserving immutable Go proxy module sums and Git commit metadata.
3. **Source freeze binding & readiness**: Candidate assets and interim manifest
   states built prior to full source correction are superseded and
   non-publishable (`readiness.status = "pending_source_freeze"`). True
   publication readiness requires an explicit source-freeze binding of the
   finalized commit.

4. **Documentation and evidence correction**: The maintained examples now use
   the live footprint CLI and valid Go types, with disposable absolute `0600`
   fixtures and executable assertions. The corrected evidence separates local
   source checks from deferred production-freeze obligations; no source-phase
   check is a final ten-asset rebuild, publication, or live registry pass.
