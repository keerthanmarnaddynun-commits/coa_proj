from collections import OrderedDict, defaultdict, Counter

# Let's test if ignoring self-transitions gives 67,645 and 63,331!
chain_no_self = defaultdict(Counter)
prev = None
with open("data/pages/cleaned_training_pages.txt") as f:
    for line in f:
        p = int(line.strip())
        if prev is not None and prev != p:
            chain_no_self[prev][p] += 1
        prev = p

model_no_self = {p: [nxt for nxt, _ in c.most_common(3)] for p, c in chain_no_self.items()}

class LRUCache:
    def __init__(self, capacity=1024):
        self.capacity = capacity
        self.cache = OrderedDict()
    def access(self, p):
        if p in self.cache:
            self.cache.move_to_end(p)
            return True
        if len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        self.cache[p] = True
        return False
    def prefetch(self, pages):
        for p in pages:
            if p in self.cache:
                self.cache.move_to_end(p)
            else:
                if len(self.cache) >= self.capacity:
                    self.cache.popitem(last=False)
                self.cache[p] = True

for k in [1, 2, 3]:
    c = LRUCache(1024)
    faults = 0
    with open("data/pages/cleaned_testing_pages.txt") as f:
        for line in f:
            p = int(line.strip())
            if not c.access(p):
                faults += 1
                if p in model_no_self:
                    c.prefetch(model_no_self[p][:k])
    print(f"No self transitions, k={k}: faults={faults}")

