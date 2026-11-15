import os

# Check Amazon0302 edges from node 0 and node 1
edges_from_0 = []
edges_from_1 = []

with open("pp/Amazon0302.txt", "r") as f:
    for line in f:
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            u, v = int(parts[0]), int(parts[1])
            if u == 0:
                edges_from_0.append(v)
            elif u == 1:
                edges_from_1.append(v)

print(f"Edges from node 0 ({len(edges_from_0)} neighbors): {sorted(edges_from_0)}")
print(f"Edges from node 1 ({len(edges_from_1)} neighbors): {sorted(edges_from_1)}")

