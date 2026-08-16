// APG74-FX-012: emitted-JavaScript/runtime boundary.
// This file checks clean, and that clean check proves nothing about the
// runtime shape of the parsed value: the assertion below is erased at emit.

export interface DeployReport {
  readonly target: string;
  readonly durationMs: number;
}

export function parseReport(raw: string): DeployReport {
  return JSON.parse(raw) as DeployReport;
}
