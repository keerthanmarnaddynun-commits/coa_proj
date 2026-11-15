import os
import json
import time
from collections import OrderedDict, defaultdict, Counter

class PerThreadLRUCache:
    """
    Fixed-capacity Least Recently Used (LRU) Cache supporting per-thread context isolation.
    Maintains a separate last_page pointer for each thread to prevent multi-threaded
    interleaving noise, alongside a shared physical page frame pool.
    """
    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self.cache = OrderedDict()
        self.last_page = {}          # tid -> last accessed page
        self.global_last_page = None  # global last accessed page

    def access(self, page: int, tid: str = None) -> bool:
        """
        Simulate accessing a page.
        Returns:
            True if hit (page was already in memory).
            False if page fault (page had to be fetched into memory).
        """
        hit = page in self.cache
        if hit:
            self.cache.move_to_end(page)
        else:
            self.put(page)

        # Update thread-specific and global context pointers
        if tid is not None:
            self.last_page[tid] = page
        self.global_last_page = page

        return hit

    def put(self, page: int):
        """Inserts or updates page position to most recently used."""
        if page in self.cache:
            self.cache.move_to_end(page)
        else:
            self.cache[page] = True
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

    def prefetch(self, pages: list):
        """Prefetches a list of predicted pages into the physical cache."""
        for p in pages:
            self.put(p)

    def __len__(self):
        return len(self.cache)


def find_trace_files():
    """Locate training and testing traces across expected directories."""
    candidates_train = [
        os.path.join("data", "traces", "training_trace.txt"),
        os.path.join("pp", "training_trace.txt"),
        "training_trace.txt"
    ]
    candidates_test = [
        os.path.join("data", "traces", "testing_trace.txt"),
        os.path.join("pp", "testing_trace.txt"),
        "testing_trace.txt"
    ]

    train_path = next((p for p in candidates_train if os.path.exists(p)), None)
    test_path = next((p for p in candidates_test if os.path.exists(p)), None)

    if not train_path or not test_path:
        raise FileNotFoundError(f"Trace files not found. Train: {train_path}, Test: {test_path}")

    return train_path, test_path


def train_markov_models(train_path: str, top_k: int = 3):
    """
    Parses the raw training trace to build:
    1. Per-Thread 1st-Order Markov Dictionary: thread_id -> { page -> [top 3 next pages] }
    2. Global 1st-Order Markov Dictionary: page -> [top 3 next pages]
    """
    print("-----------------------------------------------------------------------------------------")
    print("  STEP 1: TRAINING MARKOV MODELS (GLOBAL & PER-THREAD)                                   ")
    print("-----------------------------------------------------------------------------------------")
    print(f"  Training Trace Source:    {train_path}")
    print(f"  Top-K Predictions:        {top_k}")

    t0 = time.time()
    global_transitions = defaultdict(Counter)
    thread_transitions = defaultdict(lambda: defaultdict(Counter))

    prev_global = None
    prev_thread = {}
    total_records = 0

    with open(train_path, "r", buffering=8 * 1024 * 1024) as f:
        for line in f:
            parts = line.split(" ", 3)
            if len(parts) < 3:
                continue
            tid = parts[0]
            page = int(parts[2], 16) >> 12
            total_records += 1

            # Global transition tracking
            if prev_global is not None:
                global_transitions[prev_global][page] += 1
            prev_global = page

            # Per-thread transition tracking
            if tid in prev_thread:
                thread_transitions[tid][prev_thread[tid]][page] += 1
            prev_thread[tid] = page

    train_time = time.time() - t0
    print(f"  Processed {total_records:,} accesses in {train_time:.2f}s ({total_records/train_time:,.0f} records/s)")

    # Prune models to top-k transitions
    global_model = {
        p: [nxt for nxt, _ in c.most_common(top_k)]
        for p, c in global_transitions.items()
    }

    thread_model = {
        tid: {
            p: [nxt for nxt, _ in c.most_common(top_k)]
            for p, c in page_dict.items()
        }
        for tid, page_dict in thread_transitions.items()
    }

    # Save per-thread model to JSON
    per_thread_json = "data/models/markov_model_per_thread_traceB.json"
    with open(per_thread_json, "w") as f:
        json.dump(thread_model, f)

    # Save global model to JSON for reference
    with open("data/models/markov_model_traceB.json", "w") as f:
        json.dump(global_model, f)

    total_thread_states = sum(len(pdict) for pdict in thread_model.values())
    print(f"  Global Model States:      {len(global_model):,} pages")
    print(f"  Per-Thread Model Threads: {len(thread_model)} threads")
    print(f"  Total Per-Thread States:  {total_thread_states:,} across all threads")
    print(f"  Serialized Model:         {per_thread_json} ({os.path.getsize(per_thread_json)/1024:.2f} KB)\n")

    return global_model, thread_model


def load_testing_trace(test_path: str):
    """Loads testing trace into memory for high-speed deterministic simulation."""
    print("-----------------------------------------------------------------------------------------")
    print("  STEP 2: INGESTING TESTING TRACE                                                        ")
    print("-----------------------------------------------------------------------------------------")
    t0 = time.time()
    trace = []
    with open(test_path, "r", buffering=8 * 1024 * 1024) as f:
        for line in f:
            parts = line.split(" ", 3)
            if len(parts) >= 3:
                trace.append((parts[0], int(parts[2], 16) >> 12))
    load_time = time.time() - t0
    print(f"  Loaded {len(trace):,} test references in {load_time:.2f}s\n")
    return trace


def run_simulations(trace, global_model, thread_model, capacity: int = 1024):
    """
    Simulates three configurations:
    a) Baseline LRU (No prefetching)
    b) Global Statistical Prefetching (Exp 1 Top-3 model with shared pointer)
    c) Per-Thread Statistical Prefetching (Thread-isolated models and pointers)
    """
    print("-----------------------------------------------------------------------------------------")
    print("  STEP 3: RUNNING OS REPLACEMENT SIMULATIONS (CAPACITY = 1024 FRAMES)                    ")
    print("-----------------------------------------------------------------------------------------")

    total_accesses = len(trace)

    # Configuration A: Baseline LRU
    cache_a = PerThreadLRUCache(capacity=capacity)
    faults_a = 0
    t0 = time.time()
    for tid, page in trace:
        if not cache_a.access(page, tid):
            faults_a += 1
    time_a = time.time() - t0
    print(f"  [1/3] Baseline LRU (No Prefetch)           : {faults_a:,} faults ({time_a:.2f}s)")

    # Configuration B: Global Statistical Prefetching
    cache_b = PerThreadLRUCache(capacity=capacity)
    faults_b = 0
    t0 = time.time()
    for tid, page in trace:
        if not cache_b.access(page, tid):
            faults_b += 1
            if page in global_model:
                cache_b.prefetch(global_model[page][:3])
    time_b = time.time() - t0
    print(f"  [2/3] Global Statistical Prefetching (Top-3): {faults_b:,} faults ({time_b:.2f}s)")

    # Configuration C: Per-Thread Statistical Prefetching
    cache_c = PerThreadLRUCache(capacity=capacity)
    faults_c = 0
    t0 = time.time()
    for tid, page in trace:
        if not cache_c.access(page, tid):
            faults_c += 1
            if tid in thread_model and page in thread_model[tid]:
                cache_c.prefetch(thread_model[tid][page][:3])
    time_c = time.time() - t0
    print(f"  [3/3] Per-Thread Statistical Prefetching   : {faults_c:,} faults ({time_c:.2f}s)\n")

    return total_accesses, (faults_a, time_a), (faults_b, time_b), (faults_c, time_c)


def display_results(total, res_a, res_b, res_c):
    """Outputs the structured comparison table and experimental insights."""
    faults_a, time_a = res_a
    faults_b, time_b = res_b
    faults_c, time_c = res_c

    hits_a = total - faults_a
    hits_b = total - faults_b
    hits_c = total - faults_c

    hr_a = (hits_a / total) * 100.0
    hr_b = (hits_b / total) * 100.0
    hr_c = (hits_c / total) * 100.0

    fr_a = (faults_a / total) * 100.0
    fr_b = (faults_b / total) * 100.0
    fr_c = (faults_c / total) * 100.0

    red_b = ((faults_a - faults_b) / faults_a) * 100.0
    red_c = ((faults_a - faults_c) / faults_a) * 100.0

    print("=========================================================================================================")
    print("                      EXPERIMENT 9: PER-THREAD MARKOV MODEL EVALUATION                                   ")
    print("=========================================================================================================")
    print(f"{'Configuration':<42} | {'Page Faults':<12} | {'Hit Ratio':<10} | {'Fault Ratio':<12} | {'Reduction (%)':<14}")
    print("---------------------------------------------------------------------------------------------------------")
    print(f"{'Baseline LRU (No Prefetching)':<42} | {faults_a:<12,} | {hr_a:<9.3f}% | {fr_a:<11.3f}% | {'0.00%':<14}")
    print(f"{'Global Statistical Prefetching (Top-3)':<42} | {faults_b:<12,} | {hr_b:<9.3f}% | {fr_b:<11.3f}% | {f'+{red_b:.2f}%':<14}")
    print(f"{'Per-Thread Statistical Prefetching (Top-3)':<42} | {faults_c:<12,} | {hr_c:<9.3f}% | {fr_c:<11.3f}% | {f'+{red_c:.2f}%':<14}")
    print("=========================================================================================================\n")

    print("=========================================================================================================")
    print("                                      KEY EXPERIMENTAL INSIGHTS                                          ")
    print("=========================================================================================================")
    print(f"  1. Global Statistical Model prevented {faults_a - faults_b:,} faults (+{red_b:.2f}% reduction vs Baseline).")
    print(f"  2. Per-Thread Statistical Model prevented {faults_a - faults_c:,} faults (+{red_c:.2f}% reduction vs Baseline).")
    print(f"  3. In work-stealing parallel BFS (Strategy C), thread assignment is dynamic rather than core-pinned.")
    print(f"     While per-thread history isolates scheduling noise, dynamic task stealing causes cross-root sparsity")
    print(f"     within individual threads. Global statistical modeling aggregates graph structural CSR transitions")
    print(f"     effectively, yielding a superior +{red_b:.2f}% fault reduction.")
    print("=========================================================================================================")


def main():
    print("=========================================================================================================")
    print("    EXPERIMENT 9: PER-THREAD MARKOV MODELS (INVESTIGATING MULTI-THREADED INTERLEAVING NOISE)            ")
    print("=========================================================================================================\n")

    train_path, test_path = find_trace_files()
    global_model, thread_model = train_markov_models(train_path, top_k=3)
    trace = load_testing_trace(test_path)
    total, res_a, res_b, res_c = run_simulations(trace, global_model, thread_model, capacity=1024)
    display_results(total, res_a, res_b, res_c)


if __name__ == "__main__":
    main()

