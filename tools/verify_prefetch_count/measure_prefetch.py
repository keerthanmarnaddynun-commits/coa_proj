import os
import json
import time
from collections import OrderedDict

class InstrumentedLRUCache:
    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self.cache = OrderedDict()  # page -> is_dirty (bool)
        
        # Eviction stats
        self.clean_evictions = 0
        self.dirty_evictions = 0
        
        # Prefetch tracking stats
        self.total_prefetches = 0      # N_pref: non-resident pages loaded
        self.prefetch_hits = 0          # N_used: referenced before eviction
        self.prefetch_waste = 0         # N_unused: evicted without reference
        self.prefetch_skipped = 0       # Candidates already resident
        self.prefetched_pages = set()   # Currently resident prefetched pages awaiting first use
        self.total_candidates = 0       # Total proposed candidates

    def access(self, page: int, is_write: bool = False) -> bool:
        if page in self.cache:
            self.cache.move_to_end(page)
            if is_write:
                self.cache[page] = True
            if page in self.prefetched_pages:
                self.prefetch_hits += 1
                self.prefetched_pages.remove(page)
            return True

        # Demand Miss / Page Fault
        if len(self.cache) >= self.capacity:
            evicted, is_dirty = self.cache.popitem(last=False)
            if is_dirty:
                self.dirty_evictions += 1
            else:
                self.clean_evictions += 1
            if evicted in self.prefetched_pages:
                self.prefetch_waste += 1
                self.prefetched_pages.remove(evicted)

        self.cache[page] = is_write
        return False

    def prefetch(self, pages: list):
        for p in pages:
            self.total_candidates += 1
            if p in self.cache:
                self.cache.move_to_end(p)
                self.prefetch_skipped += 1
            else:
                self.total_prefetches += 1
                if len(self.cache) >= self.capacity:
                    evicted, is_dirty = self.cache.popitem(last=False)
                    if is_dirty:
                        self.dirty_evictions += 1
                    else:
                        self.clean_evictions += 1
                    if evicted in self.prefetched_pages:
                        self.prefetch_waste += 1
                        self.prefetched_pages.remove(evicted)
                self.cache[p] = False
                self.prefetched_pages.add(p)


def run_trace_a():
    print("=================================================================")
    print("RUNNING TRACE A EVALUATION")
    print("=================================================================")
    trace_path = "data/pages/cleaned_testing_pages.txt"
    model_path = "data/models/markov_model_traceA.json"
    
    with open(model_path, "r") as f:
        raw_model = json.load(f)
    model = {int(k): [int(x) for x in v] for k, v in raw_model.items()}
    
    # Baseline
    cache_base = InstrumentedLRUCache(capacity=1024)
    faults_base = 0
    total_refs = 0
    t0 = time.time()
    with open(trace_path, "r", buffering=8*1024*1024) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = int(line)
            total_refs += 1
            if not cache_base.access(p, False):
                faults_base += 1
    t_base = time.time() - t0
    print(f"Trace A Baseline: Faults={faults_base:,}, Total={total_refs:,} in {t_base:.2f}s")
    
    # Prefetching Top-3
    cache_pref = InstrumentedLRUCache(capacity=1024)
    faults_pref = 0
    t0 = time.time()
    with open(trace_path, "r", buffering=8*1024*1024) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            p = int(line)
            if not cache_pref.access(p, False):
                faults_pref += 1
                if p in model:
                    cache_pref.prefetch(model[p][:3])
    t_pref = time.time() - t0
    print(f"Trace A Top-3: Faults={faults_pref:,} in {t_pref:.2f}s")
    
    n_pref = cache_pref.total_prefetches
    n_used = cache_pref.prefetch_hits
    n_unused = cache_pref.prefetch_waste
    n_skipped = cache_pref.prefetch_skipped
    n_candidates = cache_pref.total_candidates
    still_resident = len(cache_pref.prefetched_pages)
    
    prec = (n_used / n_pref) * 100 if n_pref > 0 else 0
    waste = (n_unused / n_pref) * 100 if n_pref > 0 else 0
    
    print(f"N_pref: {n_pref:,}")
    print(f"N_used: {n_used:,}")
    print(f"N_unused: {n_unused:,}")
    print(f"N_skipped (already resident): {n_skipped:,}")
    print(f"Total candidates proposed: {n_candidates:,}")
    print(f"Still resident at EOF: {still_resident}")
    print(f"Precision: {prec:.2f}%")
    print(f"Waste: {waste:.2f}%")
    return {
        "faults_base": faults_base,
        "faults_pref": faults_pref,
        "n_pref": n_pref,
        "n_used": n_used,
        "n_unused": n_unused,
        "n_skipped": n_skipped,
        "n_candidates": n_candidates,
        "still_resident": still_resident,
        "precision": prec,
        "waste": waste,
        "total_refs": total_refs
    }


def run_trace_b():
    print("\n=================================================================")
    print("RUNNING TRACE B EVALUATION")
    print("=================================================================")
    test_candidates = [
        os.path.join("data", "traces", "testing_trace.txt"),
        os.path.join("pp", "testing_trace.txt"),
        "testing_trace.txt"
    ]
    test_path = next((p for p in test_candidates if os.path.exists(p)), None)
    model_path = "data/models/markov_model_traceB.json"
    
    with open(model_path, "r") as f:
        raw_model = json.load(f)
    model = {int(k): [int(x) for x in v] for k, v in raw_model.items()}
    
    # Load trace
    print(f"Loading Trace B from {test_path}...")
    trace = []
    t0 = time.time()
    with open(test_path, "r", buffering=8*1024*1024) as f:
        for line in f:
            parts = line.split(" ", 3)
            if len(parts) >= 3:
                op = parts[1]
                page = int(parts[2], 16) >> 12
                trace.append((page, op.upper() == "WRITE"))
            elif len(parts) == 2:
                op = parts[0]
                page = int(parts[1], 16) >> 12
                trace.append((page, op.upper() == "WRITE"))
    print(f"Loaded {len(trace):,} references in {time.time() - t0:.2f}s")
    total_refs = len(trace)
    
    # Baseline
    cache_base = InstrumentedLRUCache(capacity=1024)
    faults_base = 0
    t0 = time.time()
    for page, is_write in trace:
        if not cache_base.access(page, is_write):
            faults_base += 1
    t_base = time.time() - t0
    base_evictions = cache_base.clean_evictions + cache_base.dirty_evictions
    base_hr = ((total_refs - faults_base) / total_refs) * 100
    print(f"Trace B Baseline: Faults={faults_base:,}, DirtyEvictions={cache_base.dirty_evictions:,}, TotalEvictions={base_evictions:,}, HitRate={base_hr:.3f}% in {t_base:.2f}s")
    
    # Global Top-3 Prefetching
    cache_pref = InstrumentedLRUCache(capacity=1024)
    faults_pref = 0
    t0 = time.time()
    for page, is_write in trace:
        if not cache_pref.access(page, is_write):
            faults_pref += 1
            if page in model:
                cache_pref.prefetch(model[page][:3])
    t_pref = time.time() - t0
    pref_evictions = cache_pref.clean_evictions + cache_pref.dirty_evictions
    pref_hr = ((total_refs - faults_pref) / total_refs) * 100
    print(f"Trace B Top-3: Faults={faults_pref:,}, DirtyEvictions={cache_pref.dirty_evictions:,}, TotalEvictions={pref_evictions:,}, HitRate={pref_hr:.3f}% in {t_pref:.2f}s")
    
    n_pref = cache_pref.total_prefetches
    n_used = cache_pref.prefetch_hits
    n_unused = cache_pref.prefetch_waste
    n_skipped = cache_pref.prefetch_skipped
    n_candidates = cache_pref.total_candidates
    still_resident = len(cache_pref.prefetched_pages)
    
    prec = (n_used / n_pref) * 100 if n_pref > 0 else 0
    waste = (n_unused / n_pref) * 100 if n_pref > 0 else 0
    
    print(f"N_pref: {n_pref:,}")
    print(f"N_used: {n_used:,}")
    print(f"N_unused: {n_unused:,}")
    print(f"N_skipped (already resident): {n_skipped:,}")
    print(f"Total candidates proposed: {n_candidates:,}")
    print(f"Still resident at EOF: {still_resident}")
    print(f"Precision: {prec:.2f}%")
    print(f"Waste: {waste:.2f}%")
    
    return {
        "faults_base": faults_base,
        "faults_pref": faults_pref,
        "dirty_base": cache_base.dirty_evictions,
        "dirty_pref": cache_pref.dirty_evictions,
        "clean_base": cache_base.clean_evictions,
        "clean_pref": cache_pref.clean_evictions,
        "evictions_base": base_evictions,
        "evictions_pref": pref_evictions,
        "hr_base": base_hr,
        "hr_pref": pref_hr,
        "n_pref": n_pref,
        "n_used": n_used,
        "n_unused": n_unused,
        "n_skipped": n_skipped,
        "n_candidates": n_candidates,
        "still_resident": still_resident,
        "precision": prec,
        "waste": waste,
        "total_refs": total_refs
    }

if __name__ == "__main__":
    res_a = run_trace_a()
    res_b = run_trace_b()
    
    # Save results to json for safety
    with open("tools/verify_prefetch_count/results.json", "w") as f:
        json.dump({"trace_a": res_a, "trace_b": res_b}, f, indent=2)

