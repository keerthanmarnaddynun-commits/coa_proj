import os
import json
import time
from collections import OrderedDict

# Copy of exp1_simulator_top1_2.py pointing to rebuilt model
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

def load_markov_model(model_path: str = "tools/audit_scratch/markov_model_traceA_rebuild.json") -> dict:
    with open(model_path, "r") as f:
        raw_model = json.load(f)
    return {
        int(curr_page): [int(nxt) for nxt in next_dict.keys()]
        for curr_page, next_dict in raw_model.items()
    }

def run_simulation(
    trace_path: str = "data/pages/cleaned_testing_pages.txt",
    model: dict = None,
    capacity: int = 1024,
    predictive: bool = False,
    prefetch_limit: int = 3
) -> tuple:
    cache = LRUCache(capacity=capacity)
    page_faults = 0
    total_accesses = 0

    with open(trace_path, "r", buffering=8 * 1024 * 1024) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            page = int(line)
            total_accesses += 1

            is_hit = cache.access(page)

            if not is_hit:
                page_faults += 1
                if predictive and model is not None and page in model:
                    predicted_pages = model[page][:prefetch_limit]
                    cache.prefetch(predicted_pages)

    return total_accesses, page_faults

if __name__ == "__main__":
    model = load_markov_model("tools/audit_scratch/markov_model_traceA_rebuild.json")
    for k in [0, 1, 2, 3]:
        pred = (k > 0)
        tot, f = run_simulation(model=model, predictive=pred, prefetch_limit=k)
        print(f"k={k}: faults={f}")

