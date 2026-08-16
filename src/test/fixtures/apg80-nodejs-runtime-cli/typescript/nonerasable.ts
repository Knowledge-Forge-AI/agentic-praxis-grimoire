// APG80-FX-001 corrected by APG81 — contrasting non-erasable syntax.
enum RuntimeKind { Node = 'node' }
console.log(JSON.stringify({ kind: RuntimeKind.Node }));
