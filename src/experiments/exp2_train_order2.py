import os
import json
import time
from collections import defaultdict, Counter

def train_markov_model_order2(
    input_file="data/pages/cleaned_training_pages.txt",
    output_file="data/models/markov_model_order2.json",
    original_model_file="data/models/markov_model.json",
    top_k=3,
    log_interval=500000
):
    """
    Trains a 2nd-order Markov Chain on sequential page accesses:
      1. Uses a 2-page sliding window (page_{t-2}, page_{t-1}) -> page_t.
      2. State keys are formatted as comma-separated strings ("page1,page2").
      3. Prunes each state to retain only the top_k most frequent next pages.
      4. Saves the pruned model to markov_model_order2.json.
      5. Compares model file size against the 1st-order model.
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"Input file '{input_file}' not found. "
            "Please ensure cleaned_training_pages.txt is in the workspace."
        )

    file_size_mb = os.path.getsize(input_file) / (1024 * 1024)
    print("=================================================================")
    print("       EXPERIMENT 2: 2ND-ORDER MARKOV MODEL TRAINING             ")
    print("=================================================================")
    print(f"  Input trace:           {input_file} ({file_size_mb:.2f} MB)")
    print(f"  Output model file:     {output_file}")
    print(f"  Order:                 2nd-order (page_{{t-2}}, page_{{t-1}}) -> page_t")
    print(f"  Top transitions (k):   {top_k}")
    print("=================================================================\n")

    start_time = time.time()
    transition_count = 0
    p2, p1 = None, None

    # Maps (p2, p1) tuple -> Counter({next_page: frequency})
    chain_order2 = defaultdict(Counter)

    # 1. Ingestion with sliding 2-page window
    print("Step 1: Ingesting sequential page trace and tracking 2nd-order transitions...")
    with open(input_file, "r", buffering=8 * 1024 * 1024) as infile:
        for line in infile:
            line = line.strip()
            if not line:
                continue

            current_page = int(line)

            # Once we have 2 preceding pages in history, record transition
            if p2 is not None and p1 is not None:
                chain_order2[(p2, p1)][current_page] += 1
                transition_count += 1

                if transition_count % log_interval == 0:
                    elapsed = time.time() - start_time
                    rate = transition_count / elapsed if elapsed > 0 else 0
                    print(f"  Ingested {transition_count:,} transitions ({rate:,.0f} trans/sec)...")

            # Slide history window
            p2, p1 = p1, current_page

    ingest_time = time.time() - start_time
    print(f"Ingestion finished in {ingest_time:.2f}s.")
    print(f"  Total transitions processed: {transition_count:,}")
    print(f"  Total unique 2nd-order states: {len(chain_order2):,}\n")

    # 2. Prune transitions to top_k and format state keys as "page1,page2"
    print(f"Step 2: Pruning transitions to top {top_k} next pages per state...")
    prune_start = time.time()
    pruned_model = {}

    for (state_p2, state_p1), next_counts in chain_order2.items():
        state_key = f"{state_p2},{state_p1}"
        pruned_model[state_key] = {
            str(nxt_page): count
            for nxt_page, count in next_counts.most_common(top_k)
        }

    prune_time = time.time() - prune_start
    print(f"Pruning finished in {prune_time:.2f}s.\n")

    # 3. Save to disk as JSON
    print(f"Step 3: Saving pruned model to '{output_file}'...")
    save_start = time.time()
    with open(output_file, "w") as outfile:
        json.dump(pruned_model, outfile, indent=2)
    save_time = time.time() - save_start
    print(f"File write finished in {save_time:.2f}s.\n")

    total_time = time.time() - start_time

    # 4. Compare file sizes against 1st-order model
    order2_size_bytes = os.path.getsize(output_file)
    order2_size_mb = order2_size_bytes / (1024 * 1024)
    order2_size_kb = order2_size_bytes / 1024

    has_orig = os.path.exists(original_model_file)
    orig_size_bytes = os.path.getsize(original_model_file) if has_orig else 0
    orig_size_kb = orig_size_bytes / 1024
    size_diff_bytes = order2_size_bytes - orig_size_bytes
    size_pct_inc = (size_diff_bytes / orig_size_bytes * 100) if orig_size_bytes > 0 else 0

    print("=================================================================")
    print("                     MODEL COMPARISON SUMMARY                    ")
    print("=================================================================")
    print(f"  Total Unique 2nd-Order States:    {len(pruned_model):,}")
    print(f"  Total Transitions Processed:      {transition_count:,}")
    print(f"  Total Execution Time:             {total_time:.2f} seconds")
    print("-" * 65)
    print(f"  1st-Order Model (Top-3):          {orig_size_kb:.2f} KB ({orig_size_bytes:,} bytes)")
    print(f"  2nd-Order Model (Top-3):          {order2_size_mb:.2f} MB ({order2_size_bytes:,} bytes)")
    print(f"  Size Increase:                    +{size_pct_inc:,.2f}% (+{size_diff_bytes:,} bytes)")
    print("=================================================================")

    return pruned_model

if __name__ == "__main__":
    train_markov_model_order2()
