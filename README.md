# Markov Page Prefetching on Parallel BFS Traces

Trace-driven study of first-order Markov page prefetching for a parallel (OpenMP) BFS over the SNAP Amazon0302 graph (262,111 vertices, 1,234,877 edges). The project has the C trace generator, Python simulators for Experiments 1 to 11, and a browser UI.

## Folder layout

    coa_proj/
      README.md
      data/
        traces/   testing_trace.txt, training_trace.txt   (Trace B, thread-tagged)
        pages/    cleaned_training_pages.txt, cleaned_testing_pages.txt   (Trace A)
        models/   markov_model_*.json, graph_oracle.json
      src/
        pipeline/      preprocess_trace.py, phase2_train_model.py, phase3_simulator.py, build_graph_oracle.py
        experiments/   exp1_* to exp11_*
      tools/
        verify_prefetch_count/   Trace B prefetch counting check
        audit_scratch/           one-off diagnostic scripts used for the audits
        patch_graph.py           archive of an old one-off edit, do not run
      docs/
        lab_record.md, README_traces.md, audit_reports/
      pp/    C trace generator (OpenMP BFS), has its own README.md and Makefile
      ui/    browser UI, tests and export_ui_data.py (see ui/README_ui.md)
      _archive/   old backups and duplicate copies

## Traces and models

- **Trace A** (original, no thread tags): only the cleaned 4 KB page sequences are kept, `data/pages/cleaned_training_pages.txt` (BFS root 0) and `data/pages/cleaned_testing_pages.txt` (root 1). Each has 3,780,309 references over 2,025 unique pages. Used by Experiments 1 to 8 and by the UI.
- **Trace B** (re-generated, thread-tagged, 22 OpenMP threads): `data/traces/training_trace.txt` and `data/traces/testing_trace.txt`, 3,780,309 lines each. Used by Experiments 9 to 11 and the prefetch-count check.
- **Models** are in `data/models/`. Trace A: `markov_model_traceA.json`, `markov_model_top5_traceA.json`, `markov_model_order2.json`, `markov_model_order2_top5.json`, `graph_oracle.json`. Trace B: `markov_model_traceB.json`, `markov_model_per_thread_traceB.json`. The files `markov_model.json`, `markov_model_top5.json` and `markov_model_per_thread.json` are byte-identical copies kept because some scripts use those names. More detail: `docs/README_traces.md`.

## How to run (always from the project root)

    python src/pipeline/phase3_simulator.py
    python src/experiments/exp1_simulator_top1_2.py
    python src/experiments/exp1_simulator_top5.py
    python src/experiments/exp2_simulator_order2.py
    python src/experiments/exp3_ram_capacity.py
    python src/experiments/exp4_confidence_threshold.py
    python src/experiments/exp5_prefetch_aware_lru.py
    python src/experiments/exp6_adaptive_topk.py
    python src/experiments/exp7_arc_baseline.py
    python src/experiments/exp8_graph_aware.py
    python src/experiments/exp9_per_thread_markov.py
    python src/experiments/exp10_page_size.py
    python src/experiments/exp11_writeback_cost.py
    python tools/verify_prefetch_count/measure_prefetch.py

Each experiment takes about 5 to 35 seconds.

UI: double-click `ui/run_ui.bat` (opens http://localhost:8000). UI tests, from the `ui` folder: `node tests/verify_sim.mjs` and `node tests/verify_scenarios.mjs`. UI data export, from the project root: `python ui/export_ui_data.py`.

C trace generator: see `pp/README.md` (build with `make` inside `pp/`).

## Read this before running anything

- These scripts rewrite files: `exp9_per_thread_markov.py` (the two Trace B model files), `phase2_train_model.py`, `exp1_train_top5.py`, `exp2_train_order2.py`, `exp2_cross_domain.py`, `build_graph_oracle.py`, `preprocess_trace.py`, and `ui/export_ui_data.py` (everything in `ui/data/`). Back up `data/` and `ui/data/` first.
- `preprocess_trace.py` cannot parse the shipped Trace B files (they have thread tags and no `0x` prefix) and would write an empty `cleaned_testing_pages.txt`. The raw Trace A traces are not in the project, so keep the existing cleaned files.
- `phase2_train_model.py` trains on the Trace A pages and writes `data/models/markov_model.json`, but the stored `markov_model.json` is the Trace B model. Use `markov_model_traceA.json` or `markov_model_traceB.json` to be certain which trace a model belongs to.
- `tools/patch_graph.py` is a record of a one-off edit to `pp/graph.c`; its hard-coded path is obsolete. Do not run it.
- `exp1_simulator_top5.py` falls back to its own copy of the simulator when `phase3_simulator` cannot be imported. The results are the same.

## Reference results (1,024 frames, 4 KB pages)

| Trace | Baseline LRU faults | Markov Top-3 faults | Change |
| :--- | :---: | :---: | :---: |
| Trace A | 67,696 | 57,512 | 15.04% fewer faults |
| Trace B | 66,979 | 57,512 | 14.13% fewer faults |

On Trace B, Top-3 issued 57,155 prefetch loads, of which 33,397 were used (58.43%). Full results and parameters: `docs/lab_record.md`.

## Experiments at a glance

Fault changes are measured against baseline LRU on the same trace: **+X% means X% fewer faults (better), -X% means more faults (worse)**. Unless stated, RAM is 1,024 frames (4 MB) with 4 KB pages.

| Exp | Question | Script | Trace | Headline result |
| :--- | :--- | :--- | :---: | :--- |
| E1 | How many pages should be prefetched (k)? | `exp1_simulator_top1_2.py`, `exp1_simulator_top5.py` | A | Top-3 saves the most (+15.04%). Top-5 saves less (+6.88%). |
| E2 | Does a longer history (2nd-order Markov) help? | `exp2_simulator_order2.py`, `exp2_cross_domain.py` | A | No. It makes up to 1.10% more faults than baseline, and its table has 403,006 states against 2,025. |
| E3 | How does RAM size change the result? | `exp3_ram_capacity.py` | A | At 512 frames prefetching hurts (-7.26%, 221,603 to 237,684 faults). At 2,048 frames it helps a lot (+53.83%, 2,025 to 935). |
| E4 | Does a confidence threshold T help? | `exp4_confidence_threshold.py` | A | Yes. T = 0.10 gives the best result (+17.65%, 55,751 faults) with 7,382 fewer prefetches than unfiltered Top-3. |
| E5 | Should prefetched pages go at the LRU end? | `exp5_prefetch_aware_lru.py` | A | At 512 frames it turns -7.26% into +13.54% (191,587 faults). The gain mixes two effects that were not separated. |
| E6 | Can k adapt automatically? | `exp6_adaptive_topk.py` | A | At 512 frames it lowers k to 2 and turns the loss into +4.29%. At 1,024 frames it raises k to 5 (+14.90%). |
| E7 | Does ARC replacement beat LRU? | `exp7_arc_baseline.py` | A | No. ARC's parameter p stayed at 0, so it behaved like LRU (-0.36% at 512, -0.01% at 1,024, 0.00% at 2,048). |
| E8 | How close is Markov to a graph-neighbour oracle? | `exp8_graph_aware.py` | A | Oracle +15.46% (57,230 faults), Markov +15.04% (57,512). Markov gets 97.3% of the oracle's saving. The oracle is a reference, not a proven upper bound. |
| E9 | Do per-thread tables beat one global table? | `exp9_per_thread_markov.py` | B | No. Per-thread Top-3 gives +12.44% against +14.13% for global. The 22 per-thread tables hold 44,398 states against 2,025. |
| E10 | Does page size matter at fixed 4 MB RAM? | `exp10_page_size.py` | B | Not steadily: +14.68% (2 KB), +14.13% (4 KB), +15.28% (8 KB), +15.83% (16 KB). |
| E11 | What about write-back cost? | `exp11_writeback_cost.py` | B | Total cost (faults + dirty evictions) still drops +12.66% (68,850 to 60,132 units). The gain disappears if a prefetch read costs more than about 0.15 of a demand-fault read. |

Training scripts for the models used above: `exp1_train_top5.py` (E1) and `exp2_train_order2.py` (E2). Full details are in `docs/lab_record.md`.

## Documentation

- `docs/lab_record.md`: experiment log for Experiments 1 to 11
- `docs/README_traces.md`: Trace A and Trace B, model provenance
- `docs/audit_reports/00_INDEX.md`: audit reports
- `ui/README_ui.md`: the browser UI
- `pp/README.md`: trace generator
