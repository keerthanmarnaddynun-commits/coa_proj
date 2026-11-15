import os
import json
import time
from collections import defaultdict, Counter

def train_markov_model(
    input_file="data/pages/cleaned_training_pages.txt",
    output_file="data/models/markov_model.json",
    top_k=3,
    log_interval=500000
):
    """
    Trains a 1st-order Markov Chain on sequential page accesses:
      1. Reads cleaned_training_pages.txt line by line.
      2. Maps each current_page to next_page transition counts.
      3. Prunes the model to retain only the top_k most frequent transitions per page.
      4. Saves the pruned model to markov_model.json.
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(
            f"Input file '{input_file}' not found. "
            "Please ensure cleaned_training_pages.txt is present in the working directory."
        )

    file_size_mb = os.path.getsize(input_file) / (1024 * 1024)
    print(f"Starting Markov Model Training:")
    print(f"  Input file:       {input_file} ({file_size_mb:.2f} MB)")
    print(f"  Output model:     {output_file}")
    print(f"  Top transitions:  {top_k}")
    print("-" * 55)

    start_time = time.time()
    transition_count = 0
    prev_page = None

    # Using defaultdict of Counter for high-performance frequency tracking
    markov_chain = defaultdict(Counter)

    # 1. Sequential Ingestion
    with open(input_file, "r") as infile:
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
                    print(f"Ingested {transition_count:,} transitions ({rate:,.0f} trans/sec)...")

            prev_page = current_page

    ingest_time = time.time() - start_time
    print(f"Ingestion complete: {transition_count:,} transitions across {len(markov_chain):,} unique pages in {ingest_time:.2f}s.")
    print("-" * 55)

    # 2. Prune transitions to top_k per page
    print(f"Pruning dictionary to top {top_k} next_page frequencies...")
    prune_start = time.time()
    pruned_model = {}

    for page, next_counts in markov_chain.items():
        # Retain only the top 3 most frequently requested next pages
        pruned_model[str(page)] = {
            str(nxt_page): count
            for nxt_page, count in next_counts.most_common(top_k)
        }

    prune_time = time.time() - prune_start
    print(f"Pruning completed in {prune_time:.2f}s.")

    # 3. Save to disk as JSON
    print(f"Saving pruned model to '{output_file}'...")
    with open(output_file, "w") as outfile:
        json.dump(pruned_model, outfile, indent=2)

    total_time = time.time() - start_time
    json_size_bytes = os.path.getsize(output_file)
    json_size_kb = json_size_bytes / 1024

    print("-" * 55)
    print("Markov Model training completed successfully!")
    print(f"  Total unique states (pages): {len(pruned_model):,}")
    print(f"  Total transitions processed: {transition_count:,}")
    print(f"  Output JSON file size:       {json_size_kb:.2f} KB ({json_size_bytes:,} bytes)")
    print(f"  Total execution time:        {total_time:.2f} seconds")

    return pruned_model

if __name__ == "__main__":
    train_markov_model()
