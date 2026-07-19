# ADR 0005: Public License and Contribution Governance

## Status

Accepted

## Date

2026-07-19

## Context

ADR 0001 established Agentic Praxis Grimoire's public-projection boundary but
deferred the distribution license, contribution policy, and public repository
creation. The project is preparing its first public mirror. It has not made a
prior public license grant, has no prior-license baseline to preserve, and has
not accepted outside contributions.

The project steward wants a recognized open-source community license that
requires source availability for modified network-service deployments while
retaining the ability to offer proprietary commercial terms. Future outside
contributions must preserve the steward's ability to sublicense and relicense
accepted contributions as part of the Project.

## Decision

1. Agentic Praxis Grimoire is licensed under the GNU Affero General Public
   License v3.0 or later (`AGPL-3.0-or-later`).
2. The complete AGPL v3 text is recorded in `LICENSE`. The `or later` election
   is stated in the repository's licensing notices.
3. Samuel Lair is the Project Steward. Copyright remains with the Project
   Steward and individual contributors.
4. The Project Steward may offer separate commercial licenses for proprietary
   terms. The AGPL remains available for uses that comply with its terms,
   including commercial uses.
5. Contributions require acceptance of `CLA.md`. Contributors retain copyright
   while granting the Project Steward and authorized successors the copyright
   and patent rights needed to distribute accepted contributions under the
   AGPL, commercial licenses, and future Project licenses.
6. Pull requests must affirmatively include this exact acknowledgment, either
   by marking its checkbox or stating it directly:

   ```text
   I agree to the Agentic Praxis Grimoire contribution terms in CLA.md.
   ```

   A `Signed-off-by` line does not replace the acknowledgment.
7. Patent rights granted to downstream recipients arise only under the Project
   license the recipient receives, such as the AGPL or a separate commercial
   license granted by the Project Steward or an authorized successor.
8. This is the Project's first public license grant. No prior public license,
   release, tag, or grant is superseded or revoked.
9. Third-party material remains governed by its own license and notice terms.
   The current provenance record identifies no copied or adapted third-party
   expression requiring a bundled third-party license notice.

The aligned governance surface consists of `LICENSE`, `README.md`,
`COMMERCIAL-LICENSE.md`, `CONTRIBUTING.md`, `CLA.md`, `NOTICE`, and
`.github/pull_request_template.md`. The repository currently has no package
metadata license field or source-file header convention to update.

## Alternatives considered

### Apache License 2.0, MIT License, or another permissive license

Rejected for the initial public grant. A permissive license would allow
proprietary network-service forks without a corresponding source-availability
obligation and would weaken the intended commercial-licensing model.

### GNU General Public License v3.0 or later

Rejected in favor of the AGPL because the GPL does not add the AGPL's specific
source-availability condition for modified versions used over a network.

### AGPL without commercial licensing or a CLA

Rejected. AGPL-only distribution would not provide negotiated proprietary terms,
and accepting contributions without adequate grants could prevent the Project
Steward from licensing the combined Project commercially.

### A custom noncommercial or source-available license

Rejected. A custom restriction would reduce open-source clarity and ecosystem
compatibility without a demonstrated need that outweighs a standard license.

## Consequences

- Public recipients receive a standard open-source license with a
  source-availability obligation for modified versions made available to users
  over a network.
- Organizations needing proprietary terms may negotiate a separate commercial
  license.
- Contributions require explicit CLA acceptance and authority to submit.
- Contribution review must preserve third-party provenance, notices, and the
  public/private publication boundary.
- Legal review may still be appropriate for unusual contributors, substantial
  commercial negotiations, or jurisdiction-specific requirements.
- Public mirror creation, release cadence, publication tooling, and the act of
  publication remain separate decisions and operations.

## Deferred decisions

- public mirror creation and hosting;
- release cadence and versioning;
- automated CLA enforcement;
- publication-surface automation; and
- standard commercial-license contract terms.
