import os

def search_text(term):
    print(f"Searching for {term}...")
    for root, dirs, files in os.walk("."):
        if ".git" in root or "__pycache__" in root: continue
        for f in files:
            p = os.path.join(root, f)
            if p.endswith((".py", ".md", ".json", ".txt")):
                if "trace" in f or "Amazon" in f or f == "cleaned_testing_pages.txt" or f == "cleaned_training_pages.txt":
                    continue
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as fp:
                        for lno, line in enumerate(fp, 1):
                            if term in line:
                                print(f"{p}:{lno}: {line.strip()}")
                except:
                    pass

search_text("67645")
search_text("67,645")
search_text("63331")
search_text("63,331")
search_text("67634")
search_text("67,634")
search_text("63132")
search_text("63,132")

