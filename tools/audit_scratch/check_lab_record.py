with open("lab_record.md", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        for val in ["67,634", "63,132", "67,645", "63,331", "Top-1", "Top-2"]:
            if val in line:
                print(f"Line {i}: {line.strip()}")

