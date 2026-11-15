import os
from collections import defaultdict, Counter, OrderedDict

# Train 1st-order Markov model on cleaned_training_pages.txt
print("Training Markov model on cleaned_training_pages.txt...")
transitions = defaultdict(Counter)
prev_page = None
with open("data/pages/cleaned_training_pages.txt") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        p = int(line)
        if prev_page is not None:
            transitions[prev_page][p] += 1
        prev_page = p

old_trained_model = {p: [nxt for nxt, _ in c.most_common(3)] for p, c in transitions.items()}
print(f"Trained old model: {len(old_trained_model):,} unique states")

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
            if p in old_trained_model:
                cache_pref.prefetch(old_trained_model[p])

print(f"Results on cleaned_testing_pages.txt with model retrained from cleaned_training_pages.txt:")
print(f"  Total accesses:  {total:,}")
print(f"  Baseline faults: {faults_base:,}")
print(f"  Top-3 faults:    {faults_pref:,}")

