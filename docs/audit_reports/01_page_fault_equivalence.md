# Audit Report 01: Page Fault Equivalence Investigation

> **Path note (project reorganized on 2026-11-15):** file names in this document use the original flat layout. Current locations: data files in `data/pages/`, `data/traces/`, `data/models/`; scripts in `src/pipeline/`, `src/experiments/`, `tools/`, `tools/audit_scratch/`, `tools/verify_prefetch_count/`. Numbers and results are unchanged.

**Audit ID:** AUDIT-01  
**Subject:** Top-3 Prefetch Fault Count Invariance (57,512 faults) Across Trace Generations  
**Date:** October 29, 2026  

---

## 1. Why This Audit Was Needed

When the memory trace generator was recompiled with OpenMP thread tagging (`T%d`), the reported baseline LRU page fault count at RAM = 1,024 frames changed from 67,696 to 66,979 faults. However, the 1st-order Markov Top-3 prefetch fault count was reported as exactly 57,512 faults in both runs. This raised immediate suspicion that the prefetch simulator might have silently reused the old test trace, loaded an un-retrained model, or contained a hardcoded result.

---

## 2. Question Asked

Why did baseline LRU page faults shift by 717 faults (67,696 $\to$ 66,979) between Experiments 0–8 (Trace A) and Experiments 9–11 (Trace B), while the Global Markov Top-3 prefetching fault count remained identical at exactly 57,512 faults?

---

## 3. Method

The investigation was conducted using read-only analysis and scratch scripts:
- **File Metadata & Path Audit:** [audit_scratch/scan_scripts.py](../../tools/audit_scratch/scan_scripts.py) and [audit_scratch/check_files.py](../../tools/audit_scratch/check_files.py) scanned all scripts for trace paths, model inputs, modification timestamps, and byte sizes.
- **Trace Diffing:** [audit_scratch/compare_traces.py](../../tools/audit_scratch/compare_traces.py) parsed `traces/testing_trace.txt` (`address // 4096`) and compared all 3,780,309 reference positions against `cleaned_testing_pages.txt`.
- **Cross-Evaluation Matrix:** [audit_scratch/run_matrix.py](../../tools/audit_scratch/run_matrix.py) evaluated both test sequences against both models under identical LRU logic.
- **Fault Event Index Tracing:** [audit_scratch/compare_fault_events.py](../../tools/audit_scratch/compare_fault_events.py) tracked the exact step indices at which each page fault occurred in both simulations.
- **Capacity Scaling on Trace B:** [audit_scratch/test_capacities_new.py](../../tools/audit_scratch/test_capacities_new.py) evaluated baseline and Top-1/2/3 prefetching across capacities 512, 1,024, and 2,048 frames.

---

## 4. Findings

### 4.1 Trace File Properties & Addressing Discrepancy
- **Trace A (`cleaned_testing_pages.txt`):** Modified `2026-10-28 10:51:08` (36,568,213 bytes, 3,780,309 lines). Virtual page addresses sit in the `11,421,696` range (pointers allocated around `0xae4...`).
- **Trace B (`traces/testing_trace.txt`):** Modified `2026-10-28 15:16:29` (175,561,072 bytes, 3,780,309 lines). Virtual page addresses sit in the `518,950,771` range (pointers allocated around `0x000001eee...`).
- **Raw Position Comparison:** All 3,780,309 positions differ numerically (100% differ) due to 64-bit OS heap base address shifts between runs.
- **Canonical Token Comparison:** Converting pages to unique arrival IDs revealed differences at 3,766,892 of 3,780,309 positions (99.64%) due to dynamic OpenMP task work-stealing scheduling jitter.

### 4.2 Cross-Simulation Matrix (Capacity = 1,024 frames)
Verified output produced by [audit_scratch/run_matrix.py](../../tools/audit_scratch/run_matrix.py):

| Test Sequence | Model Applied | Baseline LRU Faults | Top-3 Prefetch Faults |
| :--- | :--- | :---: | :---: |
| **Trace A** (`cleaned_testing_pages.txt`) | Model A (trained on `cleaned_training_pages.txt`) | **67,696** | **57,512** |
| **Trace A** (`cleaned_testing_pages.txt`) | Model B (trained on `traces/training_trace.txt`) | **67,696** | **67,696** (0 hits) |
| **Trace B** (`traces/testing_trace.txt`) | Model A (trained on `cleaned_training_pages.txt`) | **66,979** | **66,979** (0 hits) |
| **Trace B** (`traces/testing_trace.txt`) | Model B (trained on `traces/training_trace.txt`) | **66,979** | **57,512** |

### 4.3 Fault Event Trajectory Verification
Verified output produced by [audit_scratch/compare_fault_events.py](../../tools/audit_scratch/compare_fault_events.py):
- Total faults in Trace A Top-3 simulation: 57,512
- Total faults in Trace B Top-3 simulation: 57,512
- **Identical Fault Step Indices:** Exactly **1,104 / 57,512 (1.92%)** coincide. Over **98% of the page faults occur at completely different access steps** in the two traces.

### 4.4 Parameter Scaling on Trace B
Verified output produced by [audit_scratch/test_capacities_new.py](../../tools/audit_scratch/test_capacities_new.py) on `traces/testing_trace.txt`:
- **512 frames:** Baseline = 218,752 \| Top-1 = 212,732 \| Top-2 = 208,347 \| **Top-3 = 233,826**
- **1,024 frames:** Baseline = 66,979 \| Top-1 = 67,361 \| Top-2 = 63,200 \| **Top-3 = 57,512**
- **2,048 frames:** Baseline = 2,025 \| Top-1 = 1,932 \| Top-2 = 1,339 \| **Top-3 = 917**

*(Comparison with Trace A targets: at 512 frames, Trace A Top-3 was 237,684 vs. Trace B 233,826; at 2,048 frames, Trace A Top-3 was 935 vs. Trace B 917. Only at nominal capacity 1,024 frames and $k=3$ do the fault totals intersect at 57,512).*

---

## 5. Conclusion

The identical fault count of 57,512 is **(d) a genuine numerical coincidence** arising from two independent simulations on statistically near-identical BFS executions:
1. `exp9_per_thread_markov.py` did not cache or hardcode numbers; it genuinely retrained on `traces/training_trace.txt` and simulated on `traces/testing_trace.txt`.
2. Both workloads represent the identical BFS algorithm executing over SNAP `Amazon0302.txt` (3,780,309 accesses across 2,025 unique 4 KB pages).
3. The minor baseline shift (67,696 to 66,979) was driven by OpenMP dynamic task-stealing order and heap array base alignment; Top-3 prefetching smoothed these scheduling variances and landed on the exact same aggregate total.

---

## 6. Effect on the Research Paper

- **Methodological Legitimacy:** There is no fraud, caching artifact, or code leakage in Experiment 9. Both 57,512 figures are authentic results of their respective trace files.
- **Reporting Strategy:**
  - When presenting Experiments 0–8 (Trace A), report Baseline = 67,696 and Top-3 = 57,512 (+15.04% reduction).
  - When presenting Experiments 9–11 (Trace B), report Baseline = 66,979, Global Top-3 = 57,512 (+14.13% reduction), and Per-Thread Top-3 = 58,650 (+12.44% reduction).
  - Clearly disclose in the paper's experimental setup that regenerating traces with thread tags altered runtime task interleaving and baseline faults, but preserved the ~14–15% prefetching gain.

---

## 7. Corrections

- In the initial preliminary discussion, it was hypothesized that `exp9_per_thread_markov.py` might have silently fallen back to reading `cleaned_testing_pages.txt`. Inspection of [exp9_per_thread_markov.py L56–75](../../src/experiments/exp9_per_thread_markov.py#L56-L75) refuted this: `find_trace_files()` directly ingested `traces/testing_trace.txt`.
- Furthermore, the cross-evaluation matrix proved that if Experiment 9 had loaded the old trace or model, prefetching would have produced zero hits (66,979 faults) due to disjoint virtual address spaces.

