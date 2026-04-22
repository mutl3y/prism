"""Lightweight standalone DI shim for convenience helpers that run outside full scan orchestration."""

from __future__ import annotations


class StandaloneDI:
    """Minimal DI shim carrying only scan_options for standalone plugin resolution."""

    def __init__(self, scan_options: dict) -> None:
        self._scan_options = scan_options

    @property
    def scan_options(self) -> dict:
        return self._scan_options


def make_standalone_di(
    role_path: str, exclude_paths: list[str] | None = None
) -> StandaloneDI:
    from prism.scanner_plugins.bundle_resolver import ensure_prepared_policy_bundle

    options: dict = {"role_path": role_path, "exclude_path_patterns": exclude_paths}
    ensure_prepared_policy_bundle(scan_options=options, di=None)
    return StandaloneDI(options)
