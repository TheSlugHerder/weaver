import os
import sys

# Ensure the `src` package and repo root are importable during tests
HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.abspath(os.path.join(HERE, ".."))
SRC_PATH = os.path.join(REPO_ROOT, "src")
# Add repo root so `src.weaver` imports work, and add src so `weaver` works too
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)
