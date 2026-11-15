import os
import json
import time
from collections import defaultdict, Counter

def train_markov_model_top5(
    input_file="data/pages/cleaned_training_pages.txt",
    output_file="data/models/markov_model_top5.json",
    original_model_file="data/models/markov_model.json",
    top_k=5,
    log_interval=500000
):
    """
    Trains a 1st-order Markov Chain retaining the top 5 transitions per page
    for Experiment 1, and compares model size against the original top-3 model.
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"Input file '{input_file}' not found. "
            "Please ensure cleaned_training_pages.txt is in the workspace."
        )

    file_size_mb = os.path.getsize(input_file) / (1024 * 1024)
    print("=================================================================")
    print("      EXPERIMENT 1: MARKOV MODEL TRAINING (TOP 5 PREDICTIONS)    ")
    print("=================================================================")
    print(f"  Input trace:          {input_file} ({file_size_mb:.2f} MB)")
    print(f"  Output model file:    {output_file}")
    print(f"  Top transitions (k):  {top_k}")
    print("=================================================================\n")

    start_time = time.time()
    transition_count = 0
    prev_page = None

    # 1. Count transition frequencies using defaultdict(Counter)
    markov_chain = defaultdict(Counter)

    print("Step 1: Reading trace and counting transitions...")
    with open(input_file, "r", buffering=8 * 1024 * 1024) as infile:
        for line in infile:
            line = line.strip()
            if not line:
                continue

            current_page = int(line)

            if prev_page is not None:
                markov_chain[prev_page][current_page] += 1
                transition_count += 1

                if transition_count % log_interval == 0:
                    elapsed = time.time() - start_time
                    rate = transition_count / elapsed if elapsed > 0 else 0
                    print(f"  Ingested {transition_count:,} transitions ({rate:,.0f} trans/sec)...")

            prev_page = current_page

    ingest_time = time.time() - start_time
    print(f"Ingestion finished in {ingest_time:.2f}s.")
    print(f"  Total transitions:    {transition_count:,}")
    print(f"  Unique current pages: {len(markov_chain):,}\n")

    # 2. Prune transitions to top_k = 5
    print(f"Step 2: Pruning transitions to top {top_k} next pages per state...")
    prune_start = time.time()
    pruned_model = {}

    for page, next_counts in markov_chain.items():
        pruned_model[str(page)] = {
            str(nxt_page): count
            for nxt_page, count in next_counts.most_common(top_k)
        }

    prune_time = time.time() - prune_start
    print(f"Pruning finished in {prune_time:.2f}s.\n")

    # 3. Save to disk as markov_model_top5.json
    print(f"Step 3: Saving pruned model to '{output_file}'...")
    with open(output_file, "w") as outfile:
        json.dump(pruned_model, outfile, indent=2)

    total_time = time.time() - start_time

    # 4. Compare file sizes
    top5_size_bytes = os.path.getsize(output_file)
    top5_size_kb = top5_size_bytes / 1024

    has_orig = os.path.exists(original_model_file)
    orig_size_bytes = os.path.getsize(original_model_file) if has_orig else 0
    orig_size_kb = orig_size_bytes / 1024
    size_diff_bytes = top5_size_bytes - orig_size_bytes
    size_pct_inc = (size_diff_bytes / orig_size_bytes * 100) if orig_size_bytes > 0 else 0

    print("\n=================================================================")
    print("                     MODEL COMPARISON SUMMARY                    ")
    print("=================================================================")
    print(f"  Total Unique States (Pages):      {len(pruned_model):,}")
    print(f"  Total Transitions Processed:      {transition_count:,}")
    print(f"  Total Execution Time:             {total_time:.2f} seconds")
    print("-" * 65)
    print(f"  Original Model (Top-3):           {orig_size_kb:.2f} KB ({orig_size_bytes:,} bytes)")
    print(f"  Updated Model  (Top-5):           {top5_size_kb:.2f} KB ({top5_size_bytes:,} bytes)")
    print(f"  Size Increase:                    +{size_pct_inc:.2f}% (+{size_diff_bytes:,} bytes)")
    print("=================================================================")

    return pruned_model

if __name__ == "__main__":
    train_markov_model_top5()
