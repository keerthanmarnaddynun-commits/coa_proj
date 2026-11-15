import os
import datetime

files = [
    "data/pages/cleaned_training_pages.txt",
    "data/pages/cleaned_testing_pages.txt",
    "data/traces/training_trace.txt",
    "data/traces/testing_trace.txt",
    "pp/training_trace.txt",
    "pp/testing_trace.txt",
    "data/models/markov_model.json",
    "data/models/markov_model_per_thread.json",
    "data/models/markov_model_top5.json",
    "data/models/markov_model_order2.json",
    "data/models/markov_model_order2_top5.json",
    "data/models/graph_oracle.json"
]

print(f"{'File':<35} | {'Size (bytes)':<12} | {'Modified Time':<25}")
print("-" * 78)
for f in files:
    if os.path.exists(f):
        stat = os.stat(f)
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{f:<35} | {stat.st_size:<12} | {mtime:<25}")
    else:
        print(f"{f:<35} | NOT FOUND")

