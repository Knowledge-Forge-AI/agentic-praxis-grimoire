# __APG_PLATFORM_NAME__

Native binary distribution of **Agentic Praxis Grimoire** (APGR) for `__APG_TARGET__`.

This platform package is installed automatically as an optional dependency by the `@knowledge-forge-ai/apgr` launcher. It contains:

- `bin/apgr`: the precompiled, standalone Go binary for `__APG_TARGET__`.
- `bin/apgr.binary-manifest.json`: the canonical `apg.binary-manifest/v1` cryptographic integrity manifest.

## Usage

Once this version is published, invoke this package through the `@knowledge-forge-ai/apgr` launcher package:

```sh
npm install -g @knowledge-forge-ai/apgr@__APG_VERSION__
apgr --version
```

Prior to publication, unpublished candidate versions are not available on npm; use an APGR Git checkout
to test candidate features.

The prebuilt binary executes runtime commands (`skills`, `footprint`, `env`, `analyze hotspots`, `report`, `response`). It does not include repository test runners or check helpers (`apgr test`), which require an APGR Git checkout and developer toolchain.

## Platform Target

- Operating System: `__APG_OS__`
- Architecture: `__APG_CPU__`
- Target: `__APG_TARGET__`
- Node.js Engine: `>=22.0.0`
- Developer Gate: Darwin arm64 passed the [integrated source qualification](https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/blob/v__APG_VERSION__/docs/status/2026/09/06/00159-apg114-v090-integrated-source-qualification-exit.md); Linux x86_64 qualification remains pending.

## License

AGPL-3.0-or-later. Commercial licensing options are available at https://www.knowledge-forge.ai.
