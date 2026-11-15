# Let's verify operations 25-40 of Root 0 vs cleaned_training_pages.txt
# and operations 25-40 of Root 1 vs cleaned_testing_pages.txt

page_to_array = {
    11421696: "distances",
    11421952: "frontier",
    11422208: "row_pointers",
    5051392:  "column_indices",
    11420672: "next_frontier",
}

with open("data/pages/cleaned_training_pages.txt") as f:
    clean_train = [int(f.readline().strip()) for _ in range(50)]

with open("data/pages/cleaned_testing_pages.txt") as f:
    clean_test = [int(f.readline().strip()) for _ in range(50)]

import sim_bfs
trace0 = sim_bfs.simulate_bfs_trace(0)
trace1 = sim_bfs.simulate_bfs_trace(1)

print("=== VERIFYING TRAINING TRACE (ROOT 0) ===")
for i in range(25, 42):
    expected_arr = trace0[i][1]
    actual_page = clean_train[i]
    actual_arr = page_to_array.get(actual_page, "unknown")
    match = (expected_arr == actual_arr)
    print(f"Op {i:2d}: Expected {expected_arr:<15} ({trace0[i][0]} {trace0[i][2]}) | Actual Page {actual_page} ({actual_arr}) | Match: {match}")

print("\n=== VERIFYING TESTING TRACE (ROOT 1) ===")
for i in range(25, 42):
    expected_arr = trace1[i][1]
    actual_page = clean_test[i]
    actual_arr = page_to_array.get(actual_page, "unknown")
    match = (expected_arr == actual_arr)
    print(f"Op {i:2d}: Expected {expected_arr:<15} ({trace1[i][0]} {trace1[i][2]}) | Actual Page {actual_page} ({actual_arr}) | Match: {match}")

