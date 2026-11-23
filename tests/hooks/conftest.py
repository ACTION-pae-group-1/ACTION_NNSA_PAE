"""Pytest configuration for hooks tests."""

import sys
from pathlib import Path

# Add hooks directory to path so tests can import hook modules directly
hooks_dir = Path(__file__).parent.parent.parent / ".claude" / "hooks"
if str(hooks_dir) not in sys.path:
    sys.path.insert(0, str(hooks_dir))
