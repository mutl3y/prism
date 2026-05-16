from prism.scanner_plugins.registry import PluginRegistry


def test_reserved_unsupported_platforms_are_frozen_and_membership_works() -> None:
    registry = PluginRegistry()

    assert not registry.is_reserved_unsupported_platform("terraform")
    registry.register_reserved_unsupported_platform("terraform")
    registry.register_reserved_unsupported_platform("terraform")

    assert registry.is_reserved_unsupported_platform("terraform")
    assert not registry.is_reserved_unsupported_platform("kubernetes")
    assert isinstance(registry._reserved_unsupported_platforms, frozenset)
