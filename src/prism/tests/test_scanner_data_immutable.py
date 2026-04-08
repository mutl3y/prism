"""Unit tests for scanner_data.immutable module."""

from __future__ import annotations

import pytest

from prism.scanner_data.immutable import FrozenDict


def test_frozen_dict_supports_read_operations() -> None:
    """FrozenDict behaves like a normal mapping for reads."""
    frozen = FrozenDict({"k": "v", "n": 1})

    assert frozen["k"] == "v"
    assert frozen.get("n") == 1
    assert list(frozen.keys()) == ["k", "n"]


def test_frozen_dict_setitem_raises_type_error() -> None:
    """Assignment is blocked to keep mapping immutable."""
    frozen = FrozenDict({"k": "v"})

    with pytest.raises(TypeError, match="FrozenDict is immutable"):
        frozen["k"] = "updated"


def test_frozen_dict_delitem_raises_type_error() -> None:
    """Item deletion is blocked to keep mapping immutable."""
    frozen = FrozenDict({"k": "v"})

    with pytest.raises(TypeError, match="FrozenDict is immutable"):
        del frozen["k"]


def test_frozen_dict_pop_raises_type_error_for_any_signature() -> None:
    """pop blocks both key-only and key-default call forms."""
    frozen = FrozenDict({"k": "v"})

    with pytest.raises(TypeError, match="FrozenDict is immutable"):
        frozen.pop("k")

    with pytest.raises(TypeError, match="FrozenDict is immutable"):
        frozen.pop("missing", None)


def test_frozen_dict_popitem_raises_attribute_error() -> None:
    """popitem is explicitly blocked."""
    frozen = FrozenDict({"k": "v"})

    with pytest.raises(AttributeError, match="FrozenDict is immutable"):
        frozen.popitem()


def test_frozen_dict_clear_raises_attribute_error() -> None:
    """clear is explicitly blocked."""
    frozen = FrozenDict({"k": "v"})

    with pytest.raises(AttributeError, match="FrozenDict is immutable"):
        frozen.clear()


def test_frozen_dict_update_raises_attribute_error_for_any_signature() -> None:
    """update blocks dict positional and kwargs update forms."""
    frozen = FrozenDict({"k": "v"})

    with pytest.raises(AttributeError, match="FrozenDict is immutable"):
        frozen.update({"k": "new"})

    with pytest.raises(AttributeError, match="FrozenDict is immutable"):
        frozen.update(k="new")


def test_frozen_dict_setdefault_raises_attribute_error() -> None:
    """setdefault is explicitly blocked."""
    frozen = FrozenDict({"k": "v"})

    with pytest.raises(AttributeError, match="FrozenDict is immutable"):
        frozen.setdefault("missing", "value")


def test_frozen_dict_all_exports_only_public_symbol() -> None:
    """Module export surface remains intentionally minimal."""
    from prism.scanner_data import immutable

    assert immutable.__all__ == ["FrozenDict"]
