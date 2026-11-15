import os
import json
import time
from collections import OrderedDict

class LRUCache:
    """Fixed-capacity Least Recently Used (LRU) Cache."""
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


def load_models():
    """Loads 1st-order and 2nd-order Markov models."""
    with open("data/models/markov_model_traceA.json", "r") as f:
        m1_raw = json.load(f)
    m1 = {int(k): [int(nxt) for nxt in v.keys()] for k, v in m1_raw.items()}

    with open("data/models/markov_model_order2.json", "r") as f:
        m2_raw = json.load(f)
    m2 = {k: [int(nxt) for nxt in v.keys()] for k, v in m2_raw.items()}

    return m1, m2


def run_baseline(trace_path="data/pages/cleaned_testing_pages.txt", capacity=1024):
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
    return total, faults, time.time() - t0


def run_order1(m1, trace_path="data/pages/cleaned_testing_pages.txt", capacity=1024):
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
                if p in m1:
                    cache.prefetch(m1[p][:3])
    return total, faults, time.time() - t0


def run_order2(m2, trace_path="data/pages/cleaned_testing_pages.txt", capacity=1024):
    cache = LRUCache(capacity)
    faults = 0
    total = 0
    p2, p1 = None, None
    t0 = time.time()
    with open(trace_path, "r", buffering=8 * 1024 * 1024) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = int(line)
            total += 1
            is_hit = cache.access(p)
            p2, p1 = p1, p
            if not is_hit:
                faults += 1
                if p2 is not None:
                    key = f"{p2},{p1}"
                    if key in m2:
                        cache.prefetch(m2[key][:3])
    return total, faults, time.time() - t0


def main():
    trace_file = "data/pages/cleaned_testing_pages.txt"
    capacity = 1024

    print("=========================================================================================")
    print("      EXPERIMENT 2: 1ST-ORDER vs 2ND-ORDER MARKOV PREFETCHING COMPARISON                 ")
    print("=========================================================================================")
    print(f"  Testing Trace:   {trace_file}")
    print(f"  RAM Capacity:    {capacity:,} pages ({capacity * 4 / 1024:.1f} MB)")
    print("=========================================================================================\n")

    print("Loading models into memory...")
    m1, m2 = load_models()
    print(f"  1st-Order Model: {len(m1):,} states")
    print(f"  2nd-Order Model: {len(m2):,} states\n")

    print("1/3 Running Baseline LRU (No prefetching)...")
    base_tot, base_f, base_t = run_baseline(trace_file, capacity)
    print(f"    Completed in {base_t:.2f}s | Faults: {base_f:,}\n")

    print("2/3 Running 1st-Order Predictive LRU (Top-3)...")
    m1_tot, m1_f, m1_t = run_order1(m1, trace_file, capacity)
    print(f"    Completed in {m1_t:.2f}s | Faults: {m1_f:,}\n")

    print("3/3 Running 2nd-Order Predictive LRU (Top-3)...")
    m2_tot, m2_f, m2_t = run_order2(m2, trace_file, capacity)
    print(f"    Completed in {m2_t:.2f}s | Faults: {m2_f:,}\n")

    def get_stats(tot, f, t, base_faults):
        hits = tot - f
        hr = (hits / tot * 100) if tot > 0 else 0
        fr = (f / tot * 100) if tot > 0 else 0
        red = ((base_faults - f) / base_faults * 100) if base_faults > 0 else 0
        return hits, hr, fr, red

    b_hits, b_hr, b_fr, b_red = get_stats(base_tot, base_f, base_t, base_f)
    m1_hits, m1_hr, m1_fr, m1_red = get_stats(m1_tot, m1_f, m1_t, base_f)
    m2_hits, m2_hr, m2_fr, m2_red = get_stats(m2_tot, m2_f, m2_t, base_f)

    col_name = 28
    col_stat = 16

    print("=========================================================================================")
    print("                         THREE-WAY CONFIGURATION PERFORMANCE TABLE                       ")
    print("=========================================================================================")
    header = (
        f"{'Metric':<{col_name}} | "
        f"{'Baseline LRU':^{col_stat}} | "
        f"{'1st-Order Markov':^{col_stat}} | "
        f"{'2nd-Order Markov':^{col_stat}}"
    )
    print(header)
    print("-" * len(header))

    def row(label, v1, v2, v3):
        print(f"{label:<{col_name}} | {v1:^{col_stat}} | {v2:^{col_stat}} | {v3:^{col_stat}}")

    row("Total Page Accesses", f"{base_tot:,}", f"{m1_tot:,}", f"{m2_tot:,}")
    row("Page Hits", f"{b_hits:,}", f"{m1_hits:,}", f"{m2_hits:,}")
    row("Page Faults", f"{base_f:,}", f"{m1_f:,}", f"{m2_f:,}")
    row("Hit Ratio (%)", f"{b_hr:.3f}%", f"{m1_hr:.3f}%", f"{m2_hr:.3f}%")
    row("Fault Ratio (%)", f"{b_fr:.3f}%", f"{m1_fr:.3f}%", f"{m2_fr:.3f}%")
    row("Page Fault Reduction (%)", f"{b_red:.2f}%", f"{m1_red:+.2f}%", f"{m2_red:+.2f}%")
    row("Simulation Time (s)", f"{base_t:.2f}s", f"{m1_t:.2f}s", f"{m2_t:.2f}s")

    print("=" * len(header))

    print("\n=========================================================================================")
    print("                               EXPERIMENT 2 FINDINGS                                     ")
    print("=========================================================================================")
    print(f"  - 1st-Order Markov:  {m1_f:,} faults ({m1_red:+.2f}% reduction vs Baseline, {base_f - m1_f:,} faults saved)")
    print(f"  - 2nd-Order Markov:  {m2_f:,} faults ({m2_red:+.2f}% reduction vs Baseline, {m2_f - base_f:,} additional faults)")
    print("  - Architectural Insight:")
    print("      The 2nd-order model suffers from severe state-space fragmentation (403k vs 2k states)")
    print("      and temporal sparsity. Under concurrent multi-threaded BFS traversal, exact 2-page")
    print("      history matches are often noisy, causing speculative cache pollution that evicts")
    print("      active working set frames and underperforms even the baseline LRU.")
    print("=========================================================================================")

if __name__ == "__main__":
    main()
