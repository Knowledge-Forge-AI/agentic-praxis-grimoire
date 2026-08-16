// APG74-FX-014: unknown option-state case. The type of the indexed read below
// changes with noUncheckedIndexedAccess, but no configuration establishes that
// option for this excluded directory. The conclusion must therefore stop.

export function firstPresent(values: readonly string[]): string {
  return values[0];
}
