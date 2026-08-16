// APG80-FX-006 — deliberately absent from the `exports` map. A package-relative
// specifier for this path is refused by Node's resolver. Encapsulation is a
// Node resolution result, not a filesystem permission and not a security control.

export const reachedVia = 'should-not-be-reachable-by-package-specifier';
