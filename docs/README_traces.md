# Trace & Model Provenance Guide

This document defines the dual-trace architecture of this repository, explains the divergence between early and late experiments, and provides guidance for consistent model loading.

---

## 1. Trace Overview

The repository contains two distinct generations of memory traces generated from parallel BFS on the SNAP Amazon co-purchasing network dataset (`Amazon0302.txt`, 262,111 vertices, 1,234,877 directed edges):

| Feature | Trace A (Original) | Trace B (Thread-Tagged) |
| :--- | :--- | :--- |
| **Raw Traces** | Generated 2026-10-28 ~10:00 without thread tags (`%s %p %s[%llu]`) | Generated 2026-10-28 15:16 with OpenMP thread tags (`T%d %s %p %s[%llu]`) |
| **Files on Disk** | `data/pages/cleaned_training_pages.txt` (34.87 MB)<br>`data/pages/cleaned_testing_pages.txt` (34.87 MB) | `data/traces/training_trace.txt` (167.46 MB)<br>`data/traces/testing_trace.txt` (167.43 MB) |
| **BFS Roots** | Training: Root **0** \| Testing: Root **1** | Training: Root **0** \| Testing: Root **1** |
| **Total Accesses** | 3,780,309 references | 3,780,309 references |
| **Unique 4 KB Pages** | 2,025 unique pages | 2,025 unique pages |
| **Virtual Address Space** | Allocations placed around `0xae4...` (virtual page numbers ~`11,421,696`) | Allocations placed around `0x000001eee...` (virtual page numbers ~`518,950,771`) |
| **Used by Experiments** | **Phase 3 Simulator & Experiments 1–8** | **Experiments 9–11** |

---

## 2. Models & Provenance

> [!WARNING]
> **Stale File Warning (`markov_model.json`):**
> During the execution of Experiment 9 at 15:34:41, `src/experiments/exp9_per_thread_markov.py` overwrote `data/models/markov_model.json` with a global model retrained on **Trace B** (`data/traces/training_trace.txt`).
> Because Trace A (`data/pages/cleaned_testing_pages.txt`) and Trace B have non-overlapping virtual address spaces, loading `data/models/markov_model.json` against `data/pages/cleaned_testing_pages.txt` yields **0 prefetch hits** (67,696 faults).

To preserve reproducibility, models are archived under explicit provenance names:

### Trace A Models (Use with `data/pages/cleaned_testing_pages.txt`)
- **`data/models/markov_model_traceA.json`**: Retrained directly from `data/pages/cleaned_training_pages.txt` using `src/pipeline/phase2_train_model.py` logic (top-3 predictions, `indent=2`, 173,325 bytes, 2,025 unique states). Reproduces 57,512 Top-3 faults (+15.04% reduction).
- **`data/models/markov_model_top5_traceA.json`**: Copy of `data/models/markov_model_top5.json` (top-5 predictions, 257,329 bytes, 2,025 unique states). Used by Experiment 1.
- **`data/models/markov_model_order2.json`**: 2nd-order Markov model for Trace A (25.74 MB). Used by Experiment 2.
- **`data/models/markov_model_order2_top5.json`**: 2nd-order Top-5 Markov model for Trace A (28.55 MB). Used by Experiment 2 cross-domain.
- **`data/models/graph_oracle.json`**: Graph adjacency oracle for Trace A (125.94 KB). Used by Experiment 8.

### Trace B Models (Use with `data/traces/testing_trace.txt`)
- **`data/models/markov_model_traceB.json`**: Dedicated copy of the Trace B global top-3 model (97,167 bytes, compact JSON, 2,025 unique states). Reproduces 57,512 Top-3 faults (+14.13% reduction vs baseline 66,979).
- **`data/models/markov_model_per_thread_traceB.json`**: Dedicated copy of the Trace B per-thread isolated model (2.03 MB, 44,398 states across 22 threads). Reproduces 58,650 Per-Thread Top-3 faults (+12.44% reduction).

---

## 3. Verified Benchmark Results

### Trace A Baseline & Prefetching (RAM = 1,024 pages, 4 KB pages)
- **Baseline Demand Paging:** 67,696 faults (1.791% fault ratio)
- **Top-1 Prefetch:** 67,634 faults (+0.09% reduction)
- **Top-2 Prefetch:** 63,132 faults (+6.74% reduction)
- **Top-3 Prefetch:** 57,512 faults (+15.04% reduction)
- **Top-5 Prefetch:** 63,041 faults (+6.88% reduction)

### Trace B Multi-Threaded Results (RAM = 1,024 pages, 4 KB pages)
- **Baseline Demand Paging:** 66,979 faults (1.772% fault ratio)
- **Global Top-3 Prefetch:** 57,512 faults (+14.13% reduction)
- **Per-Thread Top-3 Prefetch:** 58,650 faults (+12.44% reduction)

---

## 4. Script-to-Model Configuration Mapping

All experiment scripts have been updated to explicitly point to their verified, corresponding model files:

### Scripts Configured for Trace A (`data/models/markov_model_traceA.json`)
- `src/pipeline/phase3_simulator.py`: Phase 3 baseline vs. Markov Top-3 prefetcher
- `src/experiments/exp1_simulator_top1_2.py`: Experiment 1 prefetch degree sensitivity (Top-1, Top-2, Top-3)
- `src/experiments/exp1_simulator_top5.py`: Experiment 1 prefetch degree comparison (Top-3 vs. Top-5)
- `src/experiments/exp2_simulator_order2.py`: Experiment 2 1st-order vs. 2nd-order comparison (1st-order uses `data/models/markov_model_traceA.json`)
- `src/experiments/exp3_ram_capacity.py`: Experiment 3 physical RAM capacity sensitivity (512, 1,024, 2,048 frames)
- `src/experiments/exp5_prefetch_aware_lru.py`: Experiment 5 prefetch-aware LRU insertion evaluation
- `src/experiments/exp6_adaptive_topk.py`: Experiment 6 closed-loop adaptive Top-K prefetching controller
- `src/experiments/exp8_graph_aware.py`: Experiment 8 graph-structure-aware prefetching (Markov Top-3 vs. Graph Oracle)

### Scripts Configured for Trace B (`data/models/markov_model_traceB.json` & `data/models/markov_model_per_thread_traceB.json`)
- `src/experiments/exp9_per_thread_markov.py`: Experiment 9 OpenMP multi-threaded per-thread vs. global modeling (writes to `data/models/markov_model_traceB.json` and `data/models/markov_model_per_thread_traceB.json`)
- `src/experiments/exp11_writeback_cost.py`: Experiment 11 dirty-aware replacement and write-back cost evaluation (loads `data/models/markov_model_traceB.json`)

*(Note: `src/experiments/exp4_confidence_threshold.py` trains on-the-fly from `data/pages/cleaned_training_pages.txt`, `src/experiments/exp7_arc_baseline.py` evaluates ARC vs. LRU demand paging without prefetching models, and `src/experiments/exp10_page_size.py` dynamically trains models on-the-fly per page size from `data/traces/training_trace.txt`).*


