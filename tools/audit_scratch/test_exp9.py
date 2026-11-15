import os
import json
import time
from collections import OrderedDict, defaultdict, Counter

class PerThreadLRUCache:
    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.last_page = {}
        self.global_last_page = None

    def access(self, page: int, tid: str = None) -> bool:
        hit = page in self.cache
        if hit:
            self.cache.move_to_end(page)
        else:
            self.put(page)
        if tid is not None:
            self.last_page[tid] = page
        self.global_last_page = page
        return hit

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

# Load markov_model.json (which is currently on disk)
with open("data/models/markov_model.json") as f:
    raw_global = json.load(f)
global_model = {int(k): [int(x) for x in v] for k, v in raw_global.items()}

with open("data/models/markov_model_per_thread.json") as f:
    raw_thread = json.load(f)
thread_model = {tid: {int(k): [int(x) for x in v] for k, v in pdict.items()} for tid, pdict in raw_thread.items()}

print(f"Loaded global_model with {len(global_model):,} keys")
print(f"Loaded thread_model with {len(thread_model):,} threads")

# Load trace from traces/testing_trace.txt
trace = []
with open("data/traces/testing_trace.txt", "r", buffering=8*1024*1024) as f:
    for line in f:
        parts = line.split(" ", 3)
        if len(parts) >= 3:
            trace.append((parts[0], int(parts[2], 16) >> 12))

print(f"Loaded {len(trace):,} references from traces/testing_trace.txt")

# Baseline
cache_a = PerThreadLRUCache(capacity=1024)
faults_a = 0
for tid, page in trace:
    if not cache_a.access(page, tid):
        faults_a += 1

# Global Top-3
cache_b = PerThreadLRUCache(capacity=1024)
faults_b = 0
for tid, page in trace:
    if not cache_b.access(page, tid):
        faults_b += 1
        if page in global_model:
            cache_b.prefetch(global_model[page][:3])

# Per-thread Top-3
cache_c = PerThreadLRUCache(capacity=1024)
faults_c = 0
for tid, page in trace:
    if not cache_c.access(page, tid):
        faults_c += 1
        if tid in thread_model and page in thread_model[tid]:
            cache_c.prefetch(thread_model[tid][page][:3])

print(f"Results on traces/testing_trace.txt:")
print(f"  Baseline LRU:            {faults_a:,}")
print(f"  Global Markov Top-3:     {faults_b:,}")
print(f"  Per-Thread Markov Top-3: {faults_c:,}")

