// APG80-FX-002 — typeless scope whose mapping depends on version-specific
// syntax detection. The nearest manifest declares no `type`; this source uses
// module-only syntax. Whether Node reparses it as ESM, and whether it emits a
// typeless-package diagnostic, is a property of the exact Node version and
// flags, not of the extension.

export const detectionEvidence = 'module-only-syntax-under-typeless-scope';
