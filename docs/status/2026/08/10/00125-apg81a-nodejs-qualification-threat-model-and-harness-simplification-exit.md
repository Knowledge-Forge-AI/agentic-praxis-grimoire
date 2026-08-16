# APG81A Node.js Qualification Threat-Model and Harness Repair Checkpoint Exit

Phase ID: `APG81A`

## Status

Complete — Node.js threat-model and harness correction preserved, integration
blocked by one High rollback finding and one Medium lifecycle-index finding,
ADR 0046 remains Proposed, and the candidate remains repair-required without
rejection or removal.

## Result

- Preserved exact APG80, APG81, and APG81A correction history and managed
  reports.
- Retired immutable-flag, protected-parent, flag-restoration, and copied-runtime
  sealing machinery under a controlled local-or-CI qualification contract.
- Preserved direct exact primary and secondary runtime pre/post observation,
  private invocation scratch, closed environment, bounded diagnostics,
  attempt-all cleanup, and zero continuous-identity or hostile-same-UID claim.
- Confirmed fresh zero-finding review of the immutable correction and zero Node
  debt.
- Stopped terminal integration after fresh review found one High rollback
  defect: the disposable rollback deleted the Node candidate instead of
  preserving it in the resulting state.
- Also retained one Medium finding: the attempted ADR index detached ADR 0045
  from its status and listed ADR 0046 twice with contradictory Accepted and
  Proposed states.
- Removed the attempted integration bytes without repairing forward, accepting
  debt, rejecting the candidate, or changing an integration owner.
- Left ADR 0046 Proposed and `nodejs-runtime-profile` corrected,
  repair-required, branch-only, and unintegrated at 33/32/32.
- Preserved exact APG79E main at 32/32/32, 14 stable / 18 provisional, and 30
  general / one ChatGPT-local / 31 checked routes.
- Preserved all ten CSS/JavaScript debt entries, corrected historical/public/
  active v0.4.0, and both unmodified, unexecuted targets.

## Next boundary

A new human continuation decision is required. No Node integration, debt
acceptance, mainline adoption, stable maturity, target command, readiness,
publication, deployment, rejection, removal, APG82, or successor work is
authorized by this exit.
