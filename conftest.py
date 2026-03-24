"""Pytest bootstrap configuration for local source imports."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# Ensure tests import the in-repo package without requiring PYTHONPATH exports.
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
