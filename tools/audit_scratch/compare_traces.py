import os
import itertools

def load_cleaned(path):
    pages = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                pages.append(int(line))
    return pages

def load_raw_trace_pages(path):
    pages = []
    with open(path, "r", buffering=8*1024*1024) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            # Find memory address token (e.g. 0xae4800000)
            addr_token = None
            for p in parts:
                if p.startswith(("0x", "0X")):
                    addr_token = p
                    break
            if addr_token is None:
                addr_token = parts[2] if len(parts) >= 3 else parts[0]
            try:
                addr = int(addr_token, 16)
                pages.append(addr // 4096)
            except ValueError:
                continue
    return pages

print("Loading cleaned_testing_pages.txt...")
cleaned_test = load_cleaned("data/pages/cleaned_testing_pages.txt")
print(f"Loaded {len(cleaned_test):,} pages from cleaned_testing_pages.txt")

print("Loading cleaned_training_pages.txt...")
cleaned_train = load_cleaned("data/pages/cleaned_training_pages.txt")
print(f"Loaded {len(cleaned_train):,} pages from cleaned_training_pages.txt")

print("Checking if cleaned_test == cleaned_train...")
diff_train_test = sum(1 for a, b in zip(cleaned_test, cleaned_train) if a != b)
print(f"Differences between cleaned_test and cleaned_train: {diff_train_test}")

print("\nParsing traces/testing_trace.txt...")
raw_test_pages = load_raw_trace_pages("data/traces/testing_trace.txt")
print(f"Loaded {len(raw_test_pages):,} pages from traces/testing_trace.txt")

print("\nComparing cleaned_testing_pages.txt vs traces/testing_trace.txt:")
len1 = len(cleaned_test)
len2 = len(raw_test_pages)
print(f"Total length cleaned_testing_pages.txt: {len1:,}")
print(f"Total length raw_test_pages:            {len2:,}")

diff_count = 0
first_10_diffs = []

for idx, (p1, p2) in enumerate(zip(cleaned_test, raw_test_pages)):
    if p1 != p2:
        diff_count += 1
        if len(first_10_diffs) < 10:
            first_10_diffs.append((idx, p1, p2))

diff_count += abs(len1 - len2)

print(f"Number of differing positions: {diff_count:,}")
print(f"First 10 differing positions (0-indexed):")
for idx, p1, p2 in first_10_diffs:
    print(f"  Index {idx}: cleaned_testing={p1}, new_raw_trace={p2}")

if diff_count == 0:
    print("Conclusion: Sequences are IDENTICAL.")
elif diff_count == max(len1, len2):
    print("Conclusion: Sequences are ENTIRELY DIFFERENT.")
else:
    print(f"Conclusion: Sequences are PARTIALLY DIFFERENT (differ at {diff_count/max(len1, len2)*100:.2f}% of positions).")

