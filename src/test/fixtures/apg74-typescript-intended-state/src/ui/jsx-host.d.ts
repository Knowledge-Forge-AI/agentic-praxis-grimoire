// APG74-FX-006 support: minimal local JSX host declarations so the .tsx
// boundary can be typed under jsx=preserve without installing React or any
// other JSX runtime.

declare namespace JSX {
  interface Element {
    readonly kind: "fixture-element";
  }
  interface IntrinsicElements {
    "status-badge": {
      label: string;
      tone?: "ok" | "warn";
    };
  }
}
