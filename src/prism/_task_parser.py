"""Compatibility alias for scanner task parser helpers.

This module remains importable for backward compatibility.
Implementation lives in ``prism.scanner_submodules.task_parser``.
"""

from .scanner_submodules import task_parser as _impl
import sys as _sys

_sys.modules[__name__] = _impl
