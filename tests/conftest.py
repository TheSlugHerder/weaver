import os
import sys

# Ensure the `src` package is importable during tests
HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
SRC_PATH = os.path.join(REPO_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
