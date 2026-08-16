// APG74-FX-002: .mts source kind (always an ECMAScript module under
// module=nodenext). The indexed access below is ManifestEntry | undefined
// because noUncheckedIndexedAccess=true.

export interface ManifestEntry {
  readonly id: string;
  readonly weight: number;
}

export function heaviestEntry(
  entries: readonly ManifestEntry[],
): ManifestEntry | undefined {
  const ordered = [...entries].sort((a, b) => b.weight - a.weight);
  return ordered[0];
}
