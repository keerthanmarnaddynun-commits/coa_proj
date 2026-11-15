# Pollution-Aware Markov Page Prefetching for Irregular Graph Workloads
## Interactive Web UI for Computer Organization & Architecture (COA) Class Presentation

An interactive, projector-optimized web demonstration and simulation tool for evaluating hardware/OS page replacement policies and speculative Markov prefetching on parallel Breadth-First Search (BFS) graph workloads (SNAP Amazon0302 co-purchasing network).

---

### Key Ground Rules & Integrity
1. **Zero Invented Numbers:** All values displayed are produced either by live simulation in the UI over the authentic 3,780,309 memory references of Trace A, or sourced directly from verified empirical experiments.
2. **Offline & Self-Contained:** Built with plain HTML5, CSS3, and modern vanilla JavaScript. No external frameworks, zero build steps, zero npm dependencies, and no CDN dependencies.
3. **High Performance:** An $O(1)$ doubly-linked list LRU cache implemented via typed arrays (`Uint8Array`, `Int16Array`) executes the full 3.78M-reference trace in ~0.1 seconds in a background Web Worker.
4. **Safety:** No existing project repository files were moved, modified, or deleted.

---

## How to Run the UI

### Method 1: One-Click Batch Script (Windows)
Double-click `ui/run_ui.bat` (or run it from PowerShell/CMD):
```cmd
cd ui
run_ui.bat
```
This launches a local Python HTTP server on port 8000 (sending Cache-Control: no-store headers) and automatically opens `http://localhost:8000` in your default web browser.

### Method 2: Manual Terminal Command
```bash
cd ui
python -c "import http.server as h; h.SimpleHTTPRequestHandler.end_headers=lambda s:(s.send_header('Cache-Control','no-store'),h.BaseHTTPRequestHandler.end_headers(s)); h.test(HandlerClass=h.SimpleHTTPRequestHandler,port=8000,bind='127.0.0.1')"
```
Then navigate to: `http://localhost:8000`

---

## How to Regenerate Data

The preprocessed data files in `ui/data/` (`trace_a.bin`, `markov_top5.json`, `graph_oracle.json`, `page_map.json`, `results.json`) can be regenerated at any time by running:
```bash
python ui/export_ui_data.py
```
This script operates in strict read-only mode on the repository's trace files (`data/pages/cleaned_testing_pages.txt`, `data/pages/cleaned_training_pages.txt`, `data/models/markov_model_top5_traceA.json`, `data/models/graph_oracle.json`) and compacts the 3.78M text lines into a little-endian `Uint16` binary stream (7.5 MB).

---

## Where the numbers come from
- The live simulator (Tab 3) computes fault counts itself from `data/trace_a.bin`. `tests/verify_sim.mjs` compares it with ground-truth values from the Python study.
- The Experiments tab (Tab 4) and the headline cards show results typed in by hand from the lab record. They are stored in `data/results.json`, which `export_ui_data.py` writes from values typed inside the script. They are not recomputed from the trace files.
- To change one of those numbers, edit it in `export_ui_data.py`, run the script, and make sure `data/results.json` is updated.

---

## Automated Verification Test Suites

To verify the mathematical and architectural accuracy of the simulation core against Python ground truth:

1. **Full Trace A Simulation Matrix (20 Test Configurations):**
   ```bash
   node ui/tests/verify_sim.mjs
   ```
   *Verifies:*
   - Baseline Demand LRU: 67,696 faults
   - Prefetch Degree $k \in \{1, 2, 3, 5\}$: 67,634, 63,132, 57,512, 63,041 faults
   - Confidence Thresholds $T \in \{0.05, 0.10, 0.20, 0.30, 0.50\}$: 55,816, 55,751, 59,431, 67,667, 67,683 faults
   - Constrained Capacity (512 frames): Baseline 221,603 / Top-3 Prefetch 237,684 (-7.26%)
   - Abundant Capacity (2,048 frames): Baseline 2,025 / Top-3 Prefetch 935 (+53.83%)
   - Prefetch-Aware LRU-End Insertion: 512 frames → 191,587 (+13.54%); 1,024 frames → 60,622 (+10.45%)
   - Adaptive Top-K Controller: 512 frames → 212,106 (159 adjs, final $k=2$); 1,024 frames → 57,609 (6 adjs, final $k=5$); 2,048 frames → 935 (0 adjs)
   - Graph Topological Oracle: 57,230 faults (+15.46%)

2. **Walkthrough Teaching Scenarios Test:**
   ```bash
   node ui/tests/verify_scenarios.mjs
   ```
   *Verifies:*
   - Scenario 1 ("Prefetching Helps"): 20 baseline faults cut to 7 faults with $k=2$.
   - Scenario 2 ("Pollution & Fixes"): 6 baseline faults doubles to 12 with naive MRU prefetching; rescued to 7 by LRU-end insertion and 6 by confidence filtering ($T=0.40$).

---

## Overview of the 5 Presentation Tabs

### Tab 1 — "The Problem" (Overview)
- **Computer Architecture Background:** Explains virtual memory page replacement and the 80,000x latency penalty of page faults (~8 ms disk I/O vs 100 ns RAM access).
- **The Pollution Hazard:** Details why speculative prefetching on irregular graph traversals risks displacing hot working set pages when physical memory headroom is constrained.
- **Architectural Pipeline:** Interactive diagram illustrating the flow from Application Threads → Page Fault Handler → 1st-Order Markov Table → Confidence Filter → Prefetch-Aware Insertion → Physical Frames, with the closed-loop Adaptive Controller feedback loop.
- **Headline Result Cards:** Highlights four primary findings across nominal (1,024 frames) and constrained (512 frames) regimes.

### Tab 2 — "Concept Walkthrough" (Teaching Simulator)
- **Side-by-Side 4-Frame Cache:** Runs standard Demand LRU (left) and Markov Prefetching (right) in lockstep over a reference tape of pages A–H.
- **Visualized Frame States:** Displays ordered physical frames from MRU to LRU with color-coded hits (green), faults (orange) and speculative prefetches (blue).
- **Interactive Controls:** Step, Back, Play/Pause, Reset, Speed Slider, Degree $k$, Insertion Position (MRU vs LRU-end), and Confidence Slider ($T \in [0, 0.5]$).
- **Two Built-in Scenarios:**
  - *Scenario 1 ("Prefetching Helps"):* Demonstrates speculative latency masking on graph frontier loops.
  - *Scenario 2 ("Pollution"):* Demonstrates how wrong speculative pages displace working sets, and shows how LRU-end insertion or confidence filtering neutralizes pollution.

### Tab 3 — "Live Simulator" (The Real Trace)
- **Full Trace Execution:** Executes the full 3,780,309 accesses of Trace A via an asynchronous Web Worker with live progress updates and cancellation support.
- **Presets & Controls:** One-click presets for all key paper configurations, adjustable frame capacities (256, 512, 1024, 2048, or custom), Markov vs Graph Oracle models, and closed-loop adaptive control.
- **Verified Badge:** A green "Verified Paper Match" badge dynamically confirms bit-for-bit equivalence when testing published configurations.
- **Timeline & History:** Overlaid chart tracking faults per 50,000 accesses alongside degree $k$ adaptations; comparison table tracking the last 10 runs.
- **COA EAT Calculator:** Computes Effective Access Time $EAT = (1 - f) \cdot t_{\text{mem}} + f \cdot t_{\text{fault}}$ and explores the impact of background prefetch bus overhead.

### Tab 4 — "Experiments" (E1 to E11)
- **Complete Empirical Record:** Left navigation bar and interactive detail panel covering all 11 experimental investigations.
- **Transparent Results:** Documents both positive results and negative results (2nd-order Markov, per-thread Markov, ARC). The causes of the negative results were not tested.
- **"Run Live in Simulator" Link:** Instantly jumps to Tab 3 and runs the selected experiment configuration live.

### Tab 5 — "Takeaways & Limits"
- **5 Core Takeaways:** Concisely summarizes the best degree tested, pollution dangers, three architectural fixes, negative result insights, and the comparison with a graph oracle.
- **Stated Limitations:** Transparently details single-workload graph scope, fully associative software cache model, offline threshold tuning, and trace set distinctions.
- **File & Script Index:** Documents repository files and their roles.

