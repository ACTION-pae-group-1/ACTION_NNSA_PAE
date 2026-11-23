"""Make the repo-root ``scripts`` package importable for tests in this folder only.

The root pytest config uses ``--import-mode=importlib``, which does not add the
repo root to ``sys.path``. Adding it here, rather than repo-wide, keeps the
change scoped to these tests.
"""

import sys
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parents[2])
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
