# APG97 Deterministic Skill Context Bundles and Agent-Scoped Materialization Exit

Phase ID: `APG97`

## Status

**Complete — deterministic task-scoped skill bundles accepted as the APG98
entry state.**

Terminal disposition:
`V07_SKILL_CONTEXT_BUNDLES_READY_FOR_APG98`.

## Outcome

APG97 embeds all 39 canonical Markdown leaves directly in the public Go
`skills` package, reconstructs and verifies canonical metadata, provides strict
model-free bundle resolution, and atomically materializes exact selected roots
from embedded bytes. Nested ChatGPT source paths remain canonical while target
discovery paths are flattened.

Request, result, selection, composition, and manifest contracts are versioned.
Result identity is order-invariant and includes reasons, source facts,
exclusions, conflicts, selected-only composition edges, content hashes, and
budget measurements. Budgets fail closed without truncation, dropping,
substitution, or partial publication.

Go `skills list`, `context-report`, `resolve`, and `materialize` are available.
Normal Python list/context routes delegate to Go; resolve/materialize are new
Go-backed convenience routes. Python project/user/global/flatten maintenance
remains unchanged.

## Qualification

- The embedded 39-leaf metadata projection hashes to
  `0509803b3c12e0366917a341c9d56945d7966897953415acf0c997254e1331c1`.
- A disposable external Go consumer resolved and materialized through only the
  public `skills` package and verified exact body readback.
- An isolated Codex 0.147 launch discovered exactly the selected APG ID
  `planning-repository-work` and no other canonical APG ID or global APG root.
- Materialized directories/files are 0700/0600 direct regular entries, with
  atomic publication, verified idempotence, collision refusal, and
  cancellation cleanup.
- Build information makes expected/embedded corpus equality explicit and
  release-like mismatch fail closed.

## Preserved state

- Version remains 0.6.0.
- Skills remain 39/39/39/39 and 14 stable / 25 provisional.
- Discovery remains zero malformed, 9,504 description bytes, 9,492 characters,
  and the unchanged 9,527-byte ceiling.
- Canonical skill Markdown and current public v0.6 artifacts remain unchanged.
- No live/global skill root, environment, hotspot, response, final wheel/npm,
  JACA, `.flakes`, Nix, publication, deployment, APG98, or APG99 work occurs.

## Next authorization

APG98 was separately authorized to implement the portable environment snapshot
contract. This exit did not itself begin APG98.
