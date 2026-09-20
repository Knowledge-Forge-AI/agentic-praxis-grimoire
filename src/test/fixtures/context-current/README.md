# Current-source F accounting

This is non-qualifying regression input for APG166U-REGRESSION1. The immutable
F-CONTEXT1 baseline remains under `testing/fixtures/context-eval/` and retains
its historical seal. This separate file retains the generator's measurement
schema and phase labels; those labels do not grant historical acceptance to
these current-source bytes.

Generate with an explicitly built current CLI:

```sh
python3 testing/fixtures/context-eval/measure_f.py --root . --binary <current-apgr-binary>
```

Review the output before replacing the current fixture. APG166S-R2 changed the
three provider standing instruction files. Only `standing_source`,
`mandatory_cost`, `payload_cost`, and `content_identity` differ across the eleven
rows. Root metadata, budgets, selected skill identities, decisions, reasons,
static fallback, rule version, scenario tasks and oracles remain unchanged.
The current Go binary with the APG164 standing inputs reproduced the frozen
measurement exactly, isolating this delta to standing-source changes.

Tests use `APG_CONTEXT_BINARY` when supplied; otherwise they use
`build/apgr-context`. Rebuild that default binary from current source before
using it for qualification. This fixture proves no live provider benefit,
recovery, promotion or default-mode change.
