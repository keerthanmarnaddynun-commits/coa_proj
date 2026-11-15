import os
import re
import glob

print("Scanning python scripts...")
py_files = sorted(glob.glob("src/**/*.py", recursive=True) + glob.glob("tools/**/*.py", recursive=True))
for f in py_files:
    with open(f, "r", encoding="utf-8", errors="ignore") as fp:
        content = fp.read()
    
    traces = set(re.findall(r'[\w\\/\.]*trace[\w\.]*|[\w\\/\.]*cleaned[\w\.]*', content, re.IGNORECASE))
    models = set(re.findall(r'[\w\\/\.]*markov[\w\.]*|[\w\\/\.]*oracle[\w\.]*', content, re.IGNORECASE))
    
    # filter reasonable filenames
    valid_traces = [t for t in traces if any(ext in t for ext in ['.txt', '.csv', '.trace']) or 'trace' in t or 'cleaned' in t]
    valid_models = [m for m in models if '.json' in m]
    
    print(f"=== {f} ===")
    print(f"  Traces referenced: {valid_traces}")
    print(f"  Models referenced: {valid_models}")

