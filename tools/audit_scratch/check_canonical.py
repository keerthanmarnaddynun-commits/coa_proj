import os

# Let's map unique pages in old_test and new_test
with open("data/pages/cleaned_testing_pages.txt") as f:
    old_test = [int(line.strip()) for line in f if line.strip()]

new_test = []
with open("data/traces/testing_trace.txt") as f:
    for line in f:
        parts = line.split(" ", 3)
        if len(parts) >= 3:
            new_test.append(int(parts[2], 16) >> 12)

print(f"Old test len: {len(old_test)}, New test len: {len(new_test)}")

# Let's assign an ID to each unique page based on order of first appearance
old_map = {}
old_canonical = []
for p in old_test:
    if p not in old_map:
        old_map[p] = len(old_map)
    old_canonical.append(old_map[p])

new_map = {}
new_canonical = []
for p in new_test:
    if p not in new_map:
        new_map[p] = len(new_map)
    new_canonical.append(new_map[p])

diffs = sum(1 for a, b in zip(old_canonical, new_canonical) if a != b)
print(f"Number of differences in canonical page sequence: {diffs:,} / {len(old_test):,}")

# First 20 differences
first_diffs = []
for i, (a, b) in enumerate(zip(old_canonical, new_canonical)):
    if a != b:
        first_diffs.append((i, a, b))
        if len(first_diffs) >= 20:
            break

print("First 20 canonical differences:")
for i, a, b in first_diffs:
    print(f"  Pos {i}: old_canon={a}, new_canon={b}")

