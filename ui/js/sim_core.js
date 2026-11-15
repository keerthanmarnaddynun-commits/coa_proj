/**
 * ui/js/sim_core.js
 * High-performance, O(1) typed-array LRU cache and simulation engine.
 * Unified module for Node.js verification and browser/WebWorker execution.
 */

export class FastLRUCache {
  constructor(capacity = 1024, maxPages = 4096) {
    this.capacity = capacity;
    this.maxPages = maxPages;

    // Typed arrays for O(1) membership and doubly-linked list
    this.inCache = new Uint8Array(maxPages);
    this.isPrefetched = new Uint8Array(maxPages);
    this.prev = new Int16Array(maxPages);
    this.next = new Int16Array(maxPages);
    this.prev.fill(-1);
    this.next.fill(-1);

    this.head = -1; // MRU end
    this.tail = -1; // LRU end
    this.size = 0;

    // Cumulative prefetch metrics
    this.totalPrefetches = 0;
    this.prefetchHits = 0;
    this.prefetchWaste = 0;

    // Interval metrics for adaptive controller
    this.intervalPrefetches = 0;
    this.intervalHits = 0;
    this.intervalWastes = 0;
  }

  detach(p) {
    const pPrev = this.prev[p];
    const pNext = this.next[p];
    if (pPrev !== -1) {
      this.next[pPrev] = pNext;
    } else if (this.head === p) {
      this.head = pNext;
    }
    if (pNext !== -1) {
      this.prev[pNext] = pPrev;
    } else if (this.tail === p) {
      this.tail = pPrev;
    }
    this.prev[p] = -1;
    this.next[p] = -1;
  }

  attachHead(p) {
    this.prev[p] = -1;
    this.next[p] = this.head;
    if (this.head !== -1) {
      this.prev[this.head] = p;
    }
    this.head = p;
    if (this.tail === -1) {
      this.tail = p;
    }
  }

  attachTail(p) {
    this.next[p] = -1;
    this.prev[p] = this.tail;
    if (this.tail !== -1) {
      this.next[this.tail] = p;
    }
    this.tail = p;
    if (this.head === -1) {
      this.head = p;
    }
  }

  evictLRU() {
    const evicted = this.tail;
    if (evicted === -1) return -1;
    this.detach(evicted);
    this.inCache[evicted] = 0;
    this.size--;
    if (this.isPrefetched[evicted]) {
      this.prefetchWaste++;
      this.intervalWastes++;
      this.isPrefetched[evicted] = 0;
    }
    return evicted;
  }

  access(page) {
    if (this.inCache[page]) {
      // Cache Hit: promote to MRU
      if (this.head !== page) {
        this.detach(page);
        this.attachHead(page);
      }
      if (this.isPrefetched[page]) {
        this.prefetchHits++;
        this.intervalHits++;
        this.isPrefetched[page] = 0;
      }
      return true;
    }

    // Demand Page Fault: insert at MRU
    this.putDemand(page);
    return false;
  }

  putDemand(page) {
    if (this.inCache[page]) {
      if (this.head !== page) {
        this.detach(page);
        this.attachHead(page);
      }
    } else {
      if (this.size >= this.capacity) {
        this.evictLRU();
      }
      this.inCache[page] = 1;
      this.attachHead(page);
      this.size++;
    }
  }

  prefetchMRU(candidates) {
    for (let i = 0; i < candidates.length; i++) {
      const p = candidates[i];
      if (this.inCache[p]) {
        // Promoted to MRU if resident
        if (this.head !== p) {
          this.detach(p);
          this.attachHead(p);
        }
      } else {
        this.totalPrefetches++;
        this.intervalPrefetches++;
        if (this.size >= this.capacity) {
          this.evictLRU();
        }
        this.inCache[p] = 1;
        this.attachHead(p);
        this.size++;
        this.isPrefetched[p] = 1;
      }
    }
  }

  prefetchLRUEnd(candidates) {
    for (let i = 0; i < candidates.length; i++) {
      const p = candidates[i];
      if (!this.inCache[p]) {
        if (this.size >= this.capacity) {
          this.evictLRU();
        }
        this.inCache[p] = 1;
        this.attachTail(p);
        this.size++;
        this.totalPrefetches++;
        this.intervalPrefetches++;
        this.isPrefetched[p] = 1;
      }
    }
  }

  resetInterval() {
    this.intervalPrefetches = 0;
    this.intervalHits = 0;
    this.intervalWastes = 0;
  }

  /**
   * Returns current cache state as an array of page IDs ordered from MRU to LRU.
   */
  toArray() {
    const arr = [];
    let curr = this.head;
    while (curr !== -1) {
      arr.push(curr);
      curr = this.next[curr];
    }
    return arr;
  }
}

/**
 * Adaptive controller implementation matching Experiment 6.
 */
export class AdaptivePrefetchController {
  constructor(initK = 3, interval = 1000) {
    this.k = initK;
    this.interval = interval;
    this.adjustments = 0;
  }

  evaluate(cache) {
    if (cache.intervalPrefetches > 0) {
      const hitRate = cache.intervalHits / cache.intervalPrefetches;
      const wasteRate = cache.intervalWastes / cache.intervalPrefetches;

      if (hitRate > 0.60 && this.k < 5) {
        this.k++;
        this.adjustments++;
      } else if (wasteRate > 0.50 && this.k > 0) {
        this.k--;
        this.adjustments++;
      }
    }
    cache.resetInterval();
  }
}

/**
 * Executes a full cache simulation over a trace.
 *
 * @param {Object} params
 * @param {Uint16Array|Array<number>} params.trace - Array of page ID references
 * @param {number} [params.capacity=1024] - Cache size in physical frames
 * @param {number} [params.k=3] - Prefetch degree (0-5)
 * @param {number} [params.threshold=0.0] - Confidence threshold T (0.0 - 0.5)
 * @param {string} [params.insertion='mru'] - 'mru' or 'lru'
 * @param {string|Object} [params.model='markov'] - 'markov', 'oracle', or loaded model data
 * @param {boolean} [params.adaptive=false] - Whether adaptive controller is active
 * @param {number} [params.baselineFaults=67696] - Baseline faults for reduction calculation
 * @param {Function} [params.onProgress] - Optional callback (percent)
 * @param {Function} [params.isCancelled] - Optional cancellation check
 * @param {number} [params.maxPages=4096] - Maximum page ID space
 */
export function runSimulation(params) {
  const {
    trace,
    capacity = 1024,
    k = 3,
    threshold = 0.0,
    insertion = 'mru',
    model = 'markov',
    markovModel = null,
    oracleModel = null,
    adaptive = false,
    baselineFaults = 67696,
    onProgress = null,
    isCancelled = null,
    maxPages = 4096
  } = params;

  const totalAccesses = trace.length;
  const cache = new FastLRUCache(capacity, maxPages);
  const controller = adaptive ? new AdaptivePrefetchController(3, 1000) : null;

  let pageFaults = 0;
  const isPredictive = (k > 0 || adaptive);
  const isLRUEnd = (insertion.toLowerCase() === 'lru');

  // Timeline tracking (every 50,000 references)
  const chunkSize = 50000;
  const numChunks = Math.ceil(totalAccesses / chunkSize);
  const timelineFaults = new Uint32Array(numChunks);
  const timelineK = adaptive ? new Uint8Array(numChunks) : null;

  let currentChunkFaults = 0;
  let chunkIdx = 0;
  const progressInterval = 250000;

  const isOracle = (model === 'oracle');
  const activeModel = isOracle ? oracleModel : markovModel;

  for (let i = 0; i < totalAccesses; i++) {
    if (isCancelled && (i & 0xffff) === 0 && isCancelled()) {
      return { cancelled: true };
    }

    if (onProgress && i > 0 && i % progressInterval === 0) {
      onProgress(Math.round((i / totalAccesses) * 100));
    }

    const page = trace[i];
    const isHit = cache.access(page);

    if (!isHit) {
      pageFaults++;
      currentChunkFaults++;

      const activeK = adaptive ? controller.k : k;

      if (isPredictive && activeK > 0 && activeModel) {
        let candidates = null;

        if (isOracle) {
          // Oracle: list of neighbor IDs
          const list = activeModel[page];
          if (list && list.length > 0) {
            candidates = list.length <= activeK ? list : list.slice(0, activeK);
          }
        } else {
          // Markov: candidates with probabilities
          const entry = activeModel[page];
          if (entry && entry.candidates && entry.candidates.length > 0) {
            const cList = entry.candidates;
            const qualified = [];
            const lim = Math.min(activeK, cList.length);
            for (let c = 0; c < lim; c++) {
              const item = cList[c];
              if (item.prob >= threshold) {
                qualified.push(item.id);
              }
            }
            if (qualified.length > 0) {
              candidates = qualified;
            }
          }
        }

        if (candidates && candidates.length > 0) {
          if (isLRUEnd) {
            cache.prefetchLRUEnd(candidates);
          } else {
            cache.prefetchMRU(candidates);
          }
        }
      }

      if (adaptive && (pageFaults % 1000 === 0)) {
        controller.evaluate(cache);
      }
    }

    if ((i + 1) % chunkSize === 0 || i === totalAccesses - 1) {
      timelineFaults[chunkIdx] = currentChunkFaults;
      if (timelineK) {
        timelineK[chunkIdx] = adaptive ? controller.k : k;
      }
      chunkIdx++;
      currentChunkFaults = 0;
    }
  }

  const hits = totalAccesses - pageFaults;
  const hitRatio = totalAccesses > 0 ? (hits / totalAccesses) * 100 : 0;
  const faultRatio = totalAccesses > 0 ? (pageFaults / totalAccesses) * 100 : 0;
  const reduction = baselineFaults > 0 ? ((baselineFaults - pageFaults) / baselineFaults) * 100 : 0;
  const precision = cache.totalPrefetches > 0 ? (cache.prefetchHits / cache.totalPrefetches) * 100 : 0;
  const waste = cache.totalPrefetches > 0 ? (cache.prefetchWaste / cache.totalPrefetches) * 100 : 0;

  return {
    totalAccesses,
    pageFaults,
    hits,
    hitRatio,
    faultRatio,
    reduction,
    totalPrefetches: cache.totalPrefetches,
    prefetchHits: cache.prefetchHits,
    prefetchWaste: cache.prefetchWaste,
    precision,
    waste,
    adjustments: controller ? controller.adjustments : 0,
    finalK: controller ? controller.k : k,
    timelineFaults: Array.from(timelineFaults),
    timelineK: timelineK ? Array.from(timelineK) : null
  };
}

// Support CommonJS environments if loaded via require()
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { FastLRUCache, AdaptivePrefetchController, runSimulation };
}

