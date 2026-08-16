// APG80-FX-007 — statically assigned CommonJS exports. Node's static analysis
// can surface these as named imports for an ESM consumer. Detection is a Node
// loading affordance, not an ECMAScript live binding.

exports.alpha = 'alpha';
exports.beta = 'beta';
