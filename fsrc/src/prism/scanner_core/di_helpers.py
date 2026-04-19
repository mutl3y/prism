"""Shared DI utility helpers for scanner_core and scanner_extract."""

from __future__ import annotations


def _scan_options_from_di(di: object | None = None) -> dict[str, object] | None:
    if di is None:
        return None
    scan_options = getattr(di, "scan_options", None)
    if isinstance(scan_options, dict):
        return scan_options
    scan_options = getattr(di, "_scan_options", None)
    if isinstance(scan_options, dict):
        return scan_options
    return None
