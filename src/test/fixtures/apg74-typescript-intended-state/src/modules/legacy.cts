// APG74-FX-003: .cts source kind (always CommonJS under module=nodenext).
// verbatimModuleSyntax=true requires value-bearing exports here to be
// CommonJS-shaped (type-only import/export syntax would stay legal), so
// this file uses `export =` rather than an ECMAScript export declaration.

const LEGACY_PREFIX = "kfa";

function formatLegacyId(serial: number): string {
  return `${LEGACY_PREFIX}-${serial.toString(16)}`;
}

export = { formatLegacyId };
