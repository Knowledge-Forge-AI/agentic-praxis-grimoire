// APG78-FX-008 — promise reactions and async propagation.
// Bounded to Jobs and HostEnqueuePromiseJob requirements. No host timer, I/O,
// browser task, microtask-checkpoint, or rejection-reporting claim.
// APG-owned.

/** Orders reactions that are all language jobs. */
export function reactionOrder(trace) {
  const settled = Promise.resolve('settled');
  settled.then(() => trace.push('then-1'));
  settled.then(() => trace.push('then-2'));
  trace.push('synchronous');
  return settled;
}

/** Suspension and resumption around `await`. */
export async function awaitBoundary(trace) {
  trace.push('before-await');
  const value = await Promise.resolve('resumed');
  trace.push('after-await');
  return value;
}

/** Rejection propagating out of an async function, and catching it. */
export async function rejectingCore() {
  await Promise.resolve();
  throw new Error('async-origin');
}

export async function catchPropagation() {
  try {
    await rejectingCore();
    return { caught: null };
  } catch (error) {
    return { caught: error.message };
  }
}
