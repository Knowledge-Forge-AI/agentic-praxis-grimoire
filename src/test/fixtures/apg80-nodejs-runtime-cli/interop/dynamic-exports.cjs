// APG80-FX-007 — contrasting control. These export names are assigned through a
// computed key, so static analysis cannot surface them as named imports. The
// values still exist on the default export at run time.

const names = ['gamma', 'delta'];

for (const name of names) {
  exports[name] = name;
}
