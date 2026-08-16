# ADR 0036: CSS Language Profile from Frozen Contract

- Status: Rejected
- Date: 2026-07-31
- Proposed in: APG61
- Decided in: APG62
- Relates to: ADR 0012 (Accepted; language-profile contract),
  ADR 0029 (Accepted with amendment; unchanged),
  ADR 0031 (Rejected; unchanged), ADR 0034 (Rejected; unchanged),
  ADR 0035 (Rejected; unchanged)

## Context

APG58 authored the first `css-language-profile` pilot. APG59 independently
corrected it, then rejected it and removed its current surfaces; ADR 0035
remains Rejected and is not restored by this proposal. Those phases are
historical evidence and defect input only.

APG60 through APG60I built and hardened the pre-authoring foundation without
authoring a replacement candidate: they froze the candidate-independent
behavior contract of sixty cases (`APG60-CSS-001` through `APG60-CSS-060`)
with its counting, policy, task, authority, semantic, exclusion, legacy,
exception, and lifecycle expectations, and closed traceability, authority,
lifecycle, repository-path, import, snapshot, phase-history, projection, and
temporary-storage defects in the maintained evaluators. ADR 0036 was reserved
but unused through APG60I.

APG61 is a candidate-only authoring phase: it starts from exact APG60I and
authors one genuinely fresh candidate against the frozen contract, without
integrating it.

## APG61 proposal

Propose one fresh `css-language-profile` candidate consisting of:

- the candidate leaf `skills/css-language-profile/SKILL.md`;
- the specification `docs/specs/css-language-profile.md`;
- the traceability map `docs/specs/css-language-profile.contract-map.json`,
  binding all sixty frozen cases to stable normative clause markers with
  exact frozen selected owners, sorted required and forbidden actions, and
  rollback booleans.

The candidate is freshly authored behavioral synthesis. It is not a
restoration of the ADR 0035 pilot and does not copy the APG58 leaf or
specification with patches; APG58/APG59 served only as historical evidence
and defect input.

The growth policy is explicit candidate policy: nonblank physical lines in
ordinary handwritten standalone stylesheets (`.css`, `.module.css`) with
Green below 300, Yellow 300–599, Orange 600–899, and Red at 900 or more.
The numbers 300/600/900 are policy-selected, not corpus inference, and are
not tuned from source or target review.

The candidate owns material CSS-language semantics and the growth policy,
and explicitly routes non-owned concerns — design, brand, token meaning and
value, HTML semantics, browser APIs, browser-support acceptance,
accessibility requirements and outcomes, host-framework conventions,
packaging, build, formatting and lint ownership, deployment, content — back
to their owners. It preserves the frozen one-count rule, the exclusion
families, legacy Red behavior, complete-task aggregation, projection-overrun
response, the authority hierarchy (with artifact exceptions owned by their
real grant source), and the bounded-exception model.

APG61 is authoring only. No catalog row, projection, route, maturity row,
release surface, candidate fixture, focused candidate test, test-inventory
owner, public surface, active surface, or target surface is added; every
current candidate-state marker remains `absent`; integrated development
counts remain 28/28/28 with 14 stable / 14 provisional maturity.

## APG62 decision

Reject the candidate after independent validation and one permitted coherent
correction. APG62 verified and remotely delivered the exact immutable APG61
authoring object, independently reconstructed all sixty frozen outcomes, and
confirmed that the authored map was mechanically exact but semantically
insufficient in seven clause-navigation and contradiction areas.

The single correction clarified Red decomposition, governing-state precedence,
rollback navigation, operation-class ownership, generated and embedded
aggregation, growth-state action ownership, and exact project-owner routing.
Corrected-state review then found a new material mismatch: the correction made
every counted decision require `record-growth-state`, while frozen cases 027,
029, and 033 through 036 deliberately omit that action. APG62 permits no second
semantic correction, so acceptance and acceptance with amendment are closed.

All current candidate artifacts and validation-only candidate tests are
removed. No catalog, projection, route, maturity, project, release, public,
active, or target owner is added. Development returns to 28 canonical skills,
28 catalog rows, 28 projections, and 14 stable / 14 provisional maturity while
this Rejected ADR and the complete APG61/APG62 evidence history remain.

## Alternatives considered

- Restore or patch the APG58 pilot: rejected — APG59's rejection stands, and
  the frozen contract demands candidate-independent behavior, not a repaired
  pilot.
- Author and integrate in one phase: rejected — integration without
  independent validation is exactly the failure mode the APG60 series was
  built to prevent.
- Derive new thresholds from the target corpus: rejected — the frozen
  contract fixes 300/600/900 as explicit policy, and target placement is not
  threshold authority.
- Author another Web/Node profile alongside CSS: rejected — every other
  Web/Node candidate remains deferred.

## Consequences

- The APG61 authoring object remains immutable evidence on its preserved
  branch; its Proposed state is historical, not current acceptance.
- No current integration surface references the candidate, and every current
  narrative marker remains `absent`.
- A later candidate would require fresh human authority and a new decision;
  this rejected candidate receives no automatic correction or successor.

## Deferred decisions

- Any new CSS candidate or successor phase requires separate human authority.
- Publication, deployment, readiness, and activation are outside both APG61
  and this ADR.
