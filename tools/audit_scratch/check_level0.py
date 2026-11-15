# Trace number of accesses in Level 0 for root 0 and root 1:
# For root 0:
# 1. WRITE distances[0]
# 2. WRITE frontier[0]
# Loop:
# READ frontier[0] (1)
# READ row_pointers[0] (1)
# READ row_pointers[1] (1)
# For each of 5 neighbors:
#   READ column_indices[e] (1)
#   READ distances[v] (1)
#   WRITE distances[v] (1)
#   WRITE next_frontier[pos] (1)
#   Total per neighbor = 4 accesses * 5 = 20 accesses.
# Total Level 0 accesses = 2 + 1 + 1 + 1 + 20 = 25 accesses?
# Wait, let's check new trace's first level accesses:

with open("data/traces/training_trace.txt") as f:
    train_lines = [f.readline().strip() for _ in range(50)]

with open("data/traces/testing_trace.txt") as f:
    test_lines = [f.readline().strip() for _ in range(50)]

print("New training trace (first 30 lines):")
for i, l in enumerate(train_lines[:30]):
    print(f"{i:2d}: {l}")

print("\nNew testing trace (first 30 lines):")
for i, l in enumerate(test_lines[:30]):
    print(f"{i:2d}: {l}")

