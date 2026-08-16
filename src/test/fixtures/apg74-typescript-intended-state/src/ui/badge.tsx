// APG74-FX-006: .tsx ownership boundary. TypeScript types the expressions
// and attributes below against the local JSX host declarations; JSX syntax
// and any transform remain outside this profile's ownership (jsx=preserve).

export function renderBadge(label: string, warn: boolean): JSX.Element {
  return <status-badge label={label} tone={warn ? "warn" : "ok"} />;
}
