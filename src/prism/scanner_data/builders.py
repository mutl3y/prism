"""Backward-compatible re-export shim for builder classes.

Builder implementations now live in the domain module that owns the contract
they produce:

  - ``VariableRowBuilder`` → :mod:`.contracts_variables`
  - ``ScanPayloadBuilder``  → :mod:`.contracts_output`

This module preserves the ``prism.scanner_data.builders`` import surface.
"""

from __future__ import annotations

from .contracts_output import ScanPayloadBuilder as ScanPayloadBuilder
from .contracts_variables import VariableRowBuilder as VariableRowBuilder

__all__ = [
    "ScanPayloadBuilder",
    "VariableRowBuilder",
]
