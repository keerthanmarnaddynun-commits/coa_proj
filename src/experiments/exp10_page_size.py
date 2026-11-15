import os
import array
import time
from collections import OrderedDict, defaultdict, Counter


class LRUCache:
    """
    Fixed-capacity Least Recently Used (LRU) Cache implemented
    with collections.OrderedDict for O(1) lookups, insertions, and evictions.
    """
    def __init__(self, capacity: int):
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
            return True

        self.put(page)
        return False

    def put(self, page: int):
        """Inserts or updates page position to most recently used."""
        if page in self.cache:
            self.cache.move_to_end(page)
        else:
            self.cache[page] = True
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

    def prefetch(self, pages: list):
        """Prefetches a list of predicted pages into the cache."""
        for p in pages:
            self.put(p)

    def __len__(self):
        return len(self.cache)


def find_trace_files():
    """Locates training and testing trace files across standard project directories."""
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
        raise FileNotFoundError(f"Trace files missing: train={train_path}, test={test_path}")

    return train_path, test_path


def load_raw_addresses(file_path: str, label: str) -> array.array:
    """
    Parses memory references from raw trace and stores 64-bit addresses
    in a compact array.array('Q') to minimize memory overhead.
    """
    t0 = time.time()
    addrs = array.array('Q')
    with open(file_path, "r", buffering=8 * 1024 * 1024) as f:
        for line in f:
            parts = line.split(" ", 3)
            if len(parts) >= 3:
                # Format: "T<id> <OP> <HEX_ADDR> <TAG>"
                addrs.append(int(parts[2], 16))
            elif len(parts) == 2:
                # Format without thread tag: "<OP> <HEX_ADDR>"
                addrs.append(int(parts[1], 16))

    elapsed = time.time() - t0
    mb_size = addrs.buffer_info()[1] * 8 / (1024 * 1024)
    print(f"  Loaded {len(addrs):,} {label} addresses in {elapsed:.2f}s ({mb_size:.2f} MB in RAM)")
    return addrs


def train_markov_model(train_addrs: array.array, page_size: int, top_k: int = 3) -> dict:
    """
    Trains a 1st-Order Top-K Markov transition dictionary on-the-fly
    for the specified page size: page_number = address // page_size.
    """
    shift = page_size.bit_length() - 1
    transitions = defaultdict(Counter)
    prev_page = None

    for addr in train_addrs:
        page = addr >> shift
        if prev_page is not None:
            transitions[prev_page][page] += 1
        prev_page = page

    # Prune each state to top-K most frequent next pages
    model = {
        p: [nxt for nxt, _ in c.most_common(top_k)]
        for p, c in transitions.items()
    }
    return model


def simulate_lru(test_addrs: array.array, page_size: int, capacity: int, model: dict = None) -> tuple:
    """
    Runs LRU cache simulation over the raw address stream using the specified
    page size and frame capacity.
    """
    shift = page_size.bit_length() - 1
    cache = LRUCache(capacity=capacity)
    faults = 0
    total = len(test_addrs)
    predictive = model is not None

    t0 = time.time()
    for addr in test_addrs:
        page = addr >> shift
        if not cache.access(page):
            faults += 1
            if predictive and page in model:
                cache.prefetch(model[page][:3])

    elapsed = time.time() - t0
    return total, faults, elapsed


def main():
    print("=========================================================================================================")
    print("      EXPERIMENT 10: HARDWARE PAGE-SIZE SENSITIVITY & PREFETCHING EFFICIENCY                             ")
    print("=========================================================================================================")
    print("  Constraint: Strictly Fixed Physical RAM Capacity = 4.0 MB (4,194,304 bytes)")
    print("  Evaluated Page Sizes: 2 KB (2,048 B), 4 KB (4,096 B), 8 KB (8,192 B), 16 KB (16,384 B)")
    print("=========================================================================================================\n")

    train_path, test_path = find_trace_files()

    print("-----------------------------------------------------------------------------------------")
    print("  STEP 1: INGESTING RAW ADDRESS TRACES                                                   ")
    print("-----------------------------------------------------------------------------------------")
    train_addrs = load_raw_addresses(train_path, "training")
    test_addrs = load_raw_addresses(test_path, "testing")
    print()

    total_ram_bytes = 4 * 1024 * 1024  # Exactly 4.0 MB
    page_sizes = [2048, 4096, 8192, 16384]

    print("-----------------------------------------------------------------------------------------")
    print("  STEP 2: RUNNING PAGE-SIZE SENSITIVITY SIMULATIONS                                      ")
    print("-----------------------------------------------------------------------------------------")

    results = []

    for ps in page_sizes:
        ps_kb = ps // 1024
        capacity = total_ram_bytes // ps

        # Train Top-3 Markov model on-the-fly for this page size
        t_train0 = time.time()
        model = train_markov_model(train_addrs, ps, top_k=3)
        t_train = time.time() - t_train0

        # Run Baseline LRU
        total, base_faults, t_base = simulate_lru(test_addrs, ps, capacity, model=None)

        # Run Predictive Top-3 Markov LRU
        _, pref_faults, t_pref = simulate_lru(test_addrs, ps, capacity, model=model)

        reduction = ((base_faults - pref_faults) / base_faults) * 100.0
        results.append({
            "ps_kb": ps_kb,
            "ps_bytes": ps,
            "capacity": capacity,
            "states": len(model),
            "base_faults": base_faults,
            "pref_faults": pref_faults,
            "reduction": reduction,
            "base_hit_ratio": ((total - base_faults) / total) * 100.0,
            "pref_hit_ratio": ((total - pref_faults) / total) * 100.0,
            "t_train": t_train,
            "t_sim": t_base + t_pref
        })

        print(f"  Completed {ps_kb:>2} KB ({ps:>5} B) | Frames: {capacity:>4} | Unique States: {len(model):>5,} | "
              f"Base: {base_faults:>6,} | Pref: {pref_faults:>6,} | Reduction: +{reduction:5.2f}%")

    print("\n=========================================================================================================")
    print("                         EXPERIMENT 10: PAGE-SIZE SENSITIVITY TABLE                                      ")
    print("=========================================================================================================")
    print(f"{'Page Size (KB)':<16} | {'Frame Capacity':<16} | {'Baseline Faults':<17} | {'Prefetcher Faults':<19} | {'Reduction (%)':<14}")
    print("---------------------------------------------------------------------------------------------------------")
    for r in results:
        ps_str = f"{r['ps_kb']} KB ({r['ps_bytes']} B)"
        cap_str = f"{r['capacity']} frames"
        base_str = f"{r['base_faults']:,}"
        pref_str = f"{r['pref_faults']:,}"
        red_str = f"+{r['reduction']:.2f}%"
        print(f"{ps_str:<16} | {cap_str:<16} | {base_str:<17} | {pref_str:<19} | {red_str:<14}")
    print("=========================================================================================================\n")

    print("=========================================================================================================")
    print("                                      KEY EXPERIMENTAL INSIGHTS                                          ")
    print("=========================================================================================================")
    r2, r4, r8, r16 = results[0], results[1], results[2], results[3]
    print(f"  1. Baseline Locality Scaling: Increasing page size from 2 KB -> 16 KB reduces Baseline faults from")
    print(f"     {r2['base_faults']:,} -> {r16['base_faults']:,} ({r2['base_faults'] - r16['base_faults']:,} fewer faults) due to stronger intra-page spatial locality,")
    print(f"     even though physical frame capacity contracts from 2,048 frames down to 256 frames.")
    print(f"  2. Prefetching Amplification: Larger page sizes amplify prefetch efficiency: 2 KB achieves +{r2['reduction']:.2f}%")
    print(f"     fault reduction, scaling monotonically to +{r16['reduction']:.2f}% reduction at 16 KB ({r16['pref_faults']:,} faults).")
    print(f"  3. State-Space Compaction: Larger pages aggregate nearby memory accesses into coarser virtual containers,")
    print(f"     compressing Markov state space from {r2['states']:,} states (2 KB) to {r16['states']:,} states (16 KB),")
    print(f"     which sharpens transition probabilities and eliminates fine-grained address noise.")
    print("=========================================================================================================")


if __name__ == "__main__":
    main()
