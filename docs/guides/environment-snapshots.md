# Portable Environment Snapshots

This guide is the current human-facing owner for strict profiles, canonical
snapshots, safe storage, and isolated or overlay resolution.

APG provides a provider-neutral Go `envsnap` package for explicit environment
profiles, snapshots, storage, loading, and resolution. The package is
importable without `cmd/apgr`, Python, a shell, Nix, or a `.flakes` checkout:

```go
import "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/envsnap"
```

`.flakes` remains the operational authority for its own profiles, shell hook,
and live snapshot files. APG's portable semantics are qualified against that
implementation but do not change it or activate a cutover.

## Public API

The library call surface is deliberately small and context-aware:

```go
func ValidateProfile(profile Profile) error
func Capture(ctx context.Context, request CaptureRequest) (Snapshot, error)
func Store(ctx context.Context, request StoreRequest) (StoredSnapshot, error)
func Load(ctx context.Context, request LoadRequest) (Snapshot, error)
func Resolve(ctx context.Context, request ResolveRequest) (ResolvedEnvironment, error)
```

`CaptureRequest` carries one explicit caller-owned `map[string]string`, a
validated `Profile`, explicit provenance, and an injectable clock. `Capture`
never reads `os.Environ()` and never mutates the supplied map. `ResolveRequest`
contains a loaded snapshot, an explicit mode, a caller-owned base map for
`Overlay`, explicit overrides, and the profile needed to validate every
profile-owned layer. Overrides without a matching profile are rejected.

The package has no provider-specific types and imports no APG `internal/`
package. Filesystem and process adapters remain outside the public API.

## Profile schema

The canonical profile schema is `apg.environment-profile/v1`. A profile has a
schema version, an exact profile ID, and ordered entries. Each entry contains
an exact environment name, one of the twelve validator IDs, a positive maximum
UTF-8 byte count, a required flag, optional default metadata, and a
description. Defaults are validation/documentation metadata only; they are
never inserted into a capture or a resolved environment.

Profile JSON is strict. The reader rejects duplicate keys, unknown fields,
invalid UTF-8, malformed names, wildcard names, duplicate entries, unknown
validators, zero/negative/overflowing limits, invalid required fields, control
characters, and defaults that fail the entry validator. Names follow
`[A-Za-z_][A-Za-z0-9_]*`.

The semantic profile fingerprint covers the schema version, profile ID, and
consequence-bearing entry fields in deterministic name order. Description
wording does not change identity unless it changes a mechanically validated
field.

## Sensitive-name policy

Environment snapshots are curated configuration artifacts, not a credential or
secret vault. APG uses `apg.environment-sensitive-name-policy/v1`, one
versioned, case-insensitive, token-aware name policy,
and fails closed for names that identify password/passphrase, secret,
credential, token material, private-key material, cookie, or session
credentials. The policy does not use a naive substring rule: a lexical token
must be classified in the name context before it is refused.

`token` is a lexical validator name; it does not mean that a value is a
secret. Conversely, `SSH_AUTH_SOCK` is deliberately permitted as a `path`
capability row. It names a socket endpoint through which an agent may be
accessed; it is not itself a private key or token string. The exception is
documented and tested, while names such as `APG98_PASSWORD` and
`APG98_PRIVATE_KEY` are refused. There is no v1 “allow secrets” escape hatch.
The sensitive-name policy governs all profile entries, snapshots, and explicit
overrides; in explicit Overlay mode, caller-supplied base environment variables
outside the profile pass through as consumer-owned base state with `base`
provenance.

Diagnostics contain names, validator IDs, and stable error classes only. They
never contain values, value fragments, connection strings, host-local paths, or
secret-looking input. Tests seed secret-looking values and search all returned
errors and CLI diagnostics for leakage.

## Validators

The twelve validator families preserve the bounded lexical behavior of the
current `.flakes` authority where APG does not intentionally change the
architecture. Every value first passes the common checks: valid UTF-8,
maximum byte length, no NUL/CR/newline or other ASCII controls, and no
case-insensitive `null` sentinel. Capture treats an empty value as missing
before validator application, matching the current snapshot behavior.

| Validator | Accepted shape |
| --- | --- |
| `bool` | `0`, `1`, `false`, `no`, `true`, or `yes`, case-insensitively. |
| `command` | Common checks only; command text is never executed. The current source also accepts an empty default. |
| `host` | Non-empty `[A-Za-z0-9._:-]+` host-like text. |
| `integer` | Signed decimal digits (`-12`, `0`, `12`); a leading plus is not part of the current lexical form. |
| `path` | Non-empty after trimming for the check; filesystem existence is not tested. |
| `path_list` | Colon-separated entries, each non-empty after trimming. |
| `port` | Decimal digits in the inclusive range 1 through 65535. |
| `raw_safe` | Common checks only. |
| `token` | One or more letters, digits, `.`, `_`, or `-`. |
| `token_list` | Comma-separated, non-empty `token` values. |
| `uri` | A parsed URI with a scheme and a netloc or path. |
| `uri_or_path` | A value accepted by `uri` or `path`. |

The `command` validator is descriptive, not an execution permission. A path
validator likewise does not grant filesystem access. APG parity fixtures cover
accepted and rejected representatives for each family, size/control/sentinel
boundaries, and the current default-validation behavior.

## Capture and canonical snapshot JSON

`Capture` validates the profile, walks its entries in canonical name order, and
selects only present, non-empty values from the explicit map. A missing or
empty required value is an error. A missing or empty optional value is reported
in `missing_optional`. No profile default is inserted. Included values are
validated and copied into a fresh snapshot; the source map is not changed.

Each entry records its name, validator, value, and explicit source
classification. `Capture` uses `capture` for values obtained from the supplied
map. Resolve provenance uses `snapshot`, `override`, and `base`, so a consumer
can distinguish the source layer without reading a diagnostic value.

The canonical snapshot schema is `apg.environment-snapshot/v1`. It contains
the schema version, profile ID and fingerprint, producer/build identity,
explicit capture provenance, capture timestamp, deterministic ordered entries,
missing optional names, and a content fingerprint. A values-bearing snapshot
is owner-protected storage; it is not printed by default.

```json
{
  "schema_version":"apg.environment-snapshot/v1",
  "profile_id":"fixture-profile",
  "profile_fingerprint":"<sha256>",
  "producer_version":"<build>",
  "provenance":{"context":"fixture","shell":"fixture-shell"},
  "captured_at":"2026-08-22T00:00:00Z",
  "entries":[
    {"name":"APG98_MODE","validator":"token","value":"fixture","source":"capture"}
  ],
  "missing_optional":[],
  "content_fingerprint":"<sha256>"
}
```

Stored JSON is strict UTF-8, compact, deterministically keyed, LF-terminated,
and free of insignificant whitespace. Duplicate keys and unknown fields are
rejected. Fingerprints cover profile identity and exact ordered resolved
entries/source classifications. They exclude capture time, storage path,
host/PID/local path, and diagnostic prose. Thus the same logical content has
the same fingerprint even when captured at different times or stored in
different disposable roots.

## Store, load, staleness, and no-churn

The CLI's canonical path is:

```text
<APGR_HOME>/environment/<profile-id>/current.json
```

Library callers provide an exact absolute storage root and receive the
resolved path. The profile ID is a safe path component. The root, profile
directory, and target are owner-controlled; symlinks, hard links, non-regular
files, unsafe owners/modes, and path ambiguity fail closed. Profile directories
are 0700 and snapshot files are 0600. Publication uses a same-directory
private temporary file, flush/fsync, atomic rename, and directory fsync where
the platform supports it. Owned temporary state is removed on cancellation;
foreign paths are never cleaned up.

Each profile directory has an APG-owned interprocess lock directory. A stable,
owner-only `.lock.guard` regular file serializes lock observation and stale
reclamation; it is infrastructure, not an invocation-owned lock or temporary
artifact. The invocation lock
contains an owner identity and an invocation token. A proven-live or
ambiguous/foreign lock is never removed. A malformed lock fails closed. A
verifiably stale lock may be reclaimed only under the documented bounded wait
or conflict policy, and only the owning invocation removes its lock. Successful
and cancelled operations leave no invocation `.lock`, stale-lock, or temporary
debt. This is a
new APG safety capability; the inherited `.flakes` writer has no equivalent
interprocess lock.

Before publication, `Store` compares the validated profile identity and content
fingerprint with the current direct regular snapshot. If they match, it
returns an `unchanged`/`reused` disposition and does not rewrite bytes, inode,
mode, or mtime, and does not advance the stored capture timestamp. A changed
identity publishes atomically. No historical-value archive is created
implicitly.

`Load` checks the same file-safety rules, enforces a bounded file size, parses
strict JSON, validates the supplied/expected profile identity and every entry,
and recomputes the content fingerprint. It reports age. A caller-supplied
maximum age turns an exceeded age into a stable stale error; without a maximum
age, age is visible but does not invalidate the snapshot.

## Resolution

`Isolated` is the default. It starts with an empty result, applies snapshot
entries, then validated explicit overrides. It does not include inherited
process state.

`Overlay` is explicit. It starts with a caller-owned base map, applies snapshot
entries, then validated explicit overrides:

```text
explicit override > snapshot > base
```

Neither mode mutates a supplied map. Snapshot and override names must belong to
the profile and use the same validator and sensitive-name policy. An override
cannot bypass profile validation by omitting the profile. Overlay base values
outside the profile are consumer-owned, are not persisted, and are marked as
`base` provenance; profile-owned base values remain subject to the profile
contract. No default is inserted in either mode.

## CLI and Python bridge

The environment command family is:

```text
apgr env profile-check --profile <profile.json>
apgr env snapshot --profile <profile.json> --storage-root <root> --context <label>
apgr env show --profile <profile.json> --storage-root <root> [--max-age <duration>]
apgr env resolve --profile <profile.json> --storage-root <root> [--mode isolated|overlay]
apgr env run --profile <profile.json> --storage-root <root> [--mode isolated|overlay] -- <argv...>
```

Profile input is a consequence-bearing file: the CLI requires an absolute,
clean, caller-owned direct regular file with one link, restrictive mode, a
bounded size, and stable identity while reading. Snapshot capture constructs
one explicit map from the CLI process environment and passes it to the public
API; it does not move ambient reads into the library.

`env show` is values-free by default and reports metadata, age,
fingerprints, entry names, and missing optional names; an exceeded `--max-age`
causes load to return a stale error. Any values-bearing mode
must be an explicit operator choice and is documented as sensitive output.
`env resolve` likewise defaults to provenance/metadata. In `--mode overlay`,
the CLI supplies the ambient process environment as the base map. `env run` requires an
explicit command argv, resolves the requested mode, and launches it with
exact-argv process semantics and no shell. Resolution failures do not print
resolved values.

The Python console route `apgr env ...` is a bridge only. It resolves the
existing APGR-home precedence (`--apgr-home`, `APGR_HOME`, then `~/.apgr`),
passes an exact storage root to Go, and delegates with exact argv. It has no
Python reimplementation and no semantic fallback when Go is unavailable.

## `.flakes` parity and intentional differences

APG98 uses bounded APG-owned fixtures derived from a fresh read-only binding of
the six `.flakes` environment files. The fixtures cover the current TSV
validation rules, all twelve validators, required/optional/empty handling,
shell detection, env-file versus sync defaults, shell quoting, modes and
metadata, no-churn writes, parser-safe run overlays, exact argv, and Bash/Zsh
hook registration/frequency. The fixture source is evidence, not a mutable
runtime dependency and not an APG product profile.

| Concern | Current `.flakes` behavior | APG98 contract |
| --- | --- | --- |
| Authority | TSV allowlists and shell export snapshots remain operational. | Versioned profile and snapshot JSON is the portable authority after qualification. |
| Capture input | Snapshot adapter defaults to ambient `os.environ`. | Library capture accepts one explicit map; CLI adapters construct that map. |
| Empty values | Required empty fails; optional empty is skipped. | Preserved. Defaults are never inserted. |
| Snapshot bytes | `export NAME=<shell-quoted-value>` text. | Strict canonical JSON; shell rendering is not canonical. |
| Metadata | Path-bearing metadata includes timestamp and content hash. | Provenance is explicit; fingerprint excludes time/path and diagnostics are values-safe. |
| Storage safety | 0700 directory, 0600 file, same-directory replacement, no-churn. | Preserves those modes and atomic/no-churn behavior, adding owner/path checks, fsync, and an interprocess lock. |
| Resolution | `env-run` overlays parsed file values onto inherited process state. | `Isolated` is default; explicit `Overlay` is base → snapshot → override. |
| Sensitive names | Current rows are not a secrets policy. | Fail-closed token-aware policy; `SSH_AUTH_SOCK` remains a documented capability-path exception. |
| Consumers | Shell/Python process boundary. | Go consumers load JSON in process; no JACA process is required. |
| Hook | Immediate and per-prompt refresh, quiet and non-fatal. | Preserved by a future thin adapter only after separate cutover authorization. |

APG does not promise byte equality with the shell snapshot. It promises the
bounded semantic parity above and tests each deliberate difference.

## In-process consumers and boundaries

A disposable external Go module imports the public `envsnap` package through a
local module replacement and performs profile validation, explicit-map capture,
disposable store/load, isolated and overlay resolution, and provenance
inspection without starting `apgr`, Python, a shell, or `.flakes`.

APG98 does not modify JACA, `.flakes`, Nix, active shell hooks, real
`~/.codex` snapshots, real `~/.apgr` state, or the host environment. A future
`.flakes` consumer cutover is specified separately in the thin contract and is
not implied by this document.
