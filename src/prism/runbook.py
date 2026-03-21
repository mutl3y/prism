"""Compatibility alias for scanner helper module.

This module remains importable for backward compatibility.
Implementation lives in prism.scanner_submodules.runbook.
"""

from .scanner_submodules import runbook as _impl
import sys as _sys

_sys.modules[__name__] = _impl
