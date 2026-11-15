# High-Performance Graph Analysis Framework (SNAP Amazon0302)

A modular, C99-compliant, high-performance C framework for parallel graph processing using Compressed Sparse Row (CSR) representation and OpenMP multi-threading. Specifically benchmarked on the Stanford Network Analysis Platform (SNAP) **Amazon product co-purchasing network dataset** (`amazon0302.txt`).

---

## 1. Project Architecture

```
.
├── graph.h            # CSR & BFS data structures, OpenMP strategy enums, and API prototypes
├── graph.c            # Parser, CSR builder, OpenMP parallel BFS kernels, and trace logger
├── main.c             # CLI driver, OpenMP benchmark suite, trace generator, and verification
├── Makefile           # Cross-platform build system (Clang/GCC, libomp, ASan, benchmark, trace)
├── Amazon0302.txt     # SNAP Amazon dataset (262,111 vertices, 1,234,877 directed edges)
├── training_trace.txt # Memory trace log from root 0 (~3.78M records, 133 MB)
├── testing_trace.txt  # Memory trace log from root 1 (~3.78M records, 133 MB)
└── README.md          # Complete documentation and performance analysis
```

---

## 2. Parallel Breadth-First Search (BFS) Traversal

The BFS implementation uses a **level-synchronous frontier expansion** pattern with dual ping-pong frontier queues (`frontier` and `next_frontier`) and an atomic compare-and-swap (`__sync_bool_compare_and_swap`) on the `distances` array to eliminate data races during concurrent neighbor visits.

### Three OpenMP Scheduling Strategies:

1. **Strategy A: Static Partitioning (`#pragma omp parallel for schedule(static)`)**
   - Evenly divides the active level frontier across threads upfront with minimal scheduling overhead.
   - Ideal when vertices across the frontier have uniform degree distributions.

2. **Strategy B: Dynamic Chunking (`#pragma omp parallel for schedule(dynamic, 64)`)**
   - Distributes chunks of 64 vertices to worker threads on demand from a runtime queue.
   - Provides load balancing when vertex out-degrees vary significantly.

3. **Strategy C: Work-Stealing Tasking (`#pragma omp task` / `#pragma omp taskwait`)**
   - Decomposes the frontier into discrete OpenMP tasks (64 vertices per task) spawned within `#pragma omp single`.
   - Worker threads participate in runtime work-stealing from local and remote task deques, synchronized at level boundaries with `#pragma omp taskwait`.

---

## 3. Memory Trace Logger

During Strategy C (Work-Stealing), an optional tracing mode can be enabled to capture the full sequence of virtual memory addresses and symbolic CSR array indices accessed during traversal:

- **Format**: `<OP> <HEX_ADDRESS> <ARRAY_NAME>[<INDEX>]`
- **Example**:
  ```text
  WRITE 0xa84800000 distances[0]
  WRITE 0xa84900000 frontier[0]
  READ  0xa84900000 frontier[0]
  READ  0xa84a00000 row_pointers[0]
  READ  0xa84a00008 row_pointers[1]
  READ  0x4eb400000 column_indices[0]
  READ  0xa84800004 distances[1]
  WRITE 0xa84800004 distances[1]
  WRITE 0xa84400000 next_frontier[0]
  ```
- **Thread-Safe Buffered I/O**: Each OpenMP task writes to a thread-local 64 KB buffer that flushes to disk under a mutex lock, logging ~3.78 million memory accesses in ~1.07 seconds without thread contention.
- **Pure Benchmark Isolation**: During timing benchmarks, tracing code is completely bypassed, guaranteeing zero overhead on CPU execution time.

---

## 4. Benchmark Results on Amazon0302 (8 Threads)

Dataset: 262,111 vertices, 1,234,877 directed edges, Max BFS Depth: 69 levels.

| Scheduling Strategy | OpenMP Directive | Execution Time | Speedup | Throughput | Verification |
|---|---|---|---|---|---|
| **Strategy A** | `#pragma omp parallel for schedule(static)` | **18.62 ms** | 1.00x | **66.33 ME/s** | PASSED |
| **Strategy B** | `#pragma omp parallel for schedule(dynamic, 64)` | **19.12 ms** | 0.97x | **64.59 ME/s** | PASSED |
| **Strategy C** | `#pragma omp task` / `#pragma omp taskwait` | **79.05 ms** | 0.24x | **15.62 ME/s** | PASSED |

> [!NOTE]
> All three strategies achieve **100% identical distance vectors** across all 262,111 reachable vertices.

---

## 5. Build and Execution Instructions

### Compilation
```bash
make
```

### Running Default Analysis and BFS Benchmarks
```bash
make run
# or
./graph_analyzer Amazon0302.txt
```

### Running Explicit Benchmark Suite
```bash
make benchmark
# with custom thread count:
./graph_analyzer Amazon0302.txt --benchmark --threads 8
```

### Generating Memory Traces (Training & Testing)
```bash
make trace
# or manually specifying custom root nodes:
./graph_analyzer Amazon0302.txt --trace --root 0 --test-root 1
```

Generates:
- `training_trace.txt` (Root node 0, ~3,780,309 records, ~133 MB)
- `testing_trace.txt` (Root node 1, ~3,780,309 records, ~133 MB)

### Debugging with AddressSanitizer
```bash
make debug
```

### Cleanup
```bash
make clean
```
