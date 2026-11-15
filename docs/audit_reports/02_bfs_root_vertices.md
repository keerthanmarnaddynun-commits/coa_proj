# Audit Report 02: BFS Root Vertices Identification

> **Path note (project reorganized on 2026-11-15):** file names in this document use the original flat layout. Current locations: data files in `data/pages/`, `data/traces/`, `data/models/`; scripts in `src/pipeline/`, `src/experiments/`, `tools/`, `tools/audit_scratch/`, `tools/verify_prefetch_count/`. Numbers and results are unchanged.

**Audit ID:** AUDIT-02  
**Subject:** Provenance and Identification of Root Vertices for Original Traces (Trace A)  
**Date:** October 29, 2026  

---

## 1. Why This Audit Was Needed

To describe the experimental methodology accurately in a research paper, the exact graph traversal parameters used to generate the benchmark traces must be explicitly stated. Because traces were generated weeks prior and preprocessed into raw page sequences (`cleaned_training_pages.txt` and `cleaned_testing_pages.txt`), the specific BFS root vertex arguments needed definitive verification from codebase artifacts and trace data.

---

## 2. Question Asked

Which BFS root vertices were used to generate the original training trace (`cleaned_training_pages.txt`) and testing trace (`cleaned_testing_pages.txt`) on October 28, 2026 (~10:25–10:51)?

---

## 3. Method

- **Repository Artifact Audit:** Searched `pp/main.c`, `pp/graph.c`, `pp/Makefile`, `pp/README.md`, and `patch_graph.py` for CLI argument parsing, defaults, and build targets.
- **Topological Adjacency Inspection:** [audit_scratch/check_amazon_roots.py](../../tools/audit_scratch/check_amazon_roots.py) extracted the out-edges and neighbor lists for candidate root vertices from the SNAP `Amazon0302.txt` dataset.
- **Trace Access Sequence Simulation:** [audit_scratch/sim_bfs.py](../../tools/audit_scratch/sim_bfs.py) and [audit_scratch/verify_indices_25_40.py](../../tools/audit_scratch/verify_indices_25_40.py) modeled the exact CSR memory access sequence generated during level-synchronous parallel BFS from root 0 vs. root 1 and compared them against `cleaned_training_pages.txt` and `cleaned_testing_pages.txt`.

---

## 4. Findings

### 4.1 Build and CLI Defaults
- **[pp/Makefile L51–53](../../pp/Makefile#L51-L53):**
  ```makefile
  trace: $(TARGET)
      ./$(TARGET) Amazon0302.txt --trace --root 0 --test-root 1
  ```
- **[pp/main.c L53–54](../../pp/main.c#L53-L54):**
  ```c
  config.root = 0;
  config.test_root = 1;
  ```
- **[pp/main.c L185–197](../../pp/main.c#L185-L197):**
  Generates `training_trace.txt` from `train_root` (0) and `testing_trace.txt` from `test_root` (1).
- **[pp/README.md L16–17, 109–110](../../pp/README.md#L16-L17):**
  Explicitly documents `training_trace.txt` as generated from root 0 and `testing_trace.txt` from root 1.

### 4.2 Empirical Trace Verification
In `Amazon0302.txt`:
- Node 0 has 5 neighbors: `[1, 2, 3, 4, 5]`
- Node 1 has 5 neighbors: `[0, 2, 4, 5, 15]`

During Level 0 (references 0–24), both traversals touch the same 5 base 4 KB pages (`distances`: 11421696, `frontier`: 11421952, `row_pointers`: 11422208, `column_indices`: 5051392, `next_frontier`: 11420672) because all vertex IDs are $< 16$.

At Level 1, the access sequences diverge at operation index 34:
- **Root 0 Traversal (Training):** Frontier expands vertex 1. Visited neighbors are skipped; reference 34 reads `column_indices[4]` $\implies$ **Page `5051392`**.
- **Root 1 Traversal (Testing):** Frontier expands vertex 0. Node 3 is unvisited, triggering `WRITE distances[3]` at reference 34 $\implies$ **Page `11421696`**.

Line 34 of `cleaned_training_pages.txt` is `5051392` (matching Root 0), while Line 34 of `cleaned_testing_pages.txt` is `11421696` (matching Root 1).

### 4.3 Traversal Horizon Across First 10,000 References

| Reference Window | Distinct Pages (Cleaned Training) | Distinct Pages (Cleaned Testing) | Traversal Behavior |
| :--- | :---: | :---: | :--- |
| **First 10 refs** | 5 | 5 | Root node Level 0 expansion |
| **First 200 refs** | 5 | 5 | Frontier levels 0–1 expanding low-index neighbors |
| **First 1,000 refs** | 7 | 6 | Frontier spreads to higher vertex indices |
| **First 5,000 refs** | 22 | 21 | Working set expands into subsequent CSR edge pages |
| **First 10,000 refs** | 42 | 56 | Distinct expansion subgraphs from roots 0 and 1 |

---

## 5. Conclusion

- **Training Root:** Vertex **`0`**
- **Testing Root:** Vertex **`1`**
- **Certainty Level:** **Certain (100%)**, verified both by hardcoded codebase build scripts and empirical trace matching against SNAP `Amazon0302.txt`.

---

## 6. Effect on the Research Paper

The experimental setup section can state with definitive precision:
> *"Memory traces were captured from parallel Breadth-First Search (BFS) using OpenMP task work-stealing over the SNAP Amazon0302 graph (262,111 vertices, 1,234,877 directed edges). The training trace was collected from BFS rooted at vertex 0 (`--root 0`), and the evaluation testing trace was collected from BFS rooted at vertex 1 (`--test-root 1`), ensuring realistic cross-root topological evaluation without synthetic synthetic bias."*

---

## 7. Corrections

None. The initial inference that roots 0 and 1 were used was fully substantiated by all documentary and mathematical evidence.

