with open("data/pages/cleaned_testing_pages.txt") as f:
    print("cleaned_testing_pages.txt (first 10):")
    for _ in range(10):
        print(repr(f.readline().strip()))

print("\ntraces/testing_trace.txt (first 10):")
with open("data/traces/testing_trace.txt") as f:
    for _ in range(10):
        print(repr(f.readline().strip()))

print("\ncleaned_training_pages.txt (first 10):")
with open("data/pages/cleaned_training_pages.txt") as f:
    for _ in range(10):
        print(repr(f.readline().strip()))

print("\ntraces/training_trace.txt (first 10):")
with open("data/traces/training_trace.txt") as f:
    for _ in range(10):
        print(repr(f.readline().strip()))

