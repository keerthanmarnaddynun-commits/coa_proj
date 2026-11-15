import os
import json
import time
from collections import defaultdict, Counter

def build_graph_oracle(
    dataset_path="pp/Amazon0302.txt",
    output_path="data/models/graph_oracle.json",
    top_k=3
):
    """
    Constructs a causal topological prefetch oracle (graph_oracle.json).
    Maps physical virtual pages (containing BFS nodes and CSR adjacency structures)
    to the pages containing their immediate topological neighbors in the graph.
    """
    if not os.path.exists(dataset_path):
        if os.path.exists("Amazon0302.txt"):
            dataset_path = "Amazon0302.txt"
        else:
            raise FileNotFoundError(f"Graph dataset not found at '{dataset_path}'.")

    print(f"Building Graph Topological Oracle from '{dataset_path}'...")
    start_time = time.time()

    # 1. Parse directed graph dataset
    adj = defaultdict(list)
    max_node = 0
    edge_count = 0

    with open(dataset_path, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            parts = line.strip().split()
            if len(parts) >= 2:
                u, v = int(parts[0]), int(parts[1])
                adj[u].append(v)
                if u > max_node:
                    max_node = u
                if v > max_node:
                    max_node = v
                edge_count += 1

    num_nodes = max_node + 1
    parse_time = time.time() - start_time
    print(f"  Parsed {num_nodes:,} nodes and {edge_count:,} edges in {parse_time:.2f}s.")

    # 2. Build Compressed Sparse Row (CSR) index bounds
    row_pointers = [0] * (num_nodes + 1)
    for i in range(num_nodes):
        row_pointers[i + 1] = row_pointers[i] + len(adj[i])

    # 3. Base page constants derived from C runtime memory addresses
    BASE_DIST = 11421696      # distances: 4 bytes/node -> 1024 nodes/page
    BASE_ROW  = 11422208      # row_pointers: 8 bytes/node -> 512 nodes/page
    BASE_COL  = 5051392       # column_indices: 4 bytes/edge -> 1024 edges/page

    # 4. Map each page to the pages containing its immediate topological neighbors
    page_oracle = defaultdict(Counter)

    for u in range(num_nodes):
        p_dist = BASE_DIST + (u // 1024)
        p_row  = BASE_ROW  + (u // 512)

        start_e = row_pointers[u]
        end_e   = row_pointers[u + 1]

        for e in range(start_e, end_e):
            p_col = BASE_COL + (e // 1024)
            v = adj[u][e - start_e]
            v_dist = BASE_DIST + (v // 1024)
            v_row  = BASE_ROW  + (v // 512)

            # Traversing node u touches its adjacency list and neighbor distances
            if p_col != p_dist:
                page_oracle[p_dist][p_col] += 1
            if v_dist != p_dist:
                page_oracle[p_dist][v_dist] += 1

            if p_col != p_row:
                page_oracle[p_row][p_col] += 1
            if v_dist != p_row:
                page_oracle[p_row][v_dist] += 1

            if v_dist != p_col:
                page_oracle[p_col][v_dist] += 1
            if v_row != p_col:
                page_oracle[p_col][v_row] += 1

    # 5. Prune to Top-K most frequent topological neighbor pages
    oracle_top_k = {}
    for p, counter in page_oracle.items():
        oracle_top_k[str(p)] = [q for q, _ in counter.most_common(top_k)]

    # 6. Save graph oracle to JSON
    with open(output_path, "w") as f:
        json.dump(oracle_top_k, f, indent=2)

    total_time = time.time() - start_time
    file_size_kb = os.path.getsize(output_path) / 1024
    print(f"Graph Oracle generation complete in {total_time:.2f}s:")
    print(f"  - Mapped pages:       {len(oracle_top_k):,}")
    print(f"  - Output file:        '{output_path}' ({file_size_kb:.2f} KB)")

    return oracle_top_k

if __name__ == "__main__":
    build_graph_oracle()

