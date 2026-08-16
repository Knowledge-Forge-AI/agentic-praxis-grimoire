# APG60F CSS Import, Owner, and Projection Closure Exit

Date: `2026-07-30`
Phase ID: `APG60F`
Exit ID: `00086`

Target result: Complete — dynamic import provenance, required lifecycle roles,
and coherent projection observation closed before CSS authoring.

APG60F preserves accepted APG60E and the unchanged sixty-case CSS contract.
The correction closes repository-local transitive import provenance and cache
isolation, makes all 52 lifecycle roles and their cross-references exact, and
revalidates the projection and canonical target as one bounded observation.

Terminal evidence:

```text
unit: 1019 passed
integration: 552 passed; 2 expected skips; coverage gate passed
integration observations: 6402-6404/7279 statements; 2149-2151/2686 branches
combined: 1019 unit and 552 integration passed; 2 expected skips
combined-union observations: 6804-6806/7279 statements; 2416-2418/2686 branches
configured Bats: 23 passed
all five actual lifecycle states: passed
independent non-author review: accepted
```

Current state remains:

```text
active CSS candidate: absent
ADR 0035: Rejected
ADR 0036: unused
skills/catalog/projections: 28/28/28
maturity: 14 stable / 14 provisional
public: corrected v0.4.0 unchanged
active: corrected v0.4.0 unchanged
APG61: recommended, not begun, not authorized
```

APG60F consumes exit `00086`; future APG61 and APG62 exits are `00087` and
`00088`. No authoring, integration, target operation, publication, deployment,
or successor work is authorized by this exit.
