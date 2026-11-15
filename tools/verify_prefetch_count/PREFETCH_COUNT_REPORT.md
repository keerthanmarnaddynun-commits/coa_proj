# Trace B Prefetch Count Verification & Table II Reconciliation

**File:** `verify_prefetch_count/PREFETCH_COUNT_REPORT.md`  
**Reference Report:** `audit_reports/05_traceB_prefetch_count.md`  
**Measurement Script:** `verify_prefetch_count/measure_prefetch.py`  
**Data Artifact:** `verify_prefetch_count/results.json`  

---

### Executive Summary

- **Paper Statement:** *"On Trace B about 57,000 speculative pages are loaded to avoid 9,467 faults."*
- **Empirical Measurement:** **57,155** speculative pages loaded ($N_{\text{pref}}$).
- **Exact Faults Avoided:** **9,467** ($66,979 - 57,512$).
- **Discrepancy:** Only **+155 pages (+0.27%)** relative to 57,000. The claim is fully validated.

---

### Verification Table

| Metric | Trace A (Exps 1–8) | Trace B (Exps 9–11) | Notes |
| :--- | :---: | :---: | :--- |
| **Demand Faults (Baseline)** | 67,696 | 66,979 | Demand miss count |
| **Demand Faults (Top-3 Prefetch)** | 57,512 | 57,512 | Demand miss count with prefetcher |
| **Faults Avoided** | **10,184** | **9,467** | $66,979 - 57,512 = 9,467$ |
| **$N_{\text{pref}}$ (Speculative Pages Loaded)** | **56,721** | **57,155** | Candidates **not** already resident in cache |
| **$N_{\text{used}}$ (Prefetch Hits / Useful)** | 33,540 | 33,397 | Touched before eviction |
| **$N_{\text{unused}}$ (Prefetch Waste)** | 23,149 | 23,714 | Evicted before demand access |
| **Residual Resident at EOF** | 32 | 44 | Still in cache at end of trace |
| **Precision** ($\frac{N_{\text{used}}}{N_{\text{pref}}}$) | **59.13%** | **58.43%** | Table II precision metric |
| **Waste** ($\frac{N_{\text{unused}}}{N_{\text{pref}}}$) | **40.81%** | **41.49%** | Table II waste metric |
| **Candidates Skipped (Already Resident)** | 115,815 | 114,913 | Redundant loads avoided |
| **Total Candidates Proposed** | 172,536 | 172,068 | $N_{\text{pref}} + N_{\text{skipped}}$ |

---

### Sanity Checks (Trace B)

- Baseline Faults: **66,979** (Exact match)
- Top-3 Faults: **57,512** (Exact match)
- Dirty Evictions: LRU = **1,871**, Top-3 = **2,620** (Exact match)
- Total Evictions: LRU = **65,955**, Top-3 = **113,643** (Exact match)
- Hit Rates: LRU = **98.228%**, Top-3 = **98.479%** (Exact match)

---

### Calibration Check (Trace A)

Trace A measurements matched the paper's Table II exactly:
- $N_{\text{pref}} = 56,721$
- Precision = $59.13\%$
- Waste = $40.81\%$

