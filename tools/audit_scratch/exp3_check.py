import os
import json
import time
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

    def __len__(self):
        return len(self.cache)


def load_markov_model(model_path="data/models/markov_model_traceA.json"):
    with open(model_path, "r") as f:
        raw = json.load(f)
    return {int(k): [int(nxt) for nxt in v.keys()] for k, v in raw.items()}


def run_simulation(trace_path, model, capacity, predictive=False, k=3):
    cache = LRUCache(capacity)
    faults = 0
    total = 0
    t0 = time.time()

    with open(trace_path, "r", buffering=8 * 1024 * 1024) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = int(line)
            total += 1

            if not cache.access(p):
                faults += 1
                if predictive and model and p in model:
                    cache.prefetch(model[p][:k])

    return total, faults, time.time() - t0


def main():
    trace_file = "data/pages/cleaned_testing_pages.txt"
    model_file = "data/models/markov_model_traceA.json"
    capacities = [512, 1024, 2048]

    print("Loading model...")
    model = load_markov_model(model_file)

    for cap in capacities:
        _, fb, tb = run_simulation(trace_file, model, cap, predictive=False)
        _, fp, tp = run_simulation(trace_file, model, cap, predictive=True, k=3)
        print(f"Capacity {cap:4d}: Baseline = {fb:7,d} | Predictive = {fp:7,d} | Reduction = {(fb-fp)/fb*100:+.2f}%")

if __name__ == "__main__":
    main()

