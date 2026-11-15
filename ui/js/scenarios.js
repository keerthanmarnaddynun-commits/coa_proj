/**
 * ui/js/scenarios.js
 * Built-in pedagogical scenarios for Tab 2 "Concept Walkthrough".
 * Verified with Node test suite (ui/tests/verify_scenarios.mjs).
 */

export const SCENARIOS = {
  helps: {
    id: 'helps',
    title: 'Prefetching Helps (Accurate Predictions)',
    description: 'Graph BFS traverses frontier in order (A -> B -> C -> D -> E -> F). The Markov table captures these transitions accurately. Speculative prefetching converts compulsory and capacity misses into hits.',
    sequence: ['A','B','C','D','E','F','A','B','C','D','E','F','A','B','C','D','E','F','A','B'],
    defaultK: 2,
    defaultInsertion: 'mru',
    defaultThreshold: 0.0,
    expected: {
      baselineFaults: 20,
      prefetchK1Faults: 10,
      prefetchK2Faults: 7
    },
    markovTable: {
      'A': [{ next: 'B', prob: 0.80 }, { next: 'C', prob: 0.60 }],
      'B': [{ next: 'C', prob: 0.90 }, { next: 'D', prob: 0.70 }],
      'C': [{ next: 'D', prob: 0.85 }],
      'D': [{ next: 'E', prob: 0.80 }, { next: 'F', prob: 0.70 }],
      'E': [{ next: 'F', prob: 0.75 }, { next: 'A', prob: 0.65 }],
      'F': [{ next: 'A', prob: 0.80 }, { next: 'B', prob: 0.70 }]
    }
  },
  pollution: {
    id: 'pollution',
    title: 'Pollution & Fixes (Inaccurate Predictions)',
    description: 'Working set of pages (A, B, C, D) is interrupted by infrequent distractor page E. Page E triggers low-confidence speculative prefetches (G, H) that displace hot working set pages under standard MRU insertion, doubling page faults. Turning on LRU-end insertion or Confidence Filtering (T=0.40) neutralizes pollution.',
    sequence: [
      'A','B','C','D',
      'A','B','C','D',
      'E',
      'D','C','B',
      'E',
      'D','C','B',
      'D','C','B','A'
    ],
    defaultK: 2,
    defaultInsertion: 'mru',
    defaultThreshold: 0.0,
    expected: {
      baselineFaults: 6,
      mruFaults: 12,
      lruEndFaults: 7,
      thresholdFaults: 6
    },
    markovTable: {
      'E': [{ next: 'G', prob: 0.35 }, { next: 'H', prob: 0.25 }]
    }
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SCENARIOS };
}

