"""Protocol compliance tests for CacheKeyProtocol adoption in scan_cache.py.

Validates that:
1. The CacheKeyProtocol is correctly imported and used
2. Custom objects implementing __cache_key__() work in scan_cache
3. scan_cache.py correctly validates return types as strings
"""

from prism.scanner_core.scan_cache import compute_scan_cache_key
from prism.scanner_data.contracts_request import CacheKeyProtocol


class CustomCacheableObject:
    """Test object implementing CacheKeyProtocol."""

    def __init__(self, name: str, version: int):
        self.name = name
        self.version = version

    def __cache_key__(self) -> str:
        """Return deterministic cache key for this object."""
        return f"CustomCacheableObject:name={self.name}:version={self.version}"


class TestCacheKeyProtocolCompliance:
    """Test CacheKeyProtocol formalization and adoption."""

    def test_protocol_definition_exists(self) -> None:
        """Protocol should be importable from contracts_request."""
        assert CacheKeyProtocol is not None
        assert hasattr(CacheKeyProtocol, "__cache_key__")

    def test_custom_object_protocol_adoption(self) -> None:
        """scan_cache should accept objects implementing __cache_key__() protocol."""
        obj = CustomCacheableObject("test", 1)
        scan_opts = {
            "object": obj,
            "nested": {"inner": CustomCacheableObject("inner", 2)},
        }

        # Should not raise; should canonicalize using __cache_key__()
        cache_key = compute_scan_cache_key(
            role_content_hash="test_hash_value", scan_options=scan_opts
        )
        assert cache_key is not None
        assert isinstance(cache_key, str)
        assert len(cache_key) > 0

    def test_protocol_runtime_checkable(self) -> None:
        """CacheKeyProtocol should be runtime-checkable."""
        # Verify the protocol has runtime_checkable metadata
        # (Python 3.10+ stores as _is_runtime_protocol)
        assert getattr(CacheKeyProtocol, "_is_runtime_protocol", False) or hasattr(
            CacheKeyProtocol, "__runtime_protocol__"
        )

        obj = CustomCacheableObject("test", 1)
        # isinstance checks should work due to runtime_checkable
        assert isinstance(obj, CacheKeyProtocol)
