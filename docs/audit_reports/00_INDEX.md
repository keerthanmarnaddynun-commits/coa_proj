# Index of Audit Reports

> **Path note (project reorganized on 2026-11-15):** file names in this document use the original flat layout. Current locations: data files in `data/pages/`, `data/traces/`, `data/models/`; scripts in `src/pipeline/`, `src/experiments/`, `tools/`, `tools/audit_scratch/`, `tools/verify_prefetch_count/`. Numbers and results are unchanged.

**Project:** Operating System Page-Replacement & Markov-Prefetching Simulation  
**Audit Series Date:** October 29, 2026  
**Auditor:** Automated Diagnostic Assistant (Antigravity)  

---

## Audit Reports Directory

| Document | Report Name | One-Line Purpose | Primary Files Investigated |
| :--- | :--- | :--- | :--- |
| **[01_page_fault_equivalence.md](01_page_fault_equivalence.md)** | Page Fault Equivalence Audit | Explains why baseline LRU changed (67,696 to 66,979) between trace runs while Top-3 prefetching remained identically 57,512. | `cleaned_testing_pages.txt`, `traces/testing_trace.txt`, `exp9_per_thread_markov.py` |
| **[02_bfs_root_vertices.md](02_bfs_root_vertices.md)** | BFS Root Vertices Audit | Identifies and mathematically verifies the exact BFS root vertices used to generate the original (Trace A) training and testing traces. | `pp/main.c`, `pp/graph.c`, `pp/Makefile`, `pp/README.md`, `cleaned_*.txt` |
| **[03_exp1_reconciliation.md](03_exp1_reconciliation.md)** | Experiment 1 Reconciliation Audit | Resolves the discrepancy between logged Top-1/Top-2 numbers (67,634 / 63,132) and invalid narrative citations (67,645 / 63,331). | `exp1_simulator_top1_2.py`, `lab_record.md`, `markov_model_top5.json` |
| **[04_trace_model_segregation.md](04_trace_model_segregation.md)** | Trace & Model Segregation Audit | Documents the reconstruction of `markov_model_traceA.json`, archiving of Trace B models, and verified reproduction of Experiments 1 and 3. | `markov_model_traceA.json`, `markov_model_traceB.json`, `phase3_simulator.py` |
| **[05_traceB_prefetch_count.md](05_traceB_prefetch_count.md)** | Trace B Prefetch Count Verification | Empirically measures exact speculative page loads ($N_{\text{pref}}=57,155$), precision (58.43%), and waste (41.49%) on Trace B, reconciling the paper's "about 57,000" claim. | `traces/testing_trace.txt`, `markov_model_traceB.json`, `exp4_confidence_threshold.py` |

---

## Verification Note
All findings documented in these reports were produced by read-only scripts executed within `audit_scratch/`. No preexisting codebase files, traces, or models were modified during this investigation.

