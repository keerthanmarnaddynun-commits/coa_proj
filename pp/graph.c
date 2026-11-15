/**
 * @file graph.c
 * @brief High-performance implementation of CSR graph loading, integrity verification,
 *        topological analysis, and parallel Breadth-First Search (BFS) using OpenMP.
 *
 * Standard: C99
 */

#define _POSIX_C_SOURCE 200809L

#include "graph.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>
#include <omp.h>

#define BFS_TASK_CHUNK_SIZE 64
#define TRACE_BUF_SIZE 65536

/* =========================================================================
 * Private Helper: Fast Character & Number Parsing
 * ========================================================================= */

/**
 * @brief Advances pointer past whitespace and comment lines (starting with '#').
 */
static inline const char* skip_whitespace_and_comments(const char *p, const char *end) {
    while (p < end) {
        if (*p == '#') {
            while (p < end && *p != '\n') {
                p++;
            }
            if (p < end && *p == '\n') {
                p++;
            }
        } else if (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n') {
            p++;
        } else {
            break;
        }
    }
    return p;
}

/**
 * @brief Parses an unsigned 32-bit integer directly from a character buffer.
 */
static inline const char* parse_node_id(const char *p, const char *end, node_t *out_val) {
    node_t val = 0;
    while (p < end && (*p >= '0' && *p <= '9')) {
        val = val * 10 + (node_t)(*p - '0');
        p++;
    }
    *out_val = val;
    return p;
}

/**
 * @brief Comparison function for qsort to order neighbors in ascending order.
 */
static int compare_nodes(const void *a, const void *b) {
    node_t na = *(const node_t *)a;
    node_t nb = *(const node_t *)b;
    if (na < nb) return -1;
    if (na > nb) return 1;
    return 0;
}

/**
 * @brief Attempts to open a file. If not found, checks common case variations
 *        (e.g., "amazon0302.txt" vs "Amazon0302.txt").
 */
static FILE* open_dataset_file(const char *filepath, char *actual_path, size_t max_len) {
    FILE *f = fopen(filepath, "rb");
    if (f) {
        strncpy(actual_path, filepath, max_len - 1);
        actual_path[max_len - 1] = '\0';
        return f;
    }

    /* Check case variations for convenience */
    const char *candidates[2] = {NULL, NULL};
    if (strstr(filepath, "amazon0302.txt")) {
        candidates[0] = "Amazon0302.txt";
    } else if (strstr(filepath, "Amazon0302.txt")) {
        candidates[0] = "amazon0302.txt";
    }

    for (int i = 0; i < 1 && candidates[i] != NULL; i++) {
        f = fopen(candidates[i], "rb");
        if (f) {
            strncpy(actual_path, candidates[i], max_len - 1);
            actual_path[max_len - 1] = '\0';
            return f;
        }
    }

    return NULL;
}

/* =========================================================================
 * Graph Lifecycle Functions
 * ========================================================================= */

GraphCSR* graph_create(node_t num_nodes, edge_t num_edges) {
    GraphCSR *graph = (GraphCSR *)malloc(sizeof(GraphCSR));
    if (!graph) {
        fprintf(stderr, "Error: Memory allocation failed for GraphCSR structure.\n");
        return NULL;
    }

    graph->num_nodes = num_nodes;
    graph->num_edges = num_edges;
    graph->row_pointers = NULL;
    graph->column_indices = NULL;

    /* row_pointers array has size (num_nodes + 1) */
    size_t row_ptr_size = ((size_t)num_nodes + 1) * sizeof(edge_t);
    graph->row_pointers = (edge_t *)calloc((size_t)num_nodes + 1, sizeof(edge_t));
    if (!graph->row_pointers && row_ptr_size > 0) {
        fprintf(stderr, "Error: Memory allocation failed for row_pointers (%zu bytes).\n", row_ptr_size);
        free(graph);
        return NULL;
    }

    /* column_indices array has size num_edges */
    if (num_edges > 0) {
        size_t col_idx_size = (size_t)num_edges * sizeof(node_t);
        graph->column_indices = (node_t *)malloc(col_idx_size);
        if (!graph->column_indices) {
            fprintf(stderr, "Error: Memory allocation failed for column_indices (%zu bytes).\n", col_idx_size);
            free(graph->row_pointers);
            free(graph);
            return NULL;
        }
    }

    return graph;
}

void graph_free(GraphCSR **graph_ptr) {
    if (!graph_ptr || !*graph_ptr) {
        return;
    }

    GraphCSR *graph = *graph_ptr;
    if (graph->row_pointers) {
        free(graph->row_pointers);
        graph->row_pointers = NULL;
    }
    if (graph->column_indices) {
        free(graph->column_indices);
        graph->column_indices = NULL;
    }

    free(graph);
    *graph_ptr = NULL;
}

/* =========================================================================
 * High-Performance Dataset Loading
 * ========================================================================= */

GraphCSR* graph_load_from_file(const char *filepath) {
    if (!filepath) {
        fprintf(stderr, "Error: Filepath is NULL.\n");
        return NULL;
    }

    char actual_path[512];
    FILE *f = open_dataset_file(filepath, actual_path, sizeof(actual_path));
    if (!f) {
        fprintf(stderr, "Error: Failed to open dataset file '%s' (errno: %s).\n",
                filepath, strerror(errno));
        return NULL;
    }

    /* Determine total file size */
    if (fseek(f, 0, SEEK_END) != 0) {
        fprintf(stderr, "Error: Unable to seek in file '%s'.\n", actual_path);
        fclose(f);
        return NULL;
    }
    long file_size = ftell(f);
    if (file_size < 0) {
        fprintf(stderr, "Error: Unable to determine file size for '%s'.\n", actual_path);
        fclose(f);
        return NULL;
    }
    rewind(f);

    /* Read entire file into contiguous memory buffer for maximum I/O throughput */
    char *buffer = (char *)malloc((size_t)file_size + 1);
    if (!buffer) {
        fprintf(stderr, "Error: Failed to allocate %ld bytes for file buffer.\n", file_size);
        fclose(f);
        return NULL;
    }

    size_t bytes_read = fread(buffer, 1, (size_t)file_size, f);
    fclose(f);
    if (bytes_read != (size_t)file_size) {
        fprintf(stderr, "Warning: Expected %ld bytes, but read %zu bytes.\n", file_size, bytes_read);
    }
    buffer[bytes_read] = '\0';

    const char *p = buffer;
    const char *end = buffer + bytes_read;

    /* Dynamic First Pass: count nodes, edges, and out-degrees */
    size_t degree_cap = 65536;
    edge_t *degrees = (edge_t *)calloc(degree_cap, sizeof(edge_t));
    if (!degrees) {
        fprintf(stderr, "Error: Failed to allocate degree tracking array.\n");
        free(buffer);
        return NULL;
    }

    node_t max_node_id = 0;
    edge_t total_edges = 0;

    while (p < end) {
        p = skip_whitespace_and_comments(p, end);
        if (p >= end) break;

        node_t u, v;
        p = parse_node_id(p, end, &u);
        p = skip_whitespace_and_comments(p, end);
        if (p >= end) {
            fprintf(stderr, "Error: Incomplete edge entry at end of file.\n");
            break;
        }
        p = parse_node_id(p, end, &v);

        total_edges++;

        /* Expand degrees buffer if node index exceeds current capacity */
        node_t larger_id = (u > v) ? u : v;
        if ((size_t)larger_id >= degree_cap) {
            size_t new_cap = degree_cap * 2;
            while ((size_t)larger_id >= new_cap) {
                new_cap *= 2;
            }
            edge_t *new_degrees = (edge_t *)realloc(degrees, new_cap * sizeof(edge_t));
            if (!new_degrees) {
                fprintf(stderr, "Error: Failed to reallocate degree array to %zu elements.\n", new_cap);
                free(degrees);
                free(buffer);
                return NULL;
            }
            memset(new_degrees + degree_cap, 0, (new_cap - degree_cap) * sizeof(edge_t));
            degrees = new_degrees;
            degree_cap = new_cap;
        }

        degrees[u]++;
        if (u > max_node_id) max_node_id = u;
        if (v > max_node_id) max_node_id = v;
    }

    node_t total_nodes = (total_edges > 0) ? (max_node_id + 1) : 0;

    /* Allocate CSR Graph */
    GraphCSR *graph = graph_create(total_nodes, total_edges);
    if (!graph) {
        free(degrees);
        free(buffer);
        return NULL;
    }

    /* Compute Prefix Sum (Cumulative Out-Degrees) to populate row_pointers */
    graph->row_pointers[0] = 0;
    for (node_t i = 0; i < total_nodes; i++) {
        graph->row_pointers[i + 1] = graph->row_pointers[i] + degrees[i];
    }

    /* Reuse degrees array as working cursor */
    edge_t *cursor = degrees;
    memcpy(cursor, graph->row_pointers, (size_t)total_nodes * sizeof(edge_t));

    /* Second Pass: populate column_indices */
    p = buffer;
    while (p < end) {
        p = skip_whitespace_and_comments(p, end);
        if (p >= end) break;

        node_t u, v;
        p = parse_node_id(p, end, &u);
        p = skip_whitespace_and_comments(p, end);
        p = parse_node_id(p, end, &v);

        graph->column_indices[cursor[u]++] = v;
    }

    /* Free temporary working buffers */
    free(cursor);
    free(buffer);

    return graph;
}

/* =========================================================================
 * Verification and Diagnostics
 * ========================================================================= */

bool graph_verify_integrity(const GraphCSR *graph) {
    if (!graph) {
        fprintf(stderr, "Integrity Failure: Graph pointer is NULL.\n");
        return false;
    }

    if (!graph->row_pointers) {
        fprintf(stderr, "Integrity Failure: row_pointers array is NULL.\n");
        return false;
    }

    if (graph->num_edges > 0 && !graph->column_indices) {
        fprintf(stderr, "Integrity Failure: column_indices array is NULL for non-empty graph.\n");
        return false;
    }

    /* Check boundary invariant 1: row_pointers[0] == 0 */
    if (graph->row_pointers[0] != 0) {
        fprintf(stderr, "Integrity Failure: row_pointers[0] = %llu, expected 0.\n",
                (unsigned long long)graph->row_pointers[0]);
        return false;
    }

    /* Check boundary invariant 2: row_pointers[num_nodes] == num_edges */
    if (graph->row_pointers[graph->num_nodes] != graph->num_edges) {
        fprintf(stderr, "Integrity Failure: row_pointers[num_nodes] (%llu) != num_edges (%llu).\n",
                (unsigned long long)graph->row_pointers[graph->num_nodes],
                (unsigned long long)graph->num_edges);
        return false;
    }

    edge_t self_loops = 0;

    /* Validate row pointer monotonicity and target vertex bounds */
    for (node_t u = 0; u < graph->num_nodes; u++) {
        edge_t start = graph->row_pointers[u];
        edge_t end = graph->row_pointers[u + 1];

        if (start > end) {
            fprintf(stderr, "Integrity Failure: Non-monotonic row_pointers at node %u: start=%llu, end=%llu.\n",
                    u, (unsigned long long)start, (unsigned long long)end);
            return false;
        }

        for (edge_t e = start; e < end; e++) {
            node_t v = graph->column_indices[e];
            if (v >= graph->num_nodes) {
                fprintf(stderr, "Integrity Failure: Destination node %u at edge index %llu exceeds total_nodes (%u).\n",
                        v, (unsigned long long)e, graph->num_nodes);
                return false;
            }
            if (u == v) {
                self_loops++;
            }
        }
    }

    if (self_loops > 0) {
        printf("Integrity Note: Detected %llu self-loop edge(s).\n", (unsigned long long)self_loops);
    }

    return true;
}

/* =========================================================================
 * Graph Statistics Calculation and Printing
 * ========================================================================= */

GraphStats graph_compute_stats(const GraphCSR *graph) {
    GraphStats stats;
    memset(&stats, 0, sizeof(GraphStats));

    if (!graph || graph->num_nodes == 0) {
        return stats;
    }

    stats.num_nodes = graph->num_nodes;
    stats.num_edges = graph->num_edges;
    stats.avg_out_degree = (double)graph->num_edges / (double)graph->num_nodes;
    stats.min_out_degree = UINT32_MAX;

    /* Allocate array to compute in-degrees */
    node_t *in_degrees = (node_t *)calloc(graph->num_nodes, sizeof(node_t));
    if (!in_degrees) {
        fprintf(stderr, "Warning: Failed to allocate in-degree buffer for statistics.\n");
    }

    /* Calculate out-degree statistics */
    for (node_t u = 0; u < graph->num_nodes; u++) {
        node_t out_deg = (node_t)(graph->row_pointers[u + 1] - graph->row_pointers[u]);

        if (out_deg > stats.max_out_degree) {
            stats.max_out_degree = out_deg;
            stats.node_max_out_degree = u;
        }
        if (out_deg < stats.min_out_degree) {
            stats.min_out_degree = out_deg;
        }
        if (out_deg == 0) {
            stats.zero_out_degree_nodes++;
        }

        /* Accumulate in-degrees */
        if (in_degrees) {
            edge_t start = graph->row_pointers[u];
            edge_t end = graph->row_pointers[u + 1];
            for (edge_t e = start; e < end; e++) {
                node_t v = graph->column_indices[e];
                in_degrees[v]++;
            }
        }
    }

    /* Calculate in-degree statistics */
    if (in_degrees) {
        stats.min_in_degree = UINT32_MAX;
        for (node_t v = 0; v < graph->num_nodes; v++) {
            node_t in_deg = in_degrees[v];
            node_t out_deg = (node_t)(graph->row_pointers[v + 1] - graph->row_pointers[v]);

            if (in_deg > stats.max_in_degree) {
                stats.max_in_degree = in_deg;
                stats.node_max_in_degree = v;
            }
            if (in_deg < stats.min_in_degree) {
                stats.min_in_degree = in_deg;
            }
            if (in_deg == 0) {
                stats.zero_in_degree_nodes++;
            }
            if (in_deg == 0 && out_deg == 0) {
                stats.isolated_nodes++;
            }
        }
        free(in_degrees);
    }

    /* Compute graph density: E / (V * (V - 1)) */
    if (graph->num_nodes > 1) {
        double possible_edges = (double)graph->num_nodes * ((double)graph->num_nodes - 1.0);
        stats.density = (double)graph->num_edges / possible_edges;
    } else {
        stats.density = 0.0;
    }

    /* Calculate CSR memory consumption in MB */
    size_t struct_bytes = sizeof(GraphCSR);
    size_t row_ptr_bytes = ((size_t)graph->num_nodes + 1) * sizeof(edge_t);
    size_t col_idx_bytes = (size_t)graph->num_edges * sizeof(node_t);
    stats.memory_mb = (double)(struct_bytes + row_ptr_bytes + col_idx_bytes) / (1024.0 * 1024.0);

    return stats;
}

void graph_print_stats(const GraphCSR *graph) {
    if (!graph) {
        printf("Graph is NULL.\n");
        return;
    }

    GraphStats stats = graph_compute_stats(graph);

    printf("===================================================================\n");
    printf("                    CSR GRAPH TOPOLOGY STATISTICS                  \n");
    printf("===================================================================\n");
    printf("  Total Vertices (|V|)          : %u\n", stats.num_nodes);
    printf("  Total Directed Edges (|E|)    : %llu\n", (unsigned long long)stats.num_edges);
    printf("  Graph Density                 : %.6e\n", stats.density);
    printf("-------------------------------------------------------------------\n");
    printf("  Out-Degree Distribution:\n");
    printf("    - Maximum Out-Degree        : %u (Node ID: %u)\n", stats.max_out_degree, stats.node_max_out_degree);
    printf("    - Minimum Out-Degree        : %u\n", stats.min_out_degree);
    printf("    - Average Out-Degree        : %.4f\n", stats.avg_out_degree);
    printf("    - Sink Nodes (Out-Deg = 0)  : %u\n", stats.zero_out_degree_nodes);
    printf("-------------------------------------------------------------------\n");
    printf("  In-Degree Distribution:\n");
    printf("    - Maximum In-Degree         : %u (Node ID: %u)\n", stats.max_in_degree, stats.node_max_in_degree);
    printf("    - Minimum In-Degree         : %u\n", stats.min_in_degree);
    printf("    - Source Nodes (In-Deg = 0) : %u\n", stats.zero_in_degree_nodes);
    printf("    - Isolated Nodes (Deg = 0)  : %u\n", stats.isolated_nodes);
    printf("-------------------------------------------------------------------\n");
    printf("  Memory Footprint:\n");
    printf("    - row_pointers Array        : %.2f MB (%zu bytes)\n",
           (double)(((size_t)stats.num_nodes + 1) * sizeof(edge_t)) / (1024.0 * 1024.0),
           ((size_t)stats.num_nodes + 1) * sizeof(edge_t));
    printf("    - column_indices Array      : %.2f MB (%zu bytes)\n",
           (double)((size_t)stats.num_edges * sizeof(node_t)) / (1024.0 * 1024.0),
           (size_t)stats.num_edges * sizeof(node_t));
    printf("    - Total CSR In-Memory Size  : %.2f MB\n", stats.memory_mb);
    printf("===================================================================\n");
}

/* =========================================================================
 * Neighbor Ordering
 * ========================================================================= */

void graph_sort_neighbors(GraphCSR *graph) {
    if (!graph || !graph->row_pointers || !graph->column_indices) {
        return;
    }

    for (node_t u = 0; u < graph->num_nodes; u++) {
        edge_t start = graph->row_pointers[u];
        edge_t end = graph->row_pointers[u + 1];
        size_t deg = (size_t)(end - start);
        if (deg > 1) {
            qsort(&graph->column_indices[start], deg, sizeof(node_t), compare_nodes);
        }
    }
}

/* =========================================================================
 * Memory Trace Logger (for Strategy C Tracing Mode)
 * ========================================================================= */

typedef struct {
    FILE *fp;
    omp_lock_t lock;
    uint64_t total_records;
    bool enabled;
} TraceLogger;

static inline void trace_flush(TraceLogger *logger, char *buf, size_t *len, uint64_t *count) {
    if (!logger || !logger->enabled || *len == 0) return;
    omp_set_lock(&logger->lock);
    fwrite(buf, 1, *len, logger->fp);
    logger->total_records += *count;
    omp_unset_lock(&logger->lock);
    *len = 0;
    *count = 0;
}

static inline void trace_log(TraceLogger *logger, char *buf, size_t *len, uint64_t *count,
                             int tid, const char *op, const void *addr, const char *array, uint64_t idx) {
    if (!logger || !logger->enabled) return;
    if (*len > TRACE_BUF_SIZE - 256) {
        trace_flush(logger, buf, len, count);
    }
    int written = snprintf(buf + *len, TRACE_BUF_SIZE - *len, "T%d %s %p %s[%llu]\n",
                           tid, op, addr, array, (unsigned long long)idx);
    if (written > 0) {
        *len += (size_t)written;
        (*count)++;
    }
}

/* =========================================================================
 * Parallel Breadth-First Search (BFS) Implementations
 * ========================================================================= */

const char* bfs_strategy_name(BFSStrategy strategy) {
    switch (strategy) {
        case BFS_STRATEGY_STATIC:
            return "Strategy A: Static Partitioning";
        case BFS_STRATEGY_DYNAMIC:
            return "Strategy B: Dynamic Chunking";
        case BFS_STRATEGY_TASKING:
            return "Strategy C: Work-Stealing Tasking";
        default:
            return "Unknown Strategy";
    }
}

const char* bfs_strategy_pragma(BFSStrategy strategy) {
    switch (strategy) {
        case BFS_STRATEGY_STATIC:
            return "#pragma omp parallel for schedule(static)";
        case BFS_STRATEGY_DYNAMIC:
            return "#pragma omp parallel for schedule(dynamic, 64)";
        case BFS_STRATEGY_TASKING:
            return "#pragma omp task / #pragma omp taskwait";
        default:
            return "N/A";
    }
}

void bfs_result_free(BFSResult *res) {
    if (res && res->distances) {
        free(res->distances);
        res->distances = NULL;
    }
}

BFSResult graph_bfs_parallel(const GraphCSR *graph, node_t root, BFSStrategy strategy, const char *trace_filepath) {
    BFSResult result;
    memset(&result, 0, sizeof(BFSResult));

    if (!graph || root >= graph->num_nodes) {
        fprintf(stderr, "Error: Invalid graph or root node %u (num_nodes: %u).\n",
                root, graph ? graph->num_nodes : 0);
        return result;
    }

    /* Allocate and initialize distance array with -1 (unvisited) */
    int32_t *distances = (int32_t *)malloc(graph->num_nodes * sizeof(int32_t));
    if (!distances) {
        fprintf(stderr, "Error: Memory allocation failed for BFS distances array.\n");
        return result;
    }

    #pragma omp parallel for schedule(static)
    for (node_t i = 0; i < graph->num_nodes; i++) {
        distances[i] = -1;
    }

    /* Allocate ping-pong frontier queues */
    node_t *frontier = (node_t *)malloc(graph->num_nodes * sizeof(node_t));
    node_t *next_frontier = (node_t *)malloc(graph->num_nodes * sizeof(node_t));
    if (!frontier || !next_frontier) {
        fprintf(stderr, "Error: Memory allocation failed for BFS frontier queues.\n");
        free(distances);
        free(frontier);
        free(next_frontier);
        return result;
    }

    /* Initialize root */
    distances[root] = 0;
    frontier[0] = root;
    size_t frontier_size = 1;
    int current_level = 0;

    /* Setup optional trace logger (only for Strategy C when trace_filepath is provided) */
    TraceLogger logger;
    memset(&logger, 0, sizeof(TraceLogger));
    bool tracing_active = (trace_filepath != NULL && strategy == BFS_STRATEGY_TASKING);

    if (tracing_active) {
        logger.fp = fopen(trace_filepath, "w");
        if (!logger.fp) {
            fprintf(stderr, "Error: Failed to open trace output file '%s' (errno: %s).\n",
                    trace_filepath, strerror(errno));
            tracing_active = false;
        } else {
            setvbuf(logger.fp, NULL, _IOFBF, 1024 * 1024);
            omp_init_lock(&logger.lock);
            logger.enabled = true;
            logger.total_records = 0;

            /* Log root initialization */
            fprintf(logger.fp, "T0 WRITE %p distances[%u]\n", (void *)&distances[root], root);
            fprintf(logger.fp, "T0 WRITE %p frontier[0]\n", (void *)&frontier[0]);
            logger.total_records += 2;
        }
    }

    /* ---------------------------------------------------------------------
     * Benchmark Timing Start
     * --------------------------------------------------------------------- */
    double t_start = omp_get_wtime();

    /* =====================================================================
     * Execution Path 1: Strategy C with Memory Trace Logging
     * ===================================================================== */
    if (tracing_active) {
        while (frontier_size > 0) {
            size_t next_size = 0;

            #pragma omp parallel
            {
                #pragma omp single
                {
                    for (size_t i = 0; i < frontier_size; i += BFS_TASK_CHUNK_SIZE) {
                        size_t start = i;
                        size_t end = (start + BFS_TASK_CHUNK_SIZE < frontier_size) ?
                                     (start + BFS_TASK_CHUNK_SIZE) : frontier_size;

                        #pragma omp task firstprivate(start, end)
                        {
                            int tid = omp_get_thread_num();
                            char local_buf[TRACE_BUF_SIZE];
                            size_t local_len = 0;
                            uint64_t local_count = 0;

                            for (size_t idx = start; idx < end; idx++) {
                                trace_log(&logger, local_buf, &local_len, &local_count,
                                          tid, "READ", &frontier[idx], "frontier", idx);
                                node_t u = frontier[idx];

                                trace_log(&logger, local_buf, &local_len, &local_count,
                                          tid, "READ", &graph->row_pointers[u], "row_pointers", u);
                                edge_t start_edge = graph->row_pointers[u];

                                trace_log(&logger, local_buf, &local_len, &local_count,
                                          tid, "READ", &graph->row_pointers[u + 1], "row_pointers", u + 1);
                                edge_t end_edge = graph->row_pointers[u + 1];

                                for (edge_t e = start_edge; e < end_edge; e++) {
                                    trace_log(&logger, local_buf, &local_len, &local_count,
                                              tid, "READ", &graph->column_indices[e], "column_indices", e);
                                    node_t v = graph->column_indices[e];

                                    trace_log(&logger, local_buf, &local_len, &local_count,
                                              tid, "READ", &distances[v], "distances", v);
                                    if (distances[v] == -1) {
                                        if (__sync_bool_compare_and_swap(&distances[v], -1, current_level + 1)) {
                                            trace_log(&logger, local_buf, &local_len, &local_count,
                                                      tid, "WRITE", &distances[v], "distances", v);
                                            size_t pos = __sync_fetch_and_add(&next_size, 1);
                                            next_frontier[pos] = v;
                                            trace_log(&logger, local_buf, &local_len, &local_count,
                                                      tid, "WRITE", &next_frontier[pos], "next_frontier", pos);
                                        }
                                    }
                                }
                            }
                            trace_flush(&logger, local_buf, &local_len, &local_count);
                        }
                    }
                    #pragma omp taskwait
                }
            }

            node_t *tmp = frontier;
            frontier = next_frontier;
            next_frontier = tmp;
            frontier_size = next_size;
            current_level++;
        }

        fclose(logger.fp);
        omp_destroy_lock(&logger.lock);
        result.trace_records = logger.total_records;

    /* =====================================================================
     * Execution Path 2: Pure Timing Benchmarks (Zero Trace Logging Overhead)
     * ===================================================================== */
    } else {
        while (frontier_size > 0) {
            size_t next_size = 0;

            if (strategy == BFS_STRATEGY_STATIC) {
                /* Strategy A: #pragma omp parallel for schedule(static) */
                #pragma omp parallel for schedule(static)
                for (size_t i = 0; i < frontier_size; i++) {
                    node_t u = frontier[i];
                    edge_t start_edge = graph->row_pointers[u];
                    edge_t end_edge = graph->row_pointers[u + 1];

                    for (edge_t e = start_edge; e < end_edge; e++) {
                        node_t v = graph->column_indices[e];
                        if (distances[v] == -1) {
                            if (__sync_bool_compare_and_swap(&distances[v], -1, current_level + 1)) {
                                size_t pos = __sync_fetch_and_add(&next_size, 1);
                                next_frontier[pos] = v;
                            }
                        }
                    }
                }
            } else if (strategy == BFS_STRATEGY_DYNAMIC) {
                /* Strategy B: #pragma omp parallel for schedule(dynamic, 64) */
                #pragma omp parallel for schedule(dynamic, 64)
                for (size_t i = 0; i < frontier_size; i++) {
                    node_t u = frontier[i];
                    edge_t start_edge = graph->row_pointers[u];
                    edge_t end_edge = graph->row_pointers[u + 1];

                    for (edge_t e = start_edge; e < end_edge; e++) {
                        node_t v = graph->column_indices[e];
                        if (distances[v] == -1) {
                            if (__sync_bool_compare_and_swap(&distances[v], -1, current_level + 1)) {
                                size_t pos = __sync_fetch_and_add(&next_size, 1);
                                next_frontier[pos] = v;
                            }
                        }
                    }
                }
            } else {
                /* Strategy C: Work-Stealing using OpenMP tasking */
                #pragma omp parallel
                {
                    #pragma omp single
                    {
                        for (size_t i = 0; i < frontier_size; i += BFS_TASK_CHUNK_SIZE) {
                            size_t start = i;
                            size_t end = (start + BFS_TASK_CHUNK_SIZE < frontier_size) ?
                                         (start + BFS_TASK_CHUNK_SIZE) : frontier_size;

                            #pragma omp task firstprivate(start, end)
                            {
                                for (size_t idx = start; idx < end; idx++) {
                                    node_t u = frontier[idx];
                                    edge_t start_edge = graph->row_pointers[u];
                                    edge_t end_edge = graph->row_pointers[u + 1];

                                    for (edge_t e = start_edge; e < end_edge; e++) {
                                        node_t v = graph->column_indices[e];
                                        if (distances[v] == -1) {
                                            if (__sync_bool_compare_and_swap(&distances[v], -1, current_level + 1)) {
                                                size_t pos = __sync_fetch_and_add(&next_size, 1);
                                                next_frontier[pos] = v;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        #pragma omp taskwait
                    }
                }
            }

            node_t *tmp = frontier;
            frontier = next_frontier;
            next_frontier = tmp;
            frontier_size = next_size;
            current_level++;
        }
    }

    double t_end = omp_get_wtime();

    /* ---------------------------------------------------------------------
     * Compute Summary Results
     * --------------------------------------------------------------------- */
    node_t visited_count = 0;
    #pragma omp parallel for schedule(static) reduction(+:visited_count)
    for (node_t i = 0; i < graph->num_nodes; i++) {
        if (distances[i] != -1) {
            visited_count++;
        }
    }

    result.distances = distances;
    result.max_level = (current_level > 0) ? (current_level - 1) : 0;
    result.total_visited = visited_count;
    result.execution_time = t_end - t_start;

    /* Free temporary frontier buffers */
    free(frontier);
    free(next_frontier);

    return result;
}
