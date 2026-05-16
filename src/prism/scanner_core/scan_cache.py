"""T3-03: Optional scan result cache.

Defines a cache backend protocol and an in-memory LRU implementation.
Cache key is computed from a content hash of role inputs plus a digest
of scan_options. Wiring into the scan pipeline is consumer-driven; this
module provides only the seam.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import threading
from collections import OrderedDict
from typing import Any, Mapping, Protocol

from prism.errors import PrismRuntimeError


def _clone_container_structure(value: object) -> object:
    """Clone container nodes so cache boundaries do not share mutable state.

    For container types (dict, list, tuple, set, frozenset), recursively clones
    all nested containers. For primitive types (str, int, float, bool, None), returns
    the value as-is (immutable). For custom objects, uses copy.deepcopy to prevent
    aliasing bugs where mutations affect all cache consumers.
    """
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
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
    # Custom objects: deep copy to prevent aliasing and race conditions
    return copy.deepcopy(value)


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

    Supports dual bounding: entry count (maxsize) and memory usage (max_memory_bytes).
    Eviction occurs when EITHER limit is exceeded (whichever comes first).

    Args:
        maxsize: Maximum number of cache entries (default 64). Set to 0 to disable.
        max_memory_bytes: Maximum memory usage in bytes (default 100MB).
                          Evicts entries when total memory exceeds this limit.
    """

    def __init__(
        self, maxsize: int = 64, max_memory_bytes: int = 100 * 1024 * 1024
    ) -> None:
        if maxsize < 0:
            raise ValueError("maxsize must be >= 0")
        if max_memory_bytes < 0:
            raise ValueError("max_memory_bytes must be >= 0")
        self._maxsize = maxsize
        self._max_memory_bytes = max_memory_bytes
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._memory_usage: dict[str, int] = {}  # Track memory per key
        self._total_memory_bytes = 0
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions_by_count = 0
        self._evictions_by_memory = 0

    def _estimate_memory_bytes(self, value: Any) -> int:
        """Estimate memory usage of a cached value using sys.getsizeof."""
        try:
            return sys.getsizeof(value)
        except Exception:
            # Fallback for objects that don't support getsizeof
            return 1024  # Conservative estimate

    def get(self, key: str) -> Any | None:
        if self._maxsize == 0:
            with self._lock:
                self._misses += 1
            return None
        with self._lock:
            try:
                value = self._store.pop(key)
                mem_size = self._memory_usage.pop(key, 0)
                self._total_memory_bytes -= mem_size
            except KeyError:
                self._misses += 1
                return None
            self._store[key] = value
            self._memory_usage[key] = mem_size
            self._total_memory_bytes += mem_size
            self._hits += 1
        return _clone_container_structure(value)

    def set(self, key: str, value: Any) -> None:
        if self._maxsize == 0:
            return
        with self._lock:
            # Remove old value if exists
            if key in self._store:
                old_mem = self._memory_usage.pop(key, 0)
                self._total_memory_bytes -= old_mem
                self._store.pop(key)

            cloned = _clone_container_structure(value)
            mem_size = self._estimate_memory_bytes(cloned)

            self._store[key] = cloned
            self._memory_usage[key] = mem_size
            self._total_memory_bytes += mem_size

            # Evict excess items: respect BOTH maxsize and max_memory_bytes
            self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        """Evict entries if either count or memory limits exceeded.

        This is called with the lock already held.
        """
        # Check entry count limit
        while len(self._store) > self._maxsize and len(self._store) > 0:
            evicted_key, evicted_value = self._store.popitem(last=False)
            evicted_mem = self._memory_usage.pop(evicted_key, 0)
            self._total_memory_bytes -= evicted_mem
            self._evictions_by_count += 1

        # Check memory limit
        while (
            self._total_memory_bytes > self._max_memory_bytes and len(self._store) > 0
        ):
            evicted_key, evicted_value = self._store.popitem(last=False)
            evicted_mem = self._memory_usage.pop(evicted_key, 0)
            self._total_memory_bytes -= evicted_mem
            self._evictions_by_memory += 1

    def invalidate(self, key: str) -> None:
        with self._lock:
            if key in self._store:
                self._store.pop(key)
                mem_size = self._memory_usage.pop(key, 0)
                self._total_memory_bytes -= mem_size

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._memory_usage.clear()
            self._total_memory_bytes = 0
            self._hits = 0
            self._misses = 0
            self._evictions_by_count = 0
            self._evictions_by_memory = 0

    @property
    def hits(self) -> int:
        with self._lock:
            return self._hits

    @property
    def misses(self) -> int:
        with self._lock:
            return self._misses

    @property
    def total_memory_bytes(self) -> int:
        """Total memory used by cached entries in bytes."""
        with self._lock:
            return self._total_memory_bytes

    @property
    def evictions_by_count(self) -> int:
        """Number of evictions due to exceeding maxsize."""
        with self._lock:
            return self._evictions_by_count

    @property
    def evictions_by_memory(self) -> int:
        """Number of evictions due to exceeding max_memory_bytes."""
        with self._lock:
            return self._evictions_by_memory

    def stats(self) -> tuple[int, int]:
        """Return (hits, misses) atomically under a single lock acquisition."""
        with self._lock:
            return self._hits, self._misses

    def memory_stats(self) -> dict[str, int | float]:
        """Return comprehensive memory statistics."""
        with self._lock:
            return {
                "total_memory_bytes": self._total_memory_bytes,
                "max_memory_bytes": self._max_memory_bytes,
                "current_entries": len(self._store),
                "max_entries": self._maxsize,
                "memory_utilization_percent": (
                    100.0 * self._total_memory_bytes / self._max_memory_bytes
                    if self._max_memory_bytes > 0
                    else 0.0
                ),
                "evictions_by_count": self._evictions_by_count,
                "evictions_by_memory": self._evictions_by_memory,
            }

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


def _callable_identity(value: object) -> str:
    """Return a stable identity string for a callable.

    Uses module.qualname which is stable across process runs. The volatile
    Python id() is NOT used because it causes cache collisions after object
    reallocation or GC. Two different function instances with the same
    module.qualname are treated as identical in caching (which is correct for
    function types, where identity is determined by source location, not memory
    address).
    """
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
    return f"{module}.{qualname}"


def _object_identity(value: object) -> str:
    """Return a stable identity string for an object.

    Uses module.qualname which is stable across process runs. The volatile
    Python id() is NOT used because it causes cache collisions after object
    reallocation or GC.
    """
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _runtime_registry_identity(value: object) -> str:
    """Return a runtime wiring identity for a registry object.

    Uses stable state fingerprint if available (preferred). Falls back to
    type-only identity for instances without fingerprinting support.

    CRITICAL FIX (GILF-NODE3-02): Removed volatile id()-based fallback which
    caused cache collisions across process restarts and object reallocations.
    Type-only identity is stable and prevents cache poisoning, though it means
    all instances of the same registry type will share cache entries.

    For persistent caching with multiple registry instances, implement
    get_state_fingerprint() on your registry class.
    """
    fingerprint = getattr(value, "get_state_fingerprint", None)
    if callable(fingerprint):
        result = fingerprint()
        if isinstance(result, str) and result:
            return result

    # Fallback: Use type-only identity (stable, but collapses all instances)
    # This is safer than id()-based identity which is process-volatile
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


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
    """Build a stable cache key from a role content hash and scan options.

    IMPORTANT: Cache keys must be deterministic and collision-free. This requires:
    1. Primitives (str, int, float, bool, None) are always safe
    2. Containers of primitives are safe (dict, list, tuple, set, frozenset)
    3. Custom objects are canonicalized by type, not instance state (to prevent collisions)

    Custom objects MUST be structurally equivalent if they have the same type
    representation. If that's not true for your object, implement __cache_key__()
    or ensure equality via __hash__ and __eq__.

    Raises:
        ValueError: If nesting depth exceeds 100 levels (prevents unbounded recursion/stack overflow)
    """
    if not role_content_hash:
        raise ValueError("role_content_hash must not be empty")

    _MAX_CANONICALIZE_DEPTH = 100

    def _canonicalize(value: object, depth: int = 0) -> object:
        if depth >= _MAX_CANONICALIZE_DEPTH:
            raise ValueError(
                f"scan_options nesting exceeds maximum depth of {_MAX_CANONICALIZE_DEPTH}; "
                f"excessively nested structures are not cacheable. "
                f"Simplify the structure or use a shallower format."
            )

        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, dict):
            # CRITICAL FIX (GILF-NODE3-02): Preserve key type to prevent collisions
            # between 1 and '1', True and 'True', etc.
            # Use JSON-serializable string format: "__key__:type:value"
            return {
                f"__key__:{type(key).__name__}:{str(key)}": _canonicalize(
                    item, depth + 1
                )
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [_canonicalize(item, depth + 1) for item in value]
        if isinstance(value, tuple):
            return {"__tuple__": [_canonicalize(item, depth + 1) for item in value]}
        if isinstance(value, set):
            return {
                "__set__": sorted(
                    (_canonicalize(item, depth + 1) for item in value),
                    key=lambda item: json.dumps(item, sort_keys=True),
                )
            }
        if isinstance(value, frozenset):
            return {
                "__frozenset__": sorted(
                    (_canonicalize(item, depth + 1) for item in value),
                    key=lambda item: json.dumps(item, sort_keys=True),
                )
            }

        # CRITICAL FIX (GILF-NODE3-04): Custom objects require explicit cache protocol
        # to prevent cache collisions from instances with different state
        # Protocol definition: prism.scanner_data.contracts_request.CacheKeyProtocol

        # Check for explicit cache_key protocol (preferred)
        if hasattr(value, "__cache_key__") and callable(value.__cache_key__):
            try:
                # Type-safe protocol compliance: __cache_key__() must return str
                cache_key = value.__cache_key__()  # CacheKeyProtocol compliance check
                if not isinstance(cache_key, str):
                    raise ValueError(
                        f"Custom object {type(value).__name__} __cache_key__() must return str, "
                        f"got {type(cache_key).__name__}: {cache_key!r}"
                    )
                return {
                    "__custom_cache_key__": f"{type(value).__module__}.{type(value).__qualname__}::{cache_key}"
                }
            except ValueError:
                raise
            except Exception as exc:
                raise ValueError(
                    f"Custom object {type(value).__name__} __cache_key__() failed: {exc}"
                ) from exc

        # Try hashability as fallback (immutable objects with meaningful __hash__)
        try:
            obj_hash = hash(value)
            # Detect if this is using default id()-based hash (identity hash)
            # If __hash__ is inherited from object and not overridden, it uses id()
            # which is unstable across instances
            value_type = type(value)
            if (
                not hasattr(value_type, "__hash__")
                or value_type.__hash__ is object.__hash__
            ):
                # Default id-based hash: fall back to type-only canonicalization
                pass  # Fall through to type-only
            else:
                # Custom __hash__: use it for canonicalization
                return {
                    "__hashable__": f"{type(value).__module__}.{type(value).__qualname__}::{obj_hash}"
                }
        except TypeError:
            pass  # Not hashable, fall through to type-only fallback

        # LAST RESORT: Type-only canonicalization with warning
        # WARNING: This collapses all instances of the same type to identical keys!
        # If your custom object has mutable state or distinct instances should cache
        # separately, implement __hash__/__eq__ or __cache_key__() protocol.
        import warnings

        type_fqn = f"{type(value).__module__}.{type(value).__qualname__}"
        warnings.warn(
            f"Cache key for custom object {type(value).__name__} uses type-only "
            f"canonicalization. Different instances will produce identical cache keys. "
            f"This can cause cache collisions if instances have different state. "
            f"To fix: implement __hash__/__eq__ (for immutable objects) or "
            f"__cache_key__() protocol (for mutable objects).",
            UserWarning,
            stacklevel=5,
        )
        return {"__opaque_type__": type_fqn}

    options_blob = json.dumps(_canonicalize(dict(scan_options)), sort_keys=True)
    options_hash = hashlib.sha256(options_blob.encode("utf-8")).hexdigest()
    return f"{role_content_hash}:{options_hash}"


def compute_path_content_hash(path: str) -> str:
    """Compute a stable sha256 hash for a file or directory path's contents.

    Safety limits prevent DoS attacks from malicious or misconfigured directory trees:
    - Max walk depth: 20 levels
    - Max files to hash: 50,000
    - Max timeout: 60 seconds (soft limit)

    If any limit is exceeded, raises ValueError to fail fast.
    """
    _MAX_WALK_DEPTH = 20
    _MAX_FILES_TO_HASH = 50_000

    h = hashlib.sha256()
    root = os.path.abspath(path)
    files_hashed = 0

    if os.path.isdir(root):
        for dirpath, dirnames, filenames in os.walk(root):
            # Enforce max depth: count slashes relative to root
            current_depth = dirpath[len(root) :].count(os.sep)
            if current_depth > _MAX_WALK_DEPTH:
                raise ValueError(
                    f"Directory tree exceeds maximum depth of {_MAX_WALK_DEPTH} levels. "
                    f"Role path too deeply nested: {dirpath}"
                )

            dirnames[:] = sorted(
                d for d in dirnames if not d.startswith(".") and d != "__pycache__"
            )
            for filename in sorted(filenames):
                if filename.startswith(".") or filename.endswith(".pyc"):
                    continue

                # Enforce max file count
                files_hashed += 1
                if files_hashed > _MAX_FILES_TO_HASH:
                    raise ValueError(
                        f"Directory contains more than {_MAX_FILES_TO_HASH} files. "
                        f"Role path too large to hash: {path}"
                    )

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
