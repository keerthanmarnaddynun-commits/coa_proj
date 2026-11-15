import os
import json
from collections import OrderedDict, defaultdict, Counter

# Load old
with open("data/pages/cleaned_testing_pages.txt") as f:
    old_test = [int(line.strip()) for line in f if line.strip()]

with open("data/pages/cleaned_training_pages.txt") as f:
    old_train = [int(line.strip()) for line in f if line.strip()]

trans_old = defaultdict(Counter)
for p1, p2 in zip(old_train[:-1], old_train[1:]):
    trans_old[p1][p2] += 1
old_model = {p: [nxt for nxt, _ in c.most_common(3)] for p, c in trans_old.items()}

# Load new
new_test = []
with open("data/traces/testing_trace.txt") as f:
    for line in f:
        parts = line.split(" ", 3)
        if len(parts) >= 3:
            new_test.append(int(parts[2], 16) >> 12)

with open("data/models/markov_model.json") as f:
    raw = json.load(f)
new_model = {int(k): [int(x) for x in v] for k, v in raw.items()}

class LRU:
    def __init__(self, cap=1024):
        self.cap = cap
        self.c = OrderedDict()
    def access(self, p):
        if p in self.c:
            self.c.move_to_end(p)
            return True
        if len(self.c) >= self.cap:
            self.c.popitem(last=False)
        self.c[p] = True
        return False
    def prefetch(self, pages):
        for p in pages:
            if p in self.c:
                self.c.move_to_end(p)
            else:
                if len(self.c) >= self.cap:
                    self.c.popitem(last=False)
                self.c[p] = True

# Old run
c_old = LRU(1024)
fault_indices_old = []
for i, p in enumerate(old_test):
    if not c_old.access(p):
        fault_indices_old.append(i)
        if p in old_model:
            c_old.prefetch(old_model[p][:3])

# New run
c_new = LRU(1024)
fault_indices_new = []
for i, p in enumerate(new_test):
    if not c_new.access(p):
        fault_indices_new.append(i)
        if p in new_model:
            c_new.prefetch(new_model[p][:3])

print(f"Total faults old: {len(fault_indices_old):,}")
print(f"Total faults new: {len(fault_indices_new):,}")

# Compare indices
matching_indices = set(fault_indices_old) & set(fault_indices_new)
print(f"Number of identical fault indices: {len(matching_indices):,} / 57,512 ({len(matching_indices)/57512*100:.2f}%)")

# Compare first 20 differing fault indices
diff_indices = []
for fo, fn in zip(fault_indices_old, fault_indices_new):
    if fo != fn:
        diff_indices.append((fo, fn))
        if len(diff_indices) >= 15:
            break

print("First 15 differing fault index pairs (old_idx, new_idx):")
for fo, fn in diff_indices:
    print(f"  Old fault at {fo:,}, New fault at {fn:,}")

