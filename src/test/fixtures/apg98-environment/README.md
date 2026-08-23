# APG98 environment fixtures

These are bounded, APG-owned fixtures for the portable environment snapshot
slice. They characterize the current `.flakes` environment subsystem without
making that subsystem a test-time dependency and without copying an operator's
environment. All values and paths in this directory are synthetic; a path such
as `/fixture/apg98/bin` is a value chosen for a fixture, not a host path.

The fixtures are data, not product defaults and not a secrets store. The
`APG98-*` names are deliberately non-sensitive. `SSH_AUTH_SOCK` is present
only as a source-compatibility case: it is an access-capability socket path,
not credential material. APG's sensitive-name policy therefore permits this
specific capability-path shape while refusing password, secret, credential,
token-material, private-key, cookie, and session-credential names.

## Inventory

| File | Purpose |
| --- | --- |
| `provenance.json` | Read-only source binding and fixture ownership facts. |
| `profile-all-validators.json` | Canonical profile-shaped input with every validator family, one optional missing row, and the deliberate `SSH_AUTH_SOCK` capability row. |
| `profile-invalid-cases.json` | Strict-profile and allowlist rejection cases: duplicate keys/names, unknown fields/validators, malformed names/limits, controls, and invalid defaults. |
| `capture-environment.json` | Explicit synthetic map used to exercise deterministic capture, empty/missing handling, and unlisted-name exclusion. |
| `expected-capture.json` | Values-free expected shape for entry order, missing optional state, and explicit provenance. Fingerprints are calculated by the implementation. |
| `flakes-project-rows.tsv` | Bounded project-profile rows preserving current `.flakes` names, validators, limits, and required/default shape with sanitized fixture defaults. |
| `flakes-sync-rows.tsv` | Bounded sync-profile rows, including `SSH_AUTH_SOCK`, preserving current source semantics with sanitized fixture defaults. |
| `parser-safe.env` | Parser-safe comments, blank lines, plain/export assignments, shell quoting, and duplicate assignment behavior. |
| `parser-invalid-cases.json` | NUL/CR, invalid-name, unsupported-line, and malformed-quote cases represented without embedding control bytes in a source file. |
| `shell-and-hook-cases.json` | Bash/Zsh detection, `env-file`/`sync` defaults, metadata/no-churn observations, and prompt-hook contract cases. |

The two `flakes-*.tsv` files are semantic fixtures, not byte-for-byte copies
of live allowlists. Names, validator IDs, limits, and required flags are kept
only where needed for the bounded parity matrix; defaults are synthetic or
blank so the fixture cannot capture an operator value. The exact live source
commit, tree, and six file blobs are recorded in the publication-excluded
APG98 source-binding evidence.

## Current-source boundaries represented here

- Allowlist input is strict UTF-8 TSV with the six current columns. Names are
  exact environment names; wildcard names, duplicates, unknown validators,
  non-positive limits, and non-boolean required flags fail.
- All twelve current validator families have an accepted and rejected case in
  `profile-all-validators.json`'s companion matrix. Common checks cover UTF-8
  byte limits, controls, and the case-insensitive `null` sentinel.
- Capture visits the explicit map only. A missing or empty required value is an
  error; a missing or empty optional value is listed as skipped. Defaults are
  metadata and are never inserted.
- The old snapshot renderer is shell export text with `shlex`-style quoting,
  owner-only 0700/0600 output, same-content no-churn, and optional metadata.
  APG's canonical representation is strict JSON instead; shell text is only a
  separately authorized adapter concern.
- The old run parser accepts comments, blanks, `NAME=value`, and
  `export NAME=value`, applies shell quoting, lets the last duplicate win, and
  launches exact argv with an inherited-environment overlay. It does not
  source arbitrary shell code.
- The old hook detects Bash or Zsh, silently no-ops when `env-snapshot` is
  unavailable, refreshes immediately, refreshes each Zsh `precmd`, and adds a
  single Bash `PROMPT_COMMAND` entry. Failures remain non-fatal and quiet.

No fixture executes a command, sources a shell file, reads ambient
`os.Environ`, touches `.flakes`, or writes a live snapshot. Consumers should
copy these data files into disposable scratch when a test needs mutation.
