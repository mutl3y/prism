"""Compatibility alias for scanner variable extractor helpers.

This module remains importable for backward compatibility.
Implementation lives in ``prism.scanner_submodules.variable_extractor``.
"""

from .scanner_submodules import variable_extractor as _impl
import sys as _sys

_sys.modules[__name__] = _impl
