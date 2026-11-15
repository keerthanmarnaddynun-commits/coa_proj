import os
from collections import defaultdict, Counter, OrderedDict

# 1. Load cleaned_testing_pages.txt
with open("data/pages/cleaned_testing_pages.txt") as f:
    old_test = [int(line.strip()) for line in f if line.strip()]

# 2. Load cleaned_training_pages.txt
with open("data/pages/cleaned_training_pages.txt") as f:
    old_train = [int(line.strip()) for line in f if line.strip()]

# 3. Load traces/testing_trace.txt
new_test = []
with open("data/traces/testing_trace.txt") as f:
    for line in f:
        parts = line.split(" ", 3)
        if len(parts) >= 3:
            new_test.append(int(parts[2], 16) >> 12)

# 4. Load traces/training_trace.txt
new_train = []
with open("data/traces/training_trace.txt") as f:
    for line in f:
        parts = line.split(" ", 3)
        if len(parts) >= 3:
            new_train.append(int(parts[2], 16) >> 12)

print(f"Old test len:  {len(old_test):,}, unique pages: {len(set(old_test)):,}")
print(f"Old train len: {len(old_train):,}, unique pages: {len(set(old_train)):,}")
print(f"New test len:  {len(new_test):,}, unique pages: {len(set(new_test)):,}")
print(f"New train len: {len(new_train):,}, unique pages: {len(set(new_train)):,}")

# Check unique pages in old vs new:
old_test_unique = sorted(list(set(old_test)))
new_test_unique = sorted(list(set(new_test)))
print(f"Old test min page: {old_test_unique[0]}, max page: {old_test_unique[-1]}")
print(f"New test min page: {new_test_unique[0]}, max page: {new_test_unique[-1]}")

# Train old model:
old_trans = defaultdict(Counter)
for p1, p2 in zip(old_train[:-1], old_train[1:]):
    old_trans[p1][p2] += 1
old_model = {p: [nxt for nxt, _ in c.most_common(3)] for p, c in old_trans.items()}

# Train new model:
new_trans = defaultdict(Counter)
for p1, p2 in zip(new_train[:-1], new_train[1:]):
    new_trans[p1][p2] += 1
new_model = {p: [nxt for nxt, _ in c.most_common(3)] for p, c in new_trans.items()}

print(f"Old model states: {len(old_model):,}")
print(f"New model states: {len(new_model):,}")

