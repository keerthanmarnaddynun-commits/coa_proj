/**
 * ui/js/app.js
 * Main application logic for the OS/COA Markov Prefetching Interactive Presentation UI.
 */

import { SCENARIOS } from './scenarios.js';
import { FastLRUCache } from './sim_core.js';
import { ChartRenderer } from './charts.js';

// Application state
const state = {
  theme: 'light',
  activeTab: 'problem',
  experimentsData: null,
  selectedExpId: 'E1',
  comparisonHistory: [],
  baselineRun: null, // Holds baseline timeline and faults for 1,024 frames
  baselineCache: {}, // { [capacity]: { faults, timeline } }
  currentRun: null,

  // Tab 2 Walkthrough state
  walkthrough: {
    scenarioId: 'helps',
    stepIdx: 0,
    isPlaying: false,
    timer: null,
    speedMs: 1200,
    k: 2,
    insertion: 'mru',
    threshold: 0.0,
    baseCache: null,
    prefCache: null,
    baseFaults: 0,
    prefFaults: 0,
    history: [],
    lastRender: null
  },

  // Tab 3 Worker state
  worker: null,
  simRunning: false,
  activeParams: null,
  hideProgressTimer: null,
  pendingPresets: ['preset-top3']
};

const KNOWN_BASELINES = {
  512: 221603,
  1024: 67696,
  2048: 2025
};

function getBaselineFaults(frames) {
  if (state.baselineCache[frames] !== undefined) {
    return state.baselineCache[frames].faults;
  }
  if (KNOWN_BASELINES[frames] !== undefined) {
    return KNOWN_BASELINES[frames];
  }
  return null;
}

// Safe localStorage access
function getSavedTheme() {
  try {
    return localStorage.getItem('coa_ui_theme') || 'light';
  } catch (e) {
    return 'light';
  }
}

function saveTheme(theme) {
  try {
    localStorage.setItem('coa_ui_theme', theme);
  } catch (e) {}
}

// Initialize Theme
function initTheme() {
  state.theme = getSavedTheme();
  document.documentElement.setAttribute('data-theme', state.theme);
  updateThemeButton();
}

function toggleTheme() {
  state.theme = state.theme === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', state.theme);
  saveTheme(state.theme);
  updateThemeButton();
  redrawActiveCharts();
}

function updateThemeButton() {
  const btn = document.getElementById('theme-toggle');
  if (btn) {
    btn.innerHTML = state.theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode';
  }
}

// Navigation Tabs
function initNavigation() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;
      switchTab(target);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll('.nav-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tabId);
  });
  document.querySelectorAll('.tab-pane').forEach(p => {
    p.classList.toggle('active', p.id === `tab-${tabId}`);
  });

  if (tabId === 'live') {
    setTimeout(() => redrawTimelineChart(), 50);
  } else if (tabId === 'experiments') {
    renderSelectedExperiment();
  }
}

// Redraw charts on resize or theme change
function redrawActiveCharts() {
  if (state.activeTab === 'live') {
    redrawTimelineChart();
  } else if (state.activeTab === 'experiments') {
    renderExperimentChart(state.selectedExpId);
  }
}

window.addEventListener('resize', () => {
  redrawActiveCharts();
});

// Load experiments data from results.json
async function loadExperimentsData() {
  try {
    const res = await fetch('data/results.json');
    state.experimentsData = await res.json();
    initExperimentsTab();
  } catch (err) {
    console.error('Failed to load results.json:', err);
  }
}

// TAB 2: CONCEPT WALKTHROUGH IMPLEMENTATION
const P_MAP = { A: 0, B: 1, C: 2, D: 3, E: 4, F: 5, G: 6, H: 7 };
const ID_TO_NAME = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'];

function initWalkthrough() {
  setupWalkthroughScenario('helps');

  document.getElementById('wt-btn-helps').addEventListener('click', () => setupWalkthroughScenario('helps'));
  document.getElementById('wt-btn-pollution').addEventListener('click', () => setupWalkthroughScenario('pollution'));

  document.getElementById('wt-btn-step').addEventListener('click', stepWalkthrough);
  document.getElementById('wt-btn-back').addEventListener('click', backWalkthrough);
  document.getElementById('wt-btn-play').addEventListener('click', togglePlayWalkthrough);
  document.getElementById('wt-btn-reset').addEventListener('click', resetWalkthrough);

  const speedSlider = document.getElementById('wt-speed');
  speedSlider.addEventListener('input', (e) => {
    state.walkthrough.speedMs = parseInt(e.target.value);
    document.getElementById('wt-speed-val').textContent = `${(state.walkthrough.speedMs / 1000).toFixed(1)}s`;
    if (state.walkthrough.isPlaying) {
      clearInterval(state.walkthrough.timer);
      state.walkthrough.timer = setInterval(stepWalkthrough, state.walkthrough.speedMs);
    }
  });

  const kSelect = document.getElementById('wt-k');
  kSelect.addEventListener('change', (e) => {
    state.walkthrough.k = parseInt(e.target.value);
    resetWalkthrough();
  });

  const insSelect = document.getElementById('wt-insertion');
  insSelect.addEventListener('change', (e) => {
    state.walkthrough.insertion = e.target.value;
    resetWalkthrough();
  });

  const threshSlider = document.getElementById('wt-threshold');
  threshSlider.addEventListener('input', (e) => {
    state.walkthrough.threshold = parseFloat(e.target.value);
    document.getElementById('wt-thresh-val').textContent = state.walkthrough.threshold.toFixed(2);
    resetWalkthrough();
  });
}

function setupWalkthroughScenario(scenId) {
  state.walkthrough.scenarioId = scenId;
  const scen = SCENARIOS[scenId];

  document.getElementById('wt-btn-helps').classList.toggle('btn-primary', scenId === 'helps');
  document.getElementById('wt-btn-helps').classList.toggle('btn-secondary', scenId !== 'helps');
  document.getElementById('wt-btn-pollution').classList.toggle('btn-primary', scenId === 'pollution');
  document.getElementById('wt-btn-pollution').classList.toggle('btn-secondary', scenId !== 'pollution');

  document.getElementById('wt-scen-title').textContent = scen.title;
  document.getElementById('wt-scen-desc').textContent = scen.description;

  // Set default controls for scenario
  state.walkthrough.k = scen.defaultK;
  state.walkthrough.insertion = scen.defaultInsertion;
  state.walkthrough.threshold = scen.defaultThreshold;

  document.getElementById('wt-k').value = state.walkthrough.k;
  document.getElementById('wt-insertion').value = state.walkthrough.insertion;
  document.getElementById('wt-threshold').value = state.walkthrough.threshold;
  document.getElementById('wt-thresh-val').textContent = state.walkthrough.threshold.toFixed(2);

  // Render Markov Table
  renderWalkthroughMarkovTable(scen.markovTable);

  // Render Verification box
  renderScenarioVerificationBox(scen);

  resetWalkthrough();
}

function renderScenarioVerificationBox(scen) {
  const box = document.getElementById('wt-verified-box');
  if (scen.id === 'helps') {
    box.innerHTML = `
      <div class="callout">
        <strong>Verified Simulation Target (4 Frames, 20 Refs):</strong><br>
        Baseline Demand LRU: <strong>${scen.expected.baselineFaults} faults</strong> | 
        Markov Prefetch (k=1): <strong>${scen.expected.prefetchK1Faults} faults</strong> | 
        Markov Prefetch (k=2): <strong>${scen.expected.prefetchK2Faults} faults (65% fewer)</strong>
      </div>
    `;
  } else {
    box.innerHTML = `
      <div class="callout orange">
        <strong>Verified Simulation Target (4 Frames, 20 Refs):</strong><br>
        Baseline Demand: <strong>${scen.expected.baselineFaults} faults</strong> | 
        MRU Prefetch (Pollution): <strong>${scen.expected.mruFaults} faults (+100% worse!)</strong><br>
        Fix 1 (LRU-end): <strong>${scen.expected.lruEndFaults} faults</strong> | 
        Fix 2 (Threshold T=0.40): <strong>${scen.expected.thresholdFaults} faults (pollution neutralized)</strong>
      </div>
    `;
  }
}

function renderWalkthroughMarkovTable(table) {
  const container = document.getElementById('wt-markov-table');
  let html = '<table class="data-table"><thead><tr><th>Page</th><th>Successors & Probabilities</th></tr></thead><tbody>';
  const keys = Object.keys(table);
  if (keys.length === 0) {
    html += '<tr><td colspan="2" style="text-align:center; color:var(--text-muted);">No transitions recorded for this working set.</td></tr>';
  } else {
    for (const k of keys) {
      const preds = table[k].map(item => `<strong>${item.next}</strong> (P=${item.prob.toFixed(2)})`).join(', ');
      html += `<tr><td><span class="ref-token" style="display:inline-flex; width:28px; height:28px; font-size:0.9rem;">${k}</span></td><td>${preds}</td></tr>`;
    }
  }
  html += '</tbody></table>';
  container.innerHTML = html;
}

function resetWalkthrough() {
  if (state.walkthrough.isPlaying) {
    togglePlayWalkthrough();
  }

  const wt = state.walkthrough;
  wt.stepIdx = 0;
  wt.baseCache = new FastLRUCache(4, 16);
  wt.prefCache = new FastLRUCache(4, 16);
  wt.baseFaults = 0;
  wt.prefFaults = 0;
  wt.history = [];
  wt.lastRender = null;

  renderWalkthroughUI();
}

function stepWalkthrough() {
  const wt = state.walkthrough;
  const scen = SCENARIOS[wt.scenarioId];
  if (wt.stepIdx >= scen.sequence.length) {
    if (wt.isPlaying) togglePlayWalkthrough();
    return;
  }

  // Save snapshot for Back button
  wt.history.push({
    baseCacheState: wt.baseCache.toArray(),
    baseFaults: wt.baseFaults,
    prefCacheState: wt.prefCache.toArray(),
    prefFaults: wt.prefFaults,
    stepIdx: wt.stepIdx,
    prefTracked: Array.from(wt.prefCache.isPrefetched),
    lastRender: wt.lastRender
  });

  const pageName = scen.sequence[wt.stepIdx];
  const pageId = P_MAP[pageName];

  // 1. Step Baseline Cache
  const baseHit = wt.baseCache.access(pageId);
  if (!baseHit) wt.baseFaults++;

  // 2. Step Prefetch Cache
  const prefHit = wt.prefCache.access(pageId);
  let prefetchedCands = [];
  if (!prefHit) {
    wt.prefFaults++;
    const entry = scen.markovTable[pageName];
    if (wt.k > 0 && entry && entry.length > 0) {
      for (let i = 0; i < Math.min(wt.k, entry.length); i++) {
        if (entry[i].prob >= wt.threshold) {
          prefetchedCands.push(entry[i]);
        }
      }
      const candIds = prefetchedCands.map(c => P_MAP[c.next]);
      if (candIds.length > 0) {
        if (wt.insertion === 'lru') {
          wt.prefCache.prefetchLRUEnd(candIds);
        } else {
          wt.prefCache.prefetchMRU(candIds);
        }
      }
    }
  }

  wt.stepIdx++;
  wt.lastRender = { pageName, baseHit, prefHit, prefetchedCands };
  renderWalkthroughUI(pageName, baseHit, prefHit, prefetchedCands);
}

function backWalkthrough() {
  const wt = state.walkthrough;
  if (wt.history.length === 0) return;
  const prev = wt.history.pop();

  wt.stepIdx = prev.stepIdx;
  wt.baseFaults = prev.baseFaults;
  wt.prefFaults = prev.prefFaults;

  // Rebuild cache states
  wt.baseCache = new FastLRUCache(4, 16);
  for (let i = prev.baseCacheState.length - 1; i >= 0; i--) {
    wt.baseCache.putDemand(prev.baseCacheState[i]);
  }

  wt.prefCache = new FastLRUCache(4, 16);
  for (let i = prev.prefCacheState.length - 1; i >= 0; i--) {
    wt.prefCache.putDemand(prev.prefCacheState[i]);
  }
  for (let p = 0; p < 16; p++) {
    wt.prefCache.isPrefetched[p] = prev.prefTracked[p];
  }

  wt.lastRender = prev.lastRender || null;
  if (wt.lastRender) {
    const { pageName, baseHit, prefHit, prefetchedCands } = wt.lastRender;
    renderWalkthroughUI(pageName, baseHit, prefHit, prefetchedCands);
  } else {
    renderWalkthroughUI();
  }
}

function togglePlayWalkthrough() {
  const wt = state.walkthrough;
  wt.isPlaying = !wt.isPlaying;
  const playBtn = document.getElementById('wt-btn-play');

  if (wt.isPlaying) {
    playBtn.innerHTML = '⏸ Pause';
    playBtn.classList.remove('btn-secondary');
    playBtn.classList.add('btn-primary');
    wt.timer = setInterval(stepWalkthrough, wt.speedMs);
  } else {
    playBtn.innerHTML = '▶ Play';
    playBtn.classList.remove('btn-primary');
    playBtn.classList.add('btn-secondary');
    clearInterval(wt.timer);
  }
}

function renderWalkthroughUI(lastPage = null, baseHit = null, prefHit = null, prefetched = []) {
  const wt = state.walkthrough;
  const scen = SCENARIOS[wt.scenarioId];

  // Update Reference Tape
  const tapeContainer = document.getElementById('wt-ref-tape');
  tapeContainer.innerHTML = scen.sequence.map((p, idx) => {
    let cls = 'ref-token';
    if (idx < wt.stepIdx - 1) cls += ' done';
    else if (idx === wt.stepIdx - 1) cls += ' active';
    return `<div class="${cls}">${p}</div>`;
  }).join('');

  // Update Fault Counters
  document.getElementById('wt-base-faults').textContent = `Faults: ${wt.baseFaults}`;
  document.getElementById('wt-pref-faults').textContent = `Faults: ${wt.prefFaults}`;

  // Render Left Cache (Baseline)
  const baseFrames = wt.baseCache.toArray();
  renderFrames('wt-base-frames', baseFrames, lastPage ? P_MAP[lastPage] : null, baseHit, null);

  // Render Right Cache (Prefetch)
  const prefFrames = wt.prefCache.toArray();
  renderFrames('wt-pref-frames', prefFrames, lastPage ? P_MAP[lastPage] : null, prefHit, wt.prefCache.isPrefetched);

  // Narration text
  const narElem = document.getElementById('wt-narration');
  if (wt.stepIdx === 0) {
    narElem.innerHTML = '<em>Press "Step" or "Play" to start step-by-step memory simulation.</em>';
  } else {
    let txt = `Step ${wt.stepIdx}/${scen.sequence.length}: Accessed page <strong>${lastPage}</strong>. `;
    txt += `Baseline: ${baseHit ? '<span style="color:#10b981; font-weight:700;">HIT ✓</span>' : '<span style="color:var(--color-harm); font-weight:700;">FAULT ✗</span>'}. `;
    txt += `Prefetch Side: ${prefHit ? '<span style="color:#10b981; font-weight:700;">HIT ✓</span>' : '<span style="color:var(--color-harm); font-weight:700;">FAULT ✗</span>'}. `;

    if (!prefHit && prefetched && prefetched.length > 0) {
      const pStr = prefetched.map(c => `<strong>${c.next}</strong> (P=${c.prob.toFixed(2)})`).join(', ');
      txt += `Issued prefetch for ${pStr} at <strong>${wt.insertion.toUpperCase()}</strong> position.`;
    } else if (!prefHit) {
      txt += `No qualified candidates to prefetch (threshold T=${wt.threshold.toFixed(2)}).`;
    }
    narElem.innerHTML = txt;
  }
}

function renderFrames(containerId, frameIds, activeId, wasHit, isPrefetchedArray) {
  const container = document.getElementById(containerId);
  let html = '';
  for (let i = 0; i < 4; i++) {
    const pId = frameIds[i];
    let badgeCls = '';
    if (pId !== undefined) {
      if (i === 0) badgeCls = 'mru-badge';
      else if (i === frameIds.length - 1) badgeCls = 'lru-badge';
    }

    let eventCls = '';
    let name = '-';
    let isPref = false;

    if (pId !== undefined) {
      name = ID_TO_NAME[pId];
      if (isPrefetchedArray && isPrefetchedArray[pId]) {
        isPref = true;
      }
      if (pId === activeId) {
        eventCls = wasHit ? 'event-hit' : 'event-fault';
      } else if (isPref) {
        eventCls = 'prefetched-page';
      }
    }

    html += `
      <div class="frame-cell ${badgeCls} ${eventCls}">
        <span class="page-name">${name}</span>
        ${isPref ? '<span style="font-size:9px; color:var(--color-prefetch); font-weight:700;">SPEC</span>' : ''}
      </div>
    `;
  }
  container.innerHTML = html;
}

// TAB 3: LIVE SIMULATOR & WORKER
function spawnWorker() {
  try {
    state.worker = new Worker('js/worker.js', { type: 'module' });
    state.worker.onmessage = handleWorkerMessage;
    state.worker.onerror = (ev) => {
      const failed = state.worker;
      console.error('Worker error:', ev.message || ev);
      state.pendingPresets = [];
      resetSimControls();
      clearTimeout(state.hideProgressTimer);
      document.getElementById('sim-progress-text').textContent = 'The simulation worker failed. Reload the page; if it keeps failing, start it with run_ui.bat.';
      document.getElementById('sim-progress-box').style.display = 'block';
      if (failed) { try { failed.terminate(); } catch (e) {} }
      state.worker = null;
      if (ev.preventDefault) ev.preventDefault();
    };
  } catch (err) {
    console.error('Failed to initialize Web Worker:', err);
  }
}

// The graph oracle has no probabilities, so the confidence threshold T does not apply to it
function syncThresholdForModel() {
  const isOracle = document.getElementById('sim-model').value === 'oracle';
  document.getElementById('sim-threshold').disabled = isOracle;
  document.getElementById('sim-threshold-note').style.display = isOracle ? 'block' : 'none';
}

function initLiveSimulator() {
  spawnWorker();

  // Button handlers
  document.getElementById('sim-run-btn').addEventListener('click', runLiveSimulation);
  document.getElementById('sim-cancel-btn').addEventListener('click', cancelLiveSimulation);
  document.getElementById('clear-history-btn').addEventListener('click', clearComparisonHistory);

  // Preset buttons
  const presets = {
    'preset-baseline': { capacity: 1024, k: 0, model: 'markov', threshold: 0.0, insertion: 'mru', adaptive: false },
    'preset-top3': { capacity: 1024, k: 3, model: 'markov', threshold: 0.0, insertion: 'mru', adaptive: false },
    'preset-top5': { capacity: 1024, k: 5, model: 'markov', threshold: 0.0, insertion: 'mru', adaptive: false },
    'preset-512-hurts': { capacity: 512, k: 3, model: 'markov', threshold: 0.0, insertion: 'mru', adaptive: false },
    'preset-fix1': { capacity: 1024, k: 3, model: 'markov', threshold: 0.10, insertion: 'mru', adaptive: false },
    'preset-fix2': { capacity: 512, k: 3, model: 'markov', threshold: 0.0, insertion: 'lru', adaptive: false },
    'preset-fix3': { capacity: 512, k: 3, model: 'markov', threshold: 0.0, insertion: 'mru', adaptive: true },
    'preset-oracle': { capacity: 1024, k: 3, model: 'oracle', threshold: 0.0, insertion: 'mru', adaptive: false }
  };

  Object.entries(presets).forEach(([btnId, p]) => {
    const el = document.getElementById(btnId);
    if (el) {
      el.addEventListener('click', () => applyPreset(p, btnId));
    }
  });

  // Adaptive toggle listener
  const adaptToggle = document.getElementById('sim-adaptive');
  adaptToggle.addEventListener('change', (e) => {
    const kGroup = document.getElementById('sim-k-group');
    if (e.target.checked) {
      kGroup.style.opacity = '0.5';
    } else {
      kGroup.style.opacity = '1';
    }
  });

  // RAM frames custom option
  const capSelect = document.getElementById('sim-capacity');
  capSelect.addEventListener('change', (e) => {
    const customInput = document.getElementById('sim-capacity-custom');
    if (e.target.value === 'custom') {
      customInput.style.display = 'inline-block';
    } else {
      customInput.style.display = 'none';
    }
  });

  // Threshold slider display
  const threshSlider = document.getElementById('sim-threshold');
  threshSlider.addEventListener('input', (e) => {
    document.getElementById('sim-threshold-val').textContent = parseFloat(e.target.value).toFixed(2);
  });
  document.getElementById('sim-model').addEventListener('change', syncThresholdForModel);

  // COA Calculator inputs
  ['eat-mem-time', 'eat-fault-time', 'eat-prefetch-cost'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      if (id === 'eat-prefetch-cost') {
        const valSpan = document.getElementById('eat-prefetch-cost-val');
        const syncPrefetchCostLabel = () => {
          if (valSpan) valSpan.textContent = `${el.value}%`;
        };
        syncPrefetchCostLabel();
        el.addEventListener('input', syncPrefetchCostLabel);
      }
      el.addEventListener('input', updateCOACalculator);
    }
  });

  // Changing a control by hand means the setup no longer matches a preset
  ['sim-capacity', 'sim-capacity-custom', 'sim-k', 'sim-model', 'sim-threshold', 'sim-insertion', 'sim-adaptive'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => setActivePreset(null));
      el.addEventListener('change', () => setActivePreset(null));
    }
  });

  // Auto-run baseline first so its timeline is available for comparison
  clickPreset('preset-baseline');
}

// Show which preset button is active (none when the controls were changed by hand)
function setActivePreset(activeId) {
  document.querySelectorAll('.preset-bar button').forEach(btn => {
    const on = btn.id === activeId;
    btn.classList.toggle('btn-primary', on);
    btn.classList.toggle('btn-secondary', !on);
  });
}

function applyPreset(p, btnId) {
  if (state.simRunning) return;
  setActivePreset(btnId);
  const capSelect = document.getElementById('sim-capacity');
  const customInput = document.getElementById('sim-capacity-custom');

  if ([256, 512, 1024, 2048].includes(p.capacity)) {
    capSelect.value = p.capacity.toString();
    customInput.style.display = 'none';
  } else {
    capSelect.value = 'custom';
    customInput.style.display = 'inline-block';
    customInput.value = p.capacity;
  }

  document.getElementById('sim-k').value = p.k.toString();
  document.getElementById('sim-model').value = p.model;
  document.getElementById('sim-threshold').value = p.threshold.toString();
  document.getElementById('sim-threshold-val').textContent = p.threshold.toFixed(2);
  syncThresholdForModel();
  document.getElementById('sim-insertion').value = p.insertion;
  document.getElementById('sim-adaptive').checked = p.adaptive;

  const kGroup = document.getElementById('sim-k-group');
  kGroup.style.opacity = p.adaptive ? '0.5' : '1';

  runLiveSimulation();
}

function clickPreset(presetId) {
  const el = document.getElementById(presetId);
  if (el) el.click();
}

export function runPresetByName(presetId) {
  switchTab('live');
  clickPreset(presetId);
}

function getSimulationParams() {
  const capSelect = document.getElementById('sim-capacity');
  let capacity = 1024;
  if (capSelect.value === 'custom') {
    capacity = parseInt(document.getElementById('sim-capacity-custom').value) || 1024;
  } else {
    capacity = parseInt(capSelect.value);
  }

  const k = parseInt(document.getElementById('sim-k').value);
  const model = document.getElementById('sim-model').value;
  const threshold = model === 'oracle' ? 0 : parseFloat(document.getElementById('sim-threshold').value);
  const insertion = document.getElementById('sim-insertion').value;
  const adaptive = document.getElementById('sim-adaptive').checked;

  return { capacity, k, model, threshold, insertion, adaptive };
}

function runLiveSimulation() {
  if (!state.worker) {
    clearTimeout(state.hideProgressTimer);
    document.getElementById('sim-progress-text').textContent = 'The simulation worker failed. Reload the page; if it keeps failing, start it with run_ui.bat.';
    document.getElementById('sim-progress-box').style.display = 'block';
    return;
  }
  if (state.simRunning) return;

  clearTimeout(state.hideProgressTimer);
  const params = getSimulationParams();
  state.activeParams = params;
  state.simRunning = true;

  document.getElementById('sim-run-btn').disabled = true;
  document.getElementById('sim-cancel-btn').disabled = false;
  document.getElementById('sim-progress-box').style.display = 'block';
  document.getElementById('sim-progress-bar').style.width = '0%';
  document.getElementById('sim-progress-text').textContent = 'Starting simulation...';

  // Find baseline faults for this capacity if known
  const baselineFaults = getBaselineFaults(params.capacity);

  state.worker.postMessage({
    type: 'RUN',
    payload: {
      capacity: params.capacity,
      k: params.k,
      threshold: params.threshold,
      insertion: params.insertion,
      model: params.model,
      adaptive: params.adaptive,
      baselineFaults
    }
  });
}

function cancelLiveSimulation() {
  if (!state.simRunning) return;
  state.pendingPresets = [];
  state.worker.terminate();
  spawnWorker();
  resetSimControls();
  document.getElementById('sim-progress-text').textContent = 'Simulation cancelled.';
}

function handleWorkerMessage(e) {
  const { type, percent, result, error } = e.data;

  if (type === 'PROGRESS') {
    document.getElementById('sim-progress-bar').style.width = `${percent}%`;
    document.getElementById('sim-progress-text').textContent = `Simulating 3,780,309 accesses... ${percent}%`;
  } else if (type === 'DONE') {
    finishSimulation(result);
  } else if (type === 'CANCELLED') {
    resetSimControls();
    document.getElementById('sim-progress-text').textContent = 'Simulation cancelled.';
  } else if (type === 'ERROR') {
    const msg = 'Simulation error: ' + error;
    console.error(msg);
    state.pendingPresets = [];
    resetSimControls();
    clearTimeout(state.hideProgressTimer);
    document.getElementById('sim-progress-text').textContent = msg;
    document.getElementById('sim-progress-box').style.display = 'block';
  }
}

function finishSimulation(result) {
  resetSimControls();
  document.getElementById('sim-progress-text').textContent = 'Trace A (3,780,309 accesses ready)';
  state.currentRun = result;

  const params = state.activeParams || getSimulationParams();
  result.config = params;

  // Save baseline timeline if running baseline
  if (params.k === 0 && !params.adaptive) {
    state.baselineCache[params.capacity] = {
      faults: result.pageFaults,
      timeline: result.timelineFaults
    };
  }

  const baseFaults = getBaselineFaults(params.capacity);
  result.reduction = (baseFaults !== null && baseFaults > 0)
    ? ((baseFaults - result.pageFaults) / baseFaults) * 100
    : null;

  // Display results in UI
  displayResults(result);

  // Append to Comparison Table
  addComparisonRow(result);

  // Redraw Timeline Chart
  redrawTimelineChart();

  // Update COA calculator
  updateCOACalculator();

  const nextPreset = state.pendingPresets.shift();
  if (nextPreset) {
    clickPreset(nextPreset);
  }
}

function resetSimControls() {
  state.simRunning = false;
  document.getElementById('sim-run-btn').disabled = false;
  document.getElementById('sim-cancel-btn').disabled = true;
  state.hideProgressTimer = setTimeout(() => {
    document.getElementById('sim-progress-box').style.display = 'none';
  }, 400);
}

function displayResults(res) {
  document.getElementById('res-faults').textContent = res.pageFaults.toLocaleString('en-US');
  document.getElementById('res-hit-ratio').textContent = `${res.hitRatio.toFixed(3)}%`;

  // Fault reduction vs baseline
  const redElem = document.getElementById('res-reduction');
  if (res.reduction === null || res.reduction === undefined) {
    redElem.textContent = 'n/a';
    redElem.className = 'stat-value baseline';
  } else {
    const sign = res.reduction > 0 ? '+' : '';
    redElem.textContent = `${sign}${res.reduction.toFixed(2)}%`;
    redElem.className = `stat-value ${res.reduction > 0 ? 'prefetch' : (res.reduction < 0 ? 'harm' : 'baseline')}`;
  }

  document.getElementById('res-prefetches').textContent = res.totalPrefetches.toLocaleString('en-US');
  document.getElementById('res-precision').textContent = `${res.precision.toFixed(2)}%`;
  document.getElementById('res-waste').textContent = `${res.waste.toFixed(2)}%`;

  const adaptInfo = document.getElementById('res-adaptive-info');
  let infoText = '';
  if (res.reduction === null || res.reduction === undefined) {
    infoText = 'Baseline not run at this size: run k=0 to compare';
  } else if (res.reduction > 0) {
    infoText = 'Fewer faults than baseline LRU (same frame count)';
  } else if (res.reduction < 0) {
    infoText = 'More faults than baseline LRU (same frame count)';
  } else if (res.config.k === 0 && !res.config.adaptive) {
    infoText = 'This run is the baseline';
  } else {
    infoText = 'Same faults as baseline LRU';
  }
  if (res.config.adaptive) {
    infoText += ` | Adaptive: ${res.adjustments} adjustments, Final k=${res.finalK}`;
  }
  adaptInfo.textContent = infoText;
  adaptInfo.style.display = 'block';

  // Check verified badge
  checkVerifiedBadge(res);
}

function checkVerifiedBadge(res) {
  const badge = document.getElementById('verified-paper-badge');
  const c = res.config;

  const knownRuns = [
    { capacity: 1024, model: 'markov', k: 0, threshold: 0.0, insertion: 'mru', adaptive: false, faults: 67696 },
    { capacity: 1024, model: 'markov', k: 1, threshold: 0.0, insertion: 'mru', adaptive: false, faults: 67634 },
    { capacity: 1024, model: 'markov', k: 2, threshold: 0.0, insertion: 'mru', adaptive: false, faults: 63132 },
    { capacity: 1024, model: 'markov', k: 3, threshold: 0.0, insertion: 'mru', adaptive: false, faults: 57512 },
    { capacity: 1024, model: 'markov', k: 5, threshold: 0.0, insertion: 'mru', adaptive: false, faults: 63041 },
    { capacity: 1024, model: 'markov', k: 3, threshold: 0.05, insertion: 'mru', adaptive: false, faults: 55816, totalPrefetches: 50258 },
    { capacity: 1024, model: 'markov', k: 3, threshold: 0.10, insertion: 'mru', adaptive: false, faults: 55751, totalPrefetches: 49339 },
    { capacity: 1024, model: 'markov', k: 3, threshold: 0.20, insertion: 'mru', adaptive: false, faults: 59431, totalPrefetches: 32463 },
    { capacity: 1024, model: 'markov', k: 3, threshold: 0.30, insertion: 'mru', adaptive: false, faults: 67667, totalPrefetches: 38 },
    { capacity: 1024, model: 'markov', k: 3, threshold: 0.50, insertion: 'mru', adaptive: false, faults: 67683, totalPrefetches: 14 },
    { capacity: 512,  model: 'markov', k: 0, threshold: 0.0, insertion: 'mru', adaptive: false, faults: 221603 },
    { capacity: 512,  model: 'markov', k: 3, threshold: 0.0, insertion: 'mru', adaptive: false, faults: 237684 },
    { capacity: 2048, model: 'markov', k: 0, threshold: 0.0, insertion: 'mru', adaptive: false, faults: 2025 },
    { capacity: 2048, model: 'markov', k: 3, threshold: 0.0, insertion: 'mru', adaptive: false, faults: 935 },
    { capacity: 512,  model: 'markov', k: 3, threshold: 0.0, insertion: 'lru', adaptive: false, faults: 191587 },
    { capacity: 1024, model: 'markov', k: 3, threshold: 0.0, insertion: 'lru', adaptive: false, faults: 60622 },
    { capacity: 512,  model: 'markov', k: null, threshold: 0.0, insertion: null, adaptive: true, faults: 212106, adjustments: 159, finalK: 2 },
    { capacity: 1024, model: 'markov', k: null, threshold: 0.0, insertion: null, adaptive: true, faults: 57609, adjustments: 6, finalK: 5 },
    { capacity: 2048, model: 'markov', k: null, threshold: 0.0, insertion: null, adaptive: true, faults: 935, adjustments: 0, finalK: 3 },
    { capacity: 1024, model: 'oracle', k: 3, threshold: 0.0, insertion: 'mru', adaptive: false, faults: 57230 }
  ];

  let isVerified = false;
  for (const entry of knownRuns) {
    if (c.capacity !== entry.capacity) continue;
    if (c.model !== entry.model) continue;
    if (c.threshold !== entry.threshold) continue;
    if (c.adaptive !== entry.adaptive) continue;
    if (!entry.adaptive && (c.k !== entry.k || c.insertion !== entry.insertion)) continue;
    if (res.pageFaults !== entry.faults) continue;
    if (entry.totalPrefetches !== undefined && res.totalPrefetches !== entry.totalPrefetches) continue;
    if (entry.adjustments !== undefined && res.adjustments !== entry.adjustments) continue;
    if (entry.finalK !== undefined && res.finalK !== entry.finalK) continue;
    isVerified = true;
    break;
  }

  badge.style.display = isVerified ? 'inline-flex' : 'none';
}

function redrawTimelineChart() {
  const canvas = document.getElementById('sim-timeline-canvas');
  if (!canvas || !state.currentRun) return;

  const cap = state.currentRun.config.capacity;
  const baseTimeline = state.baselineCache[cap]?.timeline || [];

  ChartRenderer.renderTimeline(canvas, {
    baselineTimeline: baseTimeline,
    currentTimeline: state.currentRun.timelineFaults,
    kTimeline: state.currentRun.timelineK
  }, {
    isDark: state.theme === 'dark',
    isHarmful: state.currentRun.reduction < 0,
    chunkSize: 50000,
    totalRefs: 3780309,
    runLabel: `Run (k=${state.currentRun.config.adaptive ? 'adapt' : state.currentRun.config.k}, ${state.currentRun.config.insertion.toUpperCase()})`
  });
}

function addComparisonRow(res) {
  const c = res.config;
  let cfgName = `${c.capacity} frames, `;
  if (c.adaptive) cfgName += `Adaptive (final k=${res.finalK})`;
  else if (c.k === 0) cfgName += 'Baseline (k=0)';
  else cfgName += `${c.model === 'oracle' ? 'Oracle' : 'Markov'} Top-${c.k}`;

  if (c.threshold > 0) cfgName += ` T=${c.threshold.toFixed(2)}`;
  if (c.insertion === 'lru') cfgName += ' (LRU-end)';

  state.comparisonHistory.unshift({
    name: cfgName,
    capacity: c.capacity,
    faults: res.pageFaults,
    prefetches: res.totalPrefetches,
    precision: res.precision,
    waste: res.waste,
    time: `${(res.elapsedMs / 1000).toFixed(2)}s`
  });

  if (state.comparisonHistory.length > 10) {
    state.comparisonHistory.pop();
  }

  renderComparisonTable();
}

function renderComparisonTable() {
  const tbody = document.getElementById('comparison-table-body');
  if (!tbody) return;

  if (state.comparisonHistory.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--text-muted);">No runs recorded yet.</td></tr>';
    return;
  }

  tbody.innerHTML = state.comparisonHistory.map(row => {
    // Work out the reduction now, so a baseline run later fills in earlier rows
    const baseFaults = getBaselineFaults(row.capacity);
    const reduction = (baseFaults !== null && baseFaults > 0)
      ? ((baseFaults - row.faults) / baseFaults) * 100
      : null;
    const hasRed = reduction !== null;
    const redCls = !hasRed ? 'baseline' : (reduction > 0 ? 'prefetch' : (reduction < 0 ? 'harm' : 'baseline'));
    const sign = hasRed && reduction > 0 ? '+' : '';
    const redText = hasRed ? `${sign}${reduction.toFixed(2)}%` : 'baseline not run at this size';
    return `
      <tr>
        <td style="font-weight:600;">${row.name}</td>
        <td style="font-family:var(--font-mono);">${row.faults.toLocaleString('en-US')}</td>
        <td style="font-family:var(--font-mono); font-weight:700;" class="${redCls}">${redText}</td>
        <td style="font-family:var(--font-mono);">${row.prefetches.toLocaleString('en-US')}</td>
        <td style="font-family:var(--font-mono);">${row.precision.toFixed(1)}%</td>
        <td style="font-family:var(--font-mono);">${row.waste.toFixed(1)}%</td>
        <td style="font-family:var(--font-mono); font-size:0.85rem;">${row.time}</td>
      </tr>
    `;
  }).join('');
}

function clearComparisonHistory() {
  state.comparisonHistory = [];
  renderComparisonTable();
}

// COA Effective Access Time (EAT) Calculator
function updateCOACalculator() {
  if (!state.currentRun) return;

  const memTimeNs = parseFloat(document.getElementById('eat-mem-time').value) || 100;
  const faultTimeMs = parseFloat(document.getElementById('eat-fault-time').value) || 8;
  const faultTimeNs = faultTimeMs * 1e6; // Convert ms to ns
  const prefetchPenaltyPct = parseFloat(document.getElementById('eat-prefetch-cost').value) || 0;

  const totalRefs = 3780309;

  // Baseline EAT at the same frame count
  const cap = state.currentRun.config.capacity;
  const baseFaults = getBaselineFaults(cap);

  // Current Run EAT
  const fCurrent = state.currentRun.pageFaults / totalRefs;
  const prefetchCount = state.currentRun.totalPrefetches;
  const prefetchPenaltyNs = (prefetchPenaltyPct / 100) * (prefetchCount / totalRefs) * faultTimeNs;
  const eatCurrentNs = (1 - fCurrent) * memTimeNs + fCurrent * faultTimeNs + prefetchPenaltyNs;

  document.getElementById('eat-current-val').textContent = formatEAT(eatCurrentNs);

  const speedupElem = document.getElementById('eat-speedup-val');
  if (baseFaults === null) {
    document.getElementById('eat-base-val').textContent = '-';
    speedupElem.textContent = '-';
    speedupElem.className = 'stat-value baseline';
    return;
  }

  const fBase = baseFaults / totalRefs;
  const eatBaseNs = (1 - fBase) * memTimeNs + fBase * faultTimeNs;
  const speedup = eatBaseNs / eatCurrentNs;

  document.getElementById('eat-base-val').textContent = formatEAT(eatBaseNs);
  speedupElem.textContent = `${speedup.toFixed(2)}x`;
  speedupElem.className = `stat-value ${speedup >= 1.0 ? 'prefetch' : 'harm'}`;
}

function formatEAT(ns) {
  if (ns >= 1e6) {
    return `${(ns / 1e6).toFixed(3)} ms`;
  } else if (ns >= 1e3) {
    return `${(ns / 1e3).toFixed(2)} µs`;
  }
  return `${ns.toFixed(1)} ns`;
}

// TAB 4: EXPERIMENTS EXPLORER
function initExperimentsTab() {
  if (!state.experimentsData) return;

  const listContainer = document.getElementById('exp-nav-list');
  const exps = state.experimentsData.experiments;

  listContainer.innerHTML = Object.keys(exps).map(expId => {
    const e = exps[expId];
    return `
      <div class="exp-nav-item ${expId === state.selectedExpId ? 'active' : ''}" data-exp="${expId}">
        <span class="exp-nav-id">${e.id}</span>
        <span class="exp-nav-title">${e.title}</span>
        <span class="tag-badge">${e.trace}</span>
      </div>
    `;
  }).join('');

  listContainer.querySelectorAll('.exp-nav-item').forEach(item => {
    item.addEventListener('click', () => {
      listContainer.querySelectorAll('.exp-nav-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      state.selectedExpId = item.dataset.exp;
      renderSelectedExperiment();
    });
  });

  renderSelectedExperiment();
}

function renderSelectedExperiment() {
  if (!state.experimentsData) return;
  const e = state.experimentsData.experiments[state.selectedExpId];
  if (!e) return;

  document.getElementById('exp-detail-title').textContent = `${e.id}: ${e.title}`;
  document.getElementById('exp-trace-tag').textContent = e.trace;
  document.getElementById('exp-tested-text').textContent = e.what_tested;
  document.getElementById('exp-found-text').textContent = e.what_found;

  const runLiveBtn = document.getElementById('exp-run-live-btn');
  if (e.runnable && e.preset) {
    runLiveBtn.style.display = 'inline-flex';
    runLiveBtn.onclick = () => {
      runPresetByName(`preset-${e.preset}`);
    };
  } else {
    runLiveBtn.style.display = 'none';
  }

  // Render Table
  renderExperimentTable(e);

  // Render Bar Chart
  renderExperimentChart(e.id);
}

function renderExperimentTable(e) {
  const tableContainer = document.getElementById('exp-table-container');
  if (!e.table || e.table.length === 0) {
    tableContainer.innerHTML = '';
    return;
  }

  const cols = Object.keys(e.table[0]);
  let html = '<table class="data-table"><thead><tr>';
  cols.forEach(col => {
    const label = col.replace(/_/g, ' ').toUpperCase();
    html += `<th>${label}</th>`;
  });
  html += '</tr></thead><tbody>';

  e.table.forEach(row => {
    html += '<tr>';
    cols.forEach(col => {
      let val = row[col];
      let style = '';
      if (typeof val === 'number') {
        val = val.toLocaleString('en-US');
        style = 'font-family:var(--font-mono);';
      } else if (typeof val === 'string' && (val.startsWith('+') || val.startsWith('-'))) {
        style = `font-family:var(--font-mono); font-weight:700; color:${val.startsWith('+') ? 'var(--color-prefetch)' : 'var(--color-harm)'};`;
      }
      html += `<td style="${style}">${val}</td>`;
    });
    html += '</tr>';
  });

  html += '</tbody></table>';
  tableContainer.innerHTML = html;
}

function renderExperimentChart(expId) {
  const canvas = document.getElementById('exp-chart-canvas');
  if (!canvas || !state.experimentsData) return;

  const e = state.experimentsData.experiments[expId];
  if (!e || !e.table) return;

  // Extract chart items based on experiment type
  const items = [];
  const shortName = (s) => s.split(' (')[0];
  const pushPair = (label1, val1, label2, val2, extra2) => {
    items.push({
      label: label1,
      value: val1,
      displayValue: val1.toLocaleString('en-US'),
      type: 'baseline'
    });
    items.push({
      label: label2,
      value: val2,
      displayValue: extra2 ? `${val2.toLocaleString('en-US')} (${extra2})` : val2.toLocaleString('en-US'),
      type: 'normal',
      isHarmful: val2 > val1
    });
  };

  e.table.forEach(row => {
    if (row.faults !== undefined) {
      const label = row.k || row.config || row.policy || row.model || row.threshold || 'Config';
      items.push({
        label: label.toString(),
        value: row.faults,
        displayValue: `${row.faults.toLocaleString('en-US')} faults`,
        type: label.toString().toLowerCase().includes('base') ? 'baseline' : 'normal'
      });
    } else if (row.mru_faults !== undefined) {
      items.push({
        label: `${row.capacity} (MRU)`,
        value: row.mru_faults,
        displayValue: `${row.mru_faults.toLocaleString('en-US')} (${row.mru_red})`,
        isHarmful: row.mru_red.startsWith('-')
      });
      items.push({
        label: `${row.capacity} (LRU-end)`,
        value: row.lru_faults,
        displayValue: `${row.lru_faults.toLocaleString('en-US')} (${row.lru_red})`,
        isHarmful: row.lru_red.startsWith('-')
      });
    } else if (row.prefetch !== undefined && row.baseline !== undefined && row.capacity !== undefined) {
      const cap = shortName(row.capacity);
      pushPair(`${cap} Baseline`, row.baseline, `${cap} Top-3`, row.prefetch, row.reduction);
    } else if (row.adaptive_faults !== undefined) {
      const cap = shortName(row.capacity);
      pushPair(`${cap} Baseline`, row.baseline, `${cap} Adaptive`, row.adaptive_faults, row.reduction);
    } else if (row.arc_faults !== undefined) {
      const cap = shortName(row.capacity);
      pushPair(`${cap} LRU`, row.lru_faults, `${cap} ARC`, row.arc_faults, row.difference);
    } else if (row.page_size !== undefined && row.prefetch !== undefined) {
      pushPair(`${row.page_size} pages Baseline`, row.baseline, `${row.page_size} pages Top-3`, row.prefetch, row.reduction);
    } else if (row.metric !== undefined && row.top3 !== undefined) {
      const metric = shortName(row.metric);
      pushPair(`${metric} Baseline`, row.baseline, `${metric} Top-3`, row.top3);
    }
  });

  const baselineIndices = [];
  items.forEach((it, idx) => {
    if (it.type === 'baseline') baselineIndices.push(idx);
  });
  if (baselineIndices.length === 1) {
    const baseIdx = baselineIndices[0];
    const baseVal = items[baseIdx].value;
    for (let i = baseIdx + 1; i < items.length; i++) {
      if (items[i].type === 'normal' && items[i].value > baseVal) {
        items[i].isHarmful = true;
      }
    }
  }

  if (canvas.parentElement) {
    canvas.parentElement.style.height = `${Math.max(220, 40 + items.length * 36)}px`;
  }

  ChartRenderer.renderBarChart(canvas, items, { isDark: state.theme === 'dark' });
}

// Window initialization
window.addEventListener('DOMContentLoaded', () => {
  initTheme();
  document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

  initNavigation();
  initWalkthrough();
  initLiveSimulator();
  loadExperimentsData();
});

