/**
 * ui/tests/verify_sim.mjs
 * Verification test suite for sim_core.js.
 * Loads ui/data/trace_a.bin, ui/data/markov_top5.json, and ui/data/graph_oracle.json,
 * executes every test configuration, and prints an explicit PASS/FAIL table.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { runSimulation } from '../js/sim_core.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const dataDir = path.join(__dirname, '..', 'data');

console.log('Loading simulation binary trace and model datasets...');
const traceBuffer = fs.readFileSync(path.join(dataDir, 'trace_a.bin'));
const trace = new Uint16Array(traceBuffer.buffer, traceBuffer.byteOffset, traceBuffer.byteLength / 2);
console.log(`Loaded trace with ${trace.length.toLocaleString()} references.`);

const markovModel = JSON.parse(fs.readFileSync(path.join(dataDir, 'markov_top5.json'), 'utf8'));
const oracleModel = JSON.parse(fs.readFileSync(path.join(dataDir, 'graph_oracle.json'), 'utf8'));
console.log(`Loaded models: Markov (${markovModel.length} states), Oracle (${oracleModel.length} states).\n`);

const tests = [
  // Trace A, 1,024 frames, Markov degree tests
  {
    category: 'Prefetch Degree (1024 frames)',
    name: 'Baseline LRU (k=0)',
    params: { trace, capacity: 1024, k: 0, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 67696 }
  },
  {
    category: 'Prefetch Degree (1024 frames)',
    name: 'Top-1 Markov (k=1)',
    params: { trace, capacity: 1024, k: 1, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 67634 }
  },
  {
    category: 'Prefetch Degree (1024 frames)',
    name: 'Top-2 Markov (k=2)',
    params: { trace, capacity: 1024, k: 2, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 63132 }
  },
  {
    category: 'Prefetch Degree (1024 frames)',
    name: 'Top-3 Markov (k=3)',
    params: { trace, capacity: 1024, k: 3, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 57512 }
  },
  {
    category: 'Prefetch Degree (1024 frames)',
    name: 'Top-5 Markov (k=5)',
    params: { trace, capacity: 1024, k: 5, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 63041 }
  },

  // Confidence Threshold Tests (1024 frames, k=3)
  {
    category: 'Confidence Threshold (k=3)',
    name: 'Threshold T=0.05',
    params: { trace, capacity: 1024, k: 3, threshold: 0.05, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 55816, prefetches: 50258 }
  },
  {
    category: 'Confidence Threshold (k=3)',
    name: 'Threshold T=0.10',
    params: { trace, capacity: 1024, k: 3, threshold: 0.10, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 55751, prefetches: 49339 }
  },
  {
    category: 'Confidence Threshold (k=3)',
    name: 'Threshold T=0.20',
    params: { trace, capacity: 1024, k: 3, threshold: 0.20, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 59431, prefetches: 32463 }
  },
  {
    category: 'Confidence Threshold (k=3)',
    name: 'Threshold T=0.30',
    params: { trace, capacity: 1024, k: 3, threshold: 0.30, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 67667, prefetches: 38 }
  },
  {
    category: 'Confidence Threshold (k=3)',
    name: 'Threshold T=0.50',
    params: { trace, capacity: 1024, k: 3, threshold: 0.50, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 67683, prefetches: 14 }
  },

  // Capacity Tests (k=3)
  {
    category: 'RAM Capacity (512 frames)',
    name: '512 frames Baseline (k=0)',
    params: { trace, capacity: 512, k: 0, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 221603 },
    expected: { faults: 221603 }
  },
  {
    category: 'RAM Capacity (512 frames)',
    name: '512 frames Top-3 Prefetch (k=3)',
    params: { trace, capacity: 512, k: 3, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 221603 },
    expected: { faults: 237684 }
  },
  {
    category: 'RAM Capacity (2048 frames)',
    name: '2,048 frames Baseline (k=0)',
    params: { trace, capacity: 2048, k: 0, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 2025 },
    expected: { faults: 2025 }
  },
  {
    category: 'RAM Capacity (2048 frames)',
    name: '2,048 frames Top-3 Prefetch (k=3)',
    params: { trace, capacity: 2048, k: 3, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: false, baselineFaults: 2025 },
    expected: { faults: 935 }
  },

  // LRU-End Insertion Tests (k=3)
  {
    category: 'LRU-End Insertion (k=3)',
    name: '512 frames LRU-End Insertion',
    params: { trace, capacity: 512, k: 3, threshold: 0.0, insertion: 'lru', model: 'markov', markovModel, adaptive: false, baselineFaults: 221603 },
    expected: { faults: 191587 }
  },
  {
    category: 'LRU-End Insertion (k=3)',
    name: '1,024 frames LRU-End Insertion',
    params: { trace, capacity: 1024, k: 3, threshold: 0.0, insertion: 'lru', model: 'markov', markovModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 60622 }
  },

  // Adaptive Top-K Controller Tests
  {
    category: 'Adaptive Controller',
    name: '512 frames Adaptive Top-K',
    params: { trace, capacity: 512, k: 3, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: true, baselineFaults: 221603 },
    expected: { faults: 212106, adjustments: 159, finalK: 2 }
  },
  {
    category: 'Adaptive Controller',
    name: '1,024 frames Adaptive Top-K',
    params: { trace, capacity: 1024, k: 3, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: true, baselineFaults: 67696 },
    expected: { faults: 57609, adjustments: 6, finalK: 5 }
  },
  {
    category: 'Adaptive Controller',
    name: '2,048 frames Adaptive Top-K',
    params: { trace, capacity: 2048, k: 3, threshold: 0.0, insertion: 'mru', model: 'markov', markovModel, adaptive: true, baselineFaults: 2025 },
    expected: { faults: 935, adjustments: 0, finalK: 3 }
  },

  // Graph Oracle Test (1024 frames, k=3)
  {
    category: 'Graph Oracle (1024 frames)',
    name: 'Graph Oracle Top-3 (k=3)',
    params: { trace, capacity: 1024, k: 3, threshold: 0.0, insertion: 'mru', model: 'oracle', oracleModel, adaptive: false, baselineFaults: 67696 },
    expected: { faults: 57230 }
  }
];

let allPassed = true;
const resultsTable = [];

console.log('Running test matrix...');
const startTime = Date.now();

for (const t of tests) {
  const t0 = Date.now();
  const res = runSimulation(t.params);
  const elapsedSec = ((Date.now() - t0) / 1000).toFixed(2);

  let passed = true;
  let details = `Faults: ${res.pageFaults.toLocaleString()}`;

  if (res.pageFaults !== t.expected.faults) {
    passed = false;
  }

  if (t.expected.prefetches !== undefined) {
    details += `, Prefetches: ${res.totalPrefetches.toLocaleString()}`;
    if (res.totalPrefetches !== t.expected.prefetches) {
      passed = false;
    }
  }

  if (t.expected.adjustments !== undefined) {
    details += `, Adjs: ${res.adjustments}`;
    if (res.adjustments !== t.expected.adjustments) {
      passed = false;
    }
  }

  if (t.expected.finalK !== undefined) {
    details += `, Final K: ${res.finalK}`;
    if (res.finalK !== t.expected.finalK) {
      passed = false;
    }
  }

  if (!passed) {
    allPassed = false;
  }

  resultsTable.push({
    category: t.category,
    name: t.name,
    expectedFaults: t.expected.faults.toLocaleString(),
    actualFaults: res.pageFaults.toLocaleString(),
    details,
    time: `${elapsedSec}s`,
    status: passed ? 'PASS' : 'FAIL'
  });
}

const totalTimeSec = ((Date.now() - startTime) / 1000).toFixed(2);

console.log('\n========================================================================================================');
console.log('                                  PHASE 1 SIMULATION VERIFICATION MATRIX                                ');
console.log('========================================================================================================');
console.log(
  'Configuration'.padEnd(35) + ' | ' +
  'Expected'.padStart(10) + ' | ' +
  'Actual'.padStart(10) + ' | ' +
  'Status'.padEnd(8) + ' | ' +
  'Time'.padStart(6) + ' | ' +
  'Details'
);
console.log('-'.repeat(104));

for (const r of resultsTable) {
  console.log(
    r.name.padEnd(35) + ' | ' +
    r.expectedFaults.padStart(10) + ' | ' +
    r.actualFaults.padStart(10) + ' | ' +
    (r.status === 'PASS' ? ' PASS   ' : ' FAIL * ') + ' | ' +
    r.time.padStart(6) + ' | ' +
    r.details
  );
}

console.log('='.repeat(104));
console.log(`Verification completed in ${totalTimeSec}s. Total tests: ${resultsTable.length}.`);

if (allPassed) {
  console.log('RESULT: ALL TESTS PASSED! Simulation core logic matches Python ground truth 100%.\n');
  process.exit(0);
} else {
  console.error('RESULT: SOME TESTS FAILED! Fix sim_core.js logic to match Python reference scripts.\n');
  process.exit(1);
}

