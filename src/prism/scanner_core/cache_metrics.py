"""Task 4.4: Cache metrics collection and reporting.

Provides cache performance metrics for monitoring and observability.
Collects hit rates, eviction patterns, and memory usage statistics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CacheMetrics:
    """Typed container for cache performance metrics."""

    total_hits: int
    total_misses: int
    hit_rate_percent: float
    total_entries: int
    max_entries: int
    total_memory_bytes: int
    max_memory_bytes: int
    memory_utilization_percent: float
    evictions_by_count: int
    evictions_by_memory: int
    total_evictions: int

    @classmethod
    def from_cache(cls, cache: Any) -> CacheMetrics:
        """Collect metrics from an InMemoryLRUScanCache instance."""
        hits, misses = cache.stats()
        total = hits + misses
        hit_rate = (100.0 * hits / total) if total > 0 else 0.0

        memory_stats = cache.memory_stats()

        return cls(
            total_hits=hits,
            total_misses=misses,
            hit_rate_percent=hit_rate,
            total_entries=len(cache),
            max_entries=cache._maxsize,
            total_memory_bytes=cache.total_memory_bytes,
            max_memory_bytes=cache._max_memory_bytes,
            memory_utilization_percent=memory_stats["memory_utilization_percent"],
            evictions_by_count=cache.evictions_by_count,
            evictions_by_memory=cache.evictions_by_memory,
            total_evictions=cache.evictions_by_count + cache.evictions_by_memory,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization."""
        return {
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "hit_rate_percent": round(self.hit_rate_percent, 2),
            "total_entries": self.total_entries,
            "max_entries": self.max_entries,
            "total_memory_bytes": self.total_memory_bytes,
            "max_memory_bytes": self.max_memory_bytes,
            "memory_utilization_percent": round(self.memory_utilization_percent, 2),
            "evictions_by_count": self.evictions_by_count,
            "evictions_by_memory": self.evictions_by_memory,
            "total_evictions": self.total_evictions,
        }

    def summary(self) -> str:
        """Return human-readable metrics summary."""
        return (
            f"Cache Metrics: {self.hit_rate_percent:.1f}% hits "
            f"({self.total_hits}/{self.total_hits + self.total_misses}), "
            f"{self.total_entries}/{self.max_entries} entries, "
            f"{self.memory_utilization_percent:.1f}% memory "
            f"({self.total_memory_bytes}/{self.max_memory_bytes} bytes), "
            f"{self.total_evictions} total evictions"
        )
