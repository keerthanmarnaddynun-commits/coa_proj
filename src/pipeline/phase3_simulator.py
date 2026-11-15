import os
import json
import time
from collections import OrderedDict

class LRUCache:
    """
    Fixed-capacity Least Recently Used (LRU) Cache implemented
    with collections.OrderedDict for O(1) lookups, insertions, and evictions.
    """
    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self.cache = OrderedDict()

    def access(self, page: int) -> bool:
        """
        Simulate accessing a page.
        Returns:
            True if hit (page was already in memory).
            False if page fault (page had to be fetched into memory).
        """
        if page in self.cache:
            self.cache.move_to_end(page)
            return True  # Hit
        
        # Page Fault: fetch into cache, evicting the least recently used page if full
        self.put(page)
        return False  # Fault

    def put(self, page: int):
        """Inserts or updates page position to most recently used."""
        if page in self.cache:
            self.cache.move_to_end(page)
        else:
            self.cache[page] = True
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)  # Evict oldest (LRU)

    def prefetch(self, pages: list):
        """Prefetches a list of predicted pages into the cache."""
        for p in pages:
            self.put(p)

    def __len__(self):
        return len(self.cache)


def load_markov_model(model_path: str = "data/models/markov_model_traceA.json") -> dict:
    """
    Loads markov_model.json and returns a lookup dictionary mapping
    current_page (int) -> list of top predicted next_page values (list of ints).
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file '{model_path}' not found.")

    with open(model_path, "r") as f:
        raw_model = json.load(f)

    # Convert string keys from JSON to integers for fast numeric lookups
    model = {}
    for curr_page, next_dict in raw_model.items():
        curr_int = int(curr_page)
        # Next pages are ordered by highest frequency
        model[curr_int] = [int(nxt) for nxt in next_dict.keys()]

    return model


def run_simulation(
    trace_path: str = "data/pages/cleaned_testing_pages.txt",
    model: dict = None,
    capacity: int = 1024,
    predictive: bool = False
) -> tuple:
    """
    Simulates page replacement over the trace file.
    Args:
        trace_path: Path to cleaned testing pages trace.
        model: Pre-trained Markov transition dictionary.
        capacity: Number of physical frames in RAM.
        predictive: If True, activates Markov prefetching on page faults.
    Returns:
        (total_accesses, page_faults, elapsed_time)
    """
    if not os.path.exists(trace_path):
        raise FileNotFoundError(f"Trace file '{trace_path}' not found.")

    cache = LRUCache(capacity=capacity)
    page_faults = 0
    total_accesses = 0

    start_time = time.time()

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

                # In Predictive Mode: on fault, query Markov model and prefetch top pages
                if predictive and model is not None and page in model:
                    predicted_pages = model[page]
                    cache.prefetch(predicted_pages)

    elapsed_time = time.time() - start_time
    return total_accesses, page_faults, elapsed_time


def main():
    trace_file = "data/pages/cleaned_testing_pages.txt"
    model_file = "data/models/markov_model_traceA.json"
    capacity = 1024

    print("=================================================================")
    print("           OS PAGE REPLACEMENT SIMULATOR (PHASE 3)               ")
    print("=================================================================")
    print(f"  Testing Trace:   {trace_file}")
    print(f"  RAM Capacity:    {capacity:,} pages ({capacity * 4 / 1024:.1f} MB)")
    print(f"  Prefetch Model:  {model_file}")
    print("=================================================================\n")

    # 1. Load Markov Model
    print("Loading Markov Model into memory...")
    t0 = time.time()
    model = load_markov_model(model_file)
    print(f"Loaded model with {len(model):,} states in {time.time() - t0:.2f}s.\n")

    # 2. Run Mode 1: Baseline LRU
    print("Running Mode 1: Baseline LRU (Standard Demand Paging)...")
    base_total, base_faults, base_time = run_simulation(
        trace_path=trace_file,
        model=None,
        capacity=capacity,
        predictive=False
    )
    base_fault_rate = (base_faults / base_total) * 100 if base_total > 0 else 0
    base_hit_rate = 100.0 - base_fault_rate
    print(f"  Mode 1 completed in {base_time:.2f}s.")
    print(f"  Page Faults: {base_faults:,} / {base_total:,} ({base_fault_rate:.3f}%)\n")

    # 3. Run Mode 2: Predictive LRU
    print("Running Mode 2: Predictive LRU (Markov Heuristic Prefetching)...")
    pred_total, pred_faults, pred_time = run_simulation(
        trace_path=trace_file,
        model=model,
        capacity=capacity,
        predictive=True
    )
    pred_fault_rate = (pred_faults / pred_total) * 100 if pred_total > 0 else 0
    pred_hit_rate = 100.0 - pred_fault_rate
    print(f"  Mode 2 completed in {pred_time:.2f}s.")
    print(f"  Page Faults: {pred_faults:,} / {pred_total:,} ({pred_fault_rate:.3f}%)\n")

    # 4. Comparative Report
    fault_reduction = base_faults - pred_faults
    pct_reduction = (fault_reduction / base_faults) * 100 if base_faults > 0 else 0

    print("=================================================================")
    print("                   SIMULATION PERFORMANCE REPORT                 ")
    print("=================================================================")
    print(f"{'Metric':<30} | {'Baseline LRU':<14} | {'Predictive LRU':<14}")
    print("-" * 65)
    print(f"{'Total Page Accesses':<30} | {base_total:<14,} | {pred_total:<14,}")
    print(f"{'Page Hits':<30} | {base_total - base_faults:<14,} | {pred_total - pred_faults:<14,}")
    print(f"{'Page Faults':<30} | {base_faults:<14,} | {pred_faults:<14,}")
    print(f"{'Hit Ratio':<30} | {base_hit_rate:<13.3f}% | {pred_hit_rate:<13.3f}%")
    print(f"{'Fault Ratio':<30} | {base_fault_rate:<13.3f}% | {pred_fault_rate:<13.3f}%")
    print(f"{'Simulation Time':<30} | {base_time:<12.2f}s | {pred_time:<12.2f}s")
    print("=" * 65)
    print("                           RESULTS                               ")
    print("=" * 65)
    print(f"  Absolute Faults Prevented:   {fault_reduction:,} faults")
    print(f"  Page Fault Reduction:        {pct_reduction:.2f}%")
    print("=================================================================")

if __name__ == "__main__":
    main()
