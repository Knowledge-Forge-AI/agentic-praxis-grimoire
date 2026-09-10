self.onmessage = function(event) {
  const data = event.data || {};
  if (data.type === 'ping') {
    self.postMessage({ type: 'pong', echo: data.payload, timestamp: Date.now() });
  } else if (data.type === 'compute') {
    self.postMessage({ type: 'result', value: data.a * data.b });
  }
};
