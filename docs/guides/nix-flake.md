# Nix flake guide

This guide covers the first-party APGR Nix flake published from v0.13.0 onward
([ADR 0076](../adr/2026/09/0076-first-party-nix-flake-publication-target.md)).
Install commands and platform status are in
[distribution](../distribution.md#first-party-nix-flake-v0130-onward).
Normal installs pin a release tag, never `main`.

## Outputs and layout

`packages.<system>.default`, `.agentic-praxis-grimoire` and `.apgr` are one
derivation. `apps` expose `apgr`, `agent-phase-dispatch` and
`apgr-dispatcher-bundle`. `checks` run against the exact built store output.
The package contains:

- `bin/`: wrappers for `apgr`, `agent-phase-dispatch`, `agent-phase-resolve`,
  `agent-phase-finalize`, `agent-phase-observations`, `agent-phase-ownership`,
  `agent-phase-adopt`, `agent-phase-adopt-entry` and `apgr-dispatcher-bundle`.
  Wrappers put the runtime and nixpkgs Python 3.13 and Bash first on `PATH`,
  append nixpkgs Git after the caller's `PATH`, and unset `PYTHONPATH` and
  `PYTHONHOME`. Git is a fallback rather than a pinned dependency because the
  dispatcher operates on the operator's repositories; an operator-selected Git
  wrapper, its configuration and its credential mediation must keep winning.
- `share/agentic-praxis-grimoire/runtime/`: the dispatcher runtime tree. It
  contains the controller-generation allowlist closure, the whole Python
  package, and licensing files. The bundled Go binary and its canonical
  manifest sit at `src/agentic_praxis_grimoire/bin/`.
- `apgr-installed-runtime.json`: a build-owned marker with the runtime root,
  version and content digest.

The Go binary comes from `bin/apg-build-go-cli` with nixpkgs `go_1_25`. It
carries the same version, corpus fingerprint and build flags as the other
surfaces. Byte identity with GitHub release assets is not claimed. The version
comes only from `src/agentic_praxis_grimoire/VERSION`.

## Installed dispatcher

The installed dispatcher runs in place from the read-only store. Its run state
records `installed_immutable_runtime` provenance with the runtime version and
digest, and a null commit and tree. It takes no generation lease and cannot
resume a generation-pinned run.

Installed mode is recognized only for a canonical runtime root inside a
write-protected `/nix/store/<hash>-<name>` object whose marker names that root
and records `distribution: nix`. Before each installed `dispatch`, `finalize`
or `ownership` run, the bootstrap recomputes the runtime digest and requires it
to match the marker; this cost about 20–60 ms on aarch64-darwin. A copied,
writable, aliased or relocated tree that still carries a marker is refused
rather than run as a checkout. These checks catch accidental or partial
modification. They are not tamper-proof against an account that can write the
store, and a custom store directory is not supported. Before real dispatch, project the bundle and
keep operator settings external:

```sh
apgr-dispatcher-bundle project --apgr-home "$APGR_HOME"
# operator-owned, never shipped: $APGR_HOME/claude/settings.json
```

Provider CLIs (`claude`, `codex`, `agy`, `rtk`) come from the operator's
`PATH`. `apgr dispatcher …` front-door routes still require an APG Git
repository, exactly as they do for the wheel. The direct commands above are
the supported installed surface. An explicit `APGR_GO_BINARY` still overrides
the bundled binary.

## Source boundary and trade-offs

`nix/source.nix` admits only the paths listed in `nix/distribution.json`.
Tests, fixtures, `testdata`, `private/`, `docs/`, `.pyc` files and every
`settings.json` stay out. The build never synthesizes operator settings.
Evaluating the flake from a development checkout still copies that checkout's
tracked files, including `private/`, into the local store. Qualify from a
scratch source prepared with `bin/apg-qualify-nix prepare-source`, or from the
public tag.

## Tagged readback

A release is fully published only after the tagged readback passes on a native
host with a disposable profile:

```sh
bin/apg-qualify-nix readback --tag v0.13.0 --scratch "$FRESH_SCRATCH" \
  --system aarch64-darwin --expect-rev "$MERGED_RELEASE_COMMIT"
```

The helper resolves the tag once with `nix flake metadata --json --refresh`,
requires the locked revision to equal `--expect-rev`, and records the
`narHash`. Every later check, build, run, profile and smoke step uses the
revision-pinned reference, never the tag name. The profile lives under the
fresh scratch directory and is removed afterwards; default profiles are
refused. This command works only after the `v0.13.0` tag is published.

## Build closure

The runtime ships the whole `bin/` and `libexec/` trees, because the
controller-generation allowlist is the proven dispatcher closure. That
includes release and test helpers the installed dispatcher never calls. The
closure follows nixpkgs `python3`: on aarch64-darwin it measured 1.6 GiB,
mostly the compiler toolchain that nixpkgs Python references.
