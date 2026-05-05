"""Canonical Jinja regex patterns (side-effect-free data module).

Located in ``scanner_data`` so leaf-imports do not trigger eager plugin
loading via ``prism.scanner_plugins/__init__.py``. The Jinja parser
plugin re-exports these symbols for plugin-facing consumers.
"""

from __future__ import annotations

import re

JINJA_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)")
JINJA_IDENTIFIER_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")

__all__ = ["JINJA_VAR_RE", "JINJA_IDENTIFIER_RE"]
