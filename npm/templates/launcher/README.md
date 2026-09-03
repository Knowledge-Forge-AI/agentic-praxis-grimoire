# @knowledge-forge-ai/apgr

The official npm launcher for **Agentic Praxis Grimoire** (APGR).

APGR is a provider-neutral toolkit and skill corpus for bounded agent engineering, providing deterministic context bundles, evidence collection, environment snapshots, hotspot analysis, and context-footprint accounting.

## Architecture

This package is a lightweight, zero-dependency Node.js launcher. It contains no runtime semantics itself. When invoked, it:

1. Inspects `process.platform` and `process.arch` to identify the target host.
2. Locates the matching platform package (`@knowledge-forge-ai/apgr-darwin-arm64`, `@knowledge-forge-ai/apgr-linux-x64`, or `@knowledge-forge-ai/apgr-linux-arm64`).
3. Verifies the prebuilt Go binary and its companion `apg.binary-manifest/v1` integrity manifest.
4. Executes the verified binary with exact arguments, inherited stdio, and `shell: false`.

All operational behavior, skill resolution, and reporting logic reside exclusively in the verified Go binary.

## Installation

Install globally via npm:

```sh
npm install -g @knowledge-forge-ai/apgr@__APG_VERSION__
apgr --version
```

Or execute directly via `npx`:

```sh
npx @knowledge-forge-ai/apgr@__APG_VERSION__ --version
```

## Supported Platforms

- `darwin/arm64` (macOS Apple Silicon) -> `@knowledge-forge-ai/apgr-darwin-arm64`
- `linux/x64` (Linux x86_64 / amd64) -> `@knowledge-forge-ai/apgr-linux-x64`
- `linux/arm64` (Linux aarch64) -> `@knowledge-forge-ai/apgr-linux-arm64`

Requirements: Node.js `>=22.0.0`.

## License

AGPL-3.0-or-later. Commercial licensing options are available at https://www.knowledge-forge.ai.
