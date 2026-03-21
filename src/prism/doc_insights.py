"""Compatibility alias for scanner helper module.

This module remains importable for backward compatibility.
Implementation lives in prism.scanner_submodules.doc_insights.
"""

from .scanner_submodules import doc_insights as _impl
import sys as _sys

_sys.modules[__name__] = _impl
