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

## Documentation

- `docs/lab_record.md`: experiment log for Experiments 1 to 11
- `docs/README_traces.md`: Trace A and Trace B, model provenance
- `docs/audit_reports/00_INDEX.md`: audit reports
- `ui/README_ui.md`: the browser UI
- `pp/README.md`: trace generator
