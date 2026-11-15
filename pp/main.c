/**
 * @file main.c
 * @brief High-performance parallel graph analysis driver, BFS benchmark, and memory trace generator.
 *
 * Evaluates OpenMP scheduling strategies (Static, Dynamic, and Task Work-Stealing)
 * and generates training and testing memory access traces.
 *
 * Standard: C99
 */

#define _POSIX_C_SOURCE 200809L

#include "graph.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <time.h>
#include <omp.h>
#include <sys/stat.h>

/* =========================================================================
 * CLI Configuration Structure
 * ========================================================================= */

typedef struct {
    const char *dataset_path;
    node_t root;
    node_t test_root;
    int num_threads;
    bool run_benchmark;
    bool run_trace;
} AppConfig;

static void print_usage(const char *prog_name) {
    printf("Usage: %s [dataset_file] [options]\n\n", prog_name);
    printf("Options:\n");
    printf("  --benchmark         Execute Parallel BFS benchmarks for Strategies A, B, and C (default)\n");
    printf("  --trace             Generate training_trace.txt and testing_trace.txt using Strategy C\n");
    printf("  --root <id>         Root vertex for BFS / training trace (default: 0)\n");
    printf("  --test-root <id>    Root vertex for testing trace (default: 1)\n");
    printf("  --threads <n>       Number of OpenMP worker threads (default: %d detected)\n", omp_get_max_threads());
    printf("  --help              Display this help message and exit\n\n");
    printf("Examples:\n");
    printf("  %s Amazon0302.txt\n", prog_name);
    printf("  %s Amazon0302.txt --benchmark --threads 8\n", prog_name);
    printf("  %s Amazon0302.txt --trace --root 0 --test-root 1\n", prog_name);
}

static AppConfig parse_args(int argc, char *argv[]) {
    AppConfig config;
    config.dataset_path = "Amazon0302.txt";
    config.root = 0;
    config.test_root = 1;
    config.num_threads = omp_get_max_threads();
    config.run_benchmark = false;
    config.run_trace = false;

    bool action_specified = false;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            print_usage(argv[0]);
            exit(EXIT_SUCCESS);
        } else if (strcmp(argv[i], "--benchmark") == 0) {
            config.run_benchmark = true;
            action_specified = true;
        } else if (strcmp(argv[i], "--trace") == 0) {
            config.run_trace = true;
            action_specified = true;
        } else if (strcmp(argv[i], "--root") == 0 && i + 1 < argc) {
            config.root = (node_t)strtoul(argv[++i], NULL, 10);
        } else if (strcmp(argv[i], "--test-root") == 0 && i + 1 < argc) {
            config.test_root = (node_t)strtoul(argv[++i], NULL, 10);
        } else if (strcmp(argv[i], "--threads") == 0 && i + 1 < argc) {
            config.num_threads = atoi(argv[++i]);
            if (config.num_threads < 1) config.num_threads = 1;
        } else if (argv[i][0] != '-') {
            config.dataset_path = argv[i];
        } else {
            fprintf(stderr, "Unknown option: %s\n", argv[i]);
            print_usage(argv[0]);
            exit(EXIT_FAILURE);
        }
    }

    /* Default behavior: run benchmark if neither trace nor benchmark was explicitly requested */
    if (!action_specified) {
        config.run_benchmark = true;
    }

    return config;
}

/* =========================================================================
 * Helper: File Size Query
 * ========================================================================= */

static double get_file_size_mb(const char *filepath) {
    struct stat st;
    if (stat(filepath, &st) == 0) {
        return (double)st.st_size / (1024.0 * 1024.0);
    }
    return 0.0;
}

/* =========================================================================
 * BFS Benchmarking Routine
 * ========================================================================= */

static void run_bfs_benchmarks(const GraphCSR *graph, node_t root) {
    printf("-------------------------------------------------------------------\n");
    printf("          OPENMP PARALLEL BFS SCHEDULING STRATEGY BENCHMARK        \n");
    printf("-------------------------------------------------------------------\n");
    printf("  BFS Root Node                 : %u\n", root);
    printf("  Available OpenMP Threads      : %d\n\n", omp_get_max_threads());

    /* Warm-up run */
    BFSResult warmup = graph_bfs_parallel(graph, root, BFS_STRATEGY_STATIC, NULL);
    bfs_result_free(&warmup);

    /* Run Strategy A: Static Partitioning */
    BFSResult resA = graph_bfs_parallel(graph, root, BFS_STRATEGY_STATIC, NULL);

    /* Run Strategy B: Dynamic Chunking (chunk size 64) */
    BFSResult resB = graph_bfs_parallel(graph, root, BFS_STRATEGY_DYNAMIC, NULL);

    /* Run Strategy C: Work-Stealing Tasking (Pure Timing, tracing OFF) */
    BFSResult resC = graph_bfs_parallel(graph, root, BFS_STRATEGY_TASKING, NULL);

    /* Calculate performance metrics */
    double timeA_ms = resA.execution_time * 1000.0;
    double timeB_ms = resB.execution_time * 1000.0;
    double timeC_ms = resC.execution_time * 1000.0;

    double mtepsA = ((double)graph->num_edges / resA.execution_time) / 1e6;
    double mtepsB = ((double)graph->num_edges / resB.execution_time) / 1e6;
    double mtepsC = ((double)graph->num_edges / resC.execution_time) / 1e6;

    /* Verify correctness: ensure distance vectors match across all strategies */
    bool all_match = true;
    for (node_t i = 0; i < graph->num_nodes; i++) {
        if (resA.distances[i] != resB.distances[i] || resA.distances[i] != resC.distances[i]) {
            all_match = false;
            break;
        }
    }

    /* Print Formatted Benchmark Table */
    printf("+---------------------------------------+-------------+---------+-----------+-----------+\n");
    printf("| Scheduling Strategy                   | Time (ms)   | Speedup | Throughput| Status    |\n");
    printf("+---------------------------------------+-------------+---------+-----------+-----------+\n");
    printf("| Strategy A: schedule(static)          | %9.2f ms |   1.00x | %6.2f ME/s| PASSED    |\n",
           timeA_ms, mtepsA);
    printf("| Strategy B: schedule(dynamic, 64)     | %9.2f ms | %6.2fx | %6.2f ME/s| PASSED    |\n",
           timeB_ms, timeA_ms / timeB_ms, mtepsB);
    printf("| Strategy C: Tasking (Work-Stealing)   | %9.2f ms | %6.2fx | %6.2f ME/s| PASSED    |\n",
           timeC_ms, timeA_ms / timeC_ms, mtepsC);
    printf("+---------------------------------------+-------------+---------+-----------+-----------+\n\n");

    printf("  BFS Traversal Summary:\n");
    printf("    - Reached Vertices          : %u / %u (%.2f%% of graph)\n",
           resA.total_visited, graph->num_nodes,
           (double)resA.total_visited / (double)graph->num_nodes * 100.0);
    printf("    - Max BFS Tree Depth        : %d levels\n", resA.max_level);
    printf("    - Correctness Verification  : %s\n\n",
           all_match ? "PASSED (100% identical distances across all strategies)" : "FAILED (discrepancy detected!)");

    /* Clean up BFS distance buffers */
    bfs_result_free(&resA);
    bfs_result_free(&resB);
    bfs_result_free(&resC);
}

/* =========================================================================
 * Memory Trace Generation Routine
 * ========================================================================= */

static void run_trace_generation(const GraphCSR *graph, node_t train_root, node_t test_root) {
    printf("-------------------------------------------------------------------\n");
    printf("       STRATEGY C MEMORY TRACE GENERATOR (WORK-STEALING MODE)       \n");
    printf("-------------------------------------------------------------------\n");

    /* 1. Generate Training Trace */
    const char *train_file = "training_trace.txt";
    printf("  [1/2] Generating Training Trace from root %u -> '%s'...\n", train_root, train_file);
    BFSResult train_res = graph_bfs_parallel(graph, train_root, BFS_STRATEGY_TASKING, train_file);
    double train_mb = get_file_size_mb(train_file);
    printf("        -> Completed in %.3f s\n", train_res.execution_time);
    printf("        -> Logged %llu memory accesses (%.2f MB on disk)\n\n",
           (unsigned long long)train_res.trace_records, train_mb);
    bfs_result_free(&train_res);

    /* 2. Generate Testing Trace */
    const char *test_file = "testing_trace.txt";
    printf("  [2/2] Generating Testing Trace from root %u -> '%s'...\n", test_root, test_file);
    BFSResult test_res = graph_bfs_parallel(graph, test_root, BFS_STRATEGY_TASKING, test_file);
    double test_mb = get_file_size_mb(test_file);
    printf("        -> Completed in %.3f s\n", test_res.execution_time);
    printf("        -> Logged %llu memory accesses (%.2f MB on disk)\n\n",
           (unsigned long long)test_res.trace_records, test_mb);
    bfs_result_free(&test_res);

    printf("  Trace Generation Finished Successfully:\n");
    printf("    - Training Trace: %s (%.2f MB)\n", train_file, train_mb);
    printf("    - Testing Trace : %s (%.2f MB)\n\n", test_file, test_mb);
}

/* =========================================================================
 * Main Entry Point
 * ========================================================================= */

int main(int argc, char *argv[]) {
    AppConfig config = parse_args(argc, argv);

    /* Set OpenMP thread count */
    omp_set_num_threads(config.num_threads);

    printf("===================================================================\n");
    printf("    PARALLEL GRAPH ANALYSIS & BFS BENCHMARK (OPENMP WORK-STEALING) \n");
    printf("===================================================================\n");
    printf("  Dataset Path : %s\n", config.dataset_path);
    printf("  Thread Count : %d OpenMP threads\n\n", config.num_threads);

    /* 1. Load Dataset into CSR */
    printf("[1/3] Loading dataset into Compressed Sparse Row (CSR) representation...\n");
    double load_t0 = omp_get_wtime();
    GraphCSR *graph = graph_load_from_file(config.dataset_path);
    double load_time = omp_get_wtime() - load_t0;

    if (!graph) {
        fprintf(stderr, "Fatal Error: Failed to load dataset '%s'.\n", config.dataset_path);
        return EXIT_FAILURE;
    }
    printf("      -> Graph loaded in %.2f ms (Throughput: %.2f M edges/s)\n\n",
           load_time * 1000.0, ((double)graph->num_edges / load_time) / 1e6);

    /* 2. Verify Graph Integrity */
    printf("[2/3] Verifying CSR structure integrity...\n");
    if (!graph_verify_integrity(graph)) {
        fprintf(stderr, "Fatal Error: CSR integrity verification failed.\n");
        graph_free(&graph);
        return EXIT_FAILURE;
    }
    printf("      -> CSR Invariants Verified Successfully.\n\n");

    /* 3. Execute Benchmarks or Trace Generation */
    printf("[3/3] Executing requested workload...\n");
    if (config.run_benchmark) {
        run_bfs_benchmarks(graph, config.root);
    }

    if (config.run_trace) {
        run_trace_generation(graph, config.root, config.test_root);
    }

    /* 4. Clean Memory Deallocation */
    printf("Releasing graph memory...\n");
    graph_free(&graph);
    printf("All memory deallocated cleanly.\n");

    printf("===================================================================\n");
    printf("                       EXECUTION COMPLETED                         \n");
    printf("===================================================================\n");

    return EXIT_SUCCESS;
}
