import os
import json
from collections import OrderedDict, defaultdict, Counter

# Let's test different variations to see what yields 67,645 and 63,331!

with open("tools/audit_scratch/markov_model_traceA_rebuild.json") as f:
    rebuilt_json = json.load(f)

model = {int(k): [int(nxt) for nxt in v.keys()] for k, v in rebuilt_json.items()}

# Let's check variation 1:
# What if already-resident pages are NOT prefetched (skipped without move_to_end)?
class LRU_skip_resident:
    def __init__(self, capacity=1024):
        self.capacity = capacity
        self.cache = OrderedDict()
    def access(self, p):
        if p in self.cache:
            self.cache.move_to_end(p)
            return True
        if len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        self.cache[p] = True
        return False
    def prefetch(self, pages):
        for p in pages:
            if p not in self.cache:
                if len(self.cache) >= self.capacity:
                    self.cache.popitem(last=False)
                self.cache[p] = True

# Variation 2:
# What if prefetch is done BEFORE putting the faulting page in cache?
# Variation 3:
# What if slice is [:k] on Counter before or after?
# Variation 4:
# What if the trace tested was NOT cleaned_testing_pages.txt, but something else?
# Wait, what if markov_model.json (the NEW model) was used? We know that gave 67,696.
# What about ties in Counter?

def run_test(cache_cls, prefetch_before=False):
    for k in [1, 2, 3]:
        c = cache_cls(1024)
        faults = 0
        with open("data/pages/cleaned_testing_pages.txt") as f:
            for line in f:
                p = int(line.strip())
                if not c.access(p):
                    faults += 1
                    if p in model:
                        c.prefetch(model[p][:k])
        print(f"k={k}: faults={faults}")

print("Testing skip_resident:")
run_test(LRU_skip_resident)

