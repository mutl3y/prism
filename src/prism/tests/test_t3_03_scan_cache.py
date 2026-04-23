"""T3-03: Scan cache backend tests."""

from __future__ import annotations

import pytest

from prism.scanner_core.scan_cache import (
    InMemoryLRUScanCache,
    compute_scan_cache_key,
)


def test_lru_cache_get_returns_none_on_miss() -> None:
    cache = InMemoryLRUScanCache()
    assert cache.get("absent") is None
    assert cache.misses == 1
    assert cache.hits == 0


def test_lru_cache_set_then_get_hits() -> None:
    cache = InMemoryLRUScanCache()
    cache.set("k", {"result": 1})
    assert cache.get("k") == {"result": 1}
    assert cache.hits == 1
    assert cache.misses == 0


def test_lru_cache_evicts_oldest_when_full() -> None:
    cache = InMemoryLRUScanCache(maxsize=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert len(cache) == 2


def test_lru_cache_get_promotes_recency() -> None:
    cache = InMemoryLRUScanCache(maxsize=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")
    cache.set("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") is None


def test_lru_cache_invalidate_and_clear() -> None:
    cache = InMemoryLRUScanCache()
    cache.set("a", 1)
    cache.invalidate("a")
    assert cache.get("a") is None
    cache.set("b", 2)
    cache.clear()
    assert len(cache) == 0
    assert cache.hits == 0
    assert cache.misses == 0


def test_lru_cache_maxsize_zero_disables() -> None:
    cache = InMemoryLRUScanCache(maxsize=0)
    cache.set("a", 1)
    assert cache.get("a") is None
    assert len(cache) == 0


def test_lru_cache_negative_maxsize_rejected() -> None:
    with pytest.raises(ValueError):
        InMemoryLRUScanCache(maxsize=-1)


def test_compute_scan_cache_key_is_stable_and_options_sensitive() -> None:
    key1 = compute_scan_cache_key(
        role_content_hash="abc123",
        scan_options={"a": 1, "b": 2},
    )
    key2 = compute_scan_cache_key(
        role_content_hash="abc123",
        scan_options={"b": 2, "a": 1},
    )
    key3 = compute_scan_cache_key(
        role_content_hash="abc123",
        scan_options={"a": 1, "b": 3},
    )
    assert key1 == key2
    assert key1 != key3


def test_compute_scan_cache_key_requires_content_hash() -> None:
    with pytest.raises(ValueError):
        compute_scan_cache_key(role_content_hash="", scan_options={})


def test_compute_scan_cache_key_distinguishes_role_content() -> None:
    k1 = compute_scan_cache_key(role_content_hash="aaa", scan_options={})
    k2 = compute_scan_cache_key(role_content_hash="bbb", scan_options={})
    assert k1 != k2
