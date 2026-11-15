import os
import json
from collections import OrderedDict, defaultdict, Counter

class LRUCache:
    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self.cache = OrderedDict()

    def access(self, page: int) -> bool:
        if page in self.cache:
            self.cache.move_to_end(page)
            return True
        self.put(page)
        return False

    def put(self, page: int):
        if page in self.cache:
            self.cache.move_to_end(page)
        else:
            self.cache[page] = True
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

    def prefetch(self, pages: list):
        for p in pages:
            self.put(p)

def run_sim(pages, model=None, k=3):
    cache = LRUCache(1024)
    faults = 0
    for p in pages:
        if not cache.access(p):
            faults += 1
            if model is not None and p in model:
                cache.prefetch(model[p][:k])
    return faults

# Load test sequences
print("Loading old test pages...")
with open("data/pages/cleaned_testing_pages.txt") as f:
    old_test = [int(line.strip()) for line in f if line.strip()]

print("Loading new test pages...")
new_test = []
with open("data/traces/testing_trace.txt") as f:
    for line in f:
        parts = line.split(" ", 3)
        if len(parts) >= 3:
            new_test.append(int(parts[2], 16) >> 12)

# Train/load models
print("Training old model from cleaned_training_pages.txt...")
trans_old = defaultdict(Counter)
with open("data/pages/cleaned_training_pages.txt") as f:
    prev = None
    for line in f:
        line = line.strip()
        if not line: continue
        p = int(line)
        if prev is not None:
            trans_old[prev][p] += 1
        prev = p
old_model = {p: [nxt for nxt, _ in c.most_common(3)] for p, c in trans_old.items()}

print("Loading new model from markov_model.json...")
with open("data/models/markov_model.json") as f:
    raw = json.load(f)
new_model = {int(k): [int(x) for x in v] for k, v in raw.items()}

print("\n--- RESULTS MATRIX ---")
combos = [
    ("Old (cleaned_testing_pages.txt)", "Old model (from cleaned_training_pages.txt)", old_test, old_model),
    ("Old (cleaned_testing_pages.txt)", "New model (from traces/training_trace.txt / current markov_model.json)", old_test, new_model),
    ("New (traces/testing_trace.txt)", "Old model (from cleaned_training_pages.txt)", new_test, old_model),
    ("New (traces/testing_trace.txt)", "New model (from traces/training_trace.txt / current markov_model.json)", new_test, new_model),
]

for seq_name, mod_name, seq, mod in combos:
    base_f = run_sim(seq, model=None)
    top3_f = run_sim(seq, model=mod, k=3)
    print(f"Test sequence: {seq_name}")
    print(f"Model used:    {mod_name}")
    print(f"Baseline faults: {base_f:,} | Top-3 faults: {top3_f:,}")
    print("-" * 60)

