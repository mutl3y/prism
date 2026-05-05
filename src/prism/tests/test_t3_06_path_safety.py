"""T3-06: Tests for path traversal validation at the API boundary."""

from __future__ import annotations

import pytest

from prism.errors import PrismRuntimeError
from prism.path_safety import (
    ERROR_CODE_PATH_TRAVERSAL,
    assert_safe_role_path,
)


def test_accepts_normal_absolute_path(tmp_path) -> None:
    result = assert_safe_role_path(str(tmp_path))
    assert result == str(tmp_path)


def test_accepts_pathlike(tmp_path) -> None:
    result = assert_safe_role_path(tmp_path)
    assert result == str(tmp_path)


def test_rejects_none() -> None:
    with pytest.raises(PrismRuntimeError) as exc:
        assert_safe_role_path(None)
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL


def test_rejects_non_string() -> None:
    with pytest.raises(PrismRuntimeError) as exc:
        assert_safe_role_path(123)  # type: ignore[arg-type]
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL


def test_rejects_empty_string() -> None:
    with pytest.raises(PrismRuntimeError) as exc:
        assert_safe_role_path("")
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL


def test_rejects_whitespace() -> None:
    with pytest.raises(PrismRuntimeError) as exc:
        assert_safe_role_path("   ")
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL


def test_rejects_nul_byte() -> None:
    with pytest.raises(PrismRuntimeError) as exc:
        assert_safe_role_path("/tmp/role\x00name")
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL


def test_rejects_parent_traversal_relative() -> None:
    with pytest.raises(PrismRuntimeError) as exc:
        assert_safe_role_path("../../../etc/passwd")
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL


def test_rejects_embedded_parent_segment() -> None:
    with pytest.raises(PrismRuntimeError) as exc:
        assert_safe_role_path("/var/lib/role/../../../etc")
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL


def test_allowed_root_accepts_contained_path(tmp_path) -> None:
    inner = tmp_path / "role"
    inner.mkdir()
    result = assert_safe_role_path(str(inner), allowed_root=str(tmp_path))
    assert result == str(inner)


def test_allowed_root_rejects_outside_path(tmp_path) -> None:
    outside = tmp_path.parent
    with pytest.raises(PrismRuntimeError) as exc:
        assert_safe_role_path(str(outside), allowed_root=str(tmp_path))
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL
    assert "allowed_root" in (exc.value.detail or {})


def test_run_scan_rejects_traversal() -> None:
    from prism import api

    with pytest.raises(PrismRuntimeError) as exc:
        api.run_scan("../../../etc/passwd")
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL


def test_scan_role_rejects_empty() -> None:
    from prism import api

    with pytest.raises(PrismRuntimeError) as exc:
        api.scan_role("")
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL


def test_scan_collection_rejects_nul() -> None:
    from prism import api

    with pytest.raises(PrismRuntimeError) as exc:
        api.scan_collection("/tmp/role\x00")
    assert exc.value.code == ERROR_CODE_PATH_TRAVERSAL
