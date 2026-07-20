# Superpowers Decommission and Rollback Runbook

## Status and authority

This is a human-owned operational runbook. The maintainer completed the
controlled decommission operation and bounded post-decommission smoke before
APG9. The sequence remains historical operational and rollback guidance; it
does not authorize restoration or another plugin mutation.

Superpowers is retired from the maintainer's workflow. Preserved source remains
reference evidence. The `apg-project-skills` command manages only opted-in
repository projections and must never install, disable, remove, restore, or
configure a global plugin.

The human maintainer owns readiness acceptance, the decommission decision,
global plugin controls, rollback authority, and final disposition. Stop if the
current Codex product does not expose a supported control for the intended
global action.

## Completed-operation disposition

The maintainer's explicit decision, completed decommission, and accepted fresh
RepoMap smoke supply the authorized v0.1 closeout facts. The smoke discovered all six APG
skills, explicitly applied the review skill, passed default and explicit
managed checks, preserved the tracked repository, and did not use Superpowers
as workflow authority.

Before the operation, APG8 supported these components:

- materially used workflow mapping;
- successful APG use in its own repository;
- successful APG use in one additional real repository;
- preservation of the Superpowers source and provenance snapshot; and
- tested project-local install, adopt, check, and uninstall behavior;
- real-project managed adoption and check; and
- this human rollback runbook.

APG9 reconciles the later outcome rather than rewriting APG8's contemporaneous
record. No rollback was required, and successful restoration remains untested.
The operation does not establish an exhaustive active-project inventory,
automatic skill selection, comparative superiority, or stable maturity.

## Controlled decommission sequence

### 1. Readiness review

Record the date, decision owner, Codex application version, APG revision,
relevant repositories, current evidence, unresolved risks, and rollback owner.
Confirm that every materially used Superpowers workflow has an accepted APG,
native Codex, repository-policy, deferral, or rejection disposition.

Stop if any authority, privacy, destructive-action, completion-evidence, or
representative-workflow regression remains unresolved.

### 2. Verify project-local APG projections

For each repository selected for the smoke, run the APG check command from the
current APG checkout:

```sh
<apg-root>/bin/apg-project-skills check --repo <target-path>
```

Confirm exact managed names, readable canonical leaves, clean normal Git status,
and no tracked target changes. Do not automatically enroll additional projects.

### 3. Preserve the Superpowers source and provenance snapshot

Confirm that the existing publication-excluded source and provenance record is
readable, immutable for the operation, and sufficient to identify the installed
source and applicable license. Do not place local plugin paths, private payloads,
or credentials in public artifacts.

### 4. Record current plugin state

Using current supported Codex inspection controls, record whether Superpowers is
installed and enabled, its observable version or identity, and the control used
to restore it. Store exact local evidence only in an authorized private
operational record. Do not infer configured state from APG skill discovery.

### 5. Obtain the explicit human decision

The maintainer must explicitly approve the named global action, affected Codex
profile, smoke scope, failure criteria, rollback operator, and time boundary.
An APG report, ADR, tool result, or agent recommendation is not approval.

### 6. Disable or remove Superpowers manually

The human operator uses only the currently supported Codex plugin controls for
the approved profile. Do not edit internal plugin files, user configuration,
desktop metadata, or caches directly, and do not ask `apg-project-skills` to
perform the action.

Stop if the supported control is absent, ambiguous, affects a broader profile,
or reports a different plugin state than the readiness record.

### 7. Restart Codex fully

Close and restart the complete Codex application using its supported lifecycle.
Opening a new task without restarting the application is insufficient when the
environment still presents cached discovery state.

### 8. Run APG discovery and representative workflow smoke

In each approved target, verify:

- the intended APG project skills are discoverable;
- Superpowers workflows are no longer presented as active governing procedures;
- one representative design or planning trigger routes correctly;
- one representative implementation or verification trigger routes correctly;
- one material non-trigger remains proportional;
- repository authority, privacy, tracked state, and required completion evidence
  remain intact; and
- `apg-project-skills check` still passes.

Record actual invocation only when observable. Do not treat filesystem
projection or skill listing alone as invocation evidence.

### 9. Apply failure criteria

Rollback is required when any approved smoke target shows:

- missing or unreadable required APG discovery;
- loss of a materially required workflow with no accepted disposition;
- authority expansion, privacy leakage, unsafe destructive behavior, or weakened
  completion evidence;
- persistent application or plugin inconsistency after the required restart;
- target tracked-file mutation or invalid projection ownership state; or
- an unresolved result that exceeds the approved smoke window.

Do not broaden the phase into plugin debugging, unsupported configuration
editing, APG skill promotion, or emergency framework development.

## Rollback sequence

### 10. Restore Superpowers through supported controls

The human operator reverses the exact approved global action using the supported
Codex control recorded before decommissioning. Restore the prior observable
plugin identity and enabled state. Do not reconstruct plugin files or internal
configuration manually.

If supported restoration is unavailable or ambiguous, stop and escalate to the
human maintainer. APG project projections may remain installed; they do not
replace a failed global restoration operation.

### 11. Optionally remove APG project projections

If rollback policy also requires removing local APG discovery, run:

```sh
<apg-root>/bin/apg-project-skills uninstall --repo <target-path>
```

Use `check` first when state is uncertain. The command removes only valid
state-owned links and its Git-local exclusion block. It does not remove
canonical APG skills or restore Superpowers.

### 12. Restart and run post-rollback smoke

Restart the full Codex application again. Verify the restored Superpowers state,
the intended APG projection state, representative workflow availability,
material non-trigger behavior, repository authority and privacy boundaries, and
clean target tracked state.

Record whether rollback fully restored the pre-decommission condition, what
remains unresolved, and the human maintainer's terminal disposition. A failed or
partial rollback stops further decommission attempts.

## Evidence and disposition

Keep a bounded private operational record containing the decision, supported
control categories, before-and-after state, smoke results, failure or rollback
trigger, and terminal human disposition. Do not retain credentials, raw private
payloads, private source content, or local paths in public records.

This runbook originally satisfied the rollback-plan documentation component of
the gate. APG9 accepts the subsequent human action and bounded smoke as the v0.1
decommission closeout while retaining the unverified inventory, universal-
coverage, and restoration dimensions as limitations. The preserved rollback
sequence remains available only under a new explicit human authorization; APG9
does not restore or test restoration.
