"""Compatibility alias for scanner style-variable rendering helpers.

This module remains importable for backward compatibility.
Implementation lives in ``prism.scanner_submodules.style_vars``.
"""

from .scanner_submodules import style_vars as _impl
import sys as _sys

_sys.modules[__name__] = _impl
