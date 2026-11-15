import os
import json
from collections import OrderedDict

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

with open("data/models/markov_model.json") as f:
    raw_model = json.load(f)
model = {int(k): [int(nxt) for nxt in (v.keys() if isinstance(v, dict) else v)] for k, v in raw_model.items()}

# Test on cleaned_testing_pages.txt
cache_base = LRUCache(1024)
cache_pref = LRUCache(1024)
faults_base = 0
faults_pref = 0
total = 0

with open("data/pages/cleaned_testing_pages.txt") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        p = int(line)
        total += 1
        if not cache_base.access(p):
            faults_base += 1
        if not cache_pref.access(p):
            faults_pref += 1
            if p in model:
                cache_pref.prefetch(model[p][:3])

print(f"Results on cleaned_testing_pages.txt using current markov_model.json:")
print(f"  Total accesses:  {total:,}")
print(f"  Baseline faults: {faults_base:,}")
print(f"  Top-3 faults:    {faults_pref:,}")

