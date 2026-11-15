# Audit Report 04: Trace & Model Segregation Audit

> **Path note (project reorganized on 2026-11-15):** file names in this document use the original flat layout. Current locations: data files in `data/pages/`, `data/traces/`, `data/models/`; scripts in `src/pipeline/`, `src/experiments/`, `tools/`, `tools/audit_scratch/`, `tools/verify_prefetch_count/`. Numbers and results are unchanged.

**Audit ID:** AUDIT-04  
**Subject:** Reconstruction and Archival Segregation of Trace A & Trace B Models  
**Date:** October 29, 2026  

---

## 1. Why This Audit Was Needed

When Experiment 9 ran, it retrained a global Markov model on the new thread-tagged training trace and overwrote `markov_model.json`. Because the new trace had different virtual memory base addresses than the original cleaned trace, the Experiment 1–8 scripts could no longer reproduce their original prefetching benefits (giving 0% fault reduction). This audit was needed to rebuild and archive the original Trace A model under a dedicated name, preserve the Trace B models, and restore complete project reproducibility without modifying existing code.

---

## 2. Question Asked

How can the original Trace A top-3 Markov model be rebuilt and segregated alongside Trace B models under explicit provenance names, and does this restoration reproduce the exact baseline and predictive fault counts across Phase 3 and Experiments 1 and 3?

---

## 3. Method

- **Reconstruction:** [audit_scratch/build_trace_models.py](../../tools/audit_scratch/build_trace_models.py) executed the exact training and pruning logic of [phase2_train_model.py](../../src/pipeline/phase2_train_model.py) on `cleaned_training_pages.txt` (extracting transitions with `most_common(3)` and formatting with `indent=2`), writing to `markov_model_traceA.json`.
- **Archival:** Copied the existing `markov_model.json` to `markov_model_traceB.json`, `markov_model_per_thread.json` to `markov_model_per_thread_traceB.json`, and `markov_model_top5.json` to `markov_model_top5_traceA.json`.
- **Simulation Verification:**
  - [audit_scratch/phase3_check.py](../../tools/audit_scratch/phase3_check.py) evaluated Phase 3 on `cleaned_testing_pages.txt` using `markov_model_traceA.json`.
  - [audit_scratch/exp1_exact_repro.py](../../tools/audit_scratch/exp1_exact_repro.py) evaluated Experiment 1 across degrees $k \in \{0, 1, 2, 3\}$.
  - [audit_scratch/exp3_check.py](../../tools/audit_scratch/exp3_check.py) evaluated Experiment 3 across capacities $\{512, 1024, 2048\}$.

---

## 4. Findings

### 4.1 Created Model Files
Verified file outputs produced by [audit_scratch/build_trace_models.py](../../tools/audit_scratch/build_trace_models.py):

| Target Filename | Size (Bytes) | Origin Trace | State Count | Verification Note |
| :--- | :---: | :---: | :---: | :--- |
| **`markov_model_traceA.json`** | **173,325** | Trace A | 2,025 | Exactly matches [lab_record.md L30](../lab_record.md#L30) (173,325 bytes, 3,780,308 transitions). |
| **`markov_model_traceB.json`** | **97,167** | Trace B | 2,025 | Exact copy of current Trace B model from `markov_model.json`. |
| **`markov_model_per_thread_traceB.json`** | **2,129,279** | Trace B | 44,398 | Exact copy of current Trace B per-thread model from `markov_model_per_thread.json`. |
| **`markov_model_top5_traceA.json`** | **257,329** | Trace A | 2,025 | Exact copy of `markov_model_top5.json`; confirmed keys sit in `11,421,696` range. |

### 4.2 Reproduction Results Across Experiments

#### Phase 3 Verification (`audit_scratch/phase3_check.py`)
- Baseline LRU: **67,696 faults** (Target: 67,696) $\implies$ **MATCH**
- Top-3 Predictive LRU: **57,512 faults** (Target: 57,512) $\implies$ **MATCH**
- Reduction: **+15.04%** (10,184 faults prevented) $\implies$ **MATCH**

#### Experiment 1 Verification (`audit_scratch/exp1_exact_repro.py`)
- Top-1 ($k=1$): **67,634 faults** (Target: 67,634) $\implies$ **MATCH**
- Top-2 ($k=2$): **63,132 faults** (Target: 63,132) $\implies$ **MATCH**
- Top-3 ($k=3$): **57,512 faults** (Target: 57,512) $\implies$ **MATCH**

#### Experiment 3 Verification (`audit_scratch/exp3_check.py`)
- RAM = 512 frames: Baseline = **221,603** \| Predictive = **237,684** (-7.26%) $\implies$ **MATCH**
- RAM = 1,024 frames: Baseline = **67,696** \| Predictive = **57,512** (+15.04%) $\implies$ **MATCH**
- RAM = 2,048 frames: Baseline = **2,025** \| Predictive = **935** (+53.83%) $\implies$ **MATCH**

---

## 5. Conclusion

Full deterministic reproducibility has been restored to the project. By segregating the models into `_traceA` and `_traceB` files, both experimental tracks can now run independently without address-space collisions or model overwrites.

---

## 6. Effect on the Research Paper

- **Cohesive Data Integrity:** The paper can present both the single-threaded baseline/sensitivity suite (Experiments 0–8) and the multi-threaded OpenMP thread-tagged suite (Experiments 9–11) with complete auditability.
- **Repository Archival:** Reviewers or researchers cloning the repository can execute the verification scripts against `markov_model_traceA.json` and obtain the exact tables published in the paper.

---

## 7. Corrections

- Clarified that `markov_model.json` on disk was not corrupted, but was legitimately overwritten with the Trace B global model by [exp9_per_thread_markov.py L140](../../src/experiments/exp9_per_thread_markov.py#L140). Preserving Trace A under `markov_model_traceA.json` fully rectifies the collision.

