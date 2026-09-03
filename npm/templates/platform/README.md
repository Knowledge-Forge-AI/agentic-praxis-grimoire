# __APG_PLATFORM_NAME__

Native binary distribution of **Agentic Praxis Grimoire** (APGR) for `__APG_TARGET__`.

This platform package is installed automatically as an optional dependency by the `@knowledge-forge-ai/apgr` launcher. It contains:

- `bin/apgr`: the precompiled, standalone Go binary for `__APG_TARGET__`.
- `bin/apgr.binary-manifest.json`: the canonical `apg.binary-manifest/v1` cryptographic integrity manifest.

## Usage

This package is designed to be invoked through the `@knowledge-forge-ai/apgr` launcher package:

```sh
npm install -g @knowledge-forge-ai/apgr@__APG_VERSION__
apgr --version
```

## Platform Target

- Operating System: `__APG_OS__`
- Architecture: `__APG_CPU__`
- Target: `__APG_TARGET__`
- Node.js Engine: `>=22.0.0`

## License

AGPL-3.0-or-later. Commercial licensing options are available at https://www.knowledge-forge.ai.
