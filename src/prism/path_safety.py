"""T3-06: Path safety check for API/CLI boundary.

Trust model
-----------
``role_path`` (and related path arguments) are treated as caller-trusted.
Callers must sanitise inputs before invoking the public API. This module
provides a defensive last line of validation at the API/CLI boundary so that
obviously malicious or malformed paths fail fast with a typed error before
any I/O is attempted.

The check is intentionally lightweight:

* Reject empty or non-string paths.
* Reject paths containing NUL bytes.
* Reject relative paths that contain ``..`` parent traversal segments.
* Optionally enforce that the resolved path is contained within an allowed
  root directory.

It does not (and cannot) defend against TOCTOU attacks or symlink races; for
that callers must run Prism in a sandboxed working directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from prism.errors import PrismRuntimeError

ERROR_CODE_PATH_TRAVERSAL = "role_path_traversal_rejected"
ERROR_CATEGORY_INPUT = "input_validation"


def assert_safe_role_path(
    role_path: object,
    *,
    allowed_root: str | os.PathLike[str] | None = None,
    field_name: str = "role_path",
) -> str:
    """Validate ``role_path`` at the API/CLI boundary.

    Returns the validated path (resolved to an absolute path string when
    possible). Raises :class:`PrismRuntimeError` with code
    ``role_path_traversal_rejected`` if the path is unsafe.
    """
    if role_path is None or not isinstance(role_path, (str, os.PathLike)):
        raise PrismRuntimeError(
            code=ERROR_CODE_PATH_TRAVERSAL,
            category=ERROR_CATEGORY_INPUT,
            message=f"{field_name} must be a non-empty path string",
            detail={"field": field_name, "value": repr(role_path)},
        )

    raw = os.fspath(role_path)
    if not raw or not raw.strip():
        raise PrismRuntimeError(
            code=ERROR_CODE_PATH_TRAVERSAL,
            category=ERROR_CATEGORY_INPUT,
            message=f"{field_name} must not be empty",
            detail={"field": field_name},
        )

    if "\x00" in raw:
        raise PrismRuntimeError(
            code=ERROR_CODE_PATH_TRAVERSAL,
            category=ERROR_CATEGORY_INPUT,
            message=f"{field_name} contains NUL byte",
            detail={"field": field_name},
        )

    parts = Path(raw).parts
    if ".." in parts:
        raise PrismRuntimeError(
            code=ERROR_CODE_PATH_TRAVERSAL,
            category=ERROR_CATEGORY_INPUT,
            message=f"{field_name} contains parent-directory traversal segment",
            detail={"field": field_name, "value": raw},
        )

    if allowed_root is not None:
        try:
            resolved = Path(raw).resolve()
            root_resolved = Path(os.fspath(allowed_root)).resolve()
        except OSError as exc:
            raise PrismRuntimeError(
                code=ERROR_CODE_PATH_TRAVERSAL,
                category=ERROR_CATEGORY_INPUT,
                message=f"{field_name} could not be resolved",
                detail={"field": field_name, "value": raw, "os_error": str(exc)},
            ) from exc
        try:
            resolved.relative_to(root_resolved)
        except ValueError as exc:
            raise PrismRuntimeError(
                code=ERROR_CODE_PATH_TRAVERSAL,
                category=ERROR_CATEGORY_INPUT,
                message=(
                    f"{field_name} resolves outside allowed root " f"{root_resolved!s}"
                ),
                detail={
                    "field": field_name,
                    "value": raw,
                    "allowed_root": str(root_resolved),
                },
            ) from exc

    return raw
