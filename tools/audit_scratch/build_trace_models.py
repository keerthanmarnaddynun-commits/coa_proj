import os
import shutil
import json
from collections import defaultdict, Counter

targets = [
    "data/models/markov_model_traceA.json",
    "data/models/markov_model_traceB.json",
    "data/models/markov_model_per_thread_traceB.json",
    "data/models/markov_model_top5_traceA.json"
]

print("Checking target existence...")
for t in targets:
    if os.path.exists(t):
        raise FileExistsError(f"Target file already exists: {t}. Aborting!")

# Task 1: Create markov_model_traceA.json using exact phase2_train_model.py logic
print("Training markov_model_traceA.json from cleaned_training_pages.txt...")
markov_chain = defaultdict(Counter)
transition_count = 0
prev_page = None

with open("data/pages/cleaned_training_pages.txt", "r") as infile:
    for line in infile:
        line = line.strip()
        if not line: continue
        current_page = int(line)
        if prev_page is not None:
            markov_chain[prev_page][current_page] += 1
            transition_count += 1
        prev_page = current_page

pruned_model = {}
for page, next_counts in markov_chain.items():
    pruned_model[str(page)] = {
        str(nxt_page): count
        for nxt_page, count in next_counts.most_common(3)
    }

with open("data/models/markov_model_traceA.json", "w") as outfile:
    json.dump(pruned_model, outfile, indent=2)

size_a = os.path.getsize("data/models/markov_model_traceA.json")
print(f"Created markov_model_traceA.json:")
print(f"  States: {len(pruned_model):,}")
print(f"  Transitions: {transition_count:,}")
print(f"  File Size: {size_a:,} bytes")

# Task 2: Create markov_model_traceB.json and markov_model_per_thread_traceB.json
print("\nCopying Trace B models...")
shutil.copyfile("data/models/markov_model.json", "data/models/markov_model_traceB.json")
shutil.copyfile("data/models/markov_model_per_thread.json", "data/models/markov_model_per_thread_traceB.json")
size_b = os.path.getsize("data/models/markov_model_traceB.json")
size_b_pt = os.path.getsize("data/models/markov_model_per_thread_traceB.json")
print(f"Created markov_model_traceB.json: {size_b:,} bytes")
print(f"Created markov_model_per_thread_traceB.json: {size_b_pt:,} bytes")

# Task 3: Create markov_model_top5_traceA.json
print("\nVerifying markov_model_top5.json keys...")
with open("data/models/markov_model_top5.json") as f:
    top5_data = json.load(f)
first_key = int(list(top5_data.keys())[0])
print(f"First key in markov_model_top5.json: {first_key}")
if 10000000 < first_key < 12000000:
    print("Confirmed markov_model_top5.json is Trace A. Creating markov_model_top5_traceA.json...")
    shutil.copyfile("data/models/markov_model_top5.json", "data/models/markov_model_top5_traceA.json")
    size_top5 = os.path.getsize("data/models/markov_model_top5_traceA.json")
    print(f"Created markov_model_top5_traceA.json: {size_top5:,} bytes")
else:
    print("WARNING: markov_model_top5.json does not appear to be Trace A.")

