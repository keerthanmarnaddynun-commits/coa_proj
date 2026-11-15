# Audit Report 03: Experiment 1 Reconciliation Audit

> **Path note (project reorganized on 2026-11-15):** file names in this document use the original flat layout. Current locations: data files in `data/pages/`, `data/traces/`, `data/models/`; scripts in `src/pipeline/`, `src/experiments/`, `tools/`, `tools/audit_scratch/`, `tools/verify_prefetch_count/`. Numbers and results are unchanged.

**Audit ID:** AUDIT-03  
**Subject:** Reconciliation of Top-1 / Top-2 Prefetch Fault Counts in Experiment 1  
**Date:** October 29, 2026  

---

## 1. Why This Audit Was Needed

During an earlier audit summary, page fault numbers of 67,645 (Top-1) and 63,331 (Top-2) were cited for Trace A at RAM = 1,024 frames. However, the original project log in `lab_record.md` recorded 67,634 (Top-1) and 63,132 (Top-2). This discrepancy created uncertainty about which set of numbers represents the true, verified execution of the Experiment 1 simulation.

---

## 2. Question Asked

Why did 67,645 and 63,331 appear in the audit text instead of the logged 67,634 and 63,132, and which numbers are the reproducible results to cite in the research paper?

---

## 3. Method

- **Exhaustive Codebase & Log Search:** [audit_scratch/search_all_numbers.py](../../tools/audit_scratch/search_all_numbers.py) scanned all repository scripts, markdown files, JSON models, and execution transcripts for both sets of numbers.
- **Trace A Model Reconstruction:** [audit_scratch/test_exp1_exact.py](../../tools/audit_scratch/test_exp1_exact.py) retrained the original top-3 Markov model from `cleaned_training_pages.txt` (producing `audit_scratch/markov_model_traceA_rebuild.json`, 173,325 bytes) and cross-verified it against `markov_model_top5.json`.
- **Exact Script Execution:** [audit_scratch/exp1_exact_repro.py](../../tools/audit_scratch/exp1_exact_repro.py) ran the exact logic of [exp1_simulator_top1_2.py](../../src/experiments/exp1_simulator_top1_2.py) on `cleaned_testing_pages.txt` across $k \in \{0, 1, 2, 3\}$.
- **Line-by-Line Logic Comparison:** Inspected candidate slicing, resident page promotion, MRU insertion order, and eviction sequence.

---

## 4. Findings

### 4.1 Search Results Across Repository
- **`67,634` and `63,132`:** Found in [lab_record.md L192, L195, L206, L207, L215, L216, L228, L229](../lab_record.md#L192).
- **`67,645` and `63,331`:** Found **nowhere** in any script, log, trace, or codebase file. They originated solely as an errant transcription in prose in the previous audit response.

### 4.2 Exact Reproduction of Experiment 1 Results
Verified output produced by [audit_scratch/exp1_exact_repro.py](../../tools/audit_scratch/exp1_exact_repro.py):

| Policy / Degree | Logged Faults in `lab_record.md` | Re-Run Faults (Exact Simulator) | Audit LRU Class Re-Run | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Baseline LRU ($k=0$)** | 67,696 | 67,696 | 67,696 | **MATCH (Exact)** |
| **Top-1 Prefetch ($k=1$)** | 67,634 | 67,634 | 67,634 | **MATCH (Exact)** |
| **Top-2 Prefetch ($k=2$)** | 63,132 | 63,132 | 63,132 | **MATCH (Exact)** |
| **Top-3 Prefetch ($k=3$)** | 57,512 | 57,512 | 57,512 | **MATCH (Exact)** |

### 4.3 Simulator Mechanics
1. **Candidate Slicing:** [exp1_simulator_top1_2.py L107](../../src/experiments/exp1_simulator_top1_2.py#L107) extracts `model[page][:prefetch_limit]`. Because candidates in the model dictionary are ordered strictly by frequency descending (via `Counter.most_common()`), slicing preserves the highest-probability transitions.
2. **Resident Promotion:** If a prefetched candidate is already resident in cache, [exp1_simulator_top1_2.py L32](../../src/experiments/exp1_simulator_top1_2.py#L32) calls `move_to_end()`, updating it to MRU without evicting another page.
3. **Insertion Priority:** The faulting demand page is placed at MRU first; prefetched pages are inserted immediately after, placing prefetched candidates at higher recency than the faulting page itself.

---

## 5. Conclusion

- **The numbers 67,645 and 63,331 are completely invalid:** They were never produced by any simulation script or trace file in this project.
- **The logged numbers in `lab_record.md` (67,634 and 63,132) are 100% genuine and reproducible:** Executing the original simulator logic reproduces them to the exact integer.

---

## 6. Effect on the Research Paper

- **Cite the Original Logged Numbers:**
  - **Baseline LRU:** 67,696 faults (1.791% fault ratio)
  - **Top-1 Prefetching:** 67,634 faults (+0.09% reduction, 62 faults saved)
  - **Top-2 Prefetching:** 63,132 faults (+6.74% reduction, 4,564 faults saved)
  - **Top-3 Prefetching:** 57,512 faults (+15.04% reduction, 10,184 faults saved)
  - **Top-5 Prefetching:** 63,041 faults (+6.88% reduction, 4,655 faults saved)
- **Analytical Takeaway:** Emphasize the steep inflection point between $k=1$ (+0.09%) and $k=2$ (+6.74%), illustrating that single-step Markov lookahead is insufficient for branching BFS traversals, whereas $k=2$ and $k=3$ capture multi-branch frontier expansions before cache pollution sets in at $k=5$.

---

## 7. Corrections

- Explicit correction: The values `67,645` and `63,331` cited in Section 7 of the preliminary audit report were an erroneous narrative transcription and must be discarded.

