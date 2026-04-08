"""Runtime contracts for Prism FSRC extension seam."""

from __future__ import annotations

from typing import Any, TypedDict


class ExtensionHookCall(TypedDict):
    """Describe a hook invocation request for extension processing."""

    hook_point: str
    args_count: int
    kwargs_keys: list[str]


class ExtensionHookResult(TypedDict):
    """Describe the result emitted by a hook invocation."""

    enabled: bool
    result_count: int
    errors: list[str]
    payload: list[Any]
