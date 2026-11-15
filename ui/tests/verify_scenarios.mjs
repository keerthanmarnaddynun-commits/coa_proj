/**
 * ui/tests/verify_scenarios.mjs
 * Verification script for the Walkthrough scenarios in Tab 2.
 */

import { FastLRUCache } from '../js/sim_core.js';
import { SCENARIOS } from '../js/scenarios.js';

const pMap = { A: 0, B: 1, C: 2, D: 3, E: 4, F: 5, G: 6, H: 7 };
const idToName = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

function runScenarioSim(sequence, markovTable, k, insertion, threshold) {
  const cache = new FastLRUCache(4, 16);
  let faults = 0;
  const numSeq = sequence.map(name => pMap[name]);

  for (const page of numSeq) {
    const isHit = cache.access(page);
    if (!isHit) {
      faults++;
      const pageName = idToName[page];
      const entry = markovTable[pageName];
      if (k > 0 && entry && entry.length > 0) {
        const qualified = [];
        for (let i = 0; i < Math.min(k, entry.length); i++) {
          if (entry[i].prob >= threshold) {
            qualified.push(pMap[entry[i].next]);
          }
        }
        if (qualified.length > 0) {
          if (insertion === 'lru') {
            cache.prefetchLRUEnd(qualified);
          } else {
            cache.prefetchMRU(qualified);
          }
        }
      }
    }
  }
  return faults;
}

console.log('================================================================================');
console.log('                      VERIFYING TAB 2 WALKTHROUGH SCENARIOS                     ');
console.log('================================================================================\n');

let allPassed = true;

// 1. Scenario 1: Prefetch Helps
console.log('1. Checking Scenario 1: "Prefetching Helps"...');
const s1 = SCENARIOS.helps;
const s1_base = runScenarioSim(s1.sequence, s1.markovTable, 0, 'mru', 0);
const s1_k1 = runScenarioSim(s1.sequence, s1.markovTable, 1, 'mru', 0);
const s1_k2 = runScenarioSim(s1.sequence, s1.markovTable, 2, 'mru', 0);

console.log(`   Baseline Demand Faults:   Expected: ${s1.expected.baselineFaults}, Actual: ${s1_base}`);
console.log(`   Prefetch (k=1) Faults:    Expected: ${s1.expected.prefetchK1Faults}, Actual: ${s1_k1}`);
console.log(`   Prefetch (k=2) Faults:    Expected: ${s1.expected.prefetchK2Faults}, Actual: ${s1_k2}`);

if (s1_base === s1.expected.baselineFaults && s1_k1 === s1.expected.prefetchK1Faults && s1_k2 === s1.expected.prefetchK2Faults) {
  console.log('   -> SCENARIO 1: PASS\n');
} else {
  console.error('   -> SCENARIO 1: FAIL\n');
  allPassed = false;
}

// 2. Scenario 2: Pollution & Fixes
console.log('2. Checking Scenario 2: "Pollution & Fixes"...');
const s2 = SCENARIOS.pollution;
const s2_base = runScenarioSim(s2.sequence, s2.markovTable, 0, 'mru', 0);
const s2_mru = runScenarioSim(s2.sequence, s2.markovTable, 2, 'mru', 0.0);
const s2_lru = runScenarioSim(s2.sequence, s2.markovTable, 2, 'lru', 0.0);
const s2_thresh = runScenarioSim(s2.sequence, s2.markovTable, 2, 'mru', 0.40);

console.log(`   Baseline Demand Faults:         Expected: ${s2.expected.baselineFaults}, Actual: ${s2_base}`);
console.log(`   MRU Prefetch (Pollution):       Expected: ${s2.expected.mruFaults}, Actual: ${s2_mru}`);
console.log(`   LRU-End Prefetch (Fix 1):       Expected: ${s2.expected.lruEndFaults}, Actual: ${s2_lru}`);
console.log(`   Confidence T=0.40 (Fix 2):      Expected: ${s2.expected.thresholdFaults}, Actual: ${s2_thresh}`);

if (s2_base === s2.expected.baselineFaults && s2_mru === s2.expected.mruFaults && s2_lru === s2.expected.lruEndFaults && s2_thresh === s2.expected.thresholdFaults) {
  console.log('   -> SCENARIO 2: PASS\n');
} else {
  console.error('   -> SCENARIO 2: FAIL\n');
  allPassed = false;
}

if (allPassed) {
  console.log('================================================================================');
  console.log('ALL WALKTHROUGH SCENARIO TESTS PASSED!');
  console.log('================================================================================');
  process.exit(0);
} else {
  console.error('WALKTHROUGH SCENARIO VERIFICATION FAILED!');
  process.exit(1);
}

