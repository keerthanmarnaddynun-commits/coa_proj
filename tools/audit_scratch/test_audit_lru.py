from collections import OrderedDict
import json

class LRU:
    def __init__(self, cap):
        self.cap = cap
        self.c = OrderedDict()
    def access(self, p):
        if p in self.c:
            self.c.move_to_end(p)
            return True
        if len(self.c) >= self.cap:
            self.c.popitem(last=False)
        self.c[p] = True
        return False
    def prefetch(self, pages):
        for p in pages:
            if p in self.c:
                self.c.move_to_end(p)
            else:
                if len(self.c) >= self.cap:
                    self.c.popitem(last=False)
                self.c[p] = True

with open("tools/audit_scratch/markov_model_traceA_rebuild.json") as f:
    raw = json.load(f)
model = {int(k): [int(nxt) for nxt in v.keys()] for k, v in raw.items()}

# Test on cleaned_testing_pages.txt
for k in [0, 1, 2, 3]:
    c = LRU(1024)
    faults = 0
    with open("data/pages/cleaned_testing_pages.txt") as f:
        for line in f:
            p = int(line.strip())
            if not c.access(p):
                faults += 1
                if k > 0 and p in model:
                    c.prefetch(model[p][:k])
    print(f"LRU class with k={k}: faults={faults}")

