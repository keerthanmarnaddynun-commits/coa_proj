import glob
import os

for f in glob.glob("tools/audit_scratch/*.py"):
    with open(f) as fp:
        content = fp.read()
        if "67645" in content or "67,645" in content or "63331" in content or "63,331" in content:
            print(f"Found in {f}")

