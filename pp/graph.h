/**
 * @file graph.h
 * @brief High-performance Compressed Sparse Row (CSR) graph representation and API.
 *
 * Designed for parallel graph analysis algorithms (PageRank, BFS, SSSP, etc.).
 * Standard: C99
 */

#ifndef GRAPH_H
#define GRAPH_H

#include <stddef.h>
#include <stdint.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @typedef node_t
 * @brief Represents node identifiers (32-bit unsigned integer).
 * Supports graphs with up to ~4.29 billion vertices.
 */
typedef uint32_t node_t;

/**
 * @typedef edge_t
 * @brief Represents edge indices and pointer offsets (64-bit unsigned integer).
 * Supports graphs with > 4 billion edges without integer overflow.
 */
typedef uint64_t edge_t;

/**
 * @struct GraphCSR
 * @brief Compressed Sparse Row (CSR) representation for directed graphs.
 *
 * Memory layout:
 * - num_nodes: Total number of vertices |V|. Node IDs are 0-indexed in [0, num_nodes - 1].
 * - num_edges: Total number of directed edges |E|.
 * - row_pointers: 1D array of size (num_nodes + 1).
 *                 row_pointers[u] contains the starting index in column_indices for outgoing edges from node u.
 *                 row_pointers[u + 1] contains the ending index (exclusive).
 *                 The out-degree of node u is: (row_pointers[u + 1] - row_pointers[u]).
 * - column_indices: 1D array of size num_edges.
 *                   column_indices[row_pointers[u] ... row_pointers[u+1]-1] contains the destination nodes.
 */
typedef struct {
    node_t num_nodes;          /**< Total number of vertices (|V|) */
    edge_t num_edges;          /**< Total number of directed edges (|E|) */
    edge_t *row_pointers;      /**< 1D array of size (num_nodes + 1) */
    node_t *column_indices;    /**< 1D array of size num_edges */
} GraphCSR;

/**
 * @struct GraphStats
 * @brief Graph topology and structural metrics.
 */
typedef struct {
    node_t num_nodes;              /**< Total vertex count */
    edge_t num_edges;              /**< Total directed edge count */
    node_t max_out_degree;         /**< Maximum out-degree across all vertices */
    node_t node_max_out_degree;    /**< Vertex ID achieving maximum out-degree */
    node_t min_out_degree;         /**< Minimum out-degree across all vertices */
    node_t max_in_degree;          /**< Maximum in-degree across all vertices */
    node_t node_max_in_degree;     /**< Vertex ID achieving maximum in-degree */
    node_t min_in_degree;          /**< Minimum in-degree across all vertices */
    double avg_out_degree;         /**< Average out-degree (|E| / |V|) */
    node_t zero_out_degree_nodes;  /**< Number of sink vertices (out-degree = 0) */
    node_t zero_in_degree_nodes;   /**< Number of source vertices (in-degree = 0) */
    node_t isolated_nodes;         /**< Number of isolated vertices (in-deg = 0 and out-deg = 0) */
    double density;                /**< Graph density: |E| / (|V| * (|V| - 1)) */
    double memory_mb;              /**< Total memory footprint in Megabytes (MB) */
} GraphStats;

/* =========================================================================
 * Parallel BFS Strategy & Result Definitions
 * ========================================================================= */

/**
 * @enum BFSStrategy
 * @brief OpenMP scheduling strategies for level-synchronous parallel BFS.
 */
typedef enum {
    BFS_STRATEGY_STATIC,   /**< Strategy A: #pragma omp parallel for schedule(static) */
    BFS_STRATEGY_DYNAMIC,  /**< Strategy B: #pragma omp parallel for schedule(dynamic, 64) */
    BFS_STRATEGY_TASKING   /**< Strategy C: Work-stealing using OpenMP tasking (#pragma omp task) */
} BFSStrategy;

/**
 * @struct BFSResult
 * @brief Results and metrics from a BFS traversal execution.
 */
typedef struct {
    int32_t *distances;     /**< Array of size num_nodes. distances[u] is BFS depth (-1 if unreachable) */
    int max_level;          /**< Maximum level (depth) reached in the BFS tree */
    node_t total_visited;   /**< Total number of vertices visited/reached */
    double execution_time;  /**< Traversal execution time in seconds */
    uint64_t trace_records; /**< Number of memory trace entries logged (if tracing was enabled) */
} BFSResult;

/* =========================================================================
 * Graph Lifecycle Management
 * ========================================================================= */

/**
 * @brief Allocates a new CSR graph structure with allocated arrays.
 *
 * @param num_nodes Total number of vertices
 * @param num_edges Total number of directed edges
 * @return Pointer to newly allocated GraphCSR, or NULL on memory allocation failure.
 */
GraphCSR* graph_create(node_t num_nodes, edge_t num_edges);

/**
 * @brief Deallocates a CSR graph and sets its pointer to NULL.
 *
 * @param graph Pointer to the GraphCSR pointer to free.
 */
void graph_free(GraphCSR **graph);

/* =========================================================================
 * Loading, Validation, and Analysis
 * ========================================================================= */

/**
 * @brief Reads an edge list file (e.g. SNAP dataset format) and constructs a CSR graph in memory.
 *
 * Automatically skips comments ('#') and blank lines, dynamically counts the nodes
 * and edges, and constructs the 1D row_pointers and column_indices arrays in two fast passes.
 *
 * @param filepath Path to dataset file (e.g., "amazon0302.txt")
 * @return Pointer to populated GraphCSR, or NULL if file read or allocation failed.
 */
GraphCSR* graph_load_from_file(const char *filepath);

/**
 * @brief Validates the structural integrity and invariant guarantees of the CSR graph.
 *
 * Checks:
 * 1. Non-NULL graph and internal array pointers.
 * 2. row_pointers[0] == 0.
 * 3. row_pointers[num_nodes] == num_edges.
 * 4. Monotonicity: row_pointers[u] <= row_pointers[u + 1] for all u.
 * 5. Destination bounds: column_indices[e] < num_nodes for all e.
 *
 * @param graph Pointer to GraphCSR to check
 * @return true if valid, false if corruption or invariant violation is detected.
 */
bool graph_verify_integrity(const GraphCSR *graph);

/**
 * @brief Computes detailed topological statistics of the graph.
 *
 * @param graph Pointer to GraphCSR
 * @return Populated GraphStats structure
 */
GraphStats graph_compute_stats(const GraphCSR *graph);

/**
 * @brief Prints formatted graph statistics to standard output.
 *
 * @param graph Pointer to GraphCSR
 */
void graph_print_stats(const GraphCSR *graph);

/**
 * @brief Sorts outgoing neighbor lists in ascending order in-place for all nodes.
 *
 * @param graph Pointer to GraphCSR
 */
void graph_sort_neighbors(GraphCSR *graph);

/* =========================================================================
 * Parallel Breadth-First Search (BFS) API
 * ========================================================================= */

/**
 * @brief Executes parallel level-synchronous BFS traversal on the CSR graph starting from a root node.
 *
 * Supports three OpenMP scheduling strategies:
 * - Strategy A: #pragma omp parallel for schedule(static)
 * - Strategy B: #pragma omp parallel for schedule(dynamic, 64)
 * - Strategy C: Work-stealing using OpenMP tasking (#pragma omp task / #pragma omp taskwait)
 *
 * When strategy == BFS_STRATEGY_TASKING and trace_filepath is non-NULL, every accessed memory address
 * and CSR array index/pointer is logged to the specified text file. When trace_filepath is NULL,
 * tracing is completely omitted to avoid distorting CPU timing benchmarks.
 *
 * @param graph Pointer to GraphCSR
 * @param root Starting root vertex ID
 * @param strategy Scheduling strategy to use
 * @param trace_filepath Path to output trace file (or NULL to disable tracing)
 * @return BFSResult containing distances array, max_level, visited count, and execution time.
 */
BFSResult graph_bfs_parallel(const GraphCSR *graph, node_t root, BFSStrategy strategy, const char *trace_filepath);

/**
 * @brief Deallocates memory dynamically allocated inside a BFSResult struct.
 *
 * @param res Pointer to BFSResult to free
 */
void bfs_result_free(BFSResult *res);

/**
 * @brief Returns human-readable name of a BFS scheduling strategy.
 */
const char* bfs_strategy_name(BFSStrategy strategy);

/**
 * @brief Returns the OpenMP pragma directive string for a BFS scheduling strategy.
 */
const char* bfs_strategy_pragma(BFSStrategy strategy);

/* =========================================================================
 * Inline Accessor Helpers (Optimized for tight loops in parallel algorithms)
 * ========================================================================= */

/**
 * @brief Returns the out-degree of node u.
 */
static inline node_t graph_get_out_degree(const GraphCSR *graph, node_t u) {
    if (!graph || !graph->row_pointers || u >= graph->num_nodes) {
        return 0;
    }
    return (node_t)(graph->row_pointers[u + 1] - graph->row_pointers[u]);
}

/**
 * @brief Obtains a pointer to the neighbor array of node u.
 */
static inline const node_t* graph_get_neighbors(const GraphCSR *graph, node_t u, node_t *degree) {
    if (!graph || !graph->row_pointers || !graph->column_indices || u >= graph->num_nodes) {
        if (degree) *degree = 0;
        return NULL;
    }
    edge_t start = graph->row_pointers[u];
    edge_t end = graph->row_pointers[u + 1];
    node_t deg = (node_t)(end - start);
    if (degree) *degree = deg;
    return (deg > 0) ? &graph->column_indices[start] : NULL;
}

#ifdef __cplusplus
}
#endif

#endif /* GRAPH_H */
