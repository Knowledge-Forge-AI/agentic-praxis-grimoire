// APG78-FX-014 — Node adapter boundary, described rather than performed.
// APG78 performs none of these operations. Each routes to node-runtime-owner.
// APG-owned.

'use strict';

const ADAPTER_CONCERNS = Object.freeze([
  'argument acquisition from process.argv',
  'environment value acquisition from process.env',
  'standard output and standard error writes',
  'filesystem access',
  'network access',
  'signal handling',
  'process exit status',
]);

function routes() {
  return ADAPTER_CONCERNS.map((concern) => ({
    concern,
    owner: 'node-runtime-owner',
    performedByApg78: false,
  }));
}

function coreInputShape() {
  return {
    argumentValues: 'ReadonlyArray<string>',
    environmentValues: 'Readonly<Record<string, string>>',
    output: '{ write(line: string): void }',
  };
}

module.exports = { ADAPTER_CONCERNS, routes, coreInputShape };
