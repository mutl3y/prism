"""Minimal scan-context builder seam for future fsrc runtime parity slices."""

from __future__ import annotations

from typing import Callable

from prism.scanner_data.contracts_request import ScanContextPayload, ScanOptionsDict


class ScanContextBuilder:
    """Build scan context payloads through an injected runtime seam."""

    def __init__(
        self,
        *,
        prepare_scan_context_fn: Callable[[ScanOptionsDict], ScanContextPayload],
    ) -> None:
        self._prepare_scan_context_fn = prepare_scan_context_fn

    def build_scan_context(self, scan_options: ScanOptionsDict) -> ScanContextPayload:
        return self._prepare_scan_context_fn(scan_options)


def build_scan_context(
    scan_options: ScanOptionsDict,
    *,
    prepare_scan_context_fn: Callable[[ScanOptionsDict], ScanContextPayload],
) -> ScanContextPayload:
    """Build scan context payload with explicit dependency injection."""
    builder = ScanContextBuilder(prepare_scan_context_fn=prepare_scan_context_fn)
    return builder.build_scan_context(scan_options)
