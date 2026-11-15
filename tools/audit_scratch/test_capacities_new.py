import os
import json
from collections import OrderedDict, defaultdict, Counter

# Load new trace
trace = []
with open("data/traces/testing_trace.txt") as f:
    for line in f:
        parts = line.split(" ", 3)
        if len(parts) >= 3:
            trace.append((parts[0], int(parts[2], 16) >> 12))

# Load new global model
with open("data/models/markov_model.json") as f:
    raw = json.load(f)
model = {int(k): [int(x) for x in v] for k, v in raw.items()}

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

# Test across capacities:
for cap in [512, 1024, 2048]:
    c_base = LRU(cap)
    c_p1 = LRU(cap)
    c_p2 = LRU(cap)
    c_p3 = LRU(cap)
    f_base, f_p1, f_p2, f_p3 = 0, 0, 0, 0
    for tid, p in trace:
        if not c_base.access(p):
            f_base += 1
        if not c_p1.access(p):
            f_p1 += 1
            if p in model:
                c_p1.prefetch(model[p][:1])
        if not c_p2.access(p):
            f_p2 += 1
            if p in model:
                c_p2.prefetch(model[p][:2])
        if not c_p3.access(p):
            f_p3 += 1
            if p in model:
                c_p3.prefetch(model[p][:3])
    print(f"Cap {cap}: Base={f_base:,}, Top1={f_p1:,}, Top2={f_p2:,}, Top3={f_p3:,}")

