# Let's map out the exact access sequence of BFS on Amazon0302 for root 0 and root 1

# Load Amazon0302 graph
adj = {}
with open("pp/Amazon0302.txt") as f:
    for line in f:
        if line.startswith("#") or not line.strip(): continue
        u, v = map(int, line.split())
        adj.setdefault(u, []).append(v)

for u in adj:
    adj[u].sort()

def simulate_bfs_trace(root):
    trace = []
    distances = {}
    frontier = [root]
    distances[root] = 0
    trace.append(('WRITE', 'distances', root))
    trace.append(('WRITE', 'frontier', 0))
    
    current_level = 0
    while frontier:
        next_frontier = []
        for idx, u in enumerate(frontier):
            trace.append(('READ', 'frontier', idx))
            trace.append(('READ', 'row_pointers', u))
            trace.append(('READ', 'row_pointers', u + 1))
            neighbors = adj.get(u, [])
            for e_idx, v in enumerate(neighbors):
                trace.append(('READ', 'column_indices', (u, v)))
                trace.append(('READ', 'distances', v))
                if v not in distances:
                    distances[v] = current_level + 1
                    trace.append(('WRITE', 'distances', v))
                    pos = len(next_frontier)
                    next_frontier.append(v)
                    trace.append(('WRITE', 'next_frontier', pos))
            if len(trace) >= 100:
                break
        frontier = next_frontier
        current_level += 1
        if len(trace) >= 100:
            break
    return trace

trace0 = simulate_bfs_trace(0)
trace1 = simulate_bfs_trace(1)

print("Root 0 trace (first 40 ops):")
for i, op in enumerate(trace0[:40]):
    print(f"{i:2d}: {op[0]:<5} {op[1]:<15} {op[2]}")

print("\nRoot 1 trace (first 40 ops):")
for i, op in enumerate(trace1[:40]):
    print(f"{i:2d}: {op[0]:<5} {op[1]:<15} {op[2]}")

