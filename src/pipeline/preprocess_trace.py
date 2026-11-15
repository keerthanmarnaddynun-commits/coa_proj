import time
import os

def preprocess_memory_trace(
    input_file="data/traces/training_trace.txt",
    output_file="data/pages/cleaned_training_pages.txt",
    log_interval=500000
):
    """
    Preprocess memory trace by extracting raw memory addresses and converting
    them into 4KB page numbers (page = address // 4096).
    
    Designed to run efficiently on Google Colab or local Python environments.
    """
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    file_size_mb = os.path.getsize(input_file) / (1024 * 1024)
    print(f"Starting preprocessing:")
    print(f" - Input file:  {input_file} ({file_size_mb:.2f} MB)")
    print(f" - Output file: {output_file}")
    print(f" - Page size:   4096 bytes (4 KB)")
    print("-" * 50)

    start_time = time.time()
    line_count = 0
    pages_written = 0

    # Using larger buffer size (e.g., 8MB) for fast I/O on large trace files
    buffer_size = 8 * 1024 * 1024

    with open(input_file, "r", buffering=buffer_size) as infile, \
         open(output_file, "w", buffering=buffer_size) as outfile:
        
        for line in infile:
            line = line.strip()
            if not line:
                continue

            line_count += 1
            parts = line.split()

            # Find memory address token (e.g. 0xae4800000)
            addr_token = None
            for p in parts:
                if p.startswith(("0x", "0X")):
                    addr_token = p
                    break
            
            # Fallback if hex prefix is omitted
            if addr_token is None:
                addr_token = parts[1] if len(parts) > 1 else parts[0]

            try:
                raw_address = int(addr_token, 16)
                page_number = raw_address // 4096
                outfile.write(f"{page_number}\n")
                pages_written += 1
            except ValueError:
                # Skip any malformed line/header
                continue

            # Progress tracking
            if line_count % log_interval == 0:
                elapsed = time.time() - start_time
                rate = line_count / elapsed if elapsed > 0 else 0
                print(f"Processed {line_count:,} lines ({rate:,.0f} lines/sec)...")

    elapsed_total = time.time() - start_time
    out_size_mb = os.path.getsize(output_file) / (1024 * 1024) if os.path.exists(output_file) else 0

    print("-" * 50)
    print(f"Preprocessing completed successfully!")
    print(f" - Total lines read:     {line_count:,}")
    print(f" - Total pages written:  {pages_written:,}")
    print(f" - Output file size:     {out_size_mb:.2f} MB")
    print(f" - Total execution time: {elapsed_total:.2f} seconds")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Preprocess memory trace to 4KB page numbers.")
    parser.add_argument(
        "--input", "-i",
        default="data/traces/testing_trace.txt" if os.path.exists("data/traces/testing_trace.txt") else "testing_trace.txt",
        help="Path to input trace file"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/pages/cleaned_testing_pages.txt",
        help="Path to output cleaned page numbers file"
    )
    parser.add_argument(
        "--log-interval",
        type=int,
        default=500000,
        help="Progress log interval in lines"
    )

    args = parser.parse_args()
    preprocess_memory_trace(
        input_file=args.input,
        output_file=args.output,
        log_interval=args.log_interval
    )
