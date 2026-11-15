import sys
sys.stdout.reconfigure(encoding='utf-8')

# Read first 10,000 pages of cleaned_training_pages.txt and cleaned_testing_pages.txt
with open("data/pages/cleaned_training_pages.txt") as f:
    clean_train = [int(f.readline().strip()) for _ in range(10000)]

with open("data/pages/cleaned_testing_pages.txt") as f:
    clean_test = [int(f.readline().strip()) for _ in range(10000)]

print(f"Total read: {len(clean_train)} train, {len(clean_test)} test")

# Distinct pages in first N
intervals = [10, 50, 100, 200, 500, 1000, 5000, 10000]
print(f"{'N references':<15} | {'Distinct Train Pages':<22} | {'Distinct Test Pages':<22}")
print("-" * 65)
for n in intervals:
    dt = len(set(clean_train[:n]))
    de = len(set(clean_test[:n]))
    print(f"{n:<15} | {dt:<22} | {de:<22}")

# Compare first 200 page numbers
diffs_200 = sum(1 for a, b in zip(clean_train[:200], clean_test[:200]) if a != b)
print(f"\nDifferences in first 200 pages between cleaned_train and cleaned_test: {diffs_200} / 200")

print("\nFirst 30 pages comparison:")
print(f"{'Idx':<5} | {'Cleaned Train':<15} | {'Cleaned Test':<15} | {'Match?':<8}")
print("-" * 50)
for i in range(30):
    match = "YES" if clean_train[i] == clean_test[i] else "NO"
    print(f"{i:<5} | {clean_train[i]:<15} | {clean_test[i]:<15} | {match:<8}")

# Check when the first difference occurs
first_diff = None
for i in range(10000):
    if clean_train[i] != clean_test[i]:
        first_diff = i
        break
print(f"\nFirst difference occurs at index: {first_diff}")
if first_diff is not None:
    print(f"At index {first_diff}: train = {clean_train[first_diff]}, test = {clean_test[first_diff]}")

