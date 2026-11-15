import os
import re

extensions = ('.md', '.c', '.h', '.py', '.txt') # exclude huge txt files
huge_files = {'cleaned_training_pages.txt', 'cleaned_testing_pages.txt', 'training_trace.txt', 'testing_trace.txt', 'Amazon0302.txt'}

results = []
for root, dirs, files in os.walk("."):
    if "audit_scratch" in root or ".git" in root or "__pycache__" in root:
        continue
    for f in files:
        if f in huge_files or f.endswith(".json") or f.endswith(".exe") or f.endswith(".o") or f.endswith(".pyc"):
            continue
        filepath = os.path.join(root, f)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as fp:
                for lno, line in enumerate(fp, 1):
                    if re.search(r'\b(root|test_root|train_root|training_trace|testing_trace|BFSRoot|root_vertex)\b', line, re.IGNORECASE):
                        results.append((filepath, lno, line.strip()))
        except Exception as e:
            pass

print(f"Found {len(results)} matches:")
for path, lno, line in results:
    print(f"{path}:{lno}: {line}")

