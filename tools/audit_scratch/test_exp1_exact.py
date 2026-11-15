import os
import json
from collections import OrderedDict

# 1. Regenerate model according to phase2_train_model.py
from collections import defaultdict, Counter

print("Rebuilding traceA model according to phase2_train_model.py...")
markov_chain = defaultdict(Counter)
prev_page = None
with open("data/pages/cleaned_training_pages.txt", "r") as infile:
    for line in infile:
        line = line.strip()
        if not line: continue
        current_page = int(line)
        if prev_page is not None:
            markov_chain[prev_page][current_page] += 1
        prev_page = current_page

rebuilt_model = {}
for page, next_counts in markov_chain.items():
    rebuilt_model[str(page)] = {
        str(nxt_page): count
        for nxt_page, count in next_counts.most_common(3)
    }

rebuilt_path = "tools/audit_scratch/markov_model_traceA_rebuild.json"
with open(rebuilt_path, "w") as outfile:
    json.dump(rebuilt_model, outfile, indent=2)

print(f"Rebuilt model saved to {rebuilt_path} ({os.path.getsize(rebuilt_path)} bytes)")

# Also load markov_model_top5.json
with open("data/models/markov_model_top5.json") as f:
    top5_json = json.load(f)

# Compare rebuilt_model with top5_json (first 3 keys)
mismatches = 0
for k, v in rebuilt_model.items():
    rebuilt_keys = list(v.keys())
    top5_keys = list(top5_json[k].keys())[:3]
    if rebuilt_keys != top5_keys:
        mismatches += 1
print(f"Mismatches between rebuilt top-3 and markov_model_top5.json first 3 keys: {mismatches}")

# Now let's test exp1_simulator_top1_2 logic on rebuilt model!
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

def run_simulation(trace_path, model, capacity=1024, predictive=False, prefetch_limit=3):
    cache = LRUCache(capacity=capacity)
    page_faults = 0
    total_accesses = 0
    with open(trace_path, "r", buffering=8 * 1024 * 1024) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            page = int(line)
            total_accesses += 1
            is_hit = cache.access(page)
            if not is_hit:
                page_faults += 1
                if predictive and model is not None and page in model:
                    predicted_pages = model[page][:prefetch_limit]
                    cache.prefetch(predicted_pages)
    return total_accesses, page_faults

# Model parsing as in exp1_simulator_top1_2.py:
model = {
    int(curr_page): [int(nxt) for nxt in next_dict.keys()]
    for curr_page, next_dict in rebuilt_model.items()
}

print("\nRunning exp1_simulator_top1_2.py logic on rebuilt model:")
base_tot, base_f = run_simulation("data/pages/cleaned_testing_pages.txt", None, predictive=False)
t1_tot, t1_f = run_simulation("data/pages/cleaned_testing_pages.txt", model, predictive=True, prefetch_limit=1)
t2_tot, t2_f = run_simulation("data/pages/cleaned_testing_pages.txt", model, predictive=True, prefetch_limit=2)
t3_tot, t3_f = run_simulation("data/pages/cleaned_testing_pages.txt", model, predictive=True, prefetch_limit=3)

print(f"  Baseline faults: {base_f:,}")
print(f"  Top-1 faults:    {t1_f:,}")
print(f"  Top-2 faults:    {t2_f:,}")
print(f"  Top-3 faults:    {t3_f:,}")

