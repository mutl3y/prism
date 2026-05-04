"""T3-03: Optional scan result cache.

Defines a cache backend protocol and an in-memory LRU implementation.
Cache key is computed from a content hash of role inputs plus a digest
of scan_options. Wiring into the scan pipeline is consumer-driven; this
module provides only the seam.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections import OrderedDict
from typing import Any, Mapping, Protocol

from prism.errors import PrismRuntimeError


def _clone_container_structure(value: object) -> object:
    """Clone container nodes so cache boundaries do not share mutable state."""
    if isinstance(value, dict):
        return {key: _clone_container_structure(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_container_structure(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_clone_container_structure(item) for item in value)
    if isinstance(value, set):
        return {_clone_container_structure(item) for item in value}
    if isinstance(value, frozenset):
        return frozenset(_clone_container_structure(item) for item in value)
    return value


class ScanCacheBackend(Protocol):
    """Backend protocol for caching completed scan results."""

    def get(self, key: str) -> Any | None: ...

    def set(self, key: str, value: Any) -> None: ...

    def invalidate(self, key: str) -> None: ...

    def clear(self) -> None: ...


class _StatsAware(Protocol):
    """Internal protocol for cache backends that expose hit/miss counters."""

    @property
    def hits(self) -> int: ...

    @property
    def misses(self) -> int: ...

    def stats(self) -> tuple[int, int]: ...


class InMemoryLRUScanCache:
    """In-memory least-recently-used :class:`ScanCacheBackend`.

    ``maxsize`` defaults to 64 entries. ``maxsize=0`` disables caching.
    """

    def __init__(self, maxsize: int = 64) -> None:
        if maxsize < 0:
            raise ValueError("maxsize must be >= 0")
        self._maxsize = maxsize
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        if self._maxsize == 0:
            with self._lock:
                self._misses += 1
            return None
        with self._lock:
            try:
                value = self._store.pop(key)
            except KeyError:
                self._misses += 1
                return None
            self._store[key] = value
            self._hits += 1
        return _clone_container_structure(value)

    def set(self, key: str, value: Any) -> None:
        if self._maxsize == 0:
            return
        with self._lock:
            if key in self._store:
                self._store.pop(key)
            self._store[key] = _clone_container_structure(value)
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    @property
    def hits(self) -> int:
        with self._lock:
            return self._hits

    @property
    def misses(self) -> int:
        with self._lock:
            return self._misses

    def stats(self) -> tuple[int, int]:
        """Return (hits, misses) atomically under a single lock acquisition."""
        with self._lock:
            return self._hits, self._misses

    def __len__(self) -> int:
        return len(self._store)


def _callable_identity(value: object) -> str:
    if not callable(value):
        raise PrismRuntimeError(
            code="scan_cache_runtime_wiring_invalid",
            category="runtime",
            message="value must be callable.",
            detail={"field": "value", "actual_type": type(value).__name__},
        )
    value_type = type(value)
    module = getattr(value, "__module__", value_type.__module__)
    qualname = getattr(value, "__qualname__", value_type.__qualname__)
    return f"{module}.{qualname}@{id(value)}"


def _object_identity(value: object) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}@{id(value)}"


def _runtime_registry_identity(value: object) -> str:
    fingerprint = getattr(value, "get_state_fingerprint", None)
    if callable(fingerprint):
        result = fingerprint()
        if isinstance(result, str) and result:
            return result
    return _object_identity(value)


def build_runtime_wiring_identity(
    *,
    route_scan_payload_orchestration_fn: object,
    orchestrate_scan_payload_with_selected_plugin_fn: object,
    runtime_registry: object | None,
) -> dict[str, str | None]:
    """Fingerprint runtime wiring inputs that can change cached payload semantics."""
    if not callable(route_scan_payload_orchestration_fn):
        raise PrismRuntimeError(
            code="scan_cache_runtime_wiring_invalid",
            category="runtime",
            message="route_scan_payload_orchestration_fn must be callable.",
            detail={
                "field": "route_scan_payload_orchestration_fn",
                "actual_type": type(route_scan_payload_orchestration_fn).__name__,
            },
        )
    if not callable(orchestrate_scan_payload_with_selected_plugin_fn):
        raise PrismRuntimeError(
            code="scan_cache_runtime_wiring_invalid",
            category="runtime",
            message=(
                "orchestrate_scan_payload_with_selected_plugin_fn must be callable."
            ),
            detail={
                "field": "orchestrate_scan_payload_with_selected_plugin_fn",
                "actual_type": type(
                    orchestrate_scan_payload_with_selected_plugin_fn
                ).__name__,
            },
        )
    return {
        "route_scan_payload_orchestration_fn": _callable_identity(
            route_scan_payload_orchestration_fn
        ),
        "orchestrate_scan_payload_with_selected_plugin_fn": _callable_identity(
            orchestrate_scan_payload_with_selected_plugin_fn
        ),
        "runtime_registry": (
            None
            if runtime_registry is None
            else _runtime_registry_identity(runtime_registry)
        ),
    }


def compute_scan_cache_key(
    *,
    role_content_hash: str,
    scan_options: Mapping[str, Any],
) -> str:
    """Build a stable cache key from a role content hash and scan options."""
    if not role_content_hash:
        raise ValueError("role_content_hash must not be empty")

    def _canonicalize(value: object) -> object:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, dict):
            return {str(key): _canonicalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [_canonicalize(item) for item in value]
        if isinstance(value, tuple):
            return {"__tuple__": [_canonicalize(item) for item in value]}
        if isinstance(value, set):
            return {
                "__set__": sorted(
                    (_canonicalize(item) for item in value),
                    key=lambda item: json.dumps(item, sort_keys=True),
                )
            }
        if isinstance(value, frozenset):
            return {
                "__frozenset__": sorted(
                    (_canonicalize(item) for item in value),
                    key=lambda item: json.dumps(item, sort_keys=True),
                )
            }
        return {
            "__opaque_type__": (f"{type(value).__module__}.{type(value).__qualname__}")
        }

    options_blob = json.dumps(_canonicalize(dict(scan_options)), sort_keys=True)
    options_hash = hashlib.sha256(options_blob.encode("utf-8")).hexdigest()
    return f"{role_content_hash}:{options_hash}"


def compute_path_content_hash(path: str) -> str:
    """Compute a stable sha256 hash for a file or directory path's contents."""
    h = hashlib.sha256()
    root = os.path.abspath(path)
    if os.path.isdir(root):
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(
                d for d in dirnames if not d.startswith(".") and d != "__pycache__"
            )
            for filename in sorted(filenames):
                if filename.startswith(".") or filename.endswith(".pyc"):
                    continue
                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, root)
                h.update(b"\x1ffile\x1f")
                h.update(rel_path.encode("utf-8"))
                h.update(b"\x1fdata\x1f")
                try:
                    with open(abs_path, "rb") as fh:
                        while chunk := fh.read(65536):
                            h.update(chunk)
                except OSError:
                    h.update(b"\x00UNREADABLE\x00")
                h.update(b"\x1fend\x1f")
        return h.hexdigest()

    if os.path.isfile(root):
        try:
            with open(root, "rb") as fh:
                while chunk := fh.read(65536):
                    h.update(chunk)
        except OSError:
            h.update(b"\x1ffile\x1f")
            h.update(root.encode("utf-8", errors="surrogateescape"))
            h.update(b"\x1fdata\x1f")
            h.update(b"\x00UNREADABLE\x00")
        return h.hexdigest()

    h.update(b"\x00MISSING\x00")
    return h.hexdigest()


def compute_role_content_hash(role_path: str) -> str:
    """Compute a stable sha256 hash of a role directory's file tree and contents."""
    return compute_path_content_hash(role_path)


def report_cache_stats(backend: _StatsAware) -> dict[str, Any]:
    """Return hit/miss stats for measurement (atomic snapshot when available)."""
    if hasattr(backend, "stats"):
        hits, misses = backend.stats()
    else:
        hits, misses = backend.hits, backend.misses
    total = hits + misses
    hit_rate = hits / total if total > 0 else 0.0
    return {
        "hits": hits,
        "misses": misses,
        "total": total,
        "hit_rate_pct": round(hit_rate * 100, 1),
    }


__all__ = [
    "build_runtime_wiring_identity",
    "InMemoryLRUScanCache",
    "ScanCacheBackend",
    "compute_path_content_hash",
    "compute_role_content_hash",
    "compute_scan_cache_key",
    "report_cache_stats",
]
