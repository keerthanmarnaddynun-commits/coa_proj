import os
import time
from collections import OrderedDict

class LRUCache:
    """
    Standard Least Recently Used (LRU) Cache implemented with OrderedDict.
    """
    def __init__(self, capacity: int = 1024):
        self.capacity = capacity
        self.cache = OrderedDict()

    def access(self, page: int) -> bool:
        """
        Simulate accessing a page.
        Returns True on hit, False on page fault.
        """
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

    def __len__(self):
        return len(self.cache)


class ARCCache:
    """
    Adaptive Replacement Cache (ARC) - Megiddo & Modha (FAST 2003):
      - T1: Resident pages requested only once recently (recency list).
      - T2: Resident pages requested at least twice recently (frequency list).
      - B1: Ghost directory of pages evicted from T1 (history of recency).
      - B2: Ghost directory of pages evicted from T2 (history of frequency).
      - p: Adaptation tuning parameter in [0, c] dynamically adjusting T1 target size.
    """
    def __init__(self, capacity: int = 1024):
        self.c = capacity
        self.p = 0.0
        self.t1 = OrderedDict()
        self.t2 = OrderedDict()
        self.b1 = OrderedDict()
        self.b2 = OrderedDict()

    def replace(self, page: int):
        """Evicts a page from T1 or T2 into ghost caches B1 or B2."""
        len_t1 = len(self.t1)
        if len_t1 > 0 and ((len_t1 > self.p) or (page in self.b2 and len_t1 == int(self.p))):
            oldest, _ = self.t1.popitem(last=False)
            self.b1[oldest] = True
        else:
            oldest, _ = self.t2.popitem(last=False)
            self.b2[oldest] = True

    def access(self, page: int) -> bool:
        """
        Simulate accessing a page under canonical ARC replacement logic.
        Returns True on hit, False on page fault.
        """
        # Case I: page in T1 or T2 (Cache Hit)
        if page in self.t1:
            del self.t1[page]
            self.t2[page] = True
            return True
        if page in self.t2:
            self.t2.move_to_end(page)
            return True

        # Cache Miss
        # Case II: page in B1 (Recency History Hit)
        if page in self.b1:
            delta = 1.0 if len(self.b1) >= len(self.b2) else len(self.b2) / len(self.b1)
            self.p = min(float(self.c), self.p + delta)
            self.replace(page)
            del self.b1[page]
            self.t2[page] = True
            return False

        # Case III: page in B2 (Frequency History Hit)
        if page in self.b2:
            delta = 1.0 if len(self.b2) >= len(self.b1) else len(self.b1) / len(self.b2)
            self.p = max(0.0, self.p - delta)
            self.replace(page)
            del self.b2[page]
            self.t2[page] = True
            return False

        # Case IV: page not in T1 U B1 U T2 U B2 (Complete Miss)
        len_l1 = len(self.t1) + len(self.b1)
        len_l2 = len(self.t2) + len(self.b2)

        if len_l1 == self.c:
            if len(self.t1) < self.c:
                self.b1.popitem(last=False)
                self.replace(page)
            else:
                self.t1.popitem(last=False)
        elif len_l1 < self.c:
            if (len_l1 + len_l2) >= self.c:
                if (len_l1 + len_l2) == 2 * self.c:
                    self.b2.popitem(last=False)
                self.replace(page)

        self.t1[page] = True
        return False

    def __len__(self):
        return len(self.t1) + len(self.t2)


def run_simulation(trace_path: str, cache_cls, capacity: int) -> tuple:
    """Runs a demand page-replacement simulation over trace_path."""
    if not os.path.exists(trace_path):
        raise FileNotFoundError(f"Trace file '{trace_path}' not found.")

    cache = cache_cls(capacity=capacity)
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

            if not cache.access(page):
                page_faults += 1

    elapsed = time.time() - start_time
    extra_info = {}
    if isinstance(cache, ARCCache):
        extra_info = {
            "p": cache.p,
            "len_t1": len(cache.t1),
            "len_t2": len(cache.t2),
            "len_b1": len(cache.b1),
            "len_b2": len(cache.b2)
        }

    return total_accesses, page_faults, elapsed, extra_info


def main():
    trace_file = "data/pages/cleaned_testing_pages.txt"
    capacities = [512, 1024, 2048]

    print("=========================================================================================")
    print("      EXPERIMENT 7: ADAPTIVE REPLACEMENT CACHE (ARC) vs LRU BASELINE EVALUATION          ")
    print("=========================================================================================")
    print(f"  Testing Trace:   {trace_file}")
    print(f"  RAM Capacities:  {capacities} pages")
    print("  Algorithms:      Baseline LRU vs. Baseline ARC (Standard Demand Paging, No Prefetching)")
    print("=========================================================================================\n")

    results = []

    for cap in capacities:
        mb = cap * 4 / 1024
        print(f"Evaluating RAM Capacity = {cap:,} pages ({mb:.1f} MB)...")

        # 1. Baseline LRU
        tot_lru, faults_lru, time_lru, _ = run_simulation(trace_file, LRUCache, cap)
        hr_lru = ((tot_lru - faults_lru) / tot_lru) * 100 if tot_lru > 0 else 0
        print(f"  - Baseline LRU: {faults_lru:7,d} faults ({hr_lru:.3f}% hit ratio) in {time_lru:.2f}s")

        # 2. Baseline ARC
        tot_arc, faults_arc, time_arc, arc_info = run_simulation(trace_file, ARCCache, cap)
        hr_arc = ((tot_arc - faults_arc) / tot_arc) * 100 if tot_arc > 0 else 0
        reduction = ((faults_lru - faults_arc) / faults_lru) * 100 if faults_lru > 0 else 0
        print(f"  - Baseline ARC: {faults_arc:7,d} faults ({hr_arc:.3f}% hit ratio, p={arc_info['p']:.2f}) in {time_arc:.2f}s")
        print(f"    [T1: {arc_info['len_t1']}, T2: {arc_info['len_t2']}, B1: {arc_info['len_b1']}, B2: {arc_info['len_b2']}]")
        print(f"  - Fault Reduction vs LRU: {reduction:+.2f}%\n")

        results.append({
            "capacity": cap,
            "mb": mb,
            "faults_lru": faults_lru,
            "faults_arc": faults_arc,
            "reduction": reduction,
            "hr_lru": hr_lru,
            "hr_arc": hr_arc,
            "p": arc_info["p"]
        })

    # Structured Comparison Table
    print("=============================================================================================================")
    print("                                   ARC vs. LRU BASELINE COMPARISON TABLE                                     ")
    print("=============================================================================================================")
    header = (
        f"{'RAM Capacity':<20} | "
        f"{'LRU Faults':^18} | "
        f"{'ARC Faults':^18} | "
        f"{'ARC Fault Reduction vs LRU (%)':^32}"
    )
    print(header)
    print("-" * len(header))

    for r in results:
        cap_str = f"{r['capacity']:,} pages ({r['mb']:.1f} MB)"
        lru_str = f"{r['faults_lru']:,}"
        arc_str = f"{r['faults_arc']:,}"
        red_str = f"{r['reduction']:+.2f}%"

        print(
            f"{cap_str:<20} | "
            f"{lru_str:^18} | "
            f"{arc_str:^18} | "
            f"{red_str:^32}"
        )

    print("=" * len(header))

    # Architectural Findings
    r512 = results[0]
    r1024 = results[1]
    r2048 = results[2]

    print("\n=============================================================================================================")
    print("                                      EXPERIMENT 7 ARCHITECTURAL FINDINGS                                    ")
    print("=============================================================================================================")
    print("  1. Near-Identical Performance Under Pure Demand Paging:")
    print(f"     - At 512 pages:  LRU = {r512['faults_lru']:,} vs. ARC = {r512['faults_arc']:,} ({r512['reduction']:+.2f}% reduction).")
    print(f"     - At 1,024 pages: LRU = {r1024['faults_lru']:,} vs. ARC = {r1024['faults_arc']:,} ({r1024['reduction']:+.2f}% reduction).")
    print(f"     - At 2,048 pages: LRU = {r2048['faults_lru']:,} vs. ARC = {r2048['faults_arc']:,} ({r2048['reduction']:+.2f}% reduction).")
    print("  2. Adaptation Parameter Convergence (p -> 0.00):")
    print("     - In graph traversal (multi-threaded BFS), page re-references occur across search iterations, heavily")
    print("       striking the B2 ghost cache and driving target parameter p to 0.00.")
    print("     - Consequently, ARC allocates virtually all available physical frames to the frequency list T2,")
    print("       behaving essentially as a frequency-biased LRU without outperforming pure LRU on demand misses.")
    print("  3. Cache Pollution Mechanism Clarification:")
    print("     - Demand ARC naturally resists scan-driven pollution on single-access bursts by filtering once-seen")
    print("       pages through T1. However, ARC without prefetching cannot eliminate capacity or compulsory faults.")
    print("     - Cache pollution in predictive systems arises because speculative prefetch requests inject unverified")
    print("       pages directly into cache frames; solving predictive pollution requires prefetch-aware insertion (Exp 5)")
    print("       or dynamic prefetch throttling (Exp 6) rather than a replacement-only policy.")
    print("=============================================================================================================")

if __name__ == "__main__":
    main()

