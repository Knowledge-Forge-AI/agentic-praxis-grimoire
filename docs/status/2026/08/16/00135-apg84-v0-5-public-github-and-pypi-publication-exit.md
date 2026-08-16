# APG84 v0.5 Public GitHub and PyPI Publication Exit

Phase ID: `APG84`

## Status

The exact tracked candidate closes the APG83 publication-enforcement concern
and owns the final v0.5 source, deterministic publication bundle, and Trusted
Publishing workflow. Publication and immutable readback remain external gates;
this tracked record does not self-attest their outcome. The canonical APG84
terminal report and numbered response are the authority for whether the final
disposition is `V05_PUBLISHED_GITHUB_AND_PYPI`,
`GITHUB_PUBLISHED_PYPI_BLOCKED`, `PUBLICATION_BLOCKED_PREMUTATION`, or
`HUMAN_DECISION_REQUIRED`.

## Candidate result

The publication bundle is built twice in disjoint roots at exact epoch
`1700000000`. Both raw sdists pass through the maintained normalizer, both final
wheel/normalized-sdist pairs pass exact metadata and content validation, and
the two three-file bundles must be byte- and mode-identical. The selected
bundle contains only the wheel, normalized sdist, and exact `SHA256SUMS`.

The release workflow has only the `release: published` trigger, uses the exact
`pypi` environment, has only read-content and OIDC-write permissions, downloads
the triggering GitHub Release's three exact assets, verifies checksums before
the publication action, and supplies only the two verified distributions to
the immutable PyPA action commit. It neither checks out nor rebuilds source and
contains no long-lived PyPI token path.

## Preserved state and stop

Topology, maturity, routing, context, and the ten accepted CSS/JavaScript debt
entries are unchanged. Corrected historical v0.4 remains an exact isolated
public predecessor. Nix, the future `agentic-praxis-grimoire-nd` adapter,
`composition-nd`, real `~/.apgr`, active skill deployment, v0.6, target
repositories, the private development remote, and announcements remain
unmodified.

On successful external publication, v0.5 is finished. The recommended next
separately authorized work is the `agentic-praxis-grimoire-nd` deployment
adapter under `~/.apgr/agentic-praxis-grimoire-nd`, consumed by
`composition-nd`; APG84 does not begin it.
