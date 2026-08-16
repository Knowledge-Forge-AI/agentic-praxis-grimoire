// APG74-FX-004: handwritten declaration file. This ambient declaration is
// authored evidence, not generated output; it asserts a runtime surface this
// project never verifies.

declare module "host-metrics" {
  export interface Sample {
    readonly at: number;
    readonly rssBytes: number;
  }
  export function snapshot(): Sample;
}
