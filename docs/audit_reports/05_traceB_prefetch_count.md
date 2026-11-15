# Audit Report 05: Trace B Prefetch Count Verification & Table II Reconciliation

> **Path note (project reorganized on 2026-11-15):** file names in this document use the original flat layout. Current locations: data files in `data/pages/`, `data/traces/`, `data/models/`; scripts in `src/pipeline/`, `src/experiments/`, `tools/`, `tools/audit_scratch/`, `tools/verify_prefetch_count/`. Numbers and results are unchanged.

**Project:** Operating System Page-Replacement & Markov-Prefetching Simulation  
**Audit Date:** October 29, 2026  
**Auditor:** Automated Diagnostic Assistant (Antigravity)  
**Status:** Verification Complete — Exact Figures Confirmed  

---

## 1. Context & Purpose

The research paper draft states:
> *"On Trace B about 57,000 speculative pages are loaded to avoid 9,467 faults."*

This audit was conducted to:
1. Empirically measure the exact number of speculative pages loaded ($N_{\text{pref}}$), hits ($N_{\text{used}}$), and waste ($N_{\text{unused}}$) on **Trace B** under standard experimental conditions (Global 1st-order Markov Top-3, $k=3$, $T=0$, 1,024 physical frames of 4 KB, standard MRU insertion).
2. Validate the counting methodology against the published **Table II** results on **Trace A** (56,721 prefetches, 59.13% precision, 40.81% waste).
3. Sanity-check the simulation against all known benchmark metrics for Trace B.
4. Determine whether the paper's statement of "about 57,000" is supported by exact experimental measurement.

---

## 2. Investigated Files and Script Locations

### Experiment Scripts
- **Experiment 9 (Per-Thread Markov):** `exp9_per_thread_markov.py`
- **Experiment 10 (Page-Size Sweeps):** `exp10_page_size.py`
- **Experiment 11 (Write-Back / Dirty Cost):** `exp11_writeback_cost.py`
- **Reference Table II Implementation:** `exp4_confidence_threshold.py`

### Trace B Files
- **Training Trace (OpenMP Thread-Tagged):** `traces/training_trace.txt` (175,593,745 bytes)
- **Testing Trace (OpenMP Thread-Tagged):** `traces/testing_trace.txt` (175,561,072 bytes)

### Model Files
- **Trace B Global Model:** `markov_model_traceB.json` (97,167 bytes, 2,025 states)
- **Trace B Per-Thread Model:** `markov_model_per_thread_traceB.json` (2,129,279 bytes, 44,398 states across 22 threads)
- **Trace A Reference Model:** `markov_model_traceA.json` (173,325 bytes, 2,025 states)

---

## 3. Simulator Prefetch Functions and Counting Logic

### Existing Scripts Analysis
1. **`exp9_per_thread_markov.py` (lines 47–51):**
   ```python
   def prefetch(self, pages: list):
       """Prefetches a list of predicted pages into the physical cache."""
       for p in pages:
           self.put(p)
   ```
   *Does not track speculative prefetch counts.*

2. **`exp11_writeback_cost.py` (lines 43–60):**
   ```python
   def prefetch(self, pages: list):
       for p in pages:
           if p in self.cache:
               self.cache.move_to_end(p)
           else:
               if len(self.cache) >= self.capacity:
                   _, is_dirty = self.cache.popitem(last=False)
                   if is_dirty:
                       self.dirty_evictions += 1
                   else:
                       self.clean_evictions += 1
               self.cache[p] = False
   ```
   *Tracks clean and dirty frame evictions, but does not isolate prefetch hits or waste.*

3. **`exp4_confidence_threshold.py` (lines 13–69):**
   This script provided the exact counting and instrumentation standard used for Table II in the paper:
   ```python
   def access(self, page: int) -> bool:
       if page in self.cache:
           self.cache.move_to_end(page)
           if page in self.prefetched_pages:
               self.prefetch_hits += 1
               self.prefetched_pages.remove(page)
           return True
       self.put(page)
       return False

   def prefetch(self, pages: list):
       for p in pages:
           if p in self.cache:
               self.cache.move_to_end(p)
           else:
               self.total_prefetches += 1
               self.cache[p] = True
               self.prefetched_pages.add(p)
               if len(self.cache) > self.capacity:
                   evicted, _ = self.cache.popitem(last=False)
                   if evicted in self.prefetched_pages:
                       self.prefetch_waste += 1
                       self.prefetched_pages.remove(evicted)
   ```

### Check of Stored Result Logs
A search across all project files confirmed that no CSV, JSON, or text log from Experiments 9–11 previously recorded `N_pref` or prefetch waste for Trace B (only page faults, hit rates, and dirty evictions were logged). The figure in the paper draft was derived from interactive simulator runs.

---

## 4. Sanity Check Against Known Benchmark Values

Using a dedicated verification script (`verify_prefetch_count/measure_prefetch.py`), Trace B was simulated under 1,024 frames of 4 KB. All benchmark metrics matched with 100% exact integer precision:

| Benchmark Metric | Expected / Known Value | Measured Value | Status |
| :--- | :---: | :---: | :---: |
| **Trace B LRU Baseline Faults** | 66,979 | 66,979 | **EXACT MATCH** |
| **Trace B Global Top-3 Faults** | 57,512 | 57,512 | **EXACT MATCH** |
| **Trace B Dirty Evictions (LRU)** | 1,871 | 1,871 | **EXACT MATCH** |
| **Trace B Dirty Evictions (Top-3)** | 2,620 | 2,620 | **EXACT MATCH** |
| **Trace B Total Evictions (LRU)** | 65,955 | 65,955 | **EXACT MATCH** |
| **Trace B Total Evictions (Top-3)** | 113,643 | 113,643 | **EXACT MATCH** |
| **Trace B Hit Rate (LRU)** | 98.228% | 98.228% | **EXACT MATCH** |
| **Trace B Hit Rate (Top-3)** | 98.479% | 98.479% | **EXACT MATCH** |

---

## 5. Trace A Reference Calibration (Table II Verification)

To confirm that prefetch metrics are counted identically to the paper, the counting logic was first run on Trace A (`cleaned_testing_pages.txt` with `markov_model_traceA.json`, $k=3$, $T=0$, 1,024 frames):

- **$N_{\text{pref}}$:** **56,721** (Matches paper Table II exactly)
- **Precision:** **59.13%** ($N_{\text{used}} = 33,540$)
- **Waste:** **40.81%** ($N_{\text{unused}} = 23,149$)
- **Demand Faults:** **57,512** (Baseline: 67,696; Faults avoided: 10,184)

This confirms exact alignment with the paper's counting methodology.

---

## 6. Complete Verification Results: Trace A vs. Trace B

**Simulation Parameters:** Global 1st-order Markov Top-3 ($k=3$), Confidence Threshold $T=0$, 1,024 physical frames (4.0 MB, 4 KB pages), standard MRU insertion.

| Metric | Trace A (Experiments 1–8) | Trace B (Experiments 9–11) | Notes / Derivation |
| :--- | :---: | :---: | :--- |
| **Total Memory References** | 3,780,309 | 3,780,309 | Full testing sequence |
| **Demand Faults (Baseline LRU)** | 67,696 | 66,979 | Demand miss count without prefetcher |
| **Demand Faults (Top-3 Markov)** | 57,512 | 57,512 | Demand miss count with prefetcher |
| **Faults Avoided** | **10,184** | **9,467** | $\text{Baseline} - \text{Top-3}$ ($66,979 - 57,512 = 9,467$) |
| **$N_{\text{pref}}$ (Speculative Pages Loaded)** | **56,721** | **57,155** | Candidates **not** already resident in cache |
| **$N_{\text{used}}$ (Prefetch Hits / Useful)** | 33,540 | 33,397 | Touched by demand reference before eviction |
| **$N_{\text{unused}}$ (Prefetch Waste)** | 23,149 | 23,714 | Evicted before any demand reference |
| **Residual Resident at EOF** | 32 | 44 | $N_{\text{pref}} - N_{\text{used}} - N_{\text{unused}}$ |
| **Precision** ($\frac{N_{\text{used}}}{N_{\text{pref}}}$) | **59.13%** | **58.43%** | Useful prefetches / total prefetches loaded |
| **Waste** ($\frac{N_{\text{unused}}}{N_{\text{pref}}}$) | **40.81%** | **41.49%** | Evicted prefetches / total prefetches loaded |
| **Candidates Skipped (Already Resident)** | 115,815 | 114,913 | Redundant loads avoided |
| **Total Candidates Proposed** | 172,536 | 172,068 | $N_{\text{pref}} + N_{\text{skipped}}$ ($\le 3 \times \text{faults}$) |

---

## 7. Assessment of the Paper's Claim

> **Finding:**  
> The statement in the paper — *"On Trace B about 57,000 speculative pages are loaded to avoid 9,467 faults"* — is **empirically supported and accurate**.  
> The exact measured number of speculative pages loaded ($N_{\text{pref}}$) is **57,155**.
> 
> - Difference vs. 57,000: **+155 pages** (a relative discrepancy of only **+0.27%**).
> - Faults avoided: Exactly **9,467** ($66,979 - 57,512$).

---

## 8. Counting Definitions & Ambiguities Resolved

1. **Definition of $N_{\text{pref}}$:**  
   $N_{\text{pref}}$ strictly represents **speculative pages fetched from disk into RAM**. Proposed candidates that were already present in the cache (114,913 occurrences on Trace B) had their LRU positions updated to MRU, but were **not** counted as prefetch loads. If all candidate proposals had been counted regardless of cache residency, the figure would be 172,068. Thus, $N_{\text{pref}} = 57,155$ is the unambiguous metric for physical I/O load.
   
2. **Precision and Waste Denominators:**  
   In alignment with [`exp4_confidence_threshold.py`](../../src/experiments/exp4_confidence_threshold.py), Precision and Waste use $N_{\text{pref}}$ as the denominator:
   $$\text{Precision} = \frac{N_{\text{used}}}{N_{\text{pref}}} = \frac{33,397}{57,155} = 58.43\%$$
   $$\text{Waste} = \frac{N_{\text{unused}}}{N_{\text{pref}}} = \frac{23,714}{57,155} = 41.49\%$$
   A tiny fraction of prefetched pages (44 pages = 0.08%) remained resident in the cache at the end of the simulation without having been referenced or evicted, causing $\text{Precision} + \text{Waste} = 99.92\%$.

