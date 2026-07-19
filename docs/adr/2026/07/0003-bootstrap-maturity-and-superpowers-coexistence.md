# ADR 0003: Bootstrap Maturity and Superpowers Coexistence

## Status

Accepted

## Date

2026-07-18

## Acceptance authority

The human maintainer's APG4 assignment accepts this decision. ChatGPT and
Codex execute and review only within that assignment; neither source evidence
nor this record expands the authorized phase.

## Context

APG3 truthfully stopped before evaluation because its accepted high-rigor
comparison required an isolated skill profile, an observable invocation event,
and controlled candidate availability and loading. The available environment
did not provide those controls without global plugin mutation or new harness
machinery. No baseline was run and no candidate was authored.

That result establishes a limitation of the APG3 experiment. It does not show
that APG must remain without useful skills until a clean comparison becomes
possible. Superpowers remains installed because other repositories use it, but
its global presence must not make it the workflow authority for APG itself.
APG also needs maturity language that separates provisional usefulness from
strong comparative, stable, or decommissioning claims.

## Decision

### 1. Repository-local coexistence

Superpowers remains globally installed during APG bootstrap. APG suppresses
its workflow authority through repository instructions: Superpowers material
is reference evidence unless a human-authorized task explicitly names a
specific skill for inspection or comparison.

This is a behavioral repository policy. It does not establish that the plugin
is unloaded, absent from model context, or mechanically disabled.

### 2. Source availability and process authority

An available source, installed plugin, worker result, report, or familiar
workflow is evidence rather than APG process authority. Current APG
instructions, accepted APG decisions, and the human-authorized phase define
the workflow.

### 3. Bootstrap before clean comparison

APG may author and retain provisionally useful skills before clean comparative
evaluation. Clean baseline-versus-skill evidence is required for strong
superiority and stability claims, not for bounded bootstrap authorship.

### 4. Maturity states

APG skills use these maturity states:

- `bootstrap`: being shaped and not yet accepted for routine use;
- `provisional`: usable within recorded limits after structural, scenario, and
  independent review;
- `evaluated`: exercised under an explicit evaluation contract with recorded
  results and limitations;
- `stable`: supported by repeated real-project use and the required transition
  review; and
- `deprecated`: retained only for migration, historical compatibility, or
  removal.

These states describe evidence maturity, not authority, installation, release,
or APG's own distribution license.

### 5. APG4 maturity and evidence

Every APG4 skill enters as `provisional`. Structural checks, public-safe
scenario walkthroughs, independent review, and bounded dogfooding are
acceptable evidence for that state. They establish only that the retained
skill is coherent and usable in the recorded examples; they do not establish
causal, statistical, universal, production, or comparative superiority.

No APG4 skill becomes `stable`. Stability requires successful use in more than
one real repository and an explicit review after Superpowers no longer governs
the comparison environment.

### 6. APG3 history

APG3 remains a truthful blocked experiment. APG4 does not rewrite it as a
failed skill, an adequate baseline, or evidence against the candidate. A later
phase may retry clean evaluation when Superpowers is no longer required
globally or a supported isolated profile exists.

### 7. Superpowers transition and decommissioning

APG records a transition map that routes materially used Superpowers workflows
to an APG skill, native Codex capability, repository policy, intentional
deferral, or intentional rejection. Useful principles are preserved through
APG-native synthesis; fixed templates, universal rituals, and project-specific
mechanics are not inherited automatically.

Superpowers decommissioning requires an explicit coverage and rollback gate.
APG4 does not satisfy or authorize that gate and does not uninstall, disable,
update, or modify Superpowers.

### 8. Removal and rollback

Each skill remains independently removable as one direct-child leaf plus its
index, provenance, and evaluation references. A skill that expands authority,
leaks private policy, creates unsafe ceremony, or cannot reach a safe
provisional state within APG4's bounded correction limit is omitted or rolled
back without introducing a compatibility runtime.

## Alternatives considered

### Wait for perfect evaluation before creating any skill

Rejected for bootstrap. It would turn an environment limitation into an
indefinite authorship prohibition and prevent practical dogfooding evidence.
Strong comparative claims still wait for an appropriate evaluation
environment.

### Remove Superpowers globally now

Rejected. Other repositories still rely on it, and APG4 has no authority to
alter global plugin state.

### Maintain two ordinary application profiles through unsupported configuration

Rejected. Unsupported profile construction would create fragile local
machinery and would not by itself prove matched invocation and loading
controls.

### Copy Superpowers unchanged

Rejected. Its procedures contain source-specific assumptions and ceremony,
would duplicate an external workflow, and would not establish APG ownership or
validation. Copied or adapted expression would also require preservation of
the applicable MIT notice.

### Use only informal prompts and no skills

Rejected as the bootstrap default. Informal prompts remain useful, but they do
not provide independently removable, triggerable procedures or a durable
maturity and provenance surface.

### Bootstrap provisional skills with explicit maturity labels

Accepted. It permits useful bounded practice while keeping evidence limits,
rollback, later comparison, and decommissioning decisions explicit.

## Consequences

- APG can begin real use without claiming that APG3's experimental controls
  now exist.
- Repository instructions, not plugin installation state, define the APG
  workflow boundary.
- Users must read maturity labels and evidence limits rather than treating
  skill presence as proof of stability.
- APG carries a continuing obligation to dogfood, review, remove weak skills,
  and retry stronger evaluation when the environment permits it.
- Superpowers remains available elsewhere and remains external MIT-licensed
  evidence for APG provenance.
- APG's own license, publication, packaging, taxonomy, and decommissioning
  decisions remain unresolved.

## Deferred decisions

- clean baseline-versus-skill evaluation;
- promotion of any skill to `evaluated` or `stable`;
- Superpowers decommissioning;
- an isolated profile, adapter, evaluator, scorer, or telemetry framework;
- APG distribution license and contribution policy;
- public release, packaging, registry, or harness projection;
- final category taxonomy; and
- migration of Superpowers workflows beyond the recorded transition map.
