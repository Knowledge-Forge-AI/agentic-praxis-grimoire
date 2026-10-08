# ADR 0076: First-party Nix flake publication target

Status: Accepted with amendment — APG166ZD / V0130-I release preparation. It
records the manager's APG166ZC publication decision and the
APG166ZC-NIX-DISTRIBUTION1 package-surface choice. The amendment below binds
installed-mode recognition to the Nix store and the tag readback to an exact
revision. The acceptance is part of the uncommitted V0130-I checkpoint and takes
effect only when the manager finalizes that checkpoint.

## Context

From v0.13.0 the manager adds first-party Nix as an APGR publication surface.
"First-party" means APGR is installable through Nix flakes directly from its own
public Git repository and release tag. It does not mean inclusion in upstream
`NixOS/nixpkgs`, Hydra, a binary cache or host activation. Earlier releases
published GitHub Release, Go, PyPI, npm and Homebrew surfaces only; their
records stay unchanged.

The v0.13 release purpose includes an independently usable dispatcher. Before
this decision the dispatcher could start only from a Git checkout or a
controller generation materialized from Git objects. The bootstrap probed the
controller root with `git status`, and the dispatcher bundle reader required
files owned by the effective account with exactly one hard link. A read-only,
root-owned, store-optimised Nix tree met none of those conditions.

## Decision

1. The repository root carries a public `flake.nix`, a committed `flake.lock`
   with one locked `nixpkgs` input, and source-owned recipes under `nix/`.
   `nix/distribution.json` is the single data authority for the supported
   systems (`aarch64-darwin`, `x86_64-linux`, `aarch64-linux`), the runtime and
   Go source roots, the exported commands and the publication critical files.
2. The package surface is the full installed runtime, not a Go-only binary.
   `packages.<system>.{default,agentic-praxis-grimoire,apgr}` alias one
   derivation containing the portable Go `apgr`, the Python front door and the
   existing dispatcher runtime tree. No second dispatcher implementation
   exists. The Go binary is built by `bin/apg-build-go-cli`, so the version,
   corpus fingerprint, build flags and manifest are those of the other surfaces.
   The version comes only from `src/agentic_praxis_grimoire/VERSION`.
3. A build-owned marker, `apgr-installed-runtime.json`, names the runtime root
   and records its content digest. When a read-only, non-Git tree carries a
   valid marker naming itself, the bootstrap runs the dispatcher in place.
   (Amended by APG166ZD: the tree must also lie in a write-protected Nix store
   object, and the digest is verified at entry; see the amendment below.) It
   records `installed_immutable_runtime` provenance with null commit and tree,
   takes no lease, materializes no generation, and refuses to resume a
   generation-pinned run.
4. The dispatcher bundle reader accepts root-owned, write-protected members and
   store hard links only for the marker-verified runtime's own
   `common/dispatcher` source defaults. Home, override and development bundles
   keep the owner and single-link checks.
5. Flake `checks` exercise the exact built store output: an installed-output
   verifier, a provider-free smoke (including a dry-run dispatch outside any
   checkout) and a negative control that must fail. A disposable-profile helper
   (`bin/apg-qualify-nix`) never targets a default profile.
6. From v0.13.0 onward, a release is not fully published until tag-pinned Nix
   readback of `github:Knowledge-Forge-AI/agentic-praxis-grimoire/v<version>`
   succeeds. Operator settings (`claude/settings.json`) remain external and
   never enter the source filter or the package.

## Consequences

- Nix users get the dispatcher and `apgr` without a checkout. The front-door
  `apgr dispatcher …` routes still require an APG Git repository, as they do
  for the wheel. The direct `agent-phase-*` and `apgr-dispatcher-bundle`
  commands are the supported installed surface.
- The runtime ships the complete `bin/` and `libexec/` trees, because the
  controller-generation allowlist is the proven dispatcher closure. That
  includes release and test helpers the installed dispatcher does not call.
- The closure depends on nixpkgs' `python3`. On Darwin that closure is large
  (about 1.6 GiB measured for aarch64-darwin) because nixpkgs Python
  references its compiler wrapper.
- Installed runs have no Git identity. Their provenance is the runtime version
  and digest, not a commit.
- The source filter bounds the derivation, not flake evaluation. Evaluating
  the flake from a development checkout, including by an editor or direnv
  integration, copies that checkout's tracked files, including `private/`,
  into the world-readable local store. Qualification uses a scratch source
  from `bin/apg-qualify-nix prepare-source` or the public tag.
- Darwin qualification in this slice ran with `sandbox = false`, so it does
  not prove the build and checks avoid host tools. Linux builds have not run.
- Historical releases gain no Nix artifact. Release tooling must add the Nix
  surface when v0.13.0 support is added to the release policy.

## What would make this wrong

- A dispatcher path writes into, or requires Git identity from, the controller
  root. Installed mode would then fail at run time, not at bootstrap.
- The marker could be forged into a tree that is not immutable in practice. The
  store-object, mode-bit, self-naming and entry digest checks bound this, but
  they are not a security boundary against an account that can write the store.
  Installed mode claims no safety lease.
- A supported installation uses a store directory other than `/nix/store`.
  Installed mode would then refuse to start rather than run.
- Nixpkgs `go_1_25` or `python313` drifts from the CI toolchains after a lock
  update, and the identity checks were not rerun.
- `aarch64-linux` is declared but has only evaluation evidence until a native
  cell executes the checks.

## Amendment — APG166ZD / V0130-I release preparation

1. **Installed-mode recognition is bound to the Nix store.** In addition to the
   original checks, `controller_generation.installed_runtime` now requires:
   `distribution == "nix"`; a canonical root (its real path equals itself); a
   root inside `/nix/store/<32 nix-base32 characters>-<name>/`; and a
   write-protected store-object directory. The store directory is a module
   constant with no environment override. A tree that carries the marker but
   fails recognition is refused. It is never treated as a source checkout.
   Custom store directories are not supported.
2. **The recorded digest is verified once per installed entry.** Before an
   installed `dispatch`, `finalize` or `ownership` run records
   `installed_immutable_runtime` provenance, the bootstrap recomputes
   `runtime_digest` and requires it to equal the marker. Measured on the
   aarch64-darwin 0.12.0 store output (284 files, 11.8 MB), this took about
   20 ms warm and 57 ms cold per entry. That is small next to a dispatch, and it
   makes the recorded provenance digest an observed fact. Bundle-reader checks
   do not re-hash.
3. **Guarantee, stated plainly.** These checks reject copied, writable,
   aliased or misplaced trees, and accidental or partial modification of an
   installed runtime. They are not tamper-proof: an account that can write the
   store can rewrite the runtime and its marker together.
4. **Tag readback resolves once and pins the revision.**
   `bin/apg-qualify-nix readback` now requires `--expect-rev`. It resolves the
   tag once with `nix flake metadata --json --refresh` and requires the locked
   revision to equal the merged release commit. It records the `narHash`, runs
   every later step against
   `github:Knowledge-Forge-AI/agentic-praxis-grimoire/<rev>`, and requires the
   tagged `apgr --version`, the store and profile smoke provenance, and
   disposable-profile removal to match.
5. **Release ordering.** The attended operator treats Nix as a readback-only
   channel after GitHub, Go, PyPI, npm and Homebrew. A missing or failed
   readback leaves the release not fully published. Completed channels are
   neither replayed nor rolled back. Hosted `nix (x86_64-linux)` and
   `nix (aarch64-darwin)` checks gate the public PR; `aarch64-linux` remains
   evaluation-only.
