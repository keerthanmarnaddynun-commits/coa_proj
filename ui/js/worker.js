/**
 * ui/js/worker.js
 * Dedicated Web Worker for running the 3.78M-reference Trace A simulation.
 * Keeps the main UI thread completely responsive and supports progress updates & cancellation.
 */

import { runSimulation } from './sim_core.js';

let traceData = null;
let markovModel = null;
let oracleModel = null;
let isCancelled = false;

async function loadData() {
  if (traceData && markovModel && oracleModel) return;

  const [traceRes, markovRes, oracleRes] = await Promise.all([
    fetch('../data/trace_a.bin'),
    fetch('../data/markov_top5.json'),
    fetch('../data/graph_oracle.json')
  ]);

  const traceBuffer = await traceRes.arrayBuffer();
  traceData = new Uint16Array(traceBuffer);
  markovModel = await markovRes.json();
  oracleModel = await oracleRes.json();
}

self.onmessage = async (e) => {
  const { type, payload } = e.data;

  if (type === 'CANCEL') {
    isCancelled = true;
    return;
  }

  if (type === 'RUN') {
    isCancelled = false;

    try {
      await loadData();
    } catch (err) {
      self.postMessage({ type: 'ERROR', error: 'Failed to load trace data: ' + err.message });
      return;
    }

    const params = {
      trace: traceData,
      capacity: payload.capacity,
      k: payload.k,
      threshold: payload.threshold,
      insertion: payload.insertion,
      model: payload.model,
      markovModel: markovModel,
      oracleModel: oracleModel,
      adaptive: payload.adaptive,
      baselineFaults: payload.baselineFaults || 67696,
      onProgress: (percent) => {
        self.postMessage({ type: 'PROGRESS', percent });
      },
      isCancelled: () => isCancelled
    };

    const startTime = performance.now();
    const result = runSimulation(params);
    const elapsedMs = performance.now() - startTime;

    if (result.cancelled) {
      self.postMessage({ type: 'CANCELLED' });
    } else {
      result.elapsedMs = elapsedMs;
      self.postMessage({ type: 'DONE', result });
    }
  }
};

